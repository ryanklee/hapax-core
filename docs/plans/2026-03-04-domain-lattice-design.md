# Domain Lattice Engine — Design Document

**Date:** 2026-03-04
**Status:** Approved
**Author:** Claude Code + Operator

**Goal:** Generalize the management-specific Knowledge Sufficiency Engine into a life-domain-aware system that detects, tracks, and proactively acquires knowledge across all operator domains — applying the executive function axiom reflexively to the system's own knowledge management.

---

## 1. Core Principle

The system maintains a model of its own knowledge about the operator's life, evaluates sufficiency per domain, detects emerging domains from activity patterns, and proactively acquires missing information. The executive function axiom (ex-init-001 through ex-alert-004) applies reflexively: the system compensates for cognitive load in managing its own knowledge, not just the operator's tasks.

The system does not decide what matters. It observes, surfaces, and proposes. The operator confirms. This mirrors the management governance axiom's "LLM prepares, human delivers" — extended to all domains.

---

## 2. Domain Registry

**File:** `hapaxromana/domains/registry.yaml`

A declarative registry of all life domains the system is aware of. Parallels the axiom registry pattern (versioned YAML, constitutional layer).

### Schema

```yaml
version: 1
updated: 2026-03-04

# Constitutional layer — constrains all domains
constitutional:
  - id: values-ethics
    description: "Higher principles, ethical constraints, personal values"
    axiom_ids: [single_user, executive_function]
    supremacy: true  # overrides domain-level decisions

domains:
  - id: management
    name: "Management & Leadership"
    status: active  # proposed | active | dormant | retired
    sufficiency_model: knowledge/management-sufficiency.yaml
    vault_paths:
      - "10-work/people"
      - "10-work/meetings"
      - "10-work/projects"
      - "10-work/decisions"
      - "10-work/references"
    profiler_dimensions:
      - management_practice
      - team_leadership
    relationships:
      - target: technical
        type: supports        # supports | competes-with | constrained-by
        description: "Technical depth informs management decisions"
      - target: personal
        type: constrained-by
        description: "Work-life boundary constraints"
    governance:
      axiom_ids: [management_governance, corporate_boundary]
      heuristics:
        - "LLM prepares, human delivers"
        - "Never generate feedback language"
        - "Signal aggregation, not recommendation"
    person_extensions:
      fields:
        - { name: mgmt-role, type: string }
        - { name: mgmt-team, type: string }
        - { name: mgmt-cadence, type: string }
        - { name: cognitive-load, type: number, range: [1, 5] }
        - { name: skill-level, type: string, options: [developing, career, advanced, expert] }
        - { name: will-signal, type: string, options: [high, moderate, low] }
        - { name: coaching-active, type: boolean }
        - { name: feedback-style, type: string }
        - { name: growth-vector, type: string }
        - { name: career-goal-3y, type: string }
        - { name: current-gaps, type: string }
        - { name: current-focus, type: string }
        - { name: last-career-convo, type: date }
        - { name: team-type, type: string }
        - { name: interaction-mode, type: string }
      staleness_days: 14

  - id: music
    name: "Music Production"
    status: active
    sufficiency_model: knowledge/music-sufficiency.yaml
    vault_paths:
      - "20-personal/music"
    profiler_dimensions:
      - music_production
      - technical_preferences
    relationships:
      - target: technical
        type: supports
        description: "MIDI/audio programming supports production"
    governance:
      axiom_ids: []
      heuristics:
        - "Creative autonomy — suggest techniques, never aesthetic judgments"
        - "Hardware-first — DAWless workflow is intentional"
    person_extensions:
      fields:
        - { name: music-role, type: string }
        - { name: music-instrument, type: string }
        - { name: music-genre, type: string }
      staleness_days: 30

  - id: personal
    name: "Personal & Family"
    status: active
    sufficiency_model: knowledge/personal-sufficiency.yaml
    vault_paths:
      - "20-personal"
    profiler_dimensions:
      - personal_interests
      - health_fitness
    relationships:
      - target: management
        type: constrained-by
        description: "Work-life boundary"
    governance:
      axiom_ids: []
      heuristics:
        - "Maximum privacy — minimal data collection"
        - "Never optimize relationships"
        - "Record only what operator explicitly shares"
    person_extensions:
      fields:
        - { name: personal-context, type: string }
        - { name: personal-cadence, type: string }
      staleness_days: 60

  - id: technical
    name: "Technical Infrastructure"
    status: active
    sufficiency_model: knowledge/technical-sufficiency.yaml
    vault_paths:
      - "30-system"
    profiler_dimensions:
      - technical_preferences
      - development_patterns
    relationships:
      - target: management
        type: supports
      - target: music
        type: supports
    governance:
      axiom_ids: [single_user]
      heuristics:
        - "Infrastructure serves domains, not the reverse"
        - "Minimize operational burden (executive function)"
    person_extensions:
      fields: []  # no person extensions for technical domain
      staleness_days: null
```

### Key Properties

- **Constitutional layer**: `values-ethics` entry with `supremacy: true` constrains all domain-level decisions. Mirrors the axiom supremacy clause.
- **Status lifecycle**: `proposed` (from emergence) -> `active` (operator confirmed) -> `dormant` (60+ days no activity) -> `retired` (operator archived). Status transitions generate nudges.
- **Relationships**: Typed edges between domains. Three types: `supports` (positive synergy), `competes-with` (time/attention tension), `constrained-by` (one domain's rules limit another).
- **Governance**: Per-domain axiom references and freeform heuristics. Agents operating in a domain must respect these.
- **Person extensions**: Domain-specific fields added to the universal person model. Each domain declares its own staleness threshold.

---

## 3. Momentum & Trajectory Model

Three continuous signals per domain, computed from existing telemetry. Zero LLM calls.

### Signals

**Activity Rate** — 7-day rolling average of domain-attributed events, divided by 30-day baseline average. Produces a ratio:
- `> 1.2` = accelerating
- `0.8 - 1.2` = steady
- `< 0.8` = decelerating
- `< 0.1` = dormant

**Engagement Regularity** — Coefficient of variation (std_dev / mean) of inter-event time gaps over 30 days:
- `< 0.5` = regular (habitual engagement)
- `0.5 - 1.0` = irregular (bursty)
- `> 1.0` = sporadic

**Goal Alignment** — Slope of sufficiency score over last 4 weekly snapshots:
- Positive slope = improving
- Flat = plateaued
- Negative = regressing (data going stale, requirements becoming unsatisfied)

### Momentum Vector

Combines into a per-domain summary:

```python
@dataclass
class MomentumVector:
    domain_id: str
    direction: str      # accelerating | steady | decelerating | dormant
    regularity: str     # regular | irregular | sporadic
    alignment: str      # improving | plateaued | regressing
    activity_rate: float
    regularity_cv: float
    alignment_slope: float
    computed_at: str    # ISO timestamp
```

### Activity Sources

Events attributed to domains via the registry's `vault_paths`, `profiler_dimensions`, and agent-domain mappings:
- Vault file modifications (folder path -> domain)
- Langfuse traces (agent name -> domain via mapping table)
- Profiler fact creation (dimension -> domain)
- RAG ingestion events (content_type -> domain)

### Implementation

New file: `cockpit/data/momentum.py`. Refresh: 5-minute slow cycle. Persists weekly snapshots to `<cache>/cockpit/momentum-history.jsonl` for trend computation.

---

## 4. Emergence Detection

Three-stage pipeline detecting potential new domains from activity that doesn't map to any declared domain.

### Stage 1: Undomained Activity Collection

Every activity source tags events with domain when possible. Activity that doesn't map to any declared domain's `vault_paths`, `profiler_dimensions`, or agent associations goes into an "undomained" buffer.

Sources:
- Profiler facts (13 dimensions — each fact has implicit domain affinity)
- Vault file creation/modification (folder paths map to domains via registry)
- RAG ingestion events (content_type, source_service from Qdrant payload)
- Langfuse traces (agent invocations imply domain)

Anti-noise: Ignores system-generated activity (briefings, health checks, automated ingestion). Only counts operator-initiated or operator-relevant events.

### Stage 2: Clustering

Weekly batch (piggybacking on the existing knowledge-maint timer window, Sunday 04:30). Groups undomained activity by:
- Co-occurring tags/keywords (TF-IDF over activity descriptions, no embeddings needed)
- Temporal proximity (events within same 48h window get affinity boost)
- Person overlap (same people appearing across undomained events)

A cluster becomes a **domain candidate** when it hits threshold: 5+ distinct events across 2+ weeks with 3+ distinct keywords. Conservative threshold avoids proposing domains from a single burst of activity.

### Stage 3: Proposal

When a candidate crosses threshold, the system generates a domain proposal nudge:

```
Category: emergence
Priority: 55 (medium)
Title: "Potential new domain detected: [cluster label]"
Detail: "[N] activities over [M] weeks involving [keywords].
         Related people: [names]. Overlaps with: [existing domains]."
Action: "/domain propose [candidate-id]"
```

The `/domain propose` command (cockpit chat) triggers one LLM call to draft a registry entry: name, suggested vault paths, potential profiler dimensions, relationship to existing domains. Operator reviews and accepts/rejects/modifies.

### Dormancy Detection

Emergence also detects when activity in a declared domain drops to near-zero for 60+ days. Generates a "domain dormancy" nudge suggesting status change to `dormant`. Similarly detects when a `dormant` domain reactivates.

### Implementation

New file: `cockpit/data/emergence.py`. Buffer persisted to `<cache>/cockpit/undomained-activity.jsonl`. Candidates persisted to `<cache>/cockpit/emergence-candidates.json`.

---

## 5. Adaptive Sufficiency

Sufficiency thresholds respond to actual downstream agent utilization rather than remaining static.

### Utilization Tracking

Per-requirement tracking added to sufficiency YAML:

```yaml
requirements:
  - id: direct-reports
    # ... existing fields ...
    utilization:
      last_consumed_by: ["management_prep", "meeting_lifecycle"]
      last_consumed_at: "2026-03-03"
      consumption_count_30d: 12
```

The audit engine records when downstream agents actually read a satisfied requirement's data.

### Priority Adjustment

Base priority (declared in YAML) gets a multiplier from utilization:
- Never consumed in 60 days: priority decays by 50%
- Consumed daily: priority boosted by 25%
- Bounds: never below 10, never above category ceiling (foundational=100, structural=80, enrichment=60)

### Cross-Domain Calibration

The system tracks sufficiency scores per domain. If management is at 85% and music is at 20%, the nudge system naturally weights music gaps higher — not because music is more important, but because the delta is larger. The operator sees this in the dashboard and can override with explicit domain priority weights in the registry.

### Agent-Declared Dependencies

When a new agent is added that needs data the sufficiency model doesn't track, the agent declares its data dependencies in a `requires` field. The sufficiency engine detects unmodeled dependencies and proposes new requirements. Zero manual YAML editing for common cases.

---

## 6. Universal Person Model

One person, one note, with domain-specific extensions.

### Core Fields (every person)

```yaml
type: person
name: "Alice Smith"
status: active          # active | inactive | departed
domains: [management, personal]
relationship: direct-report
first-met: 2024-06-15
last-interaction: 2026-03-01
interaction-momentum: regular    # computed: regular | fading | dormant | new
```

### Domain Extensions

Declared in the domain registry's `person_extensions`. Management domain adds `mgmt-role`, `mgmt-team`, `cognitive-load`, etc. Music domain adds `music-role`, `music-instrument`. Personal domain adds `personal-context`, `personal-cadence`.

### Key Behaviors

- Person notes stay in `10-work/people/` — the folder is domain-neutral despite the name. No migration needed.
- `domains` array is the index. Agents filter by `domains contains <domain-id>`.
- `interaction-momentum` is computed from `last-interaction` using the momentum model's regularity signal, scoped to the person. Replaces the binary "stale 1:1" check with a continuous signal.
- Cross-domain people (e.g., coworker who's also a music collaborator) appear once with both domain extensions. The sufficiency engine checks each domain's person extension fields independently.
- Template (`tpl-person.md`) gets a `domains` multi-select and conditional extension blocks.

### Per-Domain Staleness

A person can be current in management (weekly 1:1s) but fading in music (haven't jammed in months). Each domain's `person_extensions` in the registry declares its own `staleness_days` threshold. The nudge system generates per-domain staleness nudges.

---

## 7. Generalized Sufficiency Engine

Unifies the pattern across domains without duplicating code.

### One YAML Model Per Domain

Stored at `hapaxromana/knowledge/{domain-id}-sufficiency.yaml`. The existing `management-sufficiency.yaml` is the first instance. All follow the same schema — the 6 check types (`file_exists`, `min_count`, `field_populated`, `field_coverage`, `any_content`, `derived`) are domain-agnostic already.

### Multi-Domain Python Audit

`knowledge_sufficiency.py` gains a multi-domain entry point:

```python
def collect_all_domain_gaps(vault_path: Path) -> dict[str, SufficiencyReport]:
    """Load every domain's sufficiency model and run audit."""
    registry = load_domain_registry()
    reports = {}
    for domain in registry["domains"]:
        model_path = KNOWLEDGE_DIR / f"{domain['id']}-sufficiency.yaml"
        if model_path.is_file():
            model = load_knowledge_model(model_path)
            reports[domain["id"]] = run_audit(model, vault_path=vault_path)
    return reports
```

Existing `run_audit()` and all check functions are unchanged — they already operate on a generic model dict.

### Nudge Generation

`gaps_to_nudges()` gets a `domain_id` parameter prepended to `source_id` (e.g., `knowledge:management:direct-reports`). Nudge priority incorporates the adaptive utilization multiplier.

### TypeScript Interview Engine

`obsidian-hapax/src/interview/engine.ts` gets a `domainId` property. The `/setup` command accepts an optional domain: `/setup management`, `/setup music`. Defaults to the domain with the lowest sufficiency score.

### Cross-Domain Sufficiency Score

Single aggregate score weighted by domain activity (from momentum model). A dormant domain's low sufficiency doesn't drag down the overall score. An active domain's gaps weigh heavily.

### No New Dependencies

The generalization is structural (loop over domains, parameterize by domain ID). All check functions, extraction logic, and vault writing remain identical.

---

## 8. Cockpit Domain Health Dashboard

### Widget: `cockpit/widgets/domain_health.py`

Vertical panel showing each active domain:

```
+-- Domain Health -----------------+
| management  ||||||||..  82%  ^   |
| music       |||.......  31%  ->  |
| personal    |.........  12%  v   |
| technical   ||||||....  58%  ^   |
|                                  |
| ! Emergence: "woodworking" (7    |
|   events / 3 weeks)             |
|                                  |
| Overall: 46%  Momentum: mixed    |
+----------------------------------+
```

Each row: domain name, sufficiency bar, percentage, momentum arrow (`^` accelerating, `->` steady, `v` decelerating, `o` dormant).

Emergence candidates appear below domain list when any exist.

### Data Collector: `cockpit/data/domain_health.py`

Aggregates from three sources:
1. `collect_all_domain_gaps()` -> per-domain sufficiency scores
2. `momentum.py` -> per-domain momentum vectors
3. `emergence.py` -> active candidates

Refresh: 5-minute slow cycle.

### Drill-Down

Enter on a domain row opens DetailScreen modal:
- Individual requirement status (satisfied/unsatisfied, with utilization counts)
- Domain relationships and their health
- Person coverage for that domain
- Staleness alerts
- Suggested next action (highest-priority unsatisfied requirement)

### Chat Commands

`/domain` command family in cockpit chat:
- `/domain list` — summary of all domains with scores
- `/domain <id>` — detailed view of one domain
- `/domain propose <candidate-id>` — draft registry entry from emergence candidate
- `/domain add <id>` — activate a proposed domain (creates YAML stub)

---

## Implementation Phasing

Five phases, each independently deployable:

### Phase 1: Domain Registry + Multi-Domain Audit (hapaxromana + ai-agents)
- Create `domains/registry.yaml` with 4 initial domains
- Generalize `knowledge_sufficiency.py` to loop over domains
- Create stub sufficiency YAMLs for music, personal, technical (5-8 requirements each)
- Update nudge generation with domain-scoped source IDs

### Phase 2: Momentum Model (ai-agents)
- New `cockpit/data/momentum.py` collector
- Activity rate from Langfuse traces + vault modification timestamps
- Engagement regularity from inter-event gaps
- Goal alignment from sufficiency score trend (requires Phase 1)

### Phase 3: Universal Person Model (hapaxromana + vault)
- Add `domains`, `interaction-momentum`, core fields to person schema
- Update `tpl-person.md` template with domain-conditional extensions
- Update `management.py` PersonState to read from new field locations
- No migration of existing notes — new fields are additive

### Phase 4: Emergence Detection (ai-agents)
- New `cockpit/data/emergence.py`
- Undomained activity collection from existing telemetry
- Weekly clustering via knowledge-maint timer
- Proposal nudge generation

### Phase 5: Cockpit Dashboard + Adaptive Sufficiency (ai-agents)
- `cockpit/widgets/domain_health.py` widget
- `cockpit/data/domain_health.py` aggregator
- Utilization tracking in audit engine
- Priority decay/boost logic
- `/domain` chat commands

Each phase has a clear deliverable and can be verified independently. Phase 1 is the foundation.

---

## Repos Affected

| Repo | Changes |
|------|---------|
| `<hapaxromana>/` | Domain registry YAML, sufficiency model YAMLs, person schema docs |
| `<ai-agents>/` | Multi-domain audit, momentum, emergence, dashboard, /domain commands |
| `<obsidian-hapax>/` | Multi-domain interview engine, /setup domain selection |
| `<personal-vault>/` | tpl-person.md template update, new vault directories if needed |

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Emergent + operator-confirmed domains | System observes, never decides what matters |
| Layered sovereignty | Constitutional axioms constrain domain governance |
| Momentum + trajectory (not binary stale/fresh) | Continuous signals reveal trends, not just snapshots |
| Universal person model | One note per person, domain extensions prevent duplication |
| Adaptive sufficiency | Priorities respond to actual agent utilization |
| Cockpit dashboard visibility | Operator sees domain health at a glance |
| Zero LLM for detection/tracking | LLM only for emergence proposal narrative |
