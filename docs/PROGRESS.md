# Implementation Progress

This file tracks what was built in each subplan — patterns established, deviations from the original spec, and key decisions. It is the first thing read before starting any new subplan to ensure coherence across sessions.

## Completed Subplans

### Subplan 01: Project Scaffold (completed 2026-03-30)
**Files created**: `pyproject.toml`, `app/__init__.py`, `app/__main__.py`, `app/config.py`, `app/api/__init__.py`, `app/api/router.py`, `app/api/endpoints/__init__.py`, `app/api/middleware/__init__.py`, `app/api/models/__init__.py`
**Files modified**: `requirements.txt` (replaced placeholder with `-e .[dev]`)
**Key patterns established**:
- **Config singleton**: `from app.config import settings` — `pydantic-settings` `BaseSettings` with `.env` fallback, `lru_cache` singleton via `get_settings()`
- **Entry point**: `python -m app` via `app/__main__.py` — parses `--host`/`--port`, runs uvicorn with import string `"app.api.router:app"`
- **FastAPI app**: Created in `app/api/router.py` as `app = FastAPI(...)` — routers from later subplans will be included here
- **Package structure**: `app/api/endpoints/`, `app/api/middleware/`, `app/api/models/` — empty packages ready for later subplans
- **Dependencies**: All deps in `pyproject.toml` `[project.dependencies]`, dev-only in `[project.optional-dependencies] dev`; `requirements.txt` is just `-e .[dev]` for CF buildpack compatibility
- **Import style**: `from __future__ import annotations` at top of every module
**Key patterns followed** (from prior subplans): N/A (first subplan)
**Deviations from plan**:
- Added `pydantic-settings>=2.6.0` to dependencies (not in original subplan) — required since Pydantic v2 moved `BaseSettings` to a separate package
- Added `csv_dir` to config settings (not in original subplan) — needed for NetworkX backend fallback, already present in `.env.example`
**Git commit**: fcb0b0f

### Subplan 02: Database Abstraction Layer (completed 2026-04-01)
**Files created**: `app/db/__init__.py`, `app/db/backend.py`, `app/db/networkx_backend.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/unit/__init__.py`, `tests/unit/db/__init__.py`, `tests/unit/db/test_networkx_backend.py`
**Files modified**: none
**Key patterns established**:
- **DataBackend Protocol**: `app.db.backend.DataBackend` — structural subtyping interface (PEP 544) with 6 methods: `execute_sql`, `get_vertex`, `get_neighbors`, `search_vertices`, `get_vertex_counts`, `get_edge_counts`
- **Backend factory**: `from app.db import get_backend` — reads `settings.graph_backend` to return the appropriate implementation; lazy imports keep unused backends out of memory
- **NetworkXBackend**: CSV → DiGraph loader with declarative vertex/edge mapping tables (`_VERTEX_DEFS`, `_EDGE_DEFS`); all 10 vertex types and 14 edge types from the HANA graph workspace are represented
- **Test structure**: `tests/unit/db/` with session-scoped `nx_backend` fixture in `tests/conftest.py`; tests skip gracefully if CSV data is unavailable
**Key patterns followed** (from prior subplans):
- Config singleton `from app.config import settings` with `settings.graph_backend` and `settings.csv_dir` (subplan 01)
- `from __future__ import annotations` at top of every module (subplan 01)
- Package structure mirrors `app/api/` convention (subplan 01)
**Deviations from plan**:
- Used stdlib `csv` module instead of pandas — simpler, no runtime dependency needed (pandas is dev-only)
- `execute_sql` raises `NotImplementedError` as specified; tools should use typed methods
**Git commit**: 823bb55

### Subplan 03: HANA Backend & SQL Query Library (completed 2026-04-01)
**Files created**: `app/db/connection.py`, `app/db/hana_backend.py`, `app/db/queries/__init__.py`, `app/db/queries/graph.py`, `app/db/queries/relational.py`, `tests/unit/db/test_queries.py`, `tests/integration/__init__.py`, `tests/integration/db/__init__.py`, `tests/integration/db/test_hana_backend.py`
**Files modified**: `app/db/__init__.py` (replaced HANA `NotImplementedError` with real `HANABackend` + `ConnectionPool` creation)
**Key patterns established**:
- **ConnectionPool**: `app.db.connection.ConnectionPool` — thread-safe `queue.Queue`-based pool with context manager checkout, validation ping (`SELECT 1 FROM DUMMY`), and configurable size/timeout
- **Query library**: `app.db.queries.graph` and `app.db.queries.relational` — functions return `(sql, params)` tuples; all use `?` placeholders (no string formatting); schema name from `settings.hana_schema`
- **HANABackend**: `app.db.hana_backend.HANABackend` — implements `DataBackend` Protocol using pool + query library; normalises HANA uppercase column names to lowercase keys matching `NetworkXBackend` output
- **Integration test pattern**: `tests/integration/` with `pytestmark = pytest.mark.skipif(not os.environ.get("HANA_HOST"), ...)` for graceful skip without credentials
**Key patterns followed** (from prior subplans):
- `DataBackend` Protocol with 6 methods (subplan 02)
- Backend factory `get_backend()` with lazy imports (subplan 02)
- Config singleton `from app.config import settings` (subplan 01)
- `from __future__ import annotations` at top of every module (subplan 01)
**Deviations from plan**:
- Graph view queries use `settings.hana_schema` instead of hard-coded `"PROCUREMENT"` — makes schema configurable as it should be
- `V_ALL_VERTICES` only has 3 columns (`vertex_id`, `vertex_type`, `label`), so `get_vertex()` returns these 3 fields; full relational attributes available via `execute_sql()` or the relational query library
**Git commit**: a2f1547
