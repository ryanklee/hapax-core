# Audit Fix Plan

**Generated**: 2026-03-02
**Source**: 9 audit documents (01-09), covering ~39K LOC across 5 repos

---

## Summary

Total findings: 162 actionable (excluding 9 bonuses from Domain 8, 1 retracted from Domain 6, and 3 positive non-actionable observations from Domain 6)

- **P0 (Critical)**: 4 -- fix immediately
- **P1 (High)**: 15 -- fix this week
- **P2 (Medium)**: 76 -- fix this month
- **P3 (Low)**: 67 -- fix when convenient

---

## P0 -- Critical (fix immediately)

### Fix 1: Replace plaintext API keys in .env with pass-backed retrieval
**Findings:** C-8.1
**Files:** `<llm-stack>/.env`, `<llm-stack>/docker-compose.yml`
**Action:** Replace all plaintext API keys (ANTHROPIC_API_KEY, GOOGLE_API_KEY, LITELLM_MASTER_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, CLICKHOUSE_PASSWORD, REDIS_PASSWORD, MINIO_ROOT_PASSWORD, N8N_ENCRYPTION_KEY) in `.env` with a startup script that populates from `pass`, or convert `.env` to an `.envrc` that uses `pass show` -- matching the pattern already used in `<ai-agents>/.envrc`. The Docker Compose file should reference `${VAR}` from the shell environment rather than a static `.env` file.
**Verification:** `grep -c 'sk-ant\|AIza\|sk-litellm\|pk-lf\|sk-lf' <llm-stack>/.env` returns 0. Services start successfully with `docker compose up -d`.

### Fix 2: Generate real WEBUI_SECRET_KEY
**Findings:** C-8.2
**Files:** `<llm-stack>/.env`
**Action:** Generate a cryptographic secret with `openssl rand -hex 32` and replace the `CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32` placeholder. Store in `pass` and reference from the `.envrc` approach in Fix 1. Restart Open WebUI.
**Verification:** `grep CHANGE_ME <llm-stack>/.env` returns no matches. Open WebUI at localhost:3080 accepts login and issues a signed session cookie.

### Fix 3: Configure Telegram chat ID
**Findings:** C-8.3
**Files:** `<llm-stack>/.env`
**Action:** Obtain the Telegram chat ID from the BotFather flow (send `/start` to the bot, then query `https://api.telegram.org/bot<TOKEN>/getUpdates` to extract the chat ID). Replace `CHANGE_ME_GET_FROM_TELEGRAM_BOT` with the actual value. Store in `pass`.
**Verification:** `grep CHANGE_ME <llm-stack>/.env` returns no matches. The n8n health-relay workflow sends a test Telegram message successfully.

### Fix 4: Fix vault path in .env
**Findings:** C-8.4
**Files:** `<llm-stack>/.env`
**Action:** Change `OBSIDIAN_VAULT_PATH=<home>/obsidian-vault` to `OBSIDIAN_VAULT_PATH=<home>/Documents/Personal`. This aligns with the correct path used in `.envrc` and `vault_writer.py` default.
**Verification:** `source <llm-stack>/.env && test -d "$OBSIDIAN_VAULT_PATH"` exits 0.

---

## P1 -- High (fix this week)

### Fix 5: Add LLM failure handling to all timer-driven agents
**Findings:** B-5.1, H-1.1
**Files:** `agents/briefing.py`, `agents/digest.py`, `agents/scout.py`, `agents/drift_detector.py`, `agents/management_prep.py`, `agents/research.py`, `agents/code_review.py`
**Action:** Wrap `agent.run()` / `agent.run_stream()` calls in try/except blocks in all 6 agents (scout already has per-component handling). For timer-driven agents (briefing, digest), produce a degraded-mode output on LLM failure: stats-only briefing, raw data digest. For interactive agents (research, code_review, management_prep), catch the exception and display a clear error message to the operator rather than crashing.
**Verification:** Mock the LLM client to raise `Exception("all models exhausted")`. Run each agent. Verify non-zero output or graceful error message instead of stack trace.

### Fix 6: Add neurocognitive micro-prompt to all agent system prompts
**Findings:** H-1.1, H-1.3
**Files:** `agents/briefing.py`, `agents/scout.py`, `agents/management_prep.py`, `agents/drift_detector.py`, `agents/digest.py`
**Action:** Add a minimal neurocognitive framing line (~15 tokens) to each agent's system prompt: `"The operator has ADHD and autism. Call lookup_constraints() before generating output to understand their cognitive needs."` This preserves the lean prompt design from the context management refactoring while ensuring agents know to query context tools for neurocognitive accommodations.
**Verification:** Grep all `SYSTEM_PROMPT` definitions in `agents/`. Each should contain "ADHD" or reference `get_system_prompt_fragment()`.

### Fix 7: Register context tools on digest agent
**Findings:** H-1.2, C-5.1
**Files:** `agents/digest.py`
**Action:** Add the standard context tool registration pattern after the agent definition:
```python
from shared.context_tools import get_context_tools
for _tool_fn in get_context_tools():
    digest_agent.tool(_tool_fn)
```
**Verification:** `grep -c "get_context_tools" agents/digest.py` returns 1. Run digest agent with mocked Qdrant; verify context tool calls appear in trace.

### Fix 8: Add profile-facts to knowledge-maint, health-monitor, and digest COLLECTIONS
**Findings:** H-2.1, C-4.1, C-4.5, B-3.7
**Files:** `agents/knowledge_maint.py`, `agents/health_monitor.py`, `agents/digest.py`
**Action:** Add `"profile-facts"` to the `COLLECTIONS` list in `knowledge_maint.py:41`, `REQUIRED_QDRANT_COLLECTIONS` in `health_monitor.py:81`, and `COLLECTIONS` in `digest.py:68`. Additionally, add a stale-point cleanup pass to `ProfileStore.index_profile()` that deletes points whose `(dimension, key)` is no longer in the profile.
**Verification:** Run `knowledge_maint --dry-run` and verify `profile-facts` appears in the collection stats output. Run health monitor; verify `profile-facts` check result appears.

### Fix 9: Add profile-facts to backup script
**Findings:** R-8.8
**Files:** `~/Scripts/setup/llm-stack-scripts/llm-stack/scripts/backup.sh`
**Action:** Change `for collection in documents samples claude-memory; do` to `for collection in documents samples claude-memory profile-facts; do`.
**Verification:** Run backup script. Verify `profile-facts` snapshot file appears in the backup directory.

### Fix 10: Fix n8n backup to use Docker volume
**Findings:** R-8.9
**Files:** `~/Scripts/setup/llm-stack-scripts/llm-stack/scripts/backup.sh`
**Action:** Replace the `$HOME/.n8n` host path check with a Docker volume export: `docker compose exec n8n n8n export:workflow --all --output=/tmp/workflows.json && docker compose cp n8n:/tmp/workflows.json "$BACKUP_DIR/n8n/"`. Alternatively, back up the named volume directly.
**Verification:** Run backup script. Verify n8n workflow JSON appears in `$BACKUP_DIR/n8n/` with actual workflow content (not empty).

### Fix 11: Fix refresh_slow() cascading failure in web API cache
**Findings:** 7.01
**Files:** `cockpit/api/cache.py`
**Action:** Replace the single try/except wrapping all 8 sequential collector calls with individual try/except per collector, matching the pattern already used for nudges and accommodations on lines 88-97. Each failed collector should log the error and leave its cache field at the previous value.
**Verification:** Mock `collect_cost()` to raise. Verify other fields (goals, readiness, management, agents) still refresh. Write a test case.

### Fix 12: Fix Path serialization in ManagementSnapshot
**Findings:** 7.02
**Files:** `cockpit/api/routes/data.py` or `cockpit/data/management.py`
**Action:** Override `_to_dict()` or add a custom JSON encoder that converts `Path` objects to strings. Alternatively, exclude `file_path` from the serialized management response (it is an internal TUI implementation detail, not useful to the web frontend).
**Verification:** With real vault data containing people notes, `curl localhost:8050/api/management` returns 200 with valid JSON (not 500).

### Fix 13: Run blocking collectors in thread pool
**Findings:** 7.03
**Files:** `cockpit/api/cache.py`
**Action:** Wrap synchronous blocking calls (`collect_cost()`, `collect_management_state()`, and the full `refresh_slow` method body) in `asyncio.to_thread()` so they don't stall the event loop.
**Verification:** While `refresh_slow` is running, concurrent `curl` requests to any API endpoint return within 1 second.

### Fix 14: Wrap profiler source readers in error handling
**Findings:** B-3.1
**Files:** `agents/profiler_sources.py`
**Action:** Add a try/except around each reader call in `_read_capped()` or at the individual reader level. Catch `(OSError, UnicodeDecodeError)` and log a warning, returning an empty list for that reader. This prevents a single deleted or permission-denied file from crashing the entire profiler run.
**Verification:** Create a profiler source file, set it to mode 000, run `profiler --auto`. Verify the profiler completes (with a logged warning) rather than crashing.

### Fix 15: Add disk space warning for Gmail MBOX temp extraction
**Findings:** B-2.1
**Files:** `shared/takeout/parsers/gmail.py`
**Action:** Before extracting the MBOX to a temp file, check available disk space with `shutil.disk_usage(tempfile.gettempdir())`. If available space is less than the MBOX size in the ZIP (obtainable from `zf.getinfo(path).file_size`), log an error and skip with a clear message: "Insufficient disk space for Gmail MBOX extraction: need {size}GB, have {avail}GB". Also document the disk space requirement in the CLI `--help` output.
**Verification:** Mock `shutil.disk_usage` to return low available space. Run Gmail parser. Verify it skips with informative error rather than crashing with `OSError`.

### Fix 16: Add health history file rotation
**Findings:** B-4.1, R-4.1
**Files:** `<local-bin>/health-watchdog`, `agents/activity_analyzer.py`, `agents/health_monitor.py`
**Action:** Add a rotation mechanism to the health-watchdog script: after appending, check line count. If exceeding a threshold (e.g., 10,000 lines / ~100 days), truncate to the most recent 5,000 lines. Alternatively, switch to date-based files (`health-history-YYYY-MM.jsonl`) and update all readers (`collect_health_trend`, `format_history`, `collect_health_history`) to glob and merge files within the requested time window.
**Verification:** Create a health-history.jsonl with 15,000 lines. Run the watchdog. Verify the file is pruned to the configured limit.

### Fix 17: Implement decision capture for dismissed and expired nudges
**Findings:** H-3.1, C-6.2
**Files:** `cockpit/app.py`, `cockpit/widgets/action_items.py`, `cockpit/data/nudges.py`
**Action:** Add a "dismiss" keybinding (e.g., `d` or `Delete`) to the ActionItemsList widget that records a `Decision(action="dismissed")`. Add expiry detection: when nudges refresh, compare previous nudge set to current; nudges that disappeared without being executed or dismissed should be recorded as `Decision(action="expired")`.
**Verification:** Run cockpit, dismiss a nudge with the keybinding. Check `decisions.jsonl` for an entry with `action: "dismissed"`. Wait for a nudge to expire; verify `action: "expired"` appears.

---

## P2 -- Medium (fix this month)

### Fix 18: Add tests for langfuse_client.py
**Findings:** C-1.1
**Files:** `tests/test_langfuse_client.py` (new)
**Action:** Create test file covering: `langfuse_get()` success path (mock urlopen), auth failure (HTTP 401), server error (HTTP 500), timeout, missing credentials (returns `{}`), and `is_available()` with/without keys.
**Verification:** `pytest tests/test_langfuse_client.py` passes.

### Fix 19: Add tests for embed_batch()
**Findings:** C-1.6
**Files:** `tests/test_config.py`
**Action:** Add tests for: empty list early return, prefix application to each text, Ollama error wrapping, return structure access, and happy-path dimension verification.
**Verification:** `pytest tests/test_config.py -k embed_batch` passes.

### Fix 20: Add schema validation for operator.json
**Findings:** R-1.1
**Files:** `shared/operator.py`
**Action:** Define a Pydantic model for operator.json (per project conventions). Validate on load. On validation failure, log a clear error and fall back to empty defaults rather than silently degrading.
**Verification:** Corrupt `operator.json` (remove required key). Run any agent. Verify a clear validation error is logged. Verify the agent still runs with defaults.

### Fix 21: Add timeout to embed() and embed_batch()
**Findings:** B-1.1
**Files:** `shared/config.py`
**Action:** Add a `timeout` parameter to the `ollama.embed()` calls (e.g., 30 seconds). Wrap the timeout as a `RuntimeError` to match the existing error contract.
**Verification:** Mock Ollama to hang. Verify `embed()` raises `RuntimeError` within 30 seconds.

### Fix 22: Differentiate Langfuse failure modes
**Findings:** B-1.2
**Files:** `shared/langfuse_client.py`
**Action:** Return a structured result (e.g., named tuple or dataclass with `data`, `error`, `available` fields) instead of bare `{}` on all failures. Callers can then distinguish "no data" from "service unreachable" from "credentials wrong". At minimum, log at `warning` level (not just return silently) for non-credential errors.
**Verification:** Mock Langfuse to return 500. Verify the caller receives an error indicator, not an empty dict indistinguishable from "no data".

### Fix 23: Fix process_takeout error detection heuristic
**Findings:** R-2.5
**Files:** `shared/takeout/processor.py`
**Action:** Replace the string-matching heuristic at line 178 with a proper boolean flag. Track whether any exception occurred for the current service. Only call `tracker.complete_service()` if no error flag is set.
**Verification:** Mock a parser to raise midway. Verify the service is marked as "failed" (not "completed") in the progress file. Run with `--resume`; verify the failed service is retried.

### Fix 24: Fix structured JSONL duplication on resume
**Findings:** R-2.7
**Files:** `shared/takeout/processor.py`, `shared/takeout/chunker.py`
**Action:** On resume of an `in_progress` service, truncate the structured JSONL file to remove records from the partial run before restarting the service. Alternatively, track the last written record_id per service in the progress file and skip records already written.
**Verification:** Start a takeout run, kill mid-service. Resume. Verify the structured JSONL has no duplicate record_ids (pipe through `jq -r .record_id | sort | uniq -d`).

### Fix 25: Add ingest.py "already processed" tracking
**Findings:** B-2.6, C-2.2
**Files:** `rag-pipeline/ingest.py`
**Action:** Before calling `ingest_file()` in `bulk_ingest()`, check if the file's content hash or mtime matches a stored value. Maintain a simple JSON or SQLite tracker file of `{path: {hash, mtime, ingested_at}}`. Skip files that haven't changed since last ingest. This eliminates the expensive re-embedding of all files on every restart.
**Verification:** Run `bulk_ingest()` twice on the same directory. Verify the second run logs "N files skipped (already ingested)" and completes in seconds rather than minutes.

### Fix 26: Add tests for RAG ingest.py
**Findings:** C-2.2
**Files:** `rag-pipeline/tests/test_ingest.py` (new)
**Action:** Create tests for: `parse_frontmatter()`, `enrich_payload()`, `queue_retry()`, `load_retry_queue()`, `process_retries()`, and `bulk_ingest()` (with mocked Qdrant and Ollama). This can reuse the replicated test logic already in `test_takeout_profiler_bridge.py` but against the real functions.
**Verification:** `pytest rag-pipeline/tests/test_ingest.py` passes.

### Fix 27: Add profiler pipeline integration tests
**Findings:** C-3.2, C-3.3
**Files:** `tests/test_profiler_integration.py` (new)
**Action:** Create integration-level tests for `run_auto()`, `run_extraction()`, and `run_curate()` with mocked LLM and Qdrant. Verify the orchestration wiring: discovery -> reading -> chunking -> extraction -> merging -> synthesis -> save. Also test `regenerate_operator()` with a deterministic snapshot.
**Verification:** `pytest tests/test_profiler_integration.py` passes.

### Fix 28: Add profile-facts stale point cleanup
**Findings:** B-3.7
**Files:** `shared/profile_store.py`
**Action:** After `index_profile()` upserts all current facts, scroll all points in the collection and delete any whose `(dimension, key)` is not in the current profile. This prevents orphaned points from accumulating.
**Verification:** Index a profile with fact "workflow/daily_routine". Delete that fact from the profile. Re-index. Verify the point is removed from Qdrant.

### Fix 29: Scope management bridge rglob to specific directories
**Findings:** B-3.3
**Files:** `shared/management_bridge.py`
**Action:** Change `vault_path.rglob("*.md")` in `_coaching_facts()` and `_feedback_facts()` to scan only `10-work/` (where coaching and feedback notes live). Exclude `60-archive/` and `90-attachments/` explicitly.
**Verification:** Add a non-coaching `.md` file to `90-attachments/`. Run `generate_facts()`. Verify the file is not opened or parsed.

### Fix 30: Add auto-fix backoff to health watchdog
**Findings:** B-4.2
**Files:** `<local-bin>/health-watchdog`
**Action:** Track fix attempts in a state file (e.g., `<cache>/health-watchdog-fix-attempts.json`). Increment on each failed fix attempt. After 3 consecutive failures for the same check, skip the fix and log a warning. Reset the counter when the check passes. This prevents noisy 15-minute retry loops for persistent issues.
**Verification:** Mock a remediation command to always fail. Run the watchdog 4 times. Verify the fix is attempted 3 times, then skipped on the 4th with a "giving up" log message.

### Fix 31: Improve knowledge_maint error reporting
**Findings:** B-4.4
**Files:** `agents/knowledge_maint.py`
**Action:** Replace bare `except Exception: pass` patterns with `except Exception as e: log.warning(...)` that records the error. Add error counts to the `MaintenanceReport` so the operator can see "3 of 500 points failed to query" rather than "0 stale, 0 duplicates" when Qdrant is intermittent.
**Verification:** Mock Qdrant to fail intermittently. Run knowledge_maint. Verify the report includes error counts.

### Fix 32: Add pagination limit to Langfuse queries
**Findings:** B-4.5, B-3.4
**Files:** `agents/activity_analyzer.py`, `agents/profiler_sources.py`
**Action:** Add a `max_pages` parameter (default 20) to the pagination loops in `collect_langfuse()` and `read_langfuse()`. Break after the limit with a warning. This prevents unbounded pagination against a busy Langfuse instance.
**Verification:** Mock Langfuse to return 100 pages. Verify only 20 pages are fetched and a warning is logged.

### Fix 33: Fix code review model override to re-register context tools
**Findings:** C-5.6
**Files:** `agents/code_review.py`
**Action:** After recreating the agent with a new model (line 86-92), re-register context tools using the standard pattern. Extract the agent creation + tool registration into a helper function called from both the module-level init and the model override path.
**Verification:** Run `code_review --model fast <file>`. Verify context tools are available (check agent tools list).

### Fix 34: Add scout report staleness check to briefing
**Findings:** R-5.2
**Files:** `agents/briefing.py`
**Action:** After loading the scout report and extracting `scout_ts`, parse it as a datetime and compare against `datetime.now(timezone.utc)`. If older than 7 days, skip the scout section (matching the documented intent in the comment at line 137).
**Verification:** Create a scout-report.json with a 30-day-old `generated_at`. Run briefing. Verify scout section is empty/not included.

### Fix 35: Add agent test coverage for scout.py
**Findings:** C-5.2 (partial)
**Files:** `tests/test_scout.py` (new)
**Action:** Create tests for: `load_registry()`, `_tavily_search()` (mocked HTTP), `search_component()`, `_build_usage_map()` (mocked Langfuse), `run_scout()` (mocked LLM), and the notification function. Scout at 544 LOC is the highest-priority untested agent.
**Verification:** `pytest tests/test_scout.py` passes.

### Fix 36: Add briefing pipeline test
**Findings:** C-5.3
**Files:** `tests/test_briefing.py`
**Action:** Add a test for `generate_briefing()` with mocked data sources (Langfuse, health, scout JSON, digest JSON, goals) and mocked LLM. Verify the prompt assembly and output structure.
**Verification:** `pytest tests/test_briefing.py -k generate_briefing` passes.

### Fix 37: Add digest pipeline test
**Findings:** C-5.4
**Files:** `tests/test_digest.py`
**Action:** Add a test for `generate_digest()` with mocked Qdrant and LLM. Verify the data collection, prompt assembly, and output structure.
**Verification:** `pytest tests/test_digest.py -k generate_digest` passes.

### Fix 38: Switch scout to shared.notify
**Findings:** C-5.5, H-2.3
**Files:** `agents/scout.py`
**Action:** Replace the direct `subprocess.run(["notify-send", ...])` call in `send_notification()` with `from shared.notify import send_notification as notify; notify(title, body, priority=...)`. This enables ntfy mobile push for scout reports.
**Verification:** Run scout with mocked Tavily. Verify `shared.notify.send_notification` is called (not `subprocess.run`).

### Fix 39: Validate briefing/digest JSON structure
**Findings:** B-5.3
**Files:** `agents/briefing.py`
**Action:** Add `TypeError` to the caught exception types in the scout report and digest report loading blocks. Additionally, wrap the list comprehension over `scout_data.get("recommendations", [])` in a guard that verifies it is iterable.
**Verification:** Set scout-report.json `recommendations` to a string instead of a list. Run briefing. Verify it handles gracefully (no crash, scout section omitted).

### Fix 40: Fix micro-probe cooldown persistence
**Findings:** R-6.2, H-3.3
**Files:** `cockpit/micro_probes.py`
**Action:** Persist `_last_probe_time` as a wall-clock timestamp (e.g., `time.time()`) in `probe-state.json` alongside `asked_topics`. On load, restore and check against current `time.time()`. This survives process restarts while still providing the 600s cooldown.
**Verification:** Ask a probe. Restart the cockpit within 600s. Verify no probe is offered. Wait 600s, restart. Verify a probe is offered.

### Fix 41: Make accommodation and session persistence atomic
**Findings:** R-6.3, R-6.5
**Files:** `cockpit/accommodations.py`, `cockpit/chat_agent.py`
**Action:** Replace `path.write_text(json.dumps(data))` with atomic write pattern: write to a temp file in the same directory, then `os.replace()` (atomic on POSIX). Apply to `save_accommodations()` and `ChatSession.save()`.
**Verification:** Verify the temp file pattern is used (code review). Simulate crash during write (not practical in unit test, but verify the pattern).

### Fix 42: Make pending-facts clear-after-flush atomic
**Findings:** B-6.7
**Files:** `cockpit/screens/chat.py`
**Action:** After `flush_interview_facts()` succeeds, use atomic write (write empty to temp, rename) to clear the pending-facts file. Alternatively, track flushed line numbers and only clear up to that point, so a crash between flush and clear doesn't cause re-flush of already-flushed facts.
**Verification:** Review code for atomic pattern. Run `/flush` command; verify file is cleared.

### Fix 43: Add interview stuck-state escape with fact backup
**Findings:** B-6.3
**Files:** `cockpit/screens/chat.py`, `cockpit/chat_agent.py`
**Action:** When `end_interview()` fails due to `flush_interview_facts` error, save accumulated facts and insights to a backup file (`<cache>/cockpit/interview-backup-{timestamp}.json`) before presenting the error. This gives the operator a path to recover accumulated facts even if `/clear` is used.
**Verification:** Mock `flush_interview_facts` to raise. Run `/interview end`. Verify backup file is created with facts and insights.

### Fix 44: Add TypeScript interfaces for remaining API endpoints
**Findings:** 7.04, 7.05, 7.06, H-5.1
**Files:** `cockpit-web/src/api/types.ts`, `cockpit-web/src/api/client.ts`, `cockpit-web/src/api/hooks.ts`
**Action:** Add TS interfaces for `DriftSummary`, `ManagementSnapshot` (+ `PersonState`, `CoachingState`, `FeedbackState`), `AccommodationSet` (+ `Accommodation`), and `HealthHistory` (+ `HealthHistoryEntry`). Add missing 3 fields to `ReadinessSnapshot`. Add corresponding client methods and TanStack Query hooks.
**Verification:** `npx tsc --noEmit` passes with no errors. All 15 endpoints have corresponding typed hooks.

### Fix 45: Add Docker resource limits to all services
**Findings:** R-8.1
**Files:** `<llm-stack>/docker-compose.yml`
**Action:** Add `mem_limit` to all services: ollama 16g, postgres 4g, litellm 2g, clickhouse 4g, open-webui 2g, n8n 1g, langfuse 2g, langfuse-worker 2g, redis 512m, minio 1g.
**Verification:** `docker compose config | grep -c mem_limit` returns 12 (one per service including the 2 already configured).

### Fix 46: Pin remaining Docker images to sha256 digests
**Findings:** R-8.2
**Files:** `<llm-stack>/docker-compose.yml`
**Action:** For the 6 unpinned images (pgvector, litellm, redis, langfuse-worker, langfuse, ntfy), pull the current image, note the digest with `docker inspect --format='{{.RepoDigests}}' <image>`, and update the compose file to use `image@sha256:...` format.
**Verification:** `grep -c '@sha256:' <llm-stack>/docker-compose.yml` returns 12.

### Fix 47: Add Langfuse healthchecks to Docker Compose
**Findings:** R-8.3
**Files:** `<llm-stack>/docker-compose.yml`
**Action:** Add healthcheck directives for langfuse (web): `test: wget --no-verbose --tries=1 --spider http://localhost:3000/api/public/health || exit 1`. For langfuse-worker: TCP check on port 3030 or a custom script.
**Verification:** `docker compose ps` shows `healthy` status for both langfuse services.

### Fix 48: Add systemd resource limits to LLM-calling services
**Findings:** R-8.5
**Files:** `<systemd-user>/daily-briefing.service`, `digest.service`, `drift-detector.service`, `scout.service`, `manifest-snapshot.service`, `knowledge-maint.service`
**Action:** Add `MemoryMax=2G` and `CPUQuota=60%` to briefing, digest, drift-detector, and scout services. Add `MemoryMax=1G` and `CPUQuota=30%` to manifest-snapshot and knowledge-maint. Run `systemctl --user daemon-reload`.
**Verification:** `systemctl --user show daily-briefing.service -p MemoryMax` returns `MemoryMax=2147483648`.

### Fix 49: Fix health watchdog false OnFailure notifications
**Findings:** R-8.7
**Files:** `<systemd-user>/health-monitor.service`
**Action:** Add `SuccessExitStatus=1` to the service definition so that exit code 1 (degraded) is treated as success by systemd. The watchdog already sends its own nuanced notification for degraded status; the OnFailure template should only fire on unexpected crashes (exit code 2+).
**Verification:** Trigger a degraded health status. Verify no "Service Failed" notification from the template (only the watchdog's own notification).

### Fix 50: Add Dockerfile.api HEALTHCHECK and document runtime deps
**Findings:** 7.13, 7.14, R-8.13
**Files:** `<ai-agents>/Dockerfile.api`
**Action:** Add `HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/')"`. Remove `COPY profiles/ profiles/` (profiles should be volume-mounted at runtime). Add a comment block documenting required volume mounts and env vars.
**Verification:** `docker build` succeeds. Docker reports container as healthy after startup.

### Fix 51: Configure digest/briefing timer ordering
**Findings:** R-8.14
**Files:** `<systemd-user>/daily-briefing.service`
**Action:** Add `After=digest.service` to the `[Unit]` section of `daily-briefing.service`. This ensures the briefing waits for the digest to complete before starting, eliminating the risk of reading a stale digest.
**Verification:** Run `systemd-analyze verify <systemd-user>/daily-briefing.service`. Check that `After=` includes `digest.service`.

### Fix 52: Consolidate PROFILES_DIR imports
**Findings:** H-2.2
**Files:** `cockpit/accommodations.py`, `shared/management_bridge.py`
**Action:** Replace the independent `PROFILES_DIR` definitions with `from shared.config import PROFILES_DIR` in both files. This eliminates the structural fragility of three independently computed paths.
**Verification:** `grep -rn "PROFILES_DIR = Path" --include="*.py"` returns only one result (in `shared/config.py`).

### Fix 53: Remove legacy store_to_qdrant() and --store-qdrant flag
**Findings:** H-4.2, H-2.4, C-3.4
**Files:** `agents/profiler.py`
**Action:** Remove the `store_to_qdrant()` function, the `store_to_mcp_memory()` function, and the `--store-qdrant` CLI argument. The new `ProfileStore.index_profile()` path (used by `run_auto()`) is the correct and only profile indexing mechanism.
**Verification:** `grep -c store_to_qdrant agents/profiler.py` returns 0. `python -m agents.profiler --help` does not list `--store-qdrant`.

### Fix 54: Implement nudge attention budget cap
**Findings:** H-5.2
**Files:** `cockpit/data/nudges.py`, `cockpit/widgets/action_items.py`
**Action:** Add a `MAX_VISIBLE_NUDGES` constant (e.g., 7). After sorting nudges by score, take only the top N. If more exist, add a summary nudge: "and {remaining} more items (press 'a' to expand)". This prevents cognitive overload from too many simultaneous demands.
**Verification:** Generate 20 nudges from various sources. Verify the ActionItemsList shows at most 7 + 1 summary item.

### Fix 55: Add Gemini parser validation or mark as experimental
**Findings:** C-2.1
**Files:** `shared/takeout/parsers/activity.py`, `shared/takeout/registry.py`
**Action:** Either (a) obtain a real Gemini Takeout export, validate the parser, and add Gemini-specific tests, or (b) add an explicit `experimental=True` flag to the Gemini service config and log a warning when it is invoked: "Gemini parser is speculative and unvalidated against real data."
**Verification:** Run `--list-services` and verify Gemini shows the experimental flag. Or: Gemini-specific tests pass.

### Fix 56: Address Location parser memory usage for large Records.json
**Findings:** C-2.4, B-2.2
**Files:** `shared/takeout/parsers/location.py`, `shared/takeout/parsers/chrome.py`
**Action:** For `_parse_raw_records` in location.py, use `ijson` for streaming JSON parsing (or extract to temp file and stream like Gmail). For Chrome history, consider the same approach. At minimum, add a size check before loading: if `zf.getinfo(path).file_size > 500_000_000`, log a warning about memory usage.
**Verification:** Mock a 1GB Records.json file. Verify the parser either streams it or logs a clear memory warning.

### Fix 57: Add YAML frontmatter escaping for special characters
**Findings:** R-2.2
**Files:** `shared/takeout/chunker.py`
**Action:** Quote `people` list items that contain commas or special YAML characters. Use proper YAML list syntax (`- item` per line) instead of inline `[item1, item2]` for the people field. Alternatively, use `yaml.dump()` for frontmatter generation instead of manual string formatting.
**Verification:** Create a NormalizedRecord with a person name containing a comma ("Smith, John"). Verify the generated frontmatter round-trips correctly through `parse_frontmatter()`.

### Fix 58: Add production SPA serving mechanism
**Findings:** 7.07, 7.08
**Files:** `cockpit/api/app.py`, `Dockerfile.api`
**Action:** Add `StaticFiles` mount to FastAPI to serve the built React SPA from a `/static` path, with a catch-all route for SPA routing. Update the Dockerfile to include a multi-stage build that builds the SPA and copies the dist into the API image. Mount `profiles/` as a volume instead of copying.
**Verification:** Build the Docker image. Access `http://localhost:8050/` in a browser. Verify the SPA loads and displays dashboard data.

### Fix 59: Quote n8n quick-capture file path
**Findings:** R-8.11
**Files:** `<ai-agents>/n8n-workflows/quick-capture.json`
**Action:** In the "Read Info File" node, change `cat {{ $json.file }}` to `cat "{{ $json.file }}"` to prevent shell injection if the file path ever contains spaces or metacharacters.
**Verification:** Review the workflow JSON. Verify quotes are present around the interpolated file path.

### Fix 60: Create captures directory for n8n quick-capture
**Findings:** R-8.12
**Files:** Filesystem
**Action:** `mkdir -p ~/documents/rag-sources/captures/`. Add a health check or startup verification in the n8n workflow to test directory writability.
**Verification:** `test -d ~/documents/rag-sources/captures/` exits 0.

### Fix 61: Move Postgres password to .env variable reference
**Findings:** R-8.15
**Files:** `<llm-stack>/docker-compose.yml`, `<llm-stack>/.env`
**Action:** Add `POSTGRES_PASSWORD` to `.env` (or the `.envrc` replacement from Fix 1). Update docker-compose.yml to use `${POSTGRES_PASSWORD}` in the postgres service and all connection strings.
**Verification:** `grep -c 'localdev' <llm-stack>/docker-compose.yml` returns 0.

### Fix 62: Fix profiler_bridge "streaming" to use incremental aggregation
**Findings:** R-2.1
**Files:** `shared/takeout/profiler_bridge.py`
**Action:** Refactor `generate_facts()` to use incremental counters instead of accumulating all records in `by_service` lists. For services that only need aggregate statistics (Chrome domain counts, Search query counts), maintain running counters. This reduces memory usage from O(records) to O(unique_values).
**Verification:** Run profiler bridge on a large JSONL (100K+ records). Monitor memory usage; verify it stays under 200MB.

### Fix 63: Add connectivity check tests
**Findings:** C-4.3
**Files:** `tests/test_health_monitor.py`
**Action:** Add tests for all 5 connectivity check functions: `check_tailscale`, `check_ntfy`, `check_n8n_health`, `check_obsidian_sync`, `check_gdrive_sync_freshness`. Mock subprocess and HTTP calls.
**Verification:** `pytest tests/test_health_monitor.py -k connectivity` passes.

### Fix 64: Fix Obsidian plugin default system prompt
**Findings:** H-1.4
**Files:** `<obsidian-hapax>/src/types.ts`
**Action:** Update the `DEFAULT_SETTINGS.systemPrompt` to include the neurocognitive model framing from `SYSTEM_CONTEXT`. The base prompt should mention ADHD, autism, and executive function support to maintain coherence with the Python system's identity. The "Hapax" name can remain as the Obsidian-specific identity, but the operational context should align.
**Verification:** Build the plugin (`pnpm run build`). Open Obsidian, check default prompt in settings. Verify it mentions ADHD/autism.

### Fix 65: Document channel capability matrix
**Findings:** H-5.3
**Files:** `<hapaxromana>/docs/` or CLAUDE.md
**Action:** Create a capability matrix documenting which features are available in each operator channel (TUI, Web, Obsidian, Mobile/Telegram). Include the intentional design rationale for each channel's scope: "TUI for full control, Web for ambient monitoring, Obsidian for knowledge work, Mobile for alerts and quick capture."
**Verification:** The document exists and covers all documented channels.

### Fix 66: Add n8n workflow credential configuration documentation
**Findings:** R-8.10
**Files:** `<ai-agents>/n8n-workflows/README.md` (new)
**Action:** Document the import + credential configuration process for all 4 n8n workflows. Include: how to import JSON, which credentials need configuration, how to obtain Telegram bot token, and how to verify workflows are active.
**Verification:** README exists in `n8n-workflows/` with setup instructions.

### Fix 67: Add accommodation effectiveness feedback loop
**Findings:** H-3.4
**Files:** `cockpit/data/decisions.py`, `cockpit/data/nudges.py`, `cockpit/accommodations.py`
**Action:** Tag decision records with active accommodation state at the time of the decision (e.g., `energy_aware_active: true`). Add a periodic analysis (in profiler or activity_analyzer) that compares decision engagement rates during accommodated vs non-accommodated periods. Surface as a nudge if an accommodation appears ineffective.
**Verification:** Record decisions with accommodation metadata. Verify the metadata appears in `decisions.jsonl`.

### Fix 68: Store background task references in web API
**Findings:** 7.09
**Files:** `cockpit/api/cache.py`
**Action:** Store the task objects returned by `asyncio.create_task()` on the `DataCache` instance or a module-level set to prevent garbage collection.
**Verification:** Code review confirms references are stored.

### Fix 69: Add HTTP error status codes or freshness metadata to API
**Findings:** 7.10, H-5.4
**Files:** `cockpit/api/routes/data.py`
**Action:** Add an `X-Cache-Age` response header to all endpoints indicating seconds since the last successful refresh. Return 503 when cache fields are `None` (initial load failed). This gives the frontend a signal to display "loading" vs "data unavailable".
**Verification:** Stop a collector permanently. Verify the endpoint returns 503 after initial cache timeout. Verify `X-Cache-Age` header is present on all responses.

### Fix 70: Move /api/health/history to cache or thread
**Findings:** 7.11
**Files:** `cockpit/api/routes/data.py`
**Action:** Either add `health_history` to the `DataCache` slow refresh cycle, or wrap the `collect_health_history()` call in `asyncio.to_thread()` to prevent blocking the event loop.
**Verification:** Verify the endpoint responds within 100ms even with a large health-history.jsonl file.

### Fix 71: Restrict CORS to GET only
**Findings:** 7.12
**Files:** `cockpit/api/app.py`
**Action:** Change `allow_methods=["*"]` to `allow_methods=["GET", "OPTIONS"]` and `allow_headers=["*"]` to `allow_headers=["Content-Type"]`.
**Verification:** `curl -X POST localhost:8050/api/health` returns CORS error.

### Fix 72: Add web API endpoint tests
**Findings:** 7.15
**Files:** `tests/test_api.py`
**Action:** Add tests for the 10 untested endpoints: briefing, scout, drift, cost, goals, readiness, management, nudges, agents, accommodations. Include a test for `_to_dict()` with Path objects (catches 7.02). Include error scenarios (collector failure during refresh).
**Verification:** `pytest tests/test_api.py` covers all 15 endpoints.

### Fix 73: Add bash -c input sanitization for auto-fix
**Findings:** B-4.3
**Files:** `agents/health_monitor.py`
**Action:** Use `subprocess.run(shlex.split(cmd), ...)` instead of `subprocess.run(["bash", "-c", cmd], ...)` for remediation commands that don't require shell features. For commands that need shell expansion (e.g., `cd ... && docker compose ...`), ensure interpolated values are `shlex.quote()`-escaped.
**Verification:** Code review confirms no unquoted interpolation in shell commands.

---

## P3 -- Low (fix when convenient)

### Fix 74: Add test files for indirectly tested modules
**Findings:** C-1.2, C-1.3, C-1.4, C-1.5
**Files:** `tests/test_langfuse_config.py` (new), `tests/test_email_utils.py` (new), `tests/test_vault_utils.py` (new), update `tests/test_vault_writer.py`
**Action:** Create dedicated test files for `langfuse_config.py` (env var setting), `email_utils.py` (move tests from test_proton.py or add cross-references), `vault_utils.py` (parse_frontmatter edge cases). Add `write_digest_to_vault` test to `test_vault_writer.py`. Fix the missing `DIGESTS_DIR` patch in the test fixture (R-1.4).
**Verification:** `pytest tests/test_langfuse_config.py tests/test_email_utils.py tests/test_vault_utils.py` passes.

### Fix 75: Add operator cache invalidation API
**Findings:** R-1.2
**Files:** `shared/operator.py`
**Action:** Add a `reload_operator()` function that sets `_operator_cache = None`, forcing the next read to reload from disk. Export it for use by long-running processes (cockpit).
**Verification:** Load operator, modify operator.json, call `reload_operator()`. Verify new data is returned.

### Fix 76: Singleton Qdrant client
**Findings:** R-1.3
**Files:** `shared/config.py`
**Action:** Cache the QdrantClient instance in a module-level variable. Return the cached instance on subsequent calls to `get_qdrant()`.
**Verification:** `assert get_qdrant() is get_qdrant()` passes.

### Fix 77: Add embed() dimension validation
**Findings:** B-1.7
**Files:** `shared/config.py`
**Action:** After receiving the embedding result, check `len(result["embeddings"][0]) == 768`. Raise `RuntimeError` with a clear message if dimensions don't match.
**Verification:** Mock Ollama to return a 512-dimension vector. Verify `RuntimeError` is raised mentioning dimension mismatch.

### Fix 78: Fix Chrome timestamp timezone handling
**Findings:** R-2.3, R-2.4
**Files:** `shared/takeout/parsers/chrome.py`
**Action:** Change `datetime.fromtimestamp(unix_seconds)` to `datetime.fromtimestamp(unix_seconds, tz=timezone.utc)` in both `_chrome_time_to_datetime` and the bookmark `ADD_DATE` parser.
**Verification:** Parse a known Chrome timestamp. Verify the result is UTC, not local time.

### Fix 79: Fix Proton processor records_skipped counter
**Findings:** C-2.5
**Files:** `shared/proton/processor.py`
**Action:** Count records filtered by `--since` by having the parser yield a sentinel or count, or by counting the delta between records seen and records written.
**Verification:** Run with `--since` on a date that filters some records. Verify `records_skipped > 0` in the summary output.

### Fix 80: Make progress file write atomic
**Findings:** R-2.8
**Files:** `shared/takeout/progress.py`
**Action:** Replace `self.progress_file.write_text(json.dumps(data, indent=2))` with write-to-temp-then-rename pattern.
**Verification:** Code review confirms atomic write pattern.

### Fix 81: Remove orphaned InfraPanel and ScoutPanel widget classes
**Findings:** C-6.1, H-4.1
**Files:** `cockpit/widgets/infra_panel.py`, `cockpit/widgets/scout_panel.py`
**Action:** Delete the `InfraPanel(Static)` class from `infra_panel.py` and `ScoutPanel(Static)` class from `scout_panel.py`. Keep the `render_infra_detail()` and `render_scout_detail()` functions which are actively used by `app.py`.
**Verification:** `grep -rn "InfraPanel\|ScoutPanel" cockpit/` returns no class references. Cockpit starts without errors.

### Fix 82: Update manual timer schedule to be dynamic
**Findings:** C-6.4
**Files:** `cockpit/manual.py`
**Action:** Replace the hardcoded `TIMER_SCHEDULE` list with dynamic generation from `systemctl --user list-timers`, or at minimum add the 3 missing timers (digest, knowledge-maint, scout). Also add `/accommodate`, `/pending`, and `/flush` to the HELP_TEXT in `screens/chat.py`.
**Verification:** Run cockpit manual view. Verify all 10 timers appear.

### Fix 83: Remove dead Perplexity extraction prompt
**Findings:** R-3.2
**Files:** `agents/profiler.py`
**Action:** Remove the Perplexity prompt generation from `generate_extraction_prompts()` (line 932-943).
**Verification:** Run `profiler --generate-prompts`. Verify no Perplexity prompt appears.

### Fix 84: Add VCF line folding support to contacts parser
**Findings:** C-2.3
**Files:** `shared/takeout/parsers/contacts.py`
**Action:** Add RFC 6350 line unfolding before parsing: `text = re.sub(r"\r?\n[ \t]", "", text)` (matching the pattern already used in calendar.py:156).
**Verification:** Create a VCF with a folded address line. Verify the full address is extracted.

### Fix 85: Fix JSONL corruption resilience consistency
**Findings:** B-2.10
**Files:** `shared/takeout/progress.py`
**Action:** Change the progress tracker from single-JSON to be more resilient: catch `json.JSONDecodeError` per field rather than discarding all progress. Or switch to a write-to-temp-then-rename pattern (already addressed by Fix 80).
**Verification:** Corrupt one field in the progress JSON. Verify the tracker preserves other fields.

### Fix 86: Add frontmatter enrichment for dropped fields
**Findings:** B-2.11
**Files:** `rag-pipeline/ingest.py`
**Action:** Add `"record_id"`, `"categories"`, and `"location"` to the `enrichment_keys` set in `enrich_payload()`. This makes these fields queryable in Qdrant.
**Verification:** Ingest a takeout-generated markdown file with location data. Query Qdrant for that point. Verify `location` and `categories` appear in the payload.

### Fix 87: Fix profiler reader count documentation
**Findings:** C-3.5
**Files:** CLAUDE.md / documentation
**Action:** Update references to "16 readers" to "14 reader functions" with a note that 3 bridged source types have both text and structured paths.
**Verification:** Grep for "16 readers" in documentation. Verify corrected to "14".

### Fix 88: Add data freshness indicators to operator interfaces
**Findings:** H-5.4
**Files:** `cockpit/copilot.py`, `cockpit/widgets/sidebar.py`
**Action:** Add a copilot rule that checks data collector freshness (e.g., if briefing data is more than 26 hours old, if cost data hasn't refreshed in 3 cycles). Surface as a P2 copilot observation: "Cost data hasn't refreshed in 15 minutes -- Langfuse may be unreachable."
**Verification:** Mock a collector to return stale data for 3 cycles. Verify the copilot surfaces a freshness warning.

### Fix 89: Expand micro-probe coverage to more dimensions
**Findings:** H-4.3
**Files:** `cockpit/micro_probes.py`
**Action:** Add probes for at least 4-5 additional dimensions: `work_patterns` ("How do you typically structure your work day?"), `tool_preferences` ("What tool do you reach for first when starting a new task?"), `decision_style` ("How do you usually decide between two technical approaches?"), `creative_preferences` ("What sparks your best creative work?").
**Verification:** `len(PROBES) >= 12` and probes cover at least 5 distinct dimensions.

### Fix 90: Consolidate VAULT_PATH imports
**Findings:** H-2.5
**Files:** `shared/vault_writer.py`, `cockpit/data/management.py`, `shared/management_bridge.py`
**Action:** Define `VAULT_PATH` once (in `shared/config.py` or `shared/vault_writer.py`) and import from there in all other modules.
**Verification:** `grep -rn "OBSIDIAN_VAULT_PATH" --include="*.py" | grep -v "config.py\|vault_writer.py" | grep -c os.environ` returns 0.

### Fix 91: Minor fixes (grouped low-severity items)
**Findings:** B-1.3, B-1.4, B-1.5, B-1.6, R-1.4, B-2.5, B-2.7, B-2.8, B-2.9, B-2.3, R-3.1, R-3.3, R-3.4, B-3.4, B-3.5, B-3.6, C-3.6, C-4.2, C-4.4, C-4.5, C-4.6, R-4.3, R-4.4, R-4.5, B-4.6, B-4.7, B-4.8, R-5.3, R-5.5, B-5.5, B-5.8, C-6.3, R-6.4, B-6.6, B-5.4, R-8.4, R-8.6, H-3.5
**Files:** Various
**Action:** These are individually low-impact findings that should be addressed opportunistically:
- Improve `notify.py` debug-level logging for outer exception catches (B-1.3)
- Check vault_writer return values in briefing.py and digest.py (B-1.4)
- Fix DIGESTS_DIR patch in test fixture (R-1.4)
- Add `_feedback_facts` direction validation instead of defaulting to "given" (R-3.4)
- Document equal-confidence merge behavior (R-3.1)
- Add Docker volume/network capture to introspect (C-4.2)
- Fix drift detector doc truncation to preserve section boundaries (B-4.6)
- Add score threshold to research agent Qdrant queries (B-5.8)
- Add digest Qdrant scroll pagination for >200 docs (B-5.4)
- Add decisions.jsonl rotation (B-6.6)
- Add systemd hardening directives (R-8.4)
- Widen Sunday timer window margins (R-8.6)
- Handle extra dimensions gracefully in `generate_digest()` instead of silently dropping (C-3.6)
- Increase near-duplicate detection sampling beyond 500 points in knowledge_maint (R-4.3)
**Verification:** Each fix is individually verifiable through unit tests or manual inspection.

### Fix 92: Missing medium-severity fixes (added during spec review)
**Findings:** C-3.1, B-3.2, R-2.6, R-4.2, R-5.1, B-5.2, B-6.1, H-3.2
**Files:** Various across `agents/`, `cockpit/`, `shared/`
**Action:**
- Add unit tests for the 6 individual reader functions in `profiler_sources.py` (C-3.1)
- Add per-batch error handling in `ProfileStore.index_profile()` so partial failures don't lose the entire index run (B-3.2)
- Make structured JSONL append atomic via write-to-temp-then-rename pattern in `shared/takeout/profiler_bridge.py` (R-2.6)
- Guard `knowledge_maint` stale source detection against temporary filesystem unavailability — check path accessibility before comparing mtimes (R-4.2)
- Add None guard in `code_review.py` system prompt concatenation to prevent crash when `get_system_prompt_fragment()` returns None (R-5.1)
- Add explicit check for empty Tavily results in `scout.py` and log warning — don't silently pass empty search results to LLM evaluation (B-5.2)
- Add streaming timeout in `cockpit/chat_agent.py` so a stalled SSE stream doesn't hang the chat indefinitely (B-6.1)
- Plan web dashboard action pathway: at minimum, add nudge dismiss/execute buttons that POST to a new API endpoint; this is the most significant ADHD accommodation gap in the web layer (H-3.2)
**Verification:** Each item verifiable via targeted unit test or manual check. H-3.2 requires a design decision before implementation.

---

## Work Streams

### WS-1: Security & Secrets
**Fixes:** 1, 2, 3, 4, 59, 61
**Findings:** C-8.1, C-8.2, C-8.3, C-8.4, R-8.11, R-8.15
**Estimated scope:** 6 files, ~50 LOC changes
**Priority range:** P0-P2

The .env file is the single biggest security gap. Fixes 1-4 are P0 because they address plaintext secrets, weak session keys, broken mobile channel, and wrong vault paths. Fix 59 (path traversal) and Fix 61 (postgres password) are P2 defense-in-depth.

### WS-2: Error Handling & Resilience
**Fixes:** 5, 11, 13, 14, 15, 16, 21, 22, 30, 31, 32, 39, 43, 73, 92 (partial: B-3.2, R-5.1, B-5.2, B-6.1)
**Findings:** B-5.1, 7.01, 7.03, B-3.1, B-2.1, B-4.1, R-4.1, B-1.1, B-1.2, B-4.2, B-4.4, B-4.5, B-3.4, B-5.3, B-6.3, B-4.3, B-3.2, R-5.1, B-5.2, B-6.1
**Estimated scope:** 14 files, ~400 LOC changes
**Priority range:** P1-P2

The most operationally impactful work stream. Addresses cascading failures in the web API, missing LLM error handling in all agents, unbounded file growth, blocking I/O, and missing timeouts. Fix 5 (LLM failure handling) alone affects 7 files.

### WS-3: Agent Coherence
**Fixes:** 6, 7, 33, 34, 64
**Findings:** H-1.1, H-1.2, H-1.3, C-5.6, R-5.2, H-1.4
**Estimated scope:** 8 files, ~100 LOC changes
**Priority range:** P1-P2

Restores the coherent operator model across all LLM agents. Every agent gets neurocognitive awareness (P1). Digest gets context tools (P1). Code review model override gets fixed (P2). Obsidian plugin aligns with system identity (P2). Scout staleness check is enforced (P2).

### WS-4: Data Flow Completeness
**Fixes:** 17, 23, 24, 40, 41, 42, 54, 67, 92 (partial: R-2.6, H-3.2)
**Findings:** H-3.1, C-6.2, R-2.5, R-2.7, R-6.2, H-3.3, R-6.3, R-6.5, B-6.7, H-5.2, H-3.4, R-2.6, H-3.2
**Estimated scope:** 10 files, ~350 LOC changes
**Priority range:** P1-P2

Completes the decision capture loop (dismissed/expired), fixes resume reliability for takeout processing, makes persistent state writes atomic, caps the nudge attention budget, and adds accommodation feedback. The nudge cap (Fix 54) is the most impactful ADHD accommodation fix in the audit.

### WS-5: Test Coverage
**Fixes:** 18, 19, 26, 27, 35, 36, 37, 63, 72, 74, 92 (partial: C-3.1)
**Findings:** C-1.1, C-1.6, C-2.2, C-3.2, C-3.3, C-5.2, C-5.3, C-5.4, C-4.3, 7.15, C-1.2, C-1.3, C-1.4, C-1.5, C-3.1
**Estimated scope:** 10+ new test files, ~2000 LOC new tests
**Priority range:** P1-P3

Addresses the largest coverage gaps: scout.py (544 LOC untested), ingest.py (525 LOC untested), profiler pipelines (untested orchestration), connectivity checks (untested), web API (10/15 endpoints untested). Scout tests (Fix 35) are P2 due to the complexity and external API dependency.

### WS-6: Dead Code & Legacy Cleanup
**Fixes:** 53, 81, 82, 83, 87
**Findings:** H-4.2, H-2.4, C-3.4, C-6.1, H-4.1, C-6.4, R-3.2, C-3.5
**Estimated scope:** 5 files, ~200 LOC removed
**Priority range:** P2-P3

Remove the legacy `store_to_qdrant()` path and CLI flag, delete orphaned widget classes, remove the dead Perplexity prompt, update manual timer list, and fix documentation count. Low risk, high clarity improvement.

### WS-7: Infrastructure Hardening
**Fixes:** 9, 10, 45, 46, 47, 48, 49, 50, 51, 60, 66
**Findings:** R-8.8, R-8.9, R-8.1, R-8.2, R-8.3, R-8.5, R-8.7, 7.13, 7.14, R-8.13, R-8.14, R-8.12, R-8.10
**Estimated scope:** 12 files, ~150 LOC changes
**Priority range:** P1-P2

Hardens the Docker Compose stack (resource limits, image pinning, healthchecks), fixes backup gaps (profile-facts collection, n8n volume), adds systemd resource limits, configures timer ordering, and documents runtime dependencies.

### WS-8: Type Safety & API Contracts
**Fixes:** 12, 44, 52, 58, 68, 69, 70, 71, 90
**Findings:** 7.02, 7.04, 7.05, 7.06, H-5.1, H-2.2, 7.07, 7.08, 7.09, 7.10, 7.11, 7.12, H-2.5
**Estimated scope:** 12 files across 2 repos, ~500 LOC changes
**Priority range:** P1-P3

Fixes the Python/TypeScript interface boundary: Path serialization bug (P1), missing TS types (P2), production SPA serving (P2), API error codes and freshness headers (P2), CORS tightening (P3), and consolidated path constants (P3).

### WS-9: Data Pipeline Robustness
**Fixes:** 20, 25, 28, 29, 55, 56, 57, 62, 78, 79, 80, 84, 85, 86, 92 (partial: R-4.2)
**Findings:** R-1.1, B-2.6, B-3.7, B-3.3, C-2.1, C-2.4, B-2.2, R-2.2, R-2.1, R-2.3, R-2.4, C-2.5, R-2.8, C-2.3, B-2.10, B-2.11, R-4.2
**Estimated scope:** 14 files, ~500 LOC changes
**Priority range:** P2-P3

Addresses the data ingestion and profile pipeline: operator.json schema validation, ingest tracking to avoid re-embedding on restart, YAML frontmatter escaping, memory usage for large files, atomic writes, timezone handling, and enrichment field mapping.

### WS-10: Operator Experience
**Fixes:** 65, 88, 89
**Findings:** H-5.3, H-5.4, H-4.3
**Estimated scope:** 4 files, ~200 LOC changes
**Priority range:** P2-P3

Improves the operator's ability to understand and interact with the system: channel capability documentation, data freshness indicators in the copilot, and expanded micro-probe coverage for better profile quality.

---

## Execution Order

The recommended execution order considers dependencies and risk reduction:

1. **Week 1**: WS-1 (Security, P0) -- immediate. All 4 critical fixes.
2. **Week 1**: WS-2 partial (Fixes 5, 11, 13, 14, 16) -- the highest-impact error handling fixes.
3. **Week 2**: WS-3 (Agent Coherence) -- restores the system's founding design principle.
4. **Week 2**: WS-4 partial (Fixes 17, 40, 41, 54) -- decision capture and nudge cap.
5. **Week 2**: WS-7 partial (Fixes 9, 10, 45, 47, 49, 51) -- infrastructure hardening.
6. **Week 3-4**: WS-5 (Test Coverage) -- systematic coverage improvement.
7. **Week 3-4**: WS-8 (Type Safety) -- web layer interface fixes.
8. **Week 3-4**: WS-9 (Data Pipeline) -- incremental robustness improvements.
9. **Ongoing**: WS-6 (Cleanup), WS-10 (Operator Experience), remaining P3 items.
