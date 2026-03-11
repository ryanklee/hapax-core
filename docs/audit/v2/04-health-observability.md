# Domain 4: Health & Observability — Audit v2 Findings

**Audited:** 2026-03-03
**Auditor:** Claude Code (v2 full re-read)
**Prior findings (v1):** 19 (6 completeness, 5 correctness, 8 robustness)
**Fixes to verify:** 5, 8, 16, 30, 31, 63

---

## Inventory

| File | v1 LOC | v2 LOC | Delta | Test File(s) | Test LOC |
|------|--------|--------|-------|-------------|----------|
| `agents/health_monitor.py` | 1,439 | 1,458 | +19 | `tests/test_health_monitor.py` | 727 |
| | | | | `tests/test_connectivity_checks.py` (new) | 182 |
| `agents/introspect.py` | 486 | 486 | 0 | `tests/test_introspect.py` | 679 |
| `agents/drift_detector.py` | 352 | 369 | +17 | `tests/test_drift_detector.py` | 453 |
| `agents/activity_analyzer.py` | 666 | 678 | +12 | `tests/test_activity_analyzer.py` | 371 |
| `agents/knowledge_maint.py` | 535 | 540 | +5 | `tests/test_knowledge_maint.py` | 448 |

**Total source:** 3,531 LOC (was 3,478, +53)
**Total test:** 2,860 LOC (was 2,593, +267)
**Test:source ratio:** 0.81 (was 0.75)

---

## Fix Verification

### Fix 5: Health monitor should test actual Langfuse credentials — VERIFIED
**v1 finding:** C-4.1 (medium)
**Status:** ✅ Complete and correct.
`check_langfuse_auth()` in the `auth` check group constructs a Basic auth header (`base64(pk:sk)`) and makes an actual HTTP request to `http://localhost:3000/api/public/health` with a 5-second timeout. Returns HEALTHY on HTTP 200, DEGRADED on failure (appropriate since Langfuse is observability infrastructure, not blocking).
**Quality note:** Correctly uses DEGRADED (not FAILED) for Langfuse auth issues, consistent with the severity model where only core services (Docker, Qdrant, Ollama, LiteLLM) fail.

### Fix 8: Health monitor should validate LiteLLM model list — VERIFIED
**v1 finding:** C-4.2 (medium)
**Status:** ✅ Complete and correct.
`check_litellm_auth()` reads `LITELLM_API_KEY` from env, rejects "changeme" as invalid, makes an actual request to `http://localhost:4000/v1/models` with Bearer auth, parses the JSON response and reports model count. Returns FAILED on auth failure.
**Quality note:** The endpoint check in the `endpoints` group still tests basic liveness (`/health/liveliness`). The `auth` group check validates actual model-list access. The two are complementary — liveness vs authentication.

### Fix 16: Health check groups should be auto-discoverable — VERIFIED
**v1 finding:** R-4.1 (medium)
**Status:** ✅ Complete and correct.
`CHECK_REGISTRY: dict[str, list[Callable]]` at line 94. `@check_group("name")` decorator auto-registers functions. The runner uses `list(CHECK_REGISTRY.keys())` dynamically. Adding a new group only requires a new decorated function — nothing else needs updating.
**Stale artifact:** The `--check` argparse help string (line 1405) lists 8 groups but the registry now has 11 (missing: `models`, `auth`, `connectivity`). Runtime validation correctly uses `CHECK_REGISTRY.keys()`.

### Fix 30: Activity analyzer Langfuse timestamp handling — VERIFIED
**v1 finding:** R-4.2 (medium)
**Status:** ✅ Complete and correct.
Centralized in `shared/langfuse_client.py` using `urllib.parse.urlencode(params)` which correctly percent-encodes the `+` in `+00:00` timezone offsets as `%2B`. Both `activity_analyzer.py` and `profiler_sources.py` pass ISO timestamps via `since.isoformat()` through this client.

### Fix 31: Activity analyzer should handle missing/partial data sources — VERIFIED
**v1 finding:** B-4.1 (medium)
**Status:** ✅ Complete and thorough.
Multiple layers of protection:
- `DataSourceStatus` model explicitly tracks availability of each data source
- `collect_langfuse()`: checks `if not LANGFUSE_PK` → returns empty `LangfuseActivity`
- `collect_health_trend()`: checks `if not HEALTH_HISTORY.is_file()` → returns zero-valued trend
- `collect_drift_trend()`, `collect_digest_trend()`, `collect_knowledge_maint_trend()`: all guard with `if file.is_file()` and catch `(json.JSONDecodeError, OSError)`
- `collect_service_events()`: checks `if rc != 0 or not out` → returns `[]`
- All collectors return typed empty objects (never None, never exceptions)
- `format_human()` shows "No X in window" for empty data

### Fix 63: Knowledge maint near-duplicate threshold + dry-run default — VERIFIED
**v1 finding:** B-4.3 (medium)
**Status:** ✅ Complete and correct.
`DEFAULT_SCORE_THRESHOLD = 0.98` — appropriately conservative (only near-exact duplicates). Configurable via `--score-threshold` CLI flag. Dry-run is the default: `MaintenanceReport.dry_run` defaults to `True`, `--apply` required for deletions. Both `prune_stale_sources()` and `merge_duplicates()` check `dry_run` and return counts without deleting.
**Design note:** `--dry-run` CLI flag is parsed but never read — `dry_run = not args.apply` ignores it. The flag is dead code but the safety behavior is correct.

### Additional v1 fixes verified (outside numbered fix plan)

**v1 B-4.1 (Health history unbounded):** ✅ Fixed. `rotate_history()` exists with `MAX_HISTORY_LINES = 10_000` rotation. Tests verify: noop when missing, noop under limit, truncation at limit, boundary exact.

**v1 C-4.3 (No connectivity tests):** ✅ Fixed. `tests/test_connectivity_checks.py` (182 LOC, 17 tests) covers all 5 connectivity checks: Tailscale (online/offline/not-installed/error/multi-peer), ntfy (healthy/unreachable/error), n8n (healthy/unreachable), Obsidian (running/not-running), gdrive-sync (dir-missing/timer-active/timer-inactive).

**v1 C-4.1 (knowledge_maint missing profile-facts):** ✅ Fixed. `COLLECTIONS = ["documents", "samples", "claude-memory", "profile-facts"]` — all 4 collections now maintained.

---

## Completeness Findings

### C2-4.1: Check count documentation says 49 but actual count is ~52
**File:** Documentation vs `agents/health_monitor.py`
**Severity:** low
**Finding:** The documentation claims "49 checks" but the actual count varies with Docker container count. With 12 containers running: 3 docker-base + 12 containers + 3 GPU + 5 systemd + 5 qdrant + 4 profiles + 4 endpoints + 6 credentials + 1 disk + 4 models + 2 auth + 5 connectivity = ~54. The documentation count was likely from a specific measured run and is not a fixed invariant.
**Impact:** Cosmetic. The check system works correctly regardless of the count.

### C2-4.2: Introspect does not capture Docker volumes or networks
**File:** `agents/introspect.py`
**Severity:** low
**Finding:** The manifest captures containers, ports, systemd units, Qdrant collections, Ollama models, GPU, LiteLLM routes, disk, listening ports, pass entries, and profile files. Missing: Docker volumes/networks, system-level systemd services, PipeWire/ALSA state, MIDI device state, Python/Node versions, n8n workflow state, Langfuse prompt versions.
**Impact:** Low. Most blind spots are irrelevant to drift detection. Docker volumes could matter for infrastructure recovery.

### C2-4.3: No tests for `run_fixes()` auto-fix path
**File:** `agents/health_monitor.py`
**Severity:** low
**Finding:** The auto-fix function (executes remediation commands via `bash -c`) has no test coverage. Given the watchdog runs `--fix --yes` every 15 minutes, this code path executes frequently in production.
**Impact:** Low. The remediation commands are constants in the code, not dynamic inputs. But the execution flow (confirmation, timeout, error handling) is untested.

### C2-4.4: No tests for `generate_manifest()` orchestration
**File:** `agents/introspect.py`
**Severity:** low
**Finding:** Individual collectors are thoroughly tested, but the top-level `generate_manifest()` (which calls all collectors via `asyncio.gather` and assembles the `InfrastructureManifest`) has no integration test.
**Impact:** Low. The individual collectors are well-tested. A regression in the assembly logic is unlikely but possible.

### C2-4.5: `collect_service_events()` in activity_analyzer untested
**File:** `agents/activity_analyzer.py`
**Severity:** low
**Finding:** The systemd journal collector parses `journalctl` output. No test exercises the parsing logic. `format_human` constructs `ServiceEvent` objects directly for rendering tests.
**Impact:** Low. The parsing is straightforward (`json.loads` on journal JSON output).

---

## Correctness Findings

### R2-4.1: `_manifest_age()` reads wrong key — always returns empty
**File:** `agents/activity_analyzer.py:458-467`
**Severity:** medium
**Finding:** `_manifest_age()` reads `data.get("generated_at", "")` but the `InfrastructureManifest` schema uses `timestamp` as the field name. This means `DataSourceStatus.manifest_age` is always an empty string regardless of whether the manifest file exists and is valid. The manifest age is supposed to tell the briefing agent how old the infrastructure snapshot is.
**Impact:** Medium. The briefing agent never knows how old the manifest is, which could mean it uses stale infrastructure data without warning. This is a key-name bug introduced during Fix 31 or the original implementation.
**Operator impact:** The operator's briefing could reference a weeks-old manifest with no indication of staleness.

### R2-4.2: `check_gdrive_sync_freshness()` doesn't check freshness
**File:** `agents/health_monitor.py`
**Severity:** low
**Finding:** The function name says "freshness" but it only checks whether the gdrive-sync timer is active. There is no mtime check on the sync directory to determine when the last sync actually completed. The function returns HEALTHY if the directory doesn't exist ("not configured").
**Impact:** Low. The gdrive-sync timer is planned but not yet created. When it is created, this check would pass even if syncs are failing silently.

### R2-4.3: `--dry-run` CLI flag in knowledge_maint is dead code
**File:** `agents/knowledge_maint.py:494, 512`
**Severity:** low
**Finding:** `--dry-run` is parsed but never read. `dry_run = not args.apply` on line 512 determines the actual behavior. Passing `--dry-run` and `--apply` together would still apply changes because `args.dry_run` is ignored.
**Impact:** Low. The default behavior is correct (dry-run by default). The dead flag is confusing to users but not dangerous.

### R2-4.4: Near-duplicate detection only samples first 500 points
**File:** `agents/knowledge_maint.py:195-196`
**Severity:** low
**Finding:** `find_near_duplicates()` scrolls only the first `sample_limit=500` points. In a collection with thousands of points, duplicates among later points are never detected. The scroll returns points in Qdrant's internal order (typically insertion order), biasing toward older content.
**Impact:** Low. The 0.98 threshold means only near-exact duplicates are caught. For the operator's collection sizes (documents ~2000, samples ~500), the sample covers a reasonable fraction.

### R2-4.5: Stale source detection vulnerable to temporary filesystem unavailability
**File:** `agents/knowledge_maint.py:128`
**Severity:** low
**Finding:** `find_stale_sources()` uses `Path(source).exists()` — if a source path is on a temporarily unmounted volume, all its vectors are incorrectly identified as stale. Mitigated by dry-run default: the timer runs without `--apply`.
**Impact:** Low with current safeguards. Would be medium if the timer ever adds `--apply`.

---

## Robustness Findings

### B2-4.1: Auto-fix watchdog runs `--fix --yes` with no backoff
**File:** `<local-bin>/health-watchdog`
**Severity:** medium
**Finding:** The watchdog passes `--fix --yes` on every invocation when status is not healthy. If a remediation fails (e.g., Docker daemon won't start), the same fix is retried every 15 minutes indefinitely. No exponential backoff, no attempt counter, no circuit breaker.
**Impact:** Medium. Mostly noise (repeated journal entries, repeated notifications). For `docker system prune -f` (disk remediation), repeated execution has diminishing returns. For `sudo systemctl start docker`, the sudo will fail unattended anyway.
**Operator impact:** Notification fatigue from repeated identical failure alerts every 15 minutes.

### B2-4.2: knowledge_maint exception handling swallows errors silently
**File:** `agents/knowledge_maint.py`
**Severity:** medium
**Finding:** Multiple operations use `except Exception` patterns that silently return empty results:
- `find_stale_sources()`: Qdrant error → empty list (logged as warning)
- `find_near_duplicates()` scroll: Qdrant error → empty list
- `find_near_duplicates()` per-point search: Qdrant error → skip point
- `prune_stale_sources()` per-source delete: Qdrant error → skip
- `merge_duplicates()` batch delete: Qdrant error → pass

If Qdrant is intermittently failing, the report shows "0 stale, 0 duplicates" — indistinguishable from a clean collection. The warnings are logged but not surfaced in the report or notification.
**Impact:** Medium. The operator sees "maintenance complete, nothing to do" when in reality Qdrant refused every query.

### B2-4.3: Langfuse pagination loop has no page limit
**File:** `agents/activity_analyzer.py:143-157`
**Severity:** low
**Finding:** The trace/observation pagination loops run `while True` until `len(all_items) >= total` or an empty page. If `totalItems` increases between pages (new traces being created), the loop continues indefinitely. With a 10-second timeout per request and hundreds of pages, this could take significant time.
**Impact:** Low. The operator's Langfuse volume is moderate. The `langfuse_get()` timeout (default 10s) provides a per-request bound, and an empty/error response breaks the loop.

### B2-4.4: `run_fixes()` executes remediation via `bash -c`
**File:** `agents/health_monitor.py:1305`
**Severity:** low
**Finding:** Remediation commands are passed to `bash -c` as strings with interpolated values like `{service}` and `{COMPOSE_FILE.parent}`. Service names come from Docker Compose output (constrained naming), so shell injection is not currently possible. But it's a defense-in-depth gap — if a container name contained shell metacharacters, they would be interpreted.
**Impact:** Low. Container names are controlled by the operator's compose file.

### B2-4.5: Drift detector truncates docs at 8000 chars
**File:** `agents/drift_detector.py:148-149`
**Severity:** low
**Finding:** Documents exceeding 8000 characters are truncated with `[... truncated ...]`. The main CLAUDE.md files can exceed this. Truncated sections containing tables or configuration details relevant to drift detection are lost. The truncation is a blunt cut — no attempt to preserve section boundaries.
**Impact:** Low. The LLM can still identify drift from the first 8000 chars of most docs. High-value content like service tables tends to appear early in CLAUDE.md files.

### B2-4.6: `find_near_duplicates()` blocks event loop
**File:** `agents/knowledge_maint.py`
**Severity:** low
**Finding:** `find_near_duplicates()` is a sync function that issues up to 2000 individual `client.search()` calls. `run_maintenance()` is async but calls it directly without `await loop.run_in_executor(...)`. For large collections, this blocks the event loop for several seconds.
**Impact:** Low. knowledge_maint runs as a standalone CLI process, not within a shared event loop.

### B2-4.7: `http_get()` returns status 0 for all error types
**File:** `agents/health_monitor.py:148-152`
**Severity:** low
**Finding:** `http_get()` returns `(0, str(e))` for all exceptions (URLError, timeout, generic). Callers can distinguish success (code 200) from failure (code 0) but cannot programmatically distinguish connection refused from timeout from DNS failure. The error string is available but unstructured.
**Impact:** Low. Callers only need pass/fail semantics. The error string is logged for diagnostics.

---

## Test Coverage Assessment

| File | Status | Tests | Notes |
|------|--------|-------|-------|
| `health_monitor.py` — check groups | **well tested** | 53 + 17 | All 11 groups have tests. Connectivity checks newly covered |
| `health_monitor.py` — runner/format | **adequate** | (in above) | run_checks, quick_check, format_human, rotate_history tested |
| `health_monitor.py` — auto-fix | **untested** | 0 | run_fixes(), format_history() not tested |
| `introspect.py` — collectors | **excellent** | 51 | Every collector has success + failure tests |
| `introspect.py` — orchestration | **untested** | 0 | generate_manifest() not tested |
| `drift_detector.py` | **well tested** | 30 | Schemas, formatters, detect/fix flow, severity filtering |
| `activity_analyzer.py` — collectors | **adequate** | 21 | Langfuse (4 cases), health/drift trend, formatters |
| `activity_analyzer.py` — service_events | **untested** | 0 | Journal collector not tested |
| `knowledge_maint.py` | **well tested** | 37 | All operations, dry-run safety, error logging, notifications |

**Overall:** 209 tests across 6 files. Significant improvement from v1 (added connectivity tests, knowledge_maint tests). Main gaps: auto-fix path, generate_manifest orchestration, service_events collector.

---

## Summary

### Fix Verification Scorecard

| Fix | Status | Quality |
|-----|--------|---------|
| 5 (Langfuse auth validation) | ✅ Complete | Good: actual HTTP request with Basic auth |
| 8 (LiteLLM model list) | ✅ Complete | Good: validates auth + model count |
| 16 (Auto-discoverable groups) | ✅ Complete | Good: decorator-based registry |
| 30 (Langfuse timestamps) | ✅ Complete | Good: centralized urlencode in langfuse_client |
| 31 (Missing data sources) | ✅ Complete | Thorough: DataSourceStatus model + per-collector guards |
| 63 (Knowledge maint thresholds) | ✅ Complete | Good: 0.98 threshold + dry-run default |

**6 of 6 fixes fully verified. 0 partial. 0 failed.**

Additionally verified: health history rotation (B-4.1), connectivity tests (C-4.3), profile-facts in COLLECTIONS (C-4.1) — all resolved.

### New Findings

| ID | Severity | Category | Summary |
|----|----------|----------|---------|
| C2-4.1 | low | completeness | Check count documentation says 49, actual ~54 |
| C2-4.2 | low | completeness | Introspect missing Docker volumes/networks |
| C2-4.3 | low | completeness | No tests for run_fixes() auto-fix path |
| C2-4.4 | low | completeness | No tests for generate_manifest() orchestration |
| C2-4.5 | low | completeness | collect_service_events() untested |
| R2-4.1 | **medium** | correctness | `_manifest_age()` reads wrong key — always empty |
| R2-4.2 | low | correctness | gdrive_sync_freshness doesn't check freshness |
| R2-4.3 | low | correctness | `--dry-run` CLI flag is dead code |
| R2-4.4 | low | correctness | Near-duplicate detection samples only first 500 points |
| R2-4.5 | low | correctness | Stale source detection vulnerable to temp filesystem unavailability |
| B2-4.1 | **medium** | robustness | Auto-fix watchdog retries with no backoff |
| B2-4.2 | **medium** | robustness | knowledge_maint swallows Qdrant errors silently |
| B2-4.3 | low | robustness | Langfuse pagination loop has no page limit |
| B2-4.4 | low | robustness | run_fixes() uses bash -c with interpolated values |
| B2-4.5 | low | robustness | Drift detector truncates docs at 8000 chars |
| B2-4.6 | low | robustness | find_near_duplicates() blocks event loop |
| B2-4.7 | low | robustness | http_get() returns status 0 for all error types |

### Overall Assessment

Domain 4 is the **strongest domain in fix quality** — all 6 fixes fully verified, plus 3 additional v1 findings resolved. The health monitor architecture (decorator registry, typed schemas, parallel async execution) is clean and extensible. The introspect/drift-detector pipeline is well-designed. Knowledge maint has appropriate safety defaults.

**Two medium findings merit attention:**
1. **R2-4.1 (`_manifest_age()` wrong key):** A silent data bug that makes manifest staleness invisible. The briefing agent uses `DataSourceStatus` but never sees actual manifest age. Single-line fix: `data.get("timestamp", "")` instead of `data.get("generated_at", "")`.
2. **B2-4.1 (watchdog no backoff):** Not dangerous but creates notification fatigue. A simple attempt counter with 3-strike pause would help.

**Fix quality assessment:** The D4 fixes were applied carefully and consistently. The check group registry (Fix 16) is the best-designed fix in the audit — it eliminates an entire category of future maintenance burden. The Langfuse timestamp fix (Fix 30) was correctly centralized rather than patched at each call site. The DataSourceStatus model (Fix 31) is thorough and well-tested.

**Operator impact:** The health & observability domain serves the operator well. The 15-minute health monitoring with auto-fix provides hands-off infrastructure management. The briefing pipeline (activity → health → briefing) gives a daily cockpit instrument panel. The main operator-facing gap is the `_manifest_age()` bug — the operator's briefing doesn't know when the infrastructure snapshot was last refreshed, which could mask stale data.
