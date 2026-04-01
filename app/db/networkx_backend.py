from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

import networkx as nx

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vertex type → (csv filename, id column, label column, extra attrs)
# ---------------------------------------------------------------------------
_VERTEX_DEFS: list[tuple[str, str, str, str]] = [
    # (csv_file, id_col, label_col, vertex_type)
    ("vendor_master.csv", "vendor_id", "vendor_name", "VENDOR"),
    ("material_master.csv", "material_id", "description", "MATERIAL"),
    ("plant.csv", "plant_id", "plant_name", "PLANT"),
    ("category_hierarchy.csv", "category_id", "category_name", "CATEGORY"),
    ("po_header.csv", "po_id", "po_id", "PURCHASE_ORDER"),
    ("contract_header.csv", "contract_id", "contract_id", "CONTRACT"),
    ("invoice_header.csv", "invoice_id", "invoice_id", "INVOICE"),
    ("gr_header.csv", "gr_id", "gr_id", "GOODS_RECEIPT"),
    ("payment.csv", "payment_id", "payment_id", "PAYMENT"),
    ("pr_header.csv", "pr_id", "pr_id", "PURCHASE_REQ"),
]

# ---------------------------------------------------------------------------
# Edge definitions: (csv, source_col, target_col, edge_type)
#
# Each entry says: "for every row in *csv*, create an edge from the value
# in *source_col* to the value in *target_col* with the given *edge_type*."
# ---------------------------------------------------------------------------
_EDGE_DEFS: list[tuple[str, str, str, str]] = [
    # SUPPLIES: vendor → material  (source_list links them)
    ("source_list.csv", "vendor_id", "material_id", "SUPPLIES"),
    # ORDERED_FROM: PO → vendor
    ("po_header.csv", "po_id", "vendor_id", "ORDERED_FROM"),
    # CONTAINS_MATERIAL: PO → material  (via line items)
    ("po_line_item.csv", "po_id", "material_id", "CONTAINS_MATERIAL"),
    # UNDER_CONTRACT: PO line → contract  (if contract_id present)
    ("po_line_item.csv", "po_id", "contract_id", "UNDER_CONTRACT"),
    # INVOICED_FOR: invoice → PO
    ("invoice_header.csv", "invoice_id", "po_id", "INVOICED_FOR"),
    # RECEIVED_FOR: goods receipt → PO
    ("gr_header.csv", "gr_id", "po_id", "RECEIVED_FOR"),
    # PAYS: payment → invoice  (via link table)
    ("payment_invoice_link.csv", "payment_id", "invoice_id", "PAYS"),
    # BELONGS_TO_CATEGORY: material → category
    ("material_master.csv", "material_id", "category_id", "BELONGS_TO_CATEGORY"),
    # CATEGORY_PARENT: category → parent category
    ("category_hierarchy.csv", "category_id", "parent_category_id", "CATEGORY_PARENT"),
    # LOCATED_AT: PO → plant
    ("po_header.csv", "po_id", "plant_id", "LOCATED_AT"),
    # HAS_CONTRACT: vendor → contract
    ("contract_header.csv", "vendor_id", "contract_id", "HAS_CONTRACT"),
    # REQUESTED_MATERIAL: PR → material  (via line items)
    ("pr_line_item.csv", "pr_id", "material_id", "REQUESTED_MATERIAL"),
    # INVOICED_BY_VENDOR: invoice → vendor
    ("invoice_header.csv", "invoice_id", "vendor_id", "INVOICED_BY_VENDOR"),
    # PAID_TO_VENDOR: payment → vendor
    ("payment.csv", "payment_id", "vendor_id", "PAID_TO_VENDOR"),
]


class NetworkXBackend:
    """Graph backend backed by CSV files loaded into a NetworkX DiGraph.

    Intended for local development when HANA Cloud is unavailable.
    """

    def __init__(self, csv_dir: str | None = None) -> None:
        self._csv_dir = Path(csv_dir or settings.csv_dir)
        self._graph = nx.DiGraph()
        self._load()
        logger.info(
            "NetworkXBackend ready — %d vertices, %d edges",
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        self._load_vertices()
        self._load_edges()

    def _read_csv(self, filename: str) -> list[dict[str, str]]:
        path = self._csv_dir / filename
        if not path.exists():
            logger.warning("CSV not found, skipping: %s", path)
            return []
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _load_vertices(self) -> None:
        for csv_file, id_col, label_col, vtype in _VERTEX_DEFS:
            rows = self._read_csv(csv_file)
            for row in rows:
                vid = row[id_col]
                self._graph.add_node(
                    vid,
                    vertex_type=vtype,
                    label=row.get(label_col, vid),
                    **row,
                )
            logger.debug("Loaded %d %s vertices from %s", len(rows), vtype, csv_file)

    def _load_edges(self) -> None:
        for csv_file, src_col, tgt_col, etype in _EDGE_DEFS:
            rows = self._read_csv(csv_file)
            count = 0
            for row in rows:
                src = row.get(src_col, "")
                tgt = row.get(tgt_col, "")
                if not src or not tgt:
                    continue
                # Ensure both endpoints exist as nodes (some may only appear
                # in edge CSVs).  Add them without vertex_type if missing.
                if src not in self._graph:
                    self._graph.add_node(src, vertex_type="UNKNOWN", label=src)
                if tgt not in self._graph:
                    self._graph.add_node(tgt, vertex_type="UNKNOWN", label=tgt)
                self._graph.add_edge(src, tgt, edge_type=etype, **row)
                count += 1
            logger.debug("Loaded %d %s edges from %s", count, etype, csv_file)

    # ------------------------------------------------------------------
    # DataBackend interface
    # ------------------------------------------------------------------

    def execute_sql(
        self, query: str, params: tuple = ()
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(
            "NetworkXBackend does not support raw SQL. "
            "Use the typed methods (get_vertex, search_vertices, …) instead."
        )

    def get_vertex(self, vertex_id: str) -> dict[str, Any] | None:
        if vertex_id not in self._graph:
            return None
        return {"id": vertex_id, **self._graph.nodes[vertex_id]}

    def get_neighbors(
        self,
        vertex_id: str,
        edge_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        if vertex_id not in self._graph:
            return []

        results: list[dict[str, Any]] = []

        if direction in ("outgoing", "both"):
            for _, tgt, data in self._graph.out_edges(vertex_id, data=True):
                if edge_type and data.get("edge_type") != edge_type:
                    continue
                results.append({
                    "id": tgt,
                    "edge_type": data.get("edge_type"),
                    "direction": "outgoing",
                    **self._graph.nodes[tgt],
                })

        if direction in ("incoming", "both"):
            for src, _, data in self._graph.in_edges(vertex_id, data=True):
                if edge_type and data.get("edge_type") != edge_type:
                    continue
                results.append({
                    "id": src,
                    "edge_type": data.get("edge_type"),
                    "direction": "incoming",
                    **self._graph.nodes[src],
                })

        return results

    def search_vertices(
        self,
        query: str,
        vertex_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for vid, data in self._graph.nodes(data=True):
            if vertex_type and data.get("vertex_type") != vertex_type:
                continue
            label = str(data.get("label", "")).lower()
            vid_lower = vid.lower()
            if query_lower in label or query_lower in vid_lower:
                results.append({"id": vid, **data})
                if len(results) >= limit:
                    break

        return results

    def get_vertex_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, data in self._graph.nodes(data=True):
            vtype = data.get("vertex_type", "UNKNOWN")
            counts[vtype] = counts.get(vtype, 0) + 1
        return counts

    def get_edge_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, _, data in self._graph.edges(data=True):
            etype = data.get("edge_type", "UNKNOWN")
            counts[etype] = counts.get(etype, 0) + 1
        return counts
