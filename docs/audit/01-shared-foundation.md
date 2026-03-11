# Domain 1: Shared Foundation -- Audit Findings

## Inventory

| File | LOC | Test File | Test LOC |
|------|-----|-----------|----------|
| `shared/config.py` | 116 | `tests/test_config.py` | 64 |
| `shared/operator.py` | 178 | `tests/test_operator.py` | 169 |
| `shared/notify.py` | 173 | `tests/test_notify.py` | 224 |
| `shared/vault_writer.py` | 284 | `tests/test_vault_writer.py` | 200 |
| `shared/vault_utils.py` | 35 | (none -- tested indirectly via `test_management_bridge.py`, `test_management.py`) | 0 |
| `shared/langfuse_client.py` | 58 | (none) | 0 |
| `shared/langfuse_config.py` | 25 | (none) | 0 |
| `shared/email_utils.py` | 108 | (none -- tested indirectly via `tests/test_proton.py`) | 0 |

**Total:** 977 source LOC, 657 test LOC, test:source ratio 0.67

---

## Completeness Findings

> Missing, dead, or assumed-but-absent.

### C-1.1: No direct test file for `langfuse_client.py`
**File:** `shared/langfuse_client.py` (all 58 lines)
**Severity:** medium
**Finding:** `langfuse_client.py` has no dedicated test file. It is imported by 4 production modules (`agents/scout.py`, `agents/activity_analyzer.py`, `agents/profiler_sources.py`, `cockpit/data/cost.py`) but never tested in isolation. The `langfuse_get()` function performs authenticated HTTP calls with base64-encoded Basic auth, URL encoding, and JSON parsing -- all untested paths. `is_available()` is also untested.
**Impact:** Auth encoding bugs, URL encoding regressions, or error-handling changes would go undetected until production use. The empty-dict-on-failure contract is documented but not verified.

### C-1.2: No direct test file for `langfuse_config.py`
**File:** `shared/langfuse_config.py` (all 25 lines)
**Severity:** low
**Finding:** `langfuse_config.py` is a side-effect-only module (sets `os.environ` on import). It has no tests. It is imported by 10+ agent modules via `from shared import langfuse_config  # noqa: F401`. The `setdefault` logic that conditionally sets OTEL env vars only when keys are present is not validated.
**Impact:** Low risk -- the module is simple and the `setdefault` pattern is standard. However, the conditional guard (`if PUBLIC_KEY and SECRET_KEY`) means silent no-op when credentials are missing, which could mask configuration failures.

### C-1.3: No direct test file for `email_utils.py`
**File:** `shared/email_utils.py` (all 108 lines)
**Severity:** low
**Finding:** `email_utils.py` has no dedicated test file. However, it is well-tested indirectly: `tests/test_proton.py` has a `TestEmailUtils` class (lines 160-195) with 12 tests covering `is_automated`, `extract_email_addr`, `decode_header`, `parse_email_date`, and `extract_body`.
**Impact:** Minimal. The indirect coverage is solid. The only risk is that test discovery is non-obvious -- a maintainer might not realize these functions are tested.

### C-1.4: No direct test file for `vault_utils.py`
**File:** `shared/vault_utils.py` (all 35 lines)
**Severity:** low
**Finding:** `vault_utils.py` has no dedicated test file. It is used by `shared/management_bridge.py` and `cockpit/data/management.py`, and tested indirectly via `tests/test_management_bridge.py` and `tests/test_management.py`. The `parse_frontmatter()` function handles edge cases defensively (missing file, no markers, invalid YAML, non-dict YAML), but these edge cases are only partially exercised.
**Impact:** Minimal. The function is small and defensive. Edge cases like non-dict YAML results or `UnicodeDecodeError` are handled but not directly asserted.

### C-1.5: `write_digest_to_vault` is untested
**File:** `shared/vault_writer.py:104-124`
**Severity:** low
**Finding:** `write_digest_to_vault()` is defined and used by `agents/digest.py`, but has no test coverage in `tests/test_vault_writer.py`. The test file imports 8 of 9 `write_*` functions but omits `write_digest_to_vault`. It is structurally identical to `write_briefing_to_vault`, so the risk is low, but it is a coverage gap.
**Impact:** Any digest-specific regression (e.g., filename format change to `{date}-digest.md`) would not be caught by unit tests.

### C-1.6: `embed_batch` has no direct tests
**File:** `shared/config.py:88-116`
**Severity:** medium
**Finding:** `embed_batch()` is tested only indirectly via `tests/test_profile_store.py` where it is mocked out. No test verifies: (a) that the empty-list early return works, (b) that the prefix is applied to each text, (c) that the Ollama error wrapping works for batch calls, (d) that the return structure (`result["embeddings"]`) is correctly accessed. The single `embed()` function has an error-handling test, but `embed_batch()` does not.
**Impact:** A batch embedding regression (e.g., Ollama API change to `result["data"]` instead of `result["embeddings"]`) would not be caught. The empty-list guard is an important optimization that is unverified.

---

## Correctness Findings

> Wrong, fragile, or accidental.

### R-1.1: `operator.json` loaded without schema validation
**File:** `shared/operator.py:38-50`
**Severity:** medium
**Finding:** `_load_operator()` does `json.loads(path.read_text())` with no validation. The returned dict is accessed throughout via `.get()` calls, which provides graceful degradation for missing keys. However, there is no check that `version == 1`, no check that required top-level keys (`operator`, `axioms`, `constraints`, `patterns`) exist, and no Pydantic model despite the project convention requiring Pydantic for structured data. A corrupt or misformatted `operator.json` would silently produce empty results from all accessor functions.
**Impact:** Medium. The `.get()` fallbacks prevent crashes, but corrupt data silently degrades all agent context. A schema validation error at load time would surface problems immediately. Note: the project convention explicitly requires Pydantic models for structured data (`shared/config.py` conventions).

### R-1.2: `_operator_cache` is a mutable global with no invalidation API
**File:** `shared/operator.py:21,38-50`
**Severity:** low
**Finding:** `_operator_cache` is set once on first load and never invalidated. There is no `reload_operator()` or cache-clearing function. Tests that need to manipulate the cache must directly set `shared.operator._operator_cache = None` (seen in `tests/test_goals.py:24,26`) or monkeypatch it (seen in `tests/test_operator.py:147`). In production, if `operator.json` is updated while an agent process is running, the cache will serve stale data.
**Impact:** Low for the current architecture (agents are stateless per-invocation, so the cache only lives for one CLI run). Higher risk for the cockpit (long-running TUI process) where operator.json changes during a session would not be reflected.

### R-1.3: `get_qdrant()` creates a new client on every call
**File:** `shared/config.py:58-60`
**Severity:** low
**Finding:** `get_qdrant()` returns `QdrantClient(QDRANT_URL)` on every call. There is no singleton, no connection pooling, and no reuse. Callers that need a client in a loop or hot path will create many TCP connections. The Qdrant Python client does manage its own internal HTTP session, so each `QdrantClient` instance maintains one connection, but having many instances defeats that purpose.
**Impact:** Low. Most callers use it once at agent startup. However, `shared/profile_store.py:40` calls `get_qdrant()` inside `__init__`, and if `ProfileStore` is instantiated frequently (e.g., per-request), this creates unnecessary connections.

### R-1.4: `VAULT_PATH` module-level constants are not patchable in isolation
**File:** `shared/vault_writer.py:28-32`
**Severity:** low
**Finding:** `VAULT_PATH`, `SYSTEM_DIR`, `BRIEFINGS_DIR`, `DIGESTS_DIR`, and `INBOX_DIR` are computed at module load time. Tests must patch all five constants independently (see `tests/test_vault_writer.py:30-33` patching 4 of 5). `DIGESTS_DIR` is not patched in the test fixture, meaning `_ensure_dirs()` at line 37 would attempt to create real filesystem directories under the original `SYSTEM_DIR / "digests"` path. This does not cause test failures because `write_to_vault` independently creates its target directory, but `_ensure_dirs()` has an unpatched side effect.
**Impact:** Low. The test fixture patches `VAULT_PATH`, `SYSTEM_DIR`, `BRIEFINGS_DIR`, and `INBOX_DIR` but misses `DIGESTS_DIR`. In practice this means `_ensure_dirs()` tries to `mkdir` the real `<personal-vault>/30-system/digests/` during tests. If the real path doesn't exist and the parent is unwritable, `_ensure_dirs` could fail, though `write_to_vault` would still succeed because it calls `target_dir.mkdir(parents=True, exist_ok=True)` independently.

---

## Robustness Findings

> Failure modes, silent errors, missing recovery.

### B-1.1: `embed()` and `embed_batch()` have no timeout control
**File:** `shared/config.py:66-116`
**Severity:** medium
**Finding:** Both `embed()` and `embed_batch()` call `ollama.embed()` without specifying a timeout. The `ollama` Python library defaults to waiting indefinitely (or until the OS TCP timeout). If Ollama is accepting connections but slow to respond (e.g., loading a model into VRAM), embedding calls block the calling agent indefinitely. The exception handler wraps *all* exceptions into `RuntimeError`, which is correct, but the lack of timeout means the exception may never fire.
**Impact:** A stalled Ollama service blocks any agent that calls `embed()` or `embed_batch()`. This includes the profiler (`--index-profile`), RAG ingest pipeline, and profile store indexing. The health monitor might detect Ollama issues, but the blocked agent process has no self-recovery.

### B-1.2: `langfuse_get()` silently returns empty dict on all failures
**File:** `shared/langfuse_client.py:23-50`
**Severity:** medium
**Finding:** `langfuse_get()` catches `(URLError, json.JSONDecodeError, OSError)` and returns `{}`. It also returns `{}` when credentials are missing (line 34-35). This means: auth failures (HTTP 401/403), server errors (HTTP 500), timeouts, network errors, and missing credentials all produce the same empty-dict result. Callers have no way to distinguish "Langfuse returned no data" from "Langfuse is completely unreachable" from "credentials are wrong".
**Impact:** Medium. The activity analyzer and profiler sources silently produce incomplete data when Langfuse is misconfigured or down. The `is_available()` function at line 53 partially mitigates this (returns False when keys are missing), but callers of `langfuse_get()` directly cannot distinguish failure modes.

### B-1.3: `_send_ntfy` catches narrow exception set, `send_notification` catches broad
**File:** `shared/notify.py:76-80,148-156`
**Severity:** low
**Finding:** `_send_ntfy()` catches `(URLError, OSError)` at line 154 and returns `False`. But `send_notification()` wraps `_send_ntfy()` in a broader `except Exception` at line 79. This means: (a) network errors are caught inside `_send_ntfy` and return `False` (clean), (b) unexpected errors (e.g., `ValueError` from malformed URL) are caught at the outer layer and logged at `debug` level (line 80). The dual-layer exception handling works correctly but the outer `Exception` catch at debug level could mask real bugs.
**Impact:** Low. The architecture is correct -- notifications should never crash the caller. The debug-level logging for the outer catch means truly unexpected errors would require debug logging to be enabled to diagnose.

### B-1.4: `vault_writer.write_to_vault()` returns `None` on failure with only a warning log
**File:** `shared/vault_writer.py:58-78`
**Severity:** low
**Finding:** `write_to_vault()` catches `(PermissionError, OSError)` and returns `None`. All higher-level `write_*_to_vault` functions propagate this `None` return. Callers are expected to check the return value, but none of the callers in the codebase check it -- e.g., `agents/briefing.py` calls `write_briefing_to_vault()` and `agents/digest.py` calls `write_digest_to_vault()` without checking the return.
**Impact:** Low. A failed vault write is logged at `warning` level but callers proceed as if the write succeeded. The agent's primary output (to stdout or profiles/) is unaffected, so this is really about the secondary egress to Obsidian failing silently.

### B-1.5: No concurrent write protection in `vault_writer`
**File:** `shared/vault_writer.py:41-78`
**Severity:** low
**Finding:** `write_to_vault()` uses `Path.write_text()` which is not atomic. If two agents write to the same file simultaneously (e.g., `nudges.md` written by cockpit while briefing agent also triggers a nudge refresh), the file could be partially written. There is no file locking, no atomic write-then-rename pattern.
**Impact:** Low. In practice, the risk is minimal: agents are typically invoked sequentially, and the files being overwritten (`nudges.md`, `goals.md`, `management-overview.md`) are snapshots where a partial write would be overwritten on the next run. However, the briefing-to-vault path runs on a timer, and if two timers fire close together (e.g., digest at 06:45 and briefing at 07:00 both writing to vault), there is a theoretical window.

### B-1.6: `langfuse_config.py` sets env vars at import time with no rollback
**File:** `shared/langfuse_config.py:15-25`
**Severity:** low
**Finding:** When imported, `langfuse_config.py` calls `os.environ.setdefault()` three times to set OTEL exporter configuration. These are process-global side effects that persist for the lifetime of the process. If a test imports this module, the OTEL env vars are set for all subsequent tests in the same process. There is no `teardown` or `atexit` handler.
**Impact:** Low. In production, this is the intended behavior (one-time OTel configuration). In tests, it could cause unexpected OTEL exporter initialization, but since the target endpoint is `localhost:3000` (which likely isn't running in CI), the exporter would silently fail. No test file imports `langfuse_config` directly.

### B-1.7: `embed()` does not validate embedding dimension
**File:** `shared/config.py:85`
**Severity:** low
**Finding:** `embed()` returns `result["embeddings"][0]` without checking that the result has the expected 768 dimensions. If the embedding model changes or returns a different dimension, the mismatch with Qdrant collections (configured for 768d) would cause insertion errors downstream rather than a clear error at the embedding step.
**Impact:** Low. The embedding model is hardcoded to `nomic-embed-text-v2-moe` which always returns 768d. The risk only materializes if someone passes a different `model` argument.

---

## Test Coverage Assessment

| Area | Status | Notes |
|------|--------|-------|
| `shared/config.py` | **partially tested** | 5 alias checks, env defaults, `get_model` with alias and passthrough, `get_qdrant` type check, `embed` error handling. Missing: `embed_batch` (empty input, prefix application, error wrapping), `embed` happy path (prefix application, return shape). |
| `shared/operator.py` | **well tested** | 19 tests cover: load, constraints (all + by category + music), patterns (all + by category), goals, agent context (existing + missing), axioms, system prompt fragment (single user axiom, executive function axiom, no constraints injected, unknown agent, neurocognitive empty/populated). Missing: JSON parse error on corrupt `operator.json`, missing `operator.json` (empty dict path). |
| `shared/notify.py` | **well tested** | 22 tests across 5 test classes. ntfy (success, custom topic, priority, tags, click_url, unreachable), desktop (success, priority, missing binary, nonzero exit), unified (both succeed, ntfy fail, desktop fail, both fail, priority passthrough, topic override), webhook (success, failure). Thorough mock coverage. No gaps identified. |
| `shared/vault_writer.py` | **well tested** | 17 tests across 8 test classes. Covers: basic write, directory creation, frontmatter, overwrite, dated briefing, empty/populated nudges, nudge sort order, goals (basic + empty), 1:1 prep (content + directory), team snapshot, management overview (write + overwrite), bridge prompt (content + directory). Missing: `write_digest_to_vault`, error path (PermissionError return None). Fixture omits `DIGESTS_DIR` patch. |
| `shared/vault_utils.py` | **indirectly tested** | `parse_frontmatter` tested via `test_management_bridge.py` and `test_management.py`. Not tested directly. |
| `shared/langfuse_client.py` | **untested** | No test file. `langfuse_get()` and `is_available()` have zero test coverage. Used by 4 production modules. |
| `shared/langfuse_config.py` | **untested** | No test file. Side-effect-only module. Acceptable for its simplicity but the conditional `setdefault` logic is unverified. |
| `shared/email_utils.py` | **indirectly tested** | 12 tests in `tests/test_proton.py::TestEmailUtils`. Good coverage of all 5 public functions. |

---

## Summary

- **Completeness:** 6 findings (0 critical, 0 high, 2 medium, 4 low)
  - `langfuse_client.py` untested (medium), `embed_batch` untested (medium), `write_digest_to_vault` untested (low), plus 3 low-severity indirect-only test coverage gaps.

- **Correctness:** 4 findings (0 critical, 0 high, 1 medium, 3 low)
  - `operator.json` has no schema validation (medium), mutable global cache without invalidation (low), new QdrantClient per call (low), unpatchable module-level vault constants (low).

- **Robustness:** 7 findings (0 critical, 0 high, 2 medium, 5 low)
  - Embedding calls have no timeout (medium), Langfuse client conflates all failure modes (medium), plus 5 low-severity findings around silent failures, missing concurrent write protection, and env var side effects.

**Overall assessment:** The shared foundation is solid for a single-operator system. Code is clean, well-structured, and defensively written. The `.get()` pattern throughout `operator.py` and the try/except-return-None pattern in `vault_writer.py` prevent crashes from missing data. Notification dispatch has proper dual-channel fallback with correct exception isolation.

The highest-priority gaps are: (1) `langfuse_client.py` being completely untested despite being a key telemetry path, (2) `embed_batch()` having no direct tests for an API-dependent function, and (3) embedding calls having no timeout against a local service that may stall during model loading. None of these are correctness bugs today -- they are resilience and coverage gaps that would matter during infrastructure changes.
