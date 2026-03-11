# Demo Generator — Design Document

**Date:** 2026-03-04
**Status:** Approved

## Goal

Enable the operator to say "produce a demo of X for Y" via Claude Code and receive a narrated MP4 video — screenshots of the live system with voice-cloned narration, tailored to the specified audience.

## Examples

```
"Produce a demo of the entire system for a non-technical friend"
"Produce a demo of the context maintenance system for a Senior Enterprise Architect on my Platform Services Team"
"Produce a demo of health monitoring" --audience family --format slides-only
```

## Architecture

A new Tier 2 Pydantic AI agent (`demo`) orchestrates an LLM planning phase followed by a deterministic four-stage pipeline.

```
User Request (natural language)
        │
        ▼
┌──── Demo Agent (LLM) ────┐
│  1. Parse scope + audience │
│  2. Resolve audience persona│
│  3. Plan scenes (DemoScript)│
│  4. Write narration per scene│
└───────────┬────────────────┘
            │
            ▼
┌──── Pipeline (deterministic) ────┐
│  Stage 1: Screenshot Capture      │
│  Stage 2: Voice Generation        │
│  Stage 3: Video Assembly          │
│  Stage 4: Cleanup & Delivery      │
└───────────┬──────────────────────┘
            │
            ▼
      output/demos/{id}/demo.mp4
```

The agent produces structured output (DemoScript). The pipeline consumes it. LLM work is separated from media production.

---

## Audience Persona System

Audience personas define what to show, what to skip, and how to talk about it. Stored as `profiles/demo-personas.yaml`, loaded by the agent.

### Built-in Archetypes

| Archetype | Key Traits | Show | Skip | Tone |
|-----------|-----------|------|------|------|
| `family` | Non-technical, cares about outcomes | High-level outcomes, visual polish, automation magic | Architecture, code, infra details | Warm, analogies, zero jargon |
| `technical-peer` | Fellow engineer, evaluates design | Architecture, agent pipeline, Qdrant/LiteLLM, code patterns | Management domain, personal context | Direct, technical vocabulary, "here's why" |
| `leadership` | Enterprise architect / engineering manager | System topology, reliability, observability, cost, scalability | Implementation details, personal automations | Professional, patterns and principles |
| `team-member` | Direct report, wants to understand tooling | Cockpit dashboard, agent capabilities, daily workflow | Personal data, music production, deep infra | Practical, "here's how you'd use this" |

### Resolution

The LLM resolves natural language audience descriptions to archetypes plus context:
- "a non-technical friend" → `family` archetype + operator profile personalization
- "Senior EA on Platform Services" → `leadership` archetype + "Platform Services, enterprise architecture vocabulary"

Operator profile facts from Qdrant (`profile-facts` collection) provide personal context the LLM weaves into narration.

---

## Demo Agent

**Location:** `<ai-agents>/agents/demo.py`

**Invocation:**
```bash
uv run python -m agents.demo "the entire system for a non-technical friend"
uv run python -m agents.demo "health monitoring" --audience family --format slides-only
```

**Also:** `POST /api/agents/demo/run` via cockpit API with SSE progress streaming.

### Agent Responsibilities (LLM-driven)

1. **Parse request** — extract scope (what part of the system) and audience (who's watching)
2. **Resolve audience** — match to archetype, pull operator profile facts for personalization
3. **Plan scenes** — decide which components to demo, in what order, at what depth
4. **Write narration** — generate spoken-word narration per scene, calibrated to audience

### Agent Does NOT Do (delegated to pipeline)

- Take screenshots (Playwright subprocess)
- Generate audio (Chatterbox subprocess)
- Assemble video (MoviePy subprocess)

### Structured Output

```python
class ScreenshotSpec(BaseModel):
    url: str                        # e.g., "http://localhost:5173"
    viewport: tuple[int, int]       # (1920, 1080)
    actions: list[str]              # Playwright actions before capture
    wait_for: str | None            # text/selector to wait for
    capture: str                    # "fullpage" | "viewport" | selector

class DemoScene(BaseModel):
    title: str
    narration: str                  # spoken text for this scene
    duration_hint: float            # estimated seconds
    screenshot: ScreenshotSpec

class DemoScript(BaseModel):
    title: str
    audience: str                   # resolved archetype
    scenes: list[DemoScene]
    intro_narration: str            # opening before first screenshot
    outro_narration: str            # closing
```

### Scope Resolution

The agent maps natural language to system components using:
- `introspect` output (containers, timers, agents, collections)
- `component-registry.yaml` (16+ components with descriptions and categories)
- System documentation (CLAUDE.md, agent-architecture.md)

"Entire system" → all categories. "Health monitoring" → health-monitor agent, health panel, systemd timer, health-history.jsonl. "Context maintenance" → profiler, Qdrant, RAG pipeline, digest, knowledge maintenance.

The agent can invoke other agents (briefing, scout) to populate live data before capturing screenshots.

---

## Pipeline Stages

Four deterministic stages, each a standalone Python module.

### Stage 1: Screenshot Capture (`pipeline/screenshots.py`)

- Drives Playwright via Python package (not MCP — headless Chromium directly)
- For each scene: navigate to URL, execute actions, wait, capture at 1920x1080
- Save to `output/{demo-id}/screenshots/`
- Requires cockpit API (:8050) + cockpit-web (:5173) running — fails fast with actionable error if not

### Stage 2: Voice Generation (`pipeline/voice.py`)

- Loads operator voice sample (`profiles/voice-sample.wav`, 10-30s recording)
- For each scene narration → Chatterbox generates WAV segment
- Chatterbox runs in Docker container on GPU (port 8200)
- VRAM management: checks GPU memory, unloads Ollama models if needed, reloads after
- Save to `output/{demo-id}/audio/`

### Stage 3: Video Assembly (`pipeline/video.py`)

- MoviePy combines screenshots + audio segments
- Each scene: screenshot displayed for duration of its audio
- Crossfade transitions (0.5s) between scenes
- Intro/outro title cards (Gruvbox-styled, generated with Pillow)
- Output: `output/{demo-id}/demo.mp4` (H.264, 1080p)

### Stage 4: Cleanup & Delivery (`pipeline/output.py`)

- Write metadata JSON (title, audience, scenes, duration, timestamp)
- Optional: generate Marp slides as companion artifact
- Log to Langfuse (full trace with spans per stage)

### Orchestrator (`pipeline/orchestrator.py`)

```
DemoScript → screenshots → voice → video → output
```

Each stage reports progress via callback. Claude Code / cockpit API see streaming updates: "Capturing screenshot 3/8...", "Generating voice for scene 2/8...", "Rendering video..."

---

## Dependencies & Infrastructure

### New Python Dependencies

| Package | Purpose |
|---------|---------|
| `moviepy` | Video assembly |
| `Pillow` | Title card generation |
| `playwright` | Screenshot automation (Python package) |

### New Docker Service: Chatterbox TTS

Added to `<llm-stack>/docker-compose.yml` under `tts` profile (on-demand, not always-on):

```yaml
chatterbox:
  image: ghcr.io/resemble-ai/chatterbox:latest
  ports:
    - "127.0.0.1:8200:8200"
  deploy:
    resources:
      reservations:
        devices:
          - capabilities: [gpu]
  volumes:
    - ./profiles:/data/profiles
  profiles: [tts]
```

Start on demand: `docker compose --profile tts up -d chatterbox`

If no official Docker image exists, build from repo. Chatterbox is pip-installable, Dockerfile is ~10 lines.

### VRAM Management

Chatterbox needs ~8GB. RTX 3090 = 24GB. Options:
- Unload Ollama models before voice stage, reload after
- Accept co-residency if total VRAM < 24GB

Pipeline checks VRAM before voice stage and manages automatically.

### Voice Sample

One-time setup: record 10-30 seconds speaking naturally, save to `<ai-agents>/profiles/voice-sample.wav`. Demo agent checks for this file and prompts if missing.

### Output Directory

`<ai-agents>/output/demos/{timestamp}-{slug}/`
- `screenshots/` — captured PNGs
- `audio/` — WAV segments per scene
- `demo.mp4` — final video
- `metadata.json` — title, audience, scenes, duration, timestamp
- `script.json` — full DemoScript for reproducibility

---

## Integration Points

### Claude Code (primary interface)

Slash command or natural language. Claude Code:
1. Ensures cockpit API + web dev server running
2. Starts Chatterbox container if needed
3. Invokes `uv run python -m agents.demo "X for Y"`
4. Streams progress
5. Returns path to MP4

### Cockpit API

`POST /api/agents/demo/run` — body: `{"prompt": "..."}`, SSE progress events.

### Langfuse

Full trace with spans: LLM planning, screenshot capture, voice generation, video assembly. Token usage + wall-clock time per stage.

---

## Build Phases

Each phase produces a usable artifact:

### Phase 1: Agent + Screenshots + Slides
- Demo agent (parse, plan, narrate)
- Audience persona system (YAML archetypes)
- Screenshot pipeline (Playwright)
- Marp slide output (markdown → PDF)
- **Deliverable:** audience-tailored slide deck with live screenshots

### Phase 2: Voice Cloning + Video
- Chatterbox Docker setup
- Voice sample recording
- Voice generation pipeline
- MoviePy video assembly
- **Deliverable:** narrated MP4 video

### Phase 3: Polish
- Cockpit API integration
- Claude Code slash command
- VRAM management automation
- Langfuse tracing
- Title card generation (Gruvbox-styled)
- **Deliverable:** production-ready, one-command demo generation
