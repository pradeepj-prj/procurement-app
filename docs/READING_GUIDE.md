# Project Reading Guide

A structured walkthrough of the procurement-genai-backend codebase, organized by subplan. Each section provides a reading list (in order), a flow to trace, and a risk to watch for.

**Time budget**: ~15 minutes per subplan, ~1 hour total.

---

## Subplan 01 — Project Scaffold

**Scope**: `pyproject.toml`, config module, FastAPI entry point, application wiring.

### Reading List (5 files, in order)

1. **`app/__main__.py`**
   *Question: Why does uvicorn.run receive an import string (`"app.api.router:app"`) instead of the app object directly, and what does that enable?*

2. **`pyproject.toml`**
   *Question: What is the relationship between `[project.dependencies]` and `[project.optional-dependencies] dev`, and why are networkx and pandas in dev-only?*

3. **`requirements.txt`**
   *Question: This file contains a single line (`-e .[dev]`). Why does it exist at all, and what does the `-e .` syntax tell pip to do?*

4. **`app/config.py`**
   *Question: How does the `lru_cache` on `get_settings()` interact with the module-level `settings = get_settings()` line to guarantee a singleton, and what would break if you called `Settings()` directly in multiple places?*

5. **`app/api/router.py`**
   *Question: Why is `get_backend()` imported inside the `lifespan()` function body rather than at the top of the module, and what problem does that lazy import solve?*

### Flow to Trace

**App Startup** — documented at `docs/request-flows/app-startup.md`.

Trace this path: `python -m app` invokes `app/__main__.py:main()`, which calls `uvicorn.run("app.api.router:app", ...)`. Uvicorn imports `app.api.router`, which constructs the `FastAPI` instance at module level (registering CORS middleware and the health router). Before serving requests, Uvicorn triggers the `lifespan()` async context manager, which calls `get_backend()` and attaches the result to `app.state.backend`. Only then do incoming requests reach endpoints.

Pay attention to the boundary between "module-level execution" (FastAPI construction, middleware registration) and "lifespan execution" (backend initialization). Understanding which code runs when is the key insight.

### Risk to Watch

**The config singleton is evaluated at import time.** The line `settings: Settings = get_settings()` at the bottom of `app/config.py` runs the moment any module does `from app.config import settings`. This means environment variables must already be set before the first import of anything in the `app` package. In tests, this makes it difficult to override settings after import — you would need to either patch the cached value or clear the `lru_cache`. The `lru_cache` also means calling `get_settings()` with different env vars later in the process lifetime will silently return stale values.

---

## Subplan 02 — Database Abstraction Layer

**Scope**: DataBackend Protocol, NetworkX backend, backend factory, config wiring, test structure.

### Reading List (5 files, in order)

1. **`app/config.py`** (49 lines)
   *Question: How does the application decide whether to use HANA or NetworkX, and where does the default CSV path come from?*
   Focus on `graph_backend` and `csv_dir`. These two settings drive everything in this subplan. Notice the `lru_cache` singleton pattern and `.env` fallback.

2. **`app/db/backend.py`** (53 lines)
   *Question: What are the 6 operations any data backend must support, and why is this a Protocol instead of an ABC?*
   This is the single most important file in the subplan. It defines the contract. Notice there is no inheritance requirement — any class with matching method signatures satisfies it (PEP 544 structural subtyping). Pay attention to the return types: everything returns `list[dict[str, Any]]` or `dict[str, Any] | None`.

3. **`app/db/networkx_backend.py`** (219 lines)
   *Question: How does the declarative `_VERTEX_DEFS` / `_EDGE_DEFS` mapping translate CSV rows into a NetworkX DiGraph, and how does each DataBackend method query that graph?*
   The key insight is the two mapping tables at the top. Every CSV file maps to either vertex nodes or directed edges. The `_load_vertices` and `_load_edges` methods iterate these tables. Then the 6 interface methods query the in-memory graph. Notice `execute_sql` deliberately raises `NotImplementedError`.

4. **`app/db/__init__.py`** (30 lines)
   *Question: How does `get_backend()` use lazy imports to avoid loading unused dependencies, and what happens if the config value is invalid?*
   This is the factory. The imports for `NetworkXBackend` and `HANABackend` are inside the `if` branches, not at the top of the file. This means if you run with `graph_backend=networkx`, the HANA driver is never imported. The final `raise ValueError` is the safety net.

5. **`tests/unit/db/test_networkx_backend.py`** (114 lines) + **`tests/conftest.py`** (24 lines)
   *Question: How does the test suite gracefully skip when CSV data is absent, and what aspects of the backend contract does it verify?*
   Start with `conftest.py` to see the session-scoped `nx_backend` fixture and the skip logic. Then read the test file. Notice it tests all 6 protocol methods and checks structural properties (vertex types present, edge types present, case-insensitive search, limit enforcement).

### Flow to Trace

**Backend selection at app startup** — documented at `docs/request-flows/backend-selection.md`.

1. `app/api/router.py` lifespan hook calls `get_backend()` on startup
2. `get_backend()` reads `settings.graph_backend` from `app/config.py`
3. If `"networkx"`: lazily imports `NetworkXBackend`, which reads `settings.csv_dir`, opens CSV files, builds a DiGraph
4. The returned backend is stored in `app.state.backend` and injected into endpoints via `Depends(get_backend)` (subplan 04)

### Risk to Watch

**The Protocol is not enforced at construction time.** Because `DataBackend` is a Protocol (structural subtyping), there is no `isinstance` check or registration. If someone adds a new method to `DataBackend` but forgets to implement it in `NetworkXBackend` or `HANABackend`, the code will only fail at runtime when that method is called — not at startup, not at import time, and not during tests unless there is a test that exercises that specific method. The only safety net is the test suite covering all 6 methods, and `mypy` type checking (if configured).

---

## Subplan 03 — HANA Backend & SQL Query Library

**Scope**: HANA connection pool, parameterized SQL queries, HANABackend implementation.

### Reading List (5 files, in order)

1. **`app/db/backend.py`** (53 lines)
   *Question: What are the 6 methods in the `DataBackend` protocol, and why does using `Protocol` (structural subtyping) mean `HANABackend` never needs to explicitly inherit from it?*

2. **`app/db/connection.py`** (132 lines)
   *Question: In `_checkout()`, there are three code paths for obtaining a connection (pool has one, room to create, pool exhausted). What happens in each path if validation fails — and could you leak a connection count in any of them?*

3. **`app/db/queries/graph.py`** (98 lines)
   *Question: How does the `neighbors()` function handle bidirectional traversal, and why does it use `UNION ALL` instead of `UNION`?*

4. **`app/db/hana_backend.py`** (107 lines)
   *Question: Why does `get_vertex()` normalize HANA uppercase column names (`VERTEX_ID`) to lowercase keys (`id`), and what would break downstream if it didn't?*

5. **`tests/unit/db/test_queries.py`** (201 lines)
   *Question: Every test asserts `sql.count("?") == len(params)`. Why is this the single most important invariant for a parameterized query library?*

### Flow to Trace

**HANA Query Execution** — documented at `docs/request-flows/hana-query-execution.md`.

Trace this path: Start at `HANABackend.get_neighbors("VND-HOKUYO", edge_type="SUPPLIES")`. Follow the call into `graph_q.neighbors()` (see how it builds the SQL with the optional `EDGE_TYPE` clause). Then follow back into `_execute()`, which calls `pool.get_connection()` — trace the checkout logic in `connection.py` (what if the pool is empty? what if the connection is stale?). Finally, watch `_rows_to_dicts()` convert cursor tuples into dicts, and see the normalization in `get_neighbors()` that maps HANA column names to the app-level schema.

The whole chain is: `HANABackend.get_neighbors` -> `graph_q.neighbors` -> `_execute` -> `pool.get_connection` -> `cursor.execute` -> `_rows_to_dicts` -> normalize keys -> return.

### Risk to Watch

**The relational query library (`queries/relational.py`) is fully built but not wired into any public `HANABackend` method.** The backend only exposes graph-view queries through its typed methods (`get_vertex`, `get_neighbors`, etc.). Relational queries like `spend_by_vendor` or `filter_vendors` can only be reached via the raw `execute_sql()` escape hatch. When later subplans build LLM tools that need relational data, they will either need to call `execute_sql()` directly with hand-built SQL, or new methods will need to be added to both `DataBackend` and both backend implementations.

---

## Subplan 04 — Health Endpoints, CORS Middleware, Dependency Injection

**Scope**: Health/readiness probes, CORS configuration, FastAPI dependency injection wiring.

### Reading List (5 files, in order)

1. **`app/api/router.py`** (34 lines)
   *Question: Why is `get_backend()` imported inside the lifespan function body rather than at the top of the module?*

2. **`app/db/backend.py`** (53 lines)
   *Question: What makes `DataBackend` a Protocol (structural subtype) rather than an ABC, and what does that mean for classes that want to satisfy it?*

3. **`app/api/dependencies.py`** (16 lines)
   *Question: How does this 3-line function connect the backend created during startup to any endpoint that needs it?*

4. **`app/api/endpoints/health.py`** (47 lines)
   *Question: Why does `/ready` catch `NotImplementedError` from `execute_sql` and fall back to `get_vertex_counts()` — what backend triggers that path?*

5. **`tests/unit/api/test_health.py`** (73 lines)
   *Question: Why does the test file set `os.environ["GRAPH_BACKEND"]` before importing the app, and why is the client fixture `scope="module"` rather than `scope="function"`?*

**Bonus (if time permits):**

6. **`app/api/middleware/cors.py`** (22 lines)
   *Question: What happens if a request arrives from `http://evil.example.com` — does the server reject it, or does something else enforce the policy?*

### Flow to Trace

**The `/ready` request, end to end** — documented at `docs/request-flows/get-ready.md`.

1. **Startup**: `app/__main__.py` launches Uvicorn with `app.api.router:app`. FastAPI runs the `lifespan()` context manager, which calls `get_backend()` and stashes the result on `app.state.backend`.

2. **Request arrives**: `GET /ready` hits the health router in `app/api/endpoints/health.py`.

3. **Dependency injection**: FastAPI sees `backend: DataBackend = Depends(get_backend)` in the `ready()` signature. It calls `app/api/dependencies.py:get_backend(request)`, which reads `request.app.state.backend` and passes it in.

4. **Backend probe**: The endpoint tries `backend.execute_sql("SELECT 1 FROM DUMMY")`. If that raises `NotImplementedError` (NetworkX backend), it falls back to `backend.get_vertex_counts()`. If either succeeds, database check is "ok". If both fail, it returns 503.

5. **Response**: Returns `{"status": "ready", "checks": {"database": "ok"}}` with status 200, or `{"status": "not_ready", ...}` with status 503.

### Risk to Watch

**The lifespan context manager has no shutdown cleanup.** Look at `app/api/router.py`: the `lifespan()` function creates the backend on startup (`yield` marks the boundary), but does nothing after `yield`. For the NetworkX backend this is harmless — it is just an in-memory graph. But when `GRAPH_BACKEND=hana`, the `ConnectionPool` holds open database connections. On graceful shutdown (SIGTERM in Cloud Foundry), those connections are never explicitly closed. Consider where `pool.close()` or equivalent teardown would go (answer: after the `yield` in `lifespan()`).

---

## Suggested Reading Order

If you're reading the whole project from scratch:

1. **Subplan 01** first — understand how the app boots
2. **Subplan 02** next — understand the data abstraction
3. **Subplan 03** — see how HANA queries actually work
4. **Subplan 04** last — see how it all wires together with DI and endpoints

Also read these supporting docs:
- `LEARNINGS.md` — What went wrong in V1 and why this is a rebuild
- `docs/PROGRESS.md` — What's been built and what's next
- `docs/DATA_MODEL.md` — The 29-table procurement schema
- `docs/GRAPHRAG_QUERY_PATTERNS.md` — All 22 query patterns the system will support
