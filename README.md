# hapax-constitution

A written constitution for LLM agents.

A governance architecture for LLM-augmented systems. It defines constitutional axioms — weighted, enforceable constraints that bound what agents can build, suggest, and automate. Axioms produce derived implications (blocking rules), and a common-law precedent system handles edge cases that the axioms don't explicitly address.

This is a pattern specification, not a framework or library. It documents how to build agent platforms where governance is structural — enforced by tooling at commit time, not by prompt instructions at runtime.

## Why this exists

The systems that implement this constitution externalize executive function into infrastructure — LLM agents handle the cognitive overhead of management practice, knowledge maintenance, and daily operations that compounds silently for every knowledge worker. The developer who built them has ADHD and autism, which made the need acute, but the problem is general: tracking open loops, maintaining context across relationships, noticing staleness patterns, and reacting to changes are executive function and context processing tasks that scale poorly with human attention alone.

When a system manages your 1:1 prep, tracks your open loops, and nudges you about stale conversations, the constraints on what agents can and cannot do need to be explicit and enforceable:

- **Don't generate feedback language.** LLMs prepare context; humans deliver words to other humans.
- **Don't build multi-user features.** There is exactly one operator. No auth systems, role management, or collaboration features.
- **Don't require manual steps for routine work.** If the operator has to remember to run something, the system has failed at its core purpose.

These constraints are defined as axioms with weights, derived implications, and enforcement hooks that block violations at commit time.

## The pattern

Four interlocking architectural patterns form the constitution:

**Filesystem-as-Bus.** Markdown files with YAML frontmatter are the state bus. Directories are collections. Agents read and write files; a reactive engine watches for changes. No message queue, no database for state — human-readable files on disk, versioned by git.

**Agent Architecture.** Three tiers: interactive (Claude Code), on-demand (Pydantic AI agents invoked by CLI or API), autonomous (systemd timers on schedules). Flat orchestration — agents never call other agents. They communicate through the filesystem.

**Axiom Governance.** Constitutional constraints defined in YAML with explicit weights, scopes, and derived implications at three tiers: T0 (existential violations — code must not exist), T1 (behavioral constraints — code must behave this way), T2 (quality requirements — code should prefer this). A precedent store records edge-case rulings for consistency.

**Reactive Engine.** An inotify watcher monitors the filesystem bus. When files change, rules evaluate against the change and produce phased actions: deterministic work first (unlimited concurrency), then LLM work (semaphore-bounded). State changes on disk cascade automatically through the system.

See [`pattern-guide.md`](pattern-guide.md) for detailed explanations with annotated code examples.

## Implementations

Two systems implement this pattern. They share an architecture, not code — each owns its full stack.

**[hapax-council](https://github.com/ryanklee/hapax-council)** — The full personal operating environment. 26+ agents, voice daemon, RAG sync pipeline, reactive cockpit, Claude Code integration. Instantiates all five axioms including executive function accommodation.

**[hapax-officium](https://github.com/ryanklee/hapax-officium)** — A management decision support system designed to be forked and grown by individual engineering managers. 16 agents for 1:1 prep, team health tracking, management profiling, and briefings. Instantiates three axioms (single_operator, decision_support, management_safety). Includes a self-demonstrating capability: bootstrap from synthetic seed data, and the system demos itself — to an audience it profiles — against live operational state. Clone it, seed it with your team, and evolve it into your own management practice.

## Contents

| Path | What it is |
|------|-----------|
| [`pattern-guide.md`](pattern-guide.md) | **Start here.** The full architectural pattern with annotated code examples |
| [`agent-architecture.md`](agent-architecture.md) | Three-tier agent system design |
| [`operations-manual.md`](operations-manual.md) | Operational reference |
| [`axioms/`](axioms/) | Axiom definitions, derived implications, and precedent seeds |
| [`domains/`](domains/) | Domain-specific extensions and life-domain registry |
| [`knowledge/`](knowledge/) | Sufficiency models (management, music, personal, technical) |
| [`research/`](research/) | Management theory deep dives (Larson, Team Topologies, Scaling People) |

## License

Apache 2.0 — see [LICENSE](LICENSE).
