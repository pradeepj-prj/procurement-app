from __future__ import annotations

import logging
from typing import Any

from app.db.connection import ConnectionPool
from app.db.queries import graph as graph_q
from app.db.queries import relational as rel_q

logger = logging.getLogger(__name__)


def _rows_to_dicts(cursor) -> list[dict[str, Any]]:
    """Convert hdbcli cursor results (tuples) to list of dicts."""
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class HANABackend:
    """DataBackend implementation backed by SAP HANA Cloud.

    Uses a :class:`ConnectionPool` for connection management and the
    query library (``app.db.queries``) for SQL construction.
    """

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _execute(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute a query and return rows as dicts."""
        with self._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if cursor.description is None:
                return []
            return _rows_to_dicts(cursor)

    # ------------------------------------------------------------------
    # DataBackend interface
    # ------------------------------------------------------------------

    def execute_sql(
        self, query: str, params: tuple = ()
    ) -> list[dict[str, Any]]:
        return self._execute(query, params)

    def get_vertex(self, vertex_id: str) -> dict[str, Any] | None:
        sql, params = graph_q.vertex_by_id(vertex_id)
        rows = self._execute(sql, params)
        if not rows:
            return None
        row = rows[0]
        # Normalise column names to lowercase to match NetworkXBackend output
        return {
            "id": row.get("VERTEX_ID", vertex_id),
            "vertex_type": row.get("VERTEX_TYPE", ""),
            "label": row.get("LABEL", ""),
        }

    def get_neighbors(
        self,
        vertex_id: str,
        edge_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        sql, params = graph_q.neighbors(vertex_id, edge_type, direction)
        if not sql:
            return []
        rows = self._execute(sql, params)
        return [
            {
                "id": r.get("VERTEX_ID", ""),
                "vertex_type": r.get("VERTEX_TYPE", ""),
                "label": r.get("LABEL", ""),
                "edge_type": r.get("EDGE_TYPE", ""),
                "direction": r.get("DIRECTION", ""),
            }
            for r in rows
        ]

    def search_vertices(
        self,
        query: str,
        vertex_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        sql, params = graph_q.search_vertices(query, vertex_type, limit)
        rows = self._execute(sql, params)
        return [
            {
                "id": r.get("VERTEX_ID", ""),
                "vertex_type": r.get("VERTEX_TYPE", ""),
                "label": r.get("LABEL", ""),
            }
            for r in rows
        ]

    def get_vertex_counts(self) -> dict[str, int]:
        sql, params = graph_q.vertex_counts()
        rows = self._execute(sql, params)
        return {r["VERTEX_TYPE"]: r["COUNT"] for r in rows}

    def get_edge_counts(self) -> dict[str, int]:
        sql, params = graph_q.edge_counts()
        rows = self._execute(sql, params)
        return {r["EDGE_TYPE"]: r["COUNT"] for r in rows}
