# Agent Architecture

> **Note:** This document is the canonical architecture reference. It was originally a design proposal and has been updated to reflect the current implemented state. For per-agent operational details, see `<ai-agents>/profiles/operations-manual.md`.

## Philosophy

Three tiers, one principle: Claude Code is the command center. Everything else is infrastructure it can invoke, inspect, and reconfigure.

### Internal fitness vs. external fitness

The self-regulation agents (health-monitor, drift-detector, introspect) evaluate the system against its own expectations: is it healthy, is it consistent, is it documented? This is **internal fitness** — necessary but insufficient.

**External fitness** asks a different question: given what exists in the wider landscape right now, is this still the right way to do things? Technology moves fast. The barrier to change is low. A component that was best-in-class six months ago may be obsolete today. The system must resist ossification by continuously evaluating itself against external alternatives — and when something better comes along with acceptable tradeoffs, adopt it, even if that means the operator's own workflows change.

This is the scout agent's purpose. Where the drift detector asks "does documentation match reality?", the scout asks "does reality match the frontier?" Every component is held loosely. Nothing is sacred except the principles:

- **Route through LiteLLM** — but if something better than LiteLLM emerges, replace it
- **Embed with nomic** — but if a better embedding model ships, switch
- **Build on Pydantic AI** — but if the framework falls behind, migrate
- **The scout itself** — if a better approach to horizon scanning exists, the scout should recommend its own replacement

```
┌──────────────────────────────────────────────────────┐
│                    TIER 1: INTERACTIVE                │
│               Claude Code (you ↔ Claude)             │
│          MCP servers · slash commands · hooks         │
│                  Full stack access                    │
│                                                      │
│          System Cockpit (web dashboard)               │
│       FastAPI backend + React SPA frontend            │
│     `uv run cockpit` · `cockpit --once` (CLI)        │
├──────────────────────────────────────────────────────┤
│                  TIER 2: ON-DEMAND                    │
│            Pydantic AI agents invoked by              │
│          Claude Code or CLI or n8n trigger            │
│                                                      │
│  Implemented:                                        │
│    research         code-review      profiler        │
│    health-monitor   introspect       drift-detector  │
│    activity-analyzer briefing        scout           │
│    management-prep  meeting-lifecycle digest          │
│    knowledge-maint  demo             demo-eval       │
│                                                      │
│  Planned:                                            │
│    sample-curator   draft            midi-programmer │
├──────────────────────────────────────────────────────┤
│                TIER 3: AUTONOMOUS                     │
│         Always-running systemd services or           │
│          n8n scheduled workflows                     │
│                                                      │
│  rag-ingest          health-monitor timer             │
│  knowledge-maint     briefing timer                  │
│  digest timer        scout timer                     │
│  drift-detector      manifest-snapshot               │
│  llm-backup          profile-update                  │
│  meeting-prep        vram-watchdog                   │
│  obsidian-webui-sync                                 │
└──────────────────────────────────────────────────────┘
         ▲               ▲               ▲
         │               │               │
    ┌────┴────┐   ┌──────┴──────┐  ┌─────┴─────┐
    │ Qdrant  │   │  LiteLLM    │  │ Langfuse   │
    │ memory  │   │  (all LLMs) │  │ (observe)  │
    └─────────┘   └─────────────┘  └───────────┘
```

## Tier 1: Interactive (Claude Code + System Cockpit + Extended Surfaces)

Claude Code is the primary interactive interface — full MCP access, slash commands, hooks, and direct agent invocation.

The **System Cockpit** is the operational dashboard, built as a **FastAPI API backend + React SPA frontend** (`cockpit-web`). It provides real-time health monitoring, agent status, nudge management, goal tracking, profile visibility, and briefing display.

- `uv run cockpit` launches the API server (default port 8095)
- `cockpit --once` produces a one-shot CLI snapshot for terminal use or piping
- The React frontend connects to the FastAPI backend and renders the dashboard in the browser

The cockpit consumes data from health-monitor, briefing, scout, activity-analyzer, and profiler agents. Persistent state lives in `<cache>/cockpit/` (probes, decisions, facts).

### Extended Interactive Surfaces

Beyond Claude Code and the Cockpit, Tier 1 includes additional LLM-enabled surfaces that route through LiteLLM for model access and Langfuse tracing. These are not agents — they are interaction points that make LLM availability ambient across the workstation.

| Surface | Tools | Purpose |
|---------|-------|---------|
| Shell LLM layer | mods, Fabric, llm plugins, shell functions | Pipe-based LLM access, NL-to-command, prompt patterns |
| Editor LLM layer | Continue.dev (VS Code) | Code completion, chat, inline edit via LiteLLM |
| Browser LLM layer | Lumos (Chrome) | Page RAG, summarization via Ollama |
| Voice input (PTT) | Voxtype / faster-whisper | Push-to-talk STT feeding into existing surfaces |
| Voice daemon | Hapax Voice (`agents/hapax_voice`) | Always-on voice interaction: wake word, presence detection, Gemini Live S2S + local STT/TTS cascade, speaker ID, PANNs ambient sound classification, context gate, screen awareness (AT-SPI + Gemini Flash vision) |
| Desktop hotkeys | fuzzel + aichat + wl-copy | Selection transforms, prompt dialogs, model switching |

Design: `docs/plans/2026-03-05-llm-enablement-design.md` (waves 1-4), `<distro-work>/docs/plans/2026-03-09-voice-modality-design.md` (Hapax Voice). Implementation: `<distro-work>/`.

**Hapax Voice utilities:** `scripts/train_wake_word.py` (generate custom OpenWakeWord models from text phrases), `scripts/enroll_speaker.py` (register speaker embedding for speaker ID verification), and `scripts/generate_screen_context.py` (generate static system context for screen awareness).

**Screen awareness subsystem:** AT-SPI2 polls for focused window changes (2s interval), grim captures on context change, Gemini Flash analyzes via LiteLLM. High-confidence errors route to TTS via NotificationQueue + ContextGate. Static system context loaded from `<local-share>/hapax-voice/screen_context.md` (auto-generated, drift-detected). Design: `docs/plans/2026-03-09-screen-awareness-design.md`.

## Tier 2: On-Demand Agents (Pydantic AI)

These live in `<ai-agents>/`. Claude Code invokes them via shell or imports them as modules. Each agent uses LiteLLM as its backend (never direct provider APIs) and logs to Langfuse.

### research-agent

**Trigger:** Claude Code `/ingest` command, or direct invocation.
**Function:** Given a topic, searches Qdrant for existing knowledge, identifies gaps, uses web search (Tavily MCP) to fill them, writes a structured briefing, stores embeddings back in Qdrant.
**Model:** claude-sonnet (via LiteLLM) for synthesis, nomic-embed for retrieval.
**Output:** Markdown briefing + Qdrant vectors updated.

### code-review-agent

**Trigger:** Git pre-push hook or Claude Code `/review` command.
**Function:** Reads staged diff, checks against project conventions (from CLAUDE.md or repo-local rules), flags issues by severity, suggests fixes. Uses AST parsing for Python/JS, not just string matching.
**Model:** claude-sonnet for analysis, qwen-coder-32b for quick syntax checks.
**Output:** Structured review in stdout or as git notes.

### sample-curator (planned)

**Trigger:** New files in sample library directories, or manual invocation.
**Function:** Analyzes audio files (BPM, key, spectral characteristics via librosa), generates semantic descriptions, categorizes by vibe/genre/instrument, stores metadata + embeddings in Qdrant `samples` collection. Can recommend samples for a given mood/context.
**Model:** nomic-embed for embeddings, claude-haiku for descriptions (cheap, high volume).
**Output:** Qdrant entries + optional SP-404 MKII bank assignment suggestions.

### digest

**Trigger:** Daily 06:45 timer (`digest.timer`) or manual CLI.
**Function:** Aggregates recently-ingested RAG content + vault inbox items. LLM-synthesized content overview highlighting notable items, themes, and connections. Runs 15 minutes before briefing so the briefing agent can consume the digest.
**Model:** claude-sonnet (balanced) for synthesis.
**Output:** `profiles/digest.md` (readable), `profiles/digest.json` (structured), vault `30-system/digests/` (on `--save`).

### draft-agent (planned)

**Trigger:** Claude Code invocation with context.
**Function:** Writes first drafts — emails, Slack messages, documents, blog posts. Takes a brief + tone + audience and produces ready-to-edit output. Can pull context from Qdrant (past conversations, project docs).
**Model:** claude-sonnet for quality drafts, gemini-flash for quick iterations.
**Output:** Text to clipboard or file.

### midi-programmer (planned)

**Trigger:** Claude Code or direct CLI.
**Function:** Generates MIDI patterns (chord progressions, drum patterns, bass lines) as .mid files or real-time ALSA output via virtual MIDI ports. Understands music theory — can generate in specific keys, scales, time signatures. Knows the hardware targets (SP-404 pad layouts, Elektron step sequencer constraints, OXI One pattern format).
**Model:** claude-sonnet (music theory reasoning), local model for rapid iterations.
**Output:** .mid files, or live MIDI via snd-virmidi → PipeWire → hardware.

### management-prep

**Trigger:** Manual CLI or Claude Code invocation before 1:1s or weekly reviews.
**Function:** Reads vault management data (people notes, coaching hypotheses, feedback records, meeting history) via `cockpit/data/management.py`, synthesizes context with one LLM call, writes preparation material to vault. Three modes: `--person "Name"` (1:1 prep), `--team-snapshot` (team state overview), `--overview` (condensed management summary).

**Boundary:** "LLM Prepares, Human Delivers." System prompt explicitly forbids drafting feedback language, generating coaching hypotheses, or suggesting what the operator should say. Focus is signal aggregation and context synthesis only.

**Model:** claude-sonnet (balanced) for prep/snapshot, claude-haiku (fast) for overview.
**Data sources:** Vault people notes, meeting notes, coaching hypotheses, feedback records (all via `shared/management_bridge.py` and `cockpit/data/management.py`).
**Output:** Markdown written to vault (`10-work/1on1-prep/`, `10-work/{date}-team-snapshot.md`, `30-system/management-overview.md`). Also stdout/JSON.

### meeting-lifecycle

**Trigger:** Daily 06:30 timer (`meeting-prep.timer`), manual CLI, or Claude Code invocation.
**Function:** Automates meeting preparation, post-meeting processing, transcript ingestion, and weekly review. Four modes: `--prepare` (auto-generate 1:1 prep for due meetings), `--transcript FILE` (parse VTT/SRT/speaker-labeled transcripts, extract action items), `--weekly-review` (aggregate week's meeting data), `--process` (post-meeting action item extraction). Supports `--person` filter and `--dry-run`.

**Boundary:** Same as management-prep — signal aggregation only, no feedback language generation.

**Model:** claude-sonnet (balanced) for synthesis.
**Data sources:** Vault meeting notes, person notes, transcripts (via `shared/transcript_parser.py`).
**Output:** Prep docs to `10-work/1on1-prep/`, meeting summaries to vault, action items extracted to meeting notes.

### scout (horizon scanner)

**Trigger:** Weekly timer (Wednesday), or manual `uv run python -m agents.scout`.
**Function:** Evaluates external fitness of every stack component. Reads a component registry (`profiles/component-registry.yaml`) that maps each component to its role, constraints, and search strategies. For each component, performs web searches (Tavily API via urllib), collects alternatives and updates, then uses an LLM to evaluate findings against operator constraints and preferences. Produces a ranked report of recommendations.

**Recommendation tiers:**
- **Adopt**: Clear improvement, low effort, reversible. System should push toward this.
- **Evaluate**: Promising, needs deeper investigation or operator decision.
- **Monitor**: Too early or unclear tradeoffs, but worth tracking.

**Model:** claude-sonnet (via LiteLLM) for evaluation reasoning.
**Data sources:** Component registry, introspect manifest, Tavily web search.
**Output:** `profiles/scout-report.json` (structured) + `profiles/scout-report.md` (human-readable). Consumed by briefing agent on report day.

**Design principle:** The scout scans components, not architecture. Structural questions ("should we still use three tiers?") are too open-ended for automated weekly runs. Instead, the scout flags when component-level findings imply architectural shifts (e.g., "MCP now has native agent orchestration — flat orchestration may no longer be needed").

### profiler

**Trigger:** 12h timer (`profile-update.timer`), manual CLI, or `--auto` flag.
**Function:** Discovers operator data sources (config files, transcripts, shell history, git repos, Langfuse traces, Takeout structured facts, Proton Mail exports, vault management notes), extracts facts via LLM or deterministic bridges, curates into a structured 13-dimension profile. Supports interactive interview for directed discovery. `--auto` flow auto-loads pre-computed structured facts from Takeout and Proton bridges (zero LLM cost for those).
**Model:** claude-sonnet (balanced) for extraction.
**Output:** `profiles/operator.json` (structured), `profiles/operator.md` (readable). Profile injected into all agent system prompts via `shared/operator.py`.

### health-monitor

**Trigger:** 15min timer (`health-monitor.timer`) or manual CLI.
**Function:** Deterministic checks across 18 groups (docker, gpu, systemd, qdrant, profiles, endpoints, credentials, disk, models, auth, connectivity, queues, budget, capacity, axioms, latency, secrets, voice). Zero LLM calls. ~85 checks total (exact count varies with Docker container count). Auto-fix for safe issues (restart containers, clear caches). History appended to `profiles/health-history.jsonl`. `--history` flag for trend analysis.
**Model:** None (fully deterministic).
**Output:** JSON health report + desktop/ntfy notifications on failure.

### introspect

**Trigger:** Weekly timer (`manifest-snapshot.timer`) or manual CLI.
**Function:** Deterministic infrastructure manifest generator. Enumerates Docker containers, systemd units, Qdrant collections, LiteLLM models, disk usage, network ports. Produces a complete snapshot of system state.
**Model:** None (fully deterministic).
**Output:** `profiles/manifest.json`

### drift-detector

**Trigger:** Weekly timer (`drift-detector.timer`) or manual CLI.
**Function:** Compares documentation (CLAUDE.md, README, architecture docs) against observed system reality. Uses LLM to identify discrepancies between what docs claim and what actually exists. `--fix` mode generates corrected doc fragments.
**Model:** claude-sonnet for comparison reasoning.
**Output:** `profiles/drift-report.json`, `profiles/drift-history.jsonl`

### activity-analyzer

**Trigger:** Manual CLI or consumed by briefing agent.
**Function:** Queries Langfuse traces, health history, drift history, systemd journal. Aggregates activity patterns, model usage, error rates, cost data. Zero LLM by default — pure data collection and aggregation. `--synthesize` flag adds an LLM-generated summary layer.
**Model:** None by default; claude-haiku (fast) for `--synthesize`.
**Output:** Activity data dict consumed by briefing agent, or standalone JSON/text report.

### briefing

**Trigger:** Daily 07:00 timer (`daily-briefing.timer`) or manual CLI.
**Function:** Consumes activity data (from activity-analyzer) + live health snapshot + scout report (when present). LLM-synthesized actionable morning briefing with priorities, action items, and system status. Integrates nudges and goal staleness.
**Model:** claude-sonnet for synthesis.
**Output:** `profiles/briefing.md` + vault `30-system/briefings/` (on `--save`) + ntfy notification.

### demo

**Trigger:** Manual CLI or Claude Code invocation.
**Function:** Audience-tailored demo generator. Produces slides, screenshots, and voice-cloned video for system demonstrations. Adapts content depth and framing to the target audience.
**Model:** claude-sonnet for content generation.
**Output:** Demo artifacts (slides, screenshots, video).

### demo-eval

**Trigger:** Manual CLI, typically after demo generation.
**Function:** Evaluates demo output quality using LLM-as-judge pattern. Scores demos on clarity, accuracy, audience fit, and visual quality. Feeds results back into a self-healing loop for iterative improvement.
**Model:** claude-sonnet for evaluation.
**Output:** Evaluation report with scores and improvement suggestions.

## Tier 3: Autonomous Agents (systemd + n8n)

### rag-ingest (systemd user service)

**Status:** Partially implemented at `<rag-pipeline>/ingest.py`.
**Behavior:** Watches `~/documents/rag-sources/` via inotify/watchdog. New files → Docling extraction → chunk → nomic-embed-text → Qdrant `documents` collection. Handles PDF, DOCX, MD, HTML, TXT.
**Service:** `<systemd-user>/rag-ingest.service`

### health-monitor timer (systemd timer)

**Behavior:** Every 15 minutes, invokes the health-monitor agent (Tier 2). Runs deterministic checks across 18 groups, auto-fixes safe issues, notifies via ntfy + desktop on failures. History appended to `profiles/health-history.jsonl`. Uses `health-watchdog.service` with `notify-failure@.service` template on failure.
**Service:** `<systemd-user>/health-monitor.timer` + `health-watchdog.service`

### knowledge-maint (systemd timer)

**Behavior:** Weekly (Sunday 04:30). Deduplicates Qdrant vectors (cosine similarity > 0.98). Prunes stale entries from deleted source files. Validates embedding dimensions (768d). Reports stats with error counts. Dry-run by default, `--apply` for deletions. Optional `--summarize` for LLM summary.
**Service:** `<systemd-user>/knowledge-maint.timer` + `knowledge-maint.service`

## Implementation Status

15 of 18 planned agents are implemented. Remaining planned agents: sample-curator, draft, midi-programmer.

All Tier 3 services are running as systemd timers (not n8n). n8n is used for notification workflows (briefing-push, health-relay, nudge-digest, quick-capture) but not for agent scheduling.

## Shared Infrastructure

All Tier 2 agents share:

```python
# <ai-agents>/shared/config.py
import os

LITELLM_BASE = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
LITELLM_KEY = os.getenv("LITELLM_API_KEY")
QDRANT_URL = "http://localhost:6333"
LANGFUSE_HOST = "http://localhost:3000"

# Standard model aliases — agents reference these, not raw model IDs
MODELS = {
    "fast": "claude-haiku",        # cheap, quick tasks
    "balanced": "claude-sonnet",   # default for most agents
    "reasoning": "deepseek-r1:14b",# complex reasoning via Ollama
    "coding": "qwen-coder-32b",   # code generation via Ollama
    "embedding": "nomic-embed",    # vector embeddings
    "local-fast": "qwen-7b",      # offline/privacy tasks
}
```

All Tier 2/3 agents emit OpenTelemetry traces to Langfuse. All use Qdrant for memory. All route model calls through LiteLLM. No Tier 2/3 agent calls a provider directly. Claude Code (Tier 1) makes direct Anthropic API calls.

## Claude Code Integration Pattern

Claude Code invokes Tier 2 agents via shell:

```bash
# From Claude Code:
cd <ai-agents>
uv run python -m agents.research --topic "ExLlamaV3 speculative decoding" --depth deep
uv run python -m agents.sample_curator --path ~/samples/new-pack/
uv run python -m agents.midi_programmer --style "boom bap" --key "Dm" --bpm 90
```

Or via custom slash commands (already scaffolded in <claude-config>/commands/).
Results flow back through stdout, files, or Qdrant queries.

## Obsidian as Operational Surface

Obsidian serves as the primary operational surface during work hours. Two vaults: Work vault (`<work-vault>/`) syncs via VS Code GitDoc (git auto-commit + push) to corporate work laptop; Personal vault (`<personal-vault>/`) is local only.

**Bidirectional data flows:**
- **System → Vault:** `vault_writer.py` writes briefings, nudges, goals to `30-system/` → GitDoc auto-commits → git push propagates to work laptop
- **Vault → System:** Operator writes notes in `31-system-inbox/` from any device → git sync delivers to home PC → RAG ingest watchdog picks up changes → Qdrant → profiler can query as `vault-inbox` source
- **VS Code + GitDoc** always running — handles vault sync via git

**Key integration points:**
- `briefing.py --save` writes to both `profiles/briefing.md` and vault `30-system/briefings/`
- RAG ingest watches `31-system-inbox/` alongside `~/documents/rag-sources/`
- Profiler discovers `vault-inbox` source type for operator notes
- Bases dashboards provide structured views of team, projects, decisions, meetings

## Design Decisions (Resolved)

1. **Agent-to-agent communication:** No — flat orchestration. Claude Code orchestrates, agents never invoke each other. This avoids cascading failures and keeps the call graph auditable.

2. **State management:** Agents are stateless per-invocation. All persistent state lives in Qdrant, filesystem (`profiles/`), or cache (`<cache>/cockpit/`). This works well for the current 15-agent roster.

3. **Cost controls:** LiteLLM fallback chains provide implicit cost control (expensive model fails → cheaper model). Langfuse traces all calls for cost visibility. High-frequency Tier 3 tasks (health-monitor, knowledge-maint) use zero LLM by default.

4. **Adoption automation:** Operator confirms all adopt recommendations. No auto-apply.
