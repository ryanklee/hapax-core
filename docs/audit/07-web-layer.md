# Domain 7: Web Layer — Audit Findings

**Audited**: 2026-03-02
**Scope**: ~722 LOC source, ~150 LOC tests across 2 repos
**Files**: `cockpit/api/` in `<ai-agents>/`, `src/` in `<cockpit-web>/`

---

## Inventory

### Backend — FastAPI (`<ai-agents>/cockpit/api/`)
| File | LOC | Purpose |
|------|-----|---------|
| `app.py` | 48 | FastAPI app, CORS middleware, lifespan hook |
| `cache.py` | 124 | Background DataCache with 30s/5min refresh loops |
| `routes/data.py` | 105 | 15 data endpoints under `/api/` |
| `__main__.py` | 41 | Uvicorn entry point with CLI args |
| `__init__.py` | 1 | Package marker |
| `routes/__init__.py` | 1 | Package marker |

### Frontend — React SPA (`<cockpit-web>/src/`)
| File | LOC | Purpose |
|------|-----|---------|
| `api/types.ts` | 142 | TypeScript interfaces for API responses |
| `api/hooks.ts` | 35 | TanStack Query hooks with polling intervals |
| `api/client.ts` | 20 | Fetch helper with `/api` base path |
| `components/Sidebar.tsx` | 109 | Health, VRAM, readiness, goals, timers panels |
| `components/MainPanel.tsx` | 76 | Nudge list, agent grid |
| `components/Header.tsx` | 29 | Status bar with health indicator |
| `App.tsx` | 15 | Layout shell |
| `main.tsx` | 19 | React root with QueryClient |

### Build/Deploy
| File | LOC | Purpose |
|------|-----|---------|
| `Dockerfile.api` | 20 | Python 3.12-slim + uv, exposes 8050 |
| `vite.config.ts` | 12 | Vite dev server with proxy to :8050 |

### Tests (`<ai-agents>/tests/`)
| File | LOC | Purpose |
|------|-----|---------|
| `test_api.py` | 104 | Endpoint tests (root, CORS, health, GPU, infra) |
| `test_api_cache.py` | 46 | Cache unit tests (initial state, refresh) |

---

## Finding Summary

| # | Severity | Category | Finding |
|---|----------|----------|---------|
| 7.01 | HIGH | correctness | `refresh_slow()` cascading failure — one exception skips all remaining collectors |
| 7.02 | HIGH | correctness | `ManagementSnapshot` contains `Path` objects — `dataclasses.asdict()` produces non-JSON-serializable output |
| 7.03 | HIGH | performance | Synchronous blocking I/O in `refresh_slow()` stalls asyncio event loop |
| 7.04 | MEDIUM | completeness | 4 TS interfaces missing — drift, management, accommodations, health-history have no typed frontend consumers |
| 7.05 | MEDIUM | completeness | 4 API client methods missing — drift, management, accommodations, health/history not in `client.ts` |
| 7.06 | MEDIUM | type-safety | `ReadinessSnapshot` TS interface missing 3 fields present in Python dataclass |
| 7.07 | MEDIUM | deployment | Dockerfile serves API only — no mechanism to serve built SPA in production |
| 7.08 | MEDIUM | deployment | `profiles/` baked into Docker image at build time — runtime data will be stale without volume mount |
| 7.09 | LOW | robustness | Background tasks created without stored references — could theoretically be GC'd |
| 7.10 | LOW | robustness | No HTTP error status codes — all failures return 200 with null/empty |
| 7.11 | LOW | robustness | `/api/health/history` bypasses cache — synchronous file read on every request |
| 7.12 | LOW | hardening | CORS `allow_methods=["*"]` and `allow_headers=["*"]` overly permissive for read-only API |
| 7.13 | LOW | deployment | Dockerfile missing HEALTHCHECK directive |
| 7.14 | LOW | deployment | Docker container needs vault path + Langfuse credentials at runtime — not documented |
| 7.15 | LOW | testing | Only 5 of 15 endpoints have test coverage |

**Totals**: 3 HIGH, 5 MEDIUM, 7 LOW

---

## Detailed Findings

### 7.01 — HIGH: `refresh_slow()` cascading failure

**File**: `cockpit/api/cache.py:76-86`

```python
try:
    self.briefing = collect_briefing()
    self.scout = collect_scout()
    self.drift = collect_drift()
    self.cost = collect_cost()          # <-- if this raises...
    self.goals = collect_goals()        # <-- these are all skipped
    self.readiness = collect_readiness()
    self.management = collect_management_state()
    self.agents = get_agent_registry()
except Exception as e:
    log.warning("Slow refresh error: %s", e)
```

Eight sequential collector calls share a single try/except. If `collect_cost()` raises (e.g., Langfuse unreachable), then goals, readiness, management, and agents are never refreshed for that cycle. The cache retains stale values from the last successful refresh, but on initial startup all skipped fields remain `None`.

**Contrast**: `refresh_fast()` uses `asyncio.gather(return_exceptions=True)` and individually checks each result — much more robust.

The nudges and accommodations sections (lines 88-97) already have independent try/except blocks, showing the intent but inconsistent execution.

**Fix**: Wrap each collector call individually, matching the pattern used for nudges:
```python
for name, fn in [("briefing", collect_briefing), ("scout", collect_scout), ...]:
    try:
        setattr(self, name, fn())
    except Exception as e:
        log.warning("Slow refresh %s failed: %s", name, e)
```

---

### 7.02 — HIGH: `Path` objects in `ManagementSnapshot` break JSON serialization

**Files**: `cockpit/data/management.py`, `cockpit/api/routes/data.py:18-26`

The `_to_dict()` function uses `dataclasses.asdict()` which recursively converts nested dataclasses. However, `PersonState.file_path`, `CoachingState.file_path`, and `FeedbackState.file_path` are all `Path | None`. `dataclasses.asdict()` copies these as-is (Path is not a dataclass), and `Path` objects are not JSON-serializable.

When `/api/management` is called and the vault has people/coaching/feedback notes, FastAPI's JSON encoder will raise `TypeError: Object of type PosixPath is not JSON serializable`.

**Impact**: The `/api/management` endpoint will return 500 errors whenever real vault data exists.

**Fix**: Either:
1. Add a custom JSON encoder to FastAPI that handles Path objects
2. Exclude `file_path` from the serialized output (it's an internal implementation detail)
3. Override `_to_dict()` to convert Path to str

Option 2 is cleanest — `file_path` is used only by vault navigation in the TUI.

---

### 7.03 — HIGH: Synchronous blocking I/O in `refresh_slow()` stalls event loop

**File**: `cockpit/api/cache.py:64-97`

`refresh_slow()` is an `async` method but calls only synchronous functions:
- `collect_briefing()` — file I/O (small, fast)
- `collect_scout()` — file I/O (small, fast)
- `collect_drift()` — file I/O (small, fast)
- `collect_cost()` — **HTTP requests via `urllib.request.urlopen()` with 15s timeout**, pagination loop can make multiple requests
- `collect_goals()` — file I/O
- `collect_readiness()` — file I/O + imports profile analysis
- `collect_management_state()` — **filesystem walk via `rglob("*.md")`**, parses YAML frontmatter for every note in vault
- `collect_nudges()` — calls multiple collectors internally, including the above

During `collect_cost()`, the event loop is blocked for up to 15 seconds per HTTP request (potentially multiple pages). During this time, no API requests can be served.

`collect_management_state()` walks the entire Obsidian vault tree with `rglob()` and parses YAML from every matching file. For a vault with hundreds of files, this could take seconds.

**Fix**: Run blocking collectors in a thread pool:
```python
self.cost = await asyncio.to_thread(collect_cost)
self.management = await asyncio.to_thread(collect_management_state)
```

Or wrap the entire slow refresh in a thread:
```python
async def refresh_slow(self):
    await asyncio.to_thread(self._refresh_slow_sync)
```

---

### 7.04 — MEDIUM: Missing TypeScript interfaces for 4 endpoint responses

**File**: `cockpit-web/src/api/types.ts`

The following Python dataclasses have endpoints but no corresponding TS interfaces:

| Endpoint | Python type | TS type |
|----------|-------------|---------|
| `/api/drift` | `DriftSummary` | missing |
| `/api/management` | `ManagementSnapshot` (+ PersonState, CoachingState, FeedbackState) | missing |
| `/api/accommodations` | `AccommodationSet` (+ Accommodation) | missing |
| `/api/health/history` | `HealthHistory` (+ HealthHistoryEntry) | missing |

These endpoints exist and return data, but no frontend component consumes them yet. The TS types should be defined proactively so future UI work has a typed contract.

---

### 7.05 — MEDIUM: Missing API client methods for 4 endpoints

**File**: `cockpit-web/src/api/client.ts`

The client object exposes 10 methods but the backend has 15 endpoints. Missing:
- `drift` — `/api/drift`
- `management` — `/api/management`
- `accommodations` — `/api/accommodations`
- `healthHistory` — `/api/health/history`

No corresponding TanStack Query hooks in `hooks.ts` either. These endpoints are defined and working on the backend but invisible to the frontend.

---

### 7.06 — MEDIUM: `ReadinessSnapshot` TS interface incomplete

**Files**: `cockpit-web/src/api/types.ts:88-99`, `cockpit/data/readiness.py:22-37`

Python `ReadinessSnapshot` has 13 fields. The TS interface has 10. Missing:

| Python field | Type | TS |
|-------------|------|-----|
| `interview_fact_count` | `int` | missing |
| `priorities_known` | `bool` | missing |
| `neurocognitive_mapped` | `bool` | missing |

The frontend currently only uses `level`, `populated_dimensions`, `total_dimensions`, `total_facts`, and `top_gap`, so no runtime errors. But the TS type is misleading — it claims to be the complete shape when it is not. The extra fields are silently present in the JSON response.

---

### 7.07 — MEDIUM: No production SPA serving mechanism

**Files**: `Dockerfile.api`, `cockpit/api/app.py`

The Dockerfile runs only the FastAPI API server. For production deployment:
- The React SPA must be built (`pnpm build`) and served somewhere
- CORS allows `http://localhost:8050` as an origin, implying the SPA would be served on the same port
- But the API has no static file serving configured

Options needed:
1. Add `StaticFiles` mount to FastAPI to serve the built SPA
2. Use a reverse proxy (nginx/caddy) in front
3. Embed the built SPA in the Docker image

None of these are configured. The current setup only works in development with `vite dev` proxying to the API.

---

### 7.08 — MEDIUM: Build-time `profiles/` in Docker image

**File**: `Dockerfile.api:14`

```dockerfile
COPY profiles/ profiles/
```

The `profiles/` directory contains runtime-mutable data: `briefing.md`, `health-history.jsonl`, `scout-report.json`, `drift-report.json`, `operator.json`, `accommodations.json`, etc. These are written by agents and timers.

Copying at build time bakes in stale data. The container needs a volume mount at runtime:
```yaml
volumes:
  - ./profiles:/app/profiles
```

Without this, the dashboard shows stale data that never updates (agents write to host filesystem, not the container).

---

### 7.09 — LOW: Background task references not stored

**File**: `cockpit/api/cache.py:123-124`

```python
asyncio.create_task(_fast_loop())
asyncio.create_task(_slow_loop())
```

The returned task objects are discarded. Per Python docs: "Important: Save a reference to the result of this function, to avoid a task disappearing mid-execution." In practice, CPython's event loop holds strong references, but this is an implementation detail, not a guarantee.

**Fix**: Store references on the cache object or module level.

---

### 7.10 — LOW: No HTTP error status codes

**File**: `cockpit/api/routes/data.py`

Every endpoint returns 200 regardless of state:
- Cache empty (initial load failed) → 200 with `null`
- Collector permanently broken → 200 with `null`
- Partial data → 200 with whatever is cached

The frontend `get<T>()` throws on non-200 responses, but the API never produces them. The client cannot distinguish "loading" from "permanently unavailable."

**Mitigation**: Add an envelope or headers indicating data freshness (e.g., `X-Cache-Age` header, or a `_meta` field with `last_refreshed` timestamp).

---

### 7.11 — LOW: `/api/health/history` bypasses cache

**File**: `cockpit/api/routes/data.py:37-40`

```python
@router.get("/health/history")
async def get_health_history():
    from cockpit.data.health import collect_health_history
    history = collect_health_history()
    return _to_dict(history)
```

Unlike all other endpoints, this reads directly from disk on every request. `collect_health_history()` reads the entire `health-history.jsonl` file (potentially thousands of lines), parses JSON for each, and builds HealthHistoryEntry objects — synchronously, blocking the event loop.

Should either be cached or run via `asyncio.to_thread()`.

---

### 7.12 — LOW: Overly permissive CORS

**File**: `cockpit/api/app.py:29-40`

```python
allow_methods=["*"],
allow_headers=["*"],
```

This is a read-only API with only GET endpoints. Allowing all methods and headers is unnecessary. For a localhost-only service the risk is minimal, but defense-in-depth says restrict to `allow_methods=["GET", "OPTIONS"]`.

---

### 7.13 — LOW: Dockerfile missing HEALTHCHECK

**File**: `Dockerfile.api`

No `HEALTHCHECK` directive. Docker (and compose) can't determine container health. The root endpoint (`GET /`) returns a version payload and would serve as a trivial health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/')"
```

---

### 7.14 — LOW: Runtime dependencies not documented for Docker

**File**: `Dockerfile.api`

The container needs several runtime dependencies not captured in the Dockerfile or any compose file:
- **Volume mount**: `profiles/` for mutable data
- **Volume mount**: Obsidian vault path for management collector (or accept empty management data)
- **Environment variables**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` for cost collector
- **Network access**: localhost services (Ollama, health checks) won't work inside a container without `host` network mode or service discovery

These constraints should be documented in a compose service definition or a README section.

---

### 7.15 — LOW: Sparse test coverage

**Files**: `tests/test_api.py`, `tests/test_api_cache.py`

150 LOC of tests covering:
- Root endpoint (1 test)
- CORS headers (1 test)
- `/api/health` with mock data (2 tests)
- `/api/gpu` with mock data (1 test)
- `/api/infrastructure` with mock data (1 test)
- Cache initial state (1 test)
- Cache refresh_fast (1 test)
- Cache refresh_slow (1 test)

Missing test coverage:
- 10 of 15 endpoints untested: briefing, scout, drift, cost, goals, readiness, management, nudges, agents, accommodations
- No test for `_to_dict()` with nested dataclasses (would catch 7.02)
- No test for error scenarios (collector failure during refresh)
- No integration test for the lifespan startup sequence
- No test for the health/history direct-read endpoint

---

## Architectural Observations

### What works well

1. **Clean separation**: Backend is a pure data proxy over the existing collector layer. No business logic duplication.
2. **Cadence alignment**: Frontend polling intervals exactly match backend cache intervals — no unnecessary traffic.
3. **Graceful degradation design**: Cache fields default to None/empty, frontend handles missing data with fallback UI.
4. **CORS origin list**: Explicit origins, no wildcards, covers both dev and planned production ports.
5. **Vite proxy**: Clean dev-time proxy avoids CORS issues during development.
6. **Static agent registry**: `staleTime: Infinity` correctly avoids polling for data that never changes.
7. **Shared collector layer**: API reuses the exact same data collectors as the TUI — no parallel implementation.

### Key concerns

1. **Event loop blocking is the most operationally impactful issue**. During a slow refresh cycle, the API cannot serve any requests. With `collect_cost()` potentially blocking 15s per HTTP call (and paginating), plus `collect_management_state()` walking the filesystem, the event loop could be blocked for 20+ seconds every 5 minutes. This makes the dashboard appear unresponsive.

2. **The cascading failure in `refresh_slow()` means a single broken collector can leave the entire dashboard showing stale data**. Combined with no HTTP error codes (7.10), the frontend has no way to indicate this to the user.

3. **The Path serialization bug (7.02) is a latent crash** — it only manifests when real vault data exists. The test suite uses mock data without Path fields, so this wouldn't be caught.

4. **Frontend coverage is ~67% of available endpoints**. The backend supports 15 endpoints but the frontend only consumes 10. The missing endpoints (drift, management, accommodations, health/history) represent significant data that the web dashboard doesn't yet surface.

### Recommended priority

1. Fix `refresh_slow()` to wrap each collector independently (7.01) — prevents cascading failures
2. Run blocking collectors via `asyncio.to_thread()` (7.03) — prevents event loop stalls
3. Handle `Path` objects in `_to_dict()` (7.02) — prevents 500 errors on /api/management
4. Add TS interfaces and client methods for remaining endpoints (7.04, 7.05) — completes the API contract
5. Production serving strategy (7.07) — needed before any real deployment
