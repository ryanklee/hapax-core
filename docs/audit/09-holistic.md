# Holistic Audit — Cross-Domain Findings

**Audited**: 2026-03-02
**Scope**: Entire three-tier agent system examined through 5 cross-cutting lenses
**Inputs**: 8 domain audit findings (01-08), all source files in `<ai-agents>/`, `<cockpit-web>/`, `<obsidian-hapax>/`, `<llm-stack>/`

---

## Context

The 8 domain-specific audits examined individual components in isolation. This holistic pass examines how those components compose into a system — and whether that system actually serves its stated purpose as externalized executive function for an operator with ADHD and autism.

The operator is not a user; the operator is a component. The human-system boundary is a system interface subject to the same design discipline as any other interface.

---

## Finding Summary

| # | Severity | Lens | Finding |
|---|----------|------|---------|
| H-1.1 | HIGH | coherence | 5 of 9 LLM agents lack neurocognitive awareness in their system prompts |
| H-1.2 | HIGH | coherence | Digest agent has no context tools — cannot look up operator constraints on demand |
| H-1.3 | MEDIUM | coherence | Briefing system prompt contradicts operator model — "technical and wants precision" without neurocognitive framing |
| H-1.4 | MEDIUM | coherence | Obsidian plugin has separate identity model disconnected from Python SYSTEM_CONTEXT |
| H-2.1 | HIGH | unity | `profile-facts` Qdrant collection invisible to knowledge maintenance, health monitor, and digest |
| H-2.2 | MEDIUM | unity | PROFILES_DIR defined independently in 3 modules instead of single import |
| H-2.3 | MEDIUM | unity | Scout agent bypasses shared.notify — desktop-only, no mobile push |
| H-2.4 | MEDIUM | unity | Two parallel Qdrant profile storage paths coexist without migration plan |
| H-2.5 | LOW | unity | VAULT_PATH independently computed in 3 modules from same env var |
| H-3.1 | HIGH | flow | Decision capture only records "executed" — dismissed and expired nudges produce no signal |
| H-3.2 | MEDIUM | flow | Operator input through web dashboard is impossible — read-only with no action pathway |
| H-3.3 | MEDIUM | flow | Micro-probe cooldown does not survive process restart — probes re-fire immediately |
| H-3.4 | MEDIUM | flow | Accommodation state has no feedback loop to validate effectiveness |
| H-3.5 | LOW | flow | Profile → agent behavior path is pull-only — agents never re-read profile mid-conversation |
| H-4.1 | MEDIUM | purpose | InfraPanel and ScoutPanel widgets exist but are not mounted in any screen |
| H-4.2 | MEDIUM | purpose | `store_to_qdrant()` (claude-memory) is legacy code with an active CLI flag but no consumers |
| H-4.3 | LOW | purpose | 8 micro-probes all target neurocognitive_profile — 12 other dimensions get zero probe coverage |
| H-5.1 | HIGH | interface | No typed contract between Python dataclasses and TypeScript interfaces — 4 endpoints missing types entirely |
| H-5.2 | MEDIUM | interface | Nudge attention budget is uncapped — system can present unbounded nudges per session |
| H-5.3 | MEDIUM | interface | Three operator channels (TUI, web, Obsidian) have incompatible capability sets with no feature parity documentation |
| H-5.4 | LOW | interface | Agent error reporting to operator is absent — all failures are silent null/empty responses |

**Totals**: 5 HIGH, 12 MEDIUM, 4 LOW

---

## Lens 1: Coherence — Does the System Agree on What It Is?

The system's founding assertion is in `shared/operator.py:8-12`:

```python
SYSTEM_CONTEXT = """\
System: Externalized executive function infrastructure for a single operator.
The operator has ADHD and autism — task initiation, sustained attention, and \
routine maintenance are genuine cognitive challenges...
"""
```

This is the ground truth. Every component that interacts with the operator should behave as though this is true. The question is whether they do.

### H-1.1 — HIGH: 5 of 9 LLM agents lack neurocognitive awareness in system prompts

**Evidence:**

`get_system_prompt_fragment()` in `shared/operator.py` builds a Tier 0 context that includes neurocognitive accommodations. Only 4 agents call it:

| Agent | Uses `get_system_prompt_fragment()`? | Has context tools? |
|-------|--------------------------------------|-------------------|
| `research.py` | Yes (line 41) | Yes (line 73) |
| `code_review.py` | Yes (line 33) | Yes (line 58) |
| `chat_agent.py` | Yes (line 61) | Yes (line 88) |
| `interview.py` | Yes (implicit via chat) | Yes (line 424) |
| `briefing.py` | **No** — static prompt | Yes (line 110) |
| `scout.py` | **No** — static prompt | Yes (line 236) |
| `management_prep.py` | **No** — static prompts (3 agents) | Yes (line 136) |
| `drift_detector.py` | **No** — static prompt | Yes (line 124) |
| `digest.py` | **No** — static prompt | **No** |

The 5 agents with static prompts describe the operator generically ("technical and wants precision") or not at all. They have context tools for on-demand lookup, but:

1. Context tools are pull-based — the agent must decide to call them. An agent with no neurocognitive awareness in its system prompt has no reason to call `lookup_constraints()` about ADHD accommodations.
2. The briefing agent generates daily output that the operator reads every morning. If the briefing doesn't account for executive function challenges in how it structures information, it's failing at its core purpose.
3. Management prep generates material for high-stakes human interactions. The prompts mention "the operator is an experienced manager" but not that they have specific cognitive needs around information density and task initiation.

**So what**: The system has a coherent operator model in theory (`SYSTEM_CONTEXT`) but an incoherent one in practice. The agents most likely to surface during autonomous Tier 3 operation (briefing, scout, digest, drift) are the ones that don't know who they're serving.

---

### H-1.2 — HIGH: Digest agent has no context tools

**File**: `agents/digest.py:179-183`

```python
digest_agent = Agent(
    get_model("fast"),
    system_prompt=SYSTEM_PROMPT,
    output_type=Digest,
)
```

No `get_context_tools()` registration follows. Every other LLM agent in the system registers context tools. The digest agent cannot look up operator constraints, patterns, or profile even if its model wanted to.

This was noted in domain audit 5 (finding C-5.1) but the holistic implication is larger: the digest is consumed by the briefing agent (`agents/briefing.py:42` reads `profiles/digest.json`). A digest that doesn't understand the operator's information processing preferences produces content that the briefing agent then has to present — potentially in a format that doesn't serve the operator's neurocognitive needs.

**So what**: The information supply chain (digest -> briefing -> operator) has a context-blind link at the start.

---

### H-1.3 — MEDIUM: Briefing system prompt contradicts operator model

**File**: `agents/briefing.py:79-104`

```python
SYSTEM_PROMPT = """\
You are a daily briefing generator for a personal AI infrastructure stack.
...
The operator is technical and wants precision, not filler.
"""
```

This describes one attribute of the operator ("technical and wants precision") while omitting the defining characteristic (ADHD, autism, executive function challenges). A briefing agent that thinks it's serving a generic technical user will:

- Present information in whatever order seems logical, rather than prioritizing by actionability (executive function support)
- Not consider cognitive load in how many items it surfaces
- Not apply the energy-aware time patterns that the accommodation system defines

The briefing agent does register context tools (line 110), so it *could* query `lookup_constraints()` during generation. But its system prompt gives it no reason to suspect those constraints exist.

---

### H-1.4 — MEDIUM: Obsidian plugin has separate identity model

**File**: `<obsidian-hapax>/src/types.ts` (DEFAULT_SETTINGS.systemPrompt)

```typescript
systemPrompt: `You are Hapax, an assistant embedded in the operator's Obsidian vault...`
```

This is a separate identity ("Hapax") with a separate personality description. The Python system uses `SYSTEM_CONTEXT` which says "externalized executive function infrastructure." The Obsidian plugin is a direct operator interface but doesn't share the system's self-understanding.

The plugin does load dynamic context from `30-system/hapax-context.md` on every message (confirmed in `chat-view.ts:135`), which can provide operator context. But the base identity is disconnected — it's a different character with different framing.

**Mitigating factor**: The vault context file can be updated to include the neurocognitive model. But the default system prompt in `types.ts` is what new installations get, and it doesn't mention executive function, ADHD, or autism.

---

## Lens 2: Unity — One System or Several?

### H-2.1 — HIGH: `profile-facts` Qdrant collection invisible to maintenance

**Files**:
- `shared/profile_store.py:27` — defines `COLLECTION = "profile-facts"`
- `agents/knowledge_maint.py:41` — `COLLECTIONS = ["documents", "samples", "claude-memory"]`
- `agents/health_monitor.py:81` — `REQUIRED_QDRANT_COLLECTIONS = {"documents", "samples", "claude-memory"}`
- `agents/digest.py:68` — `COLLECTIONS = ["documents", "samples", "claude-memory"]`

The `ProfileStore` introduced during the context management refactoring writes to a new `profile-facts` collection. But the three agents responsible for system hygiene — knowledge maintenance, health monitoring, and content digest — don't know it exists.

Consequences:
1. **Knowledge maintenance** (`knowledge_maint.py`) will never prune stale facts, detect duplicates, or verify dimensions in `profile-facts`. The collection grows without bound.
2. **Health monitor** will never check whether `profile-facts` exists or is healthy. If the collection is corrupted or deleted, no alert fires.
3. **Digest** won't report `profile-facts` statistics. The operator has no visibility into collection size or growth rate.

**So what**: A new component was added to the system but the existing maintenance infrastructure wasn't updated to know about it. The `profile-facts` collection is an unmonitored, unmaintained data store that will accumulate without hygiene.

---

### H-2.2 — MEDIUM: PROFILES_DIR defined independently in 3 modules

**Files**:
- `shared/config.py:26` — `PROFILES_DIR: Path = Path(__file__).resolve().parent.parent / "profiles"` (canonical)
- `cockpit/accommodations.py:17` — `PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"` (independent)
- `shared/management_bridge.py:19` — `PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"` (independent)

The canonical definition is in `shared/config.py`. Most modules import from there (27 import sites across the codebase). But `accommodations.py` and `management_bridge.py` define their own copies using the same relative path computation.

Today all three resolve to the same directory because the files are in the expected positions. But this is a structural fragility — if the package layout changes, the canonical import will track the change while the two independent definitions may diverge silently.

**Contrast**: `VAULT_PATH` has a similar pattern (computed independently in `vault_writer.py`, `management.py`, and `management_bridge.py`), but all three read from the `OBSIDIAN_VAULT_PATH` environment variable with the same default, making divergence less likely. Still, the principle of single source of truth is violated in both cases.

---

### H-2.3 — MEDIUM: Scout bypasses shared notification infrastructure

**File**: `agents/scout.py:467-483`

```python
def send_notification(report: ScoutReport) -> None:
    ...
    subprocess.run(
        ["notify-send", "--app-name=LLM Stack", "Horizon Scan", f"{summary}\n{body}"],
        timeout=5,
        capture_output=True,
    )
```

The system has a unified notification module (`shared/notify.py`) that sends via ntfy (mobile push) with fallback to desktop notify-send. The briefing agent (`briefing.py`), digest agent (`digest.py`), and knowledge maintenance agent (`knowledge_maint.py`) all use it correctly.

The scout agent defines its own `send_notification()` function that calls `notify-send` directly. This means:
1. Scout notifications are desktop-only — they don't reach mobile via ntfy
2. If the operator is away from the desk when the weekly scout runs (Wed 10:00), they never see the results
3. The unified notification path's priority mapping and tag system are bypassed

**So what**: The scout is the agent responsible for evaluating whether the system's components are still the best choice. If its output doesn't reach the operator through all channels, the "external fitness" signal has a delivery failure.

---

### H-2.4 — MEDIUM: Two parallel Qdrant profile storage paths

**Files**:
- `agents/profiler.py:1018-1045` — `store_to_qdrant()` writes to `claude-memory` collection
- `shared/profile_store.py:27` — `ProfileStore` writes to `profile-facts` collection
- `agents/profiler.py:1793-1798` — `run_auto()` calls `ProfileStore.index_profile()` (new path)
- `agents/profiler.py:1825` — `--store-qdrant` CLI flag calls `store_to_qdrant()` (legacy path)

The `run_auto()` pipeline (called by the 12h profile-update timer) uses the new `profile-facts` path. The `--store-qdrant` CLI flag uses the legacy `claude-memory` path. Both write profile data to Qdrant but to different collections with different schemas.

Context tools (`shared/context_tools.py`) read from `profile-facts` via `ProfileStore`. Nothing reads profile data from `claude-memory` programmatically (it was the original MCP memory store, now semantically overloaded).

**So what**: There's no migration plan. The old path is still accessible and actively offered as a CLI flag, but nothing consumes its output. A developer running `--store-qdrant` would write to the wrong collection and see no effect.

---

### H-2.5 — LOW: VAULT_PATH independently computed in 3 modules

**Files**:
- `shared/vault_writer.py:28` — `VAULT_PATH = Path(os.environ.get("OBSIDIAN_VAULT_PATH", ...))`
- `cockpit/data/management.py:17` — `VAULT_PATH = Path(os.environ.get("OBSIDIAN_VAULT_PATH", ...))`
- `shared/management_bridge.py:52` — reads `OBSIDIAN_VAULT_PATH` inline in function

All three read the same environment variable with the same default. The duplication is structural (same pattern as H-2.2) but lower risk because the env var provides a single source of truth at runtime. Noted for consistency: a single canonical `VAULT_PATH` import would eliminate the pattern.

---

### Parallel Approach Checks

#### Embedding consistency

**Expected**: All embedding calls route through `shared/config.py:embed()` and `embed_batch()`.

**Actual**:
- `shared/config.py` — canonical `embed()` (line 66) and `embed_batch()` (line 88), both call `ollama.embed()` with `EMBEDDING_MODEL = "nomic-embed-text-v2-moe"` and proper prefix handling.
- `shared/profile_store.py` — uses `from shared.config import embed_batch` (line 62) and `from shared.config import embed` (line 124). Correct.
- `cockpit/chat_agent.py` — uses `from shared.config import ... embed` (line 19). Correct.
- `agents/profiler.py` — uses `from shared.config import ... embed` (line 34). Correct.
- `agents/research.py` — uses `from shared.config import ... embed` (line 14). Correct.
- `rag-pipeline/ingest.py` — defines its **own** `embed()` function (line 107-112) that calls `ollama.embed()` directly. Does NOT import from `shared/config.py`. This is a separate repo with its own venv, so it cannot import `shared.config`.
- `obsidian-hapax/src/qdrant-client.ts` — defines its own `embed()` method (line 18) that calls Ollama's `/api/embed` HTTP endpoint directly. This is TypeScript/Obsidian — it correctly hardcodes `"nomic-embed-text-v2-moe"` and applies the `"search_query: "` prefix.

**Verdict**: Within the Python `ai-agents` repo, embedding is fully centralized through `shared/config.py`. The two exceptions (`rag-pipeline` and `obsidian-hapax`) are separate repos/languages that cannot import from `shared/config`. Both hardcode the same model name and apply the same prefix convention. The risk is model name drift — if the embedding model changes, three locations need updating (`shared/config.py`, `ingest.py:43`, `qdrant-client.ts:24`).

#### Configuration sources

**Expected**: Configuration flows from a single source of truth.

**Actual**: Three distinct configuration layers exist:

1. **`shared/config.py`** — Model aliases (`MODELS` dict), `EMBEDDING_MODEL`, `PROFILES_DIR`, `QDRANT_URL`. These are code-level constants + environment variable reads (`LITELLM_API_BASE`, `LITELLM_API_KEY`, `QDRANT_URL`).
2. **`.envrc`** — Runtime secrets and service URLs loaded via `direnv`. Contains `LITELLM_API_KEY` (from `pass`), `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `TAVILY_API_KEY`, `OBSIDIAN_VAULT_PATH`. These are environment variables consumed by `config.py` and other modules.
3. **`profiles/operator.json`** — Operator identity, axioms, constraints, patterns, goals, neurocognitive profile, agent context map. Read by `shared/operator.py` and cached. This is the operator manifest — it defines *who* the system serves, not *how* it runs.

**Verdict**: These are not three competing sources — they serve different purposes. `config.py` handles infrastructure (how to connect to services), `.envrc` handles secrets (credentials), `operator.json` handles identity (who the operator is). The separation is intentional and appropriate. The only overlap is `OBSIDIAN_VAULT_PATH` which is in `.envrc` and independently read by 3 modules (H-2.5). No conflicting values were found.

#### Naming conventions

**Expected**: Consistent naming across Python/TypeScript/YAML.

**Actual**:
- **Python**: `snake_case` throughout — module names (`chat_agent.py`, `profile_store.py`), function names, variable names. Profile dimensions use `snake_case` (`neurocognitive_profile`, `team_leadership`). Profile fact keys use `snake_case` (enforced by profiler prompts: "Use snake_case keys"). Consistent.
- **TypeScript** (obsidian-hapax): `camelCase` for variables/functions, `PascalCase` for interfaces/types (`HapaxSettings`, `ChatMessage`, `QdrantSearchResult`). Standard TypeScript conventions. Consistent within the TS codebase.
- **YAML** (`component-registry.yaml`): `kebab-case` for component names (`embedding-model`, `vector-database`), `snake_case` for field names (`search_hints`, `eval_notes`). This is a minor inconsistency — the component keys use kebab-case while the property keys use snake_case.
- **systemd units**: `kebab-case` for service/timer names (`health-monitor.timer`, `daily-briefing.service`). Standard systemd convention.
- **File names**: Python files use `snake_case`, TypeScript files use `kebab-case` (`chat-view.ts`, `qdrant-client.ts`). Both follow their ecosystem conventions.

**Verdict**: Each language ecosystem follows its own convention correctly. The only cross-boundary naming issue is that Python profile dimensions use `snake_case` (`neurocognitive_profile`) while YAML component names use `kebab-case` (`embedding-model`). This is cosmetic — no code crosses this boundary programmatically.

---

## Lens 3: Flow — Does Data Move Without Breaks?

### H-3.1 — HIGH: Decision capture only records "executed" actions

**File**: `cockpit/app.py:386-398`

```python
@on(ActionItemsList.ActionItemSelected)
def _on_action_item_selected(self, event):
    nudge = event.item
    record_decision(Decision(
        timestamp=datetime.now(timezone.utc).isoformat(),
        nudge_title=nudge.title,
        nudge_category=nudge.category,
        action="executed",
        context=nudge.command_hint or "",
    ))
```

The `Decision` dataclass defines three possible actions: `"executed"`, `"dismissed"`, `"expired"` (see `cockpit/data/decisions.py:25`). But the only call site in the codebase always passes `action="executed"`. There is no code path that records a dismissed or expired nudge.

This means the profiler (which reads `decisions.jsonl` via `profiler_sources.py:559`) only sees what the operator chose to do — never what they chose to ignore. For an operator with ADHD, the pattern of ignored nudges is arguably *more* informative than the pattern of executed ones:
- Consistently dismissed health nudges might indicate the operator has learned to work around the issue
- Expired nudges might indicate task initiation difficulty — the system surfaced something actionable but the operator couldn't start it
- A pattern of "all dismissed during afternoon hours" would validate the energy-aware accommodation

Without dismissal and expiry data, the profile's behavioral understanding is one-dimensional.

**So what**: The decision capture infrastructure exists and is wired end-to-end (cockpit -> JSONL -> profiler_sources -> profiler extraction). But it captures only one third of the signal it was designed for. The flow exists but carries impoverished data.

---

### H-3.2 — MEDIUM: Web dashboard has no action pathway

**Files**: `cockpit-web/src/components/Sidebar.tsx`, `cockpit-web/src/components/MainPanel.tsx`

The web dashboard (Domain 7) is read-only. It renders nudges, health status, VRAM, goals, and agent grid — but the operator cannot:
- Execute a nudge command
- Dismiss a nudge
- Launch an agent
- Send a chat message
- Respond to a micro-probe

Every operator action requires switching to the TUI or command line. For an operator with ADHD, the cognitive cost of context-switching between interfaces is significant. The web dashboard surfaces attention-demanding information (nudges with "you should do X") without providing the affordance to act on it.

**Contrast**: The TUI has `ActionItemsList.ActionItemSelected` which records a decision and executes the command. The web dashboard has no equivalent interaction.

**So what**: The web dashboard creates attention demand without providing action resolution. For the documented operator profile, this is a net negative — it surfaces cognitive load without reducing it.

---

### H-3.3 — MEDIUM: Micro-probe cooldown does not survive restart

**File**: `cockpit/micro_probes.py`

The `MicroProbeEngine` tracks a `_last_probe_time` using `time.monotonic()` (a relative clock). The cooldown (600 seconds) prevents re-probing too soon. But `time.monotonic()` resets on process restart, so the cooldown is lost whenever the TUI is restarted.

The `asked_topics` set *is* persisted to `<cache>/cockpit/probe-state.json`, so a topic won't be re-asked forever. But the time-based cooldown between any probes is ephemeral.

For the operator: frequent TUI restarts (which happen during development or after crashes) will cause probes to fire immediately on startup, adding cognitive load at exactly the moment the operator is trying to get oriented.

**So what**: A system designed for ADHD accommodation has a mechanism that can create unwanted interruptions during the already-costly process of reorienting after a restart.

---

### H-3.4 — MEDIUM: Accommodation state has no effectiveness feedback loop

**Files**: `cockpit/accommodations.py`, `cockpit/data/decisions.py`

The accommodation system proposes behavior changes (time anchoring, soft framing, energy-aware nudge reduction) that the operator confirms. Once active, these accommodations modify system behavior. But:

1. No mechanism measures whether the accommodation is working (e.g., did energy-aware nudge reduction lead to better nudge engagement during low-energy hours?)
2. No mechanism deactivates an accommodation that isn't helping
3. The accommodation's effect is invisible in the decision log (decisions don't record whether they occurred during an accommodated period)

The profiler reads decisions but has no way to correlate decision patterns with accommodation states. The accommodations are a one-way configuration — set and forget, never evaluated.

**So what**: Accommodations are the system's most direct expression of neurocognitive awareness, but they operate open-loop. For a system that aspires to externalized executive function, the accommodation layer should be the most instrumented part — instead it's the least.

---

### H-3.5 — LOW: Profile influences agent behavior only at conversation start

**Files**: `shared/context_tools.py`, all agents with context tool registration

Context tools are registered as Pydantic AI tools. Agents call them during a conversation to look up operator constraints or patterns. But:

1. Profile data is read on-demand per tool call — there's no mechanism for a long conversation to be interrupted by a profile update
2. If the profiler runs while a briefing is being generated, the briefing won't see the new profile data until the next generation cycle

This is acceptable for most agents (which run once and exit). But the cockpit chat agent can run for extended sessions. If the operator provides a correction via `/profile correct` that changes their accommodation preferences, the current chat session won't see it.

**So what**: Minor flow delay, not a break. The eventual consistency is adequate for all current use cases.

---

### Flow Traces

The following 7 flows were traced through source code to verify end-to-end operation. Three additional flows (nudge -> decision capture, web dashboard interaction, probe cooldown) were already addressed by findings H-3.1, H-3.2, and H-3.3 above.

#### Operator -> System Flows

**1. Vault inbox note -> RAG -> profiler -> profile updated?**

Traced through 3 codebases:

1. `ingest.py:33-37` — Config watches `<personal-vault>/31-system-inbox` (third entry in `watch_dirs`). Watchdog fires on file create/modify, debounces 2s, then calls `ingest_file()` which parses, chunks, embeds via Ollama, upserts to Qdrant `documents` collection. Frontmatter parsing enriches payloads.
2. `profiler_sources.py:58-60` — `VAULT_INBOX_DIR` reads same `OBSIDIAN_VAULT_PATH` env var, resolves to `31-system-inbox`. `discover_sources()` globs `*.md` files there (line 182-184). `read_vault_inbox()` chunks them as source type `vault-inbox` with a cap of 50 chunks.
3. `profiler.py` — `read_all_sources()` includes vault-inbox chunks in extraction. The profiler runs extraction via LLM, producing `ProfileFact` objects that are merged into the profile and saved.

**Verdict**: Works end-to-end. The vault inbox note gets ingested into Qdrant for RAG retrieval AND read by the profiler for profile extraction. Two independent consumption paths, both functional.

**2. Chat observation (record_observation) -> pending-facts.jsonl -> profiler reads -> profile updated?**

1. `chat_agent.py:313-352` — `record_observation` tool writes a JSON entry to `<cache>/cockpit/pending-facts.jsonl` with dimension, key, value, confidence 0.6, evidence, source "conversation:cockpit", and ISO timestamp.
2. `profiler_sources.py:157-159` — `discover_sources()` checks for `pending-facts.jsonl` at exactly that path. Sets `sources.pending_facts = pending_path`.
3. `profiler_sources.py:520-553` — `read_pending_facts()` reads the JSONL, formats each entry as `"- [{dim}] {key}: {value}"` with evidence, wraps in a `SourceChunk` with source type "conversation" and cap of 10 chunks.
4. During profiler extraction, the LLM processes these chunks and produces `ProfileFact` objects that are merged into the profile.

**Verdict**: Works end-to-end. The pending facts file is a clean handoff mechanism. One concern: the file is never truncated or rotated after profiler reads it. Over time, the profiler will re-read and re-extract the same pending facts each run. The change detection (`detect_changed_sources()`) based on mtime would skip if the file hasn't changed since last run, but if new facts are appended, the entire file is re-processed.

**3. Profile correction (correct_profile_fact) -> profiler apply_corrections() -> actually applied?**

1. `chat_agent.py:441-471` — `correct_profile_fact` tool builds a corrections list with dimension, key, value (or None for deletion). Calls `profiler.apply_corrections()` directly.
2. `profiler.py:707-794` — `apply_corrections()` loads the existing profile, iterates corrections:
   - Delete: filters out matching facts by dimension+key
   - Correct: creates a `ProfileFact` with confidence 1.0, source "operator:correction", calls `merge_facts()` which handles deduplication with authority-source priority
3. Rebuilds all dimensions, increments profile version, saves via `save_profile()`.

**Verdict**: Works end-to-end. Corrections are applied immediately and persistently. Source "operator:correction" with confidence 1.0 ensures corrections take precedence over all other sources. Profile version is bumped, so downstream consumers see the update on next read.

**4. Probe response -> where does it go?**

1. `copilot.py:156-158` — When a probe is surfaced, the copilot displays the probe's question as a text message: `"I've been wondering -- {rationale}. {question}"`. The probe is surfaced during idle periods (>300s, every 4th eval).
2. `micro_probes.py:146-149` — `mark_asked()` records the topic in `_asked` set and persists to `probe-state.json`. This prevents re-asking.
3. `chat_agent.py:356-393` — If the operator engages with the probe question in chat, the chat agent has a `record_probe_response` tool. This tool creates a `RecordedFact` and calls `profiler.flush_interview_facts()` which writes facts to the profile with source "micro-probe:cockpit".

**Verdict**: The probe surfacing -> operator engagement -> fact recording path works, but it depends on the chat agent correctly identifying that the conversation is probe-related and choosing to call `record_probe_response`. There is no explicit handoff mechanism from copilot to chat agent saying "the operator is responding to a probe." The copilot's `follow_up_hint` is set on the probe object but is only available if the chat agent reads `current_probe` from the context — and the chat agent's system prompt mentions `record_observation` (the general tool) but the probe-specific tool `record_probe_response` is registered separately. The probe response may be recorded via the general `record_observation` tool (confidence 0.6) instead of the probe-specific tool (confidence 0.7), depending on which tool the LLM chooses. Both paths lead to the profiler, but through different mechanisms (pending-facts.jsonl vs direct flush).

#### System -> Operator Flows

**1. Health failure -> notification -> reaches operator when?**

1. `health-monitor.timer` — Fires every 15 minutes (`OnUnitActiveSec=15min`), first run 2 minutes after boot.
2. `health-watchdog` (bash script) — Runs `health_monitor --json`, checks status. If not healthy, runs `--fix --yes` for auto-remediation, then re-checks.
3. Post-fix notification path:
   - If auto-fix resolved everything: sends "Auto-Fixed" notification via `shared.notify.send_notification()` (ntfy + desktop)
   - If still degraded/failed: sends alert via `shared.notify.send_notification()` with priority escalation (failed="high", degraded="default"). Also sends webhook to n8n (`N8N_HEALTH_WEBHOOK_URL`) for Telegram relay.
   - If healthy: silent. No notification.
4. Appends to `profiles/health-history.jsonl` regardless of status.

**Verdict**: Works end-to-end. The notification path is robust: ntfy (mobile push) -> desktop (fallback) -> n8n webhook (Telegram relay, if configured). The operator receives notification within 15 minutes of a failure persisting past auto-fix. Silent on healthy prevents notification fatigue. One gap: the briefing-watchdog script (see below) uses raw `notify-send` for its notification instead of `shared.notify`, so the briefing's own notification path is desktop-only.

**2. Briefing -> vault + notification -> operator reads when?**

1. `daily-briefing.timer` — Fires at `07:00` daily (`OnCalendar=*-*-* 07:00:00`, Persistent=true so missed runs catch up).
2. `briefing-watchdog` (bash script) — Runs `briefing --hours 24 --save --json`. The `--save` flag triggers two writes:
   - `profiles/briefing.md` (local file, read by cockpit)
   - `vault_writer.write_briefing_to_vault()` -> `<personal-vault>/30-system/briefings/YYYY-MM-DD.md` (Obsidian Sync picks this up)
3. The watchdog script extracts headline + high-priority count, then sends desktop notification via raw `notify-send`.
4. n8n `briefing-push.json` workflow triggers at 07:15 (15 min later), reads `profiles/briefing.md`, formats for mobile, sends via Telegram.

**Verdict**: The generation and persistence path works end-to-end. The operator can read the briefing in three places: Obsidian vault (via Sync, any device), TUI cockpit (reads briefing.md), or Telegram (via n8n, if deployed). However, the briefing-watchdog notification uses raw `notify-send` (desktop only, line 28-33) instead of `shared.notify` — so the operator only gets a mobile notification if the n8n Telegram workflow is deployed. If Telegram isn't configured, the briefing notification is desktop-only — invisible to a mobile operator.

**3. Copilot -> TUI display -> is observational mode low-interruption?**

1. `copilot.py:84-165` — `CopilotEngine.evaluate()` runs a priority-ordered rule engine:
   - P1 (immediate): health transitions, agent completions, screen returns
   - P2 (ongoing): stale briefing, degraded health, high VRAM, drift accumulation, bootstrapping readiness
   - P3 (idle >300s): readiness rotations, micro-probe questions, "quiet session"
   - P4 (ambient): session greeting (<60s), status summary

2. The copilot output is displayed in a single `CopilotLine` widget (one line of text at the top of the TUI). It does not:
   - Trigger modal dialogs or pop-ups
   - Play sounds or vibrate
   - Require operator response to dismiss
   - Block interaction with other TUI elements

3. Accommodation post-processing (`_apply_accommodations`, line 197-208): If `time_anchor_enabled`, appends session duration to messages (e.g., "quiet session. (23m in)"). This is the only active accommodation affecting copilot output.

**Verdict**: The copilot is genuinely observational and low-interruption. It updates a single text line that the operator can glance at or ignore. The priority ordering ensures urgent information (health drops, agent failures) surfaces immediately but still as passive text, not as an interrupting modal. Micro-probes are gated behind idle threshold (300s) and eval-count modulo (every 4th eval, ~2 min intervals at 30s refresh). The design respects ADHD attention patterns — it surfaces information without demanding a response.

#### Full Lifecycle Trace

**Operator writes a note in Obsidian (any device) -> note syncs via Obsidian Sync -> arrives in `31-system-inbox/` -> RAG ingest watchdog picks it up -> Docling parses, chunks, embeds -> Qdrant `documents` collection updated -> profiler's next `--auto` run (12h timer) discovers vault-inbox files, reads them, extracts profile facts -> profile updated, version bumped -> ProfileStore indexes to `profile-facts` collection -> context tools serve updated facts to all agents -> next briefing (daily 07:00) reads updated profile via context tools -> briefing output reflects new information -> briefing saved to vault `30-system/briefings/` -> syncs back to operator's devices.**

This lifecycle demonstrates the full bidirectional loop: operator input (Obsidian note) -> system processing (RAG + profiler) -> system output (briefing) -> operator consumption (vault sync). The loop closes, but the latency is up to ~12 hours for the profile update step (profiler timer). RAG ingestion is near-immediate (watchdog runs continuously), so the note's content is searchable via Qdrant within seconds. Profile integration is the slow link.

---

## Lens 4: Purpose — Does Every Part Justify Its Existence?

### H-4.1 — MEDIUM: InfraPanel and ScoutPanel widgets are orphaned code

**Files**:
- `cockpit/widgets/infra_panel.py:44` — `class InfraPanel(Static)`
- `cockpit/widgets/scout_panel.py:52` — `class ScoutPanel(Static)`
- `cockpit/app.py` — neither class is imported or mounted

Both widgets are fully implemented with CSS and rendering logic. Neither is referenced in `app.py` or any other screen. They were likely built as part of an earlier UI design that was replaced by the consolidated sidebar.

These are ~100 LOC of dead code that will:
- Confuse developers who find them and assume they're used
- Accumulate drift from the data layer they reference (if the data format changes, these won't get updated)
- Potentially be imported by mistake in future refactoring

**So what**: Dead code in a system designed for a single operator creates maintenance overhead disproportionate to its harm. But dead code that renders operator-facing information creates a risk of presenting stale or wrong data if accidentally reactivated.

---

### H-4.2 — MEDIUM: Legacy `store_to_qdrant()` has active CLI flag but no consumers

**Files**:
- `agents/profiler.py:1018-1045` — `store_to_qdrant()` writes dimension summaries to `claude-memory`
- `agents/profiler.py:1825` — `--store-qdrant` CLI flag triggers the legacy path

The `run_auto()` pipeline (used by the 12h timer) uses `ProfileStore.index_profile()` which writes to `profile-facts`. The `--store-qdrant` flag calls the old `store_to_qdrant()` which writes to `claude-memory`. No agent or tool reads profile data from `claude-memory`.

This is functional dead code with an active entry point. An operator running `--store-qdrant` would believe they're indexing their profile for agent consumption, but no agent will read it from that collection.

**So what**: An operator with executive function challenges should not be presented with options that appear functional but produce no effect. Every inactive CLI flag is a potential confusion point.

---

### H-4.3 — LOW: Micro-probes cover 1 of 13 profile dimensions

**File**: `cockpit/micro_probes.py`

All 8 hardcoded probes target `neurocognitive_profile`:

```
"What helps you start tasks when motivation is low?"
"How do you typically recover from interruptions?"
"What's your ideal work environment?"
...
```

The profiler tracks 13 dimensions: technical_proficiency, communication_style, work_patterns, tool_preferences, project_priorities, domain_knowledge, learning_patterns, creative_preferences, neurocognitive_profile, decision_style, collaboration_approach, management_practice, team_leadership.

The 12 non-neurocognitive dimensions get zero probe coverage. For a single-operator system where the profile directly shapes agent behavior, this leaves large gaps in experiential data collection.

**Mitigating factor**: The profiler extracts facts from many sources (shell history, git repos, vault, LLM exports, Takeout, Proton mail). Micro-probes are supplemental. But they're the *only* source that asks the operator directly, which produces the highest-confidence facts.

**So what**: The probe system exists and works, but its coverage is narrow. Expanding to other dimensions would improve profile quality across the board, not just neurocognitive.

---

## Lens 5: Interface Integrity — Do the Seams Hold?

### H-5.1 — HIGH: No typed contract between Python and TypeScript layers

**Files**:
- `agents/` and `cockpit/data/` — Python dataclasses as API response types
- `cockpit-web/src/api/types.ts:88-99` — TypeScript interfaces

The web layer (Domain 7) found that 4 of 15 endpoints have no TypeScript interfaces at all (drift, management, accommodations, health/history). Additionally, `ReadinessSnapshot` is missing 3 fields (`interview_fact_count`, `priorities_known`, `neurocognitive_mapped`) present in the Python dataclass.

There is no automated mechanism to detect when Python dataclasses and TypeScript interfaces diverge. Changes to Python response shapes silently break the TypeScript consumer. This is not just a web layer issue — it's a system-wide interface integrity problem:

1. **No schema generation**: No tool generates TS types from Python dataclasses
2. **No contract tests**: No tests verify that Python-serialized data matches TS type expectations
3. **No CI validation**: Divergence is only caught when the frontend renders wrong/missing data

**So what**: The API boundary between Python and TypeScript is an implicit contract. In a system maintained by one operator with ADHD, implicit contracts are especially dangerous — they require the operator to remember cross-repo dependencies when making changes.

---

### H-5.2 — MEDIUM: Nudge attention budget is uncapped

**File**: `cockpit/data/nudges.py`

The nudge collector aggregates from 8 sources: health, briefing action items, scout, drift, goals, readiness, management (stale 1:1s, overdue feedback, overdue coaching, high cognitive load). Each source can produce multiple nudges. There is no limit on how many nudges are surfaced.

In a pathological but realistic scenario:
- 3 health failures (score 100 each)
- 5 high-priority briefing action items (score 80 each)
- 2 stale goals (score 60, 35)
- 3 management nudges (score 70, 65, 55)
- 1 stale briefing (score 55)
- 1 scout recommendation (score 30)

That's 15 nudges demanding attention simultaneously. For an operator with ADHD, this is the opposite of executive function support — it's a wall of demands that triggers task paralysis.

The energy-aware accommodation reduces non-critical scores by 20% during low-energy hours, which changes ordering but not quantity. There is no mechanism to:
- Cap the number of visible nudges (e.g., "show top 5")
- Batch similar nudges (e.g., "3 management items need attention")
- Suppress lower-priority nudges when high-priority ones exist

**So what**: The nudge system was designed with priority scoring to help the operator focus. But without quantity management, the scoring just determines which item in an overwhelming list comes first. The system creates more cognitive load than it resolves when many things need attention simultaneously — exactly the condition where ADHD support is most needed.

---

### H-5.3 — MEDIUM: Three operator channels have incompatible capability sets

| Capability | TUI (cockpit) | Web (cockpit-web) | Obsidian (hapax plugin) |
|-----------|---------------|-------------------|------------------------|
| View nudges | Yes | Yes | No |
| Execute nudge | Yes | No | No |
| Dismiss nudge | No* | No | No |
| Chat with agent | Yes | No | Yes |
| Profile visibility | Yes (/profile) | No | No |
| Probe interaction | Yes (copilot) | No | No |
| RAG search | No** | No | Yes |
| 1:1 prep generation | No | No | Yes |
| Decision capture | Yes (execute only) | No | No |
| Accommodation management | Yes (/accommodate) | No | No |
| Health status | Yes | Yes | No |
| Agent launching | Yes | No | No |
| Briefing view | Yes | Yes | Via vault file |

*Decision records "executed" only (H-3.1). **Chat agent could search Qdrant via tools.

There is no documentation of which channel supports which capabilities. An operator choosing between channels has to discover capabilities by trial. For an operator with ADHD, the uncertainty of "can I do X here or do I need to switch?" creates friction that discourages engagement.

The capability gaps are particularly notable:
- The web dashboard (intended for ambient monitoring) shows nudges but can't act on them
- The Obsidian plugin (intended for knowledge work) can chat and search but has no visibility into system health or nudges
- The TUI (full-featured) requires terminal access, which isn't available from all contexts (e.g., mobile via Tailscale+Telegram has yet a different, fourth capability set)

**So what**: Multi-channel access is a design goal (documented in CLAUDE.md). But the channels aren't complementary — they're arbitrarily different subsets of the same features. A clear capability matrix and intentional channel design ("TUI for control, Web for monitoring, Obsidian for knowledge, Mobile for alerts") would reduce the operator's cognitive load in choosing how to interact.

---

### H-5.4 — LOW: Agent errors are invisible to the operator

**Files**: Multiple — `cockpit/api/routes/data.py`, `cockpit/data/nudges.py`, collector modules

Across the system, agent and collector failures are handled by:
- Returning `None` or empty data (cache returns, nudge collectors wrap in bare `except`)
- Logging a warning
- Continuing with stale data

The operator sees: nudges that were there yesterday but aren't today. Or a briefing section that's empty. Or health data that hasn't changed in hours. There is no mechanism that says "the cost collector has been failing for 3 cycles" or "the management scanner can't find your vault."

For the TUI, the copilot could observe this — but the copilot rules don't include data freshness monitoring. For the web dashboard, there are no error indicators at all (all endpoints return 200, finding 7.10).

**So what**: Silent failure is the default behavior of a system designed for an operator who needs help noticing things. The system assumes the operator will notice missing data. That's the exact cognitive function the system is supposed to externalize.

---

### Mobile (Telegram bot + ntfy) — ADHD appropriateness

**Files**: `n8n-workflows/briefing-push.json`, `n8n-workflows/health-relay.json`, `shared/notify.py`

The mobile notification path has two channels:

1. **ntfy push** (`shared/notify.py`): Priority-mapped (min/low/default/high/urgent), tag-based, reaches Android via F-Droid app. Health watchdog sends degraded/failed alerts via `send_notification()` with appropriate priority escalation. Silent on healthy — no notification spam.

2. **Telegram bot** (via n8n): Briefing push at 07:15 (15 min after briefing generates), health relay via webhook. Formats messages for mobile with extracted headline + action items in Markdown.

For ADHD-appropriate mobile attention:
- **Good**: Health watchdog is silent when healthy — no notification fatigue. Priority escalation is proportional (degraded = default, failed = high). ntfy tags allow filtering.
- **Good**: Briefing push extracts only headline + action items — information-dense, not full briefing dump.
- **Gap**: Telegram credentials are `CONFIGURE_ME` — the n8n workflows appear undeployed. If so, mobile is ntfy-only (push notifications without context). The briefing narrative and action commands are lost.
- **Gap**: No notification batching. If health degrades every 15 minutes (the timer period), the operator gets a push every 15 minutes for the same issue. No deduplication or escalation throttle.
- **Gap**: Quick-capture workflow (`quick-capture.json`) exists for Telegram-to-RAG, but there's no mobile path to *dismiss* a nudge or *acknowledge* a health alert — mobile is receive-only.

**So what**: The notification design is sound (priority mapping, silence on healthy, headline extraction). But the apparent non-deployment of Telegram workflows means mobile notification is limited to push without context. And the lack of deduplication means a persistent failure becomes persistent interruption — the opposite of ADHD accommodation.

---

### Vault (Obsidian) — cognitive overhead assessment

**Files**: `<personal-vault>/` folder structure, `50-templates/`

The vault has a clear hierarchical structure (00-inbox through 90-attachments) with numbered prefixes that provide spatial consistency — the folders always appear in the same visual order. This is good for an operator with ADHD.

For cognitive overhead:
- **Good**: `00-inbox/` as universal capture point is low-friction. QuickAdd plugin provides rapid capture templates. Inbox currently has 1 item, suggesting it's being processed regularly.
- **Good**: Templates (16 total) reduce blank-page paralysis. `tpl-daily.md`, `tpl-1on1-prep.md`, `tpl-meeting-1on1.md` all provide structured scaffolding for recurring tasks.
- **Good**: `31-system-inbox/` is a bidirectional bridge — operator writes notes, system reads them. This gives the operator a familiar interface (Obsidian) rather than requiring them to learn system-specific tools.
- **Good**: Bases dashboards (team-dashboard, active-projects, decision-log, recent-meetings, system-dashboard, team-operating-picture) provide pre-built views that don't require constructing queries.
- **Concern**: The folder hierarchy is 10 folders deep (00 through 90). For someone with ADHD, navigating to `10-work/meetings/` vs `10-work/decisions/` vs `32-bridge/prompts/` requires remembering the taxonomy. The numbered prefix system helps, but the tree depth could create "where does this go?" friction. The inbox as universal capture zone mitigates this — the operator can always dump into `00-inbox/` and sort later.
- **Concern**: Templates are in `50-templates/` accessed via Templater plugin. The operator must remember which template to use for which context. Templater's folder-based triggers can automate this (create in `10-work/meetings/` -> auto-apply meeting template), but this requires initial configuration.

**So what**: The vault structure is well-designed for scannability and low-friction capture. The main ADHD risk is the sort-later problem — items captured to inbox may accumulate if the operator doesn't have a regular processing habit. The system doesn't currently nudge for inbox processing (no vault-inbox-stale nudge exists in `nudges.py`).

---

## Cross-Cutting Observations

### The Coherence Problem Is Structural

The neurocognitive awareness gap (H-1.1, H-1.2, H-1.3) is not an oversight — it's a consequence of the context management refactoring (documented in MEMORY.md). The refactoring moved from large static prompts to lean prompts + context tools. The intent was to reduce token waste. The side effect was that agents without the static neurocognitive context became dependent on the LLM choosing to call `lookup_constraints()` — which it won't do if its system prompt doesn't suggest the need.

The fix isn't to revert to large static prompts. It's to ensure that every agent's system prompt contains a minimum viable neurocognitive framing — one sentence — that causes the LLM to use context tools appropriately:

```
The operator has ADHD and autism. Call lookup_constraints() before generating output.
```

This is ~15 tokens. The token budget savings from the refactoring are preserved.

### The Measurement Gap

Across all 5 lenses, the most consistent theme is: **the system acts but doesn't measure the effect of its actions.**

- Accommodations are set but not evaluated (H-3.4)
- Nudges are scored but not capped (H-5.2)
- Decisions are captured but only one-third of the signal (H-3.1)
- Probes ask but only about one dimension (H-4.3)
- Errors occur but are invisible (H-5.4)

A system that externalizes executive function must include the feedback loop: act -> observe effect -> adjust. Currently the system has act -> (silence). The profiler is the intended feedback mechanism, but it receives impoverished input from the system's own telemetry.

### The Unity Tax

Every parallel definition (H-2.2, H-2.5), every bypassed shared module (H-2.3), every unmaintained collection (H-2.1) adds a maintenance burden that falls on one operator. In a team, redundancy is annoying. For a single operator with ADHD, every redundancy is a potential "which one did I need to update?" decision point that drains executive function.

---

## Recommended Priority

1. **Add neurocognitive micro-prompt to all agent system prompts** (H-1.1, H-1.2, H-1.3) — ~15 tokens per agent, restores coherence. Register context tools on digest agent.
2. **Add `profile-facts` to knowledge-maint, health-monitor, digest COLLECTIONS** (H-2.1) — one-line fix per file, prevents unbounded growth.
3. **Implement nudge cap** (H-5.2) — surface top N nudges, batch the rest as "and N more." Most impactful ADHD accommodation fix in the whole audit.
4. **Record dismissed/expired decisions** (H-3.1) — complete the decision capture flow that's already wired end-to-end.
5. **Switch scout to shared.notify** (H-2.3) — one import change, enables mobile notification.
6. **Remove legacy `store_to_qdrant()` and `--store-qdrant` flag** (H-4.2) — eliminate dead path.
7. **Remove orphaned InfraPanel/ScoutPanel widgets** (H-4.1) — eliminate dead code.
8. **Add TypeScript code generation from Python dataclasses** (H-5.1) — long-term interface integrity.
9. **Document channel capability matrix** (H-5.3) — low effort, high orientation value.
10. **Add data freshness indicators to operator interfaces** (H-5.4) — make failures visible.
