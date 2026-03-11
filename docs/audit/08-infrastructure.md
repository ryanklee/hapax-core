# Domain 8: Infrastructure — Audit Findings

**Audited**: 2026-03-02
**Scope**: Docker Compose (~351 LOC), 22 systemd units (~306 LOC), 4 n8n workflows (~544 LOC), Dockerfile.api (20 LOC), .envrc (21 LOC), backup script (~102 LOC), 6 watchdog scripts, ntfy/ClickHouse/LiteLLM configs
**Files**: `<llm-stack>/`, `<systemd-user>/`, `<ai-agents>/n8n-workflows/`, `<ai-agents>/Dockerfile.api`

---

## Inventory

### Docker Compose (`<llm-stack>/docker-compose.yml`)
| Service | Image | Profile | Healthcheck | mem_limit | Ports |
|---------|-------|---------|-------------|-----------|-------|
| qdrant | qdrant/qdrant (sha256-pinned) | core | TCP :6333 | 4g | 6333, 6334 |
| ollama | ollama/ollama (sha256-pinned) | core | `ollama list` | none | 11434 |
| postgres | pgvector/pgvector:pg16 (NOT pinned) | core | `pg_isready` | none | 5432 |
| litellm | litellm:main-stable (NOT pinned) | core | python3 urllib /health/liveliness | none | 4000 |
| clickhouse | clickhouse-server (sha256-pinned) | full | wget /ping | none | 8123, 9000 |
| redis | redis:7-alpine (NOT pinned) | full | redis-cli ping | none | none |
| minio | minio (sha256-pinned) | full | mc ready local | none | 9090, 9091 |
| langfuse-worker | langfuse-worker:3 (NOT pinned) | full | none | none | 3030 |
| langfuse | langfuse:3 (NOT pinned) | full | none | none | 3000 |
| open-webui | open-webui (sha256-pinned) | full | curl /health | none | 3080 |
| n8n | n8n (sha256-pinned) | full | wget /healthz | none | 5678 |
| ntfy | ntfy:latest (NOT pinned) | full | wget /v1/health | 256m | 8090 |

### Systemd User Units (`<systemd-user>/`)

**Always-running services:**
| Unit | Type | Restart | MemoryMax | CPUQuota | OnFailure |
|------|------|---------|-----------|----------|-----------|
| llm-stack.service | oneshot (RemainAfterExit) | none | none | none | yes |
| rag-ingest.service | simple | on-failure/15s | 4G | 80% | yes |
| midi-route.service | oneshot (RemainAfterExit) | on-failure/5s | none | none | none |

**Timer-triggered oneshot services:**
| Unit | MemoryMax | CPUQuota | OnFailure |
|------|-----------|----------|-----------|
| health-monitor.service | 512M | 30% | yes |
| profile-update.service | 4G | 80% | yes |
| llm-backup.service | 1G | 50% | yes |
| daily-briefing.service | none | none | yes |
| digest.service | none | none | yes |
| drift-detector.service | none | none | yes |
| manifest-snapshot.service | none | none | yes |
| knowledge-maint.service | none | none | yes |
| scout.service | none | none | yes |

**Timers:**
| Timer | Schedule | RandomizedDelay | Persistent |
|-------|----------|-----------------|------------|
| health-monitor | OnBootSec=2min, OnUnitActiveSec=15min | 1min | no |
| profile-update | OnBootSec=10min, OnUnitActiveSec=6h | 15min | yes |
| llm-backup | Sun 02:00 | 30min | yes |
| manifest-snapshot | Sun 02:30 | 5min | yes |
| drift-detector | Sun 03:00 | 10min | yes |
| knowledge-maint | Sun 04:30 | 10min | yes |
| digest | Daily 06:45 | none | yes |
| daily-briefing | Daily 07:00 | none | yes |
| scout | Wed 10:00 | 30min | yes |

**Template unit:**
| Unit | Purpose |
|------|---------|
| notify-failure@.service | Desktop notification on service failure |

### n8n Workflows (`<ai-agents>/n8n-workflows/`)
| Workflow | Trigger | Nodes | Purpose |
|----------|---------|-------|---------|
| briefing-push.json | Schedule 07:15 | 4 | Read briefing.md, format, send Telegram |
| health-relay.json | Webhook POST | 4 | Format health alert, send Telegram, respond |
| nudge-digest.json | Schedule 2h (09-23) | 4 | Read briefing.md, filter high-priority, send Telegram |
| quick-capture.json | Telegram trigger | 13 | Route commands (/note, /ask, /health, /goals, /briefing), execute |

### Supporting Configs
| File | Purpose |
|------|---------|
| litellm-config.yaml | Model routing, fallbacks, Langfuse callbacks |
| ntfy/server.yml | Push notification server config |
| clickhouse-config/keeper.xml | ClickHouse Keeper for single-node Langfuse |
| init-db.sql | Creates litellm + langfuse databases with pgvector |
| .env | All secrets and configuration variables |
| .envrc (ai-agents) | pass-backed secrets for agent runtime |

---

## Finding Summary

| # | Severity | Category | Finding |
|---|----------|----------|---------|
| C-8.1 | Critical | Secret Management | Plaintext API keys in `.env` file |
| C-8.2 | Critical | Secret Management | WEBUI_SECRET_KEY still has CHANGE_ME placeholder |
| C-8.3 | Critical | Secret Management | TELEGRAM_CHAT_ID still has CHANGE_ME placeholder |
| C-8.4 | Critical | Configuration | Vault path mismatch — `.env` vs `.envrc` vs actual |
| R-8.1 | Recommendation | Docker Resources | 10 of 12 Docker services lack mem_limit |
| R-8.2 | Recommendation | Docker Pinning | 6 of 12 Docker images not pinned to sha256 digest |
| R-8.3 | Recommendation | Healthchecks | Langfuse web and worker have no healthcheck |
| R-8.4 | Recommendation | Systemd Hardening | No services use PrivateTmp or ProtectSystem |
| R-8.5 | Recommendation | Systemd Resources | 6 of 9 timer-triggered services lack MemoryMax/CPUQuota |
| R-8.6 | Recommendation | Timer Scheduling | Sunday window has potential backup/manifest overlap |
| R-8.7 | Recommendation | Health Watchdog | Degraded status exits 1, triggers OnFailure notification |
| R-8.8 | Recommendation | Backup | profile-facts Qdrant collection not included in backup |
| R-8.9 | Recommendation | Backup | n8n backup checks host `<n8n-data>` but data is in Docker volume |
| R-8.10 | Recommendation | n8n Workflows | All 4 workflows have CONFIGURE_ME credential placeholders |
| R-8.11 | Recommendation | n8n Security | quick-capture `/info` command has path traversal risk |
| R-8.12 | Recommendation | n8n Missing Dir | quick-capture `/note` writes to non-existent captures directory |
| R-8.13 | Recommendation | Dockerfile | Dockerfile.api copies profiles/ at build time — stale at runtime |
| R-8.14 | Recommendation | Digest/Briefing Timing | digest (06:45) and briefing (07:00) have no randomized delay |
| R-8.15 | Recommendation | Postgres Password | Hardcoded `localdev` password in compose, not from .env |
| B-8.1 | Bonus | Log Rotation | All 12 Docker services use json-file with 50m/3 rotation |
| B-8.2 | Bonus | Boot Sequence | llm-stack.service uses ExecStartPre Docker check, depends_on with health conditions |
| B-8.3 | Bonus | GPU Passthrough | Ollama deploy.resources.reservations correct for nvidia-container-toolkit |
| B-8.4 | Bonus | Watchdog Scripts | Well-structured bash with set -euo pipefail, eval .envrc, fallback handling |
| B-8.5 | Bonus | Langfuse v3 Stack | ClickHouse + Redis + MinIO inter-service wiring is correct |
| B-8.6 | Bonus | Fallback Chains | LiteLLM bidirectional fallbacks across providers |
| B-8.7 | Bonus | Network Isolation | All ports bound to 127.0.0.1, single `llm-stack` network |
| B-8.8 | Bonus | Failure Notification | notify-failure@.service template covers all agent services |
| B-8.9 | Bonus | Backup Comprehensiveness | Backup covers Claude config, Langfuse prompts, Qdrant snapshots, Postgres dumps, systemd units, profiles |

---

## Finding Details

### C-8.1: Plaintext API Keys in `.env` File (Critical)

**File**: `<llm-stack>/.env`

The `.env` file contains plaintext API keys for Anthropic, Google, LiteLLM, Langfuse, ClickHouse, Redis, MinIO, and n8n:

```
ANTHROPIC_API_KEY=sk-ant-api03-uShabFqm...
GOOGLE_API_KEY=AIzaSyD48x...
LITELLM_MASTER_KEY=sk-litellm-81d949...
```

The `.envrc` in `<ai-agents>/` correctly uses `pass show` to retrieve secrets at runtime. The `.env` file does not — it was "Generated 2026-02-28" and contains static plaintext values. This contradicts the stated convention that all secrets go through `pass`.

**Risk**: Any process or user that can read `<llm-stack>/.env` has all API keys. The file is not encrypted at rest.

**Fix**: Replace `.env` values with a startup script that populates from `pass`, or use Docker Compose `environment` with a wrapper that injects from `pass` at compose-up time. An `.envrc` approach like the ai-agents project uses would be consistent.

---

### C-8.2: WEBUI_SECRET_KEY Placeholder (Critical)

**File**: `<llm-stack>/.env`

```
WEBUI_SECRET_KEY=CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32
```

Open WebUI is running with a placeholder secret key. This means session tokens are signed with a predictable value. While the port is bound to 127.0.0.1, any local process could forge session tokens.

**Fix**: Generate and set: `openssl rand -hex 32`

---

### C-8.3: TELEGRAM_CHAT_ID Placeholder (Critical)

**File**: `<llm-stack>/.env`

```
TELEGRAM_CHAT_ID=CHANGE_ME_GET_FROM_TELEGRAM_BOT
```

All four n8n workflows reference `$env.TELEGRAM_CHAT_ID`. With the placeholder value, all Telegram-based notifications (briefing push, health relay, nudge digest, quick capture replies) silently fail. The multi-channel access system is non-functional for mobile push via Telegram.

**Fix**: Get actual chat ID from Telegram BotFather flow and update.

---

### C-8.4: Vault Path Mismatch (Critical)

Three locations define the Obsidian vault path with conflicting values:

| Source | Path |
|--------|------|
| `<llm-stack>/.env` | `<home>/obsidian-vault` (WRONG) |
| `<ai-agents>/.envrc` | `$HOME/Documents/Personal` (CORRECT) |
| `vault_writer.py` default | `~/Documents/Personal` (CORRECT) |
| Actual vault location | `<personal-vault>/` (exists, 10 folders) |

The `.env` file's `OBSIDIAN_VAULT_PATH` points to a non-existent `<home>/obsidian-vault`. Since the agent services load `.envrc` (which overrides with the correct path), this is not currently causing failures. However, any service that loads from `.env` instead (e.g., if Docker services needed the path) would get the wrong value.

**Fix**: Update `.env` to `OBSIDIAN_VAULT_PATH=<home>/Documents/Personal`.

---

### N/A: Docker Socket Mount (Focus Area 9)

The execution plan asked about the cockpit-api container mounting `/var/run/docker.sock:ro`. This container does not yet exist in the current infrastructure — it is described only in the Phase 1 web layer plan (`docs/plans/2026-03-02-cockpit-web-phase1.md`). Will be auditable once deployed.

---

### R-8.1: Missing Docker Resource Limits (Recommendation)

Only 2 of 12 services have `mem_limit`:
- qdrant: 4g
- ntfy: 256m

Missing limits on all others. The most concerning omissions on a consumer machine with 64GB RAM:

| Service | Risk | Suggested Limit |
|---------|------|-----------------|
| ollama | GPU VRAM-bound but host RAM unbounded | 16g |
| postgres | Can grow with trace/LLM data | 4g |
| litellm | Gateway, should be lightweight | 2g |
| clickhouse | OLAP, can consume significant RAM | 4g |
| open-webui | Python app, moderate | 2g |
| n8n | Workflow engine | 1g |
| langfuse / langfuse-worker | Web app + worker | 2g each |
| redis | Cache only | 512m |
| minio | Object storage | 1g |

**Fix**: Add `mem_limit` to all services. Ollama is the highest risk — it allocates host RAM for model loading beyond VRAM.

---

### R-8.2: Docker Images Not Pinned to SHA256 (Recommendation)

6 images use mutable tags without sha256 pinning:

```yaml
pgvector/pgvector:pg16                    # could break with pg16 update
docker.litellm.ai/berriai/litellm:main-stable  # "stable" but not pinned
redis:7-alpine                            # alpine rebuilds
langfuse/langfuse-worker:3                # major version tag
langfuse/langfuse:3                       # major version tag
binwiederhier/ntfy:latest                 # latest = anything
```

6 images are properly pinned (qdrant, ollama, clickhouse, minio, open-webui, n8n).

**Risk**: `docker compose pull` could introduce breaking changes. The Langfuse v3 images are particularly risky since Langfuse v3 is relatively new and the API surface may shift.

**Fix**: Pin all images to sha256 digests. Update intentionally via a controlled process.

---

### R-8.3: Langfuse Web and Worker Missing Healthchecks (Recommendation)

**File**: `<llm-stack>/docker-compose.yml`

Both `langfuse` (web) and `langfuse-worker` lack healthcheck definitions. Every other service in the compose file has one.

**Impact**: No service can use `depends_on: langfuse: condition: service_healthy`. The LiteLLM `LANGFUSE_HOST` connection is fire-and-forget — if Langfuse is not ready when LiteLLM starts, trace delivery may fail silently until Langfuse becomes available.

**Fix**: Add healthchecks. Langfuse web exposes `/api/public/health`. For the worker, a TCP check on :3030 or a custom script would work.

---

### R-8.4: No Systemd Service Hardening Directives (Recommendation)

Zero services use `PrivateTmp=true`, `ProtectSystem=strict`, `ProtectHome=read-only`, `NoNewPrivileges=true`, or `ReadOnlyPaths`. These are standard hardening directives for systemd services.

Most services are oneshot scripts that read from known paths and write to known paths. Adding sandboxing would reduce blast radius if a dependency (uv, Python package, or agent) were compromised.

**Fix**: At minimum, add to all agent services:
```ini
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=<project-root>/profiles
```

Note: `ProtectHome` cannot be `read-only` for services that write to `<ai-agents>/profiles/`. Use `ReadWritePaths` to allowlist specific directories.

---

### R-8.5: Timer-Triggered Services Missing Resource Limits (Recommendation)

6 of 9 timer-triggered services lack both `MemoryMax` and `CPUQuota`:

| Service | Has MemoryMax | Has CPUQuota |
|---------|:---:|:---:|
| health-monitor | 512M | 30% |
| profile-update | 4G | 80% |
| llm-backup | 1G | 50% |
| daily-briefing | -- | -- |
| digest | -- | -- |
| drift-detector | -- | -- |
| manifest-snapshot | -- | -- |
| knowledge-maint | -- | -- |
| scout | -- | -- |

The briefing, digest, drift-detector, and scout services all invoke LLM calls and could consume significant memory depending on response sizes and context windows.

**Fix**: Add at least `MemoryMax=2G` and `CPUQuota=60%` to all LLM-calling services (daily-briefing, digest, drift-detector, scout). `manifest-snapshot` and `knowledge-maint` can use lower limits (1G/30%).

---

### R-8.6: Sunday Timer Window Overlap Risk (Recommendation)

The Sunday maintenance window schedules:

```
02:00  llm-backup       (RandomizedDelaySec=30min → could start 02:00-02:30)
02:30  manifest-snapshot (RandomizedDelaySec=5min  → could start 02:30-02:35)
03:00  drift-detector   (RandomizedDelaySec=10min → could start 03:00-03:10)
04:30  knowledge-maint  (RandomizedDelaySec=10min → could start 04:30-04:40)
```

**Overlap scenario**: `llm-backup` with 30min randomized delay could start as late as 02:30, exactly when `manifest-snapshot` fires. The backup script runs `pg_dump` on all three databases and creates Qdrant snapshots. If `manifest-snapshot` runs concurrently, the `introspect` agent queries the same services (Docker, Qdrant, etc.) creating resource contention.

**Worse scenario**: The backup script takes longer than 30 minutes (large Postgres databases or slow Qdrant snapshots), overlapping with drift-detector at 03:00.

**Fix**: Either:
1. Remove `RandomizedDelaySec` from `llm-backup` and separate by wider margins, or
2. Chain `manifest-snapshot` with `After=llm-backup.service` dependency, or
3. Shift manifest-snapshot to 02:45 with no randomized delay.

---

### R-8.7: Health Watchdog Triggers False OnFailure Notifications (Recommendation)

**File**: `<local-bin>/health-watchdog`

The script exits with code 1 on degraded status:
```bash
case "$STATUS" in
    healthy)  exit 0 ;;
    degraded) exit 1 ;;
    failed)   exit 2 ;;
esac
```

The `health-monitor.service` has `OnFailure=notify-failure@%n.service`. Any non-zero exit triggers the failure notification template, which sends:

> "Service Failed: health-monitor.service"

This means a _degraded_ stack (e.g., one minor check failing) sends a "Service Failed" desktop notification that implies the health monitor itself crashed, not that the stack is degraded. The health-watchdog already sends its own nuanced notification via `shared.notify` before exiting. The `OnFailure` notification is redundant and misleading.

**Fix**: Either:
1. Change exit codes: `degraded) exit 0 ;;` (already notified internally), or
2. Remove `OnFailure` from health-monitor.service since it handles its own notifications, or
3. Use `SuccessExitStatus=1` in the service to tell systemd that exit code 1 is acceptable.

---

### R-8.8: Backup Missing profile-facts Qdrant Collection (Recommendation)

**File**: `~/Scripts/setup/llm-stack-scripts/llm-stack/scripts/backup.sh`

```bash
for collection in documents samples claude-memory; do
```

The `profile-facts` collection (768d, used by ProfileStore for semantic profile search) is not backed up. This collection was added as part of the context management refactoring and contains indexed profile digests.

**Fix**: Add `profile-facts` to the collection list:
```bash
for collection in documents samples claude-memory profile-facts; do
```

---

### R-8.9: n8n Backup Targets Host Path, Data in Docker Volume (Recommendation)

**File**: `~/Scripts/setup/llm-stack-scripts/llm-stack/scripts/backup.sh`

```bash
if [[ -d "$HOME/.n8n" ]]; then
    cp -r "$HOME/.n8n/"*.json "$BACKUP_DIR/n8n/" 2>/dev/null || true
```

n8n data is stored in the Docker volume `n8n_data` mounted at `/home/node/.n8n` inside the container. The host path `<n8n-data>` does not exist. This backup section silently succeeds (due to `|| true`) while backing up nothing.

n8n workflow definitions are imported via the UI and stored in the container's SQLite database inside the volume, not as individual JSON files. The JSON files in `<ai-agents>/n8n-workflows/` are templates for import, not the live state.

**Fix**: Either:
1. Use `docker compose exec n8n n8n export:workflow --all --output=/tmp/workflows.json` to export live workflows, or
2. Mount a host path for n8n data instead of using a named volume, or
3. Back up the named volume directly: `docker run --rm -v n8n_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/n8n-data.tar.gz /data`.

---

### R-8.10: n8n Workflow Credential Placeholders (Recommendation)

All 4 workflows contain Telegram credential placeholders:
```json
"credentials": {
  "telegramApi": {
    "id": "CONFIGURE_ME",
    "name": "Telegram Bot"
  }
}
```

- `briefing-push.json`: 1 occurrence
- `health-relay.json`: 1 occurrence
- `nudge-digest.json`: 1 occurrence
- `quick-capture.json`: 5 occurrences

These are template files meant to be imported into n8n. After import, credentials must be configured in the n8n UI. The placeholder pattern is correct design for version-controlled workflow templates.

**However**: There is no documentation of the import + configuration process. If the n8n container is rebuilt, workflows and credentials are lost (since they're in the Docker volume, not backed up — see R-8.9).

**Fix**: Add a setup guide in the n8n-workflows directory, or add a post-import verification step to the health monitor.

---

### R-8.11: Quick Capture `/info` Command Path Traversal Risk (Recommendation)

**File**: `<ai-agents>/n8n-workflows/quick-capture.json`

The "Pick Info File" node constrains the file to either `operator.json` or `briefing.md`:
```javascript
let file = command === 'goals' ? '/data/ai-agents/profiles/operator.json' : '/data/ai-agents/profiles/briefing.md';
```

This is safe — the file path is not user-controlled. The switch node ensures only `goals` or `briefing` commands reach this path. However, the "Read Info File" node uses shell interpolation:

```
"command": "=cat {{ $json.file }} 2>/dev/null | head -50 || echo 'File not available'"
```

If a future developer adds more commands to the switch without constraining the `file` value, this becomes a shell injection vector. The `{{ $json.file }}` is not quoted.

**Fix**: Quote the file path: `cat "{{ $json.file }}"` and validate the path in the Pick Info File node.

---

### R-8.12: Quick Capture Missing Captures Directory (Recommendation)

**File**: `<ai-agents>/n8n-workflows/quick-capture.json`

The `/note` command writes captured notes to:
```
/data/rag-sources/captures/{{ $json.filename }}
```

Which maps to the host path `~/documents/rag-sources/captures/`. This directory does not exist:
```
$ ls ~/documents/rag-sources/captures/
captures directory does not exist
```

The n8n `writeFile` node will fail when attempting to write to a non-existent directory.

**Fix**: Create the directory: `mkdir -p ~/documents/rag-sources/captures/`

---

### R-8.13: Dockerfile.api Copies Profiles at Build Time (Recommendation)

**File**: `<ai-agents>/Dockerfile.api`

```dockerfile
COPY profiles/ profiles/
```

The `profiles/` directory contains runtime state (operator.json, briefing.md, health-history.jsonl) that changes frequently. Copying it at build time means the container runs with stale profile data.

**Fix**: Mount `profiles/` as a volume at runtime instead of copying at build:
```yaml
volumes:
  - ./profiles:/app/profiles:ro
```

Remove the `COPY profiles/ profiles/` line from the Dockerfile.

---

### R-8.14: Digest and Briefing Timers Lack Randomized Delay (Recommendation)

```
digest.timer:    OnCalendar=*-*-* 06:45:00  (no RandomizedDelaySec)
briefing.timer:  OnCalendar=*-*-* 07:00:00  (no RandomizedDelaySec)
```

Both fire at exact times. The briefing depends on the digest having completed (briefing reads digest.md). With only 15 minutes between them and no guarantee of digest completion time, the briefing could read a stale digest if the LLM call takes longer than 15 minutes.

Additionally, the n8n `briefing-push` workflow fires at 07:15, giving only 15 minutes for the briefing to complete. If the LLM provider is slow or falls back through the chain, this could be tight.

**Fix**: Either:
1. Chain them: add `After=digest.service` to `daily-briefing.service`, or
2. Add a check in the briefing agent that verifies digest freshness before proceeding.

---

### R-8.15: Hardcoded Postgres Password (Recommendation)

**File**: `<llm-stack>/docker-compose.yml`

```yaml
# postgres service
POSTGRES_PASSWORD: localdev

# litellm service
LITELLM_DATABASE_URL: "postgresql://postgres:localdev@postgres:5432/litellm"

# langfuse services
DATABASE_URL: "postgresql://postgres:localdev@postgres:5432/langfuse"
```

The Postgres password `localdev` is hardcoded in the compose file rather than referenced from `.env`. While the database is only accessible on 127.0.0.1:5432, this is inconsistent with the secret management approach used for other credentials.

**Fix**: Move to `.env`: `POSTGRES_PASSWORD=localdev` and reference as `${POSTGRES_PASSWORD}` in compose. Update connection strings accordingly.

---

### B-8.1: Consistent Log Rotation (Bonus)

All 12 Docker services reference the YAML anchor `*default-logging`:
```yaml
x-logging: &default-logging
  driver: json-file
  options:
    max-size: "50m"
    max-file: "3"
```

This is thorough — no service was missed. Maximum disk usage from Docker logs: 12 services x 50MB x 3 files = 1.8GB.

---

### B-8.2: Boot Sequence Correctness (Bonus)

The startup chain is well-ordered:

1. `llm-stack.service` (WantedBy=default.target) runs `docker compose --profile full up -d`
2. `ExecStartPre=/usr/bin/docker info` verifies Docker daemon is running before compose
3. `TimeoutStartSec=120` allows slow image pulls
4. Within compose, `depends_on` with `condition: service_healthy`:
   - litellm waits for postgres + ollama
   - langfuse/langfuse-worker wait for postgres + clickhouse + redis + minio
   - open-webui waits for ollama + litellm
5. `loginctl linger` ensures user services run without active login session

The only gap: the `depends_on` chain means if one core service (e.g., postgres) fails its healthcheck, all dependent services block indefinitely. The compose `restart: unless-stopped` will keep retrying postgres, but there is no timeout or circuit breaker at the compose level.

---

### B-8.3: Ollama GPU Passthrough (Bonus)

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

This is the correct specification for nvidia-container-toolkit GPU passthrough. The `count: 1` matches the single RTX 3090. The `capabilities: [gpu]` is the required capability for CUDA workloads. No `mem_limit` on the Ollama container is intentional here — Ollama manages VRAM allocation internally and auto-unloads idle models.

---

### B-8.4: Watchdog Script Quality (Bonus)

All 6 watchdog scripts follow consistent patterns:
- `set -euo pipefail` for strict error handling
- `eval "$(<.envrc)"` to load pass-backed secrets
- Absolute paths for `uv` binary
- Fallback error handling (e.g., `2>/dev/null || true`)
- JSON output parsing for notification formatting
- Structured history appending (JSONL format)

The health-watchdog is particularly well-designed: it runs checks, attempts auto-fix, re-checks, sends contextual notifications, and appends to history — all in a single script.

---

### B-8.5: Langfuse v3 Inter-Service Configuration (Bonus)

The Langfuse v3 stack is correctly wired:
- ClickHouse: migration URL uses port 9000 (native), query URL uses 8123 (HTTP)
- Redis: auth password passed consistently, host uses Docker service name
- MinIO: force-path-style enabled (required for non-AWS S3), separate event/media prefixes
- YAML anchor (`&langfuse-env`) correctly shares environment between web and worker
- Web adds `NEXTAUTH_SECRET` on top of shared config
- Keeper config enables single-node ClickHouse coordination

---

### B-8.6: LiteLLM Fallback Chains (Bonus)

```yaml
fallbacks:
  - claude-opus: [claude-sonnet, gemini-pro]
  - claude-sonnet: [gemini-pro]
  - claude-haiku: [gemini-flash]
  - gemini-pro: [claude-sonnet]
  - gemini-flash: [claude-haiku]
```

Bidirectional cross-provider fallback ensures that if either Anthropic or Google has an outage, the system degrades gracefully. Combined with `num_retries: 2`, `allowed_fails: 3`, and `cooldown_time: 30`, this provides robust model availability.

---

### B-8.7: Network Isolation (Bonus)

All 12 service port bindings use `127.0.0.1:`:
```yaml
ports:
  - "127.0.0.1:6333:6333"
```

No service is exposed to the network. The single Docker network `llm-stack` provides inter-container communication. Redis does not even expose a host port — it is only accessible within the Docker network.

---

### B-8.8: Failure Notification Template (Bonus)

```ini
[Service]
Type=oneshot
ExecStart=/usr/bin/notify-send --urgency=critical --app-name="LLM Stack" --icon=dialog-error \
    "Service Failed: %i" "Check: journalctl --user -u %i --no-pager -n 20"
```

Clean template using `%i` specifier. Every agent service (except midi-route) has `OnFailure=notify-failure@%n.service`. The notification includes the exact journalctl command to debug, which is a good operator UX.

---

### B-8.9: Backup Comprehensiveness (Bonus)

The backup script covers 7 categories:
1. Claude Code config (`~/.claude`)
2. aichat config
3. Langfuse prompts (via API export)
4. Qdrant snapshots (3 of 4 collections — see R-8.8)
5. PostgreSQL dumps (all 3 databases)
6. Systemd user units
7. Agent profiles

Retention policy: keeps last 8 backups, prunes oldest. Weekly schedule means ~2 months of history.

---

## Summary

| Category | Count |
|----------|-------|
| Critical | 4 |
| Recommendation | 15 |
| Bonus | 9 |
| **Total** | **28** |

### Key Concerns

1. **Secret management inconsistency**: The `.env` file contains plaintext API keys while the `.envrc` correctly uses `pass`. This is the single biggest security gap — the stated convention is contradicted by the actual implementation for Docker services.

2. **Placeholder values in production**: WEBUI_SECRET_KEY and TELEGRAM_CHAT_ID are still placeholders, meaning Open WebUI session security is weak and the entire Telegram-based mobile access channel is non-functional.

3. **Vault path mismatch**: The `.env` file points to a non-existent vault path. Currently masked by `.envrc` override, but a latent bug.

4. **Backup gaps**: The backup script misses the profile-facts Qdrant collection and fails silently on n8n workflows (checks wrong path). These are data loss risks for disaster recovery.

5. **Resource limits**: Most Docker services and systemd services run without memory limits. On a consumer machine, a misbehaving service could exhaust system RAM.

### Architectural Strengths

The infrastructure layer is well-designed at the architectural level. The Docker Compose file demonstrates disciplined practices (log rotation, healthchecks, port binding, YAML anchors). The systemd timer system provides a clean separation between scheduling and execution. The watchdog scripts are production-quality bash. The Langfuse v3 stack and LiteLLM gateway are correctly configured with proper fallback chains. The boot sequence handles dependencies correctly.

The primary issues are operational housekeeping (placeholders, pinning, limits) rather than architectural defects. The infrastructure would benefit from a hardening pass to close the gap between the careful design and the current runtime configuration.
