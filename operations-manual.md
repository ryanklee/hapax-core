# Hapax System — Operations Manual

*For the single operator of an LLM-first development and creative production workstation.*

---

## What This System Is

Hapax is a three-tier autonomous agent system running on a single workstation with an NVIDIA RTX 3090. It provides:

- **Externalized executive function** — automated routines, proactive nudges, and contextual briefings compensate for ADHD/autism-related challenges with task initiation and sustained attention
- **LLM-augmented development** — Claude Code as primary interface, 23 specialized agents, RAG-backed knowledge retrieval
- **Music production infrastructure** — MIDI routing, sample management, hardware integration for a DAWless studio
- **Management support** — 1:1 prep, team snapshots, coaching signal tracking (aggregation only, never generates feedback language)

Tier 2/3 agents route all LLM calls through LiteLLM for observability (Claude Code makes direct Anthropic API calls). Everything stores vectors in Qdrant. Agent calls trace to Langfuse. The operator interacts primarily through Claude Code and Obsidian.

---

## First Day

### 1. Verify the Stack Is Running

Open a terminal. Check infrastructure health:

```bash
cd <ai-agents> && eval "$(<.envrc)" && uv run python -m agents.health_monitor
```

This runs 85+ deterministic checks across 17 groups: auth, axioms, budget, capacity, connectivity, credentials, disk, docker, endpoints, gpu, latency, models, profiles, qdrant, queues, secrets, systemd. No LLM calls — pure infrastructure verification.

Expected output: `85/85 HEALTHY` (check count grows as new checks are added). If degraded, the output tells you exactly what failed and how to fix it. Common first-day issues:

| Symptom | Fix |
|---------|-----|
| Docker containers down | `cd ~/llm-stack && eval "$(<.envrc)" && docker compose --profile full up -d` |
| Ollama models not loaded | They load on first request; initial pull: `docker compose exec ollama ollama pull nomic-embed-text` |
| Qdrant collections missing | Agents create them on first use |
| Systemd timers not running | `systemctl --user enable --now health-monitor.timer` (repeat for each timer) |

### 2. Read the Morning Briefing

The briefing agent runs daily at 07:00 via systemd timer. To generate one manually:

```bash
cd <ai-agents> && eval "$(<.envrc)" && uv run python -m agents.briefing --hours 24 --save
```

The briefing synthesizes: LLM call volume and cost, error rates by model, health check history, axiom compliance status, drift items, and action items ranked by priority. Output saves to `<ai-agents>/profiles/briefing.md` and writes to the Obsidian vault at `30-system/`.

The briefing is your daily operational summary. Read it. Act on any high-priority items it flags.

### 3. Launch the Cockpit

The cockpit is a web application: a FastAPI backend serves data on port 8051 and a React SPA frontend provides the interactive dashboard. In production, the API runs as a Docker container (`hapax-agents`).

**Start the API server** (if not running as Docker container):

```bash
cd <ai-agents> && eval "$(<.envrc)" && uv run cockpit
```

This launches the FastAPI API server. The Docker container maps it to http://localhost:8051.

**Start the web frontend** (in a separate terminal):

```bash
cd <cockpit-web> && pnpm dev
```

Open http://localhost:5173. The web dashboard shows health status, Docker containers, systemd timers, GPU/VRAM, nudges, cost tracking, domain health, briefings, and scout reports. In production, the built SPA can be served directly from the API server.

**CLI snapshots** (no web UI needed):

```bash
uv run cockpit --once                # Plain text snapshot to stdout
uv run cockpit --color               # Rich formatted CLI snapshot
```

These print a point-in-time system overview to the terminal and exit — useful for scripting or quick checks without launching the full web UI.

### 4. Open Obsidian

Obsidian is the knowledge interface. Two vaults with different sync mechanisms:

- **Work vault** (`<work-vault>/`) — git repo, syncs via VS Code GitDoc (auto-commit + push) to corporate work laptop
- **Personal vault** (`<personal-vault>/`) — local only (no sync needed)

Work vault folders:

| Folder | Purpose |
|--------|---------|
| `00-inbox/` | Work captures from any device |
| `10-work/` | Management domain — people, meetings, projects, decisions, references, coaching, feedback, 1on1-prep |
| `30-system/` | System-managed outputs — briefings, digests, nudges, goals, management-overview, hapax-context |
| `32-bridge/` | Bridge zone — prompts, guides |
| `40-calendar/` | Daily and weekly notes |
| `50-templates/` | Work templates |
| `90-attachments/` | Media and file attachments |

Personal vault folders:

| Folder | Purpose |
|--------|---------|
| `00-inbox/` | Personal captures |
| `20-personal/` | Personal domain — music, etc. |
| `50-templates/` | Personal templates |
| `90-attachments/` | Media and file attachments |

**Quick creation macros** (Ctrl+P → QuickAdd): Quick Capture, System Inbox, New Decision, New Coaching Hypothesis, New Feedback Record, New Meeting 1:1, New Person, New Project, New Meeting (Ceremony).

**Hapax Chat plugin** (sidebar): Streaming LLM chat that automatically includes the active note as context. 12 note-type prefixes adapt the system prompt based on what you're looking at. 4 slash commands: `/prep` (1:1 talking points), `/review-week` (person's week summary), `/growth` (trajectory assessment), `/team-risks` (risk signals).

### 5. Understand Claude Code

Claude Code is the primary interactive interface. It has full MCP access to: filesystem, Docker, PostgreSQL, Qdrant, git, browser automation, web search, and persistent memory.

Key slash commands available in Claude Code:

| Command | Purpose |
|---------|---------|
| `/status` | Run health monitor |
| `/briefing` | Generate system briefing |
| `/axiom-check` | Check axiom compliance |
| `/axiom-review` | Review pending precedents |
| `/axiom-sweep` | Scan repos for axiom violations |
| `/vram` | GPU memory analysis |
| `/ingest` | RAG pipeline status |
| `/studio` | Music production infrastructure check |
| `/deploy-check` | Pre-push readiness verification |
| `/weekly-review` | Week's aggregated system data |

Claude Code also has access to the operator profile (13 dimensions in Qdrant), axiom governance (4 axioms, 16 T0 implications), and the full system topology. Skills are defined in `<hapax-system>/skills/`.

### 6. First-Day Checklist

- [ ] Verify `health-monitor` returns all checks HEALTHY
- [ ] Read the morning briefing (or generate one)
- [ ] Launch the cockpit (`uv run cockpit` + web frontend), familiarize with the dashboard
- [ ] Open Obsidian, verify sync is working
- [ ] Open Claude Code, run `/status` to confirm it sees the stack
- [ ] Check systemd timers are enabled: `systemctl --user list-timers`
- [ ] Browse `30-system/` in Obsidian — see what the system has written recently
- [ ] Browse existing nudges in the cockpit — what does the system think needs attention?

---

## First Week

### Daily Rhythm

The system has a built-in daily sequence that runs automatically:

| Time | What Happens |
|------|-------------|
| 06:30 | Meeting prep agent generates 1:1 prep docs for today's meetings |
| 06:45 | Digest agent aggregates recently ingested content (runs before briefing so briefing can consume digest output) |
| 07:00 | Briefing agent synthesizes 24h of telemetry + digest output → saves to vault and sends push notification |
| Every 15 min | Health monitor runs, auto-fixes what it can, notifies on failures |
| Every 30 min | Google Calendar, Obsidian vault, and audio processor sync to RAG |
| Every 1-2h | Gmail, Chrome history, Claude Code transcripts, and Google Drive sync to RAG |
| Every 12h | Profiler agent incrementally updates operator profile |
| Always on | RAG ingestion watchdog, audio recorder, voice daemon, BT keepalive |

Your morning routine: read the briefing (arrives as ntfy push notification, also in `30-system/`), check any nudges in the cockpit, act on flagged items.

### Agent Workflows to Practice

**Research** — when you need to know something, with RAG context:
```bash
cd <ai-agents> && eval "$(<.envrc)"
uv run python -m agents.research "How does the LiteLLM fallback chain work?"
```
This queries Qdrant for relevant document chunks and synthesizes an answer.

**Code review** — when you want a second opinion on a file:
```bash
uv run python -m agents.code_review <ai-agents>/cockpit/app.py
```

**Management prep** — before 1:1s:
```bash
uv run python -m agents.management_prep --person "Alice"
uv run python -m agents.management_prep --team-snapshot
uv run python -m agents.management_prep --overview
```
These read from person notes in the vault (10-work/people/) and aggregate signals. They never generate feedback language or coaching recommendations — they surface patterns and open loops for you to interpret.

**Meeting lifecycle** — after meetings:
```bash
uv run python -m agents.meeting_lifecycle --transcript ~/path/to/transcript.vtt
```
Parses transcripts (VTT/SRT/speaker-labeled), extracts action items, and updates the vault.

### Knowledge Ingestion

Documents dropped into `~/documents/rag-sources/` are automatically ingested by the RAG pipeline (always-running `rag-ingest.service`). They go through Docling for parsing, get chunked, embedded with nomic-embed-text, and stored in Qdrant's `documents` collection.

The ambient audio pipeline continuously records from the microphone (`audio-recorder.service`), segments and transcribes recordings every 30 minutes (`audio-processor.timer`), and archives raw audio to Google Drive nightly (`audio-archiver.timer`). Transcriptions are stored in Qdrant for RAG retrieval.

The voice daemon (`hapax-voice.service`) provides always-on voice interaction with wake word detection, presence awareness, and TTS/STT via Chatterbox.

Check ingestion status:
```bash
# In Claude Code
/ingest
```

### Obsidian Workflow

**People management**: Create person notes (QuickAdd → New Person). The template includes Meta Bind widgets for cognitive load (slider), skill level, will signal, coaching status, and status. These frontmatter fields feed into management prep and team snapshot agents.

**Meetings**: Create meeting notes (QuickAdd → New Meeting 1:1 or New Meeting Ceremony). The 1:1 template references the prep doc. After the meeting, update action items using the Tasks plugin syntax (`- [ ] Action @person`).

**Decisions**: Create decision records (QuickAdd → New Decision). The template captures context, options, decision, and rationale. Decisions are indexed by the RAG pipeline.

**RAG ingestion**: Drop files into `~/documents/rag-sources/` for the system to learn. The RAG pipeline ingests them automatically.

### Notification Channels

Notifications flow through `shared/notify.py`:

1. **ntfy** (primary) — push notifications to phone (ntfy app on F-Droid) and desktop. Server at localhost:8090, topic `cockpit`. Supports priority levels (min through urgent) and click-through URLs to Obsidian notes.
2. **notify-send** (fallback) — desktop notification via libnotify.
3. **n8n webhooks** — 4 workflows: briefing-push, nudge-digest, quick-capture (Telegram), health-relay.

### Axiom Governance

The system is governed by 4 axioms:

| Axiom | Weight | Core Principle |
|-------|--------|---------------|
| `single_operator` | 100 | No auth, no multi-user, no collaboration features |
| `decision_support` | 95 | Zero-config agents, actionable errors, automated routines |
| `management_safety` | 95 | LLMs prepare, humans deliver — never generate feedback language |
| `corporate_boundary` | dormant | Obsidian plugin cross-network boundary (retained for reference) |

These aren't aspirational — they're enforced. The axiom enforcement infrastructure (defined in `<hapax-system>/hooks/`) includes SessionStart hooks that verify axiom count, PreToolUse pattern scanners that block violations, and PostToolUse audit loggers. 16 T0 implications block code that violates existential constraints. 15 sufficiency probes verify agent compliance.

Check compliance: `/axiom-check` in Claude Code. Review pending precedents: `/axiom-review`.

### First-Week Checklist

- [ ] Read the briefing every morning for 5 consecutive days
- [ ] Run at least one research query
- [ ] Run management prep for a real person
- [ ] Create a person note, meeting note, and decision in Obsidian
- [ ] Drop a document into `~/documents/rag-sources/` and verify it appears in RAG
- [ ] Try the Hapax Chat sidebar in Obsidian — open a person note and type `/prep`
- [ ] Check the cockpit dashboard — what needs attention?
- [ ] Review the nudges list — act on or dismiss at least one
- [ ] Check your phone for ntfy push notifications from the briefing timer

---

## First Month

### Weekly Maintenance Rhythm

Sunday is the maintenance window. These run automatically:

| Time | Timer | Purpose |
|------|-------|---------|
| Sun 02:00 | `llm-backup` | Full stack backup (Claude config, Qdrant snapshots, PostgreSQL dumps, n8n workflows, systemd units, Langfuse prompts, agent profiles, hotkey scripts). Keeps last 8 backups. |
| Sun 02:30 | `manifest-snapshot` | Infrastructure manifest for drift detection |
| Sun 03:00 | `drift-detector` | Compares documentation against actual system state |
| Sun 04:30 | `knowledge-maint` | Qdrant dedup, stale vector pruning, collection stats |

Monday morning: check if drift-detector found anything. Run `/weekly-review` in Claude Code for the aggregated week summary.

Wednesday: scout agent runs at 10:00, evaluating each stack component against the external landscape (newer versions, better alternatives, deprecation risks). Check scout results in the cockpit.

### Domain Lattice Engine

The system tracks 4 life domains: **management**, **music**, **personal**, **technical**. Each has:

- **Sufficiency model** — what knowledge/data the system needs to be useful in that domain (YAML definitions in `hapaxromana/knowledge/`)
- **Momentum tracking** — 7-day/30-day activity ratio, regularity of engagement, alignment of sufficiency improvement
- **Relationships** — domains connect (management → personal via "energy budget", music → technical via "MIDI tooling")
- **Domain health** — aggregated view in cockpit dashboard with status indicators

The system also runs **emergence detection** — clustering undomained vault activity by keyword co-occurrence to surface potential new domains.

Nudges from the domain lattice appear in the cockpit: "management-sufficiency gap: meeting notes", "emergence-cluster: 3 notes about woodworking".

### Profiler System

The operator profile has 13 dimensions (identity, workflow, philosophy, neurocognitive patterns, goals, contradictions, etc.) stored as vectors in Qdrant's `profile-facts` collection.

Sources that feed the profiler:
- Chat history (Claude.ai, Gemini, Open WebUI conversations)
- Google Takeout exports (Chrome, Keep, YouTube, Calendar, Gmail, Drive, etc.)
- Vault inbox notes
- Interview sessions (Socratic interrogation via cockpit or CLI)
- Micro-probes (brief targeted questions via cockpit or CLI)

The profiler runs every 12h automatically. You can trigger it manually:
```bash
cd <ai-agents> && eval "$(<.envrc)"
uv run python -m agents.profiler --auto          # Incremental from all sources
uv run python -m agents.profiler --digest         # From digest content
uv run python -m agents.profiler --source vault-inbox  # From specific source
```

Profile facts surface in agent context — research, code review, management prep, and cockpit chat all have access to the operator profile.

### LLM Cost Awareness

All LLM calls route through LiteLLM and trace to Langfuse. The briefing reports daily cost. The cockpit dashboard shows running cost totals.

Typical daily cost: $5–25 depending on usage intensity. Heavy subagent sessions (like Domain Lattice Engine implementation) can spike to $50+ in a day.

Cost management levers:
- Use `fast` (claude-haiku) alias for cheap quick tasks
- Use local models (Ollama) for private data or high-volume tasks
- The fallback chain (`claude-opus→sonnet→gemini-pro`) automatically routes to cheaper models on rate limits
- Monitor via Langfuse at http://localhost:3000 — filter by model, see per-generation costs

### GPU/VRAM Management

The RTX 3090 has 24GB VRAM. Only one large model loads at a time. Ollama auto-unloads idle models after 5 minutes.

Check current state: `/vram` in Claude Code.

Common model combinations:
- `nomic-embed-text` (0.5GB) — always loaded, needed for all embedding
- `qwen2.5-coder:32b` (18GB) — coding tasks, leaves room for embed model
- `qwen3:30b-a3b` (18GB) — general reasoning, MoE architecture
- `deepseek-r1:14b` (9GB) — reasoning, can coexist with smaller models

If VRAM is full, Ollama queues requests until a model unloads. The health monitor checks VRAM pressure and warns if temperature exceeds thresholds.

### Backup Verification

Backups run Sunday at 02:00. Verify they're working:

```bash
ls -la <backups>/
```

Each backup directory contains: `claude-config/`, `qdrant/` (7 collection snapshots), `postgres/` (database dumps), `n8n/` (workflows + credentials), `systemd/`, `profiles/`, `hotkeys/`, `langfuse-prompts.json`. Last 8 backups retained.

### Precedent System

When domain axiom T0 blocks overlap with constitutional T0 blocks, the system flags "supremacy tensions." These aren't violations — they're structural overlaps that need explicit operator reasoning.

Review them: `/axiom-review`. Record a precedent with your reasoning. The precedent store (Qdrant `axiom-precedents` collection) maintains a case-law database with authority hierarchy: operator > agent > derived.

Recorded precedents filter out of future health checks. Unreviewed tensions cause the health monitor to report DEGRADED.

### Multi-Channel Access Matrix

| Channel | Best For |
|---------|----------|
| Claude Code | Full system control — all agents, MCP tools, code, infrastructure |
| Cockpit Web | Interactive dashboard — health, nudges, domain status, cost, briefings, scout reports |
| Obsidian | Knowledge — notes, people management, chat with context, vault search |
| Phone (ntfy) | Alerts — briefings, health failures, nudge digests |
| Telegram | Quick capture — notes from mobile → `00-inbox/` |
| Open WebUI | Web chat — when you want browser-based LLM conversation |

### Monthly Checklist

- [ ] Review drift-detector output for accumulated documentation drift
- [ ] Check scout reports — are any stack components flagging risk?
- [ ] Verify backups are running and directories are populated
- [ ] Check Qdrant collection sizes: are they growing as expected?
- [ ] Review Langfuse traces — are error rates nominal?
- [ ] Run a full profiler pass: `uv run python -m agents.profiler --auto`
- [ ] Check domain health in cockpit — are all 4 domains showing momentum?
- [ ] Review and act on any pending axiom precedents
- [ ] Consider if any new domain is emerging (check emergence nudges)
- [ ] Verify vault git sync is current across all devices

---

## Use Cases and Optimal Workflows

### "I need to prepare for a 1:1"

1. In Obsidian, open the person note (or create one: QuickAdd → New Person)
2. In the Hapax Chat sidebar, type `/prep`
3. The system reads the person note (frontmatter: cognitive load, skill level, will signal, coaching status, career goal) plus recent meeting notes and coaching hypotheses
4. It returns talking points, open loops, and questions to ask — never feedback language
5. Alternatively, from CLI: `uv run python -m agents.management_prep --person "Alice"`

### "I need a team snapshot before a leadership meeting"

```bash
uv run python -m agents.management_prep --team-snapshot
```
Or in Obsidian, open a team-state note and type `/team-risks`. The system aggregates all person notes, assesses Larson state (falling-behind/treading-water/repaying-debt/innovating), flags capacity risks, and identifies stale 1:1s or overdue coaching.

### "I want to research something with full system context"

```bash
uv run python -m agents.research "What's the current state of the Qdrant migration?"
```
The research agent queries RAG document chunks, includes operator profile context, and synthesizes a grounded answer with source citations.

### "I ingested a bunch of documents and want to know what's new"

The digest agent aggregates recently ingested RAG content:
```bash
uv run python -m agents.digest
```
It runs daily at 06:45 and writes to the vault at `30-system/`.

### "Something feels broken"

1. Run `/status` in Claude Code (or `uv run python -m agents.health_monitor`)
2. The health monitor checks all probes and reports exactly what's failing
3. Run with `--fix` to auto-remediate common issues:
   ```bash
   uv run python -m agents.health_monitor --fix
   ```
4. Check `--history` for patterns:
   ```bash
   uv run python -m agents.health_monitor --history
   ```

### "I want to process a meeting transcript"

```bash
uv run python -m agents.meeting_lifecycle --transcript ~/Downloads/meeting.vtt
```
Supports VTT, SRT, and speaker-labeled text. Extracts action items, updates relevant meeting notes in the vault, and links to person notes.

### "I want to evaluate a code change"

```bash
uv run python -m agents.code_review path/to/file.py
```
Reviews with operator context (coding preferences from profile), checks axiom compliance, and provides actionable feedback.

### "I want to import data from Google Takeout"

```bash
cd <ai-agents> && eval "$(<.envrc)"
uv run python -m shared.takeout --list-services ~/Downloads/takeout.zip
uv run python -m shared.takeout ~/Downloads/takeout.zip --services chrome,keep,calendar --since 2025-01-01
```
Dual-path processing: unstructured content → RAG pipeline, structured data → direct profile facts (zero LLM cost).

### "I want to check if my docs match reality"

```bash
uv run python -m agents.drift_detector
```
Compares documentation claims against actual system state. Run with `--fix` to auto-correct drift, `--json` for structured output.

---

## Quick Reference

### Essential Commands

```bash
# Health
cd <ai-agents> && eval "$(<.envrc)"
uv run python -m agents.health_monitor           # Check health
uv run python -m agents.health_monitor --fix      # Auto-fix
uv run python -m agents.health_monitor --history  # Trend

# Briefing
uv run python -m agents.briefing --hours 24 --save

# Cockpit
uv run cockpit                                     # API server (port 8051 via Docker)
uv run cockpit --once                              # Plain text CLI snapshot
uv run cockpit --color                             # Rich CLI snapshot
cd <cockpit-web> && pnpm dev              # Web frontend (port 5173)

# Docker
cd ~/llm-stack
docker compose --profile full up -d               # Start everything
docker compose ps                                  # Status
docker compose logs litellm --tail 20             # Debug

# Systemd timers
systemctl --user list-timers                      # All timer schedules
systemctl --user status health-monitor.timer      # Specific timer
journalctl --user -u health-watchdog -n 20        # Timer service logs

# VRAM
nvidia-smi --query-gpu=memory.used,memory.total,memory.free --format=csv,noheader,nounits

# Obsidian plugin
cd <obsidian-hapax> && pnpm run build    # Rebuild after changes
```

### Key Paths

| Path | What |
|------|------|
| `<llm-stack>/` | Docker Compose, service configs |
| `<ai-agents>/` | Agent implementations + cockpit API |
| `<hapaxromana>/` | Architecture specs, axioms, this manual |
| `<hapax-system>/` | Claude Code skills, agents, rules, hooks |
| `<cockpit-web>/` | Web dashboard (React SPA) |
| `<obsidian-hapax>/` | Obsidian plugin |
| `<rag-pipeline>/` | Docling + watchdog RAG ingestion (deprecated — now in ai-agents) |
| `<work-vault>/` | Obsidian Work vault (syncs via GitDoc) |
| `<personal-vault>/` | Obsidian Personal vault (home only) |
| `~/documents/rag-sources/` | RAG ingestion drop zone |
| `<backups>/` | Weekly backups |
| `<cache>/axiom-audit/` | Axiom audit trail |
| `<systemd-user>/` | Timer/service definitions |

### Model Aliases (via LiteLLM at localhost:4000)

| Alias | Model | When to Use |
|-------|-------|-------------|
| `claude-opus` | claude-opus-4 | Complex analysis |
| `claude-sonnet` / `balanced` | claude-sonnet-4 | Default for most agents |
| `claude-haiku` / `fast` | claude-haiku-4.5 | Cheap quick tasks |
| `gemini-pro` | gemini-2.5-pro | Google's reasoning model |
| `gemini-flash` | gemini-2.5-flash | Fast Google model |
| `qwen-coder-32b` / `coding` | qwen2.5-coder:32b | Code generation (local) |
| `qwen-7b` / `local-fast` | qwen2.5:7b | Lightweight local tasks |
| `nomic-embed` | nomic-embed-text-v2-moe | Embeddings (768d) |

Wildcard routes (`anthropic/*`, `gemini/*`, `ollama/*`) pass through any model not explicitly aliased. Fallback chain: `claude-opus→sonnet→gemini-pro`, `claude-sonnet→gemini-pro`, `claude-haiku→gemini-flash`.

### Secrets

All in `pass` (GPG-encrypted). Access: `pass show <path>`. Per-directory `.envrc` files auto-load via direnv. Never hardcode secrets.

---

## Agent Reference

All agents invoked as: `cd <ai-agents> && eval "$(<.envrc)" && uv run python -m agents.<name> [flags]`

| Agent | Purpose | LLM? | Key Flags |
|-------|---------|------|-----------|
| audio_processor | Ambient audio VAD, classification, diarization, transcription | No | `--process`, `--stats`, `--reprocess FILE` |
| briefing | Daily system briefing from activity data + health snapshot | Yes | `--save`, `--hours N`, `--json`, `--notify` |
| chrome_sync | Chrome browsing history and bookmarks RAG sync | No | `--full-sync`, `--auto`, `--stats` |
| claude_code_sync | Claude Code JSONL transcript parsing for RAG | No | `--full-sync`, `--auto`, `--stats` |
| code_review | Code review from diff, file, or stdin | Yes | `path`, `--diff`, `--model` |
| demo | Audience-tailored demo generation from natural language | Yes | `request`, `--audience`, `--format`, `--duration`, `--voice` |
| demo_eval | Demo evaluation and iterative improvement via rubrics | Yes | `--demo-dir PATH`, `--max-iterations N`, `--pass-threshold N` |
| digest | Content digest aggregating recent RAG documents + vault items | Yes | `--save`, `--hours N`, `--json`, `--notify` |
| drift_detector | Documentation drift detection: live infra vs docs | Yes | `--fix`, `--json` |
| gcalendar_sync | Google Calendar event indexing for RAG | No | `--auth`, `--full-sync`, `--auto`, `--stats` |
| gdrive_sync | Google Drive smart tiered RAG sync | No | `--auth`, `--full-scan`, `--auto`, `--fetch ID`, `--stats` |
| gmail_sync | Gmail metadata indexing for RAG (metadata-only by default) | No | `--auth`, `--full-sync`, `--auto`, `--stats` |
| hapax_voice | Voice interaction daemon (wake word, presence, TTS/STT) | Yes | `--config PATH`, `--check` |
| health_monitor | Deterministic stack health checks + auto-fix | No | `--fix`, `--yes`, `--check GROUPS`, `--json`, `--verbose` |
| ingest | RAG document ingestion (Docling + watchdog + Qdrant) | No | `--bulk-only`, `--watch-only`, `--retry-status`, `--force` |
| knowledge_maint | Qdrant maintenance: stats, stale pruning, dedup | Optional | `--apply`, `--collection NAME`, `--json`, `--summarize` |
| management_prep | 1:1 prep, team snapshots, management overviews | Yes | `--person NAME`, `--team-snapshot`, `--overview` |
| meeting_lifecycle | Meeting prep, transcript processing, weekly review | Yes | `--prepare`, `--transcript FILE`, `--weekly-review` |
| obsidian_sync | Obsidian vault RAG sync with frontmatter extraction | No | `--full-sync`, `--auto`, `--stats` |
| profiler | Operator profile extraction from local data sources | Yes | `--auto`, `--source TYPE`, `--digest`, `--show`, `--curate` |
| query | CLI tool for testing RAG retrieval against Qdrant | No | `query`, `-c COLLECTION`, `-n LIMIT`, `--stats` |
| research | RAG-enabled research with Qdrant retrieval | Yes | `query`, `--interactive` |
| scout | Horizon scanner evaluating stack vs frontier alternatives | Yes | `--json`, `--save`, `--component NAME`, `--notify` |
| youtube_sync | YouTube subscriptions, likes, playlists RAG sync | No | `--auth`, `--full-sync`, `--auto`, `--stats` |

---

## Data Flow

### The Universal Pattern

Nearly all data pipelines converge through two paths:

1. **RAG path**: Source → sync agent → `~/documents/rag-sources/<service>/*.md` → `ingest.py` (watchdog) → Docling parse → nomic-embed-text embedding → Qdrant `documents` collection
2. **Profile bridge**: Every sync agent also writes `*-profile-facts.jsonl` to `<cache>/<agent>/` → profiler loads these as zero-LLM-cost deterministic facts → Qdrant `profile-facts` collection

### Ambient Audio Pipeline

```
Mic (Blue Yeti via PipeWire) → audio-recorder.service (ffmpeg, 15-min FLAC segments)
  → ~/audio-recording/raw/rec-*.flac
    → audio-processor (VAD + transcription) → ~/documents/rag-sources/audio/*.md
    → ingest.py → Qdrant "documents" (source_service: ambient-audio)
  → audio-archiver (rclone, files >48h) → Google Drive gdrive:audio-archive/
```

### Google Sync Agents

```
Google Drive API   → gdrive_sync   → ~/documents/rag-sources/gdrive/   (source_service: gdrive)
Google Calendar API → gcalendar_sync → ~/documents/rag-sources/gcalendar/ (source_service: gcalendar)
Gmail API          → gmail_sync    → ~/documents/rag-sources/gmail/    (source_service: gmail)
YouTube API        → youtube_sync  → ~/documents/rag-sources/youtube/  (source_service: youtube)
  └→ all → ingest.py → Qdrant "documents"
```

All four share OAuth2 via `shared/google_auth.py` (single token in `pass show google/token`).

### Local Sync Agents

```
Chrome History SQLite  → chrome_sync      → ~/documents/rag-sources/chrome/      (source_service: chrome)
Claude Code JSONL      → claude_code_sync → ~/documents/rag-sources/claude-code/ (source_service: claude-code)
Obsidian vault (Personal) → obsidian_sync → ~/documents/rag-sources/obsidian/    (source_service: obsidian)
  └→ all → ingest.py → Qdrant "documents"
```

### Knowledge → Briefing Pipeline

```
Langfuse API ──────────┐
Health monitor ────────┤
Scout report ──────────┤
Digest output ─────────┤  → briefing agent (1 LLM call)
Calendar context ──────┤      → profiles/briefing.md
Profile data ──────────┤      → Obsidian vault 30-system/
Axiom governance ──────┘      → ntfy push notification
```

The digest agent runs at 06:45 (15 min before briefing) to aggregate recently ingested content. The briefing consumes digest output at 07:00.

---

## Sync Agent Data Sources

| Agent | Source | Data Types | Refresh | State Tracking |
|-------|--------|------------|---------|----------------|
| gdrive_sync | Google Drive API | Docs, sheets, slides (exported); binaries get metadata stubs; >25MB metadata-only | Every 2h | Changes API `start_page_token` + per-file MD5 |
| gcalendar_sync | Google Calendar API | Events (30d back, 90d forward; 14d RAG window) | Every 30min | Calendar sync token |
| gmail_sync | Gmail API | Email metadata; body opt-in for IMPORTANT/STARRED labels | Every 1h | History ID high-water mark |
| youtube_sync | YouTube Data API | Liked videos (200 max), subscriptions, playlists | Every 6h | Timestamp only (full sync each run) |
| chrome_sync | Local SQLite + JSON | Domain visit summaries (min 3 visits), bookmarks | Every 1h | WebKit timestamp high-water + bookmark hash |
| claude_code_sync | Local JSONL | Transcript sessions (user + assistant messages) | Every 2h | Per-file size + mtime |
| obsidian_sync | Local vault files | Notes with frontmatter, tags, wikilinks | Every 30min | Per-note content MD5 hash |

State files stored at `<cache>/<agent>-sync/state.json`. Google agents authenticate via shared OAuth2 token.

---

## Where Agent Output Goes

| Agent | File Output | Qdrant | Vault | Notify |
|-------|------------|--------|-------|--------|
| briefing | `profiles/briefing.md` | — | `30-system/briefings/` + nudges | ntfy + desktop |
| digest | `profiles/digest.md`, `digest.json` | — | `30-system/` | ntfy |
| health_monitor | `profiles/health-history.jsonl` | — | — | — |
| drift_detector | In-place doc edits + git commits (`--fix --apply`) | — | — | ntfy on applied fixes |
| scout | `profiles/scout-report.json` | — | `30-system/` | ntfy |
| profiler | `profiles/operator-profile.json`, `operator-profile.md`, `operator.json` | `profile-facts` | — | — |
| management_prep | — | — | `10-work/1on1-prep/` | — |
| meeting_lifecycle | — | — | Updates meeting notes | — |
| knowledge_maint | `profiles/knowledge-maint-report.json` | Prunes `documents`, `profile-facts`, `claude-memory` | — | ntfy |
| demo | `<ai-agents>/output/demos/` | — | — | — |
| ingest | `<cache>/rag-ingest/retry-queue.jsonl` | `documents` | — | — |
| *sync agents* | `~/documents/rag-sources/<service>/` | `documents` (via ingest) | — | — |
| code_review | stdout | — | — | — |
| research | stdout | — | — | — |
| query | stdout | — | — | — |

`profiles/` = `<ai-agents>/profiles/`. Sync agents also write `*-profile-facts.jsonl` to `<cache>/<agent>/` for the profiler bridge. `hapax_voice` is a notification *consumer* — it subscribes to ntfy and delivers alerts via TTS audio.

---

## Troubleshooting

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| Docker container not running | Container crashed or OOM | `cd ~/llm-stack && eval "$(<.envrc)" && docker compose up -d <service>` |
| `nvidia-smi` fails | Driver crash, kernel module unloaded | `sudo modprobe nvidia`; reboot if persistent |
| VRAM >90%, model loading fails | Multiple Ollama models loaded | `docker exec ollama ollama stop <model>`; Ollama auto-unloads after 5 min idle |
| GPU temperature >80°C | Sustained inference, poor airflow | Unload models, check fans |
| Langfuse auth failure (49x pattern) | GPG `scdaemon` crash blocks `pass show` | `gpgconf --kill scdaemon && gpgconf --launch scdaemon`; add `disable-scdaemon` to `<gnupg>/gpg-agent.conf` if no hardware key |
| LiteLLM 401 errors | Stale API key (same `pass` failure) or key mismatch | `pass show litellm/master-key` to verify; `docker compose restart litellm` |
| Sonnet rate limiting (429s) | Concurrent agent LLM calls saturating Anthropic limits | Reduce `max_parallel_requests` in litellm-config.yaml; stagger timer schedules |
| RAG retry queue stuck (>50 items) | macOS resource forks (`._*`) or binary files failing Docling | `> <cache>/rag-ingest/retry-queue.jsonl` to clear; pre-filters now skip these |
| Qdrant unreachable | Container down or not started | `docker compose up -d qdrant`; collections auto-create on first use |
| Systemd timer not firing | Unit files out of sync after code update | `cd <ai-agents> && make install-systemd` |
| ntfy notifications silent | ntfy container stopped | `docker compose up -d ntfy`; fallback: `notify-send` fires for desktop |
| DNS stale after container restart | Docker internal DNS cache stale | Full restart: `docker compose down && docker compose up -d` |
| Uptime shows 0% but system is fine | Single degraded check taints all runs | Check which check is persistently degraded via `--history`; fix the underlying check |
| `pass show` hangs | GPG agent locked or pinentry blocked | `gpgconf --kill gpg-agent && gpgconf --launch gpg-agent` |
| Ollama model missing | Model not pulled after container rebuild | `docker exec ollama ollama pull <model>` |
| Profile stale (>48h) | `profile-update.timer` failed | `uv run python -m agents.profiler --auto` |
| Disk usage >85% | Docker images, audio recordings accumulating | `docker system prune -f`; audio-archiver moves raw audio daily at 03:00 |
| Service latency degraded | Container resource contention | `docker stats` to check; restart the offending container |
| Axiom hooks not firing | `install.sh` not re-run after hapax-system update | `cd <hapax-system> && ./install.sh`; restart Claude Code |
| Voice daemon VRAM lock stale | `hapax-voice` crashed without releasing lock | `rm <cache>/hapax-voice/vram.lock`; lock class auto-detects stale PIDs |

For any issue: start with `/status` (or `uv run python -m agents.health_monitor`). Run with `--fix --yes` to auto-remediate common failures.

---

## Principles

1. **The system compensates for executive function challenges.** If you have to remember to do something routine, the system has failed. Automate it.
2. **LLMs prepare, humans deliver.** The system aggregates signals and surfaces patterns. It never makes people decisions for you.
3. **Single user, single machine.** No auth, no multi-user, no collaboration features. This constraint simplifies everything.
4. **Route everything through LiteLLM.** Universal observability. If a model call doesn't go through the proxy, it's invisible.
5. **Git bridges the boundary.** Two vaults: Work vault syncs via GitDoc (git auto-commit + push) to corporate work laptop, Personal stays local-only.
6. **Evidence before assertions.** The system states epistemic confidence. "I don't know" is better than speculation.
