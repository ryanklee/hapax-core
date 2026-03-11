# hapax-system Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a private Claude Code plugin that consolidates all project-specific configuration (hooks, skills, agents, rules) into a single portable, version-controlled package.

**Architecture:** Plugin source lives at `<hapax-system>/` as a git repo. Registered directly in `<claude-config>/plugins/installed_plugins.json` with `installPath` pointing to the source directory. Rules (not a plugin primitive) are symlinked from plugin source to `<claude-config>/rules/` via an install script.

**Tech Stack:** Bash (hooks), Markdown (skills/agents/rules), JSON (plugin manifest, hooks config), jq (hook scripts)

---

### Task 1: Create plugin repo and manifest

**Files:**
- Create: `<hapax-system>/.claude-plugin/plugin.json`
- Create: `<hapax-system>/.gitignore`

**Step 1: Initialize repo**

```bash
mkdir -p <hapax-system>/.claude-plugin
cd <hapax-system> && git init
```

**Step 2: Write plugin manifest**

Create `<hapax-system>/.claude-plugin/plugin.json`:

```json
{
  "name": "hapax-system",
  "description": "System-aware Claude Code configuration for the hapax three-tier agent stack. Provides axiom governance, operator-aligned workflows, and infrastructure awareness.",
  "version": "1.0.0",
  "author": {
    "name": "the operator"
  }
}
```

**Step 3: Write .gitignore**

Create `<hapax-system>/.gitignore`:

```
*.swp
*.swo
.DS_Store
```

**Step 4: Create directory scaffold**

```bash
cd <hapax-system>
mkdir -p skills/{status,briefing,studio,vram,ingest,axiom-check,axiom-review,deploy-check,weekly-review}
mkdir -p agents
mkdir -p hooks/scripts
mkdir -p rules
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: plugin scaffold with manifest"
```

---

### Task 2: Migrate hook scripts

Copy the 3 existing axiom hook scripts from ai-agents into the plugin, adapting paths to use `${CLAUDE_PLUGIN_ROOT}`.

**Files:**
- Create: `<hapax-system>/hooks/scripts/axiom-scan.sh`
- Create: `<hapax-system>/hooks/scripts/axiom-audit.sh`
- Create: `<hapax-system>/hooks/scripts/axiom-commit-scan.sh`

**Step 1: Copy axiom-scan.sh**

Copy verbatim from `<ai-agents>/.claude/hooks/axiom-scan.sh` to `<hapax-system>/hooks/scripts/axiom-scan.sh`. No changes needed — script reads from stdin and uses no path references.

**Step 2: Copy axiom-audit.sh**

Copy verbatim from `<ai-agents>/.claude/hooks/axiom-audit.sh` to `<hapax-system>/hooks/scripts/axiom-audit.sh`. No changes needed.

**Step 3: Copy axiom-commit-scan.sh**

Copy verbatim from `<ai-agents>/.claude/hooks/axiom-commit-scan.sh` to `<hapax-system>/hooks/scripts/axiom-commit-scan.sh`. No changes needed.

**Step 4: Make executable**

```bash
chmod +x <hapax-system>/hooks/scripts/*.sh
```

**Step 5: Verify scripts parse cleanly**

```bash
bash -n <hapax-system>/hooks/scripts/axiom-scan.sh && echo OK
bash -n <hapax-system>/hooks/scripts/axiom-audit.sh && echo OK
bash -n <hapax-system>/hooks/scripts/axiom-commit-scan.sh && echo OK
```

Expected: three `OK` lines.

**Step 6: Commit**

```bash
cd <hapax-system>
git add hooks/scripts/
git commit -m "feat: migrate axiom hook scripts from ai-agents"
```

---

### Task 3: Create session-context.sh hook

New SessionStart hook that outputs system state summary. Replaces both the ai-agents SessionStart hook (axiom status) and the global compact SessionStart hook (branch/docker/GPU).

**Files:**
- Create: `<hapax-system>/hooks/scripts/session-context.sh`

**Step 1: Write session-context.sh**

Create `<hapax-system>/hooks/scripts/session-context.sh`:

```bash
#!/usr/bin/env bash
# session-context.sh — SessionStart hook for hapax-system plugin
# Injects system state summary into Claude Code context.
# Replaces: ai-agents SessionStart hook + global compact hook.

echo '## System Context'

# Axiom status
AXIOM_COUNT="2"
AXIOM_NAMES="single_user, executive_function"
if [ -d "$HOME/projects/ai-agents" ]; then
  RESULT="$(cd "$HOME/projects/ai-agents" && python3 -c "
import sys; sys.path.insert(0, '.')
from shared.axiom_registry import load_axioms
axs=load_axioms()
print('%d|%s' % (len(axs), ', '.join(a.id for a in axs)))
" 2>/dev/null || true)"
  if [ -n "$RESULT" ]; then
    AXIOM_COUNT="$(echo "$RESULT" | cut -d'|' -f1)"
    AXIOM_NAMES="$(echo "$RESULT" | cut -d'|' -f2)"
  fi
fi
echo "Axioms: $AXIOM_COUNT loaded ($AXIOM_NAMES)"

# Git context
BRANCH="$(git branch --show-current 2>/dev/null || echo 'N/A')"
LAST_COMMIT="$(git log --oneline -1 2>/dev/null || echo 'N/A')"
echo "Branch: $BRANCH | Last commit: $LAST_COMMIT"

# Health summary (from latest health-history.jsonl entry)
HEALTH_FILE="$HOME/projects/ai-agents/profiles/health-history.jsonl"
if [ -f "$HEALTH_FILE" ]; then
  LATEST="$(tail -1 "$HEALTH_FILE" 2>/dev/null || true)"
  if [ -n "$LATEST" ]; then
    STATUS="$(echo "$LATEST" | jq -r '.status // "unknown"' 2>/dev/null || echo unknown)"
    HEALTHY="$(echo "$LATEST" | jq -r '.healthy // 0' 2>/dev/null || echo 0)"
    TOTAL="$(echo "$LATEST" | jq -r '(.healthy + .degraded + .failed) // 0' 2>/dev/null || echo 0)"
    TS="$(echo "$LATEST" | jq -r '.timestamp // ""' 2>/dev/null || true)"
    echo "Health: $HEALTHY/$TOTAL $STATUS | Last run: ${TS:0:16}"
  fi
fi

# Docker containers
RUNNING="$(docker ps --format '{{.Names}}' 2>/dev/null | wc -l || echo 0)"
echo "Docker: $RUNNING containers running"

# GPU
GPU="$(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null || true)"
if [ -n "$GPU" ]; then
  USED="$(echo "$GPU" | awk -F', ' '{print $1}')"
  TOTAL="$(echo "$GPU" | awk -F', ' '{print $2}')"
  echo "GPU: ${USED}/${TOTAL} MiB used"
fi
```

**Step 2: Make executable**

```bash
chmod +x <hapax-system>/hooks/scripts/session-context.sh
```

**Step 3: Test locally**

```bash
bash <hapax-system>/hooks/scripts/session-context.sh
```

Expected: Multi-line output starting with `## System Context`.

**Step 4: Commit**

```bash
cd <hapax-system>
git add hooks/scripts/session-context.sh
git commit -m "feat: session-context.sh — unified SessionStart hook"
```

---

### Task 4: Write hooks.json

Wire all hook scripts into the plugin hook manifest.

**Files:**
- Create: `<hapax-system>/hooks/hooks.json`

**Step 1: Write hooks.json**

Create `<hapax-system>/hooks/hooks.json`:

```json
{
  "description": "hapax-system plugin hooks — axiom governance + system awareness",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-context.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/axiom-scan.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/axiom-commit-scan.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/axiom-audit.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "AUDIT_FILE=\"$HOME/.cache/axiom-audit/$(date +%Y-%m-%d).jsonl\"; if [ -f \"$AUDIT_FILE\" ]; then TOTAL=$(wc -l < \"$AUDIT_FILE\"); BLOCKED=$(grep -c '\"blocked\":true' \"$AUDIT_FILE\" 2>/dev/null || echo 0); echo \"Axiom audit: $TOTAL edits tracked, $BLOCKED blocked.\"; fi"
          }
        ]
      }
    ]
  }
}
```

**Step 2: Validate JSON**

```bash
jq . <hapax-system>/hooks/hooks.json > /dev/null && echo "Valid JSON"
```

Expected: `Valid JSON`

**Step 3: Commit**

```bash
cd <hapax-system>
git add hooks/hooks.json
git commit -m "feat: hooks.json — axiom governance + session context pipeline"
```

---

### Task 5: Create rules files

Rules are NOT a plugin primitive — they must be symlinked to `<claude-config>/rules/` by the install script (Task 10). For now, create them in the plugin source.

**Files:**
- Create: `<hapax-system>/rules/axioms.md`
- Create: `<hapax-system>/rules/system-context.md`

**Step 1: Copy axioms.md**

Copy verbatim from `<ai-agents>/.claude/rules/axioms.md` to `<hapax-system>/rules/axioms.md`. No changes needed.

**Step 2: Write system-context.md**

Create `<hapax-system>/rules/system-context.md`. This is the "aggressive awareness" file — live system topology that Claude Code always has in context.

```markdown
# System Topology

## Service Topology (Docker, all ports 127.0.0.1)

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Ollama | ollama | 11434 | Local LLM inference (GPU) |
| Qdrant | qdrant | 6333 | Vector database (768d, nomic-embed) |
| PostgreSQL | postgres | 5432 | pgvector, LiteLLM + Langfuse backend |
| LiteLLM | litellm | 4000 | API gateway — all model routing + Langfuse tracing |
| Langfuse Web | langfuse | 3000 | LLM observability (v3) |
| Langfuse Worker | langfuse-worker | 3030 | Async trace processing |
| ClickHouse | clickhouse | 8123 | OLAP backend for Langfuse v3 |
| Redis | redis | — | Cache/queue for Langfuse v3 |
| MinIO | minio | 9090 | S3-compatible storage for Langfuse v3 |
| Open WebUI | open-webui | 3080 | Web chat UI |
| n8n | n8n | 5678 | Workflow automation |
| ntfy | ntfy | 8090 | Push notifications |

## Tier 2 Agents (<ai-agents>/)

Invoke: `cd <ai-agents> && uv run python -m agents.<name> [flags]`

| Agent | LLM? | Key Flags |
|-------|------|-----------|
| health_monitor | No | `--fix`, `--history` |
| introspect | No | `--save` |
| activity_analyzer | No* | `--synthesize`, `--hours N` |
| drift_detector | Yes | `--fix`, `--json` |
| briefing | Yes | `--hours N`, `--save` |
| scout | Yes | |
| profiler | Yes | `--auto`, `--digest`, `--source TYPE` |
| research | Yes | `<query>` |
| code_review | Yes | `<file>` |
| management_prep | Yes | `--person NAME`, `--team-snapshot`, `--overview` |
| digest | Yes | |
| knowledge_maint | No* | `--apply`, `--summarize` |

## Tier 3 Timers (systemd user)

| Timer | Schedule | Purpose |
|-------|----------|---------|
| health-monitor | Every 15 min | Auto-fix + notify |
| profile-update | Every 12h | Incremental profile |
| digest | Daily 06:45 | Content digest |
| daily-briefing | Daily 07:00 | Morning briefing |
| scout | Weekly Wed 10:00 | Horizon scan |
| drift-detector | Weekly Sun 03:00 | Doc drift check |
| manifest-snapshot | Weekly Sun 02:30 | System state snapshot |
| knowledge-maint | Weekly Sun 04:30 | Qdrant hygiene |
| llm-backup | Weekly Sun 02:00 | Full stack backup |

## Model Aliases (via LiteLLM at :4000)

| Alias | Model | Use |
|-------|-------|-----|
| fast | claude-haiku | Cheap quick tasks |
| balanced | claude-sonnet | Default for agents |
| reasoning | deepseek-r1:14b | Complex reasoning (local) |
| coding | qwen-coder-32b | Code generation (local) |
| local-fast | qwen-7b | Lightweight local tasks |

Embedding: nomic-embed-text-v2-moe (768d). Requires `search_query:` / `search_document:` prefixes.
VRAM: RTX 3090 = 24GB. One large Ollama model at a time.

## Qdrant Collections

| Collection | Dims | Purpose |
|-----------|------|---------|
| documents | 768 | RAG document chunks |
| samples | 768 | Audio sample metadata |
| claude-memory | 768 | Claude Code persistent memory |
| profile-facts | 768 | Operator profile facts |

## Key Paths

| Path | Purpose |
|------|---------|
| <llm-stack>/ | Docker compose + service configs |
| <ai-agents>/ | Tier 2 agent implementations |
| <hapaxromana>/ | Architecture specs + axioms |
| <rag-pipeline>/ | RAG ingestion service |
| <obsidian-hapax>/ | Obsidian plugin |
| <personal-vault>/ | Obsidian vault |
| <cache>/axiom-audit/ | Axiom audit trail (JSONL) |
| <cache>/cockpit/ | Cockpit state (probes, decisions, facts) |
```

**Step 3: Commit**

```bash
cd <hapax-system>
git add rules/
git commit -m "feat: rules — axiom governance + system topology context"
```

---

### Task 6: Migrate 7 commands to skills

Convert each `<claude-config>/commands/*.md` to a plugin skill at `skills/<name>/SKILL.md` with proper YAML frontmatter.

**Files:**
- Create: `<hapax-system>/skills/status/SKILL.md`
- Create: `<hapax-system>/skills/briefing/SKILL.md`
- Create: `<hapax-system>/skills/studio/SKILL.md`
- Create: `<hapax-system>/skills/vram/SKILL.md`
- Create: `<hapax-system>/skills/ingest/SKILL.md`
- Create: `<hapax-system>/skills/axiom-check/SKILL.md`
- Create: `<hapax-system>/skills/axiom-review/SKILL.md`

**Step 1: Write skills/status/SKILL.md**

```markdown
---
name: status
description: Run the health monitor and report results. Use when the user asks about system health, infrastructure status, or runs /status.
---

Run the health monitor and report results:

```bash
cd <ai-agents> && uv run python -m agents.health_monitor
```

If checks show FAILED, suggest: `uv run python -m agents.health_monitor --fix`
```

**Step 2: Write skills/briefing/SKILL.md**

```markdown
---
name: briefing
description: Generate a system briefing covering the last 24 hours. Use when the user asks for a briefing, daily summary, or runs /briefing.
---

Generate a system briefing covering the last 24 hours:

```bash
cd <ai-agents> && eval "$(<.envrc)" && uv run python -m agents.briefing --hours 24 --save
```

If action items show high priority, suggest running the relevant fix commands.
The latest briefing is always saved to `<ai-agents>/profiles/briefing.md`.
```

**Step 3: Write skills/studio/SKILL.md**

```markdown
---
name: studio
description: Check music production infrastructure. Use when the user asks about MIDI, audio devices, studio setup, or runs /studio.
---

Check music production infrastructure:

1. ALSA MIDI ports: run `aconnect -l` and show connected ports
2. Audio devices: run `aplay -l` and summarize
3. Virtual MIDI: verify snd-virmidi is loaded (`lsmod | grep virmidi`)
4. MIDI MCP server: check if running
5. Any audio-related Docker containers

Report connections between MCP MIDI Out and hardware devices.
```

**Step 4: Write skills/vram/SKILL.md**

```markdown
---
name: vram
description: Show detailed VRAM analysis. Use when the user asks about GPU memory, VRAM, model loading capacity, or runs /vram.
---

Show detailed VRAM analysis:

1. Run `nvidia-smi` and parse output
2. List all Ollama loaded models: `curl -s http://localhost:11434/api/ps`
3. Check if TabbyAPI is running on port 5000
4. Estimate available VRAM for additional tasks
5. Recommend which models can be loaded concurrently
```

**Step 5: Write skills/ingest/SKILL.md**

```markdown
---
name: ingest
description: Check RAG ingestion pipeline status. Use when the user asks about RAG, document ingestion, Qdrant indexing, or runs /ingest.
---

Check RAG ingestion pipeline:

1. Systemd service status: `systemctl --user status rag-ingest`
2. Recent journal logs: `journalctl --user -u rag-ingest --since '1 hour ago' --no-pager`
3. Qdrant collection stats: `curl http://localhost:6333/collections/documents`
4. Count of documents in watched directories
5. Any errors or warnings in the pipeline
```

**Step 6: Write skills/axiom-check/SKILL.md**

```markdown
---
name: axiom-check
description: Check axiom compliance of the current project. Use when the user asks about axiom status, compliance, governance, or runs /axiom-check.
---

Check axiom compliance of the current project.

Run:

```bash
cd <ai-agents> && eval "$(direnv export bash 2>/dev/null)" && uv run python -c "
import asyncio
from shared.axiom_registry import load_axioms, load_implications
from shared.axiom_precedents import PrecedentStore

async def check():
    axioms = load_axioms()
    for ax in axioms:
        imps = load_implications(ax.id)
        t0 = [i for i in imps if i.tier == 'T0']
        print(f'## {ax.id} ({len(t0)} T0 blocks, {len(imps)} total implications)')
        for imp in t0:
            print(f'  [BLOCK] {imp.id}: {imp.text}')
    try:
        store = PrecedentStore()
        pending = await store.get_pending_review()
        if pending:
            print(f'\n## Pending Review: {len(pending)} agent precedent(s)')
            for p in pending:
                print(f'  - {p.id}: {p.situation[:80]}...')
        else:
            print('\nNo pending precedents.')
    except Exception as e:
        print(f'\nPrecedent store unavailable: {e}')

asyncio.run(check())
"
```

Review the output and suggest any compliance concerns for the current work.
```

**Step 7: Write skills/axiom-review/SKILL.md**

```markdown
---
name: axiom-review
description: Review pending axiom precedents that agents have created. Use when the user asks to review precedents, axiom decisions, or runs /axiom-review.
---

Review pending axiom precedents that agents have created.

Run:

```bash
cd <ai-agents> && eval "$(direnv export bash 2>/dev/null)" && uv run python -c "
import asyncio
from shared.axiom_precedents import PrecedentStore

async def review():
    store = PrecedentStore()
    pending = await store.get_pending_review()
    if not pending:
        print('No pending precedents to review.')
        return
    for p in pending:
        print('---')
        print(f'ID: {p.id}')
        print(f'Axiom: {p.axiom_id}')
        print(f'Tier: {p.tier}')
        print(f'Decision: {p.decision}')
        print(f'Situation: {p.situation}')
        print(f'Reasoning: {p.reasoning}')
        print(f'Distinguishing facts: {p.distinguishing_facts}')
        print()

asyncio.run(review())
"
```

For each precedent, ask the operator whether to CONFIRM (promote to operator authority) or REJECT (with correction).
```

**Step 8: Commit**

```bash
cd <hapax-system>
git add skills/
git commit -m "feat: migrate 7 commands to plugin skills"
```

---

### Task 7: Create 2 new skills

**Files:**
- Create: `<hapax-system>/skills/deploy-check/SKILL.md`
- Create: `<hapax-system>/skills/weekly-review/SKILL.md`

**Step 1: Write skills/deploy-check/SKILL.md**

```markdown
---
name: deploy-check
description: Pre-push readiness verification. Use before pushing code, when the user asks to verify deployment readiness, or runs /deploy-check.
---

# Pre-Push Readiness Check

Run these checks before pushing to remote:

1. **Uncommitted changes**: `git status` — flag any unstaged or untracked files
2. **Tests pass**: `cd <ai-agents> && uv run pytest --tb=short -q`
3. **Health check**: `cd <ai-agents> && uv run python -m agents.health_monitor`
4. **Axiom compliance of branch diff**:
   ```bash
   BASE=$(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null)
   git diff "$BASE"...HEAD | grep '^+[^+]' | grep -Ei 'class User(Manager|Service|Repository|Controller|Model)\b|class Auth(Manager|Service|Handler)\b|class (Role|Permission|ACL|RBAC|OAuth|Session)Manager\b|def (authenticate|authorize|login|logout|register)_user' && echo "AXIOM VIOLATION DETECTED" || echo "Axiom scan: clean"
   ```
5. **Branch is up to date**: `git fetch origin && git log HEAD..origin/main --oneline`

Report a go/no-go summary. Block on test failures or axiom violations. Warn on uncommitted changes.
```

**Step 2: Write skills/weekly-review/SKILL.md**

```markdown
---
name: weekly-review
description: Aggregate the week's system data into a structured review. Use on Sunday evenings or Monday mornings, when the user asks for a weekly summary, or runs /weekly-review.
---

# Weekly System Review

Aggregate data from the past 7 days:

1. **Audit trail**: `cat <cache>/axiom-audit/*.jsonl 2>/dev/null | wc -l` total edits, `grep -c '"blocked":true' <cache>/axiom-audit/*.jsonl 2>/dev/null || echo 0` blocked
2. **Health history**: `cd <ai-agents> && uv run python -m agents.health_monitor --history`
3. **Drift report** (if recent): `cat <ai-agents>/profiles/drift-report.json 2>/dev/null | jq '.drift_items | length'`
4. **Scout report** (if recent): `cat <ai-agents>/profiles/scout-report.json 2>/dev/null | jq '.evaluations | length'`
5. **Briefing** (latest): `head -30 <ai-agents>/profiles/briefing.md`
6. **Timer status**: `systemctl --user list-timers --no-pager`

Synthesize into a 5-line summary: overall health, notable incidents, drift status, axiom compliance, recommended actions for the coming week.
```

**Step 3: Commit**

```bash
cd <hapax-system>
git add skills/deploy-check/ skills/weekly-review/
git commit -m "feat: deploy-check + weekly-review skills"
```

---

### Task 8: Migrate operator-voice agent

**Files:**
- Create: `<hapax-system>/agents/operator-voice.md`

**Step 1: Copy operator-voice.md**

Copy from `<hapaxromana>/.claude/agents/operator-voice.md` to `<hapax-system>/agents/operator-voice.md`.

The file already has proper YAML frontmatter (name, description, model, color, memory). One change needed: the memory path reference at the bottom says `hapaxromana/.claude/agent-memory/operator-voice/`. This path stays the same — the agent memory directory persists independently of the agent definition file's location.

No content changes needed.

**Step 2: Commit**

```bash
cd <hapax-system>
git add agents/operator-voice.md
git commit -m "feat: migrate operator-voice agent from hapaxromana"
```

---

### Task 9: Create infra-check and convention-guard agents

**Files:**
- Create: `<hapax-system>/agents/infra-check.md`
- Create: `<hapax-system>/agents/convention-guard.md`

**Step 1: Write agents/infra-check.md**

```markdown
---
name: infra-check
description: "Verify infrastructure assumptions before implementation changes. Use when you need to confirm Docker services are running, ports are accessible, Qdrant collections exist, LiteLLM routes are available, or systemd timers are active. Invoke proactively before making changes that depend on infrastructure state."
model: haiku
color: green
---

You are an infrastructure verification agent for a three-tier autonomous agent system running on a single workstation (Pop!_OS 24.04, RTX 3090).

## Your Job

Verify that infrastructure components are alive and correctly configured. Run actual checks — never assume.

## Checks to Run

### Docker Services
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | head -15
```
Expected: 12 containers running (ollama, qdrant, postgres, litellm, langfuse, langfuse-worker, clickhouse, redis, minio, open-webui, n8n, ntfy).

### LiteLLM Gateway
```bash
curl -s http://localhost:4000/health/liveliness | head -5
```
Expected: healthy response.

### Qdrant
```bash
curl -s http://localhost:6333/collections | jq '.result.collections[].name'
```
Expected: documents, samples, claude-memory, profile-facts.

### Ollama
```bash
curl -s http://localhost:11434/api/tags | jq '.models[].name' | head -10
```

### GPU
```bash
nvidia-smi --query-gpu=memory.used,memory.total,memory.free --format=csv,noheader
```

### Systemd Timers
```bash
systemctl --user list-timers --no-pager
```

## Output Format

```
## Infrastructure Check
- Docker: [N]/12 running [list any missing]
- LiteLLM: [healthy/unreachable]
- Qdrant: [N] collections [list any missing]
- Ollama: [N] models available
- GPU: [used]/[total] MiB
- Timers: [N] active

[Any issues or recommendations]
```

Report facts. Don't speculate about causes unless evidence is clear.
```

**Step 2: Write agents/convention-guard.md**

```markdown
---
name: convention-guard
description: "Review code changes for convention compliance against project standards. Use after implementing features, modifying code, or before committing. Checks: uv not pip, pnpm not npm, secrets in pass not hardcoded, ports on 127.0.0.1, type hints present, Pydantic models used, conventional commits, LiteLLM routing."
model: haiku
color: yellow
---

You are a convention compliance reviewer for a single-user LLM-first development stack. Your job is to catch convention violations before they ship.

## Conventions to Enforce

### Python
- Package management: `uv` only. Never `pip install`, `pip freeze`, `requirements.txt`.
- Type hints: mandatory on all function signatures.
- Models: Pydantic `BaseModel` for data structures, not plain dicts or dataclasses (unless dataclass is clearly better).
- Imports: `from __future__ import annotations` at top of every module.

### Node
- Package management: `pnpm` only. Never `npm` or `yarn`.
- One-off tools: `npx -y` with `-y` flag.

### Docker
- Compose v2: `docker compose` not `docker-compose`.
- Ports: always bound to `127.0.0.1`, never `0.0.0.0`.
- Resource limits: set on all containers.
- Images: prefer sha256 digest pinning for production.

### Secrets
- All secrets via `pass show <path>` or loaded by `direnv` from `.envrc`.
- Never hardcoded in source files.
- Never committed to git (check for `.env` files, API keys, tokens).

### LLM
- All model calls through LiteLLM at `localhost:4000`. Never direct to provider APIs (exception: Claude Code's own API calls).
- Langfuse tracing: all LLM calls should be traced.

### Git
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Feature branches from `main`.

### Architecture
- Flat orchestration: agents never invoke other agents. Claude Code or systemd invokes agents.
- Single user: no auth, no user management, no multi-tenant features (enforced by axiom-scan.sh).

## Review Process

1. Read the changed files (use `git diff` or read specific files).
2. Check each convention above.
3. Report violations with exact file:line references.
4. Categorize: BLOCK (security, correctness), WARN (convention), INFO (style).
5. If everything passes, say so briefly.

## Output Format

```
## Convention Review

**Files reviewed:** [list]
**Verdict:** [PASS / N violations found]

### Violations
1. [BLOCK/WARN/INFO] file.py:42 — description
   Fix: specific fix

### Clean
[Brief note on what's good]
```
```

**Step 3: Commit**

```bash
cd <hapax-system>
git add agents/
git commit -m "feat: infra-check + convention-guard agents"
```

---

### Task 10: Write install and uninstall scripts

**Files:**
- Create: `<hapax-system>/install.sh`
- Create: `<hapax-system>/uninstall.sh`

**Step 1: Write install.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

PLUGIN_SRC="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_NAME="hapax-system"
MARKETPLACE="hapax-local"
VERSION="1.0.0"

CACHE_DIR="$HOME/.claude/plugins/cache/$MARKETPLACE/$PLUGIN_NAME/$VERSION"
INSTALLED_PLUGINS="$HOME/.claude/plugins/installed_plugins.json"
SETTINGS="$HOME/.claude/settings.json"
RULES_DIR="$HOME/.claude/rules"

echo "Installing $PLUGIN_NAME plugin..."

# 1. Symlink plugin to cache directory
mkdir -p "$(dirname "$CACHE_DIR")"
if [ -L "$CACHE_DIR" ]; then
  rm "$CACHE_DIR"
elif [ -d "$CACHE_DIR" ]; then
  echo "ERROR: $CACHE_DIR exists and is not a symlink. Remove it first."
  exit 1
fi
ln -s "$PLUGIN_SRC" "$CACHE_DIR"
echo "  Symlinked: $CACHE_DIR -> $PLUGIN_SRC"

# 2. Register in installed_plugins.json
if [ -f "$INSTALLED_PLUGINS" ]; then
  # Add entry if not present
  if ! jq -e ".plugins[\"$PLUGIN_NAME@$MARKETPLACE\"]" "$INSTALLED_PLUGINS" > /dev/null 2>&1; then
    TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
    jq --arg name "$PLUGIN_NAME@$MARKETPLACE" \
       --arg path "$CACHE_DIR" \
       --arg ver "$VERSION" \
       --arg ts "$TIMESTAMP" \
       '.plugins[$name] = [{"scope":"user","installPath":$path,"version":$ver,"installedAt":$ts,"lastUpdated":$ts}]' \
       "$INSTALLED_PLUGINS" > "${INSTALLED_PLUGINS}.tmp" && mv "${INSTALLED_PLUGINS}.tmp" "$INSTALLED_PLUGINS"
    echo "  Registered in installed_plugins.json"
  else
    echo "  Already in installed_plugins.json"
  fi
fi

# 3. Enable in settings.json
if [ -f "$SETTINGS" ]; then
  if ! jq -e ".enabledPlugins[\"$PLUGIN_NAME@$MARKETPLACE\"]" "$SETTINGS" > /dev/null 2>&1; then
    jq --arg name "$PLUGIN_NAME@$MARKETPLACE" \
       '.enabledPlugins[$name] = true' \
       "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
    echo "  Enabled in settings.json"
  else
    echo "  Already enabled in settings.json"
  fi
fi

# 4. Symlink rules to <claude-config>/rules/
mkdir -p "$RULES_DIR"
for rule_file in "$PLUGIN_SRC/rules/"*.md; do
  if [ -f "$rule_file" ]; then
    BASENAME="$(basename "$rule_file")"
    TARGET="$RULES_DIR/hapax-$BASENAME"
    if [ -L "$TARGET" ]; then
      rm "$TARGET"
    fi
    ln -s "$rule_file" "$TARGET"
    echo "  Symlinked rule: $TARGET -> $rule_file"
  fi
done

echo ""
echo "Done. Restart Claude Code to activate."
echo "Verify: start a new session and check that /status, /briefing skills are available."
```

**Step 2: Write uninstall.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

PLUGIN_NAME="hapax-system"
MARKETPLACE="hapax-local"
VERSION="1.0.0"

CACHE_DIR="$HOME/.claude/plugins/cache/$MARKETPLACE/$PLUGIN_NAME/$VERSION"
INSTALLED_PLUGINS="$HOME/.claude/plugins/installed_plugins.json"
SETTINGS="$HOME/.claude/settings.json"
RULES_DIR="$HOME/.claude/rules"

echo "Uninstalling $PLUGIN_NAME plugin..."

# 1. Remove cache symlink
if [ -L "$CACHE_DIR" ]; then
  rm "$CACHE_DIR"
  echo "  Removed symlink: $CACHE_DIR"
fi
# Clean up empty parent dirs
rmdir "$HOME/.claude/plugins/cache/$MARKETPLACE/$PLUGIN_NAME" 2>/dev/null || true
rmdir "$HOME/.claude/plugins/cache/$MARKETPLACE" 2>/dev/null || true

# 2. Remove from installed_plugins.json
if [ -f "$INSTALLED_PLUGINS" ]; then
  jq --arg name "$PLUGIN_NAME@$MARKETPLACE" \
     'del(.plugins[$name])' \
     "$INSTALLED_PLUGINS" > "${INSTALLED_PLUGINS}.tmp" && mv "${INSTALLED_PLUGINS}.tmp" "$INSTALLED_PLUGINS"
  echo "  Removed from installed_plugins.json"
fi

# 3. Disable in settings.json
if [ -f "$SETTINGS" ]; then
  jq --arg name "$PLUGIN_NAME@$MARKETPLACE" \
     'del(.enabledPlugins[$name])' \
     "$SETTINGS" > "${SETTINGS}.tmp" && mv "${SETTINGS}.tmp" "$SETTINGS"
  echo "  Disabled in settings.json"
fi

# 4. Remove rule symlinks
for link in "$RULES_DIR"/hapax-*.md; do
  if [ -L "$link" ]; then
    rm "$link"
    echo "  Removed rule symlink: $link"
  fi
done

echo ""
echo "Done. Restart Claude Code to deactivate."
```

**Step 3: Make executable**

```bash
chmod +x <hapax-system>/install.sh <hapax-system>/uninstall.sh
```

**Step 4: Commit**

```bash
cd <hapax-system>
git add install.sh uninstall.sh
git commit -m "feat: install/uninstall scripts for plugin registration"
```

---

### Task 11: Run install and verify

**Step 1: Run install**

```bash
cd <hapax-system> && ./install.sh
```

Expected output: symlink created, registered, enabled, rules symlinked.

**Step 2: Verify file structure**

```bash
ls -la <claude-config>/plugins/cache/hapax-local/hapax-system/1.0.0/
ls -la <claude-config>/rules/hapax-*.md
jq '.enabledPlugins["hapax-system@hapax-local"]' <claude-config>/settings.json
jq '.plugins["hapax-system@hapax-local"]' <claude-config>/plugins/installed_plugins.json
```

Expected: symlink exists, rules symlinked, enabled=true, install entry present.

**Step 3: Verify hooks parse**

```bash
jq . <claude-config>/plugins/cache/hapax-local/hapax-system/1.0.0/hooks/hooks.json > /dev/null && echo "hooks.json: OK"
```

**Step 4: Verify axiom-scan still blocks violations**

```bash
echo '{"tool_input":{"new_string":"class UserManager:\n    pass","file_path":"test.py"}}' | \
  bash <hapax-system>/hooks/scripts/axiom-scan.sh 2>&1; echo "Exit: $?"
```

Expected: violation message on stderr, Exit: 2.

**Step 5: Verify axiom-scan passes clean code**

```bash
printf '{"tool_input":{"new_string":"user_config = {}","file_path":"test.py"}}' | \
  bash <hapax-system>/hooks/scripts/axiom-scan.sh 2>&1; echo "Exit: $?"
```

Expected: no output, Exit: 0.

**Step 6: Verify session-context.sh runs**

```bash
bash <hapax-system>/hooks/scripts/session-context.sh
```

Expected: multi-line output with System Context header, axiom count, branch, health, docker, GPU.

**Step 7: Commit (if any fixups needed)**

```bash
cd <hapax-system>
git status
# Only commit if there were fixups
```

---

### Task 12: Clean up migrated configs

Remove the old configurations that are now handled by the plugin.

**Step 1: Remove ai-agents axiom hooks and rules**

```bash
rm <ai-agents>/.claude/hooks/axiom-scan.sh
rm <ai-agents>/.claude/hooks/axiom-audit.sh
rm <ai-agents>/.claude/hooks/axiom-commit-scan.sh
rmdir <ai-agents>/.claude/hooks
rm <ai-agents>/.claude/rules/axioms.md
rmdir <ai-agents>/.claude/rules
rm <ai-agents>/.claude/settings.json
```

**Step 2: Commit in ai-agents**

```bash
cd <ai-agents>
git add -A .claude/
git commit -m "chore: remove axiom hooks/rules migrated to hapax-system plugin"
```

**Step 3: Remove hapaxromana operator-voice agent definition (keep memory)**

```bash
rm <hapaxromana>/.claude/agents/operator-voice.md
```

Do NOT remove `<hapaxromana>/.claude/agent-memory/operator-voice/` — the memory persists.

**Step 4: Commit in hapaxromana**

```bash
cd <hapaxromana>
git add -A .claude/agents/
git commit -m "chore: remove operator-voice agent migrated to hapax-system plugin"
```

**Step 5: Remove global commands**

```bash
rm <claude-config>/commands/status.md
rm <claude-config>/commands/briefing.md
rm <claude-config>/commands/studio.md
rm <claude-config>/commands/vram.md
rm <claude-config>/commands/ingest.md
rm <claude-config>/commands/axiom-check.md
rm <claude-config>/commands/axiom-review.md
```

**Step 6: Update global hooks.json — remove SessionStart compact hook**

Read `<claude-config>/hooks.json`. Remove the `SessionStart` entry (absorbed by plugin's session-context.sh). Keep PostToolUse prettier and Notification hooks.

New content:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "prettier --write \"$CLAUDE_FILE_PATH\" 2>/dev/null || true"
      }
    ],
    "Notification": [
      {
        "command": "notify-send 'Claude Code' \"$CLAUDE_NOTIFICATION\" --icon=dialog-information --expire-time=10000"
      }
    ]
  }
}
```

---

### Task 13: Disable duplicate and irrelevant plugins

**Files:**
- Modify: `<claude-config>/settings.json`

**Step 1: Disable duplicates and irrelevant plugins**

Use jq to set these to `false` in `<claude-config>/settings.json`:

```bash
cd ~
jq '
  .enabledPlugins["code-review@awesome-claude-plugins"] = false |
  .enabledPlugins["frontend-design@awesome-claude-plugins"] = false |
  .enabledPlugins["security-guidance@awesome-claude-plugins"] = false |
  .enabledPlugins["dns@paddo-tools"] = false |
  .enabledPlugins["mobile@paddo-tools"] = false |
  .enabledPlugins["headless@paddo-tools"] = false |
  .enabledPlugins["canvas-design@awesome-claude-plugins"] = false |
  .enabledPlugins["theme-factory@awesome-claude-plugins"] = false |
  .enabledPlugins["artifacts-builder@awesome-claude-plugins"] = false |
  .enabledPlugins["connect-apps@awesome-claude-plugins"] = false |
  .enabledPlugins["senior-frontend@awesome-claude-plugins"] = false
' <claude-config>/settings.json > <claude-config>/settings.json.tmp && mv <claude-config>/settings.json.tmp <claude-config>/settings.json
```

**Step 2: Verify**

```bash
jq '.enabledPlugins | to_entries | map(select(.value == true)) | length' <claude-config>/settings.json
```

Expected: ~24 (22 kept + hapax-system + any I missed).

```bash
jq '.enabledPlugins | to_entries | map(select(.value == false)) | .[].key' <claude-config>/settings.json
```

Expected: 11 disabled plugins listed.

---

### Task 14: Final end-to-end verification

**Step 1: Start a fresh Claude Code session**

Open a new terminal and start Claude Code in the ai-agents directory:

```bash
cd <ai-agents> && claude
```

**Step 2: Verify in the new session**

Check the following:
1. SessionStart hook fires — system context summary appears
2. Skills are available — invoke `/status` or ask about system health
3. Rules loaded — axiom governance context is in `/context`
4. Axiom scan works — try to write `class UserManager:` → should block
5. Operator-voice agent available — invoke it for a decision review
6. Old commands are gone — `/status` resolves to the plugin skill, not the old command
7. Stop hook fires — session summary appears on exit

**Step 3: Commit final state of hapax-system repo**

```bash
cd <hapax-system>
git log --oneline
```

Verify all 8+ commits are present.

---

## Summary of All Files Created

| File | Task | Purpose |
|------|------|---------|
| `hapax-system/.claude-plugin/plugin.json` | 1 | Plugin manifest |
| `hapax-system/hooks/scripts/axiom-scan.sh` | 2 | T0 violation scanner |
| `hapax-system/hooks/scripts/axiom-audit.sh` | 2 | Edit/Write audit logger |
| `hapax-system/hooks/scripts/axiom-commit-scan.sh` | 2 | Git commit/push scanner |
| `hapax-system/hooks/scripts/session-context.sh` | 3 | SessionStart system state |
| `hapax-system/hooks/hooks.json` | 4 | Hook definitions |
| `hapax-system/rules/axioms.md` | 5 | Axiom governance rules |
| `hapax-system/rules/system-context.md` | 5 | System topology rules |
| `hapax-system/skills/status/SKILL.md` | 6 | Health monitor skill |
| `hapax-system/skills/briefing/SKILL.md` | 6 | System briefing skill |
| `hapax-system/skills/studio/SKILL.md` | 6 | Music production skill |
| `hapax-system/skills/vram/SKILL.md` | 6 | GPU analysis skill |
| `hapax-system/skills/ingest/SKILL.md` | 6 | RAG pipeline skill |
| `hapax-system/skills/axiom-check/SKILL.md` | 6 | Axiom compliance skill |
| `hapax-system/skills/axiom-review/SKILL.md` | 6 | Precedent review skill |
| `hapax-system/skills/deploy-check/SKILL.md` | 7 | Pre-push readiness skill |
| `hapax-system/skills/weekly-review/SKILL.md` | 7 | Weekly review skill |
| `hapax-system/agents/operator-voice.md` | 8 | Operator stand-in agent |
| `hapax-system/agents/infra-check.md` | 9 | Infrastructure verification |
| `hapax-system/agents/convention-guard.md` | 9 | Convention compliance |
| `hapax-system/install.sh` | 10 | Plugin install script |
| `hapax-system/uninstall.sh` | 10 | Plugin uninstall script |

## Files Removed After Migration

| File | Task | Replaced By |
|------|------|-------------|
| `ai-agents/.claude/hooks/axiom-scan.sh` | 12 | Plugin hooks/scripts/ |
| `ai-agents/.claude/hooks/axiom-audit.sh` | 12 | Plugin hooks/scripts/ |
| `ai-agents/.claude/hooks/axiom-commit-scan.sh` | 12 | Plugin hooks/scripts/ |
| `ai-agents/.claude/settings.json` | 12 | Plugin hooks/hooks.json |
| `ai-agents/.claude/rules/axioms.md` | 12 | Plugin rules/axioms.md |
| `hapaxromana/.claude/agents/operator-voice.md` | 12 | Plugin agents/ |
| `<claude-config>/commands/status.md` | 12 | Plugin skills/status/ |
| `<claude-config>/commands/briefing.md` | 12 | Plugin skills/briefing/ |
| `<claude-config>/commands/studio.md` | 12 | Plugin skills/studio/ |
| `<claude-config>/commands/vram.md` | 12 | Plugin skills/vram/ |
| `<claude-config>/commands/ingest.md` | 12 | Plugin skills/ingest/ |
| `<claude-config>/commands/axiom-check.md` | 12 | Plugin skills/axiom-check/ |
| `<claude-config>/commands/axiom-review.md` | 12 | Plugin skills/axiom-review/ |
