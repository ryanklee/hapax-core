# Cross-Project Boundary: Hapax System ↔ Management Cockpit

This document defines the relationship between the wider hapax system and the
containerized management cockpit. It must be byte-identical in both repos:

- `<hapaxromana>/docs/cross-project-boundary.md`
- `<hapax-mgmt>/docs/cross-project-boundary.md`

Any divergence is a high-severity drift item detected by the wider system's
drift-detector agent (weekly Sunday 03:00).

## Project Identities

**Wider Hapax System** (`hapaxromana` + `ai-agents`): A personal executive
function platform for a single operator. Covers all domains — management,
personal knowledge, health monitoring, audio capture, content sync, creative
production. 28+ agents across sync, RAG, analysis, and automation.

**Management Cockpit** (`hapax-mgmt`): A management-only decision
support system extracted from the wider system in March 2026. Purpose-built
for team leadership — 1:1 prep, coaching tracking, management self-awareness
profiling, actionable nudges. 8 agents, all management-scoped. Safety
principle: LLMs prepare, humans deliver.

## Shared Lineage

Both projects share the same origin codebase. The management cockpit was
extracted via a deliberate conversion that:

- Removed 22 agents outside management scope
- Renamed 5 agents for management clarity
- Added 1 management-specific agent (management_activity)
- Regrounded axioms from personal/ADHD context to management decision theory
- Removed all personal context (executive function, ADHD accommodations)
- Rewrote the demo pipeline for management-only content

The extraction is documented in:
- `hapax-mgmt/docs/plans/2026-03-06-management-conversion-design.md`
- `hapax-mgmt/docs/plans/2026-03-06-management-conversion-plan.md`

## Axiom Correspondence

Containerization's axioms are a fork-with-rename of the wider system's axioms.
Same constitutional principles, different grounding language.

| Wider System (hapaxromana) | Containerization | Weight | Notes |
|---------------------------|------------------|--------|-------|
| single_user | single_operator | 100 | Same semantics, role-generic language |
| executive_function | decision_support | 95 | Regrounded: ADHD accommodation → decision-support theory |
| management_governance | management_safety | 95 | Elevated: domain axiom → constitutional scope |
| corporate_boundary | corporate_boundary | 90 | Unchanged, dormant in both |

All T0 blocking implications are preserved. Only the grounding text differs.

## Agent Roster Divergence

### Present in both (identical or renamed)

| Wider System | Containerization | Change |
|-------------|------------------|--------|
| management_prep | management_prep | Identical |
| meeting_lifecycle | meeting_lifecycle | Identical |
| briefing | management_briefing | Renamed, management-focused |
| profiler | management_profiler | Renamed, 13 → 6 dimensions |
| demo, demo_eval | demo, demo_eval | Ported with adaptation |
| health_monitor | system_check | Rewritten: 75 checks → 4, no auto-fix |

### Only in containerization

| Agent | Purpose |
|-------|---------|
| management_activity | Vault-based management practice metrics (no LLM) |

### Only in wider system (22 agents removed from containerization)

Sync agents (7): gdrive_sync, gcalendar_sync, gmail_sync, youtube_sync,
chrome_sync, claude_code_sync, obsidian_sync.

Analysis agents (5): research, code_review, introspect, drift_detector, scout.

Content agents (4): digest, knowledge_maint, ingest, activity_analyzer.

Audio agents (3): audio_processor, hapax_voice, audio_recorder (systemd).

Other (3): query, profiler_sources, demo pipeline differences.

## Shared Modules

18 modules in `shared/` exist in both repos. Containerization is a strict
subset — it has no unique shared modules.

Key shared modules: config.py, operator.py, profile_store.py,
management_bridge.py, notify.py, vault_writer.py, axiom_*.py,
context_tools.py, langfuse_client.py, langfuse_config.py.

The wider system has 18 additional shared modules not present in
containerization (google_auth.py, calendar_context.py, health_*.py,
capacity.py, dimensions.py, email_utils.py, service_*.py, etc.).

## Infrastructure (Isolated)

Each system runs its own infrastructure stack. No shared services, databases,
collections, or traces.

| Service | Wider System | Management Cockpit |
|---------|-------------|-------------------|
| Qdrant | localhost:6333 | localhost:6433 |
| LiteLLM | localhost:4000 | localhost:4100 |
| Langfuse | localhost:3000 | localhost:3100 |
| PostgreSQL | localhost:5432 | localhost:5532 |
| Ollama | localhost:11434 | localhost:11434 (shared — single GPU) |

Ollama is the one shared service — stateless inference with auto-managed
model loading. Both stacks point at the same instance. Not a data store.

## Isolation Status

Infrastructure isolation completed March 2026. Each system has its own
Qdrant collections, LiteLLM proxy, Langfuse traces, and PostgreSQL databases.
Ollama remains shared (single GPU constraint, stateless inference).

Data source isolation in progress — the management cockpit's vault dependency
has been excised. VS Code + Qdrant integration is the planned replacement.

## Boundary Rules

Changes in one repo that may affect the other:

- **Shared module APIs**: Function signatures and class interfaces in shared/
  modules used by both repos. A breaking change in one breaks the other.
- **Axiom semantics**: Redefining what a constitutional axiom means affects
  both systems' governance.
- **Qdrant collection schemas**: Field names, vector dimensions, payload
  structure changes affect both readers.
- **Vault structure**: Path changes in <work-vault>/ that
  management_bridge.py reads.
- **Profile dimensions**: The 6 management dimensions in profile_store.py
  are used by both systems' profilers.
- **Operator manifest**: operator.json structure changes affect both
  operator.py implementations.
