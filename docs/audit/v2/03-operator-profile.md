# Domain 3: Operator Profile — Audit v2 Findings

**Audited:** 2026-03-03
**Auditor:** Claude Code (v2 full re-read)
**Prior findings (v1):** 17 (6 completeness, 4 correctness, 7 robustness)
**Fixes to verify:** 27, 28, 29, 53

---

## Inventory

| File | v1 LOC | v2 LOC | Delta | Test File(s) | Test LOC |
|------|--------|--------|-------|-------------|----------|
| `agents/profiler.py` | 1,862 | 1,746 | -116 | `tests/test_profiler.py` | 1,227 |
| | | | | `tests/test_profiler_integration.py` | 245 |
| | | | | `tests/test_profile_visibility.py` | 228 |
| `agents/profiler_sources.py` | 958 | 978 | +20 | (in test_profiler.py) | — |
| `shared/profile_store.py` | 178 | 211 | +33 | `tests/test_profile_store.py` | 387 |
| `shared/context_tools.py` | 162 | 162 | 0 | `tests/test_context_tools.py` | 212 |
| `shared/management_bridge.py` | 298 | 301 | +3 | `tests/test_management_bridge.py` | 230 |

**Additional D3-adjacent test files:**
- `tests/test_interview.py` (578 LOC, 37 tests) — interview state, flush_interview_facts
- `tests/test_conversational_learning.py` (262 LOC, 18 tests) — pending_facts reader
- `tests/test_decisions.py` (191 LOC, 14 tests) — decisions reader

**Total source:** 3,398 LOC (was 3,458, -60 — context refactoring removed static injection)
**Total primary test:** 2,529 LOC (147 tests)
**Total including adjacent:** 3,560 LOC (216 tests)
**Test:source ratio:** 0.75 (primary) / 1.05 (including adjacent)

---

## Fix Verification

### Fix 27: Profiler should validate operator.json before overwriting — NOT IMPLEMENTED
**v1 finding:** B-3.2 (medium)
**Status:** ❌ Not implemented.
`regenerate_operator()` at `profiler.py:1035-1046` reads `operator.json`, passes it through LLM for updates, then writes back with `operator_path.write_text(json.dumps(operator_data, indent=2))`. There is:
- No pre-write size comparison against the original
- No backup before overwriting
- No atomic write (write-to-temp-then-rename)
- No validation that the resulting JSON is non-empty or structurally valid

If the LLM returns an empty or corrupted update, or if the process is killed mid-write, `operator.json` is silently corrupted. Additionally, `load_existing_profile()` at line 507 swallows all exceptions with `except Exception: return None` — a corrupted `operator-profile.json` becomes invisible, triggering full re-extraction as if no profile existed.
**Impact:** Medium. The operator's profile is the single source of truth for system behavior. A corrupted `operator.json` would degrade all agents that use context tools. The `regenerate_operator()` path runs during `--auto` (the 12h timer), so corruption would happen silently during unattended operation.

### Fix 28: Profiler fact dedup — VERIFIED
**v1 finding:** C-3.1 (medium)
**Status:** ✅ Complete and correct.
`merge_facts()` at `profiler.py:287-323` uses `(dimension, key)` tuple as dedup key with authority-aware precedence:
1. New authority overrides existing observation (regardless of confidence)
2. Existing authority blocks new observation
3. Same class: higher confidence wins
4. Equal confidence: existing wins (tie-break)

`AUTHORITY_SOURCES = frozenset({"interview", "config", "memory", "operator"})` correctly defined.
**Tests:** 7 test cases covering all merge paths: `test_merge_facts_higher_confidence_wins`, `test_merge_authority_overrides_observation`, `test_merge_observation_cannot_override_authority`, `test_merge_both_authority_higher_confidence_wins`, etc.
**Quality note:** Dedup only operates on exact `(dimension, key)` string match. Semantically identical facts with different key strings (e.g., `"python_tool"` vs `"preferred_python_tool"`) are not caught. This is by design — the curation pass handles semantic dedup via LLM. In `run_auto()`, curation IS called post-extraction, which is correct. In `run_extraction()`, curation is NOT called — manual runs don't curate, only `--auto` does.

### Fix 29: Profiler source error isolation — PARTIALLY APPLIED
**v1 finding:** B-3.1 (high)
**Status:** ⚠️ Partial. Two complementary mechanisms were implemented:

1. **`_read_capped()`** in `read_all_sources()` (`profiler_sources.py:416-447`) catches `(OSError, UnicodeDecodeError)` per-file and continues. This protects against file I/O errors during bulk reading.

2. **`_extract_one()`** in `extract_from_chunks()` (`profiler.py:386-393`) catches `Exception` per-chunk for LLM failures. Failed chunks return empty fact lists; siblings continue.

**What's still broken:**
- **Git reader bypasses `_read_capped()`:** `read_git_info()` is called directly in `read_all_sources()` at line ~420 without a try/except wrapper. A git binary missing from PATH or a subprocess error would abort the entire source reading loop.
- **8 reader functions have no internal error handling:** `read_config_file()`, `read_transcript()`, `read_memory_file()`, `read_llm_export()`, `read_takeout()`, `read_proton()`, `read_vault_inbox()`, `read_management_notes()` all call `path.read_text()` bare. While `_read_capped()` catches `OSError | UnicodeDecodeError`, any other exception type (unlikely but possible) would propagate.
- **`_read_capped()` catch scope is narrow:** Only `OSError` and `UnicodeDecodeError` are caught. A hypothetical `MemoryError` from a very large file or a `RecursionError` from pathological content would propagate unhandled.

**Test:** `test_extract_from_chunks_error_handling` verifies per-chunk isolation. No test for reader-level isolation.

### Fix 53: Consolidate system prompt fragment injection — PARTIALLY APPLIED
**v1 finding:** H-3.1 (medium)
**Status:** ⚠️ Partial. The architectural intent is correct and mostly implemented:

**What's done:**
- `SYSTEM_CONTEXT` in `shared/operator.py:37` slimmed to ~150 tokens (identity + neurocognitive note + pointer to tools)
- `get_system_prompt_fragment()` returns only identity + axioms + accommodations
- All major agents register context tools via `get_context_tools()` pattern
- `briefing.py` is the cleanest implementation: pure domain prompt, no `SYSTEM_CONTEXT`, tools registered

**What's inconsistent:**
- `research.py:43` injects `SYSTEM_CONTEXT` directly in `_build_system_prompt()` AND registers context tools — dual injection
- `code_review.py:36` imports `SYSTEM_CONTEXT` directly instead of using `get_system_prompt_fragment()` — works identically but inconsistent pattern
- No test enforces the token budget constraint or verifies prohibited content is absent from static injection

**Impact:** Low. The inconsistencies don't cause functional bugs since `SYSTEM_CONTEXT` is already lean. They're architectural hygiene issues that could drift over time.

---

## Completeness Findings

### C2-3.1: No integration tests for pipeline orchestration
**File:** `agents/profiler.py:1480-1858`
**Severity:** medium
**Finding:** `run_auto()`, `run_extraction()`, `run_curate()`, `run_ingest()` have zero test coverage. These are the primary entry points that orchestrate discovery → extraction → merging → synthesis → curation → digest → indexing. `test_profiler_integration.py` (245 LOC, 10 tests) claims to test integration but actually tests individual components in isolation — none of the pipeline functions are invoked.
**Impact:** Orchestration bugs (wrong argument passing, incorrect state flow between stages, missing error handling around stage transitions) would go undetected.

### C2-3.2: No tests for regenerate_operator() or _regenerate_operator_md()
**File:** `agents/profiler.py:1035-1284`
**Severity:** medium
**Finding:** The operator manifest update pipeline (LLM-powered goal progress, pattern additions, neurocognitive updates) and `_regenerate_operator_md()` (pure formatting) have no test coverage.
**Impact:** Bugs in operator manifest regeneration would be undetected until observed in production. `_regenerate_operator_md()` is a pure function that could easily be tested deterministically.

### C2-3.3: Six individual reader functions have no unit tests
**File:** `agents/profiler_sources.py:238-515`
**Severity:** low
**Finding:** `read_config_file()`, `read_shell_history()`, `read_git_info()`, `read_memory_file()`, `read_vault_inbox()`, `read_management_notes()`, `read_drift_report()` have no dedicated tests. Most are trivial wrappers around `_chunk_text()`, but `read_shell_history()` (history parsing), `read_git_info()` (subprocess calls), and `read_drift_report()` (JSON parsing) have meaningful logic.
**Impact:** Low. Core logic (`_chunk_text`) is well-tested. Reader-specific logic is minimal.

### C2-3.4: store_to_qdrant() appears to be legacy code alongside ProfileStore
**File:** `agents/profiler.py:984-1047`
**Severity:** low
**Finding:** `store_to_qdrant()` writes to the `claude-memory` collection while `ProfileStore.index_profile()` writes to `profile-facts`. Both paths exist. The `run_auto()` pipeline calls `ProfileStore.index_profile()` (the new path) but `store_to_qdrant()` remains callable. The coexistence is confusing and could lead to stale data in `claude-memory`.
**Impact:** Low. If `store_to_qdrant()` is never called, it's dead code. If it IS called (e.g., by a manual invocation), it writes to the wrong collection.

### C2-3.5: generate_digest() silently drops non-standard dimensions
**File:** `agents/profiler.py:1066`
**Severity:** low
**Finding:** `generate_digest()` iterates only `PROFILE_DIMENSIONS` (standard 13). `build_profile()` handles extra dimensions from LLM extraction, but the digest ignores them. Facts in non-standard dimensions would be in the profile but absent from the digest and unfindable via `get_profile_summary()`.
**Impact:** Low. Non-standard dimensions are rare in practice.

---

## Correctness Findings

### R2-3.1: load_existing_profile() silently swallows all exceptions
**File:** `agents/profiler.py:507-516`
**Severity:** medium
**Finding:** `except Exception: return None` with no logging. A corrupted `operator-profile.json` (e.g., from an interrupted write by Fix 27's missing atomic write) silently returns `None`. The caller in `run_auto()` treats `None` as "no profile exists" and triggers full re-extraction — potentially destroying the version history and accumulated curation work.
**Impact:** Medium. Profile corruption becomes invisible. The operator's carefully curated profile could be silently replaced by a fresh extraction with no indication of what happened.

### R2-3.2: load_structured_facts() silently discards malformed items
**File:** `agents/profiler.py:822-826`
**Severity:** low
**Finding:** Individual items in structured facts files are validated via `ProfileFact.model_validate(item)` in a `try/except Exception: pass` with no counter or log. If a profiler bridge produces hundreds of malformed items, all facts from that bridge are silently dropped with zero indication.
**Impact:** Low. Bridge output is deterministic and tested. Corruption would require filesystem issues.

### R2-3.3: management_bridge save_facts() overwrites valid data with empty array
**File:** `shared/management_bridge.py:61`
**Severity:** low
**Finding:** `save_facts(facts)` writes without checking whether `facts` is empty. If all vault notes are malformed (wrong frontmatter), `generate_facts()` returns `[]`, and `save_facts([])` overwrites a previously valid `management-structured-facts.json` with an empty JSON array.
**Impact:** Low. The vault is operator-authored and unlikely to have ALL notes malformed simultaneously.

### R2-3.4: _feedback_facts defaults missing direction to "given"
**File:** `shared/management_bridge.py:237`
**Severity:** low
**Finding:** `direction = fm.get("direction", "given")` silently defaults to "given" for feedback notes without an explicit `direction` property. This skews the `feedback_direction_ratio` fact.
**Impact:** Low. Feedback templates include the `direction` property. Only older notes lacking it would be affected.

### R2-3.5: run_extraction() skips curation — inconsistent with run_auto()
**File:** `agents/profiler.py:1454-1455`
**Severity:** low
**Finding:** `run_extraction()` calls `build_profile` + `save_profile` but not `curate_profile`. `run_auto()` calls all three. Profiles updated via manual `--extract` accumulate near-duplicate facts that would be cleaned by curation.
**Impact:** Low. Operators typically use `--auto` (timer-invoked). Manual extraction is for debugging.

---

## Robustness Findings

### B2-3.1: Git reader called outside _read_capped() — crashes abort source loop
**File:** `agents/profiler_sources.py:~420`
**Severity:** medium
**Finding:** `read_git_info()` is called directly in `read_all_sources()` without the `_read_capped()` wrapper that provides error isolation. If the git binary is missing or a repository is corrupted, the exception propagates up and aborts reading of ALL subsequent source types (vault-inbox, management, drift, etc.).
**Impact:** Medium. The git reader runs early in the source loop. A git failure during `run_auto()` (12h timer) would silently produce an incomplete profile update — only sources processed before git would contribute.
**Operator impact:** The operator might not notice incomplete profile updates since the profiler logs the error but still saves whatever it collected.

### B2-3.2: regenerate_operator() crashes on corrupt operator.json
**File:** `agents/profiler.py:1046`
**Severity:** medium
**Finding:** `operator_data = json.loads(operator_path.read_text())` has no exception handling. If `operator.json` is corrupted (from a previous interrupted write — per the missing Fix 27), this line raises `json.JSONDecodeError` and the entire `run_auto()` pipeline fails at the operator regeneration stage. The corrupted file is never repaired.
**Impact:** Medium. A self-reinforcing failure: missing atomic write → corruption → crash → no recovery. The operator must manually fix `operator.json`.

### B2-3.3: Operator cache never expires in long-running processes
**File:** `shared/operator.py`
**Severity:** low
**Finding:** `_operator_cache` is set once and never expires. In the cockpit TUI (long-running), if `operator.json` is updated by `regenerate_operator()` during a `--auto` run, the cockpit continues serving stale cached data until `reload_operator()` is explicitly called. The chat agent's system prompt is built at agent construction time and would not reflect post-run updates.
**Impact:** Low. The cockpit refreshes data periodically but doesn't call `reload_operator()`. In practice, the operator restarts the cockpit more often than the profile changes significantly.

### B2-3.4: _coaching_facts and _feedback_facts rglob entire vault
**File:** `shared/management_bridge.py:197, 232`
**Severity:** low
**Finding:** `_coaching_facts()` and `_feedback_facts()` use `vault_path.rglob("*.md")` which scans the entire vault recursively. For a vault with thousands of files, every markdown file is opened and frontmatter-parsed — including `60-archive/` and `90-attachments/`. The `_people_facts()` and `_meeting_facts()` functions correctly scope to `10-work/people/` and `10-work/meetings/` respectively.
**Impact:** Low. The operator's vault is hundreds (not thousands) of files. But it's wasteful and would scale poorly.

### B2-3.5: Langfuse reader fetches up to 4000 items with no memory cap
**File:** `agents/profiler_sources.py:615-651`
**Severity:** low
**Finding:** Traces and observations are fetched with pagination until `len(all_traces) >= total`, up to 20 pages of 100 items each (2000 traces + 2000 observations). All are held in memory simultaneously. With 30 days of heavy LLM usage, this could be several MB of JSON.
**Impact:** Low. The operator's usage volume is moderate. The page limit (20) provides a practical cap.

### B2-3.6: ProfileStore._cleanup_stale_points exists but scope is limited
**File:** `shared/profile_store.py`
**Severity:** low
**Finding:** The v1 finding (B-3.7) about stale points has been addressed — `_cleanup_stale_points()` now removes orphaned points after indexing. This is tested (`test_cleanup_stale_points_removes_orphans`). However, the cleanup only runs during `index_profile()` calls. If `index_profile()` is skipped (e.g., Qdrant is temporarily down), stale points accumulate until the next successful indexing.
**Impact:** Low. The cleanup is effective when it runs. Qdrant downtime during profiler runs is rare.

---

## Test Coverage Assessment

| File | Status | Tests | Notes |
|------|--------|-------|-------|
| `profiler.py` — schemas | **well tested** | 88 in test_profiler | All models, validators, serialization |
| `profiler.py` — merge/curation | **excellent** | (in test_profiler) | 7 merge cases, 4 curation ops |
| `profiler.py` — extraction | **adequate** | (in test_profiler) | Concurrency, early-stop, error handling |
| `profiler.py` — pipelines | **untested** | 0 | run_auto, run_extraction, run_curate, regenerate_operator |
| `profiler_sources.py` — discovery | **well tested** | (in test_profiler) | Sources, IDs, change detection |
| `profiler_sources.py` — readers | **partial** | scattered | langfuse (4), pending_facts (6), decisions (4). Six readers untested |
| `profile_store.py` | **well tested** | 21 | Collection, index, search, digest, cleanup |
| `context_tools.py` | **well tested** | 18 | All 4 tools + error paths |
| `management_bridge.py` | **well tested** | 18 | All extract functions + save |

**Primary gap:** Pipeline orchestration (`run_auto`, `run_extraction`, `run_curate`, `regenerate_operator`) — the functions that tie everything together.

---

## Summary

### Fix Verification Scorecard

| Fix | Status | Quality |
|-----|--------|---------|
| 27 (operator.json validation) | ❌ Not implemented | No size check, no backup, no atomic write |
| 28 (fact dedup) | ✅ Complete | Good: authority-aware merge on (dimension, key) |
| 29 (source error isolation) | ⚠️ Partial | Per-chunk LLM isolation good; reader-level isolation incomplete |
| 53 (context tool consolidation) | ⚠️ Partial | Architecture correct; 2 agents use inconsistent patterns |

**1 of 4 fixes fully verified. 2 partial (29, 53). 1 not implemented (27).**

### New Findings

| ID | Severity | Category | Summary |
|----|----------|----------|---------|
| C2-3.1 | medium | completeness | No integration tests for pipeline orchestration |
| C2-3.2 | medium | completeness | No tests for regenerate_operator() |
| C2-3.3 | low | completeness | Six reader functions untested |
| C2-3.4 | low | completeness | store_to_qdrant() is legacy alongside ProfileStore |
| C2-3.5 | low | completeness | generate_digest() drops non-standard dimensions |
| R2-3.1 | **medium** | correctness | load_existing_profile() silently swallows all exceptions |
| R2-3.2 | low | correctness | load_structured_facts() silently discards malformed items |
| R2-3.3 | low | correctness | save_facts() can overwrite valid data with empty array |
| R2-3.4 | low | correctness | _feedback_facts defaults missing direction to "given" |
| R2-3.5 | low | correctness | run_extraction() skips curation (inconsistent with run_auto) |
| B2-3.1 | **medium** | robustness | Git reader bypasses error isolation — crashes abort source loop |
| B2-3.2 | **medium** | robustness | regenerate_operator() crashes on corrupt operator.json |
| B2-3.3 | low | robustness | Operator cache never expires in long-running processes |
| B2-3.4 | low | robustness | coaching/feedback rglob scans entire vault |
| B2-3.5 | low | robustness | Langfuse reader fetches up to 4000 items, no memory cap |
| B2-3.6 | low | robustness | Stale point cleanup only runs during successful index |

### Overall Assessment

The operator profile system has strong core logic — merge semantics, authority hierarchy, curation operations, and context tools are well-designed and well-tested. The test:source ratio of 1.05 (including adjacent tests) is healthy.

**Three medium findings form a connected risk:**
1. **Fix 27 (not implemented):** `regenerate_operator()` writes without validation or atomic write
2. **R2-3.1:** `load_existing_profile()` silently swallows corruption
3. **B2-3.2:** `regenerate_operator()` crashes on already-corrupt files

Together these create a self-reinforcing failure path: a process kill during write → silent corruption → crash on next read → no recovery without manual intervention. This is the most important finding in D3.

**Fix quality assessment:** Fix 28 (dedup) is well-implemented with thorough tests. Fix 29 (error isolation) was applied at the extraction layer but not consistently at the reader layer. Fix 53 (context tools) achieved its architectural goal but left inconsistencies in 2 of ~8 agents. Fix 27 was simply not done.

**Operator impact:** The profile system is the operator's self-model — it drives all agent behavior via context tools. The core value proposition (multi-source extraction, authority-aware merge, interactive corrections, semantic search) works well. The main operator-facing risk is the corruption path described above, which could silently destroy carefully curated profile data during an unattended `--auto` run.
