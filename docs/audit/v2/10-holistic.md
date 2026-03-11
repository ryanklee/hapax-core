# Holistic Pass — Audit v2 Findings

**Auditor:** Claude Opus 4.6
**Date:** 2026-03-03
**Scope:** Cross-cutting assessment of the complete system across 9 domains
**Method:** Five lenses — Coherence, Unity, Flow, Operator Fit, Architectural Integrity

## Aggregate Summary

### Finding Counts by Domain

| Domain | Findings | Medium+ | Fix Verified | Fix Partial | Fix Failed |
|--------|----------|---------|-------------|-------------|------------|
| D1 Shared Foundation | 12 | 1 | 7/9 | 1 | 0 |
| D2 Data Ingestion | 14 | 2 | 8/12 | 2 | 1 |
| D3 Operator Profile | 16 | ~4 | 1/4 | 2 | 1 |
| D4 Health & Observability | 17 | 3 | 6/6 | 0 | 0 |
| D5 Intelligence Agents | 10 | 2 | 10/11 | 1 | 0 |
| D6 Cockpit TUI | 9 | 3 | 7/9 | 0 | 1+1bug |
| D7 Web Layer | 6 | 1 | 8/12 | 2 | 1 |
| D8 Infrastructure | 6 | 1 | 13/16 | 1 | 1 |
| D9 Documents | 13 | 4 | n/a | n/a | n/a |
| **Total** | **~103** | **~21** | **60/79** | **9** | **5+1bug** |

### Fix Verification Summary

Of 79 v1 fixes verified across 8 code domains:
- **60 fully verified** (76%) — fix present, correct, no regressions
- **9 partial** (11%) — fix attempted, partially effective
- **5 not fixed** (6%) — fix not implemented
- **1 with bugs** (1%) — fix introduced new defects (D6 decisions.py)
- **4 other** (5%) — subsumed, caveat, or improved

The fully-verified rate is strong for a set of 89 fixes applied in a single session. The one buggy fix (decisions.py) is the most concerning — it's in the operator's executive function infrastructure.

---

## Lens 1: Coherence

*Do parts agree on what the system is and who the operator is?*

### System Identity: Strong

All components share a clear identity: three-tier autonomous agent system for a single operator on a single workstation. This identity is:
- Stated consistently across all 9 documents
- Enforced architecturally (LiteLLM gateway, Qdrant memory, Langfuse observability)
- Reflected in code (flat orchestration, stateless agents, pass-backed secrets)

### Operator Identity: Strong

The operator model is consistent: experienced developer with executive function needs, music production background, management responsibilities. This is woven through:
- Profiler (13 dimensions, multiple sources)
- Accommodations system (negotiated behavior changes)
- Neurocognitive axiom in operator.json
- System prompt injection via context tools
- Management prep agent + vault bridge

### H2-1.1: Document authority hierarchy undefined [medium]

Nine documents describe the system. When they conflict (health check counts, agent inventories, timer lists), there is no declared source of truth. A reader encountering `operations-manual.md` first would get incomplete and partially wrong information. The drift detector compares documents against the running system but not against each other.

**Pattern:** The hapaxromana CLAUDE.md is implicitly authoritative (most current, most complete), but this is not documented. The architecture doc (`agent-architecture.md`) is implicitly historical, but this is also not marked.

---

## Lens 2: Unity

*One way to do things, or parallel approaches accumulating?*

### Unified: Model Access

All LLM calls route through LiteLLM. All embeddings use nomic-embed via Ollama. All vector storage uses Qdrant. All observability flows through Langfuse. No exceptions found across 12 agents and all infrastructure components. This is the strongest unity across the system.

### Unified: Secret Management

All secrets stored in `pass`, accessed via `.envrc` or `generate-env.sh`. No hardcoded secrets in any codebase (D8 verified). The generate-env.sh pattern for Docker services is elegant and consistent.

### H2-2.1: Atomic write pattern inconsistency [medium]

Six modules need atomic file writes. Four different patterns are used:

| Module | Pattern | Correct? |
|--------|---------|----------|
| `accommodations.py` | `tempfile.mkstemp()` + `os.replace()` | Yes |
| `chat.py` (flush) | `tempfile.mkstemp()` + `os.replace()` | Yes |
| `decisions.py` (rotation) | `os.fdopen()` + `os.replace()` + `os.unlink()` | Broken (missing `import os`) |
| `micro_probes.py` | `Path.write_text()` | No (truncate-then-write) |
| `vault_writer.py` | `Path.write_text()` | No (truncate-then-write) |
| `health-watchdog` (fix-attempts) | `open('w')` | No (truncate-then-write) |

Three of six modules use non-atomic writes. This means process interruption (OOM, signal) could corrupt state files. The impact varies: micro_probes and fix-attempts have safe fallback behavior (reset to defaults), but vault_writer corruption could lose a briefing or nudge update.

### H2-2.2: Notification dispatch fragmentation [low]

`shared/notify.py` provides unified notification dispatch (ntfy + desktop). But only 2 of 6 watchdog scripts use it:
- health-watchdog: uses `shared.notify.send_notification()` — mobile + desktop
- scout-watchdog: uses agent `--notify` flag — mobile + desktop
- briefing-watchdog: uses raw `notify-send` — desktop only
- digest-watchdog: inline Python — desktop only
- drift-watchdog: inline Python — desktop only
- knowledge-maint-watchdog: inline Python — desktop only

This means briefing completions, drift detections, digest summaries, and knowledge maintenance results don't reach mobile (ntfy). The operator only gets mobile push for health alerts and scout recommendations.

---

## Lens 3: Flow

*Data moves without breaks, dead ends, or orphaned paths?*

### Working Flows

Seven primary data flows were verified as complete:

1. **Health loop:** timer → health-monitor → history.jsonl → activity-analyzer → briefing → vault + ntfy
2. **Profile loop:** sources → profiler → operator.json → context tools → agent system prompts
3. **Knowledge loop:** documents → RAG ingest → Qdrant → research agent → stdout
4. **Vault egress:** agents → vault_writer → 30-system/ → Obsidian Sync → all devices
5. **Vault ingress:** 31-system-inbox/ → RAG ingest → Qdrant; profiler reads vault-inbox
6. **Management loop:** vault people/coaching → management_bridge → profiler → operator.json
7. **Scout loop:** component-registry → scout → scout-report → briefing integration

### H2-3.1: Accommodation tracking flow broken [high]

The decision/accommodation tracking flow is severed by two bugs in `decisions.py`:

1. **Missing `import os`** (R2-6.1): The rotation function uses `os.fdopen()`, `os.replace()`, `os.unlink()` but `os` is not imported. This crashes at runtime after 500 decision records when rotation triggers. The crash is caught by a bare `except Exception: pass`, making it silent.

2. **Wrong attribute `a.key`** (R2-6.2): `decision.active_accommodations = [a.key for a in active if a.active]` uses `a.key` but the Accommodation dataclass has `a.id`. This crashes inside a `try/except`, so accommodations are never recorded in decision records.

**Flow impact:** The operator activates accommodations (e.g., `time_anchor`, `soft_framing`). The cockpit records decisions on nudges. But the decision records never include which accommodations were active at the time. The profiler reads decisions.jsonl but gets empty accommodation lists, so it can never correlate decision patterns with accommodation states. The feedback loop from accommodations → decisions → profiler → accommodation effectiveness is broken.

### H2-3.2: Micro-probe state is a dead end [low]

Micro-probes collect operator responses to experiential questions ("How focused do you feel right now?"). The state is saved to `<cache>/cockpit/probe-state.json`. No downstream component reads this file:
- The profiler doesn't discover it as a source
- The briefing agent doesn't include probe trends
- The accommodation system doesn't react to probe responses

The probes serve as ephemeral conversation starters in the chat system, but the collected data is not consumed.

---

## Lens 4: Operator Fit

*Does the system serve THIS operator with THEIR neurocognitive profile?*

### Core Design: Excellent

The system is designed around an explicit executive function model. The operator profile identifies cognitive patterns (task initiation difficulty, energy cycles, attention variability) and treats them as design inputs, not deficits. Key accommodations:

- **External structure:** Nudges as unified action items, goal staleness tracking, stale-1:1 alerts
- **Low cognitive overhead:** Proactive briefings, priority sorting, desktop/mobile push
- **Multiple engagement surfaces:** TUI for deep work, Obsidian for knowledge, mobile for alerts
- **Graduated attention:** Fast refresh (30s) for immediate state, slow refresh (5min) for trends

### H2-4.1: Executive function infrastructure has bugs in its most critical components [high]

The accommodation and decision tracking systems are the most operator-personal components in the entire stack. They're specifically designed to support executive function by:
- Tracking which accommodations are active when decisions are made
- Feeding decision patterns into the profiler
- Enabling the system to learn which accommodations improve outcomes

Both bugs (H2-3.1) are in this exact path. The system can propose accommodations and the operator can activate them, but the system cannot track their effectiveness because the recording mechanism is broken.

This is the highest-impact finding in the entire audit. The infrastructure for the operator's most important need (executive function support) has silent bugs introduced by the v1 fix session.

### H2-4.2: System complexity approaches the operator's attention budget [medium]

The system's operational surface:
- 12 Pydantic AI agents (+ 3 planned)
- 10 active systemd timers
- 12 Docker services
- 4 n8n workflows
- 9 specification documents
- 4 Qdrant collections
- 6 watchdog scripts
- ~14K LOC source, ~6K LOC tests

The self-regulation agents (health monitor, drift detector, scout) help manage this complexity. But when things go wrong (as they did in the v1 fix session), the operator must understand the full system to debug it. The 89-fixes-in-one-night pattern itself suggests the complexity sometimes overwhelms the attention budget.

**Mitigating factors:** The cockpit TUI provides a single-pane view. The briefing agent synthesizes across all subsystems. The health monitor auto-fixes routine issues. These reduce day-to-day cognitive load.

---

## Lens 5: Architectural Integrity

*Cross-domain contracts explicit? System evolvable? Complexity budget reasonable?*

### Architecture Quality: Strong

The three-tier design is clean and well-maintained:
- Tier 1 (Claude Code) remains the sole orchestrator
- Tier 2 agents are genuinely stateless per-invocation
- Tier 3 services are properly isolated via systemd
- The LiteLLM gateway enforces model access unity
- The context tools refactoring successfully replaced static prompt injection

### H2-5.1: No cross-domain contract tests [medium]

Components agree on data formats by convention, not by contract:
- All agents expect `operator.json` to have a specific schema, but only `OperatorSchema` validates it (and only minimally — D1 R2-1.1)
- The web API types.ts mirrors Python dataclass fields, but no test verifies the mapping
- The cache collectors assume specific shapes from agent outputs, but no integration test runs agents and verifies collector parsing
- The briefing agent consumes activity-analyzer output but doesn't validate its structure

If any agent changes its output format, downstream consumers would silently receive wrong data. The system is resilient because formats haven't changed, but this is a fragility that grows with each new component.

### H2-5.2: Fix quality degrades with batch size [medium]

The v1 fix session applied 89 fixes across 9 batches in one night. Fix verification reveals a pattern:

| Domain | Fix Success Rate | Notes |
|--------|-----------------|-------|
| D4 Health & Observability | 6/6 (100%) | Applied early |
| D8 Infrastructure | 13/16 (81%) | Architectural (generate-env.sh) |
| D5 Intelligence Agents | 10/11 (91%) | Pattern-based (error handling) |
| D1 Shared Foundation | 7/9 (78%) | Some partial |
| D7 Web Layer | 8/12 (67%) | 2 partial, 1 not fixed |
| D2 Data Ingestion | 8/12 (67%) | 2 partial, 1 not fixed |
| D3 Operator Profile | 1/4 (25%) | 2 partial, 1 not implemented |
| D6 Cockpit TUI | 7/9 (78%) | But 1 introduced bugs |

D3 (operator profile) and D6 (cockpit) had the lowest fix quality. These are also the most complex domains with the most interacting components. The decisions.py bugs were introduced in a batch that included 3 related fixes (40, 67, 81) — each individually reasonable but collectively untested.

**Implication:** Future fix sessions should limit batch size, especially for operator-critical components. The current testing infrastructure (1211 tests) is strong but didn't catch the decisions.py bugs because:
1. The `import os` bug only triggers after 500 decisions (rotation code path)
2. The `a.key` bug is caught by a bare `except` — tests would need to mock active accommodations

### H2-5.3: Drift detector scope gap [low]

The drift detector (`agents/drift_detector.py`) compares documentation against live system state (ports, services, containers). It catches claims like "Qdrant runs on port 6334" when it actually uses 6333. But it does not:
- Compare documents against each other (D9's K-9.1 consistency issues)
- Verify code claims (test counts, agent counts in docs)
- Track temporal staleness (agent-architecture.md was last materially correct months ago)

This means the drift detector would not catch the health check count disagreement (A-9.1) or the stale operations manual (P-9.1) because those are inter-document inconsistencies, not doc-vs-reality discrepancies.

---

## Cross-Domain Patterns

### Pattern 1: Silent failure accumulation

Multiple domains have the same anti-pattern: exceptions caught with `except Exception: pass` or `except: pass`, making failures invisible:
- D6: decisions.py — `a.key` AttributeError silently caught
- D3: profiler `load_existing_profile()` — corruption silently swallowed
- D4: knowledge_maint — Qdrant errors silently caught
- D1: langfuse_get() — all failures return `{}`

Each instance is individually defensible (graceful degradation). But collectively, they create a system where failures accumulate silently. The operator sees "everything working" while accommodations aren't tracked, profile loads fail, and knowledge maintenance silently skips collections.

### Pattern 2: Carry-forward findings

Several v1 findings are documented as "carry-forward" or "P3" across multiple domains. These are low-priority issues that weren't fixed in the v1 session and remain in v2:
- vault_writer non-atomic writes (D1)
- langfuse_config untested (D1)
- Gemini export parser speculative (D2)
- systemd hardening directives (D8)

These are individually low-risk but represent an accumulating backlog of known issues.

### Pattern 3: Test coverage inversely correlates with operator personalization

The most-tested components are infrastructure (health monitor, ingestion, config). The least-tested are operator-personal components (decisions, accommodations, micro-probes). The bugs found in D6 are precisely in the under-tested personal components. This makes sense — infrastructure is easier to test deterministically — but it's a gap that matters most for operator fit.

---

## Overall Assessment

### System Health: Good

The system is functional, well-architected, and serves its operator effectively in daily use. The self-regulation infrastructure (health monitor, drift detector, scout, briefing) is mature. The v1 fix session resolved the most critical issues (cascading failures, security gaps, missing functionality). Test coverage is strong (1211 tests, ~0.9 test:source ratio).

### Primary Concern: Operator-Critical Bug

The single highest-priority issue is H2-3.1/H2-4.1: the accommodation tracking flow is broken by two bugs in decisions.py. This is not a functional regression (the cockpit still works), but it severs the feedback loop that was designed to help the operator understand which accommodations improve their outcomes. Fixing these two bugs is the most impactful single action in the fix plan.

### Secondary Concern: Maintenance Velocity

The system's complexity (14K LOC, 12 agents, 10 timers) means changes have a wide blast radius. The v1 fix session demonstrated this — 89 fixes in one night, with quality degrading in later batches. Future changes should be smaller, with explicit testing of cross-component interactions (especially around operator-personal features).

---

## Summary

| Lens | Findings | Severity |
|------|----------|----------|
| H2-1 Coherence | 1 | medium |
| H2-2 Unity | 2 | medium, low |
| H2-3 Flow | 2 | high, low |
| H2-4 Operator Fit | 2 | high, medium |
| H2-5 Architectural Integrity | 3 | medium, medium, low |
| **Total** | **10** | **2 high, 5 medium, 3 low** |

The two HIGH findings both trace to the same root cause: decisions.py bugs introduced during the v1 fix session that break the accommodation effectiveness tracking flow, undermining the system's core executive function support mission.
