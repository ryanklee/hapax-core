# hapax-constitution

A governance architecture for LLM agent systems, specified as a pattern with two reference implementations.

## Problem

LLM agents that manage personal infrastructure — preparing meeting context, maintaining knowledge bases, monitoring system health, reacting to filesystem changes — accumulate autonomy without accumulating constraints. Prompt-level instructions are advisory. They degrade under context pressure, cannot be audited, and provide no mechanism for handling cases the author didn't anticipate.

Adding more rules does not solve this. Rules cover anticipated cases and fail silently on everything else.

This project specifies a governance architecture borrowed from constitutional law: weighted axioms (statutes), derived implications (case law), an interpretive canon (judicial reasoning methods), sufficiency probes (affirmative obligations, not only prohibitions), and a precedent store (stare decisis). The architecture is designed to handle unanticipated cases, not only anticipated ones.

## Design context

The two systems that implement this pattern externalize executive function into infrastructure. Their operator has ADHD and autism, which makes the cognitive cost of tracking open loops, maintaining relational context, and noticing staleness patterns acute. The underlying problem is general: knowledge workers perform executive function work that produces no deliverables, scales poorly with attention, and compounds when neglected. Agents doing this work require constraints that are structural, not advisory.

## The pattern

Four interlocking mechanisms compose the architecture.

### Filesystem-as-bus

Message queues, RPC, and shared databases each add infrastructure to operate, abstractions to debug through, and failure modes to handle. Filesystem-as-bus uses a different mechanism: all state lives as markdown files with YAML frontmatter on disk. Directories are collections. Agents read files to gather context and write files to produce output.

This trades transactional consistency and ordered delivery for: human-readable state (open any file in a text editor), git-native history (every state transition is a diff), tool-agnostic interoperability (any language reads markdown), zero-infrastructure coordination (no broker to run or monitor), and graceful degradation (if the engine is down, the data is still there and can be edited manually).

At single-operator scale with sequential or low-concurrency agent execution, the consistency trade-off has no practical cost.

The pattern predates and is now validated by two independent formalizations: "From Everything-is-a-File to Files-Are-All-You-Need" (arXiv:2601.11672, January 2026) and "Everything is Context: Agentic File System Abstraction for Context Engineering" (arXiv:2512.05470, December 2025). Unlike the virtual filesystem abstractions those papers propose, this pattern uses literal files on disk — debuggable with `cat`, `grep`, `diff`, and `git log`.

### Agent architecture

Three tiers, differentiated by invocation model and autonomy:

- **Tier 1 (Interactive):** Claude Code with MCP tools and system cockpit. Full operator supervision.
- **Tier 2 (On-demand):** Pydantic AI agents invoked by CLI, API, or Tier 1. Stateless per-invocation; all persistent state lives on the filesystem or in vector storage.
- **Tier 3 (Autonomous):** systemd timers running Tier 2 agents on schedules. High-frequency agents (health monitoring, knowledge maintenance) are deterministic with zero LLM calls.

Agents never invoke other agents. There is no orchestrator, no DAG, no workflow engine. Orchestration is flat. Agents communicate through filesystem artifacts, which decouples them temporally (agent A doesn't need to know when agent B runs) and makes the coordination graph auditable through standard Unix tools (`ls -lt` shows what ran, `git log` shows what changed, `diff` shows what was produced).

### Axiom governance

Constitutional axioms are weighted constraints defined in YAML. Each axiom produces derived implications at graduated enforcement tiers:

| Tier | Enforcement | Meaning |
|------|-------------|---------|
| T0 | Block | Existential violation. Code matching this pattern must not exist. |
| T1 | Review | Significant constraint. Requires operator awareness. |
| T2 | Warn | Quality preference. Should be followed absent reason not to. |

Each implication carries an **interpretive canon** — a classification borrowed from legal theory that governs how the implication is applied to unforeseen cases:

- **Textualist:** Apply the literal text. If the implication says "no auth," there is no auth.
- **Purposivist:** Apply the axiom's intent. If the purpose is reducing cognitive load, evaluate whether the code increases it.
- **Absurdity:** Reject literal application if the result contradicts the axiom's purpose.
- **Omitted-case:** The axiom is silent. Apply the nearest precedent or escalate to the operator.

The interpretive canon addresses a problem that formal constraint systems share with legal codes: specification cannot anticipate every case. Rather than expanding the specification indefinitely, the canon provides a principled method for applying existing axioms to new situations.

Each implication also carries a **mode** — either `prohibition` (the system must NOT do this) or `sufficiency` (the system MUST do this). Most governance systems check only for violations — they scan for the presence of bad things. Sufficiency probes invert this: they check for the *absence* of required things.

Example: the `executive_function` axiom (weight 95) produces the sufficiency implication "error messages must include a concrete next action." A prohibition-only system checks that error messages don't contain jargon. The sufficiency probe checks that every error message contains something actionable — a command to run, a file to check, a person to contact. This inversion is absent from the agent governance literature (ArbiterOS, ABC, PCAS, GaaS) as of early 2026.

The governance system also governs itself. The deliberative process — adversarial multi-round debates between agents over axiom tensions — is evaluated by sufficiency probes under `executive_function`. Four implications (ex-delib-001 through ex-delib-004) require that deliberations pass process-tracing hoop tests, maintain activation rates above threshold, avoid concession asymmetry, and show no sustained trend degradation. The evaluation mechanism is the same one used for all other governance concerns: implications define requirements, probes check compliance deterministically. No separate meta-governance layer was needed.

A **precedent store** records operator rulings on edge cases, building a common-law layer over time. When an axiom implication produces a tension — e.g., a domain-specific T0 block appears to conflict with a constitutional T0 block — the operator records a precedent: the reasoning, the resolution, and the scope. Future evaluations query the precedent store (via semantic search over embeddings) before escalating. New cases are evaluated against prior rulings. Precedents can be promoted (widened scope) or superseded (overruled). Over time, the precedent corpus makes axiom interpretation consistent and reduces operator interrupts.

### Reactive engine

An inotify watcher monitors the filesystem bus. File changes produce enriched events (including document type from YAML frontmatter). Rules — pure functions mapping events to actions — evaluate against each change. Multiple rules can fire; duplicate actions collapse.

Actions execute in phases:
- **Phase 0 (deterministic):** Cache refreshes, metric recalculation, file indexing. Unlimited concurrency. Zero cost.
- **Phase 1+ (LLM):** Synthesis, summarization, evaluation. Semaphore-bounded to prevent GPU saturation or API cost runaway.

**Self-trigger prevention:** when the engine writes an output file, inotify fires again. Without prevention, the engine evaluates its own output in an infinite loop. The engine tracks which files it has written and skips events from its own writes.

Notification delivery batches on a configurable interval to prevent storms.

## Axioms

Four axioms are defined in the registry. Two are constitutional (scope: all implementations). Two are domain-scoped.

| Axiom | Weight | Scope | Summary |
|-------|--------|-------|---------|
| `single_user` | 100 | Constitutional | One operator develops and uses the system. No auth, roles, or multi-user features. |
| `executive_function` | 95 | Constitutional | The system compensates for executive function challenges. Zero-config agents, actionable errors, automated routines, visible state. |
| `management_governance` | 85 | Domain: management | LLMs prepare context; humans deliver words to other humans. Never generate feedback language or coaching recommendations about individuals. |
| `corporate_boundary` | 90 | Domain: infrastructure | Work data stays in employer-controlled systems. Graceful degradation when home-only services are unreachable. |

The axioms produce 74+ derived implications across all tiers. See `axioms/implications/` for the full set.

## Implementations

Two systems implement this pattern. They share architecture, not code — each owns its full stack. They share infrastructure (Qdrant, LiteLLM, Ollama, PostgreSQL) but their agent pools, data directories, axiom registries, and reactive engines are independent. The constitution is the specification; the implementations are self-contained systems that happen to follow it.

**[hapax-council](https://github.com/ryanklee/hapax-council)** — Personal operating environment. 26+ agents across management, knowledge, sync, voice, and system domains. Always-on voice daemon with ambient perception. RAG pipeline ingesting 7 external sources into Qdrant. Natural language query subsystem with three specialized agents (development archaeology, system operations, knowledge search) auto-routed and served as SSE streams. Reactive cockpit with FastAPI API and React dashboard. Health monitoring, horizon scanning, documentation drift detection. Deliberation evaluation with metrics extraction and governance probes. Instantiates all four axioms.

**[hapax-officium](https://github.com/ryanklee/hapax-officium)** — Management-domain extraction, designed to be forked by other engineering managers. 16 agents for 1:1 preparation, team health tracking, management profiling, and briefings. Includes a self-demonstrating capability: bootstrap from synthetic seed data, and the system generates a demonstration — tailored to a profiled audience — against live operational state. Instantiates three axioms (`single_operator`, `decision_support`, `management_safety`). Officium was originally part of council and was extracted when the management agents proved usable without the rest of the system.

## Relationship to prior work

The constitutional pattern was designed in early 2026. Several independent formalizations of agent governance appeared in late 2025 and early 2026:

- **ArbiterOS** (arXiv:2510.13857, October 2025) — governance-first paradigm with non-bypassable "Arbiter Loop"
- **Agent Behavioral Contracts** (arXiv:2602.22302, February 2026) — Design by Contract for agent behavior with drift bound proofs
- **PCAS** (arXiv:2602.16708, February 2026) — policy compiler with reference monitor pattern, improving compliance from 48% to 93%
- **Governance-as-a-Service** (arXiv:2508.18765, August 2025) — modular enforcement with Trust Factor scoring

This pattern arrives at similar structural conclusions (governance separated from the governed, multi-layered enforcement, formal specification) but adds the interpretive canon, sufficiency probes, and personal axioms — mechanisms not present in the research literature.

The 1st Workshop on Operating Systems Design for AI Agents (AgenticOS, co-located with ASPLOS 2026) signals that the systems research community now formally recognizes agent scheduling, state management, and constraint enforcement as OS-level concerns.

## Contents

| Path | Contents |
|------|----------|
| [`pattern-guide.md`](pattern-guide.md) | Full architectural pattern with annotated code examples |
| [`agent-architecture.md`](agent-architecture.md) | Three-tier agent system design |
| [`operations-manual.md`](operations-manual.md) | Operational reference for running implementations |
| [`axioms/registry.yaml`](axioms/registry.yaml) | Axiom definitions (weights, scopes, types) |
| [`axioms/implications/`](axioms/implications/) | Derived implications per axiom (74+ total) |
| [`axioms/precedents/`](axioms/precedents/) | Precedent seeds for common-law interpretation |
| [`docs/design/`](docs/design/) | Design documents (deliberative governance, perception interface, governance primitives) |
| [`knowledge/`](knowledge/) | Sufficiency models (management, music, personal, technical) |
| [`domains/`](domains/) | Domain-specific extensions and life-domain registry |
| [`research/`](research/) | Management theory synthesis (Larson, Team Topologies, Scaling People) |

## License

Apache 2.0 — see [LICENSE](LICENSE).
