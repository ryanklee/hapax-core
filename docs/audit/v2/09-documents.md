# Domain 9: Documents & Specifications — Audit v2 Findings

**Auditor:** Claude Opus 4.6
**Date:** 2026-03-03
**Scope:** 8 documents (~2,300 LOC), 4 rule files (~62 LOC), 1 config registry (371 LOC)
**v1 reference:** None (new domain in v2)

## Inventory

| Document | LOC | Purpose | Authority |
|----------|-----|---------|-----------|
| `<hapaxromana>/CLAUDE.md` | 178 | Project-level agent specification | Primary — agents, timers, channels |
| `<hapaxromana>/agent-architecture.md` | 281 | Original design proposal | Historical — pre-implementation |
| `<ai-agents>/README.md` | 192 | Agent project documentation | Primary — developer reference |
| `<ai-agents>/n8n-workflows/README.md` | 105 | n8n workflow setup guide | Primary — workflow reference |
| `<ai-agents>/profiles/operations-manual.md` | 303 | Operator task reference | Primary — operational reference |
| `<ai-agents>/profiles/component-registry.yaml` | 371 | Scout agent input | Primary — component inventory |
| `<claude-config>/CLAUDE.md` | ~267 | Global Claude Code context | Primary — environment reference |
| `<claude-config>/rules/environment.md` | 11 | Environment context | Supplementary |
| `<claude-config>/rules/toolchain.md` | 13 | Toolchain conventions | Supplementary |
| `<claude-config>/rules/models.md` | 17 | Model selection guide | Supplementary |
| `<claude-config>/rules/music-production.md` | 21 | Music production context | Supplementary |

### Audit Axes (Document-Specific)

- **Accuracy (A-9.X):** Factual claims verified against reality
- **Completeness (P-9.X):** Implemented features documented
- **Consistency (K-9.X):** Documents agree with each other
- **Currency (U-9.X):** Post-fix state reflected

---

## Findings

### Accuracy

#### A-9.1: Health check count conflicts — 44 vs 49 [medium]

Four documents claim different health check counts:

| Document | Claim | Groups |
|----------|-------|--------|
| `<claude-config>/CLAUDE.md` | 44 checks | — |
| `operations-manual.md` (lines 33, 139) | 44 checks, 10 groups | 10 |
| `hapaxromana/CLAUDE.md` (line 44) | 49 checks (incl. connectivity) | 11 |
| `ai-agents/README.md` (line 24) | 49 checks | — |

**Reality:** 23 check functions across **11** groups (docker, gpu, systemd, qdrant, profiles, endpoints, credentials, disk, models, auth, connectivity). Each function returns a variable number of `CheckResult` objects — the total depends on runtime state (how many containers, services, collections exist). Neither 44 nor 49 is a stable number.

The "11 groups" claim in the project CLAUDE.md is correct. The operations manual's "10 groups" is wrong (likely predates the connectivity group addition).

#### A-9.2: README test count stale [low]

`ai-agents/README.md:188` — `uv run pytest tests/ -q       # Run tests (988 passing)`
`ai-agents/README.md:122` — `tests/            970+ tests (pytest, no LLM calls)`

**Reality:** 1210 passed, 1 failed (1211 total). The count is 22% higher than documented. The 988 figure is from before the Takeout/Proton/management additions.

#### A-9.3: agent-architecture.md lists sample-watch as implemented [low]

`agent-architecture.md:46` — Tier 3 diagram shows `sample-watch` alongside `rag-ingest`, `health-monitor timer`, `knowledge-maint`. No `sample-watch.service` or `sample-watch.timer` exists in `<systemd-user>/`. The sample-curator agent is still in "planned" status.

#### A-9.4: agent-architecture.md lists knowledge-maint as n8n-scheduled [low]

`agent-architecture.md:189-192` — Knowledge maintenance described as "n8n scheduled" workflow using "Qdrant API calls → LiteLLM for summarization → Qdrant update." **Reality:** knowledge-maint is a Pydantic AI agent (`agents/knowledge_maint.py`) triggered by a systemd timer (`knowledge-maint.timer`, Sunday 04:30), not an n8n workflow.

#### A-9.5: Operations manual lists wrong check groups [low]

`operations-manual.md:148` — `--check GROUPS` choices listed as: `docker, gpu, systemd, qdrant, profiles, endpoints, credentials, disk`. Missing 3 actual groups: `models`, `auth`, `connectivity`. These were added after the manual was written.

### Completeness

#### P-9.1: Operations manual missing 3 agents and 2 timers [medium]

The Quick Reference table (lines 8-17) lists 9 agents. Missing from all sections:
- `management-prep` — no mention anywhere in the manual
- `digest` — no mention anywhere in the manual
- `knowledge-maint` — no mention anywhere in the manual

The Timer Schedule table (lines 283-293) lists 7 timers. Missing:
- `digest.timer` (Daily 06:45)
- `knowledge-maint.timer` (Weekly Sun 04:30)

These agents and timers are documented in the README and project CLAUDE.md, but the operations manual — the primary operator reference — lacks them entirely.

#### P-9.2: agent-architecture.md lists digest as planned, not implemented [low]

`agent-architecture.md:38` — `Planned: sample-curator, digest, draft, midi-programmer`. Both digest and knowledge-maint have been implemented (with tests, systemd timers, and watchdog scripts). The architecture doc's "Implemented" list (lines 31-35) shows only 10 agents, missing digest and knowledge-maint.

#### P-9.3: agent-architecture.md open questions are answered [low]

`agent-architecture.md:269-281` — Six "Open Questions" remain in the document:
1. Agent-to-agent communication → **Decided: flat orchestration** (documented everywhere else)
2. State management → **Decided: stateless per-invocation** (documented everywhere else)
3. Cost controls → **Implemented: LiteLLM fallback chains, Langfuse cost tracking**
4. Eval integration → **Not implemented, but descoped** (promptfoo exists but not per-agent)
5. Scout confidence calibration → **Partially addressed** (scout-history.jsonl tracks adopt/evaluate counts)
6. Adoption automation → **Decided: operator confirms** (documented in operations-manual)

### Consistency

#### K-9.1: Tier 2 agent count inconsistent across documents [medium]

| Document | Implemented Count | Listed |
|----------|-------------------|--------|
| `agent-architecture.md` | 10 | research, code-review, profiler, health-monitor, introspect, drift-detector, activity-analyzer, briefing, scout, management-prep |
| `hapaxromana/CLAUDE.md` | 12 | Adds digest, knowledge-maint |
| `ai-agents/README.md` | 12 | Same as project CLAUDE.md |
| `operations-manual.md` | 9 | Missing management-prep, digest, knowledge-maint |
| `<claude-config>/CLAUDE.md` | 12 | Full list |

The project CLAUDE.md and README are the most current (12 agents). The operations manual and architecture doc have not been updated.

#### K-9.2: Timer count inconsistent [low]

| Document | Timers Listed |
|----------|---------------|
| `operations-manual.md` | 7 (missing digest, knowledge-maint) |
| `hapaxromana/CLAUDE.md` | 10 (includes digest, knowledge-maint, and notes Obsidian desktop + gdrive-sync planned) |
| `ai-agents/README.md` | 11 (includes obsidian-sync and gdrive-sync as if active; gdrive-sync noted as planned) |
| `<claude-config>/CLAUDE.md` | 10 |

The README lists `obsidian-sync` as "Always running" — this is actually the Obsidian Desktop app (desktop autostart entry), not a systemd timer. Listing it as a timer row is misleading.

#### K-9.3: Model references inconsistent precision [low]

| Document | Model Reference |
|----------|----------------|
| `<claude-config>/rules/models.md` | `claude-sonnet-4-5` (pinned) |
| `hapaxromana/CLAUDE.md` | `claude-sonnet` (alias) |
| `agent-architecture.md` | `claude-sonnet` (alias) |
| `<claude-config>/CLAUDE.md` | `claude-sonnet` (alias) in table, specific IDs elsewhere |

The rules/models.md uses a different naming convention (provider model IDs) than the rest of the docs (LiteLLM aliases). Not a conflict, but a reader encountering both would need to know the alias mapping.

### Currency

#### U-9.1: agent-architecture.md is pre-implementation design doc [medium]

The architecture document reflects the original design proposal, not the current state. Specific stale items:
- Tier 2 shows 10 implemented (actually 12)
- Tier 3 lists sample-watch (doesn't exist) and knowledge-maint as n8n (is systemd)
- Open Questions contain answered decisions
- digest-agent description (lines 81-86) describes a morning email/calendar/GitHub aggregator — the actual implementation is a RAG content digest
- Implementation Priority section (lines 194-211) has phases that are now irrelevant
- Shared Infrastructure code block (lines 217-235) shows a simplified config.py that doesn't match the actual `shared/config.py`

The document is valuable as historical context but should be marked as such or updated to reflect reality.

#### U-9.2: Operations manual predates 3 agents and 2 timers [low]

Written before management-prep, digest, and knowledge-maint were implemented. The manual is otherwise accurate for the agents it covers — the missing items are additions, not corrections.

---

## Document Quality Assessment

### By Document

| Document | Accuracy | Completeness | Consistency | Currency | Overall |
|----------|----------|--------------|-------------|----------|---------|
| `hapaxromana/CLAUDE.md` | High | High | High | Current | Best |
| `ai-agents/README.md` | Medium (test count) | High | High | Mostly current | Good |
| `<claude-config>/CLAUDE.md` | Medium (44 checks) | High | High | Mostly current | Good |
| `n8n-workflows/README.md` | High | High | High | Current | Good |
| `operations-manual.md` | Medium (44/10) | Low (missing 3 agents) | Low | Stale | Needs update |
| `agent-architecture.md` | Low | Low | Low | Stale | Historical |
| `component-registry.yaml` | High | High | High | Current | Good |
| Rule files (4) | High | High | High | Current | Good |

### Authority Hierarchy

The documents form an implicit hierarchy, but it's not documented anywhere:
1. **hapaxromana/CLAUDE.md** — most current, most complete
2. **ai-agents/README.md** — developer reference, matches #1
3. **<claude-config>/CLAUDE.md** — environment context, mostly matches
4. **operations-manual.md** — operator reference, partially stale
5. **agent-architecture.md** — historical design, significantly stale

When documents conflict, the hapaxromana CLAUDE.md should be treated as authoritative. But a reader encountering the operations manual first would get incomplete and partially wrong information.

---

## Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Accuracy | 0 | 0 | 1 | 4 | **5** |
| Completeness | 0 | 0 | 1 | 2 | **3** |
| Consistency | 0 | 0 | 1 | 2 | **3** |
| Currency | 0 | 0 | 1 | 1 | **2** |
| **Total** | **0** | **0** | **4** | **9** | **13** |

**Core issue:** Documents were written at different points during implementation and not all kept current. The hapaxromana CLAUDE.md and README are well-maintained. The operations manual and architecture doc have drifted. The architecture doc is the most stale — it's a design proposal that should either be updated to reflect reality or explicitly marked as historical.

**No critical or high findings.** All issues are medium (conflicting counts, missing agents) or low (stale details). The system's documentation is substantially better than average for a personal project, but the multi-document architecture creates drift opportunities that aren't caught by the existing drift-detector agent (which compares docs vs running system, not docs vs docs).
