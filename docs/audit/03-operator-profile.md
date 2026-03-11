# Domain 3: Operator Profile System -- Audit Findings

## Inventory

### Source Files

| File | LOC | Purpose |
|------|-----|---------|
| `agents/profiler.py` | 1,862 | Operator profile extraction/curation, 13 dimensions, run_auto pipeline |
| `agents/profiler_sources.py` | 958 | Source readers (Langfuse, vault, takeout, proton, management, etc.) |
| `shared/profile_store.py` | 178 | Qdrant profile-facts collection, semantic search, digest access |
| `shared/context_tools.py` | 162 | Tool functions for on-demand operator context |
| `shared/management_bridge.py` | 298 | Deterministic fact extraction from Obsidian vault |
| **Total source** | **3,458** | |

### Test Files

| File | LOC | Purpose |
|------|-----|---------|
| `tests/test_profiler.py` | 1,225 | Schema, merging, discovery, chunking, curation, scalability |
| `tests/test_profile_store.py` | 315 | Collection management, indexing, search, digest access |
| `tests/test_context_tools.py` | 212 | All 4 tool functions, error handling, docstring validation |
| `tests/test_management_bridge.py` | 230 | All _extract_* functions, save_facts, frontmatter parsing |
| **Total test** | **1,982** | |

### Additional Test Coverage (outside scoped files)

| File | Relevance |
|------|-----------|
| `tests/test_profile_visibility.py` | Tests `apply_corrections()`, operator correction authority |
| `tests/test_conversational_learning.py` | Tests `read_pending_facts()` reader |
| `tests/test_decisions.py` | Tests `read_decisions_log()` reader |
| `tests/test_llm_export_converter.py` | Tests `read_llm_export()` reader |
| `tests/test_takeout_profiler_bridge.py` | Tests `read_takeout()` and `load_structured_facts()` |

---

## Focus Area 1: Source Discovery Completeness

### Reader Inventory

There are **16 distinct source types** with corresponding readers in `profiler_sources.py`:

| # | Source Type | Reader Function | Lines | Has Tests? |
|---|-----------|----------------|-------|------------|
| 1 | `config` | `read_config_file()` | 238-242 | Indirect (via discovery) |
| 2 | `transcript` | `read_transcript()` | 245-282 | Indirect (via discovery) |
| 3 | `shell-history` | `read_shell_history()` | 285-304 | No unit test |
| 4 | `git` | `read_git_info()` | 307-335 | No unit test |
| 5 | `memory` | `read_memory_file()` | 338-342 | No unit test |
| 6 | `llm-export` | `read_llm_export()` | 345-349 | Yes (test_llm_export_converter.py) |
| 7 | `takeout` | `read_takeout()` | 352-356 | Yes (test_takeout_profiler_bridge.py) |
| 8 | `proton` | `read_proton()` | 359-363 | Indirect (via exclude tests) |
| 9 | `vault-inbox` | `read_vault_inbox()` | 366-370 | No unit test |
| 10 | `management` | `read_management_notes()` | 373-377 | Indirect (via discover_sources test) |
| 11 | `drift` | `read_drift_report()` | 497-515 | No unit test |
| 12 | `conversation` | `read_pending_facts()` | 520-553 | Yes (test_conversational_learning.py) |
| 13 | `decisions` | `read_decisions_log()` | 558-589 | Yes (test_decisions.py) |
| 14 | `langfuse` | `read_langfuse()` | 603-750 | Yes (test_profiler.py, 4 tests) |

Total readers: **14** (not 16). The CLAUDE.md says 16, but 2 of the source types (`takeout`, `proton`, `management`) are "bridged" sources that get read as text for LLM extraction AND have deterministic profiler bridges. They are not separate readers; they just dual-path. The actual number of distinct reader functions is 14.

### Absent source handling

All file-based readers use `path.read_text(encoding="utf-8", errors="replace")` which will raise `FileNotFoundError` if the file is missing. Only some readers wrap this:

- `read_shell_history()` catches `OSError` -- good.
- `read_drift_report()` catches `(json.JSONDecodeError, OSError)` -- good.
- `read_pending_facts()` catches `OSError` -- good.
- `read_decisions_log()` catches `OSError` -- good.
- `read_git_info()` catches `(subprocess.TimeoutExpired, OSError)` -- good.
- `read_langfuse()` returns `[]` if no credentials -- good.

However, `read_config_file()`, `read_transcript()`, `read_memory_file()`, `read_llm_export()`, `read_takeout()`, `read_proton()`, `read_vault_inbox()`, and `read_management_notes()` do **not** catch file I/O errors. This is partially mitigated because `_read_capped()` in `read_all_sources()` does not catch exceptions from individual readers either -- a single unreadable file would crash the entire bulk read loop for that source type.

---

## Focus Area 2: Fact Deduplication and Conflict Resolution

### Merge Logic (profiler.py:289-323)

The `merge_facts()` function uses a `(dimension, key)` tuple as the dedup key. Same dimension + same key = **replace** (not accumulate). The logic is:

1. All existing facts are loaded into a `fact_map` keyed by `(dimension, key)`.
2. For each new fact:
   - If key not present: insert directly.
   - If key present, check authority:
     - New is authority, existing is observation: **new wins** (regardless of confidence).
     - Existing is authority, new is observation: **existing wins** (regardless of confidence).
     - Same class (both authority or both observation): **higher confidence wins**.
     - **Equal confidence, same class**: existing wins (no replacement). This is the implicit `elif` fall-through.

**Verified with tests**: `test_merge_authority_overrides_observation`, `test_merge_observation_cannot_override_authority`, `test_merge_same_type_higher_confidence_wins`, `test_merge_both_authority_higher_confidence_wins`.

### Authority sources

Defined at line 77: `AUTHORITY_SOURCES = frozenset({"interview", "config", "memory", "operator"})`. The `_source_prefix()` function (line 284-286) splits on both `/` and `:` to extract the prefix, correctly handling sources like `"interview:2024-01-15"`, `"config:<claude-config>/CLAUDE.md"`, and `"operator:correction"`.

---

## Focus Area 3: Confidence Scoring Consistency

### Confidence levels by source

| Source | Confidence | Where Assigned |
|--------|-----------|----------------|
| Operator corrections | 1.0 | `apply_corrections()` line 749 |
| Interview facts | Varies (from RecordedFact) | `flush_interview_facts()` line 618-626 |
| Interview insights | 0.85 | `flush_interview_facts()` line 645 |
| Management bridge | 0.90 | `management_bridge._make_fact()` line 29 |
| Takeout/Proton bridge | 0.95 | `profiler_bridge.py` (not in scope, per MEMORY.md) |
| LLM-extracted facts | 0.0-1.0 (LLM decides) | `extraction_agent` system prompt line 135 |

### Operator corrections authority verification

`apply_corrections()` (lines 707-794) creates facts with `confidence=1.0` and `source="operator:correction"`. Since `"operator"` is in `AUTHORITY_SOURCES`, these facts will always override observation-sourced facts during merge. They will also beat other authority sources via the equal-class confidence comparison (1.0 is maximum). This is correct.

Tested in `test_profile_visibility.py` (`test_apply_correction_updates_value`, `test_apply_correction_overrides_any_source`, etc.).

### Rationale gap

There is no documented rationale for why management bridge uses 0.90 and takeout bridge uses 0.95. Both are deterministic sources. The difference is arbitrary and has no practical consequence since they use different keys.

---

## Focus Area 4: Digest Generation

### generate_digest() (profiler.py:1052-1122)

**Fact sampling**: For each dimension, sorts facts by confidence descending and takes top 20 (line 1079). This is correct behavior for large dimensions.

**Empty dimensions**: Handled explicitly at lines 1069-1075. Empty dimensions get `"No data collected yet."` summary with `fact_count=0` and `avg_confidence=0.0`. Good.

**LLM failure mid-digest**: Each dimension has its own try/except (lines 1082-1099). If one LLM call fails, the fallback summary is `"{count} facts collected, avg confidence {avg_conf:.2f}."` Other dimensions continue processing. Good fault isolation.

**Output structure**: The digest dict has keys `generated_at`, `profile_version`, `total_facts`, `overall_summary`, and `dimensions` (keyed by dimension name). `ProfileStore.get_digest()` (line 153-165) simply loads this JSON and returns it. `get_profile_summary()` in `context_tools.py` accesses `digest.get("dimensions", {})` which matches. Confirmed compatible.

**Test coverage**: `test_generate_digest_structure` in `test_profile_store.py` validates the structure and file persistence. Good.

**Observation**: `generate_digest()` only iterates `PROFILE_DIMENSIONS` (line 1066), not the actual profile dimensions. Extra dimensions (outside the standard 13) added by LLM extraction would be silently dropped from the digest. The digest `total_facts` (line 1107) sums only standard dimensions, so it could undercount.

---

## Focus Area 5: Profile Indexing to Qdrant

### index_profile() (profile_store.py:56-105)

**Deterministic IDs**: Uses `uuid.uuid5(uuid.NAMESPACE_DNS, f"profile-fact-{dimension}-{key}")` (line 92-95). `NAMESPACE_DNS` is a standard UUID namespace. The format concatenates dimension and key, making the ID stable across runs for the same fact. Verified by `test_index_profile_deterministic_ids`.

**Batch upsert**: Batch size is 100 (line 99). For a profile with 150 facts, this produces 2 batches: 100 + 50. Verified by `test_index_profile_batches_large_profiles`.

**Qdrant failure mid-batch**: No error handling around the `self.client.upsert()` call (line 102). If Qdrant fails during the second batch, the first 100 points are already written but the remaining 50 are lost. This leaves the collection in an inconsistent state. However, because IDs are deterministic, a retry would overwrite the first batch and add the second, eventually reaching consistency.

**Called from run_auto**: The `run_auto()` pipeline wraps the indexing in a try/except (lines 1793-1800), logging a warning on failure. Good -- a Qdrant outage does not crash the auto-update.

---

## Focus Area 6: Structured Fact Loading

### load_structured_facts() (profiler.py:799-828)

Loads from three files:
1. `takeout-structured-facts.json`
2. `proton-structured-facts.json`
3. `management-structured-facts.json`

**Missing file**: `if not facts_file.exists(): continue` (line 813). Graceful.

**Corrupt JSON**: Caught by `except (json.JSONDecodeError, OSError)` (line 817). Logs warning and continues. Good.

**Not a list**: `if not isinstance(data, list): continue` (line 820-821). Handles unexpected top-level JSON type. Good.

**Malformed individual facts**: Each item is validated via `ProfileFact.model_validate(item)` in a try/except that silently skips invalid entries (lines 822-826). This means a single corrupt entry does not block loading of valid entries. Good.

**Test coverage**: `test_load_structured_facts_includes_management` and `test_load_structured_facts_empty_when_missing` in `test_profiler.py`. Additional tests in `test_takeout_profiler_bridge.py` for corrupt JSON, non-list data, and invalid entries.

---

## Focus Area 7: Context Tools Error Handling

### lookup_constraints() and lookup_patterns() (context_tools.py:24-73)

Both follow the same pattern: import from `shared.operator`, call the function, catch generic `Exception`, return error message string. The dependency (`shared.operator.get_constraints` / `get_patterns`) loads from `profiles/operator.json`. If the file is missing, `get_constraints` returns an empty list, not an exception, so the tool returns "No constraints found." -- correct fallback.

### search_profile() (context_tools.py:76-107)

The entire ProfileStore creation and search is wrapped in `try/except Exception` (lines 86-96). If Qdrant is down, the exception message is returned as `"Profile search unavailable: {e}"`. Verified by `test_search_profile_handles_error`.

### get_profile_summary() (context_tools.py:110-152)

ProfileStore creation and `get_digest()` are wrapped in `try/except Exception` (lines 119-125). If Qdrant is down (or ProfileStore constructor fails), returns `"Profile digest unavailable: {e}"`. If digest is `None` (file missing), returns actionable guidance: `"No profile digest available. Run profiler --digest to generate one."` Verified by `test_get_profile_summary_no_digest`.

**All 4 tools fail gracefully.** No exceptions leak to the caller.

---

## Focus Area 8: Management Bridge Vault Scanning

### _parse_frontmatter() (management_bridge.py:76-79)

Delegates to `shared.vault_utils.parse_frontmatter()` (vault_utils.py:9-35) which:
- Catches `(OSError, UnicodeDecodeError)` on file read (returns `{}`).
- Returns `{}` if no `---` markers.
- Returns `{}` if empty YAML.
- Catches `yaml.YAMLError` (returns `{}`).
- Returns `{}` if parsed YAML is not a dict.

**Missing files**: Handled. **Malformed frontmatter**: Handled. **Empty properties**: Returns `{}`, and all callers check for expected keys with `.get()` and default values. Good.

### _people_facts() (management_bridge.py:82-185)

- Missing `10-work/people/` directory: `if not people_dir.is_dir(): return []` (line 85-86). Good.
- Files without correct type/status: Skipped by `if fm.get("type") != "person" or fm.get("status") != "active": continue` (lines 97-98). Good.
- Missing `cognitive-load` property: `cog_load = fm.get("cognitive-load")` returns `None`, skipped by the `if cog_load is not None` check (line 110). Good.
- Non-integer cognitive-load: Caught by `except (ValueError, TypeError)` (line 113). Good.
- Missing `team` or `cadence`: `.get()` returns empty string, Counters handle empty strings (they just create a `""` key). Not ideal but not harmful.

### _coaching_facts() (management_bridge.py:188-222)

Uses `vault_path.rglob("*.md")` which scans the entire vault. Performance could be a concern with large vaults, but functionally correct. Handles zero coaching notes (returns `[]`).

### _feedback_facts() (management_bridge.py:225-266)

Same `rglob` pattern. Defaults `direction` to `"given"` (line 237), which is a silent assumption -- if the frontmatter has no direction property, the feedback is counted as given. This could miscount.

### _meeting_facts() (management_bridge.py:269-298)

Only scans `10-work/meetings/` (not rglob). Missing directory handled.

---

## Completeness Findings

### C-3.1: Six individual reader functions have no direct unit tests
**File:** `profiler_sources.py:238-377`
**Severity:** medium
**Finding:** `read_config_file()`, `read_shell_history()`, `read_git_info()`, `read_memory_file()`, `read_vault_inbox()`, and `read_management_notes()` have no dedicated unit tests. They are only exercised indirectly through integration-level tests (discovery tests, exclude tests). `read_drift_report()` also has no unit test.
**Impact:** Regressions in these simple readers would go undetected. Most are trivial wrappers around `_chunk_text()` (which is well-tested), but `read_shell_history()` and `read_git_info()` have meaningful logic.

### C-3.2: No tests for run_auto, run_extraction, run_curate, or run_ingest pipelines
**File:** `profiler.py:1480-1858`
**Severity:** medium
**Finding:** The main async pipelines (`run_auto`, `run_extraction`, `run_curate`, `run_ingest`) have zero test coverage. These are the primary entry points that orchestrate discovery, extraction, merging, synthesis, curation, digest generation, and Qdrant indexing.
**Impact:** Integration-level bugs (wrong argument passing, incorrect state flow between stages) would not be caught. The individual components are well-tested, but the orchestration wiring is untested.

### C-3.3: No tests for regenerate_operator() or _regenerate_operator_md()
**File:** `profiler.py:1127-1284`
**Severity:** medium
**Finding:** The operator manifest update pipeline (LLM-powered goal progress updates, pattern additions, neurocognitive updates) has no test coverage. `_regenerate_operator_md()` is a pure formatting function that could easily be tested deterministically.
**Impact:** Bugs in operator manifest regeneration (e.g., incorrect JSON path traversal, missed goal updates) would be undetected.

### C-3.4: No tests for store_to_qdrant() or store_to_mcp_memory()
**File:** `profiler.py:984-1047`
**Severity:** low
**Finding:** Neither the legacy Qdrant storage function (`store_to_qdrant()` which writes to `claude-memory` collection, distinct from `ProfileStore.index_profile()` which writes to `profile-facts`) nor the MCP memory output function has tests.
**Impact:** These appear to be deprecated/secondary paths. `store_to_qdrant()` writes to the old `claude-memory` collection while `ProfileStore.index_profile()` writes to the new `profile-facts` collection. The coexistence of both is confusing.

### C-3.5: Reader count mismatch -- 14 readers, not 16
**File:** `profiler_sources.py`
**Severity:** low
**Finding:** The design docs and CLAUDE.md reference "16 readers" in various places, but there are 14 distinct reader functions. The discrepancy likely counts the 3 bridged source types (takeout, proton, management) as having dual readers (text + structured), but their text readers are just wrappers around `_chunk_text()`.
**Impact:** Documentation inaccuracy, no functional impact.

### C-3.6: generate_digest() silently drops extra dimensions
**File:** `profiler.py:1066`
**Severity:** low
**Finding:** `generate_digest()` iterates only `PROFILE_DIMENSIONS` (the standard 13). The `build_profile()` function (lines 486-492) explicitly handles extra dimensions created by LLM extraction, but the digest generator ignores them. If the LLM creates facts in a dimension outside the standard 13, they will be in the profile but absent from the digest.
**Impact:** Extra dimensions (rare in practice) would have no digest summaries and would not be findable via `get_profile_summary()`.

---

## Correctness Findings

### R-3.1: Equal-confidence merge silently keeps existing fact
**File:** `profiler.py:319`
**Severity:** low
**Finding:** When two facts from the same source class have identical confidence, the existing fact wins. The `elif fact.confidence > existing_fact.confidence` check (strict greater-than) means equal confidence does not trigger replacement. This is a reasonable design choice but is not documented -- one might expect timestamp or source recency to break ties.
**Impact:** Newer facts at the same confidence level are silently dropped. In practice, this is unlikely to cause issues since LLM extraction rarely produces identical confidence values.

### R-3.2: Perplexity extraction prompt still present
**File:** `profiler.py:932-943`
**Severity:** low
**Finding:** `generate_extraction_prompts()` still generates a Perplexity prompt (line 932), but the MEMORY.md states "Perplexity removed: no official bulk export exists, dropped parser." The prompt is dead code.
**Impact:** Misleading output if operator runs `--generate-prompts`. No functional harm.

### R-3.3: flush_interview_facts rebuilds dimensions but drops non-standard dimensions
**File:** `profiler.py:665-681`
**Severity:** low
**Finding:** `flush_interview_facts()` rebuilds dimensions by iterating `PROFILE_DIMENSIONS` first (line 665), then adds extra dimensions (lines 675-681). However, line 667 uses `if dim_facts:` to filter, meaning standard dimensions with zero facts after the merge are dropped -- which also drops their existing summaries. This is inconsistent with `build_profile()` (line 478) which keeps dimensions that have summaries but no facts.
**Impact:** If a dimension had only a summary (no facts), `flush_interview_facts()` would drop it while `build_profile()` would keep it. Minor inconsistency.

### R-3.4: _feedback_facts defaults missing direction to "given"
**File:** `management_bridge.py:237`
**Severity:** low
**Finding:** `direction = fm.get("direction", "given")` defaults to "given" if the frontmatter lacks a `direction` property. Feedback records without explicit direction are silently counted as given, which could skew the direction ratio.
**Impact:** Incorrect `feedback_direction_ratio` fact if any feedback notes lack the `direction` property.

---

## Robustness Findings

### B-3.1: File-reading readers crash on I/O errors
**File:** `profiler_sources.py:238-377`
**Severity:** high
**Finding:** `read_config_file()`, `read_transcript()`, `read_memory_file()`, `read_llm_export()`, `read_takeout()`, `read_proton()`, `read_vault_inbox()`, and `read_management_notes()` call `path.read_text()` without any error handling. If a file has been deleted between discovery and reading, or has permission issues, the reader will raise an exception. The callers (`_read_capped()` and `read_all_sources()`) also lack error handling around individual reader calls.
**Impact:** A single unreadable file in any source type will crash the entire bulk read for that source type, potentially aborting the profiler run. For `run_auto()` (the timer-invoked path), this would cause the systemd service to fail.

### B-3.2: index_profile() has no error handling per batch
**File:** `profile_store.py:100-102`
**Severity:** medium
**Finding:** The batch upsert loop `self.client.upsert(COLLECTION, batch)` has no try/except. If Qdrant fails on the Nth batch, previously upserted batches are already committed while the remaining batches are lost. There is no retry logic.
**Impact:** Partial indexing. Mitigated by deterministic IDs (re-running overwrites), and by `run_auto()` wrapping the entire call in try/except (so the profile is still saved to disk even if indexing fails).

### B-3.3: _coaching_facts and _feedback_facts use rglob("*.md") on entire vault
**File:** `management_bridge.py:197, 232`
**Severity:** medium
**Finding:** `_coaching_facts()` and `_feedback_facts()` scan the entire vault recursively with `vault_path.rglob("*.md")`. For a vault with thousands of markdown files, this means every file is opened and its frontmatter parsed, even though coaching and feedback notes may be rare.
**Impact:** Performance degradation proportional to vault size. Every file is opened, read, and YAML-parsed. For the operator's vault this is likely acceptable (hundreds, not thousands of files), but it does not scale. Additionally, files in `60-archive/` or `90-attachments/` are unnecessarily scanned.

### B-3.4: Langfuse reader has no page limit / unbounded pagination
**File:** `profiler_sources.py:615-651`
**Severity:** low
**Finding:** Both the traces and observations fetch loops paginate until `len(all_traces) >= total`. For a busy system with thousands of traces in the lookback window, this could result in many API calls and significant memory usage. There is no upper bound on the total number of items fetched.
**Impact:** Slow profiler runs if Langfuse has a large trace volume. Memory pressure is possible but unlikely for typical workloads (30-day window).

### B-3.5: Early-stop race condition with concurrent extraction
**File:** `profiler.py:376-381, 411-415`
**Severity:** low
**Finding:** The early-stop check at line 376 (`if chunk.source_type in stopped_types`) happens before acquiring the semaphore, but there is a re-check after acquiring (line 381). The `stopped_types` set is mutated inside the `async with lock` block (line 415). Since all chunks for a source type are launched as tasks immediately (line 434), many chunks may already be queued when early-stop fires. The `concurrency` semaphore limits how many are in flight, but tasks already waiting on the semaphore will re-check and return early.
**Impact:** With high concurrency, a few extra chunks beyond the early-stop window may be processed. This is by design (noted in the code) and is harmless -- it just means early-stop is not perfectly precise.

### B-3.6: generate_digest creates a new Agent per dimension
**File:** `profiler.py:1083-1091`
**Severity:** low
**Finding:** Inside the loop over PROFILE_DIMENSIONS, a new `Agent` instance is created for every dimension (line 1083). Pydantic AI agents are lightweight but this is unnecessarily wasteful -- the same agent could be reused across dimensions since the system prompt is identical for all.
**Impact:** Minor overhead. 13 Agent instantiations per digest generation. No functional impact.

### B-3.7: No cleanup of stale points in profile-facts collection
**File:** `profile_store.py:56-105`
**Severity:** medium
**Finding:** `index_profile()` upserts points with deterministic IDs based on `(dimension, key)`. If a fact is deleted from the profile (e.g., via curation or corrections), its corresponding point in Qdrant remains. There is no mechanism to delete stale points. Over time, the `profile-facts` collection accumulates orphaned points for facts that no longer exist in the profile.
**Impact:** `search_profile()` could return results for deleted facts. The `knowledge_maint` agent handles general Qdrant hygiene, but there is no profile-specific cleanup.

---

## Test Coverage Assessment

### profiler.py (1,862 LOC)

| Component | Tested? | Test Location | Quality |
|-----------|---------|---------------|---------|
| ProfileFact schema | Yes | test_profiler.py | Good -- bounds, serialization |
| ChunkExtraction schema | Yes | test_profiler.py | Minimal -- empty + with facts |
| UserProfile serialization | Yes | test_profiler.py | Good -- round-trip |
| merge_facts() | Yes | test_profiler.py | Excellent -- 7 test cases covering all merge paths |
| group_facts_by_dimension() | Yes | test_profiler.py | Good |
| build_profile() | Yes | test_profiler.py | Good -- basic + version increment |
| extract_from_chunks() | Yes | test_profiler.py | Good -- concurrency, early-stop, error handling |
| synthesize_profile() | No | - | Not tested (LLM-dependent) |
| generate_digest() | Yes | test_profile_store.py | Good -- structure, file save |
| apply_curation() | Yes | test_profiler.py | Excellent -- all 4 actions + edge cases |
| apply_corrections() | Yes | test_profile_visibility.py | Good -- update, delete, authority |
| flush_interview_facts() | Yes | test_conversational_learning.py, test_interview.py | Good |
| load_structured_facts() | Yes | test_profiler.py + test_takeout_profiler_bridge.py | Good -- missing, corrupt, valid |
| load_existing_profile() | Indirect | Used in other tests | Not tested for corrupt JSON |
| run_auto() | No | - | **Gap** -- primary automated entry point |
| run_extraction() | No | - | **Gap** -- primary interactive entry point |
| run_curate() | No | - | **Gap** |
| regenerate_operator() | No | - | **Gap** |
| curate_profile() | No | - | **Gap** |
| store_to_qdrant() | No | - | Low priority (deprecated path) |
| store_to_mcp_memory() | No | - | Low priority (output only) |

### profiler_sources.py (958 LOC)

| Component | Tested? | Test Location | Quality |
|-----------|---------|---------------|---------|
| discover_sources() | Yes | test_profiler.py | Good -- config, rules, transcripts |
| list_source_ids() | Yes | test_profiler.py | Good |
| read_all_sources() | Yes | test_profiler.py | Good -- filter, exclude, cap |
| _chunk_text() | Yes | test_profiler.py | Good -- empty, short, long |
| _extract_text_content() | Yes | test_profiler.py | Good -- string, list, thinking |
| _compress_ranges() | Yes | test_profiler.py | Good |
| _sort_by_mtime() | Yes | test_profiler.py | Good -- including missing files |
| read_langfuse() | Yes | test_profiler.py | Good -- 4 test cases |
| read_pending_facts() | Yes | test_conversational_learning.py | Good -- 6 test cases |
| read_decisions_log() | Yes | test_decisions.py | Good -- 4 test cases |
| detect_changed_sources() | Yes | test_profiler.py | Good -- all-new, nothing-changed |
| save_state() / load_state() | Yes | test_profiler.py | Good |
| read_config_file() | No | - | Trivial wrapper |
| read_shell_history() | No | - | Has logic worth testing |
| read_git_info() | No | - | Has subprocess logic |
| read_drift_report() | No | - | Has JSON parsing logic |

### profile_store.py (178 LOC)

| Component | Tested? | Quality |
|-----------|---------|---------|
| ensure_collection() | Yes | Good -- create + skip |
| index_profile() | Yes | Good -- basic, empty, deterministic IDs, batching |
| search() | Yes | Good -- results, filter, empty |
| get_digest() | Yes | Good -- missing, valid, corrupt |
| get_dimension_summary() | Yes | Good -- found, missing dim, no digest |

### context_tools.py (162 LOC)

| Component | Tested? | Quality |
|-----------|---------|---------|
| get_context_tools() | Yes | Good -- count, names |
| lookup_constraints() | Yes | Good -- all, filtered, empty, multi |
| lookup_patterns() | Yes | Good -- all, filtered, empty |
| search_profile() | Yes | Good -- results, empty, dimension, error |
| get_profile_summary() | Yes | Good -- overall, dimension, missing dim, no digest |
| All tools async | Yes | Good -- explicit check |
| All tools have docstrings | Yes | Good -- length check |

### management_bridge.py (298 LOC)

| Component | Tested? | Quality |
|-----------|---------|---------|
| generate_facts() | Yes | Good -- full vault, empty vault |
| save_facts() | Yes | Good |
| _parse_frontmatter() | Yes | Good -- valid, missing, no frontmatter |
| _people_facts() | Yes | Good -- basic, empty, inactive, high load, confidence |
| _coaching_facts() | Yes | Good -- counts, empty |
| _feedback_facts() | Yes | Good -- direction, empty |
| _meeting_facts() | Yes | Good -- 1:1 count, missing dir |

---

## Summary

- **Completeness:** 6 findings (0 critical, 0 high, 3 medium, 3 low)
- **Correctness:** 4 findings (0 critical, 0 high, 0 medium, 4 low)
- **Robustness:** 7 findings (0 critical, 1 high, 3 medium, 3 low)

**Total: 17 findings** (0 critical, 1 high, 6 medium, 10 low)

### Key Concerns

1. **B-3.1 (high)**: File-reading readers crash on I/O errors. A single permission-denied or file-deleted-between-discovery-and-read will abort the profiler run. This is the only high-severity finding and has a simple fix: wrap reader calls in try/except within `_read_capped()`.

2. **C-3.2 (medium)**: No integration tests for the main pipeline entry points (`run_auto`, `run_extraction`, `run_curate`). The individual components are well-tested, but orchestration bugs would go undetected.

3. **B-3.7 (medium)**: Stale facts accumulate in the profile-facts Qdrant collection because `index_profile()` only upserts, never deletes. A `delete_absent_points()` pass after indexing would fix this.

4. **B-3.3 (medium)**: Vault-wide rglob in management bridge scans every markdown file for coaching/feedback notes. Should be scoped to specific directories.

### Overall Assessment

The operator profile system is architecturally sound with well-defined merge semantics, authority hierarchy, and graceful degradation at the context-tools layer. The 14 readers cover a comprehensive range of data sources. Test coverage for the core logic (merging, curation, schema validation) is excellent. The main gaps are: no integration tests for pipeline orchestration, and insufficient error handling in file-reading readers. The confidence scoring system is consistent but undocumented.
