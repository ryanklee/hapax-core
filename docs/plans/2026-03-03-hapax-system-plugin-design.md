# hapax-system Plugin Design

Private Claude Code plugin that consolidates all project-specific configuration into a single portable, versioned package. Replaces scattered global commands, per-project hooks, agent definitions, and rules files with a unified plugin that provides system-aware context, axiom governance, and operator-aligned workflows.

## Design Principles

1. **Aggressive awareness**: Spend tokens freely on injecting system state into context. The operator prefers Claude Code to know everything about the stack rather than discover it incrementally.
2. **Drift resistance**: Plugin is the single source of truth. Per-repo configs are thin shells that import from the plugin, not independent copies.
3. **Executive function respect**: Silent audit by default. Block only on high-confidence T0 violations. Never add cognitive load for informational-only alerts.
4. **Flat orchestration preserved**: Plugin configures Claude Code's environment — it does not add orchestration layers. Agents remain invoked explicitly.

## Plugin Structure

```
<claude-config>/plugins/local/hapax-system/
  .claude-plugin/
    plugin.json              # Plugin manifest
  skills/
    status.md                # Health monitor (replaces /status command)
    briefing.md              # System briefing (replaces /briefing command)
    studio.md                # Music production infra (replaces /studio command)
    vram.md                  # GPU analysis (replaces /vram command)
    ingest.md                # RAG pipeline (replaces /ingest command)
    axiom-check.md           # Axiom compliance (replaces /axiom-check command)
    axiom-review.md          # Precedent review (replaces /axiom-review command)
    deploy-check.md          # Pre-push readiness check (NEW)
    weekly-review.md         # Weekly system health review (NEW)
  agents/
    operator-voice.md        # Operator stand-in (migrated from hapaxromana)
    infra-check.md           # Infrastructure verification agent (NEW)
    convention-guard.md      # Convention compliance reviewer (NEW)
  hooks/
    hooks.json               # All hook definitions
    scripts/
      axiom-scan.sh          # T0 violation scanner (migrated from ai-agents)
      axiom-audit.sh         # Edit/Write audit logger (migrated from ai-agents)
      axiom-commit-scan.sh   # Git commit/push scanner (migrated from ai-agents)
      session-context.sh     # SessionStart: inject system state (NEW)
      compact-restore.sh     # PreCompact: preserve critical context (NEW)
  rules/
    axioms.md                # Axiom governance context (migrated from ai-agents)
    conventions.md           # Stack conventions (derived from global rules)
    system-context.md        # Live system topology + agent inventory
  .mcp.json                  # Plugin-scoped MCP servers (if needed)
```

## Hooks Pipeline

### hooks/hooks.json

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/session-context.sh"
        }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/axiom-scan.sh"
        }]
      },
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/axiom-commit-scan.sh"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [{
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/axiom-audit.sh"
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": "AUDIT_FILE=\"$HOME/.cache/axiom-audit/$(date +%Y-%m-%d).jsonl\"; if [ -f \"$AUDIT_FILE\" ]; then TOTAL=$(wc -l < \"$AUDIT_FILE\"); BLOCKED=$(grep -c '\"blocked\":true' \"$AUDIT_FILE\" 2>/dev/null || echo 0); echo \"Axiom audit: $TOTAL edits tracked, $BLOCKED blocked.\"; fi"
        }]
      }
    ]
  }
}
```

### Hook Details

| Event | Script | Purpose | Blocking? |
|-------|--------|---------|-----------|
| SessionStart | `session-context.sh` | Inject axiom status + system health summary | No |
| PreToolUse (Edit/Write) | `axiom-scan.sh` | T0 violation pattern scan on file content | Yes (exit 2) |
| PreToolUse (Bash) | `axiom-commit-scan.sh` | Scan git commit/push diffs for T0 violations | Yes (exit 2) |
| PostToolUse (Edit/Write) | `axiom-audit.sh` | Log edits to JSONL audit trail | No |
| Stop | inline | One-line session audit summary | No |

### session-context.sh (NEW)

Replaces both the ai-agents SessionStart hook and the global compact SessionStart hook. Outputs:

```
## System Context
Axioms: 2 loaded (single_user, executive_function)
Branch: feat/current-work | Last commit: abc1234 feat: something
Health: 40/40 healthy (15m ago) | Docker: 12/12 running
GPU: 8192/24576 MiB used
```

Subsumes the global `<claude-config>/hooks.json` SessionStart compact hook (which currently shows branch/commit/docker/GPU). The global hook can be removed after plugin activation.

### compact-restore.sh (DEFERRED)

PreCompact hook for preserving critical context during compaction. Deferred to Batch 4 — need to validate that PreCompact is available in the current Claude Code version and understand the exact stdin/stdout contract.

## Skills (9 total)

### Migrated from Commands (7)

Each command at `<claude-config>/commands/*.md` becomes a SKILL.md in the plugin. The upgrade adds:
- Structured YAML frontmatter (name, description, trigger patterns)
- Richer context injection (skills can include tool allowlists, model overrides)
- Plugin portability (moves with the plugin, not scattered globally)

| Skill | Source Command | Changes |
|-------|---------------|---------|
| `status` | `/status` | No functional changes |
| `briefing` | `/briefing` | No functional changes |
| `studio` | `/studio` | No functional changes |
| `vram` | `/vram` | No functional changes |
| `ingest` | `/ingest` | No functional changes |
| `axiom-check` | `/axiom-check` | No functional changes |
| `axiom-review` | `/axiom-review` | No functional changes |

### New Skills (2)

**deploy-check**: Pre-push readiness verification. Runs health monitor, checks axiom compliance of staged changes, verifies tests pass, checks for uncommitted files. Invoked manually before push.

**weekly-review**: Aggregates the week's audit log, drift report, scout report, and health history into a structured weekly review. Designed to be run Sunday evenings or Monday mornings.

## Agents (3)

### operator-voice (migrated)

Moved from `hapaxromana/.claude/agents/operator-voice.md` to plugin scope. No functional changes — same system prompt, same memory directory, same model (opus). The hapaxromana-local copy is deleted after migration.

### infra-check (NEW)

Lightweight agent that verifies infrastructure assumptions before implementation. Invoked by convention-guard or manually. Checks: Docker services running, ports accessible, Qdrant collections exist, LiteLLM routes available.

```yaml
---
name: infra-check
description: Verify infrastructure assumptions before implementation changes
model: haiku
---
```

### convention-guard (NEW)

Reviews code changes for convention compliance. Not a blocking hook — invoked on-demand or by other agents. Checks: uv not pip, pnpm not npm, secrets in pass, ports on 127.0.0.1, type hints present, Pydantic models used, conventional commits.

```yaml
---
name: convention-guard
description: Review code for convention compliance against project standards
model: haiku
---
```

## Rules (3 files)

### axioms.md (migrated)

Moved from `ai-agents/.claude/rules/axioms.md`. Contains both axiom texts and all T0 blocking implications. Loads in every session via plugin rules auto-loading.

### conventions.md (NEW)

Distills from the 4 global rules files (`environment.md`, `toolchain.md`, `models.md`, `music-production.md`) into a single file scoped to this project's concerns. The global files remain for non-project contexts. This file focuses on:
- Python: uv, type hints, Pydantic
- Node: pnpm
- Docker: compose v2, resource limits, 127.0.0.1 binding
- Secrets: pass + direnv
- Git: conventional commits, feature branches from main
- LLM: all calls through LiteLLM, Langfuse tracing
- Embeddings: nomic-embed-text-v2-moe, 768d, prefix requirements

### system-context.md (NEW)

Live reference for the system topology. Unlike CLAUDE.md (which is a human-maintained document), this is a machine-readable summary:
- Service topology (containers, ports, health endpoints)
- Agent inventory (all Tier 2 agents with invocation patterns)
- Timer schedule
- Model aliases
- Qdrant collections
- Key file paths

This file is ~100-150 lines and provides the "system awareness" that the operator wants Claude Code to always have.

## Per-Repo Configuration

After plugin activation, per-repo `.claude/` directories become thin:

### ai-agents/.claude/

```
settings.json    → REMOVE (hooks migrated to plugin)
rules/axioms.md  → REMOVE (migrated to plugin)
hooks/           → REMOVE (scripts migrated to plugin)
```

The only remaining config is project-level permissions in `settings.local.json` (if needed).

### hapaxromana/.claude/

```
agents/operator-voice.md           → REMOVE (migrated to plugin)
agent-memory/operator-voice/       → STAYS (memory persists, plugin agent reads from same path)
settings.local.json                → STAYS (project-level permissions)
```

### Other repos (rag-pipeline, obsidian-hapax, etc.)

No changes needed. The plugin loads globally. Repo-specific CLAUDE.md files continue to provide per-repo context.

## Global Configuration Changes

### <claude-config>/hooks.json

Remove the SessionStart compact hook (absorbed by plugin's session-context.sh). Keep:
- PostToolUse prettier (non-conflicting, useful for non-project files)
- Notification hook (useful, non-conflicting)

After:
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

### <claude-config>/commands/

All 7 command files are removed after plugin skills are verified working:
- `status.md`, `briefing.md`, `studio.md`, `vram.md`, `ingest.md`, `axiom-check.md`, `axiom-review.md`

### <claude-config>/rules/

All 4 global rule files stay. They provide context in non-project sessions too. The plugin's `conventions.md` is a project-focused distillation, not a replacement.

### <claude-config>/settings.json — Plugin Cleanup

Disable these plugins (duplicates or irrelevant):

**Duplicates (keep official, disable awesome):**
- `code-review@awesome-claude-plugins`
- `frontend-design@awesome-claude-plugins`
- `security-guidance@awesome-claude-plugins`

**Irrelevant to this project's stack:**
- `dns@paddo-tools` (no DNS management)
- `mobile@paddo-tools` (no mobile apps)
- `headless@paddo-tools` (no site migration)
- `canvas-design@awesome-claude-plugins` (no visual art generation)
- `theme-factory@awesome-claude-plugins` (no artifact theming)
- `artifacts-builder@awesome-claude-plugins` (no Claude.ai artifacts)
- `connect-apps@awesome-claude-plugins` (no third-party app integration)
- `senior-frontend@awesome-claude-plugins` (redundant with frontend-developer)

**Keep (22 plugins including hapax-system):**
- `context7`, `superpowers`, `compound-engineering`, `playwright`, `github`, `feature-dev`, `code-simplifier`, `ralph-loop`, `gemini-tools`, `backend-architect`, `debugger`, `bug-fix`, `perf`, `mcp-builder`, `documentation-generator`, `audit-project`, `commit`, `frontend-developer`, `changelog-generator`, `frontend-design@official`, `code-review@official`, `security-guidance@official`

## StatusLine

Configure ambient terminal status in the plugin or via user settings:

```json
{
  "statusLine": {
    "enabled": true,
    "template": "{{branch}} | {{model}} | axioms: active"
  }
}
```

This is a low-priority enhancement. The built-in StatusLine shows branch and model by default. Custom templates may not be supported yet — validate before implementing.

## Migration Plan

### Phase 1: Create Plugin Structure
1. Create `<claude-config>/plugins/local/hapax-system/` directory tree
2. Write `plugin.json` manifest
3. Copy/adapt all scripts, skills, agents, rules
4. Register plugin in `<claude-config>/settings.json`

### Phase 2: Verify Plugin Loads
1. Start new Claude Code session
2. Verify skills appear in `/skills` or Skill tool
3. Verify hooks fire (test axiom-scan with intentional violation)
4. Verify agents appear in Agent tool
5. Verify rules load (check `/context`)

### Phase 3: Remove Migrated Configs
1. Remove `ai-agents/.claude/settings.json`, `rules/`, `hooks/`
2. Remove `hapaxromana/.claude/agents/operator-voice.md`
3. Remove `<claude-config>/commands/*.md` (all 7)
4. Remove SessionStart compact hook from `<claude-config>/hooks.json`
5. Disable duplicate/irrelevant plugins in `<claude-config>/settings.json`

### Phase 4: Iterate (Batch 4 from axiom plan)
1. Analyze audit data after 1 week
2. Tune violation patterns
3. Evaluate PreCompact hook (if supported)
4. Evaluate PostToolUse semantic evaluation (if pattern scanner has gaps)
5. Consider StatusLine custom template (if supported)

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Plugin hooks don't fire in non-project dirs | Plugin hooks are global — they fire everywhere. Scripts check `$CLAUDE_PROJECT_DIR` before acting |
| Hook ordering with other plugins | Claude Code runs hooks in registration order. Our PreToolUse axiom-scan fires alongside security-guidance — both are non-conflicting (different concerns) |
| Skills collide with old commands | Remove commands in Phase 3 AFTER verifying skills work |
| Operator-voice agent memory path changes | Keep memory at original path, reference via absolute path in agent definition |
| Token budget from system-context.md | ~150-200 lines ≈ 500-800 tokens. Acceptable under aggressive budget policy |

## What Stays Outside the Plugin

| Item | Location | Why |
|------|----------|-----|
| Global rules (4 files) | `<claude-config>/rules/` | Apply to all projects, not just this stack |
| Per-repo CLAUDE.md | Each repo root | Repo-specific context, maintained alongside code |
| Per-repo .claudeignore | Each repo root | Repo-specific file exclusions |
| Prettier PostToolUse hook | `<claude-config>/hooks.json` | Applies to all projects |
| Notification hook | `<claude-config>/hooks.json` | Applies to all projects |
| Project permissions | Each repo's `settings.local.json` | Per-repo, not portable |
| Operator-voice memory | `hapaxromana/.claude/agent-memory/` | Persists independently of agent definition |
