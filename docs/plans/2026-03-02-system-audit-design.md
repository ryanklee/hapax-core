# Full System Audit Design

**Date:** 2026-03-02
**Status:** Approved
**Scope:** Everything — code, infrastructure, systemd, vault, n8n, Docker. Structural + behavioral depth.
**Output:** Per-domain findings documents + holistic findings + prioritized fix plan.

## Purpose

Audit the entire system for completeness, correctness, and robustness at the part level, then for coherence, unity, flow, and purpose at the whole level. The operator is a first-class component of the system — the holistic pass treats the human-system boundary as a system interface, not an external concern.

## System Inventory

| Component | Location | LOC | Type |
|-----------|----------|-----|------|
| Agents (13) | `<ai-agents>/agents/` | 8,418 | Python |
| Cockpit TUI + API | `<ai-agents>/cockpit/` | 7,896 | Python |
| Shared utilities | `<ai-agents>/shared/` | 6,088 | Python |
| Tests | `<ai-agents>/tests/` | 14,292 | Python |
| RAG pipeline | `<rag-pipeline>/` | 651 | Python |
| Obsidian plugin | `<obsidian-hapax>/` | 1,264 | TypeScript |
| Cockpit web | `<cockpit-web>/` | 457 | TypeScript |
| Architecture spec | `<hapaxromana>/` | — | Markdown |
| Docker infrastructure | `<llm-stack>/` | — | YAML/config |
| Systemd services | `<systemd-user>/` | — | Unit files |
| n8n workflows | `<ai-agents>/n8n-workflows/` | — | JSON |
| Obsidian vault | `<personal-vault>/` | — | Markdown/YAML |

**Total:** ~39K LOC code, 1,024 tests, 12 Docker containers, 20 systemd units, 4 n8n workflows, 3 Qdrant collections.

## Partitioning: 8 Functional Domains

Ordered from foundation upward — earlier domains inform later ones.

### Domain 1: Shared Foundation

**Files:** `shared/config.py`, `shared/operator.py`, `shared/notify.py`, `shared/vault_writer.py`, `shared/vault_utils.py`, `shared/langfuse_client.py`, `shared/langfuse_config.py`, `shared/email_utils.py`

**~1,060 LOC.** Everything else depends on this. Audit first because bugs here propagate everywhere.

**Specific focus:**
- Model alias correctness and completeness in `config.py`
- `embed()` / `embed_batch()` failure handling and prefix correctness
- `operator.json` schema validation — is the schema trusted or validated?
- `notify.py` degradation when ntfy is down, when desktop session is absent
- `vault_writer.py` handling of missing directories, permission errors, concurrent writes
- `langfuse_client.py` auth handling, timeout behavior
- Singleton patterns and initialization ordering

### Domain 2: Data Ingestion

**Files:** `shared/takeout/` (1,536 LOC, 13 parsers), `shared/proton/` (513 LOC), `shared/llm_export_converter.py` (386 LOC), `<rag-pipeline>/` (651 LOC)

**~3,086 LOC.**

**Specific focus:**
- Parser correctness against real data formats (especially Gemini parser — written speculatively)
- Resume/progress tracking reliability across Ctrl+C, crash, partial writes
- Memory behavior on large inputs (500GB/14-zip takeout)
- JSONL corruption handling (partial lines, encoding errors)
- RAG ingest watchdog recovery after crash
- Retry queue correctness (exponential backoff: 30s→2m→10m→1h→1h, 5 max)
- Frontmatter enrichment fidelity (do Qdrant payloads match source metadata?)
- `process_batch()` aggregation correctness across multiple ZIPs
- Streaming JSONL parsing in `profiler_bridge.py`

### Domain 3: Operator Profile System

**Files:** `agents/profiler.py` (1,862 LOC), `agents/profiler_sources.py` (958 LOC), `shared/profile_store.py` (178 LOC), `shared/context_tools.py` (162 LOC), `shared/management_bridge.py` (298 LOC)

**~3,458 LOC.**

**Specific focus:**
- Source discovery completeness — do all 14 reader functions actually work against real data? (3 bridged sources have both text + structured paths)
- Fact deduplication and conflict resolution logic
- Confidence scoring accuracy and consistency across sources
- Digest generation correctness (`generate_digest()` per-dimension summaries)
- Profile indexing to Qdrant (`profile-facts` collection) — deterministic IDs, batch upsert
- `apply_corrections()` with `operator:correction` source (confidence 1.0)
- Structured fact loading across takeout/proton/management JSONs
- Context tool error handling when Qdrant is down, when digest file is missing
- `management_bridge.py` vault scanning reliability (missing files, malformed frontmatter)

### Domain 4: Health & Observability

**Files:** `agents/health_monitor.py` (1,439 LOC), `agents/introspect.py` (486 LOC), `agents/drift_detector.py` (352 LOC), `agents/activity_analyzer.py` (666 LOC), `agents/knowledge_maint.py` (535 LOC)

**~3,478 LOC.**

**Specific focus:**
- All 49 health checks — do they test what they claim? Are thresholds sensible?
- Auto-fix safety — can auto-fix make things worse? What's the blast radius?
- Connectivity checks (11th group) — timeout behavior, false positives
- Drift detector accuracy — does it actually compare docs to reality or just pattern match?
- Near-duplicate detection threshold (0.98) — is this too aggressive or too lenient?
- Stale source pruning criteria in knowledge_maint — could it delete important data?
- Manifest completeness — does `introspect.py` capture everything Docker/systemd/Qdrant actually has?
- Activity analyzer Langfuse query correctness (URL encoding, date range filtering)
- Health history JSONL growth — is it bounded? Does it get pruned?

### Domain 5: Intelligence Agents

**Files:** `agents/research.py` (181 LOC), `agents/code_review.py` (120 LOC), `agents/briefing.py` (385 LOC), `agents/scout.py` (544 LOC), `agents/digest.py` (385 LOC), `agents/management_prep.py` (505 LOC)

**~2,120 LOC.**

**Specific focus:**
- Tool registration correctness — do all agents have context tools registered?
- LLM fallback behavior when primary model is down
- Output structure validation — do agents validate LLM output or trust it blindly?
- Briefing data freshness — what happens when source data is stale?
- Scout web search error handling (Tavily API failures, rate limits)
- Management prep vault dependency — what happens when vault is empty or malformed?
- Digest content collection — does it actually find recently-ingested RAG content?
- Research agent Qdrant search quality — are search results relevant?

### Domain 6: Cockpit

**Files:** `cockpit/app.py` (545), `cockpit/chat_agent.py` (985), `cockpit/interview.py` (655), `cockpit/copilot.py` (255), `cockpit/accommodations.py` (163), `cockpit/micro_probes.py` (169), `cockpit/snapshot.py` (364), `cockpit/manual.py` (280), `cockpit/runner.py` (160), `cockpit/voice.py` (28), `cockpit/screens/` (4 files), `cockpit/widgets/` (8 files), `cockpit/data/` (13 collectors)

**~7,900 LOC.** Largest domain.

**Specific focus:**
- Orphaned widgets (InfraPanel, ScoutPanel) — dead code or planned integration?
- Chat streaming reliability — what happens on network interruption, LLM timeout, malformed SSE?
- Interview state machine correctness — can it get stuck? What happens on crash mid-interview?
- Copilot priority rules — do they actually match documented behavior?
- Accommodation persistence — is `profiles/accommodations.json` read/written atomically?
- Data collector error isolation — does one failing collector break the others?
- Nudge priority scoring logic — are scores correct? Do they reflect actual urgency?
- Decision capture completeness — are all operator actions on nudges actually recorded?
- Micro-probe cooldown state — survives restart? Handles clock changes?
- `voice.py` — placeholder or dead code?
- Chat tools (`record_observation`, `read_profile`, `correct_profile_fact`) — do they actually work end-to-end?
- `/pending`, `/flush`, `/profile`, `/export`, `/stop`, `/accommodate` commands — all functional?

### Domain 7: Web Layer

**Files:** `cockpit/api/` (320 LOC), `<cockpit-web>/` (457 LOC)

**~777 LOC.** Brand new code.

**Specific focus:**
- `_to_dict()` — does it handle all real dataclass shapes from all 13 collectors?
- CORS configuration — correct origins, no overly permissive wildcards
- Cache singleton thread safety under concurrent requests
- Lifespan startup ordering — what if a collector fails during initial load?
- TypeScript types matching Python dataclasses — field names, nullability, enum values
- React query hook intervals matching cache refresh intervals (30s/5min)
- Vite proxy configuration correctness
- Missing endpoints — any data collectors not exposed via API?
- Error responses — what does the client see when cache is empty vs when collector fails?

### Domain 8: Infrastructure

**Files:** `<llm-stack>/docker-compose.yml`, systemd units (20), n8n workflows (4), `.envrc` files, Obsidian vault structure, `Dockerfile.api`

**Specific focus:**
- Docker resource limits — are MemoryMax/CPUQuota set? Are they sensible?
- Healthcheck correctness — do healthchecks actually verify service health or just process liveness?
- Systemd service hardening — MemoryMax, CPUQuota, restart policy, OnFailure
- Timer scheduling conflicts — Sunday 02:00-04:30 has backup, manifest, drift, knowledge-maint all running. Contention?
- n8n workflow correctness — do Telegram bot, briefing push, health relay actually work?
- Secret management — are any secrets in plaintext anywhere? `.env` files, n8n configs, Docker volumes?
- Vault folder structure — does it match what `vault_writer.py`, `management_bridge.py`, and profiler expect?
- `Dockerfile.api` — does it actually build? Are all required files copied? Missing profiles dir at runtime?
- Docker socket mount security — cockpit-api container has `/var/run/docker.sock:ro`
- Langfuse v3 stack — ClickHouse + Redis + MinIO correct configuration?
- Ollama GPU passthrough — is nvidia-container-toolkit properly configured?
- Log rotation — all services using json-file with 50m/3 files?
- Boot sequence — does `llm-stack.service` start everything in correct order?

## Per-Part Audit Method

For each domain:

1. **Inventory** — List every file, its purpose, its LOC, its test file
2. **Read every module** — Structural + behavioral examination
3. **Completeness findings** — Missing, dead, or assumed-but-absent
4. **Correctness findings** — Wrong, fragile, or accidental
5. **Robustness findings** — Failure modes, silent errors, missing recovery
6. **Test coverage assessment** — What's tested, what isn't, what's tested badly
7. **Write findings** — Structured per the template above

Each domain audit is independent. Findings reference specific files and line numbers.

## Holistic Audit

After all 8 domains are individually audited, examine the system as an integrated whole. The operator is a first-class component — the human-system boundary is a system interface.

### Coherence

Do the parts agree on what the system is and who the operator is? Does the operator model stay consistent across all touchpoints — the 13-dimension profile that the profiler writes, the context tools that agents query, the accommodations that shape system behavior, the nudge priorities that decide what gets attention, the copilot observations that decide what gets said? When the system prompt says "ADHD and autism — task initiation and sustained attention are genuine cognitive challenges," does every agent actually behave as though that's true?

### Unity

One operator model or several? The profiler writes `operator-profile.json`. Context tools read `profiles/operator-digest.json`. The chat agent has `record_observation`. Accommodations live in `profiles/accommodations.json`. Micro-probe state lives in `<cache>/cockpit/probe-state.json`. Pending facts in `<cache>/cockpit/pending-facts.jsonl`. Decisions in `<cache>/cockpit/decisions.jsonl`. Are these fragments of one coherent operator model, or have they drifted into parallel representations that don't inform each other?

Is there one way to do things across the system, or have parallel approaches accumulated? One notification path or three? One embedding strategy or drift between modules? Consistent naming conventions?

### Flow

Does data move through the system — including to and from the operator — without bottlenecks, dead ends, or orphaned paths?

**Operator → System:** Does operator input (vault inbox, chat, decisions, corrections, probe responses) actually reach the profile, and does the profile actually change agent behavior? Or does information enter and go nowhere?

**System → Operator:** Does system output (nudges, briefings, copilot, accommodations) actually reach the operator at the right time, in the right form, through the right channel? Given the documented neurocognitive profile, are the attention demands the system places on the operator reasonable? Does the system respect its own accommodations?

**Full lifecycle:** Raw data in → ingestion → Qdrant → retrieval → agent reasoning → output → operator attention → operator action → back into the system. Are there breaks?

### Part-to-Whole Purpose

Does every part justify its existence relative to the whole — including relative to the operator it serves? Does every agent, every nudge category, every data collector serve the stated purpose of externalized executive function? Are there components that exist because they were built, not because the operator needs them? Are there gaps — cognitive overhead the operator still carries that the system could offload but doesn't?

### Interface Integrity

Where domains meet — and where the system meets the operator — do they meet cleanly? Are the operator's interfaces well-designed for someone with the documented neurocognitive profile? Is the attention cost of each interface proportional to its value? Are the contracts between components explicit or implicit? Every seam is a potential failure point — including the seams between the system and the human it augments.

### Holistic Output

- **Coherence findings** (contradictions, disagreements between parts)
- **Unity findings** (parallel approaches, inconsistencies, naming drift)
- **Flow findings** (dead ends, orphaned data, broken chains, attention overload)
- **Purpose findings** (unjustified components, missing components, cognitive gaps)
- **Interface findings** (implicit contracts, fragile seams, mismatched assumptions)

## Sequencing

```
Domain 1: Shared Foundation
  ↓
Domain 2: Data Ingestion
  ↓
Domain 3: Operator Profile System
  ↓
Domain 4: Health & Observability
  ↓
Domain 5: Intelligence Agents
  ↓
Domain 6: Cockpit
  ↓
Domain 7: Web Layer
  ↓
Domain 8: Infrastructure
  ↓
Holistic Pass (all 5 lenses)
  ↓
Consolidated Fix Plan (prioritized)
```

Each domain produces its own findings document. The holistic pass reads all 8 findings plus the code itself. The fix plan consolidates everything into a prioritized action list.

## Output Artifacts

| Artifact | Location |
|----------|----------|
| Domain 1 findings | `docs/audit/01-shared-foundation.md` |
| Domain 2 findings | `docs/audit/02-data-ingestion.md` |
| Domain 3 findings | `docs/audit/03-operator-profile.md` |
| Domain 4 findings | `docs/audit/04-health-observability.md` |
| Domain 5 findings | `docs/audit/05-intelligence-agents.md` |
| Domain 6 findings | `docs/audit/06-cockpit.md` |
| Domain 7 findings | `docs/audit/07-web-layer.md` |
| Domain 8 findings | `docs/audit/08-infrastructure.md` |
| Holistic findings | `docs/audit/09-holistic.md` |
| Fix plan | `docs/audit/10-fix-plan.md` |

All artifacts committed to the hapaxromana repo (architecture spec repo — audit results belong with the system design, not with any single implementation repo).
