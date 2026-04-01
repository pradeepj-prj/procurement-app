from __future__ import annotations

from typing import Any, Protocol


class DataBackend(Protocol):
    """Abstract interface for data access.

    Any class with matching method signatures satisfies this protocol
    (structural subtyping / PEP 544).  Tools call these methods —
    they never know whether the backing store is HANA or NetworkX.
    """

    def execute_sql(
        self, query: str, params: tuple = ()
    ) -> list[dict[str, Any]]:
        """Run a SQL query and return rows as dicts."""
        ...

    def get_vertex(self, vertex_id: str) -> dict[str, Any] | None:
        """Return a single vertex by ID, or None if not found."""
        ...

    def get_neighbors(
        self,
        vertex_id: str,
        edge_type: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict[str, Any]]:
        """Return vertices connected to *vertex_id*.

        *direction* is ``"outgoing"``, ``"incoming"``, or ``"both"``.
        If *edge_type* is given, only edges of that type are followed.
        """
        ...

    def search_vertices(
        self,
        query: str,
        vertex_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Case-insensitive substring search across vertex labels/names."""
        ...

    def get_vertex_counts(self) -> dict[str, int]:
        """Return ``{vertex_type: count}`` for every type in the graph."""
        ...

    def get_edge_counts(self) -> dict[str, int]:
        """Return ``{edge_type: count}`` for every type in the graph."""
        ...
