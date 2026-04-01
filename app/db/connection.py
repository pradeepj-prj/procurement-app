from __future__ import annotations

import logging
import queue
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from app.config import settings

if TYPE_CHECKING:
    from hdbcli.dbapi import Connection

logger = logging.getLogger(__name__)

_PING_SQL = "SELECT 1 FROM DUMMY"


class ConnectionPool:
    """Thread-safe bounded connection pool for SAP HANA Cloud.

    Uses :class:`queue.Queue` to hold idle connections.  Connections are
    validated on checkout with ``SELECT 1 FROM DUMMY`` and silently
    replaced if the validation fails.
    """

    def __init__(self, pool_size: int = 5, checkout_timeout: float = 30.0) -> None:
        self._pool_size = pool_size
        self._checkout_timeout = checkout_timeout
        self._pool: queue.Queue[Connection] = queue.Queue(maxsize=pool_size)
        self._created = 0

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def _create_connection(self) -> Connection:
        from hdbcli import dbapi

        conn = dbapi.connect(
            address=settings.hana_host,
            port=settings.hana_port,
            user=settings.hana_user,
            password=settings.hana_password,
            encrypt=True,
            sslValidateCertificate=False,
        )
        logger.debug("Created new HANA connection (%d/%d)", self._created + 1, self._pool_size)
        self._created += 1
        return conn

    @staticmethod
    def _validate(conn: Connection) -> bool:
        try:
            cursor = conn.cursor()
            cursor.execute(_PING_SQL)
            cursor.close()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @contextmanager
    def get_connection(self) -> Iterator[Connection]:
        """Check out a validated connection; return it when done.

        Usage::

            with pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
        """
        conn = self._checkout()
        try:
            yield conn
        finally:
            self._return(conn)

    # ------------------------------------------------------------------
    # Internal checkout / return
    # ------------------------------------------------------------------

    def _checkout(self) -> Connection:
        # Try to get an existing connection from the pool (non-blocking).
        try:
            conn = self._pool.get_nowait()
            if self._validate(conn):
                return conn
            # Stale connection — discard and create a replacement.
            logger.debug("Discarded stale HANA connection")
            self._created -= 1
        except queue.Empty:
            pass

        # Room to create a new connection?
        if self._created < self._pool_size:
            return self._create_connection()

        # Pool exhausted — block until one is returned.
        try:
            conn = self._pool.get(timeout=self._checkout_timeout)
            if self._validate(conn):
                return conn
            self._created -= 1
            return self._create_connection()
        except queue.Empty:
            raise TimeoutError(
                f"Could not obtain a HANA connection within {self._checkout_timeout}s "
                f"(pool size: {self._pool_size})"
            )

    def _return(self, conn: Connection) -> None:
        try:
            self._pool.put_nowait(conn)
        except queue.Full:
            # Shouldn't happen, but just close the connection.
            conn.close()
            self._created -= 1

    def close_all(self) -> None:
        """Drain and close every connection in the pool."""
        while True:
            try:
                conn = self._pool.get_nowait()
                conn.close()
                self._created -= 1
            except queue.Empty:
                break
        logger.info("ConnectionPool closed all connections")
