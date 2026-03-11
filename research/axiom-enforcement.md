# Axiom Enforcement Research

Status: **In Progress** — OQ1-OQ7 researched, synthesis and recommendations in progress
Started: 2026-03-03

## Problem Statement

How do we enforce arbitrary axioms defined in plain language — broad, high-level
principles that should govern all decisions in a system?

Example axiom: *"This system is developed for a single user and by that single
user, the operator (Hapax). This will always be the case. All decisions must
be made respecting and leveraging that fact."*

## Core Challenge

Axioms operate at a fundamentally different abstraction level than anything we
traditionally enforce. A linter checks syntax. A type system checks contracts.
A test checks behavior. An axiom constrains *judgment*. The enforcement problem
decomposes into:

1. **Interpretation**: What does the axiom concretely mean in this codebase, now?
2. **Detection**: How do you know when a decision violated it?
3. **Prevention vs. correction**: Stop violations before they land, or catch after?

No single mechanism handles all three. The answer is a layered defense.

## Proposed Layered Architecture

### Layer 1: Static Injection (visibility)
- CLAUDE.md, system prompts, operator context
- Ensures axioms are *present* at decision time
- Necessary but not sufficient — visibility does not equal compliance
- **Cost**: near-zero. **Coverage**: universal. **Strength**: weak.

### Layer 2: Concrete Rule Derivation (tests, lints, assertions)
- Hand-written or auto-generated rules encoding known implications
- Deterministic, fast, runs in CI
- Can only cover *known* implications — can't handle unknown unknowns
- **Cost**: authoring time. **Coverage**: enumerated cases. **Strength**: strong for what it covers.

### Layer 3: LLM Axiom Decomposition (the novel bridge)
- LLM with full codebase context generates concrete, current implications
- Regenerated periodically as codebase evolves
- Some implications become Layer 2 tests. Some become review prompts. Some become planning constraints.
- Bridges the abstraction gap between axiom and enforcement
- **Cost**: LLM calls per regeneration. **Coverage**: broad but imperfect. **Strength**: medium-high.
- **Stability concern**: Must derive-once-then-enforce, not re-derive per check (see OQ3).

### Layer 4: Top-Down Axiom Audit (periodic LLM review)
- Scheduled agent reads full codebase against axiom set, reports violations
- Works top-down: "given the code, does it comply?" (not "what should it look like?")
- Catches drift and accumulation of small violations
- **Cost**: high (full codebase reads). **Coverage**: comprehensive. **Strength**: medium.

### Layer 5: Decision-Time Axiom Reasoning (active enforcement)
- At significant decisions (plan mode, architecture), explicitly reason about compliance
- Requires stated relationship between decision and each axiom
- Prevents rather than detects
- **Cost**: friction per decision. **Coverage**: LLM-mediated decisions only. **Strength**: high.

### Layer 6: Operator Authority (final arbiter)
- Operator validates interpretations, adjudicates edge cases, updates axioms
- No automated system gets final word on axiom interpretation
- **Cost**: human attention. **Coverage**: escalated cases. **Strength**: definitive.

### Layer 7: Precedent Database (accumulated case law) — NEW

Research strongly supports adding a precedent accumulation mechanism:

- Records each significant axiom-application decision (situation, axiom, decision, reasoning)
- Indexed by semantic similarity for retrieval when similar situations arise
- Operator decisions carry highest authority (vertical stare decisis analog)
- Supersession chains: new decisions that override old ones link explicitly
- Distinguishing metadata: what facts were decisive, enabling future "distinguishing"
- Review triggers: frequently-distinguished precedents signal axiom refinement needed

This layer is the **connective tissue** between all other layers. Layer 3 decomposition
produces initial precedents. Layer 5 decision-time reasoning consumes and creates them.
Layer 6 operator authority creates the highest-weight precedents. Over time, the
precedent database becomes the primary source of "what this axiom means in practice."

## Constitutional Law Analogy

| Legal System | Axiom Enforcement |
|---|---|
| Constitution | Axioms (broad, stable, plain language) |
| Canons of construction | Interpretive framework for axiom decomposition |
| Judicial interpretation | LLM decomposition (axiom to concrete implications) |
| Case law / stare decisis | Precedent database (accumulated decisions) |
| Legislation | Derived tests and rules |
| Law enforcement | CI, linters, mechanical checks |
| Levels of scrutiny | Enforcement tiering by impact (see OQ6) |
| Judicial review | Periodic axiom audit (top-down compliance) |
| Amendment process | Operator revising axioms |

## Key Insight

LLMs don't replace traditional enforcement — they **generate the rules** that
traditional enforcement checks. The LLM's role is interpretation (what does this
axiom mean here?), not policing (did you follow it?). The decomposition pipeline:

```
Axiom (plain language)
  -> LLM interpretation (context-specific implications)
    -> Concrete rules (tests, lint rules, review checklists)
      -> Mechanical enforcement (CI, pre-commit, scheduled audit)
        -> Operator adjudication (edge cases, false positives)
          -> Precedent database (accumulated case law)
            -> feeds back into interpretation
```

---

## Open Questions — Research Findings

### OQ1: Axiom Conflict Resolution

**Question**: What happens when axioms contradict? Example: "single user" vs
"accessible from multiple devices" — is mobile access multi-user scaffolding?

**Status**: Researched. Three viable strategies identified.

**Finding**: Three fundamentally different approaches exist in practice:

#### Strategy A: Proportionality Balancing (legal tradition)

Robert Alexy's framework (from *A Theory of Constitutional Rights*) distinguishes
rules (binary validity: applies or doesn't) from principles (optimization requirements
with *weight*). Conflicting principles are resolved through contextual balancing,
not by invalidating one.

Alexy's weight formula: `W(i,j) = (I_i * W_i * R_i) / (I_j * W_j * R_j)`

Where: I = intensity of interference, W = abstract weight, R = epistemic reliability.

Key property: **the same two principles may balance differently in different contexts.**
Courts are "loath to build intra-constitutional hierarchies of norms" — instead
announcing "no right is absolute," which forces case-by-case balancing.

*Source: Stone Sweet & Mathews, "Proportionality Balancing and Global Constitutionalism,"
Columbia J. Transnat'l L. (2008)*

#### Strategy B: Lexicographic Ordering (Anthropic's approach)

Anthropic's 2026 constitution uses strict priority tiers:
1. Safety (overrides everything)
2. Ethics (overrides compliance and helpfulness)
3. Compliance with Anthropic guidelines
4. Helpfulness (lowest priority)

"In cases of apparent conflict, Claude should generally prioritize these properties
in the order in which they're listed."

Advantage: deterministic, simple. Disadvantage: crude — the word "generally"
provides an escape hatch because strict ordering fails on edge cases. Academic
critique (arXiv 2512.03048): models learn "the surface grammar of compliance
rather than its normative substance."

#### Strategy C: Deterministic Override Rules (policy-as-code)

Cedar (AWS): `forbid > permit > implicit deny`. Period. No balancing.
OPA (Rego): developer-defined composition — the conflict resolution is itself
an explicit policy.

Advantage: perfectly predictable, auditable. Disadvantage: only works when
outcomes are binary (allow/deny), not when principles operate in continuous space.

#### Recommendation for Axiom Systems

Use **Strategy A (proportionality) as the default**, with **Strategy B (precedence
ordering) as fallback** when proportionality yields no clear answer:

1. When axioms appear to conflict in a specific case, **balance contextually**:
   which axiom is more intensely affected? Which has stronger epistemic grounding?
2. If balancing is inconclusive, fall back to a **declared precedence ordering**
   of axioms (operator-maintained).
3. **Record the resolution as precedent** (Layer 7) so the same conflict in similar
   circumstances doesn't require re-adjudication.

For the specific "single user" vs "multi-device" example: these are not actually
conflicting. Multi-device access *for the single user* is consistent with both.
The real conflict would be "single user" vs "let visitors browse read-only" — and
proportionality balancing would consider: how intensely does read-only access
violate single-user? (Mildly — no data mutation, no auth complexity.) How
important is the visitor-access goal? (Depends on context.)

---

### OQ2: Axiom Weighting / Precedence

**Question**: Are all axioms equal, or do some override others?

**Status**: Researched. Strong consensus: not all equal.

**Finding**: Every mature system uses some form of weighting or tiering.

#### Legal: Tiered Scrutiny

US constitutional law applies different levels of review depending on what's at stake:
- **Strict scrutiny**: fundamental rights (speech, religion, race). Must be
  "narrowly tailored" to a "compelling interest." Laws rarely survive.
- **Intermediate scrutiny**: important but not fundamental (gender). Must be
  "substantially related" to an "important objective."
- **Rational basis**: everything else. Must be "rationally related" to a
  "legitimate purpose." Laws almost always survive.

Critical insight: **the tier is selected based on what is at stake in the specific
case, not which principle is invoked.** The First Amendment produces strict scrutiny
for political speech but rational basis for signage permits.

#### AI Safety: Explicit Hierarchy

Anthropic's 4-tier lexicographic ordering. Justified pragmatically: "It's not that
safety ultimately matters more than ethics, but that current models can make mistakes
... because of flawed beliefs, value gaps, or limited contextual understanding."
The ordering reflects epistemic humility, not permanent value judgment.

Also uses **hardcoded vs. softcoded** distinction:
- Hardcoded: absolute prohibitions (never overridable)
- Softcoded defaults: adjustable by operators within bounds

#### Architecture: Explicit QAR Ranking

SEI's ATAM (Architecture Tradeoff Analysis Method): teams explicitly rank quality
attributes at project inception. "System Priority Setting: one has to pick where to
excel, and where to make the myriad compromises necessary." The ranking becomes the
tiebreaker for all subsequent decisions.

Neal Ford: the priority ranking should itself evolve. Fitness functions protect the
current ordering, but the ordering can be revisited.

#### Recommendation for Axiom Systems

1. **Axioms should have declared weights**, but weights are defaults, not absolutes.
2. Use a **two-level system**: abstract weight (operator-declared, relatively stable)
   and contextual intensity (assessed per-case). This mirrors Alexy's formula.
3. **Distinguish hardcoded from softcoded axioms.** Some axioms may be absolute
   (never violated regardless of context). Others may be defeasible (violated
   when a stronger axiom demands it in a specific context).
4. **Document the weighting rationale** so it can be challenged and revised.

---

### OQ3: Decomposition Stability

**Question**: How do you prevent LLM from generating different implications on
different runs?

**Status**: Researched. Problem is real and empirically severe. Mitigations exist.

**Finding**: LLMs are demonstrably non-deterministic even at temperature=0.

#### The Problem is Real

- **arXiv 2408.04667**: 5 LLMs, 8 tasks, 10 runs at T=0 — accuracy variations
  up to **15% across runs**, best-to-worst gap up to **70%**.
- **Blair-Stanek et al. (2025)**: 500 legal questions at T=0 — GPT-4o unstable
  on **43%** of cases, Claude 3.5 on **10.6%**, Gemini 1.5 on **50.4%**.
- **Purushothama et al. (2025)**: Legal interpretation — only **9 of 2,070**
  model-scenario pairs were perfectly stable across prompt variants.

Root cause: floating-point instability in parallel GPU computation. Not a fixable
software bug — it's inherent to the architecture.

#### Mitigation: Derive-Once-Then-Enforce (Primary)

The most important insight: **separate the high-variance interpretation step from
the low-variance enforcement step.**

1. Run LLM decomposition to generate concrete implications.
2. Human-review the implications.
3. Lock the reviewed implications as versioned rules.
4. Enforce the locked rules mechanically.
5. Re-derive only when axioms change or the codebase has evolved significantly.

This is analogous to how Constitutional AI works: consistency comes from training
(learning compliance patterns at the weight level), not from runtime interpretation.
For a non-training system, the analog is: **commit the interpretations to a stable
artifact (file, database), don't regenerate them per-check.**

#### Mitigation: Self-Consistency Voting (Supplementary)

For the derivation step itself:
- **Self-consistency** (Wang et al., 2022): Generate N reasoning paths from the
  same prompt, take majority vote. Improves accuracy on reasoning benchmarks.
- **Inter-LLM voting**: ~5% accuracy improvement by voting across different LLMs.
  Intra-LLM voting (same model, multiple runs) shows minimal improvement because
  within-model variation is mostly random noise.
- **Cost**: N=5 costs 5x a single call. Acceptable for infrequent rule derivation,
  not for per-check enforcement.

#### Mitigation: Prompt Design

- Structured output formats (JSON schemas) reduce surface variation.
- Few-shot examples establish consistent interpretive frames.
- Explicit rubrics: "Consider against these specific criteria: [list]."
- Use the same model version with pinned system prompt for all derivation runs.

#### Mitigation: Caching / Versioning

- **Semantic caching**: Cache outputs for semantically equivalent inputs.
- **Prompt versioning** (Langfuse): Version-control prompts and pin to environments.
- **Derived-rule versioning**: Git-track the output of each decomposition run.

#### Recommendation

1. **Primary**: Derive-once-then-enforce. Generate implications, review, lock.
2. **At derivation time**: Use self-consistency (N=3-5) and structured output.
3. **Version everything**: axiom text, derivation prompt, model used, derived rules.
4. **Scheduled re-derivation**: Tied to axiom changes or significant codebase evolution,
   not per-run. Diff new derivation against previous to surface genuine changes vs. noise.

---

### OQ4: Cost / Proportionality

**Question**: How much enforcement overhead is acceptable?

**Status**: Researched. Concrete thresholds identified.

**Finding**: Enforcement overhead has a hard ceiling beyond which it becomes
counterproductive. The literature converges on several thresholds.

#### Empirical Thresholds

- **10-minute rule**: If total pipeline time exceeds 10 minutes, developer behavior
  changes — they batch commits, context-switch, lose flow state. Elite DORA teams
  keep total lead time under 1 hour with multiple deploys per day.
- **Compliance crowding out production**: Natsios (former USAID administrator):
  "A point can be reached when compliance becomes counter-productive. I believe we
  are well past that point." Enforcement that consumes more time than the work it
  protects is a failure.
- **Alarm fatigue**: When developers start ignoring quality gate signals, enforcement
  has become counterproductive. No published threshold, but the pattern is universal.
- **Atlassian (2024)**: 69% of developers lose 8+ hours/week to inefficiencies.
  Three pillars of positive developer experience: fast feedback loops, manageable
  cognitive load, flow state.

#### Typical CI Budget Allocation

| Gate | Budget | Notes |
|------|--------|-------|
| Linting/formatting | < 30s | Auto-fix preferred over blocking |
| Static analysis (incremental) | < 2 min | Differential analysis — only check changes |
| Unit tests | 1-5 min | Parallelized |
| Integration tests | 5-15 min | Often parallelized, may run async |
| Full pipeline | < 10 min (elite) to < 30 min (acceptable) | |

#### Architecture Fitness Function Overhead

Neal Ford's framework: fitness functions use diverse mechanisms (tests, metrics,
monitoring). Overhead varies by implementation:
- **ArchUnit** (architecture tests): seconds for small projects, minutes for large.
  Class caching mitigates import cost.
- Key constraint: **velocity is proportional to cycle time**. Fitness function
  overhead directly limits the speed of architectural evolution. Slow checks lead
  to skipped checks.

#### The Proportionality Principle

From legal analysis: **enforcement should be proportional to the severity of the
risk.** Applied to axioms:

| Axiom Implication Severity | Enforcement Budget | Example |
|---|---|---|
| Architectural (existential) | High — block until resolved | Multi-user database schema |
| Design (significant) | Medium — flag for review | API supporting multiple auth providers |
| Implementation (minor) | Low — automated check, auto-fix | Config file supporting user switching |
| Stylistic (cosmetic) | Minimal — lint only | Variable names implying multiple users |

#### Recommendation

1. **Total axiom enforcement budget**: < 5% of total development time. This is a
   rough guideline — the real test is whether enforcement is being ignored.
2. **Per-check latency**: Layer 2 (mechanical) < 30s. Layer 3 (LLM decomposition)
   is amortized, not per-check. Layer 4 (audit) runs async, never blocks work.
3. **Escalation, not blocking**: Most axiom checks should warn, not block. Reserve
   blocking for hardcoded axiom violations (the equivalent of strict scrutiny).
4. **Monitor enforcement health**: Track false positive rate, override frequency,
   and time-to-resolution. Rising numbers indicate enforcement recalibration needed.

---

### OQ5: Axiom Lifecycle

**Question**: How do axioms get created, challenged, modified, or retired?

**Status**: Researched. Strong convergent patterns across domains.

**Finding**: Every mature system for managing broad principles converges on
**immutability + supersession** rather than in-place mutation.

#### Patterns Across Domains

| Mechanism | Constitution | IETF RFC | Software ADR | OPA/Cedar | Anthropic CAI |
|-----------|-------------|----------|-------------|-----------|---------------|
| Immutable after acceptance | Yes (amendments) | Yes | Yes | Versioned | **No** (mutable at discretion) |
| Supersession chain | Amendments repeal prior | "Obsoleted by" | "Superseded by" | Git history | No chain |
| Formal proposal process | Article V | Internet-Draft | Proposed status | Pull request | Internal team |
| Ratification/review | 3/4 states | IETF consensus | Team review | CI + tests | None |
| Scheduled review | Florida: every 20 years | None | `next_review_due` | Impact analysis | None |

Anthropic's constitution is the **outlier** — mutable at discretion with no
supersession record. Every other mature system uses append-only history.

#### Key Properties

1. **High friction for creation**: Constitutional amendments require supermajority
   (3/4 states). 27 amendments in 237 years. High friction ensures only principles
   with overwhelming consensus survive. This is by design.

2. **Immutability preserves reasoning**: When an ADR or RFC is superseded, the old
   document + reasoning remains visible. You can always trace *why* the system
   evolved. In-place mutation destroys this institutional memory.

3. **Supersession chains enable archaeology**: A chain of superseding documents
   tells the story of how understanding evolved. "The 27th Amendment was ratified
   in 1992 after a 202-year delay from its 1789 proposal."

4. **Triggers for revision**: Social crisis, structural problems, sustained
   movements, accumulated case law revealing inadequacy. In software: repeated
   ADR distinguishing (applying a principle but narrowing it) signals the
   principle needs updating.

#### Recommendation for Axiom Lifecycle

1. **Creation**: Operator declares axioms explicitly. Each axiom gets an ID, text,
   creation date, and declared weight. Creation is a deliberate act, not an
   emergent inference.

2. **Immutability**: Once active, axiom text is frozen. Changes produce a new axiom
   version that explicitly supersedes the old one. Both versions remain in the record.

3. **Challenge mechanism**: Any layer can flag a potential axiom inadequacy:
   - Layer 3 decomposition produces contradictory implications
   - Layer 4 audit finds persistent false positives
   - Layer 5 decision-time reasoning finds inapplicable axiom
   - Layer 7 precedent database shows frequent distinguishing

4. **Revision trigger**: Axiom revision is operator-initiated, not automated.
   The system surfaces evidence that revision may be needed; the operator decides.

5. **Retirement**: Axioms can be retired (marked inactive) but never deleted.
   The precedent database retains all decisions made under retired axioms.

6. **Scheduled review**: Optional periodic review (quarterly/annual) where operator
   re-assesses all active axioms against accumulated precedent.

---

### OQ6: Enforcement Granularity Mismatch

**Question**: A single-sentence axiom has implications ranging from architecture
to variable naming. How to match enforcement intensity to significance?

**Status**: Researched. The answer is tiered scrutiny.

**Finding**: Every domain that enforces broad principles uses some form of
**impact-based tiering** to match enforcement intensity to significance.

#### The Universal Pattern

```
Principle: "Single user system"
    |
    +-- Implication: Architecture stores data for one user only
    |     -> High impact: Architecture review, blocking check
    |
    +-- Implication: No multi-tenant API patterns
    |     -> Medium impact: PR review flag, non-blocking
    |
    +-- Implication: No user-switching UI
    |     -> Low impact: Automated lint check
    |
    +-- Implication: Comments don't say "users" (plural)
          -> Cosmetic: Ignore (enforcement cost > violation cost)
```

#### Legal: Levels of Scrutiny (detailed)

The First Amendment is one sentence, but enforcement intensity varies by orders
of magnitude depending on what's at stake:

- Political speech -> strict scrutiny (almost never restrict)
- Commercial advertising -> intermediate scrutiny (can regulate with justification)
- Signage permits -> rational basis (almost always upheld)

**The tier is selected based on what is at stake, not which principle is invoked.**

#### Software: Layered Enforcement

| Layer | Mechanism | Scope | Cost | Latency |
|-------|-----------|-------|------|---------|
| IDE | Linter, formatter | Developer | Near-zero | Instant |
| Pre-commit | Hooks | Single commit | Low | Seconds |
| Pull request | Static analysis, review | Change set | Medium | Minutes |
| CI/CD | Integration tests, quality gates | Build pipeline | Medium-high | Minutes-hours |
| Architecture review | Design review, ADR | System-level | High | Days-weeks |
| Governance | Audits, compliance | Organization-wide | Very high | Quarterly |

The same principle ("code must be secure") produces different enforcement at each
layer. A linter catches dangerous function calls instantly for free. A security
review board considers the authentication architecture at high cost over weeks.

#### Security: Risk-Based Tiering

NIST CSF, ISO 27001, and CIS Controls all use **implementation groups** that scale
enforcement to assessed risk:

- CIS IG1: "basic cyber hygiene" for every organization
- CIS IG2: more controls for organizations with sensitive data
- CIS IG3: full controls for organizations with highly sensitive data

**Asset classification determines enforcement intensity**, not the principle itself.
"Protect data" is one principle, but enforcement differs by orders of magnitude
between PII and public docs.

#### Recommendation: Axiom Implication Tiers

Define four tiers for axiom implications, mirroring legal scrutiny levels:

| Tier | Legal Analog | Enforcement | Examples |
|------|-------------|-------------|---------|
| T0: Existential | Strict scrutiny | Block until resolved | Architecture decisions that contradict axiom |
| T1: Significant | Intermediate scrutiny | Flag for review, require justification | Design patterns that weaken axiom compliance |
| T2: Minor | Rational basis | Automated check, warn | Implementation choices with axiom implications |
| T3: Cosmetic | Below threshold | Ignore or lint-only | Naming, comments, stylistic conformance |

**The tier assignment itself is a judgment call** — and should be made during
Layer 3 decomposition, reviewed by operator, and recorded in the precedent database.

---

### OQ7: Existing Art / Prior Work

**Question**: What existing systems, papers, or frameworks address this problem?

**Status**: Researched. Comprehensive survey complete.

#### Constitutional AI (Anthropic)

The most direct prior art. Bakes principle-compliance into model weights through
training:
- Phase 1 (SFT): Model critiques and revises outputs against principles
- Phase 2 (RLAIF): Model generates preference pairs judged against random principle

**Key limitation for our context**: CAI requires *training* the model. Our axioms
can't modify Claude's weights. We must achieve compliance through prompt-based and
tool-based mechanisms, not training.

**Key insight borrowed**: The distinction between hardcoded (never overridable) and
softcoded (adjustable within bounds) principles.

#### Policy-as-Code (OPA, Sentinel, Cedar)

Deterministic policy engines. Policies written in domain-specific languages, evaluated
mechanically, binary outcomes (allow/deny).

**Key limitation**: Only handles axiom implications that can be expressed as
deterministic rules. ~30-40% of "single user" implications could be automated
this way; 60-70% require judgment.

**Key insight borrowed**: Treat policies as code artifacts — version-controlled,
tested, staged rollout, rollback capability.

#### Architecture Fitness Functions (Neal Ford)

Automated checks that verify architectural characteristics haven't degraded.
Use tests, metrics, and monitoring. Continuous verification rather than
point-in-time review.

**Key insight borrowed**: Fitness functions for axioms — automated checks that
verify axiom compliance metrics haven't degraded. Can encode Layer 2 rules as
fitness functions.

#### AI Guardrails (Guardrails AI, NeMo Guardrails)

Runtime input/output validation for LLM applications. Validators check for
specific patterns (PII, toxicity, off-topic responses).

**Key limitation**: Guardrails check *outputs*, not *decisions*. An axiom violation
might be a decision that never produces a visible output (e.g., choosing a
multi-user database schema).

**Key insight borrowed**: The validator pattern — pluggable checks that can be
composed into pipelines. Each axiom implication could be a validator.

#### Statutory Construction for AI Constitutions (arXiv:2509.01186)

He, Nadeem et al. (Princeton/Stanford, 2025). Most directly relevant paper.

**Key findings**:
- 5 judge models across 56 rules: **20 of 56 rules lack consensus on >50% of
  tested scenarios.** Models default to broad interpretations.
- Adapted **12 legal canons of statutory construction** for AI constitutions:
  textualist (literal), purposivist (intent-based), omitted-case canon, etc.
- **Rule refinement pipeline**: Iteratively rewrites ambiguous rules using
  high-disagreement examples. Both prompt-based and RL-based approaches
  "significantly reduce entropy across the set of reasonable interpreters."
- **Absurdity doctrine**: Disregard interpretations producing results "no
  reasonable person could endorse." Useful for filtering harmful derivations.
- **Irreconcilability canon**: When two contradictory provisions are simultaneously
  adopted, neither should be given effect. Flags contradictions.

**Key insight borrowed**: Explicit interpretive strategies matter enormously.
Axiom decomposition should specify *which canon of construction* is being applied.

#### Case-Based Reasoning for AI Alignment (UW, 2025)

Feng, Chen et al. propose "Case Repositories" as complement to constitutional approaches:
1. Gather seed cases from real conflicts
2. Elicit key dimensions through expert input
3. Use LLMs to generate case variations
4. Public judgment to improve cases
5. Compile into case repository that serves as precedent

Directly supported by Oxford/Stanford "Legal Alignment" paper (Kolt et al., 2026):
"Legal positivist arguments for analogical reasoning that ground decision-making
in the concrete facts of prior cases and precedent... are already inspiring
case-based reasoning approaches to alignment."

**Key insight borrowed**: The case repository concept becomes our Layer 7 Precedent
Database. Axioms gain enforceable content through accumulated concrete decisions.

#### Real-World Principle Enforcement (Rails, Linux, Google)

How successful projects enforce broad design principles without formal mechanisms:

- **Rails** ("convention over configuration"): Encoded in the framework itself.
  The conventional path is easy; the unconventional path is possible but harder.
  This is **friction-based enforcement** — the principle shapes the tool ergonomics.
- **Linux kernel**: Linus Torvalds as gatekeeper. Principles enforced through code
  review culture and benevolent dictator final say. Human judgment, not automation.
- **Google** (testing culture): Principles embedded in tooling defaults, style
  guides enforced by automated formatters, architecture decisions documented in
  design docs reviewed by readability reviewers.

**Key insight borrowed**: Friction-based enforcement (making axiom-compliant choices
the path of least resistance) is complementary to detection-based enforcement
(finding violations after the fact).

---

## Cross-Cutting Findings

Three patterns recur across every domain studied:

### Finding 1: Principles Require Interpretation Infrastructure

A principle alone is insufficient. Legal systems add canons of construction, case
law, levels of scrutiny. Software adds linters, review boards, ADRs. Security
frameworks add risk assessment, implementation groups, tiered controls. The He et al.
paper demonstrates empirically: bare rules produce 50%+ disagreement. **The
interpretation infrastructure is as important as the principle itself.**

### Finding 2: Immutability + Supersession Beats Mutation

Every mature system (constitutions, RFCs, ADRs, OPA policies) treats principles
as immutable after acceptance and evolves through explicit supersession chains.
The append-only approach preserves institutional memory and enables reasoning about
*why* things changed. **Mutation destroys provenance.**

### Finding 3: Impact Determines Enforcement Intensity

Constitutional law discovered this with levels of scrutiny. Security frameworks
with risk-based tiering. Software with enforcement layers. The principle stays
constant; the question is always "how significant is this specific application?"
**One axiom, many enforcement intensities, selected by impact assessment.**

---

## Synthesis: Toward an Implementation

### What We Know

1. The layered architecture (Layers 1-7) is sound. Every domain studied uses
   layered enforcement. No single mechanism suffices.

2. The LLM's role is **interpreter, not enforcer**. LLMs generate rules; traditional
   tools enforce them. This is the derive-once-then-enforce pattern.

3. Axioms need **interpretation infrastructure**: declared weights, explicit
   interpretive strategies (which canon of construction), impact-based tiering
   of implications, and a precedent database.

4. The **precedent database** (Layer 7) is the most novel and potentially highest-value
   addition. It's where the axiom system accumulates "case law" that gives concrete
   meaning to abstract principles.

5. Axiom lifecycle should be **immutable + supersession**, not in-place editing.

6. Enforcement overhead must be **proportional to impact**. The 10-minute rule,
   the compliance-crowding-out antipattern, and alarm fatigue are real constraints.

### What Remains Unknown

1. **Optimal derivation frequency**: How often should Layer 3 re-derive implications?
   Tied to codebase change rate, but no empirical guidance on thresholds.

2. **Precedent retrieval quality**: Does vector similarity actually find relevant
   precedents, or does it surface false matches? Needs empirical testing.

3. **Operator cognitive budget**: How many axiom-related decisions per week can the
   operator handle before enforcement becomes a burden? Directly tied to the
   single-user axiom — the operator is the bottleneck by design.

4. **False positive tolerance**: What false positive rate on axiom checks is
   acceptable before the system starts being ignored? Literature suggests this
   varies by individual and context.

### Recommended Next Steps

1. **Define the axiom schema**: ID, text, weight, hardcoded/softcoded, created date,
   supersedes, status (active/retired). File format: YAML or TOML in repo.

2. **Implement Layer 7 (precedent database)**: Design the case structure, decide on
   storage (Qdrant collection? JSONL file? SQLite?), implement retrieval.

3. **Build a prototype decomposition pipeline**: Take the "single user" axiom,
   run Layer 3 decomposition with self-consistency (N=3), review output, lock
   as versioned rules.

4. **Design the interpretive framework**: Which canons of construction will the
   system use? How are implications tiered (T0-T3)? Document explicitly.

5. **Instrument and measure**: Track false positive rate, operator override
   frequency, time spent on axiom adjudication. These are the health metrics
   of the enforcement system itself.

---

## References

### Papers
- Alexy, R. *A Theory of Constitutional Rights.* Oxford University Press, 2002.
- He, Nadeem, Liao, Chen, Chen, Cuellar, Henderson. "Statutory Construction for AI Constitutions." arXiv:2509.01186, 2025.
- Feng, Chen, Cheong, Xia, Zhang. "Case Repositories for AI Alignment." UW, 2025.
- Kolt, Caputo et al. "Legal Alignment for Safe and Ethical AI." Oxford/Stanford, 2026.
- Stone Sweet and Mathews. "Proportionality Balancing and Global Constitutionalism." Columbia J. Transnat'l L., 2008.
- Wang et al. "Self-Consistency Improves Chain of Thought Reasoning in Language Models." arXiv, 2022.
- arXiv 2408.04667. "Non-Determinism of Deterministic LLM Settings." 2024.
- arXiv 2512.03048. "Constitutional AI and the Is-Ought Gap." 2025.
- Natsios, A. "The Clash of the Counter-bureaucracy and Development." USAID, 2010.

### Systems and Frameworks
- Anthropic. "Claude's New Constitution." January 2026.
- Open Policy Agent (OPA). openpolicyagent.org
- Cedar Policy Language (AWS). docs.cedarpolicy.com
- NIST Cybersecurity Framework v2.0
- CIS Controls v8
- Neal Ford. *Building Evolutionary Architectures.* O'Reilly, 2nd ed.
- SEI/CMU. "The Architecture Tradeoff Analysis Method." CMU/SEI-98-TR-008.
- Architecture Decision Records. adr.github.io
