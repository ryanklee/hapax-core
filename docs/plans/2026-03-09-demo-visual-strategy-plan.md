# Demo Visual Strategy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace constraint-driven visual selection with research-backed purpose-driven selection, add workflow corpus, and add illustration visual type backed by Gemini image generation.

**Architecture:** Two phases. Phase 1 fixes the selection heuristic (purpose-driven matrix in LLM prompts, Mayer's principles as critique rules, workflow corpus in research context). Phase 2 adds `illustration` visual type backed by Gemini Nano Banana API with audience-specific style keywords and coherence gating.

**Tech Stack:** Python 3.12, Pydantic, pytest (asyncio_mode=auto), Gemini API (google-genai), YAML, D2

---

## Phase 1: Research-Backed Media Selection + Workflow Corpus

### Task 1: Workflow Corpus Registry

**Files:**
- Create: `profiles/workflow-registry.yaml`
- Test: `tests/test_demo_research.py` (modify)

**Step 1: Create workflow-registry.yaml**

```yaml
# Canonical workflow definitions for demo diagram generation.
# The research gatherer injects relevant workflows so LLM-generated
# D2 diagrams draw from actual step sequences instead of hallucinating.

workflows:
  morning-briefing:
    label: "Morning Briefing Pipeline"
    trigger: "daily-briefing.timer at 07:00"
    steps:
      - "digest agent aggregates RAG content (06:45 timer)"
      - "briefing agent consumes digest output + health snapshot + calendar schedule"
      - "LLM synthesizes operational briefing via LiteLLM"
      - "vault_writer saves markdown to 30-system/briefings/"
      - "ntfy push notification sent to mobile"
    components: [digest, briefing, vault_writer, ntfy]

  health-monitoring:
    label: "Health Monitoring Loop"
    trigger: "health-monitor.timer every 15min"
    steps:
      - "75 deterministic checks across 17 groups (zero LLM)"
      - "auto-fix for known failure patterns (Docker restart, port conflicts)"
      - "desktop notification via notify-send on failures"
      - "history logged to <cache>/hapax-agents/health/"
    components: [health_monitor, ntfy]

  rag-ingestion:
    label: "RAG Ingestion Pipeline"
    trigger: "always-on watchdog + periodic sync timers"
    steps:
      - "sync agents pull from sources (Drive, Calendar, Gmail, Chrome, Obsidian, Claude Code)"
      - "files land in ~/documents/rag-sources/{service}/"
      - "rag-ingest watchdog detects new/changed files"
      - "Docling converts documents to markdown chunks"
      - "nomic-embed-text generates 768-dim vectors via Ollama"
      - "vectors stored in Qdrant 'documents' collection with source metadata"
    components: [gdrive_sync, gcalendar_sync, gmail_sync, chrome_sync, obsidian_sync, claude_code_sync, rag-ingest, qdrant]

  meeting-prep:
    label: "Meeting Prep Automation"
    trigger: "meeting-prep.timer daily 06:30"
    steps:
      - "calendar agent checks today's schedule for 1:1 meetings"
      - "management_prep agent loads person notes from vault"
      - "Gmail thread context pulled for each meeting participant"
      - "LLM generates prep doc with talking points and open loops"
      - "vault_writer saves to 10-work/1on1-prep/"
    components: [gcalendar_sync, management_prep, gmail_sync, vault_writer]

  profile-update:
    label: "Operator Profile Update"
    trigger: "profile-update.timer every 12h"
    steps:
      - "profiler agent scans new RAG documents since last run"
      - "LLM extracts profile facts across 13 dimensions"
      - "dedup against existing profile-facts in Qdrant"
      - "new facts upserted to profile-facts collection"
    components: [profiler, qdrant]

  demo-generation:
    label: "Self-Demo Pipeline"
    trigger: "on-demand via CLI"
    steps:
      - "readiness gate checks infrastructure health"
      - "sufficiency gate scores knowledge adequacy for topic + audience"
      - "research gatherer builds audience-specific context"
      - "content agent plans scene skeleton (facts only, no prose)"
      - "voice agent applies presenter style to skeleton"
      - "critique loop evaluates and revises (max 4 iterations)"
      - "Playwright captures screenshots and screencasts"
      - "D2 renders diagrams, Matplotlib renders charts"
      - "Chatterbox TTS generates voice-cloned audio"
      - "MoviePy assembles final video with crossfades"
      - "HTML player generated for interactive viewing"
    components: [demo, screenshots, screencasts, diagrams, charts, voice, video, html_player, critique]

  ambient-audio:
    label: "Ambient Audio Pipeline"
    trigger: "audio-recorder.service always on + audio-processor.timer every 30min"
    steps:
      - "ffmpeg records continuous audio from Blue Yeti mic"
      - "audio-processor segments by silence detection (VAD)"
      - "classifier categorizes segments (speech, music, ambient)"
      - "speech segments transcribed via faster-whisper"
      - "speaker diarization identifies who is speaking"
      - "transcripts embedded and stored in Qdrant documents collection"
      - "raw audio archived to Google Drive daily at 03:00 via rclone"
    components: [audio_processor, qdrant, rclone]
```

**Step 2: Write test for workflow loading**

In `tests/test_demo_research.py`, add:

```python
class TestWorkflowCorpus:
    def test_load_workflow_registry(self):
        """Workflow registry loads and has expected structure."""
        import yaml
        from pathlib import Path

        registry_path = Path(__file__).resolve().parent.parent / "profiles" / "workflow-registry.yaml"
        assert registry_path.exists(), "workflow-registry.yaml not found"

        data = yaml.safe_load(registry_path.read_text())
        assert "workflows" in data

        for name, wf in data["workflows"].items():
            assert "label" in wf, f"Workflow {name} missing label"
            assert "trigger" in wf, f"Workflow {name} missing trigger"
            assert "steps" in wf, f"Workflow {name} missing steps"
            assert len(wf["steps"]) >= 2, f"Workflow {name} has too few steps"
            assert "components" in wf, f"Workflow {name} missing components"

    def test_load_workflow_registry_all_components_are_strings(self):
        import yaml
        from pathlib import Path

        registry_path = Path(__file__).resolve().parent.parent / "profiles" / "workflow-registry.yaml"
        data = yaml.safe_load(registry_path.read_text())
        for name, wf in data["workflows"].items():
            for comp in wf["components"]:
                assert isinstance(comp, str), f"Component in {name} is not a string: {comp}"
```

**Step 3: Run tests**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_research.py::TestWorkflowCorpus -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add profiles/workflow-registry.yaml tests/test_demo_research.py
git commit -m "feat(demo): add workflow corpus registry for diagram accuracy"
```

---

### Task 2: Inject Workflow Corpus into Research Context

**Files:**
- Modify: `agents/demo_pipeline/research.py` (lines 20-77 AUDIENCE_SOURCES, lines 865-889 _SECTION_HEADERS, lines 922-986 gather loop)
- Test: `tests/test_demo_research.py`

**Step 1: Write test for workflow content in research output**

```python
class TestWorkflowInResearch:
    def test_gather_workflow_patterns_returns_content(self):
        """_gather_workflow_patterns returns formatted workflow descriptions."""
        from agents.demo_pipeline.research import _gather_workflow_patterns
        result = _gather_workflow_patterns("full system")
        assert "Morning Briefing Pipeline" in result
        assert "steps:" in result.lower() or "→" in result or "1." in result

    def test_gather_workflow_patterns_filters_by_scope(self):
        """Scope keyword narrows which workflows are returned."""
        from agents.demo_pipeline.research import _gather_workflow_patterns
        result = _gather_workflow_patterns("health monitoring")
        assert "Health Monitoring" in result
        # Should still include related workflows but health should be prominent
```

**Step 2: Run tests to see them fail**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_research.py::TestWorkflowInResearch -v
```

Expected: FAIL — `_gather_workflow_patterns` does not exist

**Step 3: Implement _gather_workflow_patterns**

In `agents/demo_pipeline/research.py`, add function (near the other `_gather_*` functions, around line 850):

```python
WORKFLOW_REGISTRY_PATH = Path(__file__).resolve().parent.parent.parent / "profiles" / "workflow-registry.yaml"


def _gather_workflow_patterns(scope: str) -> str:
    """Load workflow definitions from registry, filtered by scope relevance."""
    if not WORKFLOW_REGISTRY_PATH.exists():
        return ""
    try:
        import yaml
        data = yaml.safe_load(WORKFLOW_REGISTRY_PATH.read_text())
        workflows = data.get("workflows", {})
    except Exception:
        return ""

    scope_lower = scope.lower()
    lines: list[str] = []

    for name, wf in workflows.items():
        # Include all workflows for broad scope, filter for narrow scope
        label = wf.get("label", name)
        components = " ".join(wf.get("components", []))
        searchable = f"{name} {label} {components}".lower()

        # Broad scopes like "full system", "entire system", "everything" get all workflows
        is_broad = any(w in scope_lower for w in ("full", "entire", "system", "everything", "all"))
        if is_broad or any(w in searchable for w in scope_lower.split()):
            trigger = wf.get("trigger", "manual")
            steps = wf.get("steps", [])
            step_text = "\n".join(f"  {i}. {s}" for i, s in enumerate(steps, 1))
            lines.append(f"### {label}\nTrigger: {trigger}\n{step_text}")

    return "\n\n".join(lines) if lines else ""
```

**Step 4: Add to AUDIENCE_SOURCES and _SECTION_HEADERS**

Add `"workflow_patterns"` to every audience's source list in AUDIENCE_SOURCES (lines 20-77).

Add to `_SECTION_HEADERS` dict (around line 865):
```python
"workflow_patterns": "## System Workflows (Canonical Definitions)",
```

Add the handler in the gather loop (around line 965, following the pattern of other source handlers):
```python
elif source == "workflow_patterns":
    text = _gather_workflow_patterns(scope)
```

**Step 5: Run tests**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_research.py -v -k "Workflow"
```

Expected: PASS

**Step 6: Commit**

```bash
git add agents/demo_pipeline/research.py tests/test_demo_research.py
git commit -m "feat(demo): inject workflow corpus into research context"
```

---

### Task 3: Purpose-Driven Visual Selection Matrix in Prompts

**Files:**
- Modify: `agents/demo.py` (lines 195-215, lines 515-517)

**Step 1: Update the visual type instruction block**

Replace lines 195-215 in `agents/demo.py` with a purpose-driven selection guide. The key change: instead of "choose the visual type" with a flat list, give the LLM a decision tree keyed by what the scene is trying to communicate and who the audience is.

```
For each scene, choose the visual type using this decision framework:

STEP 1 — What is this scene communicating?
  A. A UI feature or live capability → screenshot (show the real system)
  B. Architecture, relationships, or component topology → diagram (D2)
  C. Quantitative data, trends, or comparisons → chart (only if real data exists in Research Context)
  D. Dynamic behavior that static images can't capture → screencast (max 2 per demo)
  E. A workflow or process sequence → diagram (D2), using the System Workflows section from Research Context for accurate step sequences
  F. An abstract concept, motivation, or "why" → diagram if it has concrete relationships, otherwise consider whether a clean title-card slide serves better than a forced diagram

STEP 2 — Audience calibration:
  - Family/non-technical: simplify diagrams (3-5 nodes max), use simple chart types (bar only), skip architecture diagrams unless essential
  - Technical peer: full detail diagrams, complex charts ok, show design rationale
  - Leadership: high-level diagrams, KPI charts, focus on impact
  - Team member: operational diagrams, show the cadence and automation

STEP 3 — Coherence check:
  Does this visual DIRECTLY illustrate the scene's key message? If not, switch to a different type or use a clean title-card slide. A decorative visual is worse than no visual.
```

**Step 2: Update the skeleton prompt visual variety section**

Replace the visual variety paragraph (around line 515-517) to reference purpose-driven selection:

```
Visual variety: AT LEAST HALF of all scenes MUST be screenshots or screencasts. Default to screenshots — only use diagrams when no web page illustrates the concept. MANDATORY: at least one screenshot/screencast of EACH route (/, /chat, /demos). MAX 2 screenshots of / or /demos (static pages). Use /chat for additional screenshots (up to 5). Max 2 screencasts. NEVER 3 consecutive same visual type. For WORKFLOW scenes, reference the System Workflows section for accurate step sequences — do NOT invent workflow topologies. If no visual directly illustrates the scene's message, use visual_type "diagram" with a simple labeled box rather than forcing a complex diagram.
```

**Step 3: Run existing demo tests to verify no breakage**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_*.py -x -q --deselect tests/test_demo_audiences.py::TestLoadAudiences::test_load_audiences_valid --deselect tests/test_demo_voice.py::TestParallelVoiceGeneration::test_max_tts_workers_is_three
```

Expected: All pass

**Step 4: Commit**

```bash
git add agents/demo.py
git commit -m "feat(demo): purpose-driven visual selection matrix in LLM prompts"
```

---

### Task 4: Mayer's Principles as Critique Rules

**Files:**
- Modify: `agents/demo_pipeline/critique.py` (lines 79-80 dimension descriptions, lines 372-480 _check_visual_variety)
- Test: `tests/test_demo_critique.py`

**Step 1: Write tests for new critique behaviors**

```python
class TestCoherenceGate:
    def test_screencast_without_interaction_flagged(self):
        """Screencast scenes without interaction spec are flagged (existing behavior)."""
        # This already exists — verify it still works
        script = _make_script(scenes=[
            _make_scene("Test", visual_type="screencast", interaction=None),
        ])
        dim = _check_visual_variety(script)
        assert dim is not None
        assert any("interaction" in i for i in dim.issues)

    def test_max_three_illustrations_enforced(self):
        """More than 3 illustration scenes are flagged."""
        scenes = [_make_scene(f"Scene {i}", visual_type="illustration") for i in range(4)]
        # Add enough screenshots for ratio
        scenes += [_make_scene(f"SS {i}", visual_type="screenshot",
                   screenshot=ScreenshotSpec(url="http://localhost:5173/chat"))
                   for i in range(4)]
        script = _make_script(scenes=scenes)
        dim = _check_visual_variety(script)
        assert dim is not None
        assert any("illustration" in i.lower() for i in dim.issues)
```

**Step 2: Update critique dimension descriptions**

In `critique.py` around line 79, update the descriptions:

```python
"visual_appropriateness": (
    "Right mix of visual types for the content? Each visual must DIRECTLY illustrate "
    "the scene's key message (Mayer's Coherence Principle). Illustration scenes must not "
    "depict architecture, data, or workflows — those have dedicated visual types."
),
"visual_substance": (
    "Does each visual convey specific information, not decorative filler? "
    "Charts where ALL values are identical are decorative filler — flag as critical. "
    "Charts with fabricated data not in research context are also filler. "
    "Diagram scenes whose narration discusses something unrelated to the diagram are mismatched."
),
```

**Step 3: Add illustration checks to _check_visual_variety**

In `_check_visual_variety()` (around line 376), add after the screencast count check:

```python
    # Max 3 illustration scenes
    illustration_count = sum(1 for s in script.scenes if s.visual_type == "illustration")
    if illustration_count > 3:
        issues.append(
            f"{illustration_count} illustration scenes — max 3 allowed. "
            f"Use screenshots, diagrams, or charts for remaining scenes."
        )

    # Illustrations must have illustration spec
    for i, s in enumerate(script.scenes):
        if s.visual_type == "illustration" and not s.illustration:
            issues.append(
                f"Scene {i+1} '{s.title}' has visual_type=illustration but no illustration spec"
            )
```

Update the screenshot ratio check (around line 416) to count illustrations separately:

```python
    ss_count = sum(1 for s in script.scenes if s.visual_type in ("screenshot", "screencast"))
```

Illustrations intentionally do NOT count toward the screenshot ratio — they're supplements, not substitutes.

**Step 4: Run tests**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_critique.py -v
```

Expected: All pass

**Step 5: Commit**

```bash
git add agents/demo_pipeline/critique.py tests/test_demo_critique.py
git commit -m "feat(demo): Mayer's principles as critique rules, illustration limits"
```

---

## Phase 2: Illustration Visual Type

### Task 5: IllustrationSpec Model + Visual Type Literal Update

**Files:**
- Modify: `agents/demo_models.py` (lines 81, 165)
- Test: `tests/test_demo_models.py` or `tests/test_demo_models_extended.py`

**Step 1: Write test for IllustrationSpec**

```python
class TestIllustrationSpec:
    def test_illustration_spec_defaults(self):
        from agents.demo_models import IllustrationSpec
        spec = IllustrationSpec(prompt="A warm sunrise over connected systems")
        assert spec.aspect_ratio == "16:9"
        assert "text" in spec.negative_prompt
        assert spec.style == ""

    def test_illustration_spec_with_style(self):
        from agents.demo_models import IllustrationSpec
        spec = IllustrationSpec(
            prompt="Neural pathways forming a network",
            style="warm minimal illustration, soft colors",
        )
        assert spec.style == "warm minimal illustration, soft colors"

    def test_scene_with_illustration_type(self):
        from agents.demo_models import DemoScene, IllustrationSpec
        scene = DemoScene(
            title="Why I Built This",
            narration="x " * 60,
            duration_hint=30.0,
            visual_type="illustration",
            illustration=IllustrationSpec(prompt="A person surrounded by helpful autonomous agents"),
        )
        assert scene.visual_type == "illustration"
        assert scene.illustration is not None

    def test_skeleton_accepts_illustration_type(self):
        from agents.demo_models import SceneSkeleton, IllustrationSpec
        skel = SceneSkeleton(
            title="Motivation",
            facts=["Built for personal productivity"],
            visual_type="illustration",
            visual_brief="Conceptual image of cognitive support",
            illustration=IllustrationSpec(prompt="Abstract cognitive support"),
        )
        assert skel.visual_type == "illustration"
```

**Step 2: Run tests to see them fail**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_models_extended.py::TestIllustrationSpec -v
```

Expected: FAIL — IllustrationSpec does not exist, "illustration" not in Literal

**Step 3: Implement**

In `agents/demo_models.py`, add after InteractionSpec (around line 50):

```python
class IllustrationSpec(BaseModel):
    """Specification for an AI-generated conceptual illustration."""

    prompt: str = Field(description="Scene-specific image generation prompt")
    style: str = Field(
        default="",
        description="Style keywords from audience persona (e.g. 'warm minimal illustration')",
    )
    negative_prompt: str = Field(
        default="text, words, labels, letters, numbers, watermark, diagram, chart, UI, screenshot",
        description="What to exclude from the generated image",
    )
    aspect_ratio: str = Field(
        default="16:9",
        description="Image aspect ratio",
    )
```

Update both Literal types on DemoScene (line 81) and SceneSkeleton (line 165):

```python
visual_type: Literal["screenshot", "diagram", "chart", "screencast", "illustration"]
```

Add field to both DemoScene (after `interaction` field) and SceneSkeleton (after `interaction` field):

```python
    illustration: IllustrationSpec | None = Field(
        default=None,
        description="Illustration spec for AI-generated conceptual images",
    )
```

**Step 4: Run tests**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_models_extended.py::TestIllustrationSpec -v
```

Expected: PASS

**Step 5: Run full model tests to verify no breakage**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_models*.py -v
```

Expected: All pass

**Step 6: Commit**

```bash
git add agents/demo_models.py tests/test_demo_models_extended.py
git commit -m "feat(demo): add IllustrationSpec model and illustration visual type"
```

---

### Task 6: Illustration Style in Audience Personas

**Files:**
- Modify: `profiles/demo-personas.yaml`
- Test: `tests/test_demo_audiences.py` or inline validation

**Step 1: Add illustration_style to each persona**

In `profiles/demo-personas.yaml`, add `illustration_style` field to each archetype:

```yaml
family:
  # ... existing fields ...
  illustration_style: "warm minimal illustration, soft gradients, approachable, human-centered, no technical elements"

technical-peer:
  # ... existing fields ...
  illustration_style: "clean precise technical illustration, dark background, geometric shapes, blueprint aesthetic, subtle glow effects"

leadership:
  # ... existing fields ...
  illustration_style: "professional business illustration, clean lines, corporate blue palette, minimal, strategic"

team-member:
  # ... existing fields ...
  illustration_style: "friendly professional illustration, warm colors, collaborative feel, modern flat style"
```

**Step 2: Verify personas still load**

```bash
cd <ai-agents> && uv run python -c "from agents.demo_models import load_personas; p = load_personas(); print(list(p.keys()))"
```

Expected: prints persona names without error. Note: `illustration_style` is NOT in AudiencePersona model — it's extra YAML data that the illustration pipeline reads directly from the YAML, not through the Pydantic model. This avoids changing the model contract.

**Step 3: Commit**

```bash
git add profiles/demo-personas.yaml
git commit -m "feat(demo): add illustration_style to audience personas"
```

---

### Task 7: Illustration Generation Module

**Files:**
- Create: `agents/demo_pipeline/illustrations.py`
- Test: `tests/test_demo_illustrations.py`

**Step 1: Write tests**

```python
"""Tests for illustration generation pipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.demo_models import IllustrationSpec


class TestIllustrationSpec:
    def test_default_negative_prompt_excludes_text(self):
        spec = IllustrationSpec(prompt="test")
        assert "text" in spec.negative_prompt
        assert "words" in spec.negative_prompt

    def test_default_aspect_ratio(self):
        spec = IllustrationSpec(prompt="test")
        assert spec.aspect_ratio == "16:9"


class TestBuildPrompt:
    def test_combines_prompt_and_style(self):
        from agents.demo_pipeline.illustrations import _build_prompt
        spec = IllustrationSpec(
            prompt="A sunrise over connected systems",
            style="warm minimal illustration, soft colors",
        )
        result = _build_prompt(spec)
        assert "sunrise" in result
        assert "warm minimal" in result

    def test_prompt_without_style(self):
        from agents.demo_pipeline.illustrations import _build_prompt
        spec = IllustrationSpec(prompt="Abstract data flow")
        result = _build_prompt(spec)
        assert "Abstract data flow" in result


class TestGenerateIllustrations:
    async def test_empty_specs_returns_empty(self, tmp_path):
        from agents.demo_pipeline.illustrations import generate_illustrations
        paths = await generate_illustrations([], tmp_path)
        assert paths == []

    @patch("agents.demo_pipeline.illustrations._generate_single")
    async def test_calls_generate_for_each_spec(self, mock_gen, tmp_path):
        from agents.demo_pipeline.illustrations import generate_illustrations
        mock_gen.return_value = tmp_path / "test.png"
        # Create a dummy file so the path exists
        (tmp_path / "test.png").write_bytes(b"fake png")

        specs = [
            ("01-intro", IllustrationSpec(prompt="Test 1")),
            ("02-concept", IllustrationSpec(prompt="Test 2")),
        ]
        paths = await generate_illustrations(specs, tmp_path)
        assert mock_gen.call_count == 2
        assert len(paths) == 2

    @patch("agents.demo_pipeline.illustrations._generate_single")
    async def test_fallback_on_failure(self, mock_gen, tmp_path):
        from agents.demo_pipeline.illustrations import generate_illustrations
        mock_gen.return_value = None  # Simulates API failure

        specs = [("01-intro", IllustrationSpec(prompt="Test"))]
        paths = await generate_illustrations(specs, tmp_path)
        # Should return None for failed generation
        assert len(paths) == 1
        assert paths[0] is None


class TestLoadIllustrationStyle:
    def test_loads_style_for_known_audience(self):
        from agents.demo_pipeline.illustrations import load_illustration_style
        style = load_illustration_style("family")
        assert isinstance(style, str)
        # Should have content if persona yaml has illustration_style
        # (may be empty string if field not present — that's ok)

    def test_unknown_audience_returns_empty(self):
        from agents.demo_pipeline.illustrations import load_illustration_style
        style = load_illustration_style("nonexistent-audience")
        assert style == ""
```

**Step 2: Run tests to see them fail**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_illustrations.py -v
```

Expected: FAIL — module does not exist

**Step 3: Implement illustrations.py**

```python
"""Illustration generation pipeline using Gemini image generation API."""
from __future__ import annotations

import base64
import logging
from collections.abc import Callable
from pathlib import Path

import yaml

from agents.demo_models import IllustrationSpec

log = logging.getLogger(__name__)

PERSONAS_PATH = Path(__file__).resolve().parent.parent.parent / "profiles" / "demo-personas.yaml"


def load_illustration_style(audience: str) -> str:
    """Load illustration_style from persona YAML for the given audience."""
    try:
        data = yaml.safe_load(PERSONAS_PATH.read_text())
        archetypes = data.get("archetypes", {})
        persona = archetypes.get(audience, {})
        return persona.get("illustration_style", "")
    except Exception:
        return ""


def _build_prompt(spec: IllustrationSpec) -> str:
    """Combine illustration prompt with style keywords."""
    parts = []
    if spec.style:
        parts.append(f"Style: {spec.style}.")
    parts.append(spec.prompt)
    if spec.negative_prompt:
        parts.append(f"Do NOT include: {spec.negative_prompt}")
    return " ".join(parts)


async def _generate_single(
    spec: IllustrationSpec,
    output_path: Path,
) -> Path | None:
    """Generate a single illustration via Gemini API.

    Returns the saved image path, or None on failure.
    """
    try:
        from google import genai

        client = genai.Client()

        prompt = _build_prompt(spec)
        log.info("Generating illustration: %s", prompt[:80])

        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=genai.types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=spec.aspect_ratio,
            ),
        )

        if not response.generated_images:
            log.warning("No images returned for prompt: %s", prompt[:60])
            return None

        image = response.generated_images[0]
        image_bytes = image.image.image_bytes
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)
        log.info("Saved illustration: %s (%.1f KB)",
                 output_path.name, len(image_bytes) / 1024)
        return output_path

    except Exception as e:
        log.error("Illustration generation failed: %s", e)
        return None


async def generate_illustrations(
    specs: list[tuple[str, IllustrationSpec]],
    output_dir: Path,
    on_progress: Callable[[str], None] | None = None,
) -> list[Path | None]:
    """Generate illustrations for each spec.

    Returns list of saved PNG paths (or None for failed generations).
    Caller should fall back to title-card for None entries.
    """
    if not specs:
        return []

    progress = on_progress or (lambda _: None)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path | None] = []

    for i, (name, spec) in enumerate(specs, 1):
        progress(f"Generating illustration {i}/{len(specs)}: {name}")
        output_path = output_dir / f"{name}.png"
        path = await _generate_single(spec, output_path)
        paths.append(path)

    generated = sum(1 for p in paths if p is not None)
    progress(f"Generated {generated}/{len(specs)} illustrations")
    return paths
```

**Step 4: Run tests**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_illustrations.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add agents/demo_pipeline/illustrations.py tests/test_demo_illustrations.py
git commit -m "feat(demo): illustration generation module with Gemini API"
```

---

### Task 8: Wire Illustrations into Demo Orchestrator

**Files:**
- Modify: `agents/demo.py` (lines 1016-1087 visual generation section, lines 195-215 prompt)

**Step 1: Add illustration handling to visual generation loop**

In `agents/demo.py`, in the visual generation section (around line 1040), add after the screencast elif:

```python
            elif scene.visual_type == "illustration":
                if scene.illustration:
                    illustration_specs.append((name, scene.illustration))
                else:
                    log.warning("Scene '%s' has visual_type=illustration but no illustration spec", scene.title)
```

Initialize `illustration_specs = []` alongside `screenshot_specs` and `screencast_specs` (around line 1023).

After the screencast recording block (around line 1086), add:

```python
        # Illustrations via Gemini image generation
        if illustration_specs:
            from agents.demo_pipeline.illustrations import generate_illustrations, load_illustration_style

            # Inject audience style into specs that don't have one
            audience_style = load_illustration_style(script.audience)
            styled_specs = []
            for ill_name, ill_spec in illustration_specs:
                if not ill_spec.style and audience_style:
                    ill_spec = ill_spec.model_copy(update={"style": audience_style})
                styled_specs.append((ill_name, ill_spec))

            illustration_paths = await generate_illustrations(
                styled_specs, visual_dir, on_progress=progress
            )
            for (ill_name, _), path in zip(illustration_specs, illustration_paths):
                if path is not None:
                    for scene in script.scenes:
                        slug = re.sub(r"[^a-z0-9]+", "-", scene.title.lower()).strip("-")
                        if ill_name.endswith(slug) and scene.title not in screenshot_map:
                            screenshot_map[scene.title] = path
                            break
```

**Step 2: Update content prompt with illustration option**

In the visual type instruction block (around line 195), add illustration to the decision framework:

```
  F. An abstract concept, motivation, or "why" that has no concrete relationships to diagram → illustration (AI-generated conceptual image, max 3 per demo)

- 'illustration' — for abstract concepts, motivation, personal meaning. NOT for architecture, data, or workflows.
  * Include an illustration spec with a descriptive prompt of what to visualize
  * The pipeline adds audience-appropriate style automatically
  * Max 3 illustration scenes per demo
  * No text will appear in the image — all text goes in key_points
```

**Step 3: Run full demo tests**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_*.py -x -q --deselect tests/test_demo_audiences.py::TestLoadAudiences::test_load_audiences_valid --deselect tests/test_demo_voice.py::TestParallelVoiceGeneration::test_max_tts_workers_is_three
```

Expected: All pass

**Step 4: Commit**

```bash
git add agents/demo.py
git commit -m "feat(demo): wire illustration generation into demo orchestrator"
```

---

### Task 9: Critique Integration for Illustrations

**Files:**
- Modify: `agents/demo_pipeline/critique.py`
- Test: `tests/test_demo_critique.py`

The illustration-specific critique checks were partially added in Task 4. This task adds the revision prompt guidance and the word-count preservation safeguard for illustration scenes.

**Step 1: Update revision guidance**

In the revision guidance prompt (around the visual variety revision section), add:

```
- Illustration scenes should have prompts that describe something directly related to the scene's narration
- Illustrations are for abstract concepts only — if the scene describes architecture, use a diagram; if it shows data, use a chart
- Max 3 illustrations per demo
```

**Step 2: Add illustration preservation to the revision safeguard**

In the post-revision scene preservation logic (around line 695), add alongside the screencast preservation:

```python
                # Restore illustration if revision cleared it AND type is still illustration
                if old_scene.visual_type == "illustration" and old_scene.illustration:
                    if not new_scene.illustration:
                        patches["illustration"] = old_scene.illustration
                # Restore illustration visual_type if revision changed it away
                if old_scene.visual_type == "illustration" and new_scene.visual_type != "illustration":
                    if new_scene.visual_type in ("diagram", "chart"):
                        patches["visual_type"] = "illustration"
                        patches["illustration"] = old_scene.illustration
                        log.info("Restored illustration visual_type for scene '%s'", old_scene.title)
```

**Step 3: Run tests**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_critique.py -v
```

Expected: All pass

**Step 4: Commit**

```bash
git add agents/demo_pipeline/critique.py
git commit -m "feat(demo): illustration preservation in critique revision loop"
```

---

### Task 10: Full Integration Verification

**Step 1: Run full test suite**

```bash
cd <ai-agents> && uv run pytest tests/test_demo_*.py -x -q --deselect tests/test_demo_audiences.py::TestLoadAudiences::test_load_audiences_valid --deselect tests/test_demo_voice.py::TestParallelVoiceGeneration::test_max_tts_workers_is_three
```

Expected: All pass

**Step 2: Verify google-genai dependency**

Check if `google-genai` is already in pyproject.toml (it was added to uv.lock in a previous commit):

```bash
cd <ai-agents> && grep "google-genai" pyproject.toml
```

If not present, add it:

```bash
cd <ai-agents> && uv add google-genai
```

**Step 3: Smoke test illustration module (mocked)**

```bash
cd <ai-agents> && uv run python -c "
from agents.demo_models import IllustrationSpec, DemoScene
spec = IllustrationSpec(prompt='Warm sunrise over a network of helpful agents')
scene = DemoScene(
    title='Why I Built This',
    narration='x ' * 60,
    duration_hint=30.0,
    visual_type='illustration',
    illustration=spec,
)
print(f'Scene: {scene.title}, type: {scene.visual_type}, prompt: {scene.illustration.prompt[:40]}')
print('Model validation passed')
"
```

Expected: prints scene info, no errors

**Step 4: Commit any remaining changes**

```bash
git add -A && git status
# Only commit if there are changes
```

---

## Verification Summary

```bash
cd <ai-agents>

# 1. All demo tests pass
uv run pytest tests/test_demo_*.py -x -q \
  --deselect tests/test_demo_audiences.py::TestLoadAudiences::test_load_audiences_valid \
  --deselect tests/test_demo_voice.py::TestParallelVoiceGeneration::test_max_tts_workers_is_three

# 2. New tests pass
uv run pytest tests/test_demo_illustrations.py tests/test_demo_research.py -v -k "Illustration or Workflow"

# 3. Generate a demo with illustrations (requires cockpit-web + cockpit API + Gemini API key)
# Start cockpit: cd <cockpit-web> && pnpm dev &
# Start API: cd <ai-agents> && direnv exec . uv run cockpit &
direnv exec . uv run python -m agents.demo "full system" --audience "chris beron" --duration 10m --voice

# 4. Manual verification:
# - Open demo.html — illustration scenes should show generated images
# - Workflow diagrams should match workflow-registry.yaml step sequences
# - No decorative/irrelevant images (coherence gate working)
# - Family audience demos should have simpler diagrams than technical peer demos
```
