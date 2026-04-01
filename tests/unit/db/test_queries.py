"""Test that query functions produce correct SQL and parameter tuples.

These tests need zero database access — they only verify SQL construction.
"""
from __future__ import annotations

from app.db.queries import graph, relational


# ---------------------------------------------------------------------------
# Graph queries
# ---------------------------------------------------------------------------

class TestGraphVertexById:
    def test_returns_sql_and_one_param(self):
        sql, params = graph.vertex_by_id("VND-HOKUYO")
        assert "V_ALL_VERTICES" in sql
        assert "VERTEX_ID" in sql
        assert params == ("VND-HOKUYO",)
        assert sql.count("?") == len(params)


class TestGraphSearchVertices:
    def test_basic_search(self):
        sql, params = graph.search_vertices("lidar")
        assert "LIKE" in sql
        assert "%lidar%" in params
        assert sql.count("?") == len(params)

    def test_search_with_type_filter(self):
        sql, params = graph.search_vertices("lidar", vertex_type="MATERIAL")
        assert "VERTEX_TYPE" in sql
        assert "MATERIAL" in params
        assert sql.count("?") == len(params)

    def test_search_with_limit(self):
        sql, params = graph.search_vertices("sensor", limit=10)
        assert "LIMIT" in sql
        assert 10 in params
        assert sql.count("?") == len(params)


class TestGraphNeighbors:
    def test_outgoing(self):
        sql, params = graph.neighbors("VND-HOKUYO", direction="outgoing")
        assert "SOURCE_VERTEX" in sql
        assert "VND-HOKUYO" in params
        assert sql.count("?") == len(params)

    def test_incoming(self):
        sql, params = graph.neighbors("VND-HOKUYO", direction="incoming")
        assert "TARGET_VERTEX" in sql
        assert "VND-HOKUYO" in params
        assert sql.count("?") == len(params)

    def test_both(self):
        sql, params = graph.neighbors("VND-HOKUYO", direction="both")
        assert "UNION ALL" in sql
        assert params.count("VND-HOKUYO") == 2
        assert sql.count("?") == len(params)

    def test_with_edge_type_filter(self):
        sql, params = graph.neighbors("VND-HOKUYO", edge_type="SUPPLIES", direction="outgoing")
        assert "EDGE_TYPE" in sql
        assert "SUPPLIES" in params
        assert sql.count("?") == len(params)

    def test_both_with_edge_type(self):
        sql, params = graph.neighbors("PO-000001", edge_type="ORDERED_FROM", direction="both")
        assert "UNION ALL" in sql
        assert params.count("ORDERED_FROM") == 2
        assert sql.count("?") == len(params)


class TestGraphCounts:
    def test_vertex_counts(self):
        sql, params = graph.vertex_counts()
        assert "GROUP BY" in sql
        assert "VERTEX_TYPE" in sql
        assert params == ()

    def test_edge_counts(self):
        sql, params = graph.edge_counts()
        assert "GROUP BY" in sql
        assert "EDGE_TYPE" in sql
        assert params == ()


# ---------------------------------------------------------------------------
# Relational queries
# ---------------------------------------------------------------------------

class TestRelationalVendor:
    def test_vendor_by_id(self):
        sql, params = relational.vendor_by_id("VND-HOKUYO")
        assert "vendor_master" in sql
        assert params == ("VND-HOKUYO",)
        assert sql.count("?") == len(params)

    def test_filter_vendors_no_filters(self):
        sql, params = relational.filter_vendors()
        assert "WHERE" not in sql.split("LIMIT")[0]
        assert sql.count("?") == len(params)

    def test_filter_vendors_all_filters(self):
        sql, params = relational.filter_vendors(
            min_risk_score=70, country="JP", status="ACTIVE", limit=10
        )
        assert "risk_score" in sql
        assert "country" in sql
        assert "status" in sql
        assert 70 in params
        assert "JP" in params
        assert "ACTIVE" in params
        assert sql.count("?") == len(params)

    def test_filter_vendors_partial_filters(self):
        sql, params = relational.filter_vendors(country="CN")
        assert "country" in sql
        assert "risk_score" not in sql
        assert sql.count("?") == len(params)


class TestRelationalMaterial:
    def test_material_by_id(self):
        sql, params = relational.material_by_id("MAT-LIDAR-2D")
        assert "material_master" in sql
        assert params == ("MAT-LIDAR-2D",)
        assert sql.count("?") == len(params)


class TestRelationalSourceList:
    def test_materials_for_vendor(self):
        sql, params = relational.materials_for_vendor("VND-HOKUYO")
        assert "source_list" in sql
        assert "material_master" in sql
        assert params == ("VND-HOKUYO",)
        assert sql.count("?") == len(params)

    def test_vendors_for_material(self):
        sql, params = relational.vendors_for_material("MAT-LIDAR-2D")
        assert "source_list" in sql
        assert "vendor_master" in sql
        assert params == ("MAT-LIDAR-2D",)
        assert sql.count("?") == len(params)


class TestRelationalContract:
    def test_contract_by_id(self):
        sql, params = relational.contract_by_id("CTR-001")
        assert "contract_header" in sql
        assert params == ("CTR-001",)
        assert sql.count("?") == len(params)

    def test_contracts_for_vendor(self):
        sql, params = relational.contracts_for_vendor("VND-HOKUYO")
        assert "contract_header" in sql
        assert params == ("VND-HOKUYO",)
        assert sql.count("?") == len(params)


class TestRelationalPO:
    def test_po_by_id(self):
        sql, params = relational.po_by_id("PO-000001")
        assert "po_header" in sql
        assert params == ("PO-000001",)

    def test_pos_for_vendor(self):
        sql, params = relational.pos_for_vendor("VND-HOKUYO")
        assert "po_header" in sql
        assert params == ("VND-HOKUYO",)

    def test_pos_for_material(self):
        sql, params = relational.pos_for_material("MAT-LIDAR-2D")
        assert "po_line_item" in sql
        assert params == ("MAT-LIDAR-2D",)

    def test_pos_for_contract(self):
        sql, params = relational.pos_for_contract("CTR-001")
        assert "po_line_item" in sql
        assert params == ("CTR-001",)

    def test_pos_for_plant(self):
        sql, params = relational.pos_for_plant("SG01")
        assert "po_header" in sql
        assert params == ("SG01",)


class TestRelationalSpend:
    def test_spend_by_vendor(self):
        sql, params = relational.spend_by_vendor(limit=10)
        assert "SUM" in sql
        assert "GROUP BY" in sql
        assert "ORDER BY" in sql
        assert 10 in params
        assert sql.count("?") == len(params)

    def test_spend_by_vendor_default_limit(self):
        sql, params = relational.spend_by_vendor()
        assert 20 in params
