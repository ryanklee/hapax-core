# Domain 2: Data Ingestion — Audit v2 Findings

**Audited:** 2026-03-03
**Auditor:** Claude Code (v2 full re-read)
**Prior findings (v1):** 23 (8 completeness, 8 correctness, 7 robustness)
**Fixes to verify:** 24, 25, 26, 55, 56, 57, 62, 78, 79, 80, 84, 86

---

## Inventory

### Takeout Core

| File | v2 LOC | Test File | Test LOC |
|------|--------|-----------|----------|
| `shared/takeout/models.py` | 54 | `tests/test_takeout_models.py` | 439 |
| `shared/takeout/registry.py` | 156 | (indirect via test_takeout_models) | — |
| `shared/takeout/processor.py` | 476 | `tests/test_takeout_processor.py` | 458 |
| `shared/takeout/progress.py` | 168 | (indirect via test_takeout_processor) | — |
| `shared/takeout/chunker.py` | 145 | (indirect via test_takeout_parsers) | — |
| `shared/takeout/profiler_bridge.py` | 346 | `tests/test_takeout_profiler_bridge.py` | 449 |

### Takeout Parsers

| File | v2 LOC | Notes |
|------|--------|-------|
| `shared/takeout/parsers/activity.py` | 216 | Search, YouTube watch, Gemini (shared parser) |
| `shared/takeout/parsers/calendar.py` | 206 | |
| `shared/takeout/parsers/chat.py` | 184 | |
| `shared/takeout/parsers/chrome.py` | 178 | |
| `shared/takeout/parsers/contacts.py` | 195 | |
| `shared/takeout/parsers/drive.py` | 166 | |
| `shared/takeout/parsers/gmail.py` | 189 | |
| `shared/takeout/parsers/keep.py` | 141 | |
| `shared/takeout/parsers/location.py` | 318 | |
| `shared/takeout/parsers/photos.py` | 145 | |
| `shared/takeout/parsers/purchases.py` | 193 | |
| `shared/takeout/parsers/tasks.py` | 133 | |

All parsers tested collectively in `tests/test_takeout_parsers.py` (830 LOC, 44 tests).

### Proton Mail

| File | v2 LOC | Test File | Test LOC |
|------|--------|-----------|----------|
| `shared/proton/parser.py` | 205 | `tests/test_proton.py` | 434 |
| `shared/proton/processor.py` | 213 | (indirect via test_proton) | — |
| `shared/proton/labels.py` | 97 | (indirect via test_proton) | — |

### Other Ingestion

| File | v2 LOC | Test File | Test LOC |
|------|--------|-----------|----------|
| `shared/llm_export_converter.py` | 386 | `tests/test_llm_export_converter.py` | 557 |
| `rag-pipeline/ingest.py` | 591 | `rag-pipeline/tests/test_ingest.py` | 522 |

**Total source:** 5,106 LOC (all new since v1 — entire domain was planned but unimplemented at v1 audit time)
**Total test:** 3,689 LOC (278 tests)
**Test:source ratio:** 0.72

---

## Fix Verification

### Fix 24: Takeout JSONL dedup on resume — VERIFIED
**v1 finding:** R-2.1 (medium)
**Status:** ✅ Complete and correct.
`processor.py:54-98` — `_purge_service_from_jsonl()` removes all records for a service before re-processing on resume. Uses atomic write: `tempfile.mkstemp()` + `Path(tmp_path).replace(structured_path)` with `try/except` cleanup. Dedup is by `record.get("service") == service_name` in the JSONL, which is correct since `NormalizedRecord.service` is always set by parsers.
**Quality note:** Clean atomic implementation. The only gap: if the process crashes between purge and re-processing, records are lost. This is acceptable — resume will re-parse them from the ZIP.

### Fix 25: RAG ingest dedup tracking — VERIFIED
**v1 finding:** C-2.1 (medium)
**Status:** ✅ Complete and correct.
`ingest.py` uses `<cache>/rag-ingest/processed.json` as a dedup tracker. On startup, loads existing hashes. On each file ingest, checks content hash before embedding. Writes updated tracker to disk after each file. 52 tests in `test_ingest.py` cover the tracker (including corruption recovery).
**Quality note:** The tracker file is written after each single file — not atomic write but acceptable since it's a cache that can be rebuilt.

### Fix 26: RAG ingest tests — VERIFIED
**v1 finding:** C-2.3 (high)
**Status:** ✅ Complete and correct.
`rag-pipeline/tests/test_ingest.py` (522 LOC, 52 tests). Covers: file watching, YAML frontmatter parsing, enrichment, retry queue, dedup tracker, batch embedding, error paths.
**Quality note:** Thorough test suite for a critical pipeline component.

### Fix 55: Gemini parser validation — PARTIALLY APPLIED
**v1 finding:** C-2.7 (low)
**Status:** ⚠️ Partial. There is no dedicated Gemini parser — the registry maps `gemini` to the shared `activity` parser with `experimental=True`. The processor emits a warning log at line 187 when processing experimental services. No validation against real Gemini Takeout data has been done (the registry comment acknowledges the format is speculative: "My Activity/Gemini Apps" path). The `experimental` flag provides user warning but no functional safeguard (no dry-run enforcement, no separate error handling).
**Impact:** Low. The activity parser is generic enough to handle most HTML-based activity formats. Worst case on mismatched format: zero records emitted with a warning.

### Fix 56: Location history memory guard — PARTIALLY APPLIED
**v1 finding:** B-2.1 (medium)
**Status:** ⚠️ Partial. `location.py:220-245` adds `LARGE_FILE_THRESHOLD = 200MB` and logs a warning when `Records.json` exceeds this. However, the file is still loaded entirely into memory via `zf.read(path)` + `json.loads(raw)`. The fix plan suggested streaming or sampling for large files. What was implemented: a warning before the potentially problematic load.
**Impact:** Medium for large exports. A 500MB Records.json will trigger the warning but still attempt to load into memory, potentially causing OOM. The mitigation is that Semantic Location History (preferred path) doesn't have this issue — only the legacy `Records.json` fallback does.

### Fix 57: YAML frontmatter escaping — VERIFIED WITH CAVEAT
**v1 finding:** R-2.3 (medium)
**Status:** ✅ Mostly correct. `chunker.py:23-31` — `_yaml_list()` checks for special YAML characters (`, : [ ] { } & * # ! | " '`) and wraps affected items in double quotes.
**Caveat:** Items containing a literal double-quote character (`"`) are wrapped in double-quotes without escaping the internal quote. E.g., `she said "hello"` becomes `"she said "hello""`, which is invalid YAML. This is unlikely in practice for the fields that use `_yaml_list()` (people names, category labels) but is a correctness gap.

### Fix 62: Profiler bridge streaming / memory — VERIFIED
**v1 finding:** B-2.5 (medium)
**Status:** ✅ Complete and correct.
`profiler_bridge.py` uses `_ServiceAccumulators` class with bounded `Counter` objects. Chrome domain counts, search queries, and YouTube channels are accumulated incrementally. Memory is O(unique_values), not O(total_records). The `Counter.most_common()` calls produce bounded output.
**Quality note:** Clean design. The accumulators pattern is the right approach for processing large structured JSONL files.

### Fix 78: Chrome timestamp timezone — VERIFIED
**v1 finding:** R-2.6 (medium)
**Status:** ✅ Complete and correct.
`chrome.py:176` — `_chrome_time_to_datetime()` now passes `tz=timezone.utc` to `datetime.fromtimestamp()`. Chrome timestamps are in microseconds since 1601-01-01 UTC; the conversion correctly adjusts the epoch offset and applies UTC timezone.

### Fix 79: Proton records_skipped count — NOT PROPERLY FIXED
**v1 finding:** R-2.7 (low)
**Status:** ❌ Still broken. `proton/processor.py:125` computes `skipped = max(0, result.total_files - count - len(result.errors))`. This is a residual calculation, not an actual count of date-filtered records. It conflates spam filtering, trash filtering, `is_automated()` filtering, and date filtering into a single number. Contrast with `takeout/processor.py:213` where `skipped += 1` is incremented only for date-filtered records.
**Impact:** Low. The `skipped` count is only used in CLI output and progress tracking, not in any downstream logic. But it gives the operator misleading information — e.g., "Skipped 15,000 emails" when most were spam/trash, not date-filtered.

### Fix 80: Progress tracker atomic write — VERIFIED
**v1 finding:** B-2.3 (medium)
**Status:** ✅ Complete and correct.
`progress.py:85-104` — `_save()` now uses `tempfile.mkstemp()` + `json.dump()` to temp file + `os.replace(tmp_path, self._path)` with `try/except` cleanup that unlinks the temp file on failure. Consistent with the atomic write pattern used in `_purge_service_from_jsonl()`.

### Fix 84: VCF line folding — VERIFIED
**v1 finding:** R-2.9 (low)
**Status:** ✅ Complete and correct.
`contacts.py` applies `re.sub(r'\r?\n[ \t]', '', text)` to unfold RFC 6350 continuation lines before parsing. This handles the case where a long field value is split across multiple lines with leading whitespace.

### Fix 86: RAG frontmatter enrichment — VERIFIED
**v1 finding:** C-2.8 (low)
**Status:** ✅ Complete and correct.
`ingest.py` now parses YAML frontmatter from markdown files and enriches the Qdrant payload with: `content_type`, `source_service`, `modality_tags`, `people`, `timestamp`, `record_id`, `categories`, `location`. The enrichment whitelist ensures only known-safe fields propagate to Qdrant metadata.

---

## Completeness Findings

### C2-2.1: No dedicated parser for Gemini — reuses generic `activity` parser
**File:** `shared/takeout/registry.py:122-130`
**Severity:** low
**Finding:** Gemini is mapped to the `activity` parser with `experimental=True`. The `activity` parser handles HTML-based "My Activity" format generically. The actual Gemini Takeout format is speculative — Google may export Gemini conversations differently (JSON conversation objects vs. HTML activity entries). The experimental flag provides a warning but no structural protection.
**Impact:** Low. If the format assumption is wrong, zero records are extracted (parser returns empty iterator). No data corruption risk.

### C2-2.2: No parser for Google Photos metadata
**File:** `shared/takeout/parsers/photos.py` (145 LOC)
**Severity:** low
**Finding:** The photos parser extracts basic metadata (filename, description, creation date, geo-coordinates) from the JSON sidecar files. It does not extract: camera settings (EXIF), album membership, sharing status, face labels, or editing history — all of which are available in some Takeout exports.
**Impact:** Low for operator profile. EXIF data is photography-specific and less relevant to behavioral profiling. Album/sharing structure could inform social patterns but is a stretch.

### C2-2.3: Proton processor has no `--resume` support
**File:** `shared/proton/processor.py`
**Severity:** low
**Finding:** Unlike the Takeout processor which has full resume support via `ProgressTracker` + `_purge_service_from_jsonl()`, the Proton processor has no resume capability. It records progress to `ProgressTracker` for display but doesn't check `is_completed()` on restart. Re-running processes all 41K+ emails from scratch.
**Impact:** Low-medium. For the operator's 41K-email export, a full re-run takes several minutes. Not catastrophic but wasteful.

### C2-2.4: `embed_batch()` not used by Proton profiler bridge
**File:** `shared/takeout/profiler_bridge.py` vs `shared/proton/processor.py`
**Severity:** low
**Finding:** The Takeout profiler bridge processes structured facts in a single pass via `generate_facts()`. The Proton profiler bridge (`_proton_mail_facts()` in `profiler_bridge.py`) similarly produces `ProfileFact` dicts deterministically. However, neither actually calls `embed_batch()` — facts are saved as JSON and loaded by the profiler's auto mode. The embedding happens later in the profiler's Qdrant indexing. This is correct design (separation of concerns) but worth noting that the profiler bridge is zero-embedding, which is its key performance property.
**Impact:** None — this is a non-issue, noted for documentation accuracy.

---

## Correctness Findings

### R2-2.1: Processor `services_processed` includes failed services
**File:** `shared/takeout/processor.py:242`
**Severity:** medium
**Finding:** `result.services_processed.append(svc_name)` at line 242 runs unconditionally for all services that had their parser loaded, regardless of whether processing succeeded or failed mid-way. Only parser-load failures (line 201) use `continue` to skip this. A service that processes 50 records then crashes on record 51 appears in `services_processed` alongside its partial `count` in `records_written`. The CLI output then reports misleading totals.
**Impact:** Medium. The `services_processed` list is used in CLI output and batch result aggregation. Misleading counts could cause the operator to believe a service was fully processed when it partially failed. Progress tracker correctly distinguishes (calls `fail_service()` on error) but `ProcessResult` doesn't.
**Operator impact:** Operator could miss partial failures in CLI output, though progress tracker (`--progress`) shows the accurate picture.

### R2-2.2: Proton `records_skipped` is a residual, not an actual count
**File:** `shared/proton/processor.py:125`
**Severity:** low
**Finding:** (Same as Fix 79 verification above.) `skipped = max(0, result.total_files - count - len(result.errors))` conflates all non-written records into one number. The operator sees "Skipped 15,000 emails" without knowing how many were spam vs. date-filtered vs. automated.
**Impact:** Low. Informational only — no downstream logic depends on this.

### R2-2.3: `_yaml_list()` doesn't escape embedded double-quotes
**File:** `shared/takeout/chunker.py:23-31`
**Severity:** low
**Finding:** (Same as Fix 57 caveat above.) Items containing `"` are wrapped in unescaped `"..."`, producing invalid YAML. The fix should either escape internal quotes as `\"` or use single-quote wrapping for items containing double-quotes.
**Impact:** Low. Fields using `_yaml_list()` are people names and category labels, which rarely contain double-quotes. If triggered, the RAG ingest frontmatter parser would fail on that file and it would enter the retry queue (then fail again permanently).

### R2-2.4: Location parser `_parse_location_time()` strips timezone info
**File:** `shared/takeout/parsers/location.py:316`
**Severity:** low
**Finding:** The ISO fallback path at line 316 does `datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)`. This correctly parses the timezone then immediately strips it. The earlier `strptime` paths (lines 297-304) also produce naive datetimes. Chrome parser (Fix 78) correctly preserves UTC. The location parser discards it.
**Impact:** Low. Location timestamps are used for date-based aggregation (by day) and record ordering. The timezone stripping means all timestamps are treated as UTC implicitly, which is correct for Google's data but not explicit. No functional bug since all records from the same export are consistently naive-UTC.

### R2-2.5: Gmail parser `_parse_date()` falls back to epoch
**File:** `shared/takeout/parsers/gmail.py`
**Severity:** low
**Finding:** The gmail parser's date parsing falls back to `datetime(1970, 1, 1)` for unparseable dates. This means malformed email dates don't cause crashes but produce records dated to epoch, which will sort incorrectly and may bypass date filters (appearing very old). The profiler bridge would treat these as ancient emails.
**Impact:** Low. Automated emails (most likely to have unusual date formats) are already filtered by `is_automated()`. Manual emails from legitimate senders rarely have malformed dates.

---

## Robustness Findings

### B2-2.1: Location `Records.json` still loaded entirely into memory
**File:** `shared/takeout/parsers/location.py:247-249`
**Severity:** medium
**Finding:** (Same as Fix 56 verification above.) Despite the 200MB threshold warning, `zf.read(path)` + `json.loads(raw)` loads the entire file. For a heavy location user, `Records.json` can be 500MB-1GB. On a 24GB VRAM / limited system RAM machine, this could cause OOM or severe swap pressure.
**Mitigating factor:** The parser prefers Semantic Location History when available (line 51), and modern Takeout exports provide it. `Records.json` is the legacy fallback.
**Impact:** Medium for large exports. Workaround: split the Takeout export or ensure sufficient RAM.
**Operator impact:** The operator's export likely has Semantic Location History (modern account), so the legacy path may never trigger. But if it does, no graceful degradation.

### B2-2.2: No rate limiting on Qdrant writes during RAG ingest
**File:** `rag-pipeline/ingest.py`
**Severity:** low
**Finding:** The RAG ingest pipeline processes files serially (watchdog callback + retry queue), which provides natural rate limiting. However, during initial bulk ingest (e.g., Takeout → markdown → rag-sources), hundreds of files can arrive simultaneously. The watchdog fires on each file creation. Qdrant accepts all writes but embedding calls hit Ollama, which processes them sequentially.
**Impact:** Low. Ollama's sequential processing is the natural bottleneck. No Qdrant overload risk. The main concern is Ollama VRAM thrashing if a large model is loaded during bulk ingest, but `embed_batch()` uses the embedding model which coexists with larger models.

### B2-2.3: LLM export converter Gemini parser written speculatively
**File:** `shared/llm_export_converter.py`
**Severity:** low
**Finding:** The Gemini parser was written based on an assumed JSON-per-conversation format. The actual Takeout format may be `My Activity/Gemini Apps/My Activity.html` (an HTML activity log). The converter's Gemini parsing would fail silently (no matching files found in ZIP) or produce empty output.
**Impact:** Low. Claude.ai export parsing works correctly (operator has validated). Gemini parsing is untested against real data and may need rewriting when actual data is available. No data corruption risk — just zero output.

### B2-2.4: Takeout progress tracker doesn't handle concurrent runs
**File:** `shared/takeout/progress.py`
**Severity:** low
**Finding:** `ProgressTracker` uses file-based JSONL. Two concurrent `process_takeout()` calls on different ZIPs would interleave progress records. The `_run_id()` differentiates by ZIP path+size, so reads would filter correctly, but the JSONL file could grow unboundedly with interleaved entries. In practice, the CLI processes ZIPs sequentially in `process_batch()`.
**Impact:** Low. No concurrent usage path exists in current code.

### B2-2.5: Gmail MBOX temp file not cleaned up on crash
**File:** `shared/takeout/parsers/gmail.py`
**Severity:** low
**Finding:** The gmail parser extracts MBOX data to a temp file for `mailbox.mbox()` processing. The temp file is cleaned up in a `finally` block. If the process is killed (SIGKILL, OOM), the temp file remains in `/tmp`. For a large MBOX (operator's 41K emails), this could be hundreds of MB lingering in `/tmp`.
**Impact:** Low. `/tmp` is cleaned on reboot. The temp file is in the system temp directory, not a user-controlled path. Normal shutdown (SIGTERM, Ctrl+C) triggers the `finally` cleanup.

---

## Test Coverage Assessment

| Area | Tests | LOC | Assessment |
|------|-------|-----|------------|
| Takeout models + registry | 47 | 439 | **well tested** — NormalizedRecord, ServiceConfig, modality_tags, record_id |
| Takeout parsers | 44 | 830 | **adequately tested** — all 12 parsers have at least basic coverage. Edge cases (malformed data, empty inputs) tested for most parsers |
| Takeout processor | 24 | 458 | **adequately tested** — resume, progress, batch, dry-run. Missing: partial failure case (R2-2.1) |
| Takeout profiler bridge | 29 | 449 | **well tested** — all fact types, accumulator bounds, empty input |
| Proton | 45 | 434 | **well tested** — labels, email_utils, parser, processor. Missing: resume |
| LLM export converter | 37 | 557 | **well tested** — Claude + Gemini formats, escaping, edge cases |
| RAG ingest | 52 | 522 | **well tested** — dedup, retry, enrichment, error paths |

**Overall:** 278 tests, 3,689 LOC. Good coverage for a greenfield domain. The main gap is the partial-failure path in `processor.py` (R2-2.1).

---

## Summary

### Fix Verification Scorecard

| Fix | Status | Quality |
|-----|--------|---------|
| 24 (JSONL dedup on resume) | ✅ Complete | Good: atomic write, correct dedup key |
| 25 (RAG ingest dedup tracking) | ✅ Complete | Good: hash-based, corruption-resilient |
| 26 (RAG ingest tests) | ✅ Complete | Good: 52 tests, comprehensive |
| 55 (Gemini validation) | ⚠️ Partial | Warning log only, no functional safeguard |
| 56 (Location memory guard) | ⚠️ Partial | Warning added but file still loaded in full |
| 57 (YAML escaping) | ✅ Complete (with caveat) | Works for realistic data, fails on embedded `"` |
| 62 (Profiler bridge memory) | ✅ Complete | Good: O(unique) accumulator design |
| 78 (Chrome timezone) | ✅ Complete | Good: `tz=timezone.utc` correctly applied |
| 79 (Proton records_skipped) | ❌ Not fixed | Residual calculation, not actual skip count |
| 80 (Progress atomic write) | ✅ Complete | Good: tempfile + os.replace pattern |
| 84 (VCF line folding) | ✅ Complete | Good: RFC 6350 compliant |
| 86 (Frontmatter enrichment) | ✅ Complete | Good: whitelist-based field propagation |

**8 of 12 fixes fully verified. 2 partial (55, 56). 1 with caveat (57). 1 not fixed (79).**

### New Findings

| ID | Severity | Category | Summary |
|----|----------|----------|---------|
| C2-2.1 | low | completeness | No dedicated Gemini parser — shares generic activity parser |
| C2-2.2 | low | completeness | Photos parser extracts minimal metadata |
| C2-2.3 | low | completeness | Proton processor has no `--resume` support |
| C2-2.4 | low | completeness | (Non-issue) Profiler bridge is correctly zero-embedding |
| R2-2.1 | **medium** | correctness | Processor `services_processed` includes partially-failed services |
| R2-2.2 | low | correctness | Proton `records_skipped` is residual, not actual count |
| R2-2.3 | low | correctness | `_yaml_list()` doesn't escape embedded double-quotes |
| R2-2.4 | low | correctness | Location parser strips timezone info |
| R2-2.5 | low | correctness | Gmail parser falls back to epoch on bad dates |
| B2-2.1 | **medium** | robustness | Location `Records.json` still loaded entirely into memory |
| B2-2.2 | low | robustness | No rate limiting on bulk RAG ingest (mitigated by Ollama bottleneck) |
| B2-2.3 | low | robustness | Gemini LLM export parser written speculatively |
| B2-2.4 | low | robustness | Progress tracker doesn't handle concurrent runs |
| B2-2.5 | low | robustness | Gmail MBOX temp file not cleaned up on crash |

### Overall Assessment

The data ingestion domain is entirely new since v1 — 5,106 LOC of source with 3,689 LOC of tests (278 tests), all written during the v1 fix session. For a greenfield domain built in a single session, the quality is remarkably good:

- **Architecture is sound.** The dual-path design (structured → deterministic facts, unstructured → RAG + LLM extraction) is well-conceived. `NormalizedRecord` provides a clean intermediate representation. The profiler bridge's zero-LLM approach for structured data is both economical and reliable.

- **Atomic writes are consistent.** Both `_purge_service_from_jsonl()` and `ProgressTracker._save()` use the same tempfile + os.replace pattern. This is the right approach and correctly applied.

- **Parser coverage is comprehensive.** 12 Takeout parsers + Proton mail + LLM export converter. All parsers follow the same contract (`parse(zf, config) -> Iterator[NormalizedRecord]`). The shared `email_utils.py` extraction prevents duplication between Gmail and Proton.

- **Two medium findings.** R2-2.1 (processor reporting partial failures as successes) is a real bug that could mislead the operator. B2-2.1 (location memory) is a known limitation with a partial mitigation (warning log) and architectural mitigation (semantic history preferred).

- **One unfixed item.** Fix 79 (Proton records_skipped) was not properly addressed — it's still a residual calculation. Low impact but represents a gap between fix intent and implementation.

**Fix quality assessment:** The bulk of D2 code was written during the v1 fix session as new functionality, not as patches. The code is well-structured, follows consistent patterns, and has good test coverage. The partial fixes (55, 56) appear to be conscious scope reductions rather than oversights. Fix 79 appears to have been overlooked or deemed not worth the refactor to thread an explicit skip counter through the parser.

**Operator impact:** The ingestion pipeline serves the operator well. Google Takeout processing is robust with resume support, progress tracking, and dual-path output. Proton mail processing handles the operator's 41K-email export. The main operator-facing gap is R2-2.1 — misleading CLI output on partial failures could cause the operator to trust incomplete data.
