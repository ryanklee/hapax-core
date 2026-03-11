# Demo Evaluation Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** A fully autonomous evaluation agent that generates a demo end-to-end, evaluates the rendered output via LLM-as-judge (Gemini Pro vision), diagnoses failures, adjusts planning parameters, and re-generates until quality passes.

**Architecture:** New Tier 2 agent (`agents/demo_eval.py`) orchestrates a generate → evaluate → heal loop. Evaluation uses three rubric categories: text (narration quality via LLM), visual (screenshot inspection via Gemini Pro vision), and structural (deterministic file/metadata checks). Self-healing adjusts planning prompt overrides, not source code.

**Tech Stack:** Pydantic AI 1.63.0 (`BinaryContent` for image input), Gemini Pro via LiteLLM (vision-capable), Pillow (image loading), existing demo pipeline.

---

## Context for Implementer

### Key Files You'll Need

- `agents/demo.py` — `generate_demo()` at line 186, `build_planning_prompt()` at line 107, `parse_request()` at line 55
- `agents/demo_models.py` — `DemoScript`, `DemoScene`, `DemoQualityReport`, `QualityDimension`
- `agents/demo_pipeline/critique.py` — existing 8 `QUALITY_DIMENSIONS`, `critique_and_revise()`
- `agents/demo_pipeline/narrative.py` — `load_style_guide()` returns dict from `profiles/presenter-style.yaml`
- `shared/config.py` — `get_model(alias)` creates LiteLLM-backed models. `"gemini-pro"` is a valid LiteLLM alias.
- `profiles/presenter-style.yaml` — style guide with avoid/embrace lists

### Pydantic AI Image Input API

```python
from pydantic_ai.messages import BinaryContent

# Load image as bytes, wrap in BinaryContent
image_bytes = Path("screenshot.png").read_bytes()
image = BinaryContent(data=image_bytes, media_type="image/png")

# Pass as list[str | BinaryContent] to agent.run()
result = await agent.run(user_prompt=["Evaluate this screenshot:", image, "Rubric: ..."])
```

### Demo Output Structure

After `generate_demo()` returns a `Path` to the demo directory:
```
output/demos/20260305-123456-the-system/
├── script.json          # DemoScript serialized
├── metadata.json        # {title, audience, scenes, format, duration, quality_pass, ...}
├── demo.html            # Self-contained HTML player
├── slides.md            # Marp markdown
├── screenshots/         # PNG files: 01-scene-slug.png, 02-scene-slug.png, ...
└── audio/               # (only if format=video)
```

### Running Tests

All test commands from `<ai-agents>/`:
```bash
uv run pytest tests/test_demo_eval.py -v           # just eval tests
uv run pytest tests/test_demo*.py -v                # all demo tests
```

---

## Task 1: Data Models for Evaluation

**Files:**
- Modify: `agents/demo_models.py` (append after line 70)
- Create: `tests/test_demo_eval_models.py`

**What:** Add `DemoEvalDimension`, `DemoEvalReport`, and `DemoEvalResult` models.

**Implementation:**

Add to `agents/demo_models.py` after the `DemoQualityReport` class (line 70):

```python
class DemoEvalDimension(BaseModel):
    """Evaluation of one output quality dimension."""

    name: str
    category: Literal["text", "visual", "structural"]
    passed: bool
    score: float = Field(ge=0.0, le=1.0, description="Quality score 0.0-1.0")
    issues: list[str] = Field(default_factory=list)
    evidence: str | None = Field(
        default=None,
        description="Quote from narration or screenshot description supporting the evaluation",
    )


class DemoEvalReport(BaseModel):
    """Evaluation report for a single iteration."""

    dimensions: list[DemoEvalDimension]
    overall_pass: bool
    overall_score: float = Field(ge=0.0, le=1.0)
    iteration: int = 1
    adjustments_applied: list[str] = Field(default_factory=list)


class DemoEvalResult(BaseModel):
    """Full evaluation run result across all iterations."""

    scenario: str
    passed: bool
    iterations: int
    final_report: DemoEvalReport
    history: list[DemoEvalReport] = Field(default_factory=list)
    demo_dir: str
    total_duration_seconds: float = 0.0
```

**Tests** (`tests/test_demo_eval_models.py`):

```python
"""Tests for demo evaluation data models."""
from agents.demo_models import DemoEvalDimension, DemoEvalReport, DemoEvalResult


class TestDemoEvalDimension:
    def test_basic_creation(self):
        dim = DemoEvalDimension(
            name="style_compliance", category="text", passed=True, score=0.9
        )
        assert dim.name == "style_compliance"
        assert dim.category == "text"
        assert dim.passed is True

    def test_with_issues(self):
        dim = DemoEvalDimension(
            name="visual_clarity", category="visual", passed=False, score=0.3,
            issues=["Screenshot shows loading spinner", "Text too small to read"],
            evidence="Scene 2 screenshot captured during page load",
        )
        assert len(dim.issues) == 2
        assert dim.evidence is not None

    def test_score_bounds(self):
        import pytest
        with pytest.raises(Exception):
            DemoEvalDimension(name="x", category="text", passed=True, score=1.5)


class TestDemoEvalReport:
    def test_passing_report(self):
        dims = [
            DemoEvalDimension(name="style", category="text", passed=True, score=0.9),
            DemoEvalDimension(name="clarity", category="visual", passed=True, score=0.8),
        ]
        report = DemoEvalReport(
            dimensions=dims, overall_pass=True, overall_score=0.85, iteration=1,
        )
        assert report.overall_pass is True
        assert report.iteration == 1

    def test_with_adjustments(self):
        report = DemoEvalReport(
            dimensions=[], overall_pass=False, overall_score=0.4, iteration=2,
            adjustments_applied=["Added explicit style avoidance list"],
        )
        assert len(report.adjustments_applied) == 1


class TestDemoEvalResult:
    def test_successful_result(self):
        report = DemoEvalReport(
            dimensions=[], overall_pass=True, overall_score=0.9, iteration=1,
        )
        result = DemoEvalResult(
            scenario="the system for a non-technical friend", passed=True, iterations=1,
            final_report=report, demo_dir="/tmp/demo",
            total_duration_seconds=45.0,
        )
        assert result.passed is True
        assert result.iterations == 1

    def test_with_history(self):
        r1 = DemoEvalReport(dimensions=[], overall_pass=False, overall_score=0.4, iteration=1)
        r2 = DemoEvalReport(dimensions=[], overall_pass=True, overall_score=0.85, iteration=2)
        result = DemoEvalResult(
            scenario="test", passed=True, iterations=2,
            final_report=r2, history=[r1, r2], demo_dir="/tmp/demo",
        )
        assert len(result.history) == 2
```

**Run:** `uv run pytest tests/test_demo_eval_models.py -v`

**Commit:** `git add agents/demo_models.py tests/test_demo_eval_models.py && git commit -m "feat(demo-eval): add evaluation data models"`

---

## Task 2: Structural Evaluation (Deterministic Checks)

**Files:**
- Create: `agents/demo_pipeline/eval_rubrics.py`
- Create: `tests/test_demo_eval_rubrics.py`

**What:** Deterministic structural checks that don't need an LLM. These validate file presence, metadata correctness, and HTML player integrity.

**Implementation** (`agents/demo_pipeline/eval_rubrics.py`):

```python
"""Evaluation rubrics for demo output quality — deterministic structural checks."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from agents.demo_models import DemoEvalDimension

log = logging.getLogger(__name__)


def check_files_present(demo_dir: Path) -> DemoEvalDimension:
    """Verify all expected output files exist."""
    issues = []
    required = ["script.json", "metadata.json", "demo.html"]
    for f in required:
        if not (demo_dir / f).exists():
            issues.append(f"Missing required file: {f}")

    screenshots_dir = demo_dir / "screenshots"
    if not screenshots_dir.exists() or not list(screenshots_dir.glob("*.png")):
        issues.append("No screenshots found in screenshots/ directory")

    # Check script.json references match actual screenshots
    script_path = demo_dir / "script.json"
    if script_path.exists():
        script = json.loads(script_path.read_text())
        scene_count = len(script.get("scenes", []))
        png_count = len(list(screenshots_dir.glob("*.png"))) if screenshots_dir.exists() else 0
        if png_count < scene_count:
            issues.append(f"Only {png_count} screenshots for {scene_count} scenes")

    passed = len(issues) == 0
    return DemoEvalDimension(
        name="files_present", category="structural",
        passed=passed, score=1.0 if passed else 0.0, issues=issues,
    )


def check_metadata_correctness(demo_dir: Path, expected_audience: str | None = None) -> DemoEvalDimension:
    """Verify metadata.json has correct values."""
    issues = []
    meta_path = demo_dir / "metadata.json"

    if not meta_path.exists():
        return DemoEvalDimension(
            name="metadata_correctness", category="structural",
            passed=False, score=0.0, issues=["metadata.json not found"],
        )

    meta = json.loads(meta_path.read_text())

    # Required keys
    required_keys = {"title", "audience", "scope", "scenes", "format", "duration", "primary_file"}
    missing = required_keys - set(meta.keys())
    if missing:
        issues.append(f"Missing metadata keys: {missing}")

    # Audience match
    if expected_audience and meta.get("audience") != expected_audience:
        issues.append(f"Audience mismatch: expected '{expected_audience}', got '{meta.get('audience')}'")

    # Scene count matches script
    script_path = demo_dir / "script.json"
    if script_path.exists():
        script = json.loads(script_path.read_text())
        if meta.get("scenes") != len(script.get("scenes", [])):
            issues.append(f"Scene count mismatch: metadata={meta.get('scenes')}, script={len(script.get('scenes', []))}")

    # Duration sanity
    duration = meta.get("duration", 0)
    if duration <= 0:
        issues.append(f"Invalid duration: {duration}")

    # Quality pass
    if meta.get("quality_pass") is False:
        issues.append("Script did not pass quality review (quality_pass=false)")

    passed = len(issues) == 0
    return DemoEvalDimension(
        name="metadata_correctness", category="structural",
        passed=passed, score=max(0.0, 1.0 - len(issues) * 0.25), issues=issues,
    )


def check_html_integrity(demo_dir: Path) -> DemoEvalDimension:
    """Verify demo.html has expected structure."""
    issues = []
    html_path = demo_dir / "demo.html"

    if not html_path.exists():
        return DemoEvalDimension(
            name="html_integrity", category="structural",
            passed=False, score=0.0, issues=["demo.html not found"],
        )

    html = html_path.read_text()

    # Must contain base64 images
    if "data:image/" not in html:
        issues.append("No base64 images found in HTML player")

    # Must contain Gruvbox background color
    if "#282828" not in html:
        issues.append("Gruvbox background color #282828 not found")

    # Must have scene structure
    script_path = demo_dir / "script.json"
    if script_path.exists():
        script = json.loads(script_path.read_text())
        for scene in script.get("scenes", []):
            if scene["title"] not in html:
                issues.append(f"Scene title '{scene['title']}' not found in HTML")
                break  # Just flag first missing, don't spam

    # Must have player controls
    if "play" not in html.lower() and "autoplay" not in html.lower():
        issues.append("No player controls found in HTML")

    passed = len(issues) == 0
    return DemoEvalDimension(
        name="html_integrity", category="structural",
        passed=passed, score=max(0.0, 1.0 - len(issues) * 0.2), issues=issues,
    )


def run_structural_checks(
    demo_dir: Path, expected_audience: str | None = None,
) -> list[DemoEvalDimension]:
    """Run all deterministic structural checks."""
    return [
        check_files_present(demo_dir),
        check_metadata_correctness(demo_dir, expected_audience),
        check_html_integrity(demo_dir),
    ]
```

**Tests** (`tests/test_demo_eval_rubrics.py`):

```python
"""Tests for demo evaluation structural rubrics."""
import json
from pathlib import Path

from PIL import Image

from agents.demo_models import DemoEvalDimension
from agents.demo_pipeline.eval_rubrics import (
    check_files_present,
    check_html_integrity,
    check_metadata_correctness,
    run_structural_checks,
)


def _make_demo_dir(tmp_path: Path, scenes: int = 3) -> Path:
    """Create a minimal demo output directory for testing."""
    demo_dir = tmp_path / "demo"
    demo_dir.mkdir()
    screenshots_dir = demo_dir / "screenshots"
    screenshots_dir.mkdir()

    # Script
    script = {
        "title": "Test Demo",
        "audience": "family",
        "scenes": [
            {"title": f"Scene {i}", "narration": f"Narration {i}",
             "duration_hint": 10.0, "key_points": [f"Point {i}"],
             "screenshot": {"url": "http://localhost:5173"}}
            for i in range(1, scenes + 1)
        ],
        "intro_narration": "Welcome.",
        "outro_narration": "Done.",
    }
    (demo_dir / "script.json").write_text(json.dumps(script))

    # Metadata
    metadata = {
        "title": "Test Demo", "audience": "family", "scope": "the system",
        "scenes": scenes, "format": "slides", "duration": 30.0,
        "timestamp": "20260305-120000", "output_dir": str(demo_dir),
        "primary_file": "demo.html", "has_video": False, "has_audio": False,
        "target_duration": 180, "quality_pass": True,
        "narrative_framework": "guided-tour",
    }
    (demo_dir / "metadata.json").write_text(json.dumps(metadata))

    # Screenshots (minimal PNGs)
    for i in range(1, scenes + 1):
        img = Image.new("RGB", (1920, 1080), color=(40, 40, 40))
        img.save(screenshots_dir / f"{i:02d}-scene-{i}.png")

    # HTML player (minimal)
    html = f"""<!DOCTYPE html>
<html><body style="background:#282828;color:#ebdbb2">
<div id="app">{''.join(f'<div class="slide">{s["title"]}</div>' for s in script["scenes"])}
<img src="data:image/png;base64,iVBOR"/>
<button>play</button>
</div></body></html>"""
    (demo_dir / "demo.html").write_text(html)

    return demo_dir


class TestCheckFilesPresent:
    def test_all_present(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        result = check_files_present(demo_dir)
        assert result.passed is True
        assert result.score == 1.0

    def test_missing_script(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        (demo_dir / "script.json").unlink()
        result = check_files_present(demo_dir)
        assert result.passed is False
        assert "script.json" in result.issues[0]

    def test_missing_screenshots(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        for p in (demo_dir / "screenshots").glob("*.png"):
            p.unlink()
        result = check_files_present(demo_dir)
        assert result.passed is False

    def test_insufficient_screenshots(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path, scenes=5)
        # Remove some screenshots
        pngs = sorted((demo_dir / "screenshots").glob("*.png"))
        for p in pngs[2:]:
            p.unlink()
        result = check_files_present(demo_dir)
        assert result.passed is False
        assert "Only 2 screenshots for 5 scenes" in result.issues[0]


class TestCheckMetadataCorrectness:
    def test_correct_metadata(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        result = check_metadata_correctness(demo_dir, expected_audience="family")
        assert result.passed is True

    def test_audience_mismatch(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        result = check_metadata_correctness(demo_dir, expected_audience="leadership")
        assert result.passed is False
        assert "Audience mismatch" in result.issues[0]

    def test_missing_metadata_file(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        (demo_dir / "metadata.json").unlink()
        result = check_metadata_correctness(demo_dir)
        assert result.passed is False

    def test_quality_pass_false(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        meta = json.loads((demo_dir / "metadata.json").read_text())
        meta["quality_pass"] = False
        (demo_dir / "metadata.json").write_text(json.dumps(meta))
        result = check_metadata_correctness(demo_dir)
        assert result.passed is False


class TestCheckHtmlIntegrity:
    def test_valid_html(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        result = check_html_integrity(demo_dir)
        assert result.passed is True

    def test_missing_base64_images(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        (demo_dir / "demo.html").write_text("<html><body>#282828</body></html>")
        result = check_html_integrity(demo_dir)
        assert result.passed is False
        assert any("base64" in i for i in result.issues)

    def test_missing_html(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        (demo_dir / "demo.html").unlink()
        result = check_html_integrity(demo_dir)
        assert result.passed is False


class TestRunStructuralChecks:
    def test_all_pass(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path)
        results = run_structural_checks(demo_dir, expected_audience="family")
        assert len(results) == 3
        assert all(r.passed for r in results)
        assert all(r.category == "structural" for r in results)
```

**Run:** `uv run pytest tests/test_demo_eval_rubrics.py -v`

**Commit:** `git add agents/demo_pipeline/eval_rubrics.py tests/test_demo_eval_rubrics.py && git commit -m "feat(demo-eval): add structural evaluation rubrics"`

---

## Task 3: Text Evaluation (LLM-as-Judge for Narration)

**Files:**
- Modify: `agents/demo_pipeline/eval_rubrics.py` (add text evaluation functions)
- Modify: `tests/test_demo_eval_rubrics.py` (add text evaluation tests)

**What:** LLM-based evaluation of narration text quality against the presenter style guide and audience calibration. Uses `get_model("balanced")` — doesn't need vision.

**Implementation** — add to `eval_rubrics.py`:

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from shared.config import get_model

# ── Text evaluation models ──────────────────────────────────────────────────

class TextEvalOutput(BaseModel):
    """Structured output from text evaluation LLM."""
    style_compliance: DimScore
    audience_calibration: DimScore
    duration_feasibility: DimScore
    key_points_quality: DimScore
    narrative_coherence: DimScore


class DimScore(BaseModel):
    """Score for a single text dimension."""
    score: float = Field(ge=0.0, le=1.0)
    passed: bool
    issues: list[str] = Field(default_factory=list)
    evidence: str | None = None


# ── Text evaluation agent ───────────────────────────────────────────────────

text_eval_agent = Agent(
    get_model("balanced"),
    system_prompt=(
        "You are a rigorous presentation quality evaluator. Given a demo script's "
        "narration and metadata, evaluate it against specific quality dimensions. "
        "Be precise and cite specific narration text as evidence for any issues found. "
        "Score each dimension 0.0-1.0 where 0.8+ is passing."
    ),
    output_type=TextEvalOutput,
)


def _build_text_eval_prompt(script_data: dict, style_guide: dict, target_seconds: int) -> str:
    """Build the prompt for text quality evaluation."""
    avoid_items = style_guide.get("avoid", [])
    embrace_items = style_guide.get("embrace", [])

    narrations = []
    key_points_all = []
    for i, scene in enumerate(script_data.get("scenes", []), 1):
        narrations.append(f"Scene {i} ({scene['title']}): {scene['narration']}")
        key_points_all.extend(scene.get("key_points", []))

    total_words = sum(len(s.get("narration", "").split()) for s in script_data.get("scenes", []))
    total_words += len(script_data.get("intro_narration", "").split())
    total_words += len(script_data.get("outro_narration", "").split())

    return f"""Evaluate this demo script's text quality.

## Narration Text

Intro: {script_data.get('intro_narration', '')}

{chr(10).join(narrations)}

Outro: {script_data.get('outro_narration', '')}

## Key Points (all scenes)
{chr(10).join(f'- {kp}' for kp in key_points_all)}

## Evaluation Criteria

### 1. style_compliance
Voice should be: {style_guide.get('voice', 'first-person')}
Cadence should be: {style_guide.get('cadence', 'state-explain-show')}
Transitions should be: {style_guide.get('transitions', 'functional')}
MUST AVOID: {'; '.join(avoid_items)}
SHOULD EMBRACE: {'; '.join(embrace_items)}
Opening rule: {style_guide.get('opening', '')}
Closing rule: {style_guide.get('closing', '')}

### 2. audience_calibration
Target audience: {script_data.get('audience', 'unknown')}
Family audience = no technical jargon, warm, accessible.
Technical audience = precise terminology, design rationale.

### 3. duration_feasibility
Target duration: {target_seconds} seconds
Total word count: {total_words}
Speech rate: ~150 words/minute (2.5 words/second)
Expected words for target: ~{int(target_seconds * 2.5)}
Tolerance: ±20%

### 4. key_points_quality
Each key point should be substantive and specific.
Must contain concrete facts, numbers, or outcomes — not vague platitudes.

### 5. narrative_coherence
Script should follow a clear narrative arc.
Scenes should build logically. Opening should set context. Closing should land on impact.

For each dimension: score 0.0-1.0 (0.8+ = pass), list specific issues with evidence quotes."""


async def run_text_evaluation(
    script_data: dict, style_guide: dict, target_seconds: int,
) -> list[DemoEvalDimension]:
    """Run LLM-based text quality evaluation on script narration."""
    prompt = _build_text_eval_prompt(script_data, style_guide, target_seconds)
    result = await text_eval_agent.run(prompt)
    output = result.output

    dimensions = []
    for name in ["style_compliance", "audience_calibration", "duration_feasibility",
                  "key_points_quality", "narrative_coherence"]:
        dim_score: DimScore = getattr(output, name)
        dimensions.append(DemoEvalDimension(
            name=name, category="text",
            passed=dim_score.passed, score=dim_score.score,
            issues=dim_score.issues, evidence=dim_score.evidence,
        ))
    return dimensions
```

Note: `DimScore` must be defined BEFORE `TextEvalOutput` in the file since `TextEvalOutput` references it.

**Tests** — add to `tests/test_demo_eval_rubrics.py`:

```python
from unittest.mock import AsyncMock, patch, MagicMock

from agents.demo_pipeline.eval_rubrics import (
    _build_text_eval_prompt,
    run_text_evaluation,
    DimScore,
    TextEvalOutput,
)


class TestBuildTextEvalPrompt:
    def test_includes_narration(self):
        script_data = {
            "audience": "family",
            "intro_narration": "Welcome to the system.",
            "outro_narration": "That's how it works.",
            "scenes": [
                {"title": "Scene 1", "narration": "This is scene one.", "key_points": ["Point A"]},
            ],
        }
        style_guide = {"voice": "first-person", "avoid": ["leverage"], "embrace": ["concrete numbers"]}
        prompt = _build_text_eval_prompt(script_data, style_guide, 180)
        assert "Welcome to the system" in prompt
        assert "scene one" in prompt
        assert "leverage" in prompt
        assert "180 seconds" in prompt

    def test_word_count_calculation(self):
        script_data = {
            "audience": "family",
            "intro_narration": "One two three",
            "outro_narration": "Four five",
            "scenes": [{"title": "S1", "narration": "Six seven eight nine ten", "key_points": []}],
        }
        prompt = _build_text_eval_prompt(script_data, {}, 60)
        # 3 + 2 + 5 = 10 words
        assert "Total word count: 10" in prompt


class TestRunTextEvaluation:
    @pytest.mark.asyncio
    async def test_returns_five_dimensions(self):
        mock_output = TextEvalOutput(
            style_compliance=DimScore(score=0.9, passed=True),
            audience_calibration=DimScore(score=0.85, passed=True),
            duration_feasibility=DimScore(score=0.7, passed=False, issues=["Too short"]),
            key_points_quality=DimScore(score=0.8, passed=True),
            narrative_coherence=DimScore(score=0.9, passed=True),
        )
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("agents.demo_pipeline.eval_rubrics.text_eval_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            dims = await run_text_evaluation(
                {"audience": "family", "scenes": [], "intro_narration": "", "outro_narration": ""},
                {}, 180,
            )

        assert len(dims) == 5
        assert all(d.category == "text" for d in dims)
        names = {d.name for d in dims}
        assert "style_compliance" in names
        assert "duration_feasibility" in names
        # Check the failing one
        dur = next(d for d in dims if d.name == "duration_feasibility")
        assert dur.passed is False
        assert "Too short" in dur.issues
```

**Run:** `uv run pytest tests/test_demo_eval_rubrics.py -v`

**Commit:** `git add agents/demo_pipeline/eval_rubrics.py tests/test_demo_eval_rubrics.py && git commit -m "feat(demo-eval): add LLM-based text narration evaluation"`

---

## Task 4: Visual Evaluation (Gemini Pro Vision)

**Files:**
- Modify: `agents/demo_pipeline/eval_rubrics.py` (add visual evaluation functions)
- Modify: `tests/test_demo_eval_rubrics.py` (add visual evaluation tests)

**What:** Send screenshots to Gemini Pro via LiteLLM as `BinaryContent` images. Evaluate visual clarity, variety, theme compliance, and visual-narration alignment.

**Implementation** — add to `eval_rubrics.py`:

```python
from pydantic_ai.messages import BinaryContent


class VisualEvalOutput(BaseModel):
    """Structured output from visual evaluation LLM."""
    visual_clarity: DimScore
    visual_variety: DimScore
    theme_compliance: DimScore
    visual_narration_alignment: DimScore


visual_eval_agent = Agent(
    get_model("gemini-pro"),
    system_prompt=(
        "You are a visual quality evaluator for presentation screenshots. "
        "You will receive multiple screenshots from a demo presentation along with "
        "their scene narrations. Evaluate the visual quality across four dimensions. "
        "Be specific — cite which screenshot/scene has issues. "
        "Score each dimension 0.0-1.0 where 0.8+ is passing."
    ),
    output_type=VisualEvalOutput,
)


def _load_screenshots_as_content(
    demo_dir: Path, script_data: dict,
) -> list[str | BinaryContent]:
    """Load screenshots and interleave with narration text for the vision prompt."""
    content: list[str | BinaryContent] = []
    screenshots_dir = demo_dir / "screenshots"

    for i, scene in enumerate(script_data.get("scenes", []), 1):
        # Find matching screenshot
        pattern = f"{i:02d}-*.png"
        matches = list(screenshots_dir.glob(pattern))
        if not matches:
            content.append(f"\n--- Scene {i}: {scene['title']} ---\n[Screenshot missing]\nNarration: {scene['narration']}\n")
            continue

        screenshot_path = matches[0]
        image_bytes = screenshot_path.read_bytes()
        image = BinaryContent(data=image_bytes, media_type="image/png")

        content.append(f"\n--- Scene {i}: {scene['title']} ---\nNarration: {scene['narration']}\nKey points: {', '.join(scene.get('key_points', []))}\n")
        content.append(image)

    return content


def _build_visual_eval_prompt(script_data: dict) -> str:
    """Build the text portion of the visual evaluation prompt."""
    return f"""Evaluate the visual quality of these demo screenshots.

The demo is titled "{script_data.get('title', 'Unknown')}" for a {script_data.get('audience', 'unknown')} audience.

## Evaluation Criteria

### 1. visual_clarity
- Screenshots should be legible and show complete, loaded content
- No error pages, loading spinners, blank screens, or browser chrome artifacts
- Text in screenshots should be readable at presentation resolution
- If a screenshot appears to show a real UI, it should show meaningful content

### 2. visual_variety
- Screenshots should show different views, pages, or data across scenes
- A demo should not have all screenshots looking nearly identical
- Different scenes should provide visual progression through the subject matter

### 3. theme_compliance
- Any diagrams or charts should use dark background colors (Gruvbox: #282828 bg, #ebdbb2 text)
- Visual style should be consistent across all scenes
- Color palette should be cohesive (Gruvbox tones: orange #fe8019, yellow #fabd2f, blue #83a598, green #b8bb26)

### 4. visual_narration_alignment
- What's shown in each screenshot should relate to what's narrated
- The visual should serve the scene's communication purpose
- If narration discusses a specific feature, the screenshot should show that feature

Score each dimension 0.0-1.0 (0.8+ = pass). Cite specific scenes for any issues."""


async def run_visual_evaluation(
    demo_dir: Path, script_data: dict,
) -> list[DemoEvalDimension]:
    """Run vision-model evaluation on demo screenshots."""
    screenshot_content = _load_screenshots_as_content(demo_dir, script_data)

    if not any(isinstance(c, BinaryContent) for c in screenshot_content):
        # No screenshots loaded — return failing scores
        return [
            DemoEvalDimension(
                name=name, category="visual", passed=False, score=0.0,
                issues=["No screenshots available for evaluation"],
            )
            for name in ["visual_clarity", "visual_variety", "theme_compliance", "visual_narration_alignment"]
        ]

    prompt_text = _build_visual_eval_prompt(script_data)
    user_prompt: list[str | BinaryContent] = [prompt_text] + screenshot_content

    result = await visual_eval_agent.run(user_prompt=user_prompt)
    output = result.output

    dimensions = []
    for name in ["visual_clarity", "visual_variety", "theme_compliance", "visual_narration_alignment"]:
        dim_score: DimScore = getattr(output, name)
        dimensions.append(DemoEvalDimension(
            name=name, category="visual",
            passed=dim_score.passed, score=dim_score.score,
            issues=dim_score.issues, evidence=dim_score.evidence,
        ))
    return dimensions
```

**Tests** — add to `tests/test_demo_eval_rubrics.py`:

```python
from agents.demo_pipeline.eval_rubrics import (
    _load_screenshots_as_content,
    _build_visual_eval_prompt,
    run_visual_evaluation,
    VisualEvalOutput,
)
from pydantic_ai.messages import BinaryContent


class TestLoadScreenshotsAsContent:
    def test_loads_screenshots(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path, scenes=2)
        script_data = json.loads((demo_dir / "script.json").read_text())
        content = _load_screenshots_as_content(demo_dir, script_data)
        # Should have text + image pairs for each scene
        images = [c for c in content if isinstance(c, BinaryContent)]
        texts = [c for c in content if isinstance(c, str)]
        assert len(images) == 2
        assert len(texts) == 2

    def test_handles_missing_screenshot(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path, scenes=2)
        # Remove one screenshot
        pngs = sorted((demo_dir / "screenshots").glob("*.png"))
        pngs[0].unlink()
        script_data = json.loads((demo_dir / "script.json").read_text())
        content = _load_screenshots_as_content(demo_dir, script_data)
        images = [c for c in content if isinstance(c, BinaryContent)]
        assert len(images) == 1  # only one loaded


class TestBuildVisualEvalPrompt:
    def test_includes_audience(self):
        prompt = _build_visual_eval_prompt({"title": "My Demo", "audience": "family"})
        assert "family" in prompt
        assert "visual_clarity" in prompt


class TestRunVisualEvaluation:
    @pytest.mark.asyncio
    async def test_no_screenshots_returns_failing(self, tmp_path):
        demo_dir = tmp_path / "empty"
        demo_dir.mkdir()
        (demo_dir / "screenshots").mkdir()
        dims = await run_visual_evaluation(demo_dir, {"scenes": []})
        assert len(dims) == 4
        assert all(d.passed is False for d in dims)

    @pytest.mark.asyncio
    async def test_returns_four_dimensions(self, tmp_path):
        demo_dir = _make_demo_dir(tmp_path, scenes=2)
        script_data = json.loads((demo_dir / "script.json").read_text())

        mock_output = VisualEvalOutput(
            visual_clarity=DimScore(score=0.9, passed=True),
            visual_variety=DimScore(score=0.7, passed=False, issues=["Screenshots look similar"]),
            theme_compliance=DimScore(score=0.85, passed=True),
            visual_narration_alignment=DimScore(score=0.8, passed=True),
        )
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("agents.demo_pipeline.eval_rubrics.visual_eval_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            dims = await run_visual_evaluation(demo_dir, script_data)

        assert len(dims) == 4
        assert all(d.category == "visual" for d in dims)
        variety = next(d for d in dims if d.name == "visual_variety")
        assert variety.passed is False
```

**Run:** `uv run pytest tests/test_demo_eval_rubrics.py -v`

**Commit:** `git add agents/demo_pipeline/eval_rubrics.py tests/test_demo_eval_rubrics.py && git commit -m "feat(demo-eval): add Gemini Pro vision-based visual evaluation"`

---

## Task 5: Diagnosis and Planning Overrides

**Files:**
- Modify: `agents/demo_pipeline/eval_rubrics.py` (add diagnosis function)
- Modify: `tests/test_demo_eval_rubrics.py` (add diagnosis tests)

**What:** When evaluation fails, an LLM analyzes the failures and produces planning prompt overrides — additional instructions to append to the next `build_planning_prompt()` call.

**Implementation** — add to `eval_rubrics.py`:

```python
class DiagnosisOutput(BaseModel):
    """LLM diagnosis of evaluation failures."""
    root_causes: list[str] = Field(description="Identified root causes for failures")
    planning_overrides: str = Field(description="Additional instructions to append to the planning prompt on next iteration")
    adjustments_summary: list[str] = Field(description="Human-readable list of what will change")


diagnosis_agent = Agent(
    get_model("balanced"),
    system_prompt=(
        "You are a presentation quality improvement specialist. Given evaluation failures, "
        "diagnose root causes and produce specific, actionable planning prompt overrides "
        "that will fix the issues on the next generation attempt. "
        "Be specific — don't say 'improve quality', say exactly what instruction to add. "
        "The overrides will be appended verbatim to the demo planning prompt."
    ),
    output_type=DiagnosisOutput,
)


def _build_diagnosis_prompt(
    eval_dimensions: list[DemoEvalDimension],
    script_data: dict,
    style_guide: dict,
    iteration: int,
) -> str:
    """Build the diagnosis prompt from evaluation failures."""
    failing = [d for d in eval_dimensions if not d.passed]
    failing_text = "\n".join(
        f"- **{d.name}** (score: {d.score:.2f}): {'; '.join(d.issues)}"
        + (f"\n  Evidence: {d.evidence}" if d.evidence else "")
        for d in failing
    )

    return f"""The demo evaluation failed on iteration {iteration}. Diagnose the root causes and produce planning prompt overrides.

## Failing Dimensions
{failing_text}

## Current Script Summary
Title: {script_data.get('title', 'Unknown')}
Audience: {script_data.get('audience', 'unknown')}
Scenes: {len(script_data.get('scenes', []))}
Intro: {script_data.get('intro_narration', '')[:200]}

## Style Guide
Voice: {style_guide.get('voice', 'first-person')}
Avoid: {'; '.join(style_guide.get('avoid', []))}

## Instructions
1. Identify the root cause of each failure
2. Produce SPECIFIC planning prompt override text that will fix these issues
3. The override text gets appended to the planning prompt — write it as direct instructions
4. Don't duplicate what's already in the style guide — only add NEW, SPECIFIC corrections
5. Focus on the most impactful changes

Example override: "CRITICAL: The narration for the family audience must use NO technical terms. Replace 'API', 'container', 'vector database' with plain language like 'the system', 'a program', 'its memory'."
"""


async def diagnose_failures(
    eval_dimensions: list[DemoEvalDimension],
    script_data: dict,
    style_guide: dict,
    iteration: int,
) -> DiagnosisOutput:
    """Diagnose evaluation failures and produce planning overrides."""
    prompt = _build_diagnosis_prompt(eval_dimensions, script_data, style_guide, iteration)
    result = await diagnosis_agent.run(prompt)
    return result.output
```

**Tests** — add to `tests/test_demo_eval_rubrics.py`:

```python
from agents.demo_pipeline.eval_rubrics import (
    _build_diagnosis_prompt,
    diagnose_failures,
    DiagnosisOutput,
)


class TestBuildDiagnosisPrompt:
    def test_includes_failing_dimensions(self):
        dims = [
            DemoEvalDimension(name="style", category="text", passed=False, score=0.3,
                              issues=["Uses 'leverage'", "Passive voice"], evidence="Scene 2: 'leverage the system'"),
            DemoEvalDimension(name="clarity", category="visual", passed=True, score=0.9),
        ]
        prompt = _build_diagnosis_prompt(dims, {"title": "Demo", "scenes": []}, {}, 1)
        assert "style" in prompt
        assert "leverage" in prompt
        # Should NOT include passing dimensions in failure list
        assert "clarity" not in prompt.split("Failing Dimensions")[1].split("Current Script")[0]

    def test_includes_iteration_number(self):
        prompt = _build_diagnosis_prompt([], {}, {}, 3)
        assert "iteration 3" in prompt


class TestDiagnoseFailures:
    @pytest.mark.asyncio
    async def test_returns_diagnosis(self):
        mock_output = DiagnosisOutput(
            root_causes=["Narration uses corporate jargon for family audience"],
            planning_overrides="CRITICAL: Replace all technical terms with plain language.",
            adjustments_summary=["Simplified vocabulary for family audience"],
        )
        mock_result = MagicMock()
        mock_result.output = mock_output

        with patch("agents.demo_pipeline.eval_rubrics.diagnosis_agent") as mock_agent:
            mock_agent.run = AsyncMock(return_value=mock_result)
            diagnosis = await diagnose_failures(
                [DemoEvalDimension(name="style", category="text", passed=False, score=0.3, issues=["jargon"])],
                {"title": "Demo", "scenes": []}, {}, 1,
            )

        assert len(diagnosis.root_causes) == 1
        assert "CRITICAL" in diagnosis.planning_overrides
```

**Run:** `uv run pytest tests/test_demo_eval_rubrics.py -v`

**Commit:** `git add agents/demo_pipeline/eval_rubrics.py tests/test_demo_eval_rubrics.py && git commit -m "feat(demo-eval): add failure diagnosis and planning override generation"`

---

## Task 6: Evaluation Agent Orchestrator

**Files:**
- Create: `agents/demo_eval.py`
- Create: `tests/test_demo_eval.py`

**What:** The main evaluation agent that orchestrates the generate → evaluate → heal loop. This is the entry point: `uv run python -m agents.demo_eval`.

**Implementation** (`agents/demo_eval.py`):

```python
"""Demo evaluation agent — generates, evaluates, and iteratively improves demos."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

from agents.demo_models import DemoEvalDimension, DemoEvalReport, DemoEvalResult

log = logging.getLogger(__name__)

DEFAULT_SCENARIO = "the system for a non-technical friend"
DEFAULT_FORMAT = "slides"
DEFAULT_DURATION = "3m"
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_PASS_THRESHOLD = 0.8


async def evaluate_demo_output(
    demo_dir: Path,
    expected_audience: str | None = None,
    target_seconds: int = 180,
) -> DemoEvalReport:
    """Evaluate a demo output directory. Returns evaluation report."""
    from agents.demo_pipeline.eval_rubrics import (
        run_structural_checks,
        run_text_evaluation,
        run_visual_evaluation,
    )
    from agents.demo_pipeline.narrative import load_style_guide

    # Load script data
    script_data = json.loads((demo_dir / "script.json").read_text())
    style_guide = load_style_guide()

    # Run all three evaluation categories
    structural_dims = run_structural_checks(demo_dir, expected_audience)
    text_dims = await run_text_evaluation(script_data, style_guide, target_seconds)
    visual_dims = await run_visual_evaluation(demo_dir, script_data)

    all_dims = structural_dims + text_dims + visual_dims

    # Compute overall score (weighted: structural 0.2, text 0.4, visual 0.4)
    weights = {"structural": 0.2, "text": 0.4, "visual": 0.4}
    weighted_sum = 0.0
    weight_total = 0.0
    for dim in all_dims:
        w = weights.get(dim.category, 0.33)
        weighted_sum += dim.score * w
        weight_total += w

    overall_score = weighted_sum / weight_total if weight_total > 0 else 0.0
    overall_pass = overall_score >= DEFAULT_PASS_THRESHOLD and all(
        d.passed for d in all_dims if d.category == "structural"
    )

    return DemoEvalReport(
        dimensions=all_dims,
        overall_pass=overall_pass,
        overall_score=round(overall_score, 3),
    )


async def run_eval_loop(
    scenario: str = DEFAULT_SCENARIO,
    format: str = DEFAULT_FORMAT,
    duration: str = DEFAULT_DURATION,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    pass_threshold: float = DEFAULT_PASS_THRESHOLD,
    on_progress: callable | None = None,
) -> DemoEvalResult:
    """Run the full generate → evaluate → heal loop."""
    from agents.demo import generate_demo, parse_request, resolve_audience, load_personas, parse_duration
    from agents.demo_pipeline.eval_rubrics import diagnose_failures
    from agents.demo_pipeline.narrative import load_style_guide

    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)
        log.info(msg)

    start_time = time.time()
    style_guide = load_style_guide()
    _, audience_text = parse_request(scenario)
    personas = load_personas()
    archetype, _ = resolve_audience(audience_text, personas)
    target_seconds = parse_duration(duration, archetype)

    history: list[DemoEvalReport] = []
    planning_overrides = ""
    demo_dir: Path | None = None

    for iteration in range(1, max_iterations + 1):
        progress(f"\n{'='*60}")
        progress(f"ITERATION {iteration}/{max_iterations}")
        progress(f"{'='*60}")

        # Generate
        progress("Generating demo...")
        request = scenario
        if planning_overrides:
            # Inject overrides by extending the request — they'll flow into the planning prompt
            # We append to an env var that generate_demo can pick up
            import os
            os.environ["DEMO_EVAL_OVERRIDES"] = planning_overrides

        try:
            demo_dir = await generate_demo(
                request=request, format=format, duration=duration,
                on_progress=progress,
            )
        except Exception as e:
            progress(f"Generation failed: {e}")
            report = DemoEvalReport(
                dimensions=[DemoEvalDimension(
                    name="generation_error", category="structural",
                    passed=False, score=0.0, issues=[str(e)],
                )],
                overall_pass=False, overall_score=0.0, iteration=iteration,
                adjustments_applied=planning_overrides.split("\n") if planning_overrides else [],
            )
            history.append(report)
            continue
        finally:
            import os
            os.environ.pop("DEMO_EVAL_OVERRIDES", None)

        # Evaluate
        progress("Evaluating output...")
        report = await evaluate_demo_output(
            demo_dir, expected_audience=archetype, target_seconds=target_seconds,
        )
        report.iteration = iteration
        if planning_overrides:
            report.adjustments_applied = [
                line.strip() for line in planning_overrides.split("\n") if line.strip()
            ]
        history.append(report)

        # Report scores
        progress(f"\nEvaluation scores (iteration {iteration}):")
        for dim in report.dimensions:
            status = "PASS" if dim.passed else "FAIL"
            progress(f"  [{status}] {dim.name}: {dim.score:.2f}")
            for issue in dim.issues:
                progress(f"         -> {issue}")
        progress(f"\n  Overall: {report.overall_score:.2f} ({'PASS' if report.overall_pass else 'FAIL'})")

        if report.overall_pass:
            progress(f"\nDemo PASSED evaluation on iteration {iteration}")
            break

        # Diagnose and plan fixes
        if iteration < max_iterations:
            progress("\nDiagnosing failures...")
            script_data = json.loads((demo_dir / "script.json").read_text())
            diagnosis = await diagnose_failures(
                report.dimensions, script_data, style_guide, iteration,
            )
            progress(f"Root causes: {'; '.join(diagnosis.root_causes)}")
            progress(f"Adjustments: {'; '.join(diagnosis.adjustments_summary)}")

            # Accumulate overrides
            planning_overrides += f"\n{diagnosis.planning_overrides}"

    elapsed = time.time() - start_time
    final_report = history[-1] if history else DemoEvalReport(
        dimensions=[], overall_pass=False, overall_score=0.0,
    )

    result = DemoEvalResult(
        scenario=scenario,
        passed=final_report.overall_pass,
        iterations=len(history),
        final_report=final_report,
        history=history,
        demo_dir=str(demo_dir) if demo_dir else "",
        total_duration_seconds=round(elapsed, 1),
    )

    # Save result
    if demo_dir:
        (demo_dir / "eval_result.json").write_text(result.model_dump_json(indent=2))
        progress(f"\nEvaluation result saved to {demo_dir / 'eval_result.json'}")

    return result


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate demo output quality with LLM-as-judge",
        prog="python -m agents.demo_eval",
    )
    parser.add_argument(
        "--scenario", default=DEFAULT_SCENARIO,
        help=f"Demo request text (default: '{DEFAULT_SCENARIO}')",
    )
    parser.add_argument("--format", default=DEFAULT_FORMAT, choices=["slides", "video"])
    parser.add_argument("--duration", default=DEFAULT_DURATION, help="Target duration (e.g. '3m', '180s')")
    parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)
    parser.add_argument("--pass-threshold", type=float, default=DEFAULT_PASS_THRESHOLD)
    parser.add_argument(
        "--eval-only", type=Path, default=None,
        help="Evaluate an existing demo directory (no generation or healing)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.eval_only:
        # Evaluate existing output
        report = await evaluate_demo_output(args.eval_only)
        print(f"\nOverall: {report.overall_score:.2f} ({'PASS' if report.overall_pass else 'FAIL'})")
        for dim in report.dimensions:
            status = "PASS" if dim.passed else "FAIL"
            print(f"  [{status}] {dim.name}: {dim.score:.2f}")
            for issue in dim.issues:
                print(f"         -> {issue}")
        sys.exit(0 if report.overall_pass else 1)

    # Full eval loop
    result = await run_eval_loop(
        scenario=args.scenario,
        format=args.format,
        duration=args.duration,
        max_iterations=args.max_iterations,
        pass_threshold=args.pass_threshold,
        on_progress=lambda msg: print(msg),
    )

    print(f"\n{'='*60}")
    print(f"FINAL RESULT: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Iterations: {result.iterations}")
    print(f"Score: {result.final_report.overall_score:.2f}")
    print(f"Duration: {result.total_duration_seconds:.0f}s")
    print(f"Output: {result.demo_dir}")
    print(f"{'='*60}")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
```

**Note on planning overrides:** The env var approach (`DEMO_EVAL_OVERRIDES`) is a temporary mechanism. A cleaner approach would be to add a `planning_overrides` parameter to `generate_demo()`. This is tracked as a minor follow-up — for Task 7 (integration wiring).

**Tests** (`tests/test_demo_eval.py`):

```python
"""Tests for the demo evaluation agent."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from agents.demo_models import DemoEvalDimension, DemoEvalReport, DemoEvalResult


class TestEvaluateDemoOutput:
    @pytest.mark.asyncio
    async def test_combines_all_categories(self, tmp_path):
        """Verify evaluate_demo_output combines structural, text, and visual results."""
        from tests.test_demo_eval_rubrics import _make_demo_dir

        demo_dir = _make_demo_dir(tmp_path)

        struct_dims = [
            DemoEvalDimension(name="files_present", category="structural", passed=True, score=1.0),
            DemoEvalDimension(name="metadata_correctness", category="structural", passed=True, score=1.0),
            DemoEvalDimension(name="html_integrity", category="structural", passed=True, score=1.0),
        ]
        text_dims = [
            DemoEvalDimension(name="style_compliance", category="text", passed=True, score=0.9),
            DemoEvalDimension(name="audience_calibration", category="text", passed=True, score=0.85),
            DemoEvalDimension(name="duration_feasibility", category="text", passed=True, score=0.8),
            DemoEvalDimension(name="key_points_quality", category="text", passed=True, score=0.8),
            DemoEvalDimension(name="narrative_coherence", category="text", passed=True, score=0.9),
        ]
        visual_dims = [
            DemoEvalDimension(name="visual_clarity", category="visual", passed=True, score=0.85),
            DemoEvalDimension(name="visual_variety", category="visual", passed=True, score=0.8),
            DemoEvalDimension(name="theme_compliance", category="visual", passed=True, score=0.9),
            DemoEvalDimension(name="visual_narration_alignment", category="visual", passed=True, score=0.85),
        ]

        with patch("agents.demo_eval.run_structural_checks", return_value=struct_dims) as mock_struct, \
             patch("agents.demo_eval.run_text_evaluation", new_callable=AsyncMock, return_value=text_dims), \
             patch("agents.demo_eval.run_visual_evaluation", new_callable=AsyncMock, return_value=visual_dims):

            from agents.demo_eval import evaluate_demo_output
            report = await evaluate_demo_output(demo_dir, expected_audience="family")

        assert len(report.dimensions) == 12  # 3 + 5 + 4
        assert report.overall_pass is True
        assert report.overall_score > 0.8

    @pytest.mark.asyncio
    async def test_fails_on_structural_failure(self, tmp_path):
        """Even high text/visual scores fail if structural checks fail."""
        from tests.test_demo_eval_rubrics import _make_demo_dir

        demo_dir = _make_demo_dir(tmp_path)

        struct_dims = [
            DemoEvalDimension(name="files_present", category="structural", passed=False, score=0.0,
                              issues=["Missing script.json"]),
        ]
        text_dims = [
            DemoEvalDimension(name="style_compliance", category="text", passed=True, score=0.95),
        ]
        visual_dims = [
            DemoEvalDimension(name="visual_clarity", category="visual", passed=True, score=0.95),
        ]

        with patch("agents.demo_eval.run_structural_checks", return_value=struct_dims), \
             patch("agents.demo_eval.run_text_evaluation", new_callable=AsyncMock, return_value=text_dims), \
             patch("agents.demo_eval.run_visual_evaluation", new_callable=AsyncMock, return_value=visual_dims):

            from agents.demo_eval import evaluate_demo_output
            report = await evaluate_demo_output(demo_dir)

        assert report.overall_pass is False  # structural failure = overall fail


class TestRunEvalLoop:
    @pytest.mark.asyncio
    async def test_passes_on_first_iteration(self):
        """If generation + evaluation passes immediately, no healing needed."""
        passing_report = DemoEvalReport(
            dimensions=[
                DemoEvalDimension(name="files_present", category="structural", passed=True, score=1.0),
            ],
            overall_pass=True, overall_score=0.9,
        )

        with patch("agents.demo_eval.generate_demo", new_callable=AsyncMock, return_value=Path("/tmp/fake")), \
             patch("agents.demo_eval.evaluate_demo_output", new_callable=AsyncMock, return_value=passing_report), \
             patch("agents.demo_eval.parse_request", return_value=("the system", "a non-technical friend")), \
             patch("agents.demo_eval.resolve_audience", return_value=("family", "")), \
             patch("agents.demo_eval.load_personas", return_value={}), \
             patch("agents.demo_eval.parse_duration", return_value=180), \
             patch("agents.demo_eval.load_style_guide", return_value={}), \
             patch("pathlib.Path.read_text", return_value='{"scenes":[]}'), \
             patch("pathlib.Path.write_text"):

            from agents.demo_eval import run_eval_loop
            result = await run_eval_loop(max_iterations=3)

        assert result.passed is True
        assert result.iterations == 1

    @pytest.mark.asyncio
    async def test_heals_on_second_iteration(self):
        """Fail first, diagnose, pass second."""
        failing_report = DemoEvalReport(
            dimensions=[
                DemoEvalDimension(name="style", category="text", passed=False, score=0.4,
                                  issues=["Uses corporate jargon"]),
            ],
            overall_pass=False, overall_score=0.4,
        )
        passing_report = DemoEvalReport(
            dimensions=[
                DemoEvalDimension(name="style", category="text", passed=True, score=0.9),
            ],
            overall_pass=True, overall_score=0.9,
        )

        eval_call_count = 0

        async def mock_evaluate(*args, **kwargs):
            nonlocal eval_call_count
            eval_call_count += 1
            return failing_report if eval_call_count == 1 else passing_report

        mock_diagnosis = MagicMock()
        mock_diagnosis.root_causes = ["Corporate jargon"]
        mock_diagnosis.planning_overrides = "AVOID: leverage, synergize"
        mock_diagnosis.adjustments_summary = ["Removed jargon"]

        with patch("agents.demo_eval.generate_demo", new_callable=AsyncMock, return_value=Path("/tmp/fake")), \
             patch("agents.demo_eval.evaluate_demo_output", side_effect=mock_evaluate), \
             patch("agents.demo_eval.diagnose_failures", new_callable=AsyncMock, return_value=mock_diagnosis), \
             patch("agents.demo_eval.parse_request", return_value=("the system", "a non-technical friend")), \
             patch("agents.demo_eval.resolve_audience", return_value=("family", "")), \
             patch("agents.demo_eval.load_personas", return_value={}), \
             patch("agents.demo_eval.parse_duration", return_value=180), \
             patch("agents.demo_eval.load_style_guide", return_value={}), \
             patch("pathlib.Path.read_text", return_value='{"scenes":[]}'), \
             patch("pathlib.Path.write_text"):

            from agents.demo_eval import run_eval_loop
            result = await run_eval_loop(max_iterations=3)

        assert result.passed is True
        assert result.iterations == 2
        assert len(result.history) == 2
```

**Run:** `uv run pytest tests/test_demo_eval.py -v`

**Commit:** `git add agents/demo_eval.py tests/test_demo_eval.py && git commit -m "feat(demo-eval): add evaluation agent orchestrator with generate/evaluate/heal loop"`

---

## Task 7: Integration Wiring — Planning Overrides in generate_demo()

**Files:**
- Modify: `agents/demo.py` — add `planning_overrides` parameter to `generate_demo()`
- Modify: `agents/demo_eval.py` — use the parameter instead of env var hack
- Modify: `tests/test_demo_agent.py` — update test for new parameter

**What:** Replace the env var hack with a clean `planning_overrides` parameter on `generate_demo()`.

**Changes to `agents/demo.py`:**

1. Add `planning_overrides: str | None = None` parameter to `generate_demo()` signature (line 186)
2. After building `planning_context` (line 246), append overrides:
   ```python
   if planning_overrides:
       planning_context += f"\n\n## EVALUATION FEEDBACK — CRITICAL CORRECTIONS\n{planning_overrides}"
   ```

**Changes to `agents/demo_eval.py`:**

Replace the env var approach in `run_eval_loop()`:
```python
# Remove: os.environ["DEMO_EVAL_OVERRIDES"] = planning_overrides
# Replace with:
demo_dir = await generate_demo(
    request=request, format=format, duration=duration,
    on_progress=progress,
    planning_overrides=planning_overrides if planning_overrides else None,
)
# Remove: finally: os.environ.pop(...)
```

**Tests** — update existing test in `tests/test_demo_agent.py`:

```python
class TestBuildPrompt:
    # ... existing tests ...

    def test_planning_overrides_not_in_prompt(self):
        """build_planning_prompt doesn't handle overrides — generate_demo does."""
        # This just verifies the function signature hasn't changed
        from agents.demo import build_planning_prompt
        personas = load_personas()
        prompt = build_planning_prompt(
            scope="test", audience_name="family",
            persona=personas["family"],
            research_context="", planning_context="## Override\nDo this thing",
        )
        assert "Do this thing" in prompt
```

**Run:** `uv run pytest tests/test_demo_agent.py tests/test_demo_eval.py -v`

**Commit:** `git add agents/demo.py agents/demo_eval.py tests/test_demo_agent.py && git commit -m "feat(demo-eval): add planning_overrides parameter to generate_demo()"`

---

## Task 8: Full Test Suite Verification + CLAUDE.md Update

**Files:**
- Modify: `<hapaxromana>/CLAUDE.md` — add `demo_eval` to agent table

**What:** Run the full test suite, verify everything passes, update documentation.

**Steps:**

1. Run all demo tests:
   ```bash
   cd <ai-agents> && uv run pytest tests/test_demo*.py -v
   ```

2. Run full test suite:
   ```bash
   cd <ai-agents> && uv run pytest --tb=short -q
   ```

3. Update `<hapaxromana>/CLAUDE.md` agent table — add row:
   ```
   | `demo_eval` | Yes | Demo output evaluator — LLM-as-judge with self-healing loop |
   ```

4. Commit documentation update.

**Run:** Full test suite as above.

**Commit in hapaxromana:** `git add CLAUDE.md && git commit -m "docs: add demo_eval agent to CLAUDE.md agent table"`

---

## Execution Order

```
Task 1 (models) → Task 2 (structural) → Task 3 (text eval) → Task 4 (visual eval) → Task 5 (diagnosis) → Task 6 (orchestrator) → Task 7 (integration) → Task 8 (verification)
```

All tasks are sequential — each builds on the previous.

## Verification

```bash
# All demo eval tests pass
cd <ai-agents> && uv run pytest tests/test_demo_eval*.py -v

# All demo tests pass (no regressions)
cd <ai-agents> && uv run pytest tests/test_demo*.py -v

# Full suite
cd <ai-agents> && uv run pytest --tb=short -q

# Manual smoke test (requires running services):
# uv run python -m agents.demo_eval
# uv run python -m agents.demo_eval --eval-only output/demos/<latest>/
```
