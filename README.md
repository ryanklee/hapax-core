# hapax-constitution

Architectural pattern documentation for axiom-governed reactive agent platforms.

hapax-constitution defines the reference architecture — a constitutional governance framework where LLM agents operate under explicit axioms, communicate through a filesystem-as-bus, and react to state changes through a phased execution engine.

## Contents

- `pattern-guide.md` — **Start here.** Generalized architectural pattern with annotated code examples
- `agent-architecture.md` — Three-tier agent system design (interactive, on-demand, autonomous)
- `operations-manual.md` — Operational reference for running the platform
- `axioms/` — Axiom definitions (`registry.yaml`), derived implications, and precedent seeds
- `domains/` — Domain-specific extensions and life-domain registry
- `knowledge/` — Sufficiency models (management, music, personal, technical)
- `research/` — Management theory deep dives (Larson, Team Topologies, Scaling People)
- `docs/` — Design documents, audit reports, and implementation plans

## The Pattern

Four interlocking patterns form the architecture:

1. **Filesystem-as-Bus** — Markdown files with YAML frontmatter are the state bus. Directories are collections. Agents read and write the bus; the reactive engine watches for changes.
2. **Agent Architecture** — Three tiers: interactive (Claude Code), on-demand (Pydantic AI agents), autonomous (systemd timers). Flat orchestration, no agent-to-agent calls.
3. **Axiom Governance** — Constitutional constraints defined in YAML, enforced through compatibility/sufficiency implications, with a common-law precedent system for edge cases.
4. **Reactive Engine** — inotify watcher triggers rule evaluation, which produces phased actions: deterministic work first (unlimited), then LLM work (semaphore-bounded).

See `pattern-guide.md` for detailed explanations with annotated code examples.

## Existence Proofs

Two systems implement this pattern:

- **[hapax-council](https://github.com/ryanklee/hapax-council)** — Full operational implementation: reactive cockpit, voice daemon, sync pipeline, Claude Code integration. Instantiates all five axioms including executive function accommodation.
- **[hapax-officium](https://github.com/ryanklee/hapax-officium)** — Management domain instantiation: decision support, team health tracking, management profiling. Instantiates a subset of axioms (single_operator, decision_support, management_safety).

The two systems share an architectural pattern, not code. Each owns its full stack. See the [pattern guide](pattern-guide.md#existence-proofs) for the rationale.

## License

Apache 2.0 — see [LICENSE](LICENSE).
