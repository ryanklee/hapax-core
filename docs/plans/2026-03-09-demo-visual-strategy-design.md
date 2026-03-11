# Demo Visual Strategy: Research-Backed Media Selection + Image Generation

**Date:** 2026-03-09
**Status:** Approved
**Scope:** agents/demo.py, agents/demo_pipeline/, profiles/

## Problem

The demo pipeline's visual selection is constraint-driven ("am I allowed another screenshot?") rather than purpose-driven ("what best illustrates this point for this audience?"). Three gaps:

1. **No conceptual/atmospheric visuals.** Every scene gets a literal screenshot, structural D2 diagram, or data chart. Abstract concepts and family audiences get the same box-and-arrow treatment as technical peers.
2. **Workflow illustrations are a knowledge-corpus gap.** The LLM invents workflow topologies during narrative construction because the research context provides facts and numbers but not workflow specifications. Plausible-looking flows may be architecturally wrong.
3. **Selection heuristic ignores multimedia learning research.** Mayer's principles (Coherence d=0.86, Multimedia d=1.39, Redundancy d=0.86) provide strong evidence for visual selection that the pipeline doesn't encode.

## Design

Two-phase approach: fix the foundation first, then add capability.

### Phase 1: Research-Backed Media Selection + Workflow Corpus

#### 1a: Purpose-Driven Visual Selection

Replace constraint-driven prompts with a decision framework grounded in multimedia learning research. The content agent receives a visual selection matrix keyed by information type and audience:

| Information Type | Technical Peer | Leadership | Family | Team Member |
|-----------------|---------------|------------|--------|-------------|
| UI feature / capability | screenshot | screenshot | screenshot | screenshot |
| Architecture / relationships | detailed D2 diagram | high-level D2 diagram | skip or simplify | D2 diagram |
| Quantitative data | chart (complex ok) | chart (KPI-focused) | chart (simple bar only) | chart |
| Dynamic behavior | screencast | screencast | screencast | screencast |
| Abstract concept / "why" | diagram with rationale | diagram with impact | illustration (Phase 2) | diagram |
| Workflow / process | D2 from corpus | D2 from corpus (simplified) | D2 from corpus (simplified) | D2 from corpus |
| Personal impact / meaning | screenshot of output | chart showing ROI | illustration (Phase 2) | screenshot |

Mayer's principles encoded as critique rules:

- **Coherence gate**: every visual must directly support the scene's key message. Reject decorative filler.
- **Redundancy guard**: if voice narration exists, on-screen text = keywords/labels only.
- **Multimedia mandate**: every content scene gets a visual, but only a relevant one.
- **No-visual option**: if nothing passes the coherence gate, use a clean title-card style slide. Better than a forced bad diagram.

Existing constraint rules (50% screenshot ratio, alternation, route limits) remain as guardrails but become secondary to purpose-driven selection.

#### 1b: Workflow Corpus

Structured registry of actual system workflows at `profiles/workflow-registry.yaml`:

```yaml
workflows:
  morning-briefing:
    trigger: "daily-briefing.timer at 07:00"
    steps:
      - "digest agent aggregates RAG content (06:45)"
      - "briefing agent consumes digest + health + calendar"
      - "LLM synthesizes operational briefing"
      - "vault_writer saves to 30-system/briefings/"
      - "ntfy push notification to mobile"
    components: [digest, briefing, vault_writer, ntfy]

  health-monitoring:
    trigger: "health-monitor.timer every 15min"
    steps:
      - "17 check groups, 75 deterministic checks"
      - "auto-fix for known failure patterns"
      - "desktop notification on failures"
      - "history logged to <cache>/hapax-agents/"
    components: [health_monitor, ntfy]

  rag-ingestion:
    trigger: "always-on watchdog + sync timers"
    steps:
      - "sync agents pull from sources (Drive, Calendar, Gmail, Chrome, Obsidian)"
      - "files land in ~/documents/rag-sources/{service}/"
      - "rag-ingest watchdog detects new files"
      - "Docling converts to markdown chunks"
      - "nomic-embed-text generates 768d vectors"
      - "Qdrant stores in 'documents' collection"
    components: [gdrive_sync, gcalendar_sync, gmail_sync, chrome_sync, obsidian_sync, rag-ingest, qdrant]
```

The research gatherer includes relevant workflows in context so D2 diagrams are drawn from actual step sequences, not hallucinated.

### Phase 2: Illustration Visual Type

New `visual_type: "illustration"` for scenes where the point is atmospheric, metaphorical, or abstract.

#### Model

| Tier | Model | Use Case | Cost |
|------|-------|----------|------|
| Default | Nano Banana (Gemini 2.5 Flash Image) | Conceptual illustrations | Free (500/day) |
| Quality | Nano Banana Pro (Gemini 3 Pro Image) | When text rendering matters | ~$0.15/image |

Route through LiteLLM for Langfuse tracing. No VRAM impact (API-based). Google API key already available via `pass show api/google`.

#### When to Use

The Phase 1 visual selection matrix gates this. Illustrations are correct when:
- The scene conveys a feeling or concept with no UI representation
- The audience is non-technical and a D2 diagram would add cognitive load
- No real data exists for a chart and no architecture relationship needs showing

The coherence gate prevents misuse: the illustration prompt must describe something directly supporting the scene's key message.

#### Style Consistency

1. Generate the first illustration in a demo
2. Use it as a style reference for all subsequent illustrations
3. Include fixed style keywords from the audience persona

Audience personas gain an `illustration_style` field:

```yaml
family:
  illustration_style: "warm minimal illustration, soft colors, approachable, no technical jargon in labels"
technical-peer:
  illustration_style: "clean technical illustration, dark background, precise lines, blueprint aesthetic"
```

#### Safety and Limits

- Max 3 illustration scenes per demo
- Never for architecture, data, or workflows (dedicated visual types exist)
- No text in generated images — all text goes in overlay (key_points, title). Sidesteps text rendering reliability entirely.
- Negative prompt always includes: "text, words, labels, letters, numbers, watermark"
- Fallback: API failure → clean title-card style slide (solid color + title text)

#### New Models

```python
class IllustrationSpec(BaseModel):
    prompt: str          # Scene-specific image generation prompt
    style: str = ""      # From persona illustration_style
    negative_prompt: str = "text, words, labels, letters, numbers, watermark"
    aspect_ratio: str = "16:9"
```

New field on DemoScene and SceneSkeleton:
```python
illustration: IllustrationSpec | None = None
```

#### New Module

`agents/demo_pipeline/illustrations.py`:
- `generate_illustrations(specs, output_dir, style_ref=None, on_progress=None) -> list[Path]`
- First call generates and saves a style reference; subsequent calls include it
- API failure returns None; caller falls back to title card

#### Critique Integration

- `visual_appropriateness`: illustration scenes must not depict architecture, data, or workflows
- `visual_substance`: illustration prompt must relate to scene's key message
- Deterministic: max 3 illustrations per demo

## Research Basis

### Mayer's Multimedia Learning Principles (key effect sizes)

| Principle | d | Implication |
|-----------|---|-------------|
| Multimedia | 1.39 | Every content scene gets a visual |
| Coherence | 0.86 | Every visual must serve the message — no decorative fills |
| Redundancy | 0.86 | Don't duplicate narration as on-screen text |
| Spatial Contiguity | 0.79 | Labels on diagrams, not separate text blocks |
| Segmenting | 0.79 | One concept per slide |
| Modality | 0.72 | Prefer voiceover to on-screen text with graphics |

### Audience-Specific Visual Strategy (from research)

- **Technical**: precise data viz, detailed architecture, code snippets. Complex charts ok.
- **Executive**: business impact, high-level diagrams, KPI charts. One message per slide.
- **Non-technical/family**: analogies, simple charts, conceptual illustrations. Break complexity into smaller visual chunks.

### Seductive Details Effect

Decorative images that are interesting but irrelevant actively harm comprehension. They consume limited working memory, activate incorrect mental schemas, and crowd out essential content. Effect is stronger for lower-prior-knowledge audiences (the audiences who need visuals most). This is why the coherence gate is a hard requirement before adding image generation.

### Image Generation State of the Art (March 2026)

- **Conceptual illustrations**: ready (Nano Banana Pro 94% text accuracy, strong compositional reasoning)
- **Architecture/UML diagrams**: not ready (diffusion models cannot guarantee structural correctness)
- **Text in images**: mostly solved at top tier but sidestepped by our "no text in illustrations" rule
- **Style consistency**: partially solved via reference images + prompt discipline
- **VRAM contention**: avoided entirely by using API-based generation instead of local ComfyUI

## Files (estimated)

### Phase 1
| File | Action |
|------|--------|
| `profiles/workflow-registry.yaml` | Create — workflow definitions |
| `agents/demo_pipeline/research.py` | Modify — include workflow corpus in context |
| `agents/demo.py` | Modify — purpose-driven visual selection matrix in prompts |
| `agents/demo_pipeline/critique.py` | Modify — coherence gate, redundancy guard, no-visual option |
| `agents/demo_models.py` | Modify — allow visual_type "none" or similar |
| `agents/demo_pipeline/html_player.py` | Modify — render text-only slides gracefully |
| `tests/test_demo_critique.py` | Modify — new critique rules |

### Phase 2
| File | Action |
|------|--------|
| `agents/demo_models.py` | Modify — IllustrationSpec, visual_type adds "illustration" |
| `agents/demo_pipeline/illustrations.py` | Create — Gemini API image generation |
| `agents/demo.py` | Modify — wire illustration generation, update prompts |
| `agents/demo_pipeline/critique.py` | Modify — illustration-specific checks |
| `profiles/demo-personas.yaml` | Modify — add illustration_style per persona |
| `agents/demo_pipeline/html_player.py` | Modify — handle illustration images |
| `agents/demo_pipeline/video.py` | Modify — illustration images in video assembly |
| `tests/test_demo_illustrations.py` | Create — illustration pipeline tests |
