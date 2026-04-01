"""Integration tests for HANABackend — skipped if HANA_HOST is not set."""
from __future__ import annotations

import os

import pytest

_skip = pytest.mark.skipif(
    not os.environ.get("HANA_HOST"),
    reason="HANA_HOST not set — skipping HANA integration tests",
)
pytestmark = _skip


@pytest.fixture(scope="module")
def hana_backend():
    from app.db.connection import ConnectionPool
    from app.db.hana_backend import HANABackend

    pool = ConnectionPool(pool_size=2)
    backend = HANABackend(pool=pool)
    yield backend
    pool.close_all()


class TestConnectionPool:
    def test_checkout_and_return(self, hana_backend):
        """Pool checkout/return cycle works without error."""
        with hana_backend._pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM DUMMY")
            row = cursor.fetchone()
            assert row[0] == 1


class TestHANABackendMethods:
    def test_get_vertex(self, hana_backend):
        v = hana_backend.get_vertex("VND-HOKUYO")
        assert v is not None
        assert v["vertex_type"] == "VENDOR"

    def test_get_vertex_missing(self, hana_backend):
        assert hana_backend.get_vertex("DOES-NOT-EXIST") is None

    def test_search_vertices(self, hana_backend):
        results = hana_backend.search_vertices("lidar")
        assert len(results) > 0

    def test_get_neighbors(self, hana_backend):
        neighbors = hana_backend.get_neighbors("VND-HOKUYO", direction="outgoing")
        assert len(neighbors) > 0

    def test_get_vertex_counts(self, hana_backend):
        counts = hana_backend.get_vertex_counts()
        assert "VENDOR" in counts
        assert counts["VENDOR"] > 0

    def test_get_edge_counts(self, hana_backend):
        counts = hana_backend.get_edge_counts()
        assert "SUPPLIES" in counts
        assert counts["SUPPLIES"] > 0

    def test_execute_sql(self, hana_backend):
        rows = hana_backend.execute_sql("SELECT 1 AS \"val\" FROM DUMMY")
        assert len(rows) == 1
        assert rows[0]["val"] == 1
