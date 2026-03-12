# Deliberative Governance: Federalist/Anti-Federalist Discourse for Axiom Systems

## Problem

The axiom governance system enforces constraints but does not reason about them. When a supremacy tension surfaces, the operator resolves it manually. When an implication blocks a legitimate action, the reasoning behind the block is not examined. When axiom weights are assigned, no structured process evaluates whether the weight is correct. The system constrains; it does not deliberate.

Constitutional law faced the same problem. Static legal codes cannot anticipate every case. The solution was not more rules but structured adversarial reasoning: opposing counsel, judicial review, dissenting opinions, and a precedent corpus that accumulates institutional knowledge over time. The hapax axiom system already borrows the structural elements (axioms, implications, interpretive canon, precedent store). This design adds the adversarial reasoning process.

## Theoretical grounding

Five mechanisms from constitutional theory inform this design.

**Pseudonymous composite agents (Federalist Papers).** Hamilton, Madison, and Jay wrote as "Publius" — a composite rhetorical agent with a coherent position distinct from any individual author. The pseudonym forced internal reconciliation before publication and depersonalized argument, requiring evaluation of reasoning rather than reputation. The Anti-Federalists ("Brutus," "Federal Farmer," "Centinel") were uncoordinated, which let them attack from any angle. This asymmetry was productive: the Federalists built comprehensive positive cases; the Anti-Federalists identified failure modes the Federalists missed. The Bill of Rights exists because of this asymmetry.

**Incompletely theorized agreements (Sunstein).** Functional governance does not require agreement on foundational principles. Participants can agree on outcomes while disagreeing about why. Axioms are deliberately underdetermined — `executive_function` means something specific to the operator but leaves room for contextual interpretation. Full specification is not the goal. Productive ambiguity that enables coordination without forced consensus is.

**Framework originalism (Balkin).** Constitutions contain both rules (specific, determinate — T0 implications) and standards/principles (abstract, requiring construction — the axioms themselves). Trying to enumerate every violation in advance produces a brittle system. The interpretive canon's purposivist mode is framework originalism: interpret the axiom according to its purpose, not its literal text.

**Constitutional moments (Ackerman).** Democratic life operates on two tracks: normal politics (incremental, representative) and constitutional moments (rare structural revision by an engaged citizenry). The governance system should resist axiom changes during normal operation but enable them when the operator deliberately initiates structural revision. Axiom amendments require a higher threshold of deliberation than configuration changes.

**Dissents as precedent seeds (Hughes, Varsava).** A dissent is "an appeal to the intelligence of a future day." When the governance layer blocks an action and the agent's reasoning explains why the action should have been permitted, that blocked-action-plus-reasoning is a dissent. Accumulated dissents against a particular implication signal that the implication may need revision. The precedent store records these; the deliberative layer surfaces them.

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

class TensionMap(BaseModel):
    agreement: str       # where both agents agree
    disagreement: str    # where they diverge
    novel_insight: str   # what emerged from the exchange

class DeliberationRecord(BaseModel):
    id: str
    trigger: DeliberationTrigger
    publius: AgentArgument
    brutus: AgentArgument
    tension_map: TensionMap
    status: Literal["pending_operator_review", "resolved", "deferred"]
    operator_ruling: str | None
    ruling_precedent_id: str | None  # precedent created from ruling
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

Both Publius and Brutus are Pydantic AI agents with fixed system prompts that encode their rhetorical position. They receive identical input context and produce `AgentArgument` as structured output.

The deliberation orchestrator:
1. Receives a governance event
2. Gathers context: relevant axioms, implications, precedents, dissents, operator profile
3. Invokes Publius and Brutus in parallel (independent, no cross-talk)
4. Generates the tension map (a third LLM call that synthesizes both arguments)
5. Writes the deliberation record to the filesystem (`profiles/deliberations/`)
6. If the trigger was a supremacy tension, links the deliberation to the tension in `validate_supremacy()` output

The tension map synthesis is the critical step. It is not a summary. It identifies: where both agents agree (this narrows the decision space), where they disagree (this is the actual decision the operator must make), and what novel insight emerged (this is why the process exists — the thing neither agent would have produced alone).

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
- Publius and Brutus agents with fixed system prompts
- Deliberation orchestrator (trigger → context gathering → parallel invocation → tension map → record)
- Deliberation record storage on filesystem (`profiles/deliberations/*.yaml`)
- Dissent recording in precedent store (new `Dissent` model)
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
