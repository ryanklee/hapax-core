# Domain 4: Health & Observability -- Audit Findings

## Inventory

| File | LOC | Test File | Test LOC | Test:Source |
|------|-----|-----------|----------|-------------|
| `agents/health_monitor.py` | 1,439 | `tests/test_health_monitor.py` | 689 | 0.48 |
| `agents/introspect.py` | 486 | `tests/test_introspect.py` | 679 | 1.40 |
| `agents/drift_detector.py` | 352 | `tests/test_drift_detector.py` | 453 | 1.29 |
| `agents/activity_analyzer.py` | 666 | `tests/test_activity_analyzer.py` | 371 | 0.56 |
| `agents/knowledge_maint.py` | 535 | `tests/test_knowledge_maint.py` | 401 | 0.75 |
| **Total** | **3,478** | | **2,593** | **0.75** |

Supporting files examined:
- `shared/langfuse_client.py` (59 LOC) -- consolidated Langfuse API client
- `<local-bin>/health-watchdog` (105 LOC) -- bash wrapper for systemd timer
- `<systemd-user>/health-monitor.service` -- systemd unit file

---

## Focus Area 1: All 49 Health Checks

### Check Group Inventory

| # | Group | Check Function | Checks Produced | Total |
|---|-------|---------------|-----------------|-------|
| 1 | `docker` | `check_docker_daemon` | 1 (daemon reachability) | |
| 2 | `docker` | `check_compose_file` | 1 (file existence) | |
| 3 | `docker` | `check_docker_containers` | N (one per container, dynamic) | ~12 |
| | | | **docker subtotal** | **~14** |
| 4 | `gpu` | `check_gpu_available` | 1 (nvidia-smi) | |
| 5 | `gpu` | `check_gpu_vram` | 1 (usage %, loaded models) | |
| 6 | `gpu` | `check_gpu_temperature` | 1 (thermal) | |
| | | | **gpu subtotal** | **3** |
| 7 | `systemd` | `check_systemd_services` | 5 (rag-ingest, profile-update.timer, digest.timer, knowledge-maint.timer, midi-route) | **5** |
| 8 | `qdrant` | `check_qdrant_health` | 1 (healthz endpoint) | |
| 9 | `qdrant` | `check_qdrant_collections` | 3 (documents, samples, claude-memory) | |
| | | | **qdrant subtotal** | **4** |
| 10 | `profiles` | `check_profile_files` | 3 (.state.json, operator.json, operator-profile.json) | |
| 11 | `profiles` | `check_profile_staleness` | 1 (last_run age) | |
| | | | **profiles subtotal** | **4** |
| 12 | `endpoints` | `check_service_endpoints` | 4 (litellm, ollama, langfuse, open-webui) | **4** |
| 13 | `credentials` | `check_pass_store` | 1 (password-store dir) | |
| 14 | `credentials` | `check_pass_entries` | 5 (api/anthropic, api/google, litellm/master-key, langfuse/public-key, langfuse/secret-key) | |
| | | | **credentials subtotal** | **6** |
| 15 | `disk` | `check_disk_usage` | 1 (/home percentage) | **1** |
| 16 | `models` | `check_ollama_models` | 4 (nomic-embed-text-v2-moe, qwen2.5-coder:32b, qwen2.5:7b, deepseek-r1:14b) | **4** |
| 17 | `auth` | `check_litellm_auth` | 1 (API key validation) | |
| 18 | `auth` | `check_langfuse_auth` | 1 (Basic auth validation) | |
| | | | **auth subtotal** | **2** |
| 19 | `connectivity` | `check_tailscale` | 1 (VPN status) | |
| 20 | `connectivity` | `check_ntfy` | 1 (push service health) | |
| 21 | `connectivity` | `check_n8n_health` | 1 (workflow engine health) | |
| 22 | `connectivity` | `check_obsidian_sync` | 1 (desktop app running) | |
| 23 | `connectivity` | `check_gdrive_sync_freshness` | 1 (timer/dir check) | |
| | | | **connectivity subtotal** | **5** |

**Effective total: ~52 checks** (varies with container count). The "49" figure in documentation is approximate -- the actual count depends on how many Docker containers are running. With the documented 12 containers, the count is approximately 52.

### Threshold Assessment

| Check | Threshold | Sensibility | Notes |
|-------|-----------|-------------|-------|
| `gpu.vram` | <90% healthy, 90-95% degraded, >95% failed | **Good** -- RTX 3090 has 24GB; 90% = 21.6GB leaves ~2.4GB headroom for OS/display | |
| `gpu.temperature` | <80C healthy, 80-90 degraded, >90 failed | **Good** -- RTX 3090 thermal throttles at 93C | |
| `disk.home` | <85% healthy, 85-95% degraded, >95% failed | **Good** -- standard thresholds | |
| `profiles.staleness` | <24h healthy, 24-72h degraded, >72h failed | **Reasonable** -- profile-update.timer runs every 12h | |
| Docker container: core down | FAILED | **Correct** -- qdrant/ollama/postgres/litellm are essential | |
| Docker container: non-core down | DEGRADED | **Correct** -- langfuse/n8n etc are useful but not critical | |

### Checks That Could Always Pass

- `connectivity.tailscale`: Returns HEALTHY if Tailscale is "not installed" (line 929-935). This is intentional ("planned infrastructure, not a failure") but means the check never detects degradation until Tailscale is actually installed.
- `connectivity.gdrive-sync`: Returns HEALTHY if the gdrive directory doesn't exist (line 1041-1047). Same reasoning.
- `systemd.midi-route.service`: Optional (`required=False`), so inactive = HEALTHY (line 401, 443-444).

These are design choices, not bugs -- they represent planned-but-not-yet-deployed infrastructure.

---

## Focus Area 2: Auto-Fix Safety

The auto-fix system (`--fix` flag, `run_fixes()` at line 1271) operates as follows:

### Fix Mechanism

1. Collects all checks with `remediation` field where `status != HEALTHY` (line 1276-1279)
2. Lists them for the operator (line 1284-1289)
3. **Requires interactive confirmation** by default (`[y/N]` prompt, line 1291-1299)
4. `--yes` flag skips confirmation (line 1291, used by watchdog)
5. Each remediation is executed via `bash -c` with 30s timeout (line 1305)

### Remediation Commands by Check

| Check | Remediation Command | Blast Radius | Risk |
|-------|--------------------|--------------|------|
| `docker.daemon` | `sudo systemctl start docker` | System-wide | **Medium** -- requires sudo, won't work unattended |
| `docker.<service>` | `docker compose up -d <service>` | Single container | **Low** -- restarts one container |
| `qdrant.health` | `docker compose up -d qdrant` | Single container | **Low** |
| `qdrant.<collection>` | `curl -X PUT` to create collection | Creates new collection | **Low** -- additive only |
| `profiles.*` | `uv run python -m agents.profiler --auto` | Runs profiler | **Low** -- generates files |
| `systemd.*` | `systemctl --user enable --now <timer>` | Enables timer | **Low** |
| `endpoints.*` | `docker compose up -d <service>` | Single container | **Low** |
| `credentials.*` | `pass insert <entry>` | Interactive | **None** -- won't work unattended |
| `disk.home` | `docker system prune -f` | Removes unused Docker objects | **Medium** -- deletes stopped containers, dangling images |
| `gpu.vram` | `docker exec ollama ollama stop <model>` | Unloads one model | **Low** |
| `models.*` | `docker exec ollama ollama pull <model>` | Downloads model | **Low** -- additive, but uses bandwidth |
| `connectivity.*` | Various compose/systemctl commands | Single service | **Low** |

### Safety Assessment

- **Dry-run option**: The `--fix` flag without `--yes` is effectively a dry-run that lists commands. There is no separate `--dry-run` flag; the default behavior without `--fix` is report-only.
- **Watchdog auto-fix**: The `health-watchdog` bash script (line 31) passes `--fix --yes`, **bypassing confirmation**. This is the primary risk vector.
- **No fix idempotency tracking**: If `docker compose up -d` fails repeatedly, the watchdog will retry every 15 minutes indefinitely with no backoff.

---

## Focus Area 3: Connectivity Checks (11th Group)

### Timeout Analysis

- `check_tailscale`: Uses `run_cmd` default timeout of **10 seconds** (line 926, via `run_cmd` default at line 115)
- `check_ntfy`: Uses `http_get` with **3.0 second** timeout (line 977)
- `check_n8n_health`: Uses `http_get` with **3.0 second** timeout (line 999)
- `check_obsidian_sync`: Uses `run_cmd` (`pgrep`) with **10 second** timeout (line 1020) -- effectively instant for pgrep
- `check_gdrive_sync_freshness`: Uses `run_cmd` with **10 second** timeout (line 1050)

### DNS False Positive Risk

All connectivity checks target **localhost** URLs (ntfy at localhost:8090, n8n at localhost:5678). No DNS resolution is involved. The Tailscale check uses the local `tailscale` CLI binary. **DNS is not a false-positive risk for this group.**

### Endpoint Validity

| Check | Endpoint | Valid? |
|-------|----------|--------|
| ntfy | `http://localhost:8090/v1/health` | Correct per ntfy docs |
| n8n | `http://localhost:5678/healthz` | Correct per n8n docs |
| Tailscale | `tailscale status --json` | Correct CLI usage |
| Obsidian | `pgrep -x obsidian` | Correct for desktop process detection |
| gdrive-sync | `systemctl --user is-active gdrive-sync.timer` | Correct |

The ntfy URL uses a configurable base: `os.environ.get("NTFY_BASE_URL", "http://localhost:8090")` (line 976), which is good practice.

---

## Focus Area 4: Drift Detector Accuracy

### Comparison Method

The drift detector performs **semantic comparison via LLM**, not simple pattern matching:

1. `generate_manifest()` from `introspect.py` captures live system state (Docker containers, systemd units, Qdrant collections, Ollama models, GPU, LiteLLM routes, disk, ports, pass entries) -- this is the **ground truth** (line 129-143)
2. `load_docs()` reads all documentation files (CLAUDE.md files across projects, agent-architecture.md) (line 70-82)
3. Both are sent to an LLM (`get_model("fast")` = claude-haiku) with detailed instructions (line 87-115)
4. The LLM returns structured `DriftReport` with typed `DriftItem` objects (line 38-52)

This is a genuine live-state-vs-docs comparison, not pattern matching.

### `--fix` Mode

The `--fix` mode (line 253-294):
1. Filters to high/medium severity items only (line 255)
2. Groups by doc file (line 260-261)
3. Sends each doc + its drift items to a second LLM call (`fix_agent`) (line 287-289)
4. LLM generates `DocFix` objects with `original` (exact substring from doc) and `corrected` (replacement) (line 216-222)
5. Output is **display-only** -- "To apply: review each change, then manually update the files" (line 316)

### Could It Generate Incorrect Doc Fragments?

**Yes, this is inherent to the LLM approach.** The fix agent prompt instructs the LLM to produce exact text replacements (line 231-244), but:
- The "original" field may not be an exact match from the document
- The "corrected" text is LLM-generated and could introduce errors
- There is **no automated application** -- fixes are human-reviewed (line 316)

The manual review step is a critical safety valve.

---

## Focus Area 5: Near-Duplicate Detection (knowledge_maint.py)

### Threshold: 0.98 Cosine Similarity

The `DEFAULT_SCORE_THRESHOLD = 0.98` (line 42) is **quite aggressive (conservative about declaring duplicates)**. At 0.98 cosine similarity, vectors must be nearly identical. For comparison:
- 0.98 typically catches exact or near-exact duplicates (same document re-ingested)
- 0.95 would catch paraphrases or very similar chunks
- 0.90 would catch topically similar content

**Assessment: Appropriately conservative.** Better to miss some duplicates than to incorrectly merge distinct content. The threshold is also configurable via `--score-threshold` CLI flag (line 503-504).

### Comparison Strategy

The comparison is **not pairwise across all vectors**. The algorithm (lines 174-245):

1. Scrolls up to `sample_limit=500` points with vectors (line 195-196)
2. For each point not already in a cluster, searches its 10 nearest neighbors above the threshold (line 221-226)
3. Groups matching neighbors into clusters (line 231-243)
4. Uses a `seen_ids` set to avoid re-clustering already-clustered points (line 213)

This is **O(n * k)** where n=sample_limit and k=10 (neighbors per search), with each search being O(log N) in Qdrant's HNSW index. This is efficient for the 500-point sample.

### Performance Implications for Large Collections

The `sample_limit=500` (line 177) bounds the operation. For a collection with 10,000+ points, **only 500 are checked**. This means:
- Duplicates among the first 500 scrolled points are detected
- Duplicates elsewhere are missed
- No randomized sampling -- scrolls from the beginning, which may bias toward older points
- The `scroll` with no filter returns points in internal order (typically insertion order)

---

## Focus Area 6: Stale Source Pruning (knowledge_maint.py)

### Staleness Criteria

A source is "stale" when its **file path no longer exists on disk** (line 101-135):
1. Scrolls all points in a collection, extracting the `source` payload field
2. Checks `Path(source).exists()` for each unique source path
3. Sources where the file is gone are marked stale

### Could It Delete Important Data?

**Risk is moderate, mitigated by dry-run default:**
- A file could be temporarily moved/renamed -- its vectors would be pruned
- A mounted volume could be temporarily unavailable -- all its vectors would appear stale
- An NFS/network path that's temporarily unreachable would trigger false positives

### Dry-Run Default

**Yes, dry-run is the default.** The `MaintenanceReport.dry_run` defaults to `True` (line 61). The CLI requires explicit `--apply` to perform deletions (line 492, 507). The `prune_stale_sources` function checks `dry_run` parameter and returns count without deleting (line 149).

---

## Focus Area 7: Manifest Completeness (introspect.py)

### What It Captures

| System Aspect | Captured | Method |
|--------------|----------|--------|
| Docker containers | Yes | `docker compose ps --format json` |
| Container ports | Yes | Publishers from compose JSON |
| Docker version | Yes | `docker info --format` |
| Systemd user services | Yes | `systemctl --user list-units --type=service` |
| Systemd user timers | Yes | `systemctl --user list-units --type=timer` |
| Qdrant collections | Yes | HTTP API `/collections` + per-collection detail |
| Ollama models | Yes | HTTP API `/api/tags` |
| GPU state | Yes | `nvidia-smi` CSV output + Ollama `/api/ps` |
| LiteLLM routes | Yes | HTTP API `/v1/models` (requires API key) |
| Disk usage | Yes | `df -h /home` |
| Listening ports (127.0.0.1) | Yes | `ss -tlnp` |
| Pass entries | Yes | `rglob("*.gpg")` on password store |
| Profile files | Yes | `iterdir()` on profiles directory |
| Compose file path | Yes | Checks if file exists |
| OS info | Yes | `uname -sr` |

### Blind Spots

| Missing Aspect | Impact |
|---------------|--------|
| **System-level systemd services** (not `--user`) | Docker, NVIDIA driver, PipeWire -- not captured |
| **Docker volumes and networks** | Storage state and network topology missing |
| **Docker image digests** | Cannot verify pinned images match running images |
| **PipeWire/ALSA audio state** | Music production audio routing not inspected |
| **MIDI device/port state** | `aconnect -l` not queried |
| **Network interfaces / Tailscale IP** | Connectivity metadata missing |
| **Cron jobs** (if any) | Only systemd timers captured |
| **Python/Node versions** | Runtime environment not captured |
| **Qdrant collection config details** (HNSW params, replication) | Only size/distance captured |
| **n8n workflow state** | Workflow list/status not queried |
| **Langfuse prompt versions** | Seeded prompts not inventoried |
| **Vault structure** | Obsidian folder state not captured |

Most of these blind spots are low-impact for drift detection purposes, but the Docker volumes/networks gap could matter for infrastructure recovery.

---

## Focus Area 8: Activity Analyzer Langfuse Queries

### URL Encoding

The `langfuse_client.py` uses `urllib.parse.urlencode(params)` (line 39) for query parameters. The `fromTimestamp` parameter receives an ISO datetime via `since.isoformat()` (line 146).

**The `urlencode` function correctly encodes the `+` in `+00:00` timezone offsets** as `%2B`. This was a previously documented issue that has been properly resolved by centralizing the Langfuse client.

### Date Range Filtering

- Traces: filtered by `fromTimestamp` (line 146) -- server-side filtering
- Observations: filtered by `fromStartTime` (line 173) -- server-side filtering
- Pagination: loops until `len(all_traces) >= total` from meta (line 155)

### When Langfuse Is Down

The `langfuse_get` function returns `{}` on any error (line 48-50 of `langfuse_client.py`). The `collect_langfuse` function checks `if not LANGFUSE_PK` and returns empty `LangfuseActivity()` (line 138-139). If Langfuse is down mid-pagination, the loop gets empty `data` and breaks (line 151-152).

**Result: Graceful degradation.** Activity report shows "No traces in window" but doesn't crash. The `data_sources.langfuse_available` field tracks whether data was retrieved (line 476).

---

## Focus Area 9: Health History Growth

### Where It's Written

The `health-watchdog` bash script appends one JSON line per run to `profiles/health-history.jsonl` (line 80-97 of `<local-bin>/health-watchdog`).

### Growth Rate

- Timer fires every 15 minutes = 96 entries/day
- Each entry is approximately 200-400 bytes (JSON with timestamp, status, counts, failed check names)
- Daily growth: ~20-40 KB
- Monthly growth: ~600 KB - 1.2 MB
- 6 months: ~3.6 - 7.2 MB
- 1 year: ~7.2 - 14.4 MB

### Is It Bounded?

**No. The file is never pruned, truncated, or rotated.**

- The `collect_health_trend` function in `activity_analyzer.py` reads the **entire file** into memory (line 246), parsing every line, then filters by timestamp
- The `format_history` function in `health_monitor.py` also reads the **entire file** (line 1328), then takes the last N entries
- The `collect_health_history` function in `cockpit/data/health.py` reads the entire file (referenced but not in audit scope)

After 6 months at 15-minute intervals, the file will contain ~17,500 lines. After a year, ~35,000 lines. This is manageable for modern systems but represents unbounded growth with no lifecycle management.

---

## Completeness Findings

### C-4.1: knowledge_maint COLLECTIONS list missing `profile-facts` [medium]

**File:** `agents/knowledge_maint.py:41`

The `COLLECTIONS` constant is `["documents", "samples", "claude-memory"]`, but the system also has a `profile-facts` collection (created by `shared/profile_store.py`). This collection is not maintained by knowledge_maint, meaning it never gets stale-source pruning or deduplication.

### C-4.2: Introspect does not capture Docker volumes or networks [low]

**File:** `agents/introspect.py`

The manifest captures containers and ports but not volumes or networks. For infrastructure recovery or drift detection of storage configuration, this is a gap. Docker compose volumes define data persistence; their absence from the manifest means volume misconfiguration cannot be detected by drift detector.

### C-4.3: No connectivity test for the connectivity checks [low]

**File:** `tests/test_health_monitor.py`

The test file covers docker, gpu, systemd, qdrant, profiles, endpoints, credentials, disk, models, and auth groups thoroughly. However, there are **no tests for any of the 5 connectivity check functions** (tailscale, ntfy, n8n_health, obsidian_sync, gdrive_sync_freshness). The registry test at line 682 verifies the group exists but no individual check functions are tested.

### C-4.4: Activity analyzer does not collect knowledge-maint trends with time filtering [low]

**File:** `agents/activity_analyzer.py:346-368`

The `collect_knowledge_maint_trend` and `collect_digest_trend` functions accept a `since` parameter but do not use it to filter history entries by time. They only read the latest report and count total history lines. Compare with `collect_health_trend` which properly filters by timestamp. The `since` parameter is misleading.

### C-4.5: Introspect missing Qdrant `profile-facts` collection detection [low]

**File:** `agents/introspect.py:195-222`

The `collect_qdrant` function dynamically discovers all collections, so `profile-facts` would appear in the manifest. However, the health monitor's `REQUIRED_QDRANT_COLLECTIONS` (line 81 of health_monitor.py) only lists 3 collections. If `profile-facts` goes missing, it won't trigger a health check failure.

### C-4.6: Drift detector DOC_FILES list is static [low]

**File:** `agents/drift_detector.py:57-68`

The doc file list is computed at **module import time** by iterating `~/projects/`. If new project directories are created after the module is imported, their CLAUDE.md files won't be included. For a long-running process this could be stale, though in practice the detector is invoked as a one-shot CLI.

---

## Correctness Findings

### R-4.1: Health history file read into memory entirely for time-filtered queries [medium]

**File:** `agents/activity_analyzer.py:245-258`

The `collect_health_trend` function reads the entire `health-history.jsonl` into memory, parses every line, and filters by timestamp. With 6 months of 15-minute writes (~17,500 lines), this loads and parses all entries even when only looking at the last 24 hours. Not incorrect per se, but inefficient and scales poorly.

### R-4.2: Stale source detection vulnerable to temporary filesystem unavailability [medium]

**File:** `agents/knowledge_maint.py:128`

The `find_stale_sources` function uses `Path(source).exists()` to determine staleness. If a source path is on a temporarily unmounted volume or network share, all its vectors will be incorrectly identified as stale. With `--apply`, this causes data loss. The dry-run default mitigates this, but the watchdog/timer could theoretically pass `--apply`.

### R-4.3: Near-duplicate detection only samples first 500 points [medium]

**File:** `agents/knowledge_maint.py:195-196`

The `find_near_duplicates` function scrolls only the first `sample_limit=500` points. In a collection with thousands of points, duplicates among later points are never detected. The scroll returns points in Qdrant's internal order, which biases sampling toward older content. A random offset or stratified sampling would be more representative.

### R-4.4: Drift detector uses "fast" model for both detection and fix generation [low]

**File:** `agents/drift_detector.py:118, 246`

Both `drift_agent` and `fix_agent` use `get_model("fast")` (claude-haiku). For fix generation, where the LLM must produce exact text replacements from a document, a more capable model might produce better results. The manual review step mitigates quality issues.

### R-4.5: `check_docker_containers` parses `Health` field as empty string for healthy [low]

**File:** `agents/health_monitor.py:241`

The condition `health in ("healthy", "", "starting")` treats empty health field as healthy. This is correct for containers without healthchecks defined, but it means a container that has a healthcheck configured but hasn't started checking yet (empty health) is reported as healthy. The `starting` state is also treated as healthy, which is a pragmatic choice to avoid false alarms during boot.

---

## Robustness Findings

### B-4.1: Health history file is unbounded -- no rotation or pruning [high]

**File:** `<local-bin>/health-watchdog:80-97`

The watchdog appends to `profiles/health-history.jsonl` every 15 minutes with no size limit, rotation, or pruning mechanism. At current rates:
- 6 months: ~4-7 MB, ~17,500 lines
- 1 year: ~8-15 MB, ~35,000 lines
- 2 years: ~16-30 MB, ~70,000 lines

Functions that read this file (`collect_health_trend`, `format_history`, `collect_health_history`) load the entire file into memory. Over time this degrades performance of the activity analyzer, briefing agent, and cockpit.

**Recommendation:** Add a rotation mechanism -- either truncate to last N entries periodically, or use date-based file rotation (e.g., `health-history-2026-03.jsonl`).

### B-4.2: Auto-fix watchdog runs `--fix --yes` with no backoff on repeated failures [medium]

**File:** `<local-bin>/health-watchdog:31`

The watchdog runs `--fix --yes` on every invocation when status is not healthy. If a remediation command fails (e.g., Docker daemon won't start), the same fix is retried every 15 minutes indefinitely. There is no:
- Exponential backoff
- Fix attempt counter
- Circuit breaker to stop retrying after N failures
- Tracking of which fixes were already attempted

For most remediations (docker compose up) this is harmless but noisy. For commands like `docker system prune -f`, repeated execution has diminishing returns.

### B-4.3: `run_fixes` executes remediation via `bash -c` with no input sanitization [medium]

**File:** `agents/health_monitor.py:1305`

Remediation commands are passed to `bash -c` as strings. These strings are constructed from constants in the code (not user input), so injection is not currently possible. However, if a container name or service name ever contained shell metacharacters, they would be interpreted by bash. The remediation strings include interpolated values like `{service}` (line 253) and `{COMPOSE_FILE.parent}` (line 219).

Current risk: **very low** because service names come from Docker Compose output which constrains naming. But this is a defense-in-depth gap.

### B-4.4: knowledge_maint exception handling swallows all errors silently [medium]

**File:** `agents/knowledge_maint.py:96, 133, 168, 202, 227, 293`

Multiple operations use bare `except Exception: pass` patterns:
- `get_collection_info` (line 96) -- at least adds a warning
- `find_stale_sources` (line 133) -- silently returns empty list
- `prune_stale_sources` per-source deletion (line 168) -- silently skips
- `find_near_duplicates` scroll (line 202) -- silently returns empty
- `find_near_duplicates` search (line 227) -- silently skips point
- `merge_duplicates` batch delete (line 293) -- silently passes

If Qdrant is intermittently failing (e.g., high load), operations silently produce incomplete results with no indication of partial failure. The report would show "0 stale, 0 duplicates" even if Qdrant refused every query.

### B-4.5: Activity analyzer Langfuse pagination could loop indefinitely [medium]

**File:** `agents/activity_analyzer.py:143-157`

The pagination loop for traces:
```python
while True:
    result = _langfuse_api("/traces", {..., "page": page})
    traces = result.get("data", [])
    if not traces:
        break
    all_traces.extend(traces)
    total = result.get("meta", {}).get("totalItems", 0)
    if len(all_traces) >= total:
        break
    page += 1
```

If the API always returns data but `totalItems` is incorrect (or increases between pages because new traces are being created), the loop runs until the API returns an empty page. With a 10-second timeout per request, a collection with thousands of traces could take significant time. There is no maximum page limit.

The same pattern exists for observations (lines 170-185).

### B-4.6: Drift detector doc truncation at 8000 chars loses context [low]

**File:** `agents/drift_detector.py:148-149`

Documents longer than 8000 characters are truncated. The main CLAUDE.md files can easily exceed this. Truncated content may contain tables or sections relevant to drift detection that the LLM never sees. The truncation is a blunt cut with no attempt to preserve section boundaries.

### B-4.7: Introspect `collect_systemd` makes N+2 subprocess calls per unit [low]

**File:** `agents/introspect.py:144-192`

For each systemd unit found by `list-units`, two additional subprocess calls are made: `is-enabled` and `show --property=Description`. With 10+ services and 10+ timers, this creates 40+ subprocess invocations. These are sequential within the function, though the function itself runs in parallel with other collectors. Not a correctness issue but suboptimal.

### B-4.8: `http_get` error handling returns status code 0 for all errors [low]

**File:** `agents/health_monitor.py:148-152`

The `http_get` utility returns `(0, str(e))` for both `URLError` (connection refused, DNS failure, timeout) and generic `Exception`. Callers check `code == 200` or `200 <= code < 400` but some error messages like "Connection refused" vs "timeout" would be useful for diagnostics. The error string is available in the body but not structured.

---

## Test Coverage Assessment

### Coverage by Check Group

| Group | Checks | Tests | Coverage |
|-------|--------|-------|----------|
| docker | ~14 | 5 tests (daemon, compose, containers, core down) | Good |
| gpu | 3 | 4 tests (available, vram healthy/critical, temp) | Good |
| systemd | 5 | 1 test (rag-ingest + midi optional) | Partial -- only 2 of 5 services verified |
| qdrant | 4 | 3 tests (health, all present, missing) | Good |
| profiles | 4 | 3 tests (files present, staleness recent, staleness old) | Good |
| endpoints | 4 | 3 tests (all up, core down, optional down) | Good |
| credentials | 6 | 2 tests (pass store, entries mixed) | Good |
| disk | 1 | 2 tests (healthy, degraded) | Good |
| models | 4 | 2 tests (all present, missing) | Good |
| auth | 2 | 2 tests (litellm no key, langfuse no keys) | Partial -- no success path tested |
| connectivity | 5 | **0 tests** | **Missing** |

### Coverage Gaps

1. **No connectivity group tests** (C-4.3): The 5 connectivity check functions (tailscale, ntfy, n8n, obsidian, gdrive) have zero test coverage. This is the most significant gap.

2. **No auth success path tests**: `check_litellm_auth` and `check_langfuse_auth` are only tested for the "no key" case, not for successful authentication or auth failure with invalid credentials.

3. **No `run_fixes` tests**: The auto-fix function has no test coverage. Given it executes shell commands, this is a notable gap.

4. **No `format_history` tests**: The history formatting function is untested.

5. **Introspect tests are thorough**: Every collector function has success and failure tests. Schema roundtrip tests verify serialization. This is the best-tested file in the domain.

6. **Drift detector tests are thorough**: Schema tests, formatter tests, generate_fixes logic (grouping, filtering, missing docs), detect_drift flow, and load_docs. Good coverage despite the LLM dependency requiring mocks.

7. **Knowledge maint tests cover dry-run safety well**: Multiple tests verify dry-run doesn't delete, apply does delete, empty inputs handled, and merge keeps newest. The notification tests are also solid.

8. **Activity analyzer tests cover collectors**: Langfuse with/without credentials, with traces, with errors, empty response, unique names. Health trend filtering by time is tested. Formatters tested for various data combinations.

---

## Summary

- **Completeness: 6 findings** (0 critical, 0 high, 1 medium, 5 low)
  - Missing `profile-facts` from knowledge_maint COLLECTIONS (medium)
  - No Docker volume/network introspection, no connectivity tests, unused `since` param in some collectors, static doc file list (low)

- **Correctness: 5 findings** (0 critical, 0 high, 2 medium, 3 low)
  - Full-file memory load for time-filtered queries (medium)
  - Stale source detection vulnerable to filesystem unavailability (medium)
  - Sample bias in dedup, fast model for fixes, empty health field semantics (low)

- **Robustness: 8 findings** (0 critical, 1 high, 4 medium, 3 low)
  - Unbounded health history file growth (high)
  - No fix backoff, bash -c execution, silent exception swallowing, pagination loop bounds (medium)
  - Doc truncation, subprocess overhead, error code granularity (low)

**Total: 19 findings** (0 critical, 1 high, 7 medium, 11 low)

### Key Concerns

1. **Health history unbounded growth (B-4.1)** is the single highest-severity finding. After months of 15-minute writes, the file grows without bound and all readers load it entirely into memory. This needs rotation.

2. **Missing connectivity test coverage (C-4.3)** means 5 of 23 check functions have zero tests. Given the watchdog runs every 15 minutes with auto-fix, these code paths should be verified.

3. **Silent exception swallowing in knowledge_maint (B-4.4)** means partial failures produce results indistinguishable from "everything is clean." A maintenance run that encountered Qdrant errors would report nothing to prune, nothing to merge -- and the operator would have no signal that anything went wrong.

4. **Auto-fix without backoff (B-4.2)** means the watchdog retries the same failed remediations every 15 minutes. While not destructive, it adds noise to systemd journal and notification channels.

### Strengths

1. **Dry-run defaults are consistent and well-enforced.** knowledge_maint defaults to dry-run with explicit `--apply`. The health monitor requires `--fix` flag and then confirmation. The drift detector `--fix` generates display-only output.

2. **The health monitor architecture is well-designed.** The decorator-based registry, parallel async execution, typed Pydantic schemas, and structured remediation commands are clean and extensible.

3. **The introspect/drift-detector pipeline is sound.** Live manifest generation feeding into LLM-powered drift detection with manual-review fix generation is a thoughtful design.

4. **Test coverage for core paths is solid.** Despite the connectivity gap, the main check groups, schemas, formatters, and runner logic are well-tested with proper mocking.
