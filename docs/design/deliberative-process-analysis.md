# Deliberative Process Analysis: Cross-Tradition Feature Classification

Classifying structural features of deliberative processes as necessary-and-valuable, incidental-and-valuable, or incidental-and-not-valuable for LLM agent governance. Grounded in empirical evidence across 8 deliberative traditions, not anchored to any single model.

Source research: `distro-work/research/deliberative-practices-structural-analysis.md`

## The core problem

The first deliberation prototype produced parallel position statements, not discourse. Both agents received the same input and argued in parallel. No reading of each other. No concessions. No position modification. The tension map was synthesized by a third call that compared static outputs. This is two briefs filed simultaneously.

The question is: which structural features of deliberative processes are load-bearing for producing generative output (novel insight, narrowed disagreement, surfaced considerations) vs. which are incidental to the traditions they come from?

## Feature classification

### Necessary and valuable

These features have strong empirical support across multiple traditions. Without them, the process does not produce generative output.

**1. Information before deliberation (Fishkin, citizens' assemblies)**

All participants receive balanced factual context before positions are staked. This is the single most robustly supported finding in deliberative democracy research. Fishkin's deliberative polls consistently show that informed deliberation produces qualitatively different outcomes from deliberation based on prior beliefs alone. Citizens' assemblies (Ireland, France) produce their outcomes through extended information phases before any position-taking.

In the governance system: both agents receive the same context package — the governance event, relevant axioms and implications, relevant precedents (via semantic search), accumulated dissents, operator profile. This context must be assembled and provided *before* either agent stakes a position. The first prototype did this correctly.

Without this: agents argue from their system prompt priors, not from the specifics of the case. Arguments become generic and non-responsive.

**2. Disconfirmation obligation (ACH, adversarial collaboration)**

Agents must identify what would *refute* their position, not just what supports it. Heuer's ACH methodology and Kahneman's adversarial collaboration protocol both center disconfirmation as the mechanism that distinguishes analysis from advocacy. Confirmation bias is the single most damaging pattern in deliberation — human or computational.

In the governance system: each agent's structured output must include a `refutation_conditions` field — specific, testable conditions under which their position would be wrong. Publius must state what evidence would make constitutional preemption inappropriate. Brutus must state what evidence would make domain autonomy unjustified.

Without this: both agents produce maximally confident advocacy. The exchange looks adversarial but never narrows because neither side specifies what would change their mind.

**3. Pre-commitment to update conditions (adversarial collaboration)**

Before the exchange begins, each agent commits to what would cause them to modify their position. This is the structural feature that distinguishes genuine deliberation from rationalized advocacy. Kahneman's adversarial collaboration protocol requires this explicitly: both sides agree in advance on what observations would resolve the dispute.

In the governance system: round 1 output from each agent includes `update_conditions` — specific claims or evidence from the opposing side that would trigger a concession or position modification. In subsequent rounds, agents must reference their own pre-committed update conditions when deciding whether to concede.

Without this: post-hoc rationalization. Agents reformulate rather than update. Position movement becomes cosmetic.

**4. Sequential responsive exchange**

Each round must respond to the previous round's specific claims. This is the mechanism that narrows disagreement and surfaces considerations neither side anticipated. The Federalist/Anti-Federalist exchange produced the Bill of Rights not because two sides argued but because the exchange modified both sides' positions. The generative output is the *movement*, not the arguments.

This feature appears in multiple traditions: Kahneman's adversarial collaboration requires iterative refinement of shared experimental designs; Fishkin's small groups require participants to engage with each other's specific points rather than restating; IBIS/dialogue mapping requires each contribution to respond to a specific existing element.

In the governance system: Brutus round 2 must reference specific sentences from Publius round 1 and explain why they are wrong, incomplete, or over-broad. Publius round 2 must either concede or rebut Brutus's specific attacks.

Without this: two parallel briefs. The tension map is a diff of static positions, not a record of what changed and why.

**5. Explicit concessions as first-class output**

When one side acknowledges the other's point, the problem space contracts. Concessions must be tracked as first-class outputs, not buried in prose. This feature draws from judicial opinion structure (where conceded points are explicitly identified) and from adversarial collaboration (where pre-committed update conditions, once met, produce formal position changes).

In the governance system: if Publius concedes that su-auth-001's text is broader than its purpose, that concession is a governance artifact — it identifies a specific deficiency in the implication text. If Brutus concedes that the absurdity doctrine resolves a tension, that concession strengthens the existing governance mechanism. Each round tracks concessions separately from arguments.

Without this: the exchange is performative. Both sides restate positions without the problem space changing.

**6. Formal recording of dissent with reasoning (judicial dissent, pre-mortem)**

Disagreement that is merely expressed is lost. Disagreement that is formally recorded with full reasoning becomes a resource for future revision. Varsava's analysis of judicial dissent shows that formalized dissents function as "living law" — they are active doctrinal resources that shape future legal development. Harlan's dissent in Plessy v. Ferguson became the basis for Brown v. Board of Education decades later.

Klein's pre-mortem technique shows a related finding: prospective hindsight (formally recording failure modes before they happen) produces ~30% more identified risks.

In the governance system: when deliberation terminates without convergence, the minority position is recorded with full reasoning in the precedent store. Future deliberations on related topics retrieve and consider past dissents. This is the mechanism by which the governance system revises itself over time.

Without this: governance decisions are point-in-time. The system has no memory of contested decisions and no mechanism for revisiting them when circumstances change.

**7. Question-first structure (IBIS, Socratic method)**

Deliberation begins by articulating the question, not by staking positions. IBIS (Issue-Based Information Systems) and dialogue mapping both start with the *question* as the root node, not a proposed answer. The Socratic method works by questioning, not asserting — targeting implicit assumptions rather than building cases.

This prevents premature commitment and ensures both agents address the same question. When agents stake positions first, they may be arguing past each other — answering different questions about the same governance event.

In the governance system: round 0 is question articulation, not position-taking. The deliberation orchestrator frames the governance event as a question: "Should mg-boundary-001 apply to system diagnostics that reference individuals?" not "mg-boundary-001 conflicts with ex-err-001." Both agents then respond to the same question.

Without this: agents frame the problem differently and argue past each other. Agreement and disagreement become difficult to identify because the agents may not be discussing the same thing.

### Incidental and valuable

These features have moderate empirical support or are achievable through simpler means. They add value but are not load-bearing for the core mechanism.

**8. Asymmetric roles (Federalist Papers, Red Team/Blue Team)**

One side builds a comprehensive, internally coherent case. The other attacks from any angle. The builder cannot cherry-pick because they must construct a complete defense. The attacker cannot be lazy because they must find actual weaknesses.

Red Team/Blue Team analysis supports this pattern, but with a critical caveat from the literature: authority parity is load-bearing. Devil's advocacy (assigned dissent without authority parity) consistently fails to produce generative outcomes — it degenerates into theater. In LLM agent systems, the authority parity problem may not apply in the same way (agents have no career incentives), but the finding that assigned dissent is weaker than authentic dissent is worth noting.

Achievable cheaper: both agents can argue their natural position (Publius for constitutional authority, Brutus for domain autonomy) without artificially assigning builder/attacker roles. The disconfirmation obligation (feature 2) and pre-committed update conditions (feature 3) do most of the work that asymmetric roles do in human systems.

**9. Proportionality screening before balancing (Alexy)**

When values conflict, first screen for suitability (does the proposed resolution actually achieve its stated goal?) and necessity (is there a less restrictive alternative?) before attempting to balance competing values. This sequential screening reduces the space of genuine dilemmas.

In the governance system: before weighing constitutional vs. domain axiom weight, first ask: does the domain implication actually address a legitimate local concern (suitability)? Is there a narrower reading that achieves the same end without triggering the tension (necessity)? Only if both screens pass does the weight hierarchy apply.

Achievable cheaper: add suitability and necessity questions to the agent prompt. The proportionality framework structures the reasoning without requiring a separate process stage.

**10. Explicit value annotation (Bench-Capon, Alexy)**

Arguments are tagged with the governance values they promote. This allows disagreements to be classified as factual (same values, different evidence assessments) or value-based (same evidence, different value orderings). Different resolution strategies apply to each type.

In the governance system: each argument in the structured output includes a `values_promoted` field. When the tension map identifies a disagreement, it classifies it as factual or value-based. Factual disagreements can be resolved by examining the text. Value-based disagreements require operator judgment about value ordering.

Achievable cheaper: the interpretive canon already does some of this work. A textualist argument promotes textual fidelity; a purposivist argument promotes axiom intent. Explicit value annotation adds precision but the canon field captures the main distinction.

**11. Composite voice reconciliation (Federalist Papers)**

Hamilton and Madison disagreed privately but published as Publius. The pseudonym forced internal reconciliation, producing arguments more robust than either would have written alone.

Achievable cheaper: constrain the agent prompt to steelman opposing views before committing to a position. Not as strong as genuine reconciliation, but captures most of the robustness benefit without doubling LLM calls per round.

**12. Multiple attacker angles (Federalist Papers, ACH)**

The Anti-Federalists attacked from multiple angles (individual rights, state sovereignty, executive power). ACH's diagnosticity matrix similarly requires evaluating evidence against *all* hypotheses, not just the favored one.

Achievable cheaper: instruct the attacker to vary angles across rounds. Round 1: textualist attack. Round 2: purposivist attack. Round 3: future scenario attack. This captures coverage without multiplying agents.

**13. Pre-mortem step (Klein)**

Before finalizing a resolution, assume it was implemented and failed. Generate failure modes. This "prospective hindsight" technique produces ~30% more identified risks than standard risk assessment.

Achievable cheaper: add a pre-mortem obligation to the final round. After the exchange converges or identifies a crux, both agents generate failure modes for the proposed resolution. This is a reasoning prompt, not a process restructuring.

### Incidental and not valuable

These features served functions in human deliberation that do not transfer to LLM agent systems.

**Pseudonymous authorship.** Depersonalized argument in the historical context. LLM agents have no reputation, ego, or social consequences. The depersonalization function is already inherent.

**Time pressure / publication deadlines.** Prevented over-theorization in human authors. LLM over-generation (verbosity, hedging) is addressed by output constraints and structured schemas, not deadline simulation.

**Real stakes (ratification vote, electoral consequences).** Created urgency and consequence in human authors. LLM agents do not respond to stakes. The urgency function is served by concrete proposals and termination conditions.

**Public audience.** Forced clarity for non-specialist readers. In a single-operator system with no public, this constraint has no function. Legibility for future machine readers is addressed by output format constraints.

**Sortition / random participant selection (citizens' assemblies).** Removes career/status incentives that distort human deliberation. LLM agents have no career incentives. The agent selection is determined by system design, not sortition.

**Facilitated small groups feeding into plenary (Fishkin).** This is the strongest empirically supported process structure for *human* deliberation. It addresses: (a) social dynamics in groups larger than ~10, (b) groupthink in unfacilitated groups, (c) perspectival diversity through random assignment. None of these problems exist in a two-agent LLM system. The facilitator role is partially captured by the deliberation orchestrator (process management, question articulation), but the small-group/plenary structure serves no function.

**Communicative vs. strategic orientation (Habermas).** The distinction between genuine understanding-seeking and manipulation-seeking is load-bearing for human discourse. LLM agents have no strategic interests. Their orientation is determined by their system prompt. The concern that agents might "strategically" argue rather than genuinely reason is addressed by disconfirmation obligations and pre-committed update conditions, not by monitoring orientation.

## Anti-patterns to avoid

From the cross-tradition analysis, the following patterns produce theatrical rather than generative outcomes:

1. **Assigned dissent without authority parity.** If Brutus's arguments have no mechanism to influence the outcome, the exchange is performative. Both agents' arguments must reach the operator with equal weight.

2. **Balancing without prior screening.** Jumping to axiom weight comparison without first checking suitability (does the domain implication address a real concern?) and necessity (is there a less restrictive reading?) skips the steps that resolve most tensions.

3. **Information during (not before) deliberation.** Introducing new context mid-exchange produces anchoring effects. All relevant axioms, implications, precedents, and dissents must be provided before round 1.

4. **Forced synthesis when positions are genuinely incompatible.** Not every tension has a "both sides are partly right" resolution. The system must be able to surface genuine dilemmas for operator decision rather than manufacturing false convergence.

5. **Deliberation without transmission (Dryzek).** Deliberation records that are never surfaced to the operator, never queried by future deliberations, and never influence precedent are wasted computation. The transmission mechanism (briefing integration, precedent store, dissent accumulation) is as important as the deliberation itself.

## Revised process design

### Structure

```
Round 0: QUESTION ARTICULATION
  The deliberation orchestrator frames the governance event as a question.
  Assembles shared context: axioms, implications, precedents, dissents,
  operator profile.

  Both agents receive identical context. Neither has staked a position.

Round 1: INITIAL POSITIONS (parallel)
  Both agents respond to the question. Each output includes:
  - Position (claim + grounds + warrant, Toulmin structure)
  - Canon applied (textualist | purposivist | absurdity | omitted-case)
  - Refutation conditions: what evidence would make this position wrong
  - Update conditions: what the other agent could say that would trigger
    a concession or position modification
  - Values promoted: which governance values this position serves

  Parallel invocation is acceptable for round 1 because agents respond
  to the question, not to each other. The sequential requirement applies
  from round 2 onward.

Round 2: RESPONSIVE EXCHANGE (sequential, alternating)
  Each agent reads the other's round 1 output. Must:
  - Reference specific claims from the other agent
  - Attack: identify weaknesses, introduce unconsidered factors
  - Check the other agent's refutation conditions against known evidence
  - Check own update conditions against the other agent's arguments
  - Concede where update conditions are met (first-class output)
  - State position movement explicitly

Round 3+: CONTINUATION (sequential, alternating)
  Continue until a termination condition is met. Each round:
  - Responds to the previous round's specific claims
  - Tracks concessions
  - States position movement
  - May introduce new attacks if prior concessions create new gaps

Final round: PRE-MORTEM
  After convergence or crux identification, both agents assume the
  proposed resolution was implemented and generate failure modes.
  This is a collaborative step, not adversarial.
```

### Termination conditions

1. **Convergence.** Both sides agree on a resolution (possibly different from either starting position).
2. **Crux identification.** The disagreement has narrowed to a single, clearly stated point that the operator must decide.
3. **Round limit.** Maximum 4 exchange rounds (8 total messages). If no convergence or crux by round 4, surface both positions and narrowing history.
4. **Concession cascade.** One side concedes enough points that their remaining position is untenable. The other side's resolution stands, pending operator review.
5. **Incompatibility.** Positions are genuinely incompatible (value-based disagreement, not factual). Surface both positions with explicit value annotations for operator decision. Do not force synthesis.

### Tracked outputs per round

```yaml
round: 2
agent: brutus
responds_to: round-1-publius
claims_attacked:
  - claim: "su-auth-001 targets user-to-system auth only"
    attack: "The text says 'all authentication code' without scoping"
    attack_type: undermining  # Toulmin: attacking a premise
refutation_conditions:
  - "If the implication derivation log shows su-auth-001 was scoped
     to user-to-system during derivation, the textualist reading is wrong"
update_conditions_checked:
  - condition: "Publius shows a precedent where su-auth-001 was applied
     to service-to-service auth"
    met: false
    reasoning: "Publius cited prec-007 but it concerns user auth only"
concessions: []
values_promoted: [domain_autonomy, implementation_freedom]
position_movement: >
  No movement from starting position. Opening attack round.
```

### What changes from the first prototype

| Feature | First prototype | Revised |
|---------|----------------|---------|
| Agent invocation | Parallel, no cross-talk | Round 1 parallel; round 2+ sequential |
| Framing | Agents receive raw tension | Orchestrator frames a question |
| Rounds | 1 per agent | 2-4 per agent (4-8 total messages) + pre-mortem |
| Disconfirmation | Not present | Required per round (refutation conditions) |
| Update conditions | Not present | Pre-committed in round 1, checked each round |
| Concessions | Not tracked | First-class output, tracked per round |
| Position movement | None (static) | Explicit per round |
| Value annotation | Not present | Per argument |
| Tension map | Third-party synthesis | Emerges from exchange |
| Dissent recording | Not present | Minority position stored in precedent store |
| Termination | Fixed (1 round) | Conditional (5 conditions) |
| Pre-mortem | Not present | Final collaborative round |

### Cost analysis

At 4 rounds (8 messages) + pre-mortem (2 messages), using `fast` (Gemini 2.5 Flash):
- ~10 LLM calls per deliberation
- Each call: ~2.5K input tokens (context + previous rounds grow), ~600 output tokens (structured, more fields)
- Total: ~31K tokens per deliberation
- At Gemini 2.5 Flash pricing: ~$0.015 per deliberation
- 6 deliberations: ~$0.09

At `balanced` (Claude Sonnet 4):
- Same token counts
- ~$0.15 per deliberation
- 6 deliberations: ~$0.90

The cost increase over the first prototype (~50%) is negligible. The constraint remains operator attention, not cost.

## Relationship to traditions

| Feature | Primary source | Supporting sources |
|---------|---------------|-------------------|
| Information before deliberation | Fishkin | Citizens' assemblies, ACH |
| Disconfirmation obligation | ACH (Heuer) | Adversarial collaboration (Kahneman) |
| Pre-committed update conditions | Adversarial collaboration | — |
| Sequential responsive exchange | Federalist Papers | Fishkin small groups, IBIS |
| Explicit concessions | Judicial opinion structure | Adversarial collaboration |
| Formal dissent recording | Judicial dissent (Hughes, Varsava) | Pre-mortem (Klein) |
| Question-first framing | IBIS, Socratic method | — |
| Proportionality screening | Alexy | European Court of Human Rights |
| Value annotation | Bench-Capon | Alexy weight formula |
| Pre-mortem | Klein | — |
| Argument structure | Toulmin | ASPIC+ (simplified) |

## Open questions

1. **Degeneration of thought.** Multi-agent LLM debate research (Du et al. 2023) shows that LLMs cannot generate novel perspectives through self-reflection once committed. The multi-round exchange mitigates this, but extended exchanges (5+ rounds) may produce entrenchment rather than convergence. The round limit (4 exchanges) is a pragmatic guard against this, not an empirically validated threshold.

2. **Homogeneous vs. heterogeneous models.** Research suggests LLMs "might not be a fair judge if different LLMs are used for agents." The current design uses the same model for both agents with different system prompts. Whether different models would produce richer deliberation is unknown.

3. **Negotiation vs. deliberation.** Mansbridge's distinction between situations requiring negotiation (genuine interest conflicts) and deliberation (reasoning about shared values) applies. Some governance tensions may be interest conflicts (domain autonomy vs. constitutional authority) rather than reasoning problems. The system should be able to identify when deliberation is the wrong tool.

4. **Computational argumentation integration.** Dung's acceptability semantics and ASPIC+'s attack taxonomy (undermining, undercutting, rebutting) could formalize the deliberation output. Whether this formalization improves operator decision-making is untested. The Toulmin structure in round outputs is a lightweight version of this.
