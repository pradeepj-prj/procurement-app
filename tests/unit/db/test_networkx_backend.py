from __future__ import annotations

import pytest


class TestNetworkXBackendLoading:
    """Verify that CSVs load into the graph without error."""

    def test_graph_has_vertices(self, nx_backend):
        counts = nx_backend.get_vertex_counts()
        assert sum(counts.values()) > 0, "Graph should have vertices"

    def test_graph_has_edges(self, nx_backend):
        counts = nx_backend.get_edge_counts()
        assert sum(counts.values()) > 0, "Graph should have edges"

    def test_expected_vertex_types_present(self, nx_backend):
        counts = nx_backend.get_vertex_counts()
        expected = {
            "VENDOR", "MATERIAL", "PLANT", "CATEGORY",
            "PURCHASE_ORDER", "CONTRACT", "INVOICE",
            "GOODS_RECEIPT", "PAYMENT", "PURCHASE_REQ",
        }
        assert expected.issubset(counts.keys()), (
            f"Missing vertex types: {expected - counts.keys()}"
        )

    def test_expected_edge_types_present(self, nx_backend):
        counts = nx_backend.get_edge_counts()
        expected = {
            "SUPPLIES", "ORDERED_FROM", "CONTAINS_MATERIAL",
            "INVOICED_FOR", "RECEIVED_FOR", "PAYS",
            "BELONGS_TO_CATEGORY", "LOCATED_AT",
        }
        assert expected.issubset(counts.keys()), (
            f"Missing edge types: {expected - counts.keys()}"
        )


class TestGetVertex:
    def test_known_vendor(self, nx_backend):
        v = nx_backend.get_vertex("VND-HOKUYO")
        assert v is not None
        assert v["vertex_type"] == "VENDOR"
        assert "Hokuyo" in v["label"]

    def test_known_material(self, nx_backend):
        v = nx_backend.get_vertex("MAT-LIDAR-2D")
        assert v is not None
        assert v["vertex_type"] == "MATERIAL"

    def test_missing_vertex_returns_none(self, nx_backend):
        assert nx_backend.get_vertex("DOES-NOT-EXIST") is None


class TestSearchVertices:
    def test_search_lidar(self, nx_backend):
        results = nx_backend.search_vertices("lidar")
        assert len(results) > 0
        assert any("lidar" in r["label"].lower() for r in results)

    def test_search_with_type_filter(self, nx_backend):
        results = nx_backend.search_vertices("lidar", vertex_type="MATERIAL")
        assert all(r["vertex_type"] == "MATERIAL" for r in results)

    def test_search_respects_limit(self, nx_backend):
        results = nx_backend.search_vertices("", limit=5)
        assert len(results) <= 5

    def test_search_case_insensitive(self, nx_backend):
        upper = nx_backend.search_vertices("HOKUYO")
        lower = nx_backend.search_vertices("hokuyo")
        assert len(upper) == len(lower)


class TestGetNeighbors:
    def test_vendor_has_outgoing_neighbors(self, nx_backend):
        # Vendors supply materials → should have outgoing SUPPLIES edges
        # But edges go vendor→material only if source_list has vendor_id→material_id
        neighbors = nx_backend.get_neighbors("VND-HOKUYO", direction="outgoing")
        assert len(neighbors) > 0

    def test_vendor_has_incoming_neighbors(self, nx_backend):
        # POs are ORDERED_FROM vendor → vendor should have incoming edges
        neighbors = nx_backend.get_neighbors("VND-HOKUYO", direction="incoming")
        assert len(neighbors) > 0

    def test_filter_by_edge_type(self, nx_backend):
        neighbors = nx_backend.get_neighbors(
            "VND-HOKUYO", edge_type="SUPPLIES", direction="outgoing"
        )
        assert all(n["edge_type"] == "SUPPLIES" for n in neighbors)

    def test_missing_vertex_returns_empty(self, nx_backend):
        assert nx_backend.get_neighbors("DOES-NOT-EXIST") == []


class TestGetCounts:
    def test_vertex_counts_are_positive(self, nx_backend):
        counts = nx_backend.get_vertex_counts()
        for vtype, count in counts.items():
            if vtype != "UNKNOWN":
                assert count > 0, f"{vtype} should have > 0 vertices"

    def test_edge_counts_are_positive(self, nx_backend):
        counts = nx_backend.get_edge_counts()
        for etype, count in counts.items():
            assert count > 0, f"{etype} should have > 0 edges"


class TestExecuteSql:
    def test_raises_not_implemented(self, nx_backend):
        with pytest.raises(NotImplementedError):
            nx_backend.execute_sql("SELECT 1")
