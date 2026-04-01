"""SQL queries against the HANA graph vertex/edge views.

Every function returns ``(sql, params)`` — a parameterized query string
and a tuple of bind values.  The caller is responsible for executing.
"""
from __future__ import annotations

from app.config import settings

_S = settings.hana_schema


def vertex_by_id(vertex_id: str) -> tuple[str, tuple]:
    """Look up a single vertex by ID from the unified vertex view."""
    return (
        f'SELECT * FROM "{_S}"."V_ALL_VERTICES" WHERE "VERTEX_ID" = ?',
        (vertex_id,),
    )


def search_vertices(
    query: str,
    vertex_type: str | None = None,
    limit: int = 20,
) -> tuple[str, tuple]:
    """Case-insensitive substring search on vertex label/ID."""
    clauses = [
        '("LABEL" LIKE ? OR "VERTEX_ID" LIKE ?)',
    ]
    params: list[str | int] = [f"%{query}%", f"%{query}%"]

    if vertex_type is not None:
        clauses.append('"VERTEX_TYPE" = ?')
        params.append(vertex_type)

    where = " AND ".join(clauses)
    return (
        f'SELECT * FROM "{_S}"."V_ALL_VERTICES" WHERE {where} LIMIT ?',
        (*params, limit),
    )


def neighbors(
    vertex_id: str,
    edge_type: str | None = None,
    direction: str = "outgoing",
) -> tuple[str, tuple]:
    """Find vertices connected to *vertex_id* via the edge view.

    Returns neighbour vertex columns plus the edge type and direction.
    """
    parts: list[str] = []
    params: list[str] = []

    if direction in ("outgoing", "both"):
        et_clause = ' AND e."EDGE_TYPE" = ?' if edge_type else ""
        et_params = [edge_type] if edge_type else []
        parts.append(
            f'SELECT v."VERTEX_ID", v."VERTEX_TYPE", v."LABEL", '
            f"e.\"EDGE_TYPE\", 'outgoing' AS \"DIRECTION\" "
            f'FROM "{_S}"."E_ALL_EDGES" e '
            f'JOIN "{_S}"."V_ALL_VERTICES" v ON v."VERTEX_ID" = e."TARGET_VERTEX" '
            f'WHERE e."SOURCE_VERTEX" = ?{et_clause}'
        )
        params.extend([vertex_id, *et_params])

    if direction in ("incoming", "both"):
        et_clause = ' AND e."EDGE_TYPE" = ?' if edge_type else ""
        et_params = [edge_type] if edge_type else []
        parts.append(
            f'SELECT v."VERTEX_ID", v."VERTEX_TYPE", v."LABEL", '
            f"e.\"EDGE_TYPE\", 'incoming' AS \"DIRECTION\" "
            f'FROM "{_S}"."E_ALL_EDGES" e '
            f'JOIN "{_S}"."V_ALL_VERTICES" v ON v."VERTEX_ID" = e."SOURCE_VERTEX" '
            f'WHERE e."TARGET_VERTEX" = ?{et_clause}'
        )
        params.extend([vertex_id, *et_params])

    sql = " UNION ALL ".join(parts)
    return (sql, tuple(params))


def vertex_counts() -> tuple[str, tuple]:
    """Count vertices grouped by type."""
    return (
        f'SELECT "VERTEX_TYPE", COUNT(*) AS "COUNT" '
        f'FROM "{_S}"."V_ALL_VERTICES" GROUP BY "VERTEX_TYPE"',
        (),
    )


def edge_counts() -> tuple[str, tuple]:
    """Count edges grouped by type."""
    return (
        f'SELECT "EDGE_TYPE", COUNT(*) AS "COUNT" '
        f'FROM "{_S}"."E_ALL_EDGES" GROUP BY "EDGE_TYPE"',
        (),
    )
