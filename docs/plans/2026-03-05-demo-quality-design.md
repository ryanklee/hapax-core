# Demo Quality System — Design Document

**Date:** 2026-03-05
**Status:** Approved

## Problem

The demo generator produces mechanically correct output (screenshots, voice, video) but the *content quality* is weak. The entire intelligence lives in a single LLM call with ~25 lines of prompt and a 4K-char system description dump. There is no narrative structure, no subject-matter research, no presenter style model, no quality evaluation loop, no supplementary visuals, and no duration-aware planning. For Fortune 500 internal demo quality — architecture reviews, executive briefings, tech talks — this is insufficient.

## Goal

Every generated demo must be thoroughly informed on its subject matter, follow effective narrative methods appropriate to the audience and intention, reflect the operator's natural presentation style, be grounded in real system data and (where appropriate) external research, include clean supplementary visuals, and meet subjective and objective quality standards across all dimensions. Demo quality is not negotiable.

## Design Decisions

### Approach: Multi-Stage Deep Planning Pipeline

Replace the single LLM call with a pipeline of focused stages. Each stage does one thing well. This is chosen over prompt engineering (quality ceiling too low) and human-in-the-loop (defeats automation purpose).

### Key Principles

- **Duration drives everything.** Scene count, depth, narration length, pacing — all derived from target duration.
- **Research before planning.** The LLM plans from rich, current, audience-filtered context — not a raw markdown dump.
- **Proven narrative frameworks.** Not one implicit structure. Multiple frameworks selected by audience + intention.
- **Self-critique is mandatory.** Every script is evaluated against 8 quality dimensions before execution.
- **Presenter style is encoded.** The operator's methodical-explainer voice is a first-class artifact, not an afterthought.
- **Visuals serve the narrative.** Screenshots, diagrams, and charts are chosen per-scene based on what communicates best.

---

## Pipeline Architecture

```
User Request ("health monitoring for leadership" --duration 10m --format video)
    │
    ▼
┌─ Stage 0: System Readiness Gate ──────────────────────┐
│  Health monitor --fix, verify services, run briefing   │
│  Stop if critical issues unresolvable                  │
└──────────────────┬────────────────────────────────────┘
                   │
    ▼
┌─ Stage 1: Subject Research ───────────────────────────┐
│  Gather: introspect, health, Langfuse, Qdrant stats    │
│  Audience-filtered: web research for leadership/peers  │
│  Produces: structured context document                 │
└──────────────────┬────────────────────────────────────┘
                   │
    ▼
┌─ Stage 2: Script Planning (LLM) ─────────────────────┐
│  Inputs: context doc, persona, style guide, narrative  │
│          framework, duration constraints               │
│  Selects: narrative framework, visual types per scene  │
│  Outputs: DemoScript (enhanced)                        │
└──────────────────┬────────────────────────────────────┘
                   │
    ▼
┌─ Stage 3: Self-Critique & Revision (LLM) ────────────┐
│  Evaluates: 8 quality dimensions                       │
│  Loop: revise if Critical or >2 Important issues       │
│  Max 3 iterations                                      │
│  Outputs: finalized DemoScript                         │
└──────────────────┬────────────────────────────────────┘
                   │
    ▼
┌─ Stage 4: Visual Generation ──────────────────────────┐
│  Screenshots: Playwright (existing)                    │
│  Diagrams: D2 → PNG (new)                              │
│  Charts: Matplotlib → PNG (new)                        │
│  Outputs: visual map {scene_title: Path}               │
└──────────────────┬────────────────────────────────────┘
                   │
    ▼
┌─ Stages 5-8: Slides → Voice → Video → HTML Player ───┐
│  (existing pipeline, unchanged)                        │
└───────────────────────────────────────────────────────┘
```

---

## Stage 0: System Readiness Gate

Before generating any demo, ensure the system is presentable.

### Checks

1. **Health monitor** (`--fix` mode) — auto-fix what's fixable
2. **Briefing** (recent window) — get fresh operational summary
3. **Scout** (check staleness) — ensure horizon scan is current
4. **Cockpit services** — cockpit API (:8050) + web (:5173) must be running
5. **TTS** (if video format) — Chatterbox container up, voice sample present

### Behavior

- Auto-fixes what it can (health monitor --fix)
- If critical issues remain: reports and stops with actionable next steps
- Outputs (health snapshot, briefing) feed into Stage 1 as context

---

## Stage 1: Subject Research

Gathers rich, current, audience-filtered context.

### Data Sources

| Source | Method | What it provides |
|--------|--------|-----------------|
| Health monitor | `--json` output | Current health score, check counts, failure history |
| Introspect | `--json` output | Live containers, ports, versions, timer schedules |
| Component registry | YAML read | Component descriptions, categories, relationships |
| Langfuse metrics | API call | Token usage, cost trends, model distribution, trace counts |
| Qdrant stats | API call | Collection sizes, document counts, embedding stats |
| CLAUDE.md | Full file read | Architecture, conventions, agent table |
| Operator profile | Qdrant profile-facts search | How/why the system was built, operator context |
| Web research | Tavily search | Industry context, SRE patterns, LLM infra trends |
| Briefing output | From Stage 0 | Recent operational summary |

### Audience Filtering

| Source | Family | Peers | Leadership | Team |
|--------|--------|-------|-----------|------|
| Health (summary) | ✓ | ✓ | ✓ | ✓ |
| Health (detail) | - | ✓ | ✓ | - |
| Introspect | - | ✓ | ✓ | partial |
| Component registry | - | ✓ | ✓ | partial |
| Langfuse metrics | - | ✓ | ✓ | - |
| Qdrant stats | - | ✓ | partial | - |
| CLAUDE.md (full) | - | ✓ | ✓ | - |
| Operator profile | ✓ | - | - | - |
| Web research | - | ✓ | ✓ | - |

### Output

Structured context document with sections, real numbers, and audience-appropriate detail level.

---

## Stage 2: Script Planning

### Inputs

- Structured context document (from Stage 1)
- Audience persona (from demo-personas.yaml)
- Presenter style guide (from presenter-style.yaml)
- Selected narrative framework (based on audience + intention)
- Duration constraints (explicit or audience-default)

### Narrative Frameworks

| Framework | When | Structure |
|-----------|------|-----------|
| **Problem → Solution → Benefit** | Leadership, architecture reviews | Frame challenge → show approach → quantify impact |
| **Guided Tour** | Family, team members | "Let me show you around" → walk capabilities → "what it means for you" |
| **Design Rationale** | Technical peers | "Here's what we built" → "here's WHY" → trade-offs considered |
| **Operational Cadence** | Team, leadership | "What happens daily/weekly" → show rhythm → how it reduces toil |

The LLM receives the framework description and structures its script accordingly.

### Duration-Driven Constraints

Target duration → scene budget → depth per scene → narration length → pacing.

| Duration | Scenes | Depth | Words/Scene | Style |
|----------|--------|-------|-------------|-------|
| 2-3 min | 3-4 | Headlines only | 15-25 | Executive summary |
| 5-7 min | 5-7 | Key points + context | 30-50 | Standard briefing |
| 10-15 min | 8-12 | Detailed explanations | 50-80 | Deep dive |
| 15-20 min | 10-15 | Full rationale | 60-100 | Tech talk |

The LLM receives explicit constraints: "You have 7 minutes. That's approximately 6 scenes at 70 seconds each. Each scene narration should be 40-55 words (roughly 20 seconds of speech at natural pace)."

Audience defaults: family=3m, team=7m, leadership=10m, peers=12m.

### Visual Type Selection

Each scene gets a `visual_type` field:

- **screenshot** — when showing the actual UI is the point
- **diagram** — when explaining structure or relationships
- **chart** — when a trend or comparison tells the story better

### Enhanced Model

```python
class DemoScene(BaseModel):
    title: str
    narration: str
    duration_hint: float
    key_points: list[str]
    screenshot: ScreenshotSpec
    visual_type: Literal["screenshot", "diagram", "chart"] = "screenshot"
    diagram_spec: str | None = None       # D2 source or chart description
    research_notes: str | None = None     # grounding for this scene's claims
```

---

## Stage 3: Self-Critique & Revision

### Quality Dimensions

| Dimension | Checks |
|-----------|--------|
| **Narrative coherence** | Follows selected framework? Scenes build logically? Clear arc? |
| **Audience calibration** | Vocabulary appropriate? Concepts at right level? Respects show/skip? |
| **Content adequacy** | Enough substance for duration? Each scene justifies its existence? |
| **Duration feasibility** | Word count × speech rate ≈ target? Pacing realistic? |
| **Style compliance** | Matches presenter style guide? No corporatisms? Functional transitions? |
| **Factual grounding** | Claims match system state? Numbers from research, not hallucinated? |
| **Visual appropriateness** | Right mix of screenshots/diagrams/charts? Each visual serves a purpose? |
| **Key points quality** | Bullets substantive, not vague? Right density for audience? |

### Loop

```
Draft script
    → Critique LLM evaluates all 8 dimensions
    → Returns: {dimension: pass|fail, severity: critical|important|minor, issues: [...]}
    → If any Critical OR >2 Important: revise and re-evaluate
    → Max 3 iterations
    → Final pass must have 0 Critical, ≤1 Important
```

The critique prompt receives: style guide, research context, narrative framework, AND duration constraints.

---

## Stage 4: Visual Generation

### Architecture Diagrams (D2)

- Generated from component-registry.yaml + introspect data
- Gruvbox-themed via D2 custom theme CSS
- Rendered to PNG at 1920x1080 via `d2 --theme` CLI
- D2 binary required (installable via package manager or direct download)
- Used for: system topology, data flow, agent orchestration, service dependencies

### Data Visualizations (Matplotlib)

- Generated from real system data (Langfuse API, health history, Qdrant stats)
- Custom `.mplstyle` file with Gruvbox palette
- Chart types: line (trends), bar (comparisons), gauge (health score)
- Rendered to PNG at 1920x1080
- No extra dependencies (matplotlib bundled with scientific Python, or add explicitly)

### Screenshots (Playwright — existing)

- Unchanged from current pipeline
- Used when showing actual UI is the point

---

## Presenter Style Guide

Stored as `profiles/presenter-style.yaml`. Loaded into every LLM call that generates narration.

```yaml
voice: first-person  # "I built this because..." not passive/third
cadence: state-explain-show  # State the thing → explain why → show it working
transitions: functional  # "That handles monitoring. Next is agent coordination."

avoid:
  - Corporate filler (leverage, synergize, best-in-class, robust, scalable)
  - Hedging (kind of, sort of, basically, essentially)
  - Breathless enthusiasm (amazing, incredible, game-changing, exciting)
  - Rhetorical questions as transitions
  - "Today I'm going to show you..." openings
  - "Any questions?" or "Thank you" closings

embrace:
  - Precise vocabulary and concrete numbers
  - Honest trade-offs ("works well for X but I'd do Y differently")
  - Short, declarative sentences
  - Occasional dry humor (understated, never forced)
  - Design rationale (why this way, not just what)

opening: Start with the problem or the thing itself. No preamble.
closing: Land on impact or next step. No ceremony.
```

---

## CLI Changes

```bash
uv run python -m agents.demo "health monitoring for leadership" --duration 10m --format video
uv run python -m agents.demo "the system for a non-technical friend" --duration 3m
uv run python -m agents.demo "agent architecture for peers" --duration 15m --format slides
```

`--duration` accepts `Nm` (minutes) or `Ns` (seconds). Defaults by audience if not specified.

---

## New Files

| File | Purpose |
|------|---------|
| `agents/demo_pipeline/research.py` | Subject matter research stage |
| `agents/demo_pipeline/readiness.py` | System readiness gate |
| `agents/demo_pipeline/critique.py` | Self-critique evaluation + revision loop |
| `agents/demo_pipeline/diagrams.py` | D2 diagram generation |
| `agents/demo_pipeline/charts.py` | Matplotlib data visualization |
| `agents/demo_pipeline/narrative.py` | Narrative framework definitions + selection |
| `profiles/presenter-style.yaml` | Presenter style guide |
| `profiles/gruvbox.mplstyle` | Matplotlib Gruvbox theme |

### Dependencies

- `jinja2>=3.1` — already added
- `matplotlib>=3.9` — data visualization (new)
- D2 CLI binary — architecture diagrams (installed separately, not a Python dep)

---

## What Changes vs. Current Pipeline

| Component | Current | New |
|-----------|---------|-----|
| System description | 4K-char CLAUDE.md truncation | Rich, multi-source, audience-filtered context doc |
| Narrative structure | Implicit (whatever LLM produces) | Explicit framework selected by audience+intention |
| Planning prompt | 25 lines, generic | Deep context + framework + style guide + duration constraints |
| Quality evaluation | None | 8-dimension self-critique with revision loop |
| Presenter style | Persona tone word ("warm") | Full style guide (voice, cadence, avoid/embrace, transitions) |
| Duration | Afterthought (duration_hint) | Primary constraint driving all planning |
| Visuals | Screenshots only | Screenshots + D2 architecture diagrams + Matplotlib data charts |
| Research | None | Audience-dependent, from live system data and web search |
| System readiness | None | Health check, service verification, baseline refresh |

---

## What Stays the Same

- Screenshot capture (Playwright)
- Voice generation (Chatterbox TTS)
- Video assembly (MoviePy)
- Slide generation (Marp)
- HTML player + chapter injection (just implemented)
- Audience persona YAML structure (extended, not replaced)
- DemoScript model (extended with new fields, backward compatible)
- Output directory structure
- Cockpit API integration
- Langfuse tracing
