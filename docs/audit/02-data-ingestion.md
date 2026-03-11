# Domain 2: Data Ingestion — Audit Findings

## Inventory

| File | LOC | Test File | Test LOC |
|------|-----|-----------|----------|
| `shared/takeout/processor.py` | 418 | `test_takeout_processor.py` (partial) + `test_takeout_parsers.py` (partial) | ~155 |
| `shared/takeout/progress.py` | 159 | `test_takeout_processor.py:260-318` | ~58 |
| `shared/takeout/chunker.py` | 136 | `test_takeout_models.py:176-357` | ~181 |
| `shared/takeout/models.py` | 53 | `test_takeout_models.py:24-103` | ~79 |
| `shared/takeout/registry.py` | 156 | `test_takeout_models.py:107-174` | ~67 |
| `shared/takeout/profiler_bridge.py` | 408 | `test_takeout_profiler_bridge.py` | 449 |
| `shared/takeout/parsers/chrome.py` | 178 | `test_takeout_parsers.py:133-202` | ~69 |
| `shared/takeout/parsers/calendar.py` | 206 | `test_takeout_parsers.py:285-378` | ~93 |
| `shared/takeout/parsers/activity.py` | 216 | `test_takeout_parsers.py:30-131` | ~101 |
| `shared/takeout/parsers/chat.py` | 184 | `test_takeout_parsers.py:632-692` | ~60 |
| `shared/takeout/parsers/contacts.py` | 191 | `test_takeout_parsers.py:380-453` | ~73 |
| `shared/takeout/parsers/drive.py` | 166 | `test_takeout_parsers.py:583-630` | ~47 |
| `shared/takeout/parsers/gmail.py` | 177 | `test_takeout_parsers.py:516-581` | ~65 |
| `shared/takeout/parsers/keep.py` | 141 | `test_takeout_parsers.py:204-283` | ~79 |
| `shared/takeout/parsers/location.py` | 300 | `test_takeout_processor.py:36-153` | ~117 |
| `shared/takeout/parsers/photos.py` | 145 | `test_takeout_processor.py:156-211` | ~55 |
| `shared/takeout/parsers/purchases.py` | 193 | `test_takeout_processor.py:213-258` | ~45 |
| `shared/takeout/parsers/tasks.py` | 133 | `test_takeout_parsers.py:455-514` | ~59 |
| `shared/proton/parser.py` | 205 | `test_proton.py:203-299` | ~96 |
| `shared/proton/processor.py` | 207 | `test_proton.py:302-434` | ~132 |
| `shared/proton/labels.py` | 97 | `test_proton.py:106-155` | ~49 |
| `shared/email_utils.py` | 109 | `test_proton.py:158-201` | ~43 |
| `shared/llm_export_converter.py` | 386 | `test_llm_export_converter.py` | 557 |
| `rag-pipeline/ingest.py` | 525 | `test_takeout_profiler_bridge.py:292-393` (replicated logic) | ~101 |
| `rag-pipeline/query.py` | 120 | (none) | 0 |

**Total:** ~5,258 source LOC, ~3,051 test LOC

---

## Completeness Findings

### C-2.1: Gemini parser is speculative — untested against real data
**File:** `shared/takeout/parsers/activity.py` (used via `registry.py:122-129`)
**Severity:** medium
**Finding:** The Gemini service entry in the registry routes to the generic `activity.py` parser with `takeout_path="My Activity/Gemini Apps"`. The activity parser assumes one of two formats: a JSON array of `{title, time, subtitles}` objects, or HTML `content-cell` divs. The CLAUDE.md project memory explicitly notes: "Gemini parser caveat: written speculatively (JSON-per-conversation assumption). Real Takeout format may be `My Activity/Gemini Apps/My Activity.html`. Needs validation against real export." The test suite has zero Gemini-specific tests — only generic activity parser tests with Search and YouTube configs.
**Impact:** The Gemini parser may silently produce zero records or incorrectly parsed records when run against a real Google Takeout. Because the activity parser's HTML fallback is basic regex extraction (`activity.py:145-185`), if the real format differs from either expected pattern, data will be lost silently (no error, just no records).

### C-2.2: No tests for rag-pipeline/ingest.py or query.py
**File:** `rag-pipeline/ingest.py`, `rag-pipeline/query.py`
**Severity:** medium
**Finding:** The RAG pipeline has zero test files. The test file `test_takeout_profiler_bridge.py:292-393` contains replicated copies of `parse_frontmatter` and `enrich_payload` functions to test them without importing the real module (documented reason: different dependencies). This means the actual `ingest.py` functions are never unit-tested — only logic-identical copies. The retry queue, watchdog handler, bulk_ingest, and Qdrant interaction logic are completely untested.
**Impact:** Any regression in ingest.py would not be caught. The retry queue, backoff schedule, and frontmatter parsing are critical paths used daily by the always-running rag-ingest.service.

### C-2.3: No test for VCF continuation lines in contacts parser
**File:** `shared/takeout/parsers/contacts.py:160-191`
**Severity:** low
**Finding:** The `_extract_vcard_fields` function does not handle RFC 6350 line folding (continuation lines starting with space/tab). Unlike the calendar parser (`calendar.py:156` — `re.sub(r"\r?\n[ \t]", "", event_text)`), the contacts parser splits on raw newlines. If a vCard field is folded across lines, it will be silently truncated.
**Impact:** Long field values (addresses, notes) in vCard exports may be split mid-value. Low severity because most modern Google Contacts exports use short-enough lines that folding is rare.

### C-2.4: Location parser raw Records.json loads entire file into memory
**File:** `shared/takeout/parsers/location.py:220-270`
**Severity:** medium
**Finding:** `_parse_raw_records` calls `zf.read(path)` then `json.loads(raw)` which loads the entire Records.json into memory. Google Location History Records.json can be hundreds of megabytes to several gigabytes for users with years of location history. This contradicts the streaming design philosophy applied elsewhere (e.g., Gmail MBOX uses temp file streaming at `gmail.py:68-83`).
**Impact:** On a large Records.json (e.g., 2GB+), this will cause excessive memory usage and potential OOM. The semantic location history parser also loads full files, but those are monthly (~1-10MB each), so the risk is lower.

### C-2.5: Proton processor records_skipped never incremented
**File:** `shared/proton/processor.py:99,126,129`
**Severity:** low
**Finding:** The `skipped` counter is initialized to 0 at line 99 but is never incremented anywhere in `process_export`. The `since` date filtering is handled inside `parse_export` (parser.py:106-108) which just returns `None` for filtered records — the processor never sees them. So `result.records_skipped` is always 0 even when emails are filtered by date. By contrast, the takeout processor correctly counts skipped records (`processor.py:155-156`).
**Impact:** Misleading summary output when using `--since` with Proton exports. Users see "Records skipped: 0" even though records were filtered.

---

## Correctness Findings

### R-2.1: profiler_bridge.py loads all records into memory despite "streaming" comment
**File:** `shared/takeout/profiler_bridge.py:47-66`
**Severity:** medium
**Finding:** The docstring says "Streams the JSONL line-by-line to avoid loading the entire file into memory" but the function builds `by_service: defaultdict[str, list[dict]]` which accumulates ALL records into lists grouped by service (line 52, 65). For a 500K-record Takeout export, this is effectively loading everything into memory. The line-by-line reading only avoids loading the raw JSON text all at once, but the parsed dicts are all retained.
**Impact:** Memory pressure on large exports. For a 500K record structured JSONL, all records are held in memory simultaneously as Python dicts. Could be mitigated by computing aggregates incrementally (counters, not lists) for services like Chrome and Search that only need aggregate statistics.

### R-2.2: YAML frontmatter generation doesn't escape special characters
**File:** `shared/takeout/chunker.py:23-65`
**Severity:** medium
**Finding:** The `record_to_markdown` function writes YAML frontmatter values without escaping. Specifically:
- `record.title` is placed in a markdown heading (line 57) — safe.
- `record.location` is quoted (line 47) — partially safe.
- `record.people` items are written as bare comma-separated values inside `[]` (line 43-44). If a person's name or email contains a comma, the list will be incorrectly parsed.
- `modality_tags` has the same issue (line 39-40) though tag values are controlled vocabulary.
- `record_id` is written bare (line 33) — could theoretically contain YAML-special characters if the hashing changes.

The downstream consumer `ingest.py:267-303` (`parse_frontmatter`) uses naive `line.partition(":")` splitting, so a value containing a colon would be partially consumed. Example: a timestamp like `timestamp: 2025-06-15T10:30:00` would parse `value = "2025-06-15T10"` then fail to match the list pattern. However, looking more closely, `partition(":")` returns everything after the first colon, so `value = " 2025-06-15T10:30:00"` — which is actually correct after stripping.

The real risk is in people/tags: `people: [Alice, Bob <alice@example.com>]` would parse as `["Alice", "Bob <alice@example.com>"]` which drops the comma in "Alice, Bob". But email addresses don't normally contain commas, so practical risk is low.
**Impact:** Edge cases with special characters in people names or locations could produce unparseable YAML frontmatter, breaking the RAG enrichment chain. Probability is low but non-zero.

### R-2.3: Chrome time_usec conversion uses naive datetime
**File:** `shared/takeout/parsers/chrome.py:167-178`
**Severity:** low
**Finding:** `_chrome_time_to_datetime` converts Chrome's Windows epoch (microseconds since 1601-01-01 UTC) using `datetime.fromtimestamp(unix_seconds)` which returns a local-time datetime, not UTC. All other parsers also use naive datetimes but from formats that are explicitly UTC (trailing Z). This means Chrome timestamps will be offset by the local timezone when compared against `--since` filters or when stored.
**Impact:** Minor timestamp inconsistency. Affects date filtering accuracy by the local timezone offset (e.g., UTC-7 for Pacific). Not data loss, but dates could be off by hours when comparing across services.

### R-2.4: Bookmark timestamps also use local time
**File:** `shared/takeout/parsers/chrome.py:146-148`
**Severity:** low
**Finding:** `datetime.fromtimestamp(int(add_date))` for bookmark ADD_DATE uses local time. The ADD_DATE in Netscape bookmark format is a Unix timestamp (seconds since epoch, UTC). Same issue as R-2.3.
**Impact:** Same as R-2.3 — minor timezone inconsistency.

### R-2.5: process_takeout error detection heuristic is fragile
**File:** `shared/takeout/processor.py:178`
**Severity:** medium
**Finding:** Line 178 checks whether a service had errors using:
```python
if svc_name not in [e.split(":")[0] for e in result.errors if e.startswith(f"Error processing {svc_name}")]
```
This is a string-matching heuristic on the error list to decide whether to call `tracker.complete_service`. The logic is: "if there's no error message starting with 'Error processing {svc_name}:', then mark as completed." However, the error messages at line 172 are formatted as `f"Error processing {svc_name}: {e}"`, so `e.split(":")[0]` would return `"Error processing chrome"` which is compared against just `"chrome"`. The comparison `svc_name not in [...]` would check if `"chrome"` is in `["Error processing chrome"]`, which is False. So it always marks the service as completed even when there was an error.

Wait — re-reading: `e.startswith(f"Error processing {svc_name}")` filters to only errors for this service. Then `e.split(":")[0]` produces `"Error processing chrome"`. Then it checks `svc_name not in [...]` = `"chrome" not in ["Error processing chrome"]`, which is True (substring match != list membership). So the service IS marked as completed even after an error.

Actually, looking more carefully: the error is already appended at line 174, and `fail_service` is called at line 176. So by line 178, if there was an error, the tracker already has it as "failed". The issue is that line 180 calls `complete_service` *overwriting* the "failed" status. The condition on line 178 is supposed to prevent this but is broken.
**Impact:** When a service partially processes (some records before the exception), the tracker marks it as both "failed" (line 176) and then "completed" (line 180), with "completed" winning. On `--resume`, this service would be skipped as "completed" even though it failed partway through.

### R-2.6: Structured JSONL append is not atomic
**File:** `shared/takeout/chunker.py:134-135`
**Severity:** medium
**Finding:** `write_record` for structured records opens the JSONL file in append mode and writes a line. If the process is killed between the `f.write(line + "\n")` call, a partial line could be written. The `json.loads` in `profiler_bridge.py:61` will hit `json.JSONDecodeError` and skip it (line 62), but the partial line could also corrupt the next valid line if the newline wasn't written.

The Python `write()` on a file opened in text mode is not guaranteed to be atomic at the OS level, especially for lines longer than the pipe buffer (4096 bytes on Linux). However, most JSONL records are well under 4096 bytes, so in practice the OS write is likely atomic.
**Impact:** On Ctrl+C during a structured record write, there's a small chance of JSONL corruption. The `profiler_bridge.py` reader handles this gracefully by skipping `JSONDecodeError` lines. Practical risk is very low.

### R-2.7: Structured JSONL records duplicated on resume of partial service
**File:** `shared/takeout/processor.py:124`, `shared/takeout/chunker.py:133-135`
**Severity:** medium
**Finding:** When a service is in `in_progress` state (e.g., killed mid-run), `processor.py:124` only skips services where `tracker.is_completed()` returns True. On resume, the partial service restarts from record zero, and `chunker.py:133-135` opens the JSONL in append mode (`"a"`). All records already written in the previous partial run are re-appended, producing duplicates in the structured JSONL that `profiler_bridge.py` then reads. The unstructured markdown path is immune (files keyed by `record_id` are overwritten idempotently), but the structured JSONL path is not.
**Impact:** After resume, profiler bridge reads duplicate structured facts. Depending on deduplication logic downstream, this could inflate fact counts or produce redundant profile entries.

### R-2.8: Progress file write is not atomic
**File:** `shared/takeout/progress.py:95`
**Severity:** low
**Finding:** `_save` writes the progress JSON with `self.progress_file.write_text(json.dumps(data, indent=2))`. If the process is killed during write, the progress file could be partially written. On reload, `_load` catches `json.JSONDecodeError` at line 73 and logs a warning, but the progress state is lost — effectively resetting the tracker. This means a `--resume` after a crash during `_save` would re-process all services from scratch.

A safer pattern would be write-to-temp-then-rename (atomic on POSIX).
**Impact:** In the rare case of a crash exactly during `_save()`, all progress is lost. The window is very small (a few milliseconds per service transition). Low practical risk but worth noting.

---

## Robustness Findings

### B-2.1: Gmail MBOX temp file extraction can exhaust disk on large exports
**File:** `shared/takeout/parsers/gmail.py:68-76`
**Severity:** high
**Finding:** The Gmail parser extracts the entire MBOX file from the ZIP to a temp file via 1MB chunks. For a 30GB Gmail export, this requires 30GB of temp disk space. The `NamedTemporaryFile(suffix=".mbox", delete=True)` will auto-delete on close, but while processing, both the ZIP and the temp file exist simultaneously, doubling disk usage. This is documented as intentional ("avoids loading the entire MBOX into memory") but the disk impact is not documented.
**Impact:** A 30GB MBOX + 30GB temp file requires 60GB+ free disk space. If `/tmp` is on a smaller partition (common on Linux), the extraction will fail with `OSError`. The error is caught by the processor's generic exception handler (`processor.py:171-176`) but the user gets no guidance about disk space.

### B-2.2: Chrome history JSON loaded entirely into memory
**File:** `shared/takeout/parsers/chrome.py:52-54`
**Severity:** medium
**Finding:** `_parse_history` reads the entire `BrowserHistory.json` into memory with `zf.read(path)` then `json.loads(raw)`. Chrome history can be millions of entries. A user with 10+ years of Chrome history could have a 500MB+ BrowserHistory.json. The deduplication logic at lines 65-94 also builds a full dict of all URLs in memory.
**Impact:** Excessive memory usage for users with extensive Chrome history. Unlike Gmail (which streams), Chrome has no streaming path.

### B-2.3: Semantic location history files loaded entirely into memory
**File:** `shared/takeout/parsers/location.py:67-69`
**Severity:** low
**Finding:** Each monthly semantic location history JSON file is loaded entirely with `zf.read(path)` + `json.loads(raw)`. Monthly files are typically 1-10MB, so this is acceptable. However, the raw `Records.json` fallback path (lines 229-231) loads the potentially multi-gigabyte raw location file.
**Impact:** The semantic path is fine. The raw Records.json path (B-2.1 already partially covers this as C-2.4) could cause OOM on large exports.

### B-2.4: process_batch opens ZIPs sequentially (good design)
**File:** `shared/takeout/processor.py:204-262`
**Severity:** (non-finding — positive)
**Finding:** `process_batch` processes ZIPs sequentially via a `for` loop, calling `process_takeout` for each. Each `process_takeout` opens the ZIP with a `with zipfile.ZipFile(zip_path) as zf:` context manager at line 100, which closes it before the next ZIP opens. This means only one ZIP is open at a time, even for multi-ZIP scenarios. This is good design.
**Impact:** None — 500GB/14-ZIP scenario is handled correctly. Each ZIP is opened and closed sequentially.

### B-2.5: Retry queue JSONL can grow unbounded
**File:** `rag-pipeline/ingest.py:142-177`
**Severity:** low
**Finding:** The retry queue JSONL file is appended to on each failure. While `_remove_from_queue` rewrites the file when re-queueing, entries that hit permanent failure (line 146) are simply logged and not added to the queue — but their original entries were already removed by `_remove_from_queue` at line 166. So the queue shouldn't grow unbounded in practice. However, if many different files fail simultaneously, the queue could get large. There's no maximum queue size check.
**Impact:** Minimal. The queue self-limits via MAX_RETRIES=5 and periodic cleanup during `process_retries`.

### B-2.6: ingest.py bulk_ingest re-processes all files on every startup
**File:** `rag-pipeline/ingest.py:443-460`
**Severity:** medium
**Finding:** `bulk_ingest` calls `d.rglob("*")` on all watch directories and calls `ingest_file` for every matching file on every startup. There is no tracking of which files have already been ingested. The `delete_file_points` + `upsert` pattern at lines 364/394 makes this idempotent (same file produces same point IDs, so upserts overwrite), but every restart re-embeds all files, which is expensive (Ollama embedding calls for every chunk of every file).
**Impact:** On a system restart or service restart, all files are re-embedded. With 1000+ files in the RAG sources directory, this could take hours and generate significant Ollama load. A simple "already ingested" tracking file (or checking if points already exist in Qdrant) would avoid this.

### B-2.7: ingest.py parse_frontmatter does not handle multi-line YAML values
**File:** `rag-pipeline/ingest.py:267-303`
**Severity:** low
**Finding:** `parse_frontmatter` parses YAML line-by-line with `line.partition(":")`. Multi-line YAML values (block scalars using `|` or `>`, or values spanning multiple lines) would not be parsed correctly. However, the takeout chunker (`chunker.py:23-65`) only ever generates single-line frontmatter values, so in practice this isn't triggered by the current pipeline.
**Impact:** If external markdown files with multi-line YAML frontmatter are placed in the RAG watch directory, their frontmatter metadata would not be correctly extracted for Qdrant enrichment. The document content itself would still be ingested correctly.

### B-2.8: Proton parser silently skips .eml parse failures
**File:** `shared/proton/parser.py:168-176`
**Severity:** low
**Finding:** When the .eml file cannot be parsed (line 175), the parser logs at debug level and sets `body = ""`. The record is still created from metadata alone, but with no body content. For received emails, this means the unstructured path gets a record with only headers, no body text.
**Impact:** Corrupted .eml files produce records that appear complete but lack body content. The user has no indication that body extraction failed unless they enable debug logging.

### B-2.9: LLM export converter loads entire conversations.json into memory
**File:** `shared/llm_export_converter.py:82-98`
**Severity:** low
**Finding:** `parse_claude_zip` reads the entire `conversations.json` into memory. Claude exports can be large (thousands of conversations with full message history). However, unlike browser history or location data, conversation exports are typically in the tens-of-megabytes range, so this is acceptable.
**Impact:** Very large Claude exports (100MB+) could cause memory pressure, but this is an unlikely edge case.

### B-2.10: JSONL corruption resilience is present but inconsistent
**File:** Multiple files
**Severity:** low
**Finding:** JSONL read paths handle corruption differently:
- `profiler_bridge.py:61-63` — skips `JSONDecodeError` lines silently (continues).
- `ingest.py:198-199` — logs warning and skips corrupt entries.
- `progress.py:73-74` — catches `JSONDecodeError` on the entire file, discards all progress.

The progress tracker (`progress.py`) is most fragile: if the JSON file is corrupt, ALL progress is lost. The others gracefully skip individual bad lines.
**Impact:** Progress tracker data loss on file corruption. Other JSONL paths are resilient.

### B-2.11: Frontmatter enrichment field mapping drops record_id, categories, location
**File:** `rag-pipeline/ingest.py:306-329`
**Severity:** low
**Finding:** `enrich_payload` has a whitelist of fields it copies from frontmatter to Qdrant payload:
```python
enrichment_keys = {
    "content_type", "source_service", "source_platform",
    "timestamp", "modality_tags", "people",
    "platform", "service",
}
```
But the takeout chunker generates additional frontmatter fields: `record_id`, `categories`, `location`. These are present in the markdown frontmatter but not copied to Qdrant payloads. The `platform` and `service` keys are correctly remapped to `source_platform` and `source_service`.
**Impact:** Qdrant points from takeout-generated markdown files lack `categories`, `location`, and `record_id` metadata. This limits filtering capabilities during RAG retrieval. Not data loss, but reduced query fidelity.

---

## Test Coverage Assessment

| Area | Status | Notes |
|------|--------|-------|
| NormalizedRecord model | well tested | 6 tests cover creation, defaults, full fields |
| ServiceConfig model | well tested | 2 tests |
| make_record_id | well tested | 4 tests for determinism, uniqueness, length, hex |
| Service registry | well tested | 5 tests cover all 14 services, tiers, completeness |
| detect_services | well tested | 5 tests including no-prefix variant |
| record_to_markdown | well tested | 5 tests covering all field combinations |
| record_to_jsonl | well tested | 2 tests including None timestamp roundtrip |
| sanitize_filename | well tested | 5 tests in models, 6 tests in llm_export |
| write_record | tested | 3 tests (unstructured, structured, dry-run) |
| Activity parser (search/youtube) | well tested | 6 tests including HTML fallback, empty entries |
| Activity parser (gemini) | **untested** | Zero tests with Gemini-specific config or data |
| Chrome parser | well tested | 4 tests including dedup and bookmarks |
| Keep parser | well tested | 5 tests including checklist and annotations |
| Calendar parser | well tested | 5 tests including recurring, attendees, all-day |
| Contacts parser | well tested | 5 tests including multi-email and categories |
| Tasks parser | tested | 3 tests |
| Gmail parser | tested | 3 tests, but no multipart MIME test |
| Drive parser | tested | 4 tests |
| Chat parser | tested | 4 tests |
| Location parser | well tested | 5 tests including semantic vs raw preference |
| Photos parser | tested | 4 tests including zero-coordinate handling |
| Purchases parser | tested | 3 tests |
| Progress tracker | well tested | 6 tests including resume and failure |
| Batch processing | well tested | 7 tests including resume, fact deferral, empty |
| Profiler bridge | well tested | 12 fact tests + 6 streaming/corruption tests |
| email_utils | tested | 8 tests covering automated detection, extraction |
| Proton labels | well tested | 10 tests |
| Proton parser | well tested | 12 tests including body extraction, CC, modality |
| Proton processor | tested | 7 tests including resume and structured routing |
| LLM export converter | well tested | 22 tests (Claude: 7, Gemini: 5, E2E: 8, profiler: 3) |
| RAG ingest.py | **untested** | No test file; logic replicated in profiler bridge tests |
| RAG query.py | **untested** | No test file |
| Retry queue logic | **untested** | queue_retry, load_retry_queue, process_retries — zero tests |
| Watchdog handler | **untested** | IngestHandler, debouncing — zero tests |
| Frontmatter parse in ingest | tested (replica) | Tests exist but on replicated code, not actual ingest.py |

---

## Focus Area Answers

### 1. Parser Correctness

Each of the 13 takeout parsers plus their assumed formats:

| Parser | Input Format | Validated? | Malformed Input Handling |
|--------|-------------|-----------|--------------------------|
| `chrome` | `BrowserHistory.json` — `{"Browser History": [...]}`; `Bookmarks.html` — Netscape format | Type-checked (list check at line 61) | Returns empty on JSONDecodeError (line 56), skips entries without URL (line 69) |
| `activity` (search/youtube/gemini) | JSON array of `{title, time, ...}`; HTML `content-cell` divs | Type-checked (list check at line 68) | Returns empty on JSONDecodeError (line 64), skips empty titles (line 75) |
| `keep` | Per-note JSON `{title, textContent, ...}` | Dict check (line 48) | Skips JSONDecodeError (line 44), skips trashed (line 52), skips empty (line 96) |
| `calendar` | ICS/iCalendar VEVENT blocks | Regex extraction, no strict validation | Skips events without SUMMARY (line 71), handles unfolding (line 156) |
| `contacts` | VCF/vCard `BEGIN:VCARD...END:VCARD` | Regex extraction | Skips cards without name (line 81), no line-folding support |
| `tasks` | JSON `{items: [...]}` or raw list | Type-checked (line 61-67) | Skips JSONDecodeError, skips empty titles (line 74) |
| `gmail` | MBOX format | stdlib `mailbox.mbox` | Filters automated senders (line 100), empty subjects (line 104) |
| `drive` | Raw files by extension | Extension-based routing | Skips binary (line 69), truncates large text (line 102) |
| `chat` | JSON `{messages: [...]}` or raw list | Type-checked (line 65-68) | Skips JSONDecodeError, skips empty text (line 79) |
| `location` | Semantic: `{timelineObjects: [...]}`, Raw: `{locations: [...]}` | Key-checked | Skips short activities <5min (line 178), returns on empty |
| `photos` | Per-photo JSON metadata `.json` | Dict check (line 56) | Skips JSONDecodeError, skips no-title (line 71) |
| `purchases` | JSON list/dict or HTML | Type-checked (line 46-54) | Skips JSONDecodeError, skips empty titles (line 77) |
| `gemini` | **Speculative** — reuses activity parser | Same as activity | Same, but real format unvalidated |

**Gemini** is the only parser with zero validation against real data. All others have reasonable defensive checks.

### 2. Resume/Progress Tracking

- **Ctrl+C survival:** Partially. `_save()` is called on every state transition (start, complete, fail) at `progress.py:109,125,137`. If Ctrl+C hits between a record being written and `_save()` being called, the progress file won't reflect the latest state. However, the worst case is that a few records are re-processed on resume — not data loss.
- **Partial writes:** NOT handled atomically. `progress.py:95` uses `self.progress_file.write_text(json.dumps(data, indent=2))` which is not atomic. A kill during write corrupts the file. `_load()` catches `JSONDecodeError` but discards ALL progress.
- **JSONL flush:** N/A — progress uses JSON, not JSONL (switched from the documented JSONL to full JSON at implementation time, per `progress.py:51` using `{run_id}.json`).
- **Write frequency:** State is written on every service start/complete/fail transition — typically 14 times for a full Takeout run (once per service).

### 3. Memory on Large Inputs

- **processor.py** opens ZIPs sequentially with `with zipfile.ZipFile(zip_path) as zf:` — good. Only one ZIP open at a time.
- **process_batch** is safe — sequential processing, no simultaneous ZIP handles.
- **zipfile.ZipFile** loads the central directory into memory (small), and `zf.read(path)` loads individual files into memory. This is the concern for Chrome history, location Records.json, etc.
- **Gmail** correctly streams via temp file extraction. Other large-file parsers (Chrome, location raw) do not stream.
- For a 500GB/14-ZIP scenario: each ZIP is processed independently, closed before the next opens. Memory depends on the largest single file within any ZIP. If one ZIP contains a 2GB Chrome history and a 30GB MBOX, memory usage peaks at the MBOX extraction (temp file, not memory) plus the Chrome JSON load (~2GB memory).

### 4. JSONL Corruption

- **profiler_bridge.py:55-63** — reads JSONL with `errors="replace"` encoding, strips empty lines, catches `JSONDecodeError` per line. This is the most robust reader.
- **chunker.py:134-135** — appends JSONL without fsync. Not atomic, but write size is small.
- **ingest.py:185-199** — `load_retry_queue` reads all lines, catches both `JSONDecodeError` and `KeyError` per line. Robust.
- **progress.py** — uses JSON not JSONL. Single `write_text` for entire file. Corruption = total loss.
- **Encoding:** `profiler_bridge.py:55` opens with `errors="replace"` — safe against encoding issues. `chunker.py:134` opens with `encoding="utf-8"` — would raise on non-UTF-8 data (but records are always serialized by the same pipeline).

### 5. RAG Ingest Recovery

- **After crash:** `bulk_ingest` re-processes ALL files on startup (`ingest.py:443-460`). There is no "already ingested" tracking. This is idempotent via `delete_file_points` + deterministic point IDs, but expensive.
- **Duplicate detection:** Point IDs are deterministic (`point_id = sha256(path:chunk_index)[:16]`). Upserts overwrite existing points with the same ID. This prevents Qdrant duplicates.
- **Retry queue backoff:** Correctly implemented. `BACKOFF_SCHEDULE = [30, 120, 600, 3600, 3600]` at line 56. `queue_retry` uses `BACKOFF_SCHEDULE[min(attempts - 1, len(BACKOFF_SCHEDULE) - 1)]` (line 149). This produces 30s, 2m, 10m, 1h, 1h for attempts 1-5. MAX_RETRIES=5. `process_retries` runs every 30s in the watch loop (line 481). Verified correct.
- **Retry queue correctness:** `_remove_from_queue` rewrites the file excluding the path (line 203-208). `process_retries` separates "due" from "not due" entries (lines 231-236), processes due entries, and writes back the remaining + re-queued entries (line 264). This is correct — successfully retried entries are simply not re-added.

### 6. Frontmatter Enrichment Fidelity

Takeout chunker generates these frontmatter fields: `platform`, `service`, `content_type`, `record_id`, `timestamp`, `modality_tags`, `people`, `location`, `categories`.

Ingest enrichment copies: `platform` (→ `source_platform`), `service` (→ `source_service`), `content_type`, `timestamp`, `modality_tags`, `people`.

**Dropped fields:** `record_id`, `location`, `categories` are NOT copied to Qdrant payloads. See finding B-2.11.

### 7. process_batch Aggregation

- **Progress trackers:** Each ZIP gets its own `ProgressTracker` with a unique `run_id` derived from `sha256(path:size)[:12]` (`processor.py:53-57`). Tracker files are stored as `{run_id}.json` in `<cache>/takeout-ingest/`. No interference.
- **Output directories:** All ZIPs share the same `output_dir` and `structured_path`. For structured JSONL, records are appended (file opened in append mode). For unstructured markdown, files are keyed by `record_id`, so duplicate records from overlapping ZIPs would overwrite each other. This is safe because Google splits Takeout across ZIPs by service, not by time — so overlapping records are rare.
- **Fact generation:** Correctly deferred. `_skip_facts=True` is passed to each individual `process_takeout` call (line 234). Facts are generated once at the end (line 253-260). Tested at `test_takeout_processor.py:392-406`.

### 8. Email Parsing

- **Multipart MIME:** `email_utils.py:41-62` handles multipart messages by walking parts. Prefers `text/plain`, falls back to `text/html` with tag stripping. This is correct RFC 2822 handling.
- **Encoded headers:** `email_utils.py:83-97` uses `email.header.decode_header` from stdlib — correctly handles RFC 2047 encoded words (e.g., `=?utf-8?q?Subject?=`). The `except Exception` at line 96 is a broad catch, but appropriate for header decoding edge cases.
- **HTML-only emails:** Handled via the fallback path at `email_utils.py:53-61`. HTML tags are stripped with `re.sub(r"<[^>]+>", " ", html)`. This is basic but functional — it won't handle CSS, scripts, or deeply nested HTML well, but extracts readable text.
- **Body truncation:** `MAX_BODY_CHARS = 2000` (email_utils.py:26). Applied at `gmail.py:113` and `proton/parser.py:174`. Truncation is applied after extraction, so the full body is decoded first, then truncated. This is correct.
- **Proton email parsing:** Uses `email.message_from_bytes` (parser.py:171) on the raw .eml content. This is the correct stdlib approach. Falls back gracefully if .eml is missing (line 168).

---

## Summary

- **Completeness:** 5 findings (0 critical, 0 high, 3 medium, 2 low)
- **Correctness:** 8 findings (0 critical, 0 high, 5 medium, 3 low)
- **Robustness:** 10 findings + 1 non-finding (0 critical, 1 high, 2 medium, 7 low)

**Total: 23 findings (0 critical, 1 high, 10 medium, 12 low)**

### Key Concerns

1. **B-2.6: Bulk re-ingest on every restart** (medium) — The RAG ingest service re-embeds all files on every restart with no "already processed" tracking. This is the most impactful operational issue for daily use.

2. **B-2.1: Gmail temp file disk exhaustion** (high) — A 30GB MBOX extraction to temp can exhaust disk space, particularly if `/tmp` is on a constrained partition. This is the highest-severity finding.

3. **R-2.5: Broken error detection in processor** (medium) — The string-matching heuristic for error detection is subtly broken, causing failed services to be marked as "completed" in the progress tracker. This undermines `--resume` reliability.

4. **R-2.1: profiler_bridge memory usage** (medium) — Despite the "streaming" comment, all records are accumulated in memory. For large exports this is a memory concern.

5. **C-2.1: Gemini parser unvalidated** (medium) — Entirely speculative code with zero Gemini-specific tests. Could produce zero records silently against real data.

### Positive Observations

The codebase is **well-structured and well-tested overall**. The dual-path architecture (structured/unstructured) is clean and consistently applied. All 13 parsers follow the same interface pattern (generator yielding NormalizedRecord). The test suite covers all parsers with synthetic fixtures and achieves good coverage of core paths. The retry queue in ingest.py is correctly implemented with proper backoff. The defensive coding pattern of catching exceptions per-record and continuing is applied consistently across all parsers, preventing a single malformed record from failing an entire service.
