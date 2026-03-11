# Architectural Pattern Guide: Axiom-Governed Reactive Agent Platforms

## Overview

This document describes a generalizable architectural pattern for building LLM-augmented agent platforms governed by constitutional axioms. The core idea: markdown files with YAML frontmatter serve as a state bus on the filesystem. Agents read and write these files. A reactive engine watches the filesystem via inotify and triggers downstream work through rule evaluation and phased execution. Constitutional axioms constrain all agent behavior through a registry, derived implications, and a precedent store. The result is a system where state is human-readable, the event flow is auditable, and governance is structurally enforced rather than advisory.

This pattern has been implemented in two production systems and is designed for single-operator environments where the operator is also the developer. It works particularly well for decision-support systems, personal knowledge management, and autonomous infrastructure monitoring.

---

## Pattern 1: Filesystem-as-Bus

### Concept

The filesystem is the message bus. Each directory is a collection. Each markdown file is a document with structured metadata (YAML frontmatter) and unstructured content (markdown body). Agents read files to gather context and write files to produce output. The reactive engine watches for changes and triggers downstream processing.

This choice has concrete advantages over database-first approaches:

- **Human-readable state.** Every piece of system state can be opened in a text editor or viewed with `cat`. No query language required for debugging.
- **Git-native history.** The entire state bus is version-controlled. Every state transition is a diff.
- **Tool-agnostic.** Any language, any tool, any script can read and write markdown files. No client library required.
- **Graceful degradation.** If the reactive engine is down, the data is still there. Agents can run manually against the same files.

### Data Model

Every document on the bus follows this structure:

```markdown
---
type: person
name: Example Person
team: platform
status: active
last-1on1: 2026-03-01
cognitive-load: 3
check-in-by: 2026-03-15
---

# Example Person

Free-form markdown content follows the frontmatter.
Notes, context, history — whatever the document type calls for.
```

Key conventions:

- **Frontmatter keys are kebab-case** (`last-1on1`, `check-in-by`, `cognitive-load`). Python dataclass fields use snake_case after parsing.
- **The `type:` field is mandatory** and determines how the document is processed. Types map to directories: `person` documents live in `people/`, `meeting` documents in `meetings/`, etc.
- **Directory-as-collection.** Each subdirectory of the data directory is a logical collection. The watcher uses the subdirectory name to route events to the correct rules.

### Frontmatter Parsing

A single canonical parser handles all frontmatter extraction. Every consumer imports from this module — the regex is never duplicated.

```python
"""Canonical YAML frontmatter parsing.

Single source of truth for the frontmatter regex and parsing logic.
All consumers import from here. Never duplicate this regex.
"""
import re
import yaml
from pathlib import Path

# The canonical regex. Captures:
#   group(1) = raw YAML between the --- delimiters
#   group(2) = body text after the closing ---
_FM_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n?(.*)", re.DOTALL)


def parse_frontmatter_text(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown string.

    Returns (frontmatter_dict, body_text). On any error returns
    ({}, text) so callers always get usable values.
    """
    match = _FM_RE.match(text)
    if not match:
        return {}, text

    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text

    if not isinstance(fm, dict):
        return {}, text

    return fm, match.group(2)


def parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter from a markdown file on disk.

    Returns (frontmatter_dict, body_text). On any I/O or parse error
    returns ({}, "").
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, ""

    fm, body = parse_frontmatter_text(text)
    if not fm and not body:
        return {}, text
    return fm, body
```

Design notes:

- **Always returns usable values.** Parse failures return `({}, text)`, never raise. Callers can always destructure the result without error handling.
- **Two entry points.** `parse_frontmatter(path)` for files on disk, `parse_frontmatter_text(text)` for strings already in memory. The file version handles I/O errors; the text version is pure.
- **DOTALL regex.** The `re.DOTALL` flag makes `.` match newlines, so multi-line YAML frontmatter is captured correctly.

### Directory Layout

A typical data directory:

```
data/
├── people/              # Person documents (type: person)
├── meetings/            # Meeting notes (type: meeting)
├── decisions/           # Decision records (type: decision)
├── goals/               # Goal tracking (type: goal)
├── references/          # Generated artifacts (briefings, digests)
├── .gitkeep             # Tracked; all other contents gitignored
```

The `references/` directory is a convention for agent-generated output. Agents write here; humans rarely edit these files directly. The separation between input directories (people, meetings, decisions) and output directories (references) makes the data flow visible in the directory structure.

---

## Pattern 2: Agent Architecture

### Three-Tier System

Agents are organized into three tiers based on how they are invoked and how much autonomy they have:

```
┌──────────────────────────────────────────────────┐
│               TIER 1: INTERACTIVE                 │
│          Claude Code (operator ↔ LLM)             │
│       MCP servers · slash commands · hooks         │
│                                                    │
│           System Dashboard (web UI)                │
│        FastAPI backend + React SPA frontend         │
├──────────────────────────────────────────────────┤
│               TIER 2: ON-DEMAND                    │
│         Pydantic AI agents invoked by              │
│       Claude Code, CLI, or scheduled trigger        │
│                                                    │
│   LLM agents: prep, briefing, profiler, digest     │
│   Deterministic: activity, introspect, health      │
├──────────────────────────────────────────────────┤
│             TIER 3: AUTONOMOUS                     │
│      Always-running services or scheduled          │
│         timers (systemd / cron / etc.)             │
│                                                    │
│   health-monitor (15min), briefing (daily),        │
│   drift-detector (weekly), knowledge-maint         │
└──────────────────────────────────────────────────┘
```

**Tier 1 (Interactive)** is the operator's primary interface. Claude Code has full stack access and orchestrates everything else. A web dashboard provides real-time visibility.

**Tier 2 (On-Demand)** agents are invoked by Tier 1 or by timers. Each agent is a standalone Python module that reads from the bus, does work (possibly involving LLM calls), and writes results back to the bus or to a profiles directory. Agents never invoke each other — Tier 1 orchestrates all multi-agent workflows.

**Tier 3 (Autonomous)** agents run on schedules without operator intervention. They are Tier 2 agents wrapped in systemd timers or cron jobs. High-frequency autonomous tasks (health checks, maintenance) are deliberately deterministic — zero LLM calls — to control cost and avoid cascading failures.

### Agent Reading and Writing the Bus

A typical agent reads documents from the data directory, processes them, and writes output:

```python
"""Example: an agent that reads person documents and produces a team summary."""
from pathlib import Path
from frontmatter import parse_frontmatter

DATA_DIR = Path("data")

def collect_team_state(data_dir: Path = DATA_DIR) -> list[dict]:
    """Read all person documents and extract structured state."""
    people = []
    people_dir = data_dir / "people"
    if not people_dir.exists():
        return []

    for path in sorted(people_dir.glob("*.md")):
        fm, body = parse_frontmatter(path)
        if not fm or fm.get("type") != "person":
            continue
        if fm.get("status") == "inactive":
            continue

        people.append({
            "name": fm.get("name", path.stem),
            "team": fm.get("team", "unknown"),
            "last_1on1": fm.get("last-1on1"),        # kebab → snake
            "cognitive_load": fm.get("cognitive-load"),
            "check_in_by": fm.get("check-in-by"),
        })

    return people
```

Design notes:

- **Agents are stateless per-invocation.** All persistent state lives on the filesystem or in a vector database. An agent can be killed and restarted at any time.
- **Flat orchestration.** Agents never import or invoke other agents. Claude Code (Tier 1) is the only orchestrator. This keeps the call graph auditable and prevents cascading failures.
- **LLM calls route through a gateway.** All Tier 2/3 agents call LLMs through a proxy (e.g., LiteLLM) for cost tracking, observability, and model aliasing. Tier 1 (Claude Code) may call providers directly for latency.

### Model Aliasing

Agents reference logical model names, not raw provider model IDs:

```python
MODELS = {
    "fast": "claude-haiku",         # cheap, quick tasks
    "balanced": "claude-sonnet",    # default for most agents
    "reasoning": "deepseek-r1:14b", # complex reasoning (local)
    "coding": "qwen-coder-32b",    # code generation (local)
}
```

This decouples agents from specific models. When a better model ships, update the alias map — agents do not change.

---

## Pattern 3: Axiom Governance

### Concept

Axioms are constitutional constraints that govern all system behavior. They are not guidelines or best practices — they are structural rules enforced at development time and checked at runtime. The governance system has four components:

1. **Registry** — YAML definitions of active axioms with weights, scopes, and status.
2. **Implications** — Derived concrete requirements from each axiom, organized by tier and enforcement level.
3. **Precedent store** — A vector database of past axiom-application decisions, searchable by situation similarity.
4. **Agent tools** — Runtime compliance tools that LLM agents call during reasoning.

### Registry

Axioms are defined in a YAML registry:

```yaml
axioms:
  - id: single_operator
    text: >
      This system is developed for a single operator and by that single
      operator. All decisions must respect and leverage that fact.
    weight: 100
    type: hardcoded
    scope: constitutional
    status: active
    created: "2025-01-15"

  - id: decision_support
    text: >
      This system supports high-stakes decisions. It proactively surfaces
      context, open loops, and patterns so the operator can act with
      confidence. Recurring workflows must be automated.
    weight: 95
    type: hardcoded
    scope: constitutional
    status: active
    created: "2025-01-15"
```

The registry loader filters by status, scope, and domain:

```python
@dataclass
class Axiom:
    id: str
    text: str
    weight: int
    type: str          # "hardcoded" | "softcoded"
    created: str
    status: str        # "active" | "retired"
    supersedes: str | None = None
    scope: str = "constitutional"   # "constitutional" | "domain"
    domain: str | None = None       # None for constitutional


def load_axioms(
    *, path: Path, scope: str = "", domain: str = ""
) -> list[Axiom]:
    """Load active axioms from registry.yaml with optional filtering.

    Inactive and retired axioms are excluded. Scope and domain filters
    narrow results for domain-specific checks.
    """
    registry_file = path / "registry.yaml"
    if not registry_file.exists():
        return []

    data = yaml.safe_load(registry_file.read_text())

    axioms = []
    for entry in data.get("axioms", []):
        axiom = Axiom(
            id=entry["id"],
            text=entry.get("text", ""),
            weight=entry.get("weight", 50),
            type=entry.get("type", "softcoded"),
            created=entry.get("created", ""),
            status=entry.get("status", "active"),
            scope=entry.get("scope", "constitutional"),
            domain=entry.get("domain"),
        )
        if axiom.status != "active":
            continue
        if scope and axiom.scope != scope:
            continue
        if domain and axiom.domain != domain:
            continue
        axioms.append(axiom)

    return axioms
```

### Implications

Each axiom has derived implications — concrete requirements organized by enforcement tier:

- **T0 (Block):** Existential violations. Code matching these patterns must not be written. Enforced by SDLC hooks.
- **T1 (Review):** Significant decisions requiring operator awareness.
- **T2 (Warn):** Potential tensions surfaced during development.
- **T3 (Lint):** Style and convention preferences.

Implications also have a **mode**: compatibility (must not violate) or sufficiency (must actively support). This distinction matters — a system can be compatible with an axiom (not violating it) while failing to be sufficient (not actively advancing it).

```yaml
# implications/single-operator.yaml
axiom_id: single_operator
implications:
  - id: su-auth-001
    tier: T0
    enforcement: block
    mode: compatibility
    text: >
      All authentication, authorization, and operator management code
      must be removed or disabled. There is exactly one operator.
    canon: literal

  - id: su-feature-001
    tier: T0
    enforcement: block
    mode: compatibility
    text: >
      Features for operator collaboration, sharing, or multi-operator
      coordination must not be developed.
    canon: literal
```

### Supremacy Clause

Constitutional axioms always apply. Domain axioms inherit constitutional constraints. When a domain axiom has T0 blocks that overlap with constitutional T0 blocks, a supremacy validation surfaces these tensions for operator review:

```python
def validate_supremacy(*, path: Path) -> list[SupremacyTension]:
    """Check domain T0 blocks against constitutional T0 blocks.

    Returns pairings where a domain axiom operates in the same
    enforcement space as a constitutional axiom. These are not
    violations — they are structural overlaps that need explicit
    reasoning recorded as precedents.
    """
```

### Agent Tools for Runtime Compliance

LLM agents get two tools for runtime axiom compliance:

- **`check_axiom_compliance(situation, axiom_id, domain)`** — Searches the precedent store for similar prior decisions. Returns relevant precedents with reasoning and distinguishing facts. If no close precedent exists, returns axiom text and derived implications.
- **`record_axiom_decision(axiom_id, situation, decision, reasoning, tier)`** — Records a new axiom-application decision as precedent with `authority=agent` (pending operator review).

This creates a common-law-style governance system. Agents consult precedent before making decisions that touch axioms. Over time, the precedent store builds a body of applied reasoning that makes axiom interpretation consistent and auditable.

---

## Pattern 4: Reactive Engine

### Concept

The reactive engine closes the loop between filesystem state and agent work. When files change in the data directory, the engine detects the change, evaluates rules to determine what work is needed, and executes that work in phases with concurrency control. The pipeline:

```
inotify → debounce → ChangeEvent → rule evaluation → ActionPlan → phased execution
```

### Watcher

The watcher uses inotify (via watchdog on Linux) to detect file changes recursively in the data directory. It handles several concerns:

- **Debouncing.** Rapid writes (e.g., editor save → format → save) are collapsed into a single event. A configurable debounce window (default 200ms) ensures only the final state triggers processing.
- **Self-trigger prevention.** When the engine itself writes files (agent output), those writes must not trigger re-evaluation. An ignore set tracks paths that the engine has written, suppressing their next inotify event.
- **Document type extraction.** On non-delete events, the watcher reads YAML frontmatter to extract the `type:` field, enriching the ChangeEvent for rule matching.

```python
@dataclass
class ChangeEvent:
    """Detected filesystem change in the data directory."""
    path: Path
    subdirectory: str       # First-level directory (e.g., "people", "meetings")
    event_type: str         # "created" | "modified" | "deleted"
    doc_type: str | None    # From YAML frontmatter type: field
    timestamp: datetime
```

The watcher bridges from the watchdog thread to the asyncio event loop using `call_soon_threadsafe`, ensuring thread safety without locks:

```python
def _handle(self, event: FileSystemEvent) -> None:
    if event.is_directory:
        return
    path = Path(str(event.src_path))
    if _is_filtered(path, self._data_dir):
        return
    # Bridge from watchdog thread to asyncio event loop
    self._loop.call_soon_threadsafe(self._schedule_debounce, path, event_type)
```

### Rule Evaluation

Rules map ChangeEvents to ActionPlans. Each rule has a trigger filter (predicate) and a produce function (action generator):

```python
@dataclass
class Rule:
    """A single rule mapping a ChangeEvent pattern to actions."""
    name: str
    trigger_filter: Callable[[ChangeEvent], bool]
    produce: Callable[[ChangeEvent], list[Action]]
    description: str = ""


def evaluate_rules(registry: RuleRegistry, event: ChangeEvent) -> ActionPlan:
    """Evaluate all rules against an event.

    - Iterates rules, calls trigger_filter for each
    - Collects actions from matching rules via produce()
    - Deduplicates actions by name (first one wins)
    - Catches and logs exceptions without aborting
    """
    actions: list[Action] = []
    seen_names: set[str] = set()

    for rule in registry.rules:
        try:
            if not rule.trigger_filter(event):
                continue
        except Exception:
            continue  # Log and skip — never abort on a rule failure

        produced = rule.produce(event)
        for action in produced:
            if action.name not in seen_names:
                seen_names.add(action.name)
                actions.append(action)

    return ActionPlan(trigger=event, actions=actions)
```

Design notes:

- **Rules are pure functions.** The trigger filter and produce callable are stateless. Rules do not modify the event or share mutable state.
- **Deduplication by action name.** Multiple rules can fire on the same event, but duplicate actions (same name) are collapsed. First registration wins.
- **Exception isolation.** A failing rule never blocks other rules from evaluating. Errors are logged and skipped.

### Phased Execution

Actions are grouped by phase and executed with concurrency control:

```python
@dataclass
class Action:
    """Unit of work to be executed by the engine."""
    name: str
    handler: Callable       # async callable
    args: dict = field(default_factory=dict)
    phase: int = 0          # 0 = deterministic, 1+ = LLM
    depends_on: list[str] = field(default_factory=list)


@dataclass
class PhasedExecutor:
    """Execute an ActionPlan phase-by-phase with concurrency control."""
    llm_concurrency: int = 2
    action_timeout_s: float = 60.0

    async def execute(self, plan: ActionPlan) -> None:
        """Run all actions in the plan, phase by phase."""
        phases = plan.actions_by_phase()
        for phase_num in sorted(phases):
            actions = phases[phase_num]
            async with asyncio.TaskGroup() as tg:
                for action in actions:
                    tg.create_task(self._run_action(action, plan, phase_num))
```

The phased model separates deterministic work from LLM work:

- **Phase 0 (deterministic):** Cache refreshes, metric recalculations, file indexing. Unlimited concurrency. Fast. No cost.
- **Phase 1+ (LLM):** Synthesis, summarization, evaluation. Bounded by a semaphore (default concurrency: 2). This prevents GPU/API saturation when multiple events fire simultaneously.

Dependencies between actions are tracked explicitly. If a dependency fails or is skipped, downstream actions are skipped automatically:

```python
async def _run_action(self, action, plan, phase):
    # Check dependencies
    if any(dep in plan.errors or dep in plan.skipped
           for dep in action.depends_on):
        plan.skipped.add(action.name)
        return

    if phase >= 1:
        async with self._llm_semaphore:
            result = await asyncio.wait_for(
                action.handler(**action.args),
                timeout=self.action_timeout_s,
            )
    else:
        result = await asyncio.wait_for(
            action.handler(**action.args),
            timeout=self.action_timeout_s,
        )
    plan.results[action.name] = result
```

### Delivery

The final stage batches notifications. Rather than sending a notification for every completed action, the engine accumulates DeliveryItems and flushes them on a configurable interval (default: 5 minutes). This prevents notification storms when many files change at once (e.g., during bootstrap or bulk import).

---

## Existence Proofs

This architectural pattern has been implemented in two published systems:

### hapax-council (Personal LLM Operating Environment)

A personal LLM-augmented operating environment. The full stack: 16 Docker services, 25+ agents spanning RAG sync, voice interaction, audio processing, profile management, and infrastructure self-regulation. Extends the pattern with voice modality (wake word detection, speaker ID, screen awareness), continuous audio processing, and Google Workspace sync pipelines.

The system is specifically designed around ADHD/autism and executive function support — the `executive_function` axiom governs accommodation patterns, proactive nudges, and cognitive load management throughout the agent architecture.

Repository: [https://github.com/ryanklee/hapax-council](https://github.com/ryanklee/hapax-council)

### hapax-officium (Management Decision Support)

A management cockpit for engineering managers. Agents prepare context for 1:1s, track management practice patterns, surface stale conversations and open loops, and profile the operator's management self-awareness. Includes a React dashboard, 16 agents, a reactive engine with 12 rules, and a demo seed system that produces fully-hydrated replicas with synthetic data.

Safety principle: "LLMs prepare, humans deliver." The system never generates feedback language, coaching recommendations, or evaluations of individual team members. This boundary is enforced as a constitutional axiom (`management_safety`, weight 95) with T0 blocking implications.

Repository: [https://github.com/ryanklee/hapax-officium](https://github.com/ryanklee/hapax-officium)

### Relationship Between Implementations

These are **forks, not libraries**. The shared code (~4,200 LOC, 25 modules) is residue of a common origin, not a library trying to get out. What is actually common is the architectural pattern documented here — axiom-governed reactive agent platform with filesystem-as-bus — not the code itself. Each system owns its full stack and evolves independently.
