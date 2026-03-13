# Deliberative Governance: Federalist/Anti-Federalist Discourse for Axiom Systems

## Problem

The axiom governance system enforces constraints but does not reason about them. When a supremacy tension surfaces, the operator resolves it manually. When an implication blocks a legitimate action, the reasoning behind the block is not examined. When axiom weights are assigned, no structured process evaluates whether the weight is correct. The system constrains; it does not deliberate.

Constitutional law faced the same problem. Static legal codes cannot anticipate every case. The solution was not more rules but structured adversarial reasoning: opposing counsel, judicial review, dissenting opinions, and a precedent corpus that accumulates institutional knowledge over time. The hapax axiom system already borrows the structural elements (axioms, implications, interpretive canon, precedent store). This design adds the adversarial reasoning process.

## Theoretical grounding

The design draws from constitutional theory and cross-tradition deliberative practices research. See `deliberative-process-analysis.md` for the full feature classification with empirical evidence.

### Constitutional theory

**Incompletely theorized agreements (Sunstein).** Functional governance does not require agreement on foundational principles. Participants can agree on outcomes while disagreeing about why. Axioms are deliberately underdetermined — `executive_function` means something specific to the operator but leaves room for contextual interpretation. Full specification is not the goal. Productive ambiguity that enables coordination without forced consensus is.

**Framework originalism (Balkin).** Constitutions contain both rules (specific, determinate — T0 implications) and standards/principles (abstract, requiring construction — the axioms themselves). The interpretive canon's purposivist mode is framework originalism: interpret the axiom according to its purpose, not its literal text.

**Constitutional moments (Ackerman).** The governance system should resist axiom changes during normal operation but enable them when the operator deliberately initiates structural revision. Axiom amendments require a higher threshold of deliberation than configuration changes.

**Dissents as precedent seeds (Hughes, Varsava).** A dissent is "an appeal to the intelligence of a future day." Accumulated dissents against a particular implication signal that the implication may need revision. The formalization requirement (full reasoning, not just disagreement) is load-bearing — informal disagreement has no future generative potential.

### Deliberative practices

**Information before deliberation (Fishkin).** Participants who deliberate with a shared factual baseline produce qualitatively different outcomes than those who deliberate from prior beliefs alone. The single most robustly supported finding in deliberative democracy research.

**Disconfirmation focus (ACH, adversarial collaboration).** Requiring participants to identify what would *refute* their position, rather than what supports it, consistently improves outcomes. Confirmation bias is the single most damaging pattern in deliberation.

**Pre-commitment to update conditions (Kahneman).** Specifying in advance what evidence would change your mind prevents post-hoc rationalization. This distinguishes genuine deliberation from rationalized advocacy.

**Proportionality screening (Alexy).** When values conflict, screen for suitability and necessity before balancing. This sequential screening reduces the space of genuine dilemmas.

**Question-first structure (IBIS, Socratic method).** Deliberation begins by articulating the question, not staking positions. Prevents premature commitment and ensures participants address the same question.

## Design

### Agents

Two LLM agents with fixed rhetorical positions, invoked as a pair on governance events.

**Publius** — the federalist position. Argues for strong constitutional axioms, broad scope, high weights, textualist interpretation, comprehensive T0 coverage. Publius defends centralized governance authority.

- When evaluating a proposed implication: argues for inclusion, higher tier, broader scope
- When evaluating a supremacy tension: argues the constitutional axiom should prevail without exception
- When evaluating a dissent: argues the block was correct and the dissenting agent's reasoning is flawed
- When evaluating a weight change: argues against reduction of constitutional axiom weights

**Brutus** — the anti-federalist position. Argues for minimal constitutional scope, domain autonomy, purposivist/omitted-case interpretation, precedent-driven rather than rule-driven governance. Brutus defends implementation freedom.

- When evaluating a proposed implication: argues against inclusion, lower tier, narrower scope, or omitted-case treatment
- When evaluating a supremacy tension: argues the domain axiom addresses a legitimate local concern that the constitutional axiom does not anticipate
- When evaluating a dissent: argues the blocked action was legitimate and the implication is over-broad
- When evaluating a weight change: argues for reduction when the weight produces over-constraint

Both agents receive the same input context: the governance event, relevant axioms and implications, relevant precedents (via semantic search), the operator profile (cognitive constraints, communication preferences), and any accumulated dissents on the relevant implications.

Neither agent decides. Both produce structured arguments. The operator decides.

### Governance events that trigger deliberation

Not every governance action warrants deliberation. The following events trigger it:

| Event | Source | Why deliberation adds value |
|-------|--------|-----------------------------|
| Supremacy tension detected | `validate_supremacy()` | Domain vs. constitutional T0 overlap requires reasoned resolution, not just operator notification |
| Dissent threshold reached | Precedent store query | 3+ dissents against the same implication suggest the implication is over-broad |
| New implication proposed | Operator or agent | Should the implication exist? At what tier? With what canon? |
| Axiom weight change proposed | Operator | Weight changes ripple through all derived implications |
| Precedent supersession proposed | Operator or agent | Overruling a precedent affects all future evaluations |
| Canon challenge | Agent during compliance check | Agent argues that a different interpretive canon should apply to this situation |

Events that do not trigger deliberation: routine compliance checks (fast-path), T0 blocks with no agent reasoning attached, configuration changes within existing axiom boundaries.

### Deliberation record

Each deliberation produces a structured artifact:

```yaml
id: deliberation-2026-03-12-001
trigger:
  type: supremacy_tension
  source: validate_supremacy()
  description: "mg-safety-003 (domain T0) overlaps with su-auth-001 (constitutional T0)"
  relevant_axioms: [single_user, management_governance]
  relevant_implications: [mg-safety-003, su-auth-001]
  relevant_precedents: [prec-007, prec-012]
  accumulated_dissents: []

publius:
  position: "su-auth-001 must prevail. The constitutional axiom is absolute (weight 100). ..."
  canon_applied: textualist
  supporting_precedents: [prec-007]
  proposed_resolution: "Record precedent affirming su-auth-001 preempts mg-safety-003 in this scope."

brutus:
  position: "mg-safety-003 addresses a domain concern not anticipated by su-auth-001. ..."
  canon_applied: purposivist
  supporting_precedents: [prec-012]
  proposed_resolution: "Narrow mg-safety-003 scope to exclude the overlap region."

tension_map:
  agreement: "Both agents agree the overlap is real and not a false positive."
  disagreement: "Whether constitutional preemption is automatic or requires scope analysis."
  novel_insight: "The overlap reveals that su-auth-001's textualist reading does not
    distinguish between authentication-as-access-control and authentication-as-identity-verification.
    mg-safety-003 concerns identity verification, not access control."

status: pending_operator_review
operator_ruling: null
created: 2026-03-12T14:30:00Z
```

The `tension_map` section is the generative output. It identifies where the agents agree (narrow the problem space), where they disagree (clarify the actual decision), and what novel insight emerged from the adversarial exchange (the part the operator would not have seen without deliberation).

### Dissent recording

When axiom enforcement blocks an action and the blocked agent provides reasoning, the reasoning is recorded as a dissent in the precedent store:

```python
@dataclass
class Dissent:
    id: str
    implication_id: str          # which implication blocked the action
    axiom_id: str
    situation: str               # what was attempted
    agent_reasoning: str         # why the agent believed the action was legitimate
    enforcement_result: str      # the block/review/warn that fired
    created: str
    deliberation_id: str | None  # linked deliberation, if threshold triggered
```

Dissents accumulate. When `count(dissents for implication X) >= threshold` (default: 3), a deliberation is triggered with the dissents as input context. This is the mechanism by which enforcement decisions are revisited — not by weakening enforcement, but by surfacing patterns that suggest the rule may be wrong.

### Integration with existing machinery

**Precedent store.** Deliberation records are stored alongside precedents. A new `authority` level: `"deliberation"` (weight 0.6, between `agent` at 0.7 and `derived` at 0.5). The operator's ruling on a deliberation record becomes an `"operator"` authority precedent (weight 1.0). Deliberation records without operator rulings inform future deliberations but do not resolve compliance checks.

**Supremacy validation.** `validate_supremacy()` currently returns a list of tensions. The deliberative layer wraps this: for each tension, check if an existing deliberation record or operator precedent already resolves it. If not, trigger a new deliberation. This replaces the current behavior of surfacing raw tensions to the operator with surfacing *reasoned tensions with proposed resolutions*.

**Health monitor.** Add a check: "unresolved deliberations." If deliberation records sit in `pending_operator_review` for more than 7 days, the health monitor flags it. This prevents deliberation debt from accumulating silently.

**Briefing.** Deliberation records surface in the morning briefing as a distinct section: "Governance deliberations pending review." Each includes the trigger, the tension map summary, and a link to the full record. The operator can rule from the briefing or defer.

**VetoChain.** No change. VetoChain remains deterministic and deny-wins. Deliberation operates *around* enforcement, not *within* it. A T0 block fires immediately; the dissent is recorded after the fact; the deliberation happens asynchronously. Enforcement is never delayed by deliberation.

**Interpretive canon.** Deliberation records can propose canon changes for specific implications. If the operator rules that a different canon applies, the implication's canon field is updated. This is how the governance system evolves its interpretive methodology over time.

### What this does not do

- Does not weaken or delay enforcement. T0 blocks fire immediately. Deliberation is asynchronous.
- Does not automate operator decisions. Both agents propose; the operator rules.
- Does not require multi-user infrastructure. Both agents run under the single operator's authority.
- Does not replace the precedent store. It feeds into it.
- Does not require consensus between Publius and Brutus. Disagreement is the point.

## Data model

```python
class DeliberationTrigger(BaseModel):
    type: Literal[
        "supremacy_tension",
        "dissent_threshold",
        "new_implication",
        "weight_change",
        "precedent_supersession",
        "canon_challenge",
    ]
    source: str
    description: str
    relevant_axioms: list[str]
    relevant_implications: list[str]
    relevant_precedents: list[str]
    accumulated_dissents: list[str]

class AgentArgument(BaseModel):
    position: str                    # the argument (2-4 paragraphs)
    canon_applied: str               # textualist | purposivist | absurdity | omitted-case
    supporting_precedents: list[str]  # precedent IDs cited
    proposed_resolution: str          # what should happen
    refutation_conditions: list[str]  # what evidence would make this position wrong
    update_conditions: list[str]      # what the other agent could say to trigger concession
    values_promoted: list[str]        # governance values this position serves

class RoundOutput(BaseModel):
    round: int
    agent: str                       # publius | brutus
    responds_to: str | None          # round reference (null for round 1)
    claims_attacked: list[dict]      # claim, attack, attack_type
    update_conditions_checked: list[dict]  # condition, met (bool), reasoning
    concessions: list[str]           # conceded points (first-class)
    position_movement: str           # what changed and why
    values_promoted: list[str]

class TensionMap(BaseModel):
    agreement: str       # where both agents agree
    disagreement: str    # where they diverge
    disagreement_type: str  # factual | value_based
    novel_insight: str   # what emerged from the exchange
    failure_modes: list[str]  # from pre-mortem round

class DeliberationRecord(BaseModel):
    id: str
    question: str        # IBIS-style question framing
    trigger: DeliberationTrigger
    rounds: list[RoundOutput]        # full exchange history
    publius_final: AgentArgument     # final position after exchange
    brutus_final: AgentArgument      # final position after exchange
    tension_map: TensionMap
    status: Literal["pending_operator_review", "resolved", "deferred"]
    operator_ruling: str | None
    ruling_precedent_id: str | None  # precedent created from ruling
    dissent_id: str | None           # if minority position recorded as dissent
    created: datetime
    resolved: datetime | None

class Dissent(BaseModel):
    id: str
    implication_id: str
    axiom_id: str
    situation: str
    agent_reasoning: str
    enforcement_result: str
    created: datetime
    deliberation_id: str | None
```

## Agent implementation

Both Publius and Brutus are Pydantic AI agents with fixed system prompts that encode their rhetorical position. They produce `AgentArgument` as structured output, which now includes disconfirmation and update condition fields.

The deliberation orchestrator:
1. Receives a governance event
2. Frames the event as a question (IBIS-style question articulation, not a raw tension description)
3. Gathers context: relevant axioms, implications, precedents, dissents, operator profile
4. Provides identical context to both agents *before* either stakes a position
5. Invokes Publius and Brutus in parallel for round 1 (initial positions, responding to the question)
6. From round 2 onward: sequential alternating exchange. Each agent reads the previous round's output and must respond to specific claims, check its own pre-committed update conditions, and track concessions.
7. Continues until a termination condition is met (convergence, crux identification, round limit, concession cascade, or incompatibility)
8. Runs a collaborative pre-mortem round: both agents assume the proposed resolution was implemented and generate failure modes
9. Generates the tension map from the exchange history (agreement, disagreement, novel insight, and failure modes)
10. Records minority position as formal dissent in the precedent store if no convergence
11. Writes the deliberation record to the filesystem (`profiles/deliberations/`)

The tension map is not a third-party synthesis of static outputs. It emerges from the exchange — tracking where positions converged, where concessions occurred, and what considerations neither agent raised in round 1 but surfaced through the exchange. This is why the process exists: the generative output is the movement, not the arguments.

## Invocation

```bash
# Trigger deliberation on a specific governance event
uv run python -m agents.deliberate --trigger supremacy_tension --tension-id st-001

# Trigger deliberation on accumulated dissents
uv run python -m agents.deliberate --trigger dissent_threshold --implication-id mg-safety-003

# Review pending deliberations
uv run python -m agents.deliberate --pending

# Record operator ruling
uv run python -m agents.deliberate --rule deliberation-2026-03-12-001 \
  --decision "Narrow mg-safety-003 scope" \
  --reasoning "The overlap concerns identity verification, not access control"
```

Autonomous invocation via systemd timer is possible but not recommended initially. Deliberation should be triggered by governance events (supremacy validation, dissent accumulation) or operator request, not on a schedule.

## Prototype scope

Phase 1 (prototype):
- Publius and Brutus agents with fixed system prompts including disconfirmation and update condition obligations
- Deliberation orchestrator (question framing → context assembly → round 1 parallel → rounds 2+ sequential → pre-mortem → tension map → record)
- Multi-round exchange with concession tracking and position movement
- Deliberation record storage on filesystem (`profiles/deliberations/*.yaml`)
- Formal dissent recording in precedent store when no convergence
- CLI interface (`agents.deliberate`)
- Tests (mocked LLM, deterministic trigger/context/output)

Phase 2 (integration):
- Supremacy validation wrapper (auto-trigger deliberation on detected tensions)
- Dissent threshold monitoring (auto-trigger on accumulation)
- Briefing integration (pending deliberations section)
- Health monitor check (unresolved deliberation age)

Phase 3 (evolution):
- Deliberation history analysis (which axioms produce the most deliberation? which implications accumulate the most dissents?)
- Canon drift detection (are operator rulings consistently overriding the assigned canon for certain implications?)
- Weight pressure signals (are dissents concentrated on high-weight axioms, suggesting the weight is too high?)

## Why this is valuable

The existing governance system is a legal code. This adds a judiciary. Legal codes that lack adversarial interpretation become either brittle (every edge case requires a new rule) or stale (the rules drift from the system's actual needs). The deliberative layer produces three things the current system cannot:

1. **Reasoned tension maps** for governance decisions that currently require unstructured operator judgment
2. **Dissent accumulation** that surfaces implication over-breadth before it causes repeated false positives
3. **Canon evolution** that lets the interpretive methodology adapt based on how operator rulings diverge from assigned canons

The prototype is small (two agents, one orchestrator, one data model, filesystem storage). The integration surface is narrow (supremacy validation, precedent store, briefing, health monitor). The value is testable: run deliberation on the 6 supremacy tensions resolved earlier today and compare the tension maps against the operator's actual rulings.

## Observability

The deliberative process must be explicit, transparent, inspectable, and queryable. Every other major subsystem in the stack — LLM calls (Langfuse), infrastructure (health monitor), documents (Qdrant), voice daemon (EventLog + OTel), axiom enforcement (audit JSONL) — has structured observability. Deliberation currently has none beyond YAML file storage and a briefing mention. This section specifies the observability contract.

### Principles

**Every deliberation is a trace.** The orchestrator creates a Langfuse trace (via OTel) at deliberation start. Each LLM call within the deliberation — question framing, round 1 Publius, round 1 Brutus, round 2+, pre-mortem, tension map synthesis — is a child span. The trace carries the deliberation ID as a tag. This connects deliberation to the existing Langfuse infrastructure without new tooling.

**Every round is an addressable record.** The `RoundOutput` model is not just internal state — it is written to disk as it is produced. If a deliberation fails mid-exchange (LLM error, timeout, operator interrupt), the rounds completed so far are preserved and inspectable. Partial deliberations are valid artifacts.

**The process is the record.** The deliberation record stores the full exchange history (`rounds: list[RoundOutput]`), not just final positions. An operator reading a deliberation record sees the same thing they would see watching the exchange in real time: who said what, what they conceded, what moved, and why.

### Trace structure

```
deliberation trace (deliberation-2026-03-12-001)
├─ span: question_framing
│   metadata: {trigger_type, relevant_axioms, relevant_implications}
├─ span: context_assembly
│   metadata: {precedents_retrieved, dissents_found, context_token_count}
├─ span: round_1_publius
│   metadata: {canon_applied, refutation_conditions_count, update_conditions_count}
│   output: AgentArgument (structured)
├─ span: round_1_brutus
│   metadata: {canon_applied, refutation_conditions_count, update_conditions_count}
│   output: AgentArgument (structured)
├─ span: round_2_brutus
│   metadata: {claims_attacked_count, concessions_count, position_movement}
│   output: RoundOutput (structured)
├─ span: round_3_publius
│   metadata: {claims_attacked_count, concessions_count, position_movement}
│   output: RoundOutput (structured)
├─ span: pre_mortem
│   metadata: {failure_modes_count}
├─ span: tension_map_synthesis
│   metadata: {disagreement_type, termination_condition}
│   output: TensionMap (structured)
└─ span: record_write
    metadata: {file_path, dissent_recorded}
```

Each span carries:
- `deliberation_id` (trace-level tag, queryable in Langfuse)
- `agent` (publius | brutus | orchestrator)
- `round` (integer)
- Model, tokens, latency (auto-instrumented via existing OTel httpx hook)

### Filesystem records

Deliberation records are written to `profiles/deliberations/` as YAML. Two levels of granularity:

**Full record** (`deliberation-2026-03-12-001.yaml`): The complete `DeliberationRecord` including all rounds, final positions, tension map. This is the canonical artifact. It is self-contained — readable without access to the trace, the precedent store, or the exchange history.

**Round log** (`deliberation-2026-03-12-001.rounds.jsonl`): One JSON line per round, written as each round completes. Enables streaming observation of in-progress deliberations and preserves partial state on failure. Each line is a serialized `RoundOutput`.

The full record is written atomically after the deliberation completes. The round log is append-only during execution.

### Queryable storage

Deliberation records are indexed for two query patterns:

**Structured queries** (JSONL index): `profiles/deliberations/index.jsonl` contains one line per deliberation with extracted fields:

```json
{
  "id": "deliberation-2026-03-12-001",
  "created": "2026-03-12T14:30:00Z",
  "trigger_type": "supremacy_tension",
  "axioms": ["single_user", "management_governance"],
  "implications": ["mg-boundary-001", "ex-err-001"],
  "status": "pending_operator_review",
  "termination": "crux_identification",
  "rounds": 4,
  "concessions_total": 2,
  "disagreement_type": "factual",
  "canons": ["textualist", "purposivist"],
  "operator_ruling_canon": null,
  "novel_insight_summary": "mg-boundary-001 does not specify ...",
  "trace_id": "abc123..."
}
```

This index supports the Phase 3 evolution queries without requiring YAML parsing:
- "Which axioms produce the most deliberation?" → filter by `axioms`, count
- "Which implications accumulate the most dissents?" → cross-reference with dissent store
- "What canons do operator rulings favor?" → filter by `operator_ruling_canon`
- "Are deliberations converging or hitting round limits?" → aggregate `termination` field
- "How many concessions per deliberation on average?" → aggregate `concessions_total`

**Semantic queries** (Qdrant): The tension map's `novel_insight` field is embedded and stored in the `documents` collection with metadata `{source_service: "deliberation", content_type: "novel_insight", deliberation_id: "..."}`. This enables semantic search over deliberation insights — "find deliberations where the novel insight relates to authentication scoping" — using the existing `search_documents()` infrastructure.

### Cockpit API endpoints

```
GET  /api/data/deliberations              # list all, filterable by status/axiom/trigger_type
GET  /api/data/deliberations/:id          # full record
GET  /api/data/deliberations/:id/rounds   # round-by-round exchange
GET  /api/data/deliberations/:id/trace    # Langfuse trace link
GET  /api/data/deliberations/stats        # aggregate statistics (for Phase 3 queries)
POST /api/data/deliberations/:id/rule     # record operator ruling (writes precedent)
```

The SPA can render a deliberation as a threaded exchange: round 1 positions side by side, then alternating rounds with concessions highlighted, then the tension map, then the pre-mortem failure modes. The operator rules from this view.

### Health monitor integration

Three checks, all in the `governance` check group:

**check_deliberation_staleness** (tier 2): Any deliberation in `pending_operator_review` for >7 days is DEGRADED. >14 days is FAILED. Remediation: `uv run python -m agents.deliberate --pending`.

**check_deliberation_process_health** (tier 3): Computed from the index. If >50% of deliberations in the last 30 days terminated via `round_limit` (rather than convergence or crux identification), the process is not narrowing effectively. DEGRADED. Remediation: review agent prompts for disconfirmation and update condition quality.

**check_dissent_accumulation** (tier 2): Any implication with ≥3 unresolved dissents that has not triggered a deliberation is FAILED — the trigger mechanism is broken. Remediation: `uv run python -m agents.deliberate --trigger dissent_threshold --implication-id <id>`.

### Briefing integration

The briefing consumes deliberation state at two levels:

**Pending deliberations**: Count, age, and one-line summary of each pending deliberation. High priority if any are >7 days old.

**Process health**: If `check_deliberation_process_health` is DEGRADED, the briefing surfaces it as an action item: "Deliberation process is not converging — N of M recent deliberations hit the round limit."

**Resolved deliberations**: When an operator rules on a deliberation, the next briefing confirms the ruling and the precedent created.

### Self-inspection

The deliberative system inspects its own behavior through three mechanisms, consistent with the existing self-inspection patterns (drift detection, sufficiency probes, emergence detection).

**Convergence rate tracking.** The index supports computing: what fraction of deliberations converge vs. hit round limits vs. identify cruxes vs. surface incompatibilities? A system where most deliberations hit the round limit is not deliberating effectively — it is producing parallel position statements with extra steps. This is the process-level equivalent of drift detection: comparing the process's actual behavior to its intended behavior.

**Agent bias detection.** If operator rulings consistently favor one agent (>70% Publius or >70% Brutus over a rolling 20-deliberation window), the agent prompts may be miscalibrated. One agent may be systematically stronger or weaker than intended. This is analogous to sufficiency probes — checking that the system actively supports its own design intent, not just avoids violating it.

**Canon drift detection.** If operator rulings consistently apply a different canon than the deliberating agents proposed (e.g., operators rule purposivist when both agents argued textualist), the assigned canon for those implications may be wrong. Track `(implication_id, canon_in_implication_yaml, canon_in_operator_ruling)` tuples. Persistent divergence signals that the implication's canon field needs updating. This is the governance equivalent of the drift detector — comparing declared interpretive methodology to actual interpretive practice.

**Update condition quality.** If agents rarely check their pre-committed update conditions as met (low concession rate despite multi-round exchange), the update conditions may be too narrow or too abstract to be actionable. Track `update_conditions_checked.met == true` rate. Persistent low rates signal that the disconfirmation mechanism is theatrical rather than functional — the agents commit to update conditions they never actually meet. This is the deliberation-specific anti-pattern detector.

## Evaluation standard

The deliberative process must be evaluated against criteria that determine whether it produces governance value or is performing deliberation theater. Three evaluation dimensions, each with computable metrics and diagnostic thresholds.

### Dimension 1: Process fidelity

Is the process structurally doing what the design specifies? These metrics detect whether the load-bearing features identified in the process analysis are functioning or theatrical.

**Metric 1.1: Update condition activation rate**

```
activation_rate = count(update_conditions_checked where met == true) / count(update_conditions_checked)
```

This is the single most diagnostic metric. Pre-committed update conditions are the structural feature that distinguishes genuine deliberation from rationalized advocacy (Kahneman's adversarial collaboration). If agents commit to conditions but never find them met, the conditions are too narrow, too abstract, or the agents are not genuinely checking.

| Rate | Interpretation | Action |
|------|---------------|--------|
| 0% | Theatrical. Conditions exist but never trigger. | Review condition specificity in agent prompts. Conditions must be concrete and testable against the other agent's actual claims. |
| 1-15% | Low but functional. Some genuine checking. | Acceptable for early iterations. Monitor trend. |
| 15-40% | Healthy. Conditions are specific enough to be triggered by real arguments. | Target range. |
| >40% | Conditions may be too permissive, or agents are conceding too readily. | Review whether concessions are substantive or reflexive. |

**Metric 1.2: Responsive reference rate**

```
reference_rate = count(rounds where claims_attacked reference specific text from prior round) / count(rounds after round 1)
```

Sequential responsive exchange is load-bearing. If round 2+ outputs do not reference specific claims from the prior round, the exchange is parallel argumentation with extra steps.

| Rate | Interpretation |
|------|---------------|
| <50% | Agents are arguing past each other. System prompt needs strengthening on specificity obligation. |
| 50-80% | Partial engagement. Some rounds are responsive, others restate. |
| >80% | Healthy. Agents are engaging with each other's specific claims. |

**Metric 1.3: Concession specificity**

Qualitative check (sampled, not computed over all deliberations): are concessions specific governance artifacts ("su-auth-001's text is broader than its purpose") or vague acknowledgments ("Brutus raises a valid point")? Vague concessions do not contract the problem space. This metric requires periodic operator review of a sample of concession fields.

### Dimension 2: Generative output

Is the process producing insight that would not exist without the exchange? This is the fundamental justification for the process — if static parallel analysis produces equivalent output, the multi-round exchange is wasted computation.

**Metric 2.1: Novel insight distinctiveness**

The tension map's `novel_insight` field should contain considerations that are not present in either agent's round 1 output. This is testable:

```
distinctiveness = 1 - max(
    semantic_similarity(novel_insight, publius_r1.position),
    semantic_similarity(novel_insight, brutus_r1.position)
)
```

Using the existing embedding infrastructure (nomic-embed-text via Ollama, Qdrant cosine similarity).

| Score | Interpretation |
|-------|---------------|
| <0.2 | Novel insight is a restatement of round 1 positions. Process did not generate new insight. |
| 0.2-0.5 | Partially novel. Some new considerations, but heavily derived from initial positions. |
| >0.5 | Genuinely novel. The exchange produced considerations neither agent raised initially. |

**Metric 2.2: Problem space contraction**

Does the deliberation narrow the decision the operator must make? Measured by comparing the scope of round 1 positions to the scope of the final tension map:

- **Convergence**: Both agents agree on a resolution. Maximum contraction — the operator confirms or overrides, but the decision space is a single point.
- **Crux identification**: Disagreement narrowed to one specific question. The operator decides that question, not the full tension.
- **Round limit with narrowing**: Positions moved but did not converge. Partial contraction — the operator's decision is smaller than the original tension.
- **Round limit without narrowing**: Positions did not move. Zero contraction. The process failed.

```
contraction_rate = count(deliberations terminating in convergence or crux) / count(deliberations)
```

| Rate | Interpretation |
|------|---------------|
| <30% | Process is not narrowing. Agents are restating rather than engaging. |
| 30-60% | Moderate. Some deliberations produce value; others do not. |
| >60% | Healthy. Most deliberations produce a narrower decision for the operator. |

**Metric 2.3: Failure mode novelty (pre-mortem)**

The pre-mortem step should identify failure modes not anticipated by either agent's round 1 analysis. Computed similarly to novel insight distinctiveness but against both agents' refutation conditions:

```
premortem_novelty = fraction of failure_modes with low similarity to any refutation_condition in round 1
```

If the pre-mortem only restates refutation conditions, it adds no value.

### Dimension 3: Governance impact

Does the process improve governance decisions over time? These metrics require accumulated deliberation history and operator rulings.

**Metric 3.1: Precedent durability**

```
durability = 1 - (count(deliberation-created precedents later superseded) / count(deliberation-created precedents))
```

Precedents created from deliberation + operator ruling should be more durable than precedents created without deliberation. If deliberation-sourced precedents are superseded at the same or higher rate as non-deliberation precedents, the process is not improving governance quality.

Requires: ≥20 resolved deliberations with operator rulings to compute meaningfully.

**Metric 3.2: Dissent prediction accuracy**

When a deliberation identifies a potential future problem (via novel insight, failure modes, or minority position), does that problem materialize?

```
prediction_accuracy = count(deliberation-predicted issues that later appeared as dissents or new tensions) / count(deliberation predictions)
```

This requires retroactive correlation: when a new dissent or tension appears, check whether any prior deliberation's novel insight or failure modes anticipated it. Implemented as a semantic search over the deliberation `novel_insight` and `failure_modes` fields in Qdrant.

High prediction accuracy validates that the process surfaces real future concerns. Low accuracy (with sufficient sample size) suggests the process generates speculative rather than grounded analysis.

**Metric 3.3: Implication revision rate**

```
revision_rate = count(implications revised following deliberation) / count(deliberations identifying implication ambiguity)
```

Deliberations that identify ambiguity in implication text (e.g., "su-auth-001 does not distinguish user-to-system from system-to-service auth") should lead to implication revisions. If identified ambiguities persist without revision, the deliberation → governance improvement feedback loop is broken.

This measures transmission (Dryzek): whether deliberation outputs actually influence the governance artifacts they analyze.

**Metric 3.4: Operator engagement**

```
review_latency = median(days from deliberation creation to operator ruling)
abandonment_rate = count(deliberations never ruled on) / count(deliberations)
```

If the operator does not engage with deliberation outputs, the process has no governance impact regardless of output quality. High review latency or abandonment signals either: (a) deliberation outputs are not useful enough to warrant review, (b) the surfacing mechanism (briefing, cockpit) is insufficient, or (c) deliberation volume exceeds operator capacity.

| Review latency | Interpretation |
|---------------|---------------|
| <3 days | Healthy. Operator is engaging with deliberation output. |
| 3-7 days | Acceptable. May indicate prioritization, not disengagement. |
| >7 days | Deliberation debt accumulating. Health monitor flags this. |
| >14 days | Process is not producing outputs the operator values enough to review. |

### Composite evaluation

No single metric is sufficient. The evaluation standard uses a composite assessment:

**Process is healthy when:**
- Update condition activation rate is 10-40%
- Responsive reference rate is >70%
- Contraction rate is >50%
- Novel insight distinctiveness is >0.3 (mean)
- Operator review latency is <7 days (median)
- Precedent durability is >80% (when sample size ≥20)

**Process is degraded when:**
- Any two process fidelity metrics fall below threshold
- Contraction rate drops below 30%
- Operator abandonment rate exceeds 25%

**Process is failing when:**
- Update condition activation rate is 0% (theatrical)
- Contraction rate is below 15% (parallel position statements with extra steps)
- Operator abandonment rate exceeds 50% (no governance impact)

### Evaluation cadence

**Per-deliberation** (automated, immediate): Update condition activation, responsive reference, concession count, termination condition. Written to the JSONL index.

**Rolling window** (automated, computed on query): Contraction rate, agent bias, canon drift, convergence trend. Computed from the index over the most recent 20 deliberations.

**Periodic review** (operator, quarterly or at 20-deliberation milestone): Concession specificity (sampled), novel insight quality (sampled), precedent durability, implication revision rate. The operator reviews a sample of deliberation outputs and assesses whether the process is producing governance value.

**Triggered** (automated): When rolling-window metrics cross degraded or failing thresholds, the health monitor flags it and the briefing surfaces it as a high-priority action item. The operator decides whether to adjust agent prompts, modify the process, or accept the current performance.

### What the evaluation standard does not do

- Does not evaluate whether operator rulings are correct. The operator's judgment is sovereign. The standard evaluates whether the process provides the operator with useful input, not whether the operator uses it well.
- Does not optimize for convergence. Incompatibility is a valid termination condition. A high incompatibility rate may indicate genuinely irreconcilable axiom tensions, not process failure.
- Does not penalize disagreement. The standard penalizes *unproductive* disagreement (round limit without narrowing) but not disagreement itself. Persistent disagreement that identifies a crux is a successful outcome.
- Does not require a minimum deliberation volume. The standard applies to whatever volume the governance system produces. Metrics that require sample size (precedent durability, dissent prediction) are flagged as not-yet-computable until the threshold is met.

### What observability does not do

- Does not add latency to enforcement. Tracing is fire-and-forget (OTel BatchSpanProcessor). Enforcement remains synchronous and unblocked.
- Does not require new infrastructure. Uses existing Langfuse (traces), Qdrant (semantic index), health monitor (checks), briefing (consumption), cockpit API (exposure).
- Does not observe operator reasoning. The operator's ruling is recorded, but the operator's internal reasoning process is not traced. The system observes its own deliberation, not the operator's decision-making.

## References

- `deliberative-process-analysis.md` — Feature classification with cross-tradition evidence (necessary vs incidental vs not valuable)
- `distro-work/research/deliberative-practices-structural-analysis.md` — Full source research across 8 deliberative traditions
