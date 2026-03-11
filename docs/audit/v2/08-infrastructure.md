# Domain 8: Infrastructure — Audit v2 Findings

**Auditor:** Claude Opus 4.6
**Date:** 2026-03-03
**Scope:** Docker Compose (372 LOC), 22 systemd units (325 LOC), 7 watchdog scripts (357 LOC), backup script (130 LOC), n8n workflows (544 LOC), configs (150 LOC), generate-env.sh (52 LOC), .envrc files (42 LOC)
**v1 reference:** `docs/audit/08-infrastructure.md` (19 findings: 4 critical, 15 recommendation; 9 bonus)

## Inventory

### Docker Compose (`<llm-stack>/docker-compose.yml`)
| Service | Image | Profile | mem_limit | Healthcheck | sha256 |
|---------|-------|---------|-----------|-------------|--------|
| qdrant | qdrant/qdrant:latest | core | 4g | TCP :6333 | yes |
| ollama | ollama/ollama:latest | core | 20g | `ollama list` | yes |
| postgres | pgvector/pgvector:pg16 | core | 4g | `pg_isready` | yes |
| litellm | litellm:main-stable | core | 2g | python urllib /health | yes |
| clickhouse | clickhouse-server:latest | full | 4g | wget /ping | yes |
| redis | redis:7-alpine | full | 512m | redis-cli ping | yes |
| minio | minio:latest | full | 1g | mc ready local | yes |
| langfuse-worker | langfuse-worker:3 | full | 2g | wget /api/health | yes |
| langfuse | langfuse:3 | full | 2g | wget /api/public/health | yes |
| open-webui | open-webui:main | full | 2g | curl /health | yes |
| n8n | n8n:latest | full | 1g | wget /healthz | yes |
| ntfy | ntfy:latest | full | 256m | wget /v1/health | yes |

### Secret Management Pipeline
| Stage | File | Mechanism |
|-------|------|-----------|
| Source | `pass` (GPG store) | Encrypted at rest, GPG agent required |
| Generation | `generate-env.sh` (52 LOC) | ExecStartPre on llm-stack.service |
| Runtime | `.env` (generated, 600 perms) | Docker Compose variable substitution |
| Cleanup | `ExecStopPost=rm -f .env` | Deleted on service stop |
| Agent access | `.envrc` (22 LOC) | `eval "$(<.envrc)"` in watchdog scripts |

### Systemd Units (`<systemd-user>/`)
| Unit | Type | MemoryMax | CPUQuota | OnFailure |
|------|------|-----------|----------|-----------|
| llm-stack.service | oneshot (RemainAfterExit) | — | — | yes |
| rag-ingest.service | simple (always-on) | 4G | 80% | yes |
| health-monitor.service | oneshot | 512M | 30% | yes |
| daily-briefing.service | oneshot | 2G | 60% | yes |
| digest.service | oneshot | 512M | 50% | yes |
| drift-detector.service | oneshot | 512M | 50% | yes |
| scout.service | oneshot | 512M | 50% | yes |
| knowledge-maint.service | oneshot | 1G | 30% | yes |
| manifest-snapshot.service | oneshot | 512M | 30% | yes |
| profile-update.service | oneshot | 4G | 80% | yes |
| llm-backup.service | oneshot | 1G | 50% | yes |
| midi-route.service | oneshot (RemainAfterExit) | — | — | — |
| notify-failure@.service | template | — | — | — |

### Watchdog Scripts (`<local-bin>/`)
| Script | LOC | Uses shared.notify |
|--------|-----|--------------------|
| health-watchdog | 141 | yes |
| briefing-watchdog | 34 | no (raw notify-send) |
| digest-watchdog | 32 | no (inline) |
| drift-watchdog | 35 | no (inline) |
| scout-watchdog | 29 | yes (via agent --notify) |
| knowledge-maint-watchdog | 29 | no (inline) |
| midi-route | 57 | n/a |

### Backup Coverage (`backup.sh`, 130 LOC)
| Target | Method | Status |
|--------|--------|--------|
| Claude Code config | cp -r ~/.claude | ok |
| aichat config | cp config.yaml | ok |
| Langfuse prompts | curl API export | ok |
| Qdrant (4 collections) | POST /snapshots | ok |
| n8n workflows | docker exec export:workflow | ok |
| n8n credentials | docker exec export:credentials | unencrypted |
| PostgreSQL (3 DBs) | docker exec pg_dump | ok |
| Systemd units | cp *.service *.timer | ok |
| Agent profiles | cp -r profiles/ | ok |
| Hotkey scripts | cp -r llm-hotkeys/ | ok |

---

## Fix Verification

### Fix 1: Plaintext secrets in .env — VERIFIED

Complete redesign. `generate-env.sh` (52 LOC) reads all 14 secrets from `pass` store, generates `.env` with 600 permissions. `llm-stack.service` runs it as `ExecStartPre` and removes `.env` on `ExecStopPost`. The `.envrc` (22 LOC) also uses `pass show` for agent service access. The `pass ls` guard at line 8 of generate-env.sh prevents startup with unavailable GPG.

### Fix 2: WEBUI_SECRET_KEY placeholder — VERIFIED

`generate-env.sh:40` — `WEBUI_SECRET_KEY=$(pass show webui/secret-key)`. Docker compose references `${WEBUI_SECRET_KEY}`.

### Fix 3: TELEGRAM_CHAT_ID placeholder — VERIFIED

`generate-env.sh:41` — `TELEGRAM_CHAT_ID=$(pass show telegram/chat-id)`. All n8n workflows can access via `$env.TELEGRAM_CHAT_ID`.

### Fix 4: Vault path mismatch — VERIFIED

`.envrc:18` — `$HOME/Documents/Personal`. `generate-env.sh:44` — `<home>/Documents/Personal`. Consistent and correct.

### Fix 9: Docker resource limits — VERIFIED

All 12 services now have `mem_limit`. Total allocated: ~43.8GB (qdrant 4G + ollama 20G + postgres 4G + litellm 2G + clickhouse 4G + redis 512M + minio 1G + langfuse-worker 2G + langfuse 2G + open-webui 2G + n8n 1G + ntfy 256M).

### Fix 10: Image pinning — VERIFIED

All 12 images pinned to sha256 digests. Including previously unpinned: pgvector:pg16, litellm:main-stable, redis:7-alpine, langfuse:3, langfuse-worker:3, ntfy:latest.

### Fix 45: Langfuse healthchecks — VERIFIED

- langfuse-worker: `wget http://localhost:3030/api/health` (30s interval)
- langfuse web: `wget http://localhost:3000/api/public/health` (30s interval)

### Fix 46: Systemd hardening — NOT FIXED

No services use PrivateTmp, ProtectSystem, NoNewPrivileges, or ReadWritePaths. Low priority given localhost-only deployment.

### Fix 47: Timer service resource limits — VERIFIED

All 9 timer-triggered services now have MemoryMax and CPUQuota. Range: 512M/30% (health-monitor, manifest-snapshot) to 4G/80% (profile-update).

### Fix 48: Sunday timer overlap — IMPROVED

Still the same schedule (02:00 backup, 02:30 manifest). But both services now have resource limits (backup 1G/50%, manifest 512M/30%), reducing the blast radius of concurrent execution. No explicit After= dependency added between them.

### Fix 49: Health watchdog exit code — VERIFIED

`health-monitor.service:8` — `SuccessExitStatus=1`. Degraded status no longer triggers the misleading `OnFailure=notify-failure@%n.service` notification.

### Fix 51: Backup profile-facts collection — VERIFIED

`backup.sh:49` — `for collection in documents samples claude-memory profile-facts;`. All 4 Qdrant collections backed up.

### Fix 59: n8n backup path — VERIFIED

`backup.sh:67-81` — Uses `docker compose exec -T n8n n8n export:workflow --all` and `export:credentials --all`. Checks container is running first. No longer references host `<n8n-data>`.

### Fix 60: n8n setup documentation — VERIFIED

`n8n-workflows/README.md` (105 LOC) — documents all 4 workflows, credential setup, environment variables, import steps.

### Fix 61: Quick capture security — VERIFIED

`quick-capture.json:186` — File path now quoted: `cat "{{ $json.file }}"`. The Pick Info File node still hard-codes the two allowed paths (operator.json, briefing.md), constraining the input. Defense-in-depth quoting prevents future shell injection if new commands are added.

### Fix 66: Digest/briefing timing — VERIFIED

`daily-briefing.service:3` — `After=network.target digest.service`. Briefing service won't start until digest completes, regardless of timer firing order. Clean dependency chain.

### Additional v1 findings — Resolution Status

| v1 ID | Finding | Status |
|-------|---------|--------|
| R-8.12 | Missing captures directory | **Resolved** — exists at `~/documents/rag-sources/captures/` |
| R-8.13 | Dockerfile copies profiles at build time | **Resolved** — comment at line 13, no COPY profiles/ |
| R-8.14 | Digest/briefing timing gap | **Resolved** — After= dependency (see Fix 66) |
| R-8.15 | Hardcoded postgres password | **Resolved** — `${POSTGRES_PASSWORD}` from .env |

**Summary: 16 fixes — 13 fully verified, 1 improved (overlap), 1 not fixed (systemd hardening), 1 subsumed (R-8.14 = Fix 66).**

---

## v1 Findings — Resolution Status

| v1 ID | Finding | v2 Status |
|-------|---------|-----------|
| C-8.1 CRIT | Plaintext API keys in .env | **Resolved** — generate-env.sh from pass + ExecStopPost cleanup |
| C-8.2 CRIT | WEBUI_SECRET_KEY placeholder | **Resolved** — from pass store |
| C-8.3 CRIT | TELEGRAM_CHAT_ID placeholder | **Resolved** — from pass store |
| C-8.4 CRIT | Vault path mismatch | **Resolved** — consistent across .envrc and generate-env.sh |
| R-8.1 | Docker resource limits missing | **Resolved** — all 12 services have mem_limit |
| R-8.2 | Images not pinned to sha256 | **Resolved** — all 12 pinned |
| R-8.3 | Langfuse missing healthchecks | **Resolved** — both web and worker have healthchecks |
| R-8.4 | No systemd hardening | **Not fixed** |
| R-8.5 | Timer services missing limits | **Resolved** — all 9 have MemoryMax+CPUQuota |
| R-8.6 | Sunday overlap risk | **Improved** — resource limits added, but no After= chain |
| R-8.7 | Health watchdog false OnFailure | **Resolved** — SuccessExitStatus=1 |
| R-8.8 | Backup missing profile-facts | **Resolved** — 4 collections backed up |
| R-8.9 | n8n backup wrong path | **Resolved** — docker exec export |
| R-8.10 | n8n credential placeholders | **Improved** — README.md documents setup |
| R-8.11 | Quick capture path traversal | **Resolved** — path quoted |
| R-8.12 | Missing captures directory | **Resolved** — created |
| R-8.13 | Dockerfile copies profiles | **Resolved** — volume mount documented |
| R-8.14 | Digest/briefing timing | **Resolved** — After=digest.service |
| R-8.15 | Hardcoded postgres password | **Resolved** — ${POSTGRES_PASSWORD} |

---

## New Findings

### Correctness

#### R2-8.1: generate-env.sh writes secret values unquoted [low]

`generate-env.sh:20-41` — Values written directly without quoting:
```bash
ANTHROPIC_API_KEY=$(pass show api/anthropic)
```

If any pass entry contains `#`, spaces, or other Docker Compose .env special characters, the value would be truncated or malformed. Docker Compose treats `#` as a comment start in .env files. A key like `sk-ant#abc` would become `sk-ant`.

Currently safe (API keys don't contain these characters), but brittle for any future secret with special characters.

#### R2-8.2: .envrc silently falls back to empty on pass failure [medium]

`llm-stack/.envrc:2-14` — Every secret has `|| echo ''` fallback:
```bash
export ANTHROPIC_API_KEY="$(pass show api/anthropic 2>/dev/null || echo '')"
```

If GPG agent is locked or pass unavailable, all secrets silently become empty strings. Unlike `generate-env.sh` (which has a `pass ls` guard at line 8 and exits on failure), the .envrc provides no warning. Agent watchdog scripts that `eval "$(<.envrc)"` would proceed with empty API keys, causing silent LLM call failures.

Impact is limited: agent services have error handling, and failures trigger OnFailure notifications. But the failure mode is opaque — the notification says "service failed" rather than "pass unavailable."

### Completeness

#### C2-8.1: Inconsistent notification dispatch in watchdog scripts [low]

Of 6 watchdog scripts, only 2 use `shared.notify` (which dispatches to ntfy + desktop):
- health-watchdog: `send_notification()` + `send_webhook()` (lines 19-21, 86-101)
- scout-watchdog: via `--notify` flag (line 8)

The other 4 use raw `notify-send` (desktop-only) or inline Python:
- briefing-watchdog: `notify-send` (lines 28-33)
- digest-watchdog: inline Python for notification
- drift-watchdog: inline Python for notification
- knowledge-maint-watchdog: inline Python for notification

This means briefing completions, drift detections, and knowledge maintenance results don't reach mobile (ntfy). Only health alerts and scout results push to mobile.

#### C2-8.2: No systemd hardening directives [low]

v1 R-8.4 still open. No services use PrivateTmp, ProtectSystem, NoNewPrivileges. All agent services run with full user permissions. Low risk for localhost-only system but represents defense-in-depth gap.

### Robustness

#### B2-8.1: health-watchdog fix-attempts.json not atomic [low]

`health-watchdog:53` — State file written with `json.dump(data, open('$FIX_STATE_FILE', 'w'))`. The `open(..., 'w')` truncates before writing, so an OOM kill or signal during write would corrupt the file. The next run would fall through to the `except: data = {}` fallback (line 48), resetting the counter — which is actually a safe failure mode. But inconsistent with the atomic pattern used for history rotation (lines 126-133).

#### B2-8.2: n8n credential backup stored unencrypted [low]

`backup.sh:74-78` — `n8n export:credentials --all` writes credentials (Telegram bot token, LiteLLM API key) to `$BACKUP_DIR/n8n/credentials.json` in plaintext. The backup directory `<backups>/` has standard user permissions. While the secrets are also in `pass`, having unencrypted copies in backup directories expands the attack surface.

---

## Architecture Assessment

### Most Improved Domain (Tied with D7)

All 4 v1 CRITICAL findings resolved through a single architectural change: the `generate-env.sh` + `ExecStartPre` pattern. This replaced the static plaintext `.env` with a runtime-generated, permission-controlled, cleanup-on-stop approach. Clean design that solves the secret management problem systemically rather than per-secret.

### Infrastructure Maturity

The infrastructure demonstrates production-grade practices:

1. **Every service** has: mem_limit, healthcheck, log rotation, sha256-pinned image, 127.0.0.1 port binding
2. **Every agent service** has: MemoryMax, CPUQuota, OnFailure notification, pass-backed secrets
3. **Boot sequence** correctly ordered: Docker check → env generation → compose up → service dependencies
4. **Backup** covers 10 categories including live n8n export (docker exec) and 4 Qdrant collections
5. **Timer scheduling** uses Persistent=true for catch-up, RandomizedDelaySec for load spreading, After= for dependency ordering

### Remaining Gaps

Two categories of remaining issues:

1. **Defense-in-depth** (systemd hardening, .envrc silent fallback): The system works correctly in normal operation but has weaker-than-ideal failure modes for edge cases (GPG agent locked, compromised dependency).

2. **Notification consistency**: The watchdog scripts evolved independently. Health and scout use the unified `shared.notify` pipeline. The others use ad-hoc notification, limiting mobile reach.

---

## Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Correctness | 0 | 0 | 1 | 1 | **2** |
| Completeness | 0 | 0 | 0 | 2 | **2** |
| Robustness | 0 | 0 | 0 | 2 | **2** |
| **Total** | **0** | **0** | **1** | **5** | **6** |

**v1 comparison:** 19 findings (4 critical, 15 recommendation) → 6 findings (0 critical, 1 medium, 5 low). Net improvement: all 4 CRITICAL findings resolved, 13 of 15 recommendations resolved or improved, 1 not fixed (systemd hardening).

**Fix verification:** 16 fixes checked — 13 fully verified, 1 improved, 1 not fixed (systemd hardening), 1 subsumed.

**Second most improved domain.** The infrastructure went from 4 critical findings (plaintext secrets, placeholder values, path mismatch) to zero. The generate-env.sh approach is the single best architectural fix across the entire audit.
