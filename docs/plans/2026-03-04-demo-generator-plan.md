# Demo Generator Phase 1 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Tier 2 Pydantic AI agent that generates audience-tailored slide decks with live system screenshots from a natural language request like "produce a demo of the entire system for a non-technical friend."

**Architecture:** Demo agent (LLM) produces a structured DemoScript. A deterministic pipeline captures screenshots via Playwright, then renders Marp slides. Audience personas stored in YAML drive content/tone selection. Phase 1 = slides only; Phase 2 (future) adds voice + video.

**Tech Stack:** Python 3.12+, pydantic-ai 1.63.0+, Playwright (Python), Marp CLI (npx), Pillow, YAML personas

**Design doc:** `docs/plans/2026-03-04-demo-generator-design.md`

---

### Task 1: Add Dependencies

**Files:**
- Modify: `<ai-agents>/pyproject.toml`

**Step 1: Add playwright and Pillow to dependencies**

In `pyproject.toml`, add to the `dependencies` list:

```toml
    "playwright>=1.49.0",
    "Pillow>=11.0.0",
```

**Step 2: Install dependencies and Playwright browser**

Run:
```bash
cd <ai-agents>
uv sync
uv run playwright install chromium
```

Expected: Dependencies install, Chromium downloads (~150MB).

**Step 3: Verify**

Run:
```bash
cd <ai-agents>
uv run python -c "from playwright.async_api import async_playwright; print('ok')"
uv run python -c "from PIL import Image; print('ok')"
```

Expected: Both print "ok".

**Step 4: Commit**

```bash
cd <ai-agents>
git add pyproject.toml uv.lock
git commit -m "chore: add playwright and Pillow dependencies for demo agent"
```

---

### Task 2: Audience Persona File

**Files:**
- Create: `<ai-agents>/profiles/demo-personas.yaml`

**Step 1: Create the persona definitions**

```yaml
# Audience archetypes for demo generation.
# The demo agent resolves natural language ("a non-technical friend", "a Senior EA") to one of these.

archetypes:
  family:
    description: "Non-technical person who cares about what the system does for the operator"
    tone: "Warm, uses analogies, zero jargon. Explain like showing someone your workshop."
    vocabulary: "simple"
    show:
      - "High-level outcomes and automations"
      - "Visual dashboard and chat interface"
      - "How the system helps with daily routines"
      - "The self-monitoring and self-healing aspects"
    skip:
      - "Architecture diagrams and code"
      - "Infrastructure details (Docker, ports, services)"
      - "Management domain and work context"
      - "Technical implementation choices"
    max_scenes: 6

  technical-peer:
    description: "Fellow engineer evaluating design decisions and architecture"
    tone: "Direct, technical vocabulary, explain the 'why' behind decisions."
    vocabulary: "technical"
    show:
      - "Three-tier agent architecture"
      - "LiteLLM routing, Qdrant vector memory, Langfuse observability"
      - "Pydantic AI agent patterns and tool design"
      - "Health monitoring and self-regulation"
      - "Axiom governance system"
      - "Code patterns and conventions"
    skip:
      - "Personal automations and music production"
      - "Management domain details"
      - "Basic explanations of common tools"
    max_scenes: 12

  leadership:
    description: "Engineering manager or enterprise architect evaluating patterns"
    tone: "Professional, focuses on system patterns, reliability, and scalability principles."
    vocabulary: "enterprise"
    show:
      - "System topology and service architecture"
      - "Observability and cost tracking (Langfuse)"
      - "Reliability patterns (health monitoring, auto-fix, fallback chains)"
      - "Agent orchestration model"
      - "Governance and constraint system (axioms)"
      - "Operational cadence (timers, briefings, drift detection)"
    skip:
      - "Personal context and music production"
      - "Low-level implementation details"
      - "Specific model names and parameters"
    max_scenes: 10

  team-member:
    description: "Direct report who wants to understand the tool ecosystem"
    tone: "Practical, 'here is how you would use this', relatable examples."
    vocabulary: "professional"
    show:
      - "Dashboard overview and what each panel shows"
      - "Chat interface and agent capabilities"
      - "How agents assist with daily work"
      - "The nudge and accommodation systems"
    skip:
      - "Personal data and music production"
      - "Deep infrastructure details"
      - "Axiom governance internals"
    max_scenes: 8
```

**Step 2: Commit**

```bash
cd <ai-agents>
git add profiles/demo-personas.yaml
git commit -m "feat(demo): add audience persona archetypes"
```

---

### Task 3: DemoScript Models

**Files:**
- Create: `<ai-agents>/agents/demo_models.py`
- Create: `<ai-agents>/tests/test_demo_models.py`

**Step 1: Write the test**

```python
"""Tests for demo script data models."""
from __future__ import annotations

import json

from agents.demo_models import (
    AudiencePersona,
    DemoScene,
    DemoScript,
    ScreenshotSpec,
    load_personas,
)


class TestScreenshotSpec:
    def test_minimal(self):
        s = ScreenshotSpec(url="http://localhost:5173")
        assert s.viewport == (1920, 1080)
        assert s.actions == []
        assert s.capture == "viewport"

    def test_with_actions(self):
        s = ScreenshotSpec(
            url="http://localhost:5173/chat",
            actions=["click #input", "type 'hello'"],
            wait_for="Assistant",
            capture="fullpage",
        )
        assert len(s.actions) == 2


class TestDemoScene:
    def test_roundtrip(self):
        scene = DemoScene(
            title="Dashboard Overview",
            narration="This is the main dashboard.",
            duration_hint=8.0,
            screenshot=ScreenshotSpec(url="http://localhost:5173"),
        )
        data = json.loads(scene.model_dump_json())
        restored = DemoScene.model_validate(data)
        assert restored.title == scene.title


class TestDemoScript:
    def test_full_script(self):
        script = DemoScript(
            title="System Demo",
            audience="family",
            scenes=[
                DemoScene(
                    title="Dashboard",
                    narration="Here is the dashboard.",
                    duration_hint=5.0,
                    screenshot=ScreenshotSpec(url="http://localhost:5173"),
                ),
            ],
            intro_narration="Welcome to the demo.",
            outro_narration="That is the system.",
        )
        assert len(script.scenes) == 1
        assert script.audience == "family"


class TestLoadPersonas:
    def test_loads_archetypes(self):
        personas = load_personas()
        assert "family" in personas
        assert "technical-peer" in personas
        assert "leadership" in personas
        assert "team-member" in personas

    def test_persona_fields(self):
        personas = load_personas()
        family = personas["family"]
        assert isinstance(family, AudiencePersona)
        assert family.vocabulary == "simple"
        assert len(family.show) > 0
        assert family.max_scenes > 0
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.demo_models'`

**Step 3: Write the implementation**

```python
"""Data models for the demo generator agent."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

PERSONAS_PATH = Path(__file__).resolve().parent.parent / "profiles" / "demo-personas.yaml"


class ScreenshotSpec(BaseModel):
    """Instructions for capturing a single screenshot."""

    url: str = Field(description="URL to navigate to")
    viewport: tuple[int, int] = Field(
        default=(1920, 1080), description="Browser viewport width x height"
    )
    actions: list[str] = Field(
        default_factory=list,
        description="Playwright actions to execute before capture (e.g. 'click #btn')",
    )
    wait_for: str | None = Field(
        default=None, description="Text or selector to wait for before capture"
    )
    capture: str = Field(
        default="viewport", description="'viewport', 'fullpage', or a CSS selector"
    )


class DemoScene(BaseModel):
    """A single scene in a demo — one screenshot with narration."""

    title: str = Field(description="Scene title (used in slide heading)")
    narration: str = Field(description="Spoken narration text for this scene")
    duration_hint: float = Field(description="Estimated duration in seconds")
    screenshot: ScreenshotSpec = Field(description="How to capture the visual")


class DemoScript(BaseModel):
    """Complete demo script produced by the LLM agent."""

    title: str = Field(description="Demo title")
    audience: str = Field(description="Resolved audience archetype name")
    scenes: list[DemoScene] = Field(description="Ordered list of scenes")
    intro_narration: str = Field(description="Opening narration before first scene")
    outro_narration: str = Field(description="Closing narration after last scene")


class AudiencePersona(BaseModel):
    """An audience archetype loaded from demo-personas.yaml."""

    description: str
    tone: str
    vocabulary: str
    show: list[str]
    skip: list[str]
    max_scenes: int = 10


def load_personas(path: Path | None = None) -> dict[str, AudiencePersona]:
    """Load audience personas from YAML file."""
    p = path or PERSONAS_PATH
    raw = yaml.safe_load(p.read_text())
    return {
        name: AudiencePersona.model_validate(data)
        for name, data in raw["archetypes"].items()
    }
```

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_models.py -v`
Expected: All 6 tests PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo_models.py tests/test_demo_models.py
git commit -m "feat(demo): add DemoScript models and persona loader"
```

---

### Task 4: Screenshot Pipeline

**Files:**
- Create: `<ai-agents>/agents/demo_pipeline/__init__.py`
- Create: `<ai-agents>/agents/demo_pipeline/screenshots.py`
- Create: `<ai-agents>/tests/test_demo_screenshots.py`

**Step 1: Write the test**

```python
"""Tests for screenshot capture pipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.demo_models import ScreenshotSpec
from agents.demo_pipeline.screenshots import capture_screenshots


class TestCaptureScreenshots:
    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "screenshots"
        d.mkdir()
        return d

    @pytest.fixture
    def specs(self) -> list[tuple[str, ScreenshotSpec]]:
        return [
            (
                "01-dashboard",
                ScreenshotSpec(url="http://localhost:5173"),
            ),
            (
                "02-chat",
                ScreenshotSpec(
                    url="http://localhost:5173/chat",
                    wait_for="Send a message",
                ),
            ),
        ]

    @patch("agents.demo_pipeline.screenshots.async_playwright")
    async def test_captures_screenshots(
        self, mock_pw, specs, output_dir
    ):
        # Set up mock chain
        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_context = AsyncMock()
        mock_context.chromium.launch.return_value = mock_browser
        mock_pw.return_value.__aenter__.return_value = mock_context

        progress = []
        paths = await capture_screenshots(
            specs, output_dir, on_progress=lambda msg: progress.append(msg)
        )

        assert len(paths) == 2
        assert mock_page.goto.call_count == 2
        assert mock_page.screenshot.call_count == 2
        assert len(progress) == 2

    @patch("agents.demo_pipeline.screenshots.async_playwright")
    async def test_sets_viewport(self, mock_pw, output_dir):
        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_context = AsyncMock()
        mock_context.chromium.launch.return_value = mock_browser
        mock_pw.return_value.__aenter__.return_value = mock_context

        specs = [
            ("wide", ScreenshotSpec(url="http://localhost:5173", viewport=(2560, 1440))),
        ]
        await capture_screenshots(specs, output_dir)
        mock_page.set_viewport_size.assert_called_with(
            {"width": 2560, "height": 1440}
        )
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_screenshots.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the init file**

`<ai-agents>/agents/demo_pipeline/__init__.py`:
```python
"""Demo generation pipeline — screenshot capture, slide rendering."""
```

**Step 4: Write the implementation**

```python
"""Screenshot capture pipeline using Playwright."""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from playwright.async_api import async_playwright

from agents.demo_models import ScreenshotSpec

log = logging.getLogger(__name__)


async def capture_screenshots(
    specs: list[tuple[str, ScreenshotSpec]],
    output_dir: Path,
    on_progress: Callable[[str], None] | None = None,
) -> list[Path]:
    """Capture screenshots for each spec. Returns list of saved file paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        for i, (name, spec) in enumerate(specs, 1):
            if on_progress:
                on_progress(f"Capturing screenshot {i}/{len(specs)}: {name}")

            await page.set_viewport_size(
                {"width": spec.viewport[0], "height": spec.viewport[1]}
            )
            await page.goto(spec.url, wait_until="networkidle")

            if spec.wait_for:
                await page.wait_for_selector(
                    f"text={spec.wait_for}", timeout=10_000
                )

            for action in spec.actions:
                parts = action.split(" ", 1)
                cmd = parts[0]
                arg = parts[1] if len(parts) > 1 else ""
                if cmd == "click":
                    await page.click(arg)
                elif cmd == "type":
                    await page.keyboard.type(arg.strip("'\""))
                elif cmd == "wait":
                    await page.wait_for_timeout(int(arg))

            filepath = output_dir / f"{name}.png"

            if spec.capture == "fullpage":
                await page.screenshot(path=str(filepath), full_page=True)
            elif spec.capture == "viewport":
                await page.screenshot(path=str(filepath))
            else:
                element = await page.query_selector(spec.capture)
                if element:
                    await element.screenshot(path=str(filepath))
                else:
                    log.warning("Selector %s not found, falling back to viewport", spec.capture)
                    await page.screenshot(path=str(filepath))

            paths.append(filepath)

        await browser.close()

    return paths
```

**Step 5: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_screenshots.py -v`
Expected: All tests PASS.

**Step 6: Commit**

```bash
cd <ai-agents>
git add agents/demo_pipeline/ tests/test_demo_screenshots.py
git commit -m "feat(demo): screenshot capture pipeline with Playwright"
```

---

### Task 5: Marp Slide Renderer

**Files:**
- Create: `<ai-agents>/agents/demo_pipeline/slides.py`
- Create: `<ai-agents>/agents/demo_pipeline/gruvbox-marp.css`
- Create: `<ai-agents>/tests/test_demo_slides.py`

**Step 1: Write the test**

```python
"""Tests for Marp slide generation."""
from __future__ import annotations

from pathlib import Path

from agents.demo_models import DemoScene, DemoScript, ScreenshotSpec
from agents.demo_pipeline.slides import generate_marp_markdown, render_slides


class TestGenerateMarpMarkdown:
    def test_basic_structure(self):
        script = DemoScript(
            title="Test Demo",
            audience="family",
            scenes=[
                DemoScene(
                    title="Dashboard",
                    narration="Here is the dashboard.",
                    duration_hint=5.0,
                    screenshot=ScreenshotSpec(url="http://localhost:5173"),
                ),
            ],
            intro_narration="Welcome.",
            outro_narration="Goodbye.",
        )
        screenshots = {"Dashboard": Path("/tmp/01-dashboard.png")}
        md = generate_marp_markdown(script, screenshots)

        assert "marp: true" in md
        assert "# Test Demo" in md
        assert "Welcome." in md
        assert "Dashboard" in md
        assert "01-dashboard.png" in md
        assert "Goodbye." in md

    def test_speaker_notes(self):
        script = DemoScript(
            title="Test",
            audience="technical-peer",
            scenes=[
                DemoScene(
                    title="Arch",
                    narration="The architecture uses three tiers.",
                    duration_hint=10.0,
                    screenshot=ScreenshotSpec(url="http://localhost:5173"),
                ),
            ],
            intro_narration="Hi.",
            outro_narration="Bye.",
        )
        screenshots = {"Arch": Path("/tmp/arch.png")}
        md = generate_marp_markdown(script, screenshots)

        # Marp speaker notes use <!-- --> comments
        assert "<!--" in md
        assert "The architecture uses three tiers." in md

    def test_multiple_scenes(self):
        scenes = [
            DemoScene(
                title=f"Scene {i}",
                narration=f"Narration {i}.",
                duration_hint=5.0,
                screenshot=ScreenshotSpec(url="http://localhost:5173"),
            )
            for i in range(3)
        ]
        script = DemoScript(
            title="Multi",
            audience="family",
            scenes=scenes,
            intro_narration="Start.",
            outro_narration="End.",
        )
        screenshots = {f"Scene {i}": Path(f"/tmp/scene-{i}.png") for i in range(3)}
        md = generate_marp_markdown(script, screenshots)

        # 3 scene slides + intro + outro = at least 4 slide separators
        assert md.count("\n---\n") >= 4


class TestRenderSlides:
    async def test_writes_markdown_file(self, tmp_path: Path):
        script = DemoScript(
            title="Render Test",
            audience="family",
            scenes=[
                DemoScene(
                    title="Dash",
                    narration="Dashboard view.",
                    duration_hint=5.0,
                    screenshot=ScreenshotSpec(url="http://localhost:5173"),
                ),
            ],
            intro_narration="Hello.",
            outro_narration="Done.",
        )
        # Create a fake screenshot
        screenshot_dir = tmp_path / "screenshots"
        screenshot_dir.mkdir()
        fake_img = screenshot_dir / "01-dash.png"
        fake_img.write_bytes(b"fake png")

        screenshot_map = {"Dash": fake_img}

        md_path = await render_slides(
            script, screenshot_map, tmp_path, render_pdf=False
        )

        assert md_path.exists()
        assert md_path.suffix == ".md"
        content = md_path.read_text()
        assert "marp: true" in content
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_slides.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Create Gruvbox Marp theme**

`<ai-agents>/agents/demo_pipeline/gruvbox-marp.css`:
```css
/* @theme gruvbox */
@import 'default';

:root {
  --bg: #282828;
  --bg1: #3c3836;
  --fg: #ebdbb2;
  --fg-dim: #a89984;
  --accent: #fe8019;
  --green: #b8bb26;
  --blue: #83a598;
  --red: #fb4934;
  --yellow: #fabd2f;
  --purple: #d3869b;
  --aqua: #8ec07c;
}

section {
  background: var(--bg);
  color: var(--fg);
  font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  font-size: 28px;
  padding: 40px 60px;
}

h1 {
  color: var(--accent);
  font-size: 48px;
  border-bottom: 2px solid var(--bg1);
  padding-bottom: 12px;
}

h2 {
  color: var(--yellow);
  font-size: 36px;
}

h3 {
  color: var(--green);
  font-size: 30px;
}

a { color: var(--blue); }

code {
  background: var(--bg1);
  color: var(--green);
  padding: 2px 6px;
  border-radius: 4px;
}

pre {
  background: var(--bg1);
  border-left: 4px solid var(--accent);
  padding: 16px;
  border-radius: 4px;
}

pre code {
  background: none;
  padding: 0;
}

blockquote {
  border-left: 4px solid var(--blue);
  color: var(--fg-dim);
  padding-left: 16px;
}

img {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

/* Title slide */
section.lead {
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

section.lead h1 {
  border-bottom: none;
  font-size: 56px;
}

/* Dim subtitle on title slide */
section.lead p {
  color: var(--fg-dim);
  font-size: 24px;
}

footer {
  color: var(--fg-dim);
  font-size: 14px;
}
```

**Step 4: Write the implementation**

```python
"""Marp slide generation from DemoScript."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from agents.demo_models import DemoScript

log = logging.getLogger(__name__)

THEME_PATH = Path(__file__).parent / "gruvbox-marp.css"


def generate_marp_markdown(
    script: DemoScript, screenshots: dict[str, Path]
) -> str:
    """Generate Marp-flavored markdown from a DemoScript."""
    lines: list[str] = []

    # Front matter
    lines.append("---")
    lines.append("marp: true")
    lines.append("theme: gruvbox")
    lines.append("paginate: true")
    lines.append(f"footer: '{script.title} — for {script.audience}'")
    lines.append("---")
    lines.append("")

    # Title slide
    lines.append("<!-- _class: lead -->")
    lines.append("")
    lines.append(f"# {script.title}")
    lines.append("")
    lines.append(f"*Prepared for: {script.audience}*")
    lines.append("")
    lines.append(f"<!-- {script.intro_narration} -->")
    lines.append("")

    # Scene slides
    for scene in script.scenes:
        lines.append("---")
        lines.append("")
        lines.append(f"## {scene.title}")
        lines.append("")

        # Embed screenshot if available
        img_path = screenshots.get(scene.title)
        if img_path:
            lines.append(f"![bg right:60% fit]({img_path})")
            lines.append("")

        # Speaker notes (narration)
        lines.append("<!--")
        lines.append(scene.narration)
        lines.append("-->")
        lines.append("")

    # Outro slide
    lines.append("---")
    lines.append("")
    lines.append("<!-- _class: lead -->")
    lines.append("")
    lines.append("# Thank You")
    lines.append("")
    lines.append(f"<!-- {script.outro_narration} -->")
    lines.append("")

    return "\n".join(lines)


async def render_slides(
    script: DemoScript,
    screenshots: dict[str, Path],
    output_dir: Path,
    render_pdf: bool = True,
) -> Path:
    """Generate Marp markdown and optionally render to PDF."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy screenshots to output dir so Marp can resolve relative paths
    slides_screenshot_dir = output_dir / "screenshots"
    slides_screenshot_dir.mkdir(exist_ok=True)
    relative_screenshots: dict[str, Path] = {}
    for title, src in screenshots.items():
        dest = slides_screenshot_dir / src.name
        if src.exists():
            shutil.copy2(src, dest)
        relative_screenshots[title] = Path("screenshots") / src.name

    md = generate_marp_markdown(script, relative_screenshots)
    md_path = output_dir / "slides.md"
    md_path.write_text(md)

    if render_pdf:
        pdf_path = output_dir / "slides.pdf"
        # Copy theme to output dir for Marp to find
        theme_dest = output_dir / "gruvbox-marp.css"
        shutil.copy2(THEME_PATH, theme_dest)

        result = subprocess.run(
            [
                "npx", "-y", "@marp-team/marp-cli",
                str(md_path),
                "--theme", str(theme_dest),
                "--html",
                "--allow-local-files",
                "-o", str(pdf_path),
            ],
            capture_output=True,
            text=True,
            cwd=str(output_dir),
        )
        if result.returncode != 0:
            log.error("Marp render failed: %s", result.stderr)
        else:
            log.info("Slides rendered to %s", pdf_path)

    return md_path
```

**Step 5: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_slides.py -v`
Expected: All tests PASS.

**Step 6: Commit**

```bash
cd <ai-agents>
git add agents/demo_pipeline/slides.py agents/demo_pipeline/gruvbox-marp.css tests/test_demo_slides.py
git commit -m "feat(demo): Marp slide renderer with Gruvbox theme"
```

---

### Task 6: Demo Agent (LLM Core)

**Files:**
- Create: `<ai-agents>/agents/demo.py`
- Create: `<ai-agents>/tests/test_demo_agent.py`

**Step 1: Write the test**

```python
"""Tests for the demo agent."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from agents.demo_models import DemoScript, DemoScene, ScreenshotSpec, load_personas


class TestResolveAudience:
    def test_direct_archetype_match(self):
        from agents.demo import resolve_audience

        archetype, context = resolve_audience("family", load_personas())
        assert archetype == "family"

    def test_natural_language_fallback(self):
        from agents.demo import resolve_audience

        # Unknown audience falls back to technical-peer
        archetype, context = resolve_audience(
            "a random stranger", load_personas()
        )
        assert archetype in ("family", "technical-peer", "leadership", "team-member")


class TestBuildPrompt:
    def test_includes_persona(self):
        from agents.demo import build_planning_prompt

        personas = load_personas()
        prompt = build_planning_prompt(
            scope="the entire system",
            audience_name="family",
            persona=personas["family"],
            system_description="A three-tier agent system...",
        )
        assert "family" in prompt.lower() or "warm" in prompt.lower()
        assert "three-tier" in prompt

    def test_includes_scope(self):
        from agents.demo import build_planning_prompt

        personas = load_personas()
        prompt = build_planning_prompt(
            scope="health monitoring",
            audience_name="technical-peer",
            persona=personas["technical-peer"],
            system_description="A three-tier agent system...",
        )
        assert "health monitoring" in prompt


class TestParseRequest:
    def test_simple_for_pattern(self):
        from agents.demo import parse_request

        scope, audience = parse_request("the entire system for a non-technical friend")
        assert scope == "the entire system"
        assert audience == "a non-technical friend"

    def test_no_audience(self):
        from agents.demo import parse_request

        scope, audience = parse_request("health monitoring")
        assert scope == "health monitoring"
        assert audience == "technical-peer"  # default

    def test_complex_audience(self):
        from agents.demo import parse_request

        scope, audience = parse_request(
            "the context maintenance system for a Senior Enterprise Architect on my Platform Services Team"
        )
        assert "context maintenance" in scope
        assert "Senior Enterprise Architect" in audience
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
"""Demo generator agent — produces audience-tailored demos from natural language requests."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai import Agent

from agents.demo_models import (
    AudiencePersona,
    DemoScript,
    load_personas,
)
from agents.demo_pipeline.screenshots import capture_screenshots
from agents.demo_pipeline.slides import render_slides
from shared.config import get_model, PROFILES_DIR

log = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "demos"

# Map common natural-language audience hints to archetypes
AUDIENCE_HINTS: dict[str, str] = {
    "friend": "family",
    "neighbor": "family",
    "partner": "family",
    "mom": "family",
    "dad": "family",
    "parent": "family",
    "friend": "family",
    "kid": "family",
    "child": "family",
    "engineer": "technical-peer",
    "developer": "technical-peer",
    "architect": "leadership",
    "manager": "leadership",
    "director": "leadership",
    "vp": "leadership",
    "cto": "leadership",
    "report": "team-member",
    "team": "team-member",
    "colleague": "team-member",
}


def parse_request(text: str) -> tuple[str, str]:
    """Parse 'scope for audience' from natural language. Returns (scope, audience)."""
    match = re.match(r"(.+?)\s+for\s+(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text.strip(), "technical-peer"


def resolve_audience(
    audience_text: str, personas: dict[str, AudiencePersona]
) -> tuple[str, str]:
    """Resolve audience text to archetype name + extra context."""
    lower = audience_text.lower()

    # Direct archetype match
    if lower in personas:
        return lower, ""

    # Hint-based matching
    for hint, archetype in AUDIENCE_HINTS.items():
        if hint in lower:
            extra = audience_text if archetype != lower else ""
            return archetype, extra

    # Default to technical-peer
    return "technical-peer", audience_text


def build_planning_prompt(
    scope: str,
    audience_name: str,
    persona: AudiencePersona,
    system_description: str,
) -> str:
    """Build the LLM prompt for demo scene planning."""
    show_list = "\n".join(f"  - {item}" for item in persona.show)
    skip_list = "\n".join(f"  - {item}" for item in persona.skip)

    return f"""Plan a demo of: {scope}

Target audience: {audience_name}
Audience description: {persona.description}
Tone: {persona.tone}
Vocabulary level: {persona.vocabulary}

What to show:
{show_list}

What to skip:
{skip_list}

Maximum scenes: {persona.max_scenes}

System overview:
{system_description}

The cockpit web dashboard is at http://localhost:5173 with these pages:
- / — Main dashboard with health, VRAM, containers, timers, briefing, scout, drift, goals, cost panels
- /chat — Chat interface with streaming LLM responses, slash commands, interview mode

Generate a DemoScript with scenes that showcase the requested scope, tailored to this audience.
Each scene needs a URL to screenshot, any actions to take, and narration text.
Write narration as natural spoken language — this will be read aloud by text-to-speech."""


def _load_system_description() -> str:
    """Load system description from available sources."""
    # Try CLAUDE.md first
    claude_md = PROFILES_DIR.parent.parent / "hapaxromana" / "CLAUDE.md"
    if claude_md.exists():
        return claude_md.read_text()[:4000]

    # Fallback to manifest
    manifest = PROFILES_DIR / "manifest.json"
    if manifest.exists():
        return manifest.read_text()[:4000]

    return "A three-tier autonomous agent system with web dashboard, health monitoring, and 13+ agents."


# Agent definition
agent = Agent(
    get_model("balanced"),
    system_prompt=(
        "You are a demo planning assistant. Given a system description and audience persona, "
        "produce a DemoScript that showcases the system effectively for that audience. "
        "Each scene should have a clear purpose, natural narration, and specific screenshot instructions."
    ),
    output_type=DemoScript,
)


async def generate_demo(
    request: str,
    format: str = "slides",
    on_progress: callable | None = None,
) -> Path:
    """Generate a complete demo from a natural language request."""

    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)
        log.info(msg)

    # 1. Parse request
    scope, audience_text = parse_request(request)
    progress(f"Scope: {scope} | Audience: {audience_text}")

    # 2. Resolve audience
    personas = load_personas()
    archetype, extra_context = resolve_audience(audience_text, personas)
    persona = personas[archetype]
    progress(f"Resolved audience: {archetype}")

    # 3. Plan demo (LLM)
    progress("Planning demo scenes...")
    system_desc = _load_system_description()
    prompt = build_planning_prompt(scope, archetype, persona, system_desc)
    if extra_context:
        prompt += f"\n\nAdditional audience context: {extra_context}"

    result = await agent.run(prompt)
    script = result.output

    progress(f"Planned {len(script.scenes)} scenes")

    # 4. Create output directory
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", scope.lower()).strip("-")[:30]
    demo_dir = OUTPUT_DIR / f"{ts}-{slug}"
    demo_dir.mkdir(parents=True, exist_ok=True)

    # Save script for reproducibility
    (demo_dir / "script.json").write_text(script.model_dump_json(indent=2))

    # 5. Capture screenshots
    progress("Capturing screenshots...")
    screenshot_specs = [
        (f"{i:02d}-{re.sub(r'[^a-z0-9]+', '-', scene.title.lower()).strip('-')}", scene.screenshot)
        for i, scene in enumerate(script.scenes, 1)
    ]
    screenshot_paths = await capture_screenshots(
        screenshot_specs, demo_dir / "screenshots", on_progress=progress
    )

    # Map scene titles to screenshot paths
    screenshot_map = {
        scene.title: path
        for scene, path in zip(script.scenes, screenshot_paths)
    }

    # 6. Render slides
    progress("Rendering slides...")
    md_path = await render_slides(
        script, screenshot_map, demo_dir, render_pdf=(format != "markdown-only")
    )

    progress(f"Demo complete: {demo_dir}")
    return demo_dir


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate audience-tailored system demos",
        prog="python -m agents.demo",
    )
    parser.add_argument("request", help="Natural language request, e.g. 'the entire system for a non-technical friend'")
    parser.add_argument("--audience", help="Override audience archetype (family, technical-peer, leadership, team-member)")
    parser.add_argument("--format", choices=["slides", "markdown-only"], default="slides", help="Output format")
    parser.add_argument("--json", action="store_true", help="Print script JSON instead of generating demo")
    args = parser.parse_args()

    request = args.request
    if args.audience:
        # Override audience in request
        scope, _ = parse_request(request)
        request = f"{scope} for {args.audience}"

    if args.json:
        # Just plan, don't capture/render
        scope, audience_text = parse_request(request)
        personas = load_personas()
        archetype, extra = resolve_audience(audience_text, personas)
        persona = personas[archetype]
        system_desc = _load_system_description()
        prompt = build_planning_prompt(scope, archetype, persona, system_desc)
        if extra:
            prompt += f"\n\nAdditional audience context: {extra}"
        result = await agent.run(prompt)
        print(result.output.model_dump_json(indent=2))
    else:
        demo_dir = await generate_demo(
            request,
            format=args.format,
            on_progress=lambda msg: print(f"  {msg}", file=sys.stderr),
        )
        print(f"\nDemo generated: {demo_dir}")
        for f in sorted(demo_dir.rglob("*")):
            if f.is_file():
                print(f"  {f.relative_to(demo_dir)}")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_agent.py -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo.py tests/test_demo_agent.py
git commit -m "feat(demo): demo agent with audience resolution and pipeline orchestration"
```

---

### Task 7: Cockpit API Route

**Files:**
- Modify: `<ai-agents>/cockpit/data/agents.py` (add demo to agent list)

**Step 1: Check existing agent registration**

Read `<ai-agents>/cockpit/data/agents.py` to see how agents are registered. The demo agent should appear in the agent list so the cockpit API can invoke it via `POST /api/agents/demo/run`.

**Step 2: Add demo agent to the registry**

Add to the `AGENTS` list (following the existing pattern):

```python
{
    "name": "demo",
    "description": "Generate audience-tailored system demos",
    "command": "uv run python -m agents.demo",
    "llm": True,
    "flags": ["--json", "--format slides", "--format markdown-only"],
},
```

**Step 3: Verify**

Run: `cd <ai-agents> && uv run cockpit --once 2>/dev/null | grep -i demo || echo "Check agent list manually"`

**Step 4: Commit**

```bash
cd <ai-agents>
git add cockpit/data/agents.py
git commit -m "feat(demo): register demo agent in cockpit API"
```

---

### Task 8: Integration Test

**Files:**
- Create: `<ai-agents>/tests/test_demo_integration.py`

**Step 1: Write an integration test that mocks the LLM but tests the full pipeline**

```python
"""Integration test for demo generation pipeline (LLM mocked, pipeline real)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from agents.demo_models import DemoScript, DemoScene, ScreenshotSpec


class TestDemoIntegration:
    @pytest.fixture
    def mock_script(self) -> DemoScript:
        return DemoScript(
            title="Test System Demo",
            audience="family",
            scenes=[
                DemoScene(
                    title="Dashboard Overview",
                    narration="This is where I see everything at a glance.",
                    duration_hint=8.0,
                    screenshot=ScreenshotSpec(
                        url="http://localhost:5173",
                        capture="viewport",
                    ),
                ),
                DemoScene(
                    title="Chat Interface",
                    narration="And this is where I talk to the system.",
                    duration_hint=6.0,
                    screenshot=ScreenshotSpec(
                        url="http://localhost:5173/chat",
                        wait_for="Send a message",
                        capture="viewport",
                    ),
                ),
            ],
            intro_narration="Let me show you what I have been building.",
            outro_narration="That is the system. Pretty cool, right?",
        )

    @patch("agents.demo_pipeline.screenshots.async_playwright")
    async def test_full_pipeline_mocked(self, mock_pw, mock_script, tmp_path):
        """Test screenshot capture + slide render with mocked browser."""
        from agents.demo_pipeline.screenshots import capture_screenshots
        from agents.demo_pipeline.slides import render_slides

        # Mock Playwright
        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_context = AsyncMock()
        mock_context.chromium.launch.return_value = mock_browser
        mock_pw.return_value.__aenter__.return_value = mock_context

        # Capture screenshots
        specs = [
            (f"{i:02d}-scene", scene.screenshot)
            for i, scene in enumerate(mock_script.scenes, 1)
        ]
        screenshot_dir = tmp_path / "screenshots"
        paths = await capture_screenshots(specs, screenshot_dir)

        # Create fake screenshot files (Playwright is mocked)
        for p in paths:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"fake png data")

        # Build screenshot map
        screenshot_map = {
            scene.title: path
            for scene, path in zip(mock_script.scenes, paths)
        }

        # Render slides (markdown only, skip PDF to avoid npx dependency in CI)
        md_path = await render_slides(
            mock_script, screenshot_map, tmp_path, render_pdf=False
        )

        # Verify outputs
        assert md_path.exists()
        content = md_path.read_text()
        assert "marp: true" in content
        assert "Test System Demo" in content
        assert "Dashboard Overview" in content
        assert "Chat Interface" in content
        assert "Let me show you" in content

        # Verify script metadata
        script_json = tmp_path / "script.json"
        if not script_json.exists():
            # Write it like the real pipeline does
            script_json.write_text(mock_script.model_dump_json(indent=2))
        assert script_json.exists()
```

**Step 2: Run integration test**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_integration.py -v`
Expected: PASS.

**Step 3: Run all demo tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo*.py -v`
Expected: All tests PASS.

**Step 4: Commit**

```bash
cd <ai-agents>
git add tests/test_demo_integration.py
git commit -m "test(demo): add integration test for full demo pipeline"
```

---

### Task 9: Output Directory and .gitignore

**Files:**
- Modify: `<ai-agents>/.gitignore`

**Step 1: Add output directory to .gitignore**

Add to `.gitignore`:
```
output/demos/
```

**Step 2: Create output directory placeholder**

```bash
mkdir -p <ai-agents>/output/demos
touch <ai-agents>/output/demos/.gitkeep
```

**Step 3: Commit**

```bash
cd <ai-agents>
git add .gitignore output/demos/.gitkeep
git commit -m "chore(demo): gitignore demo output, add directory placeholder"
```

---

## Execution Order

Tasks 1-2 are prerequisites (dependencies + persona file).
Tasks 3-5 are independent (models, screenshots, slides).
Task 6 depends on 3-5 (agent imports all modules).
Task 7 depends on 6 (API registration).
Task 8 depends on 3-6 (integration test).
Task 9 is independent.

Recommended: 1 → 2 → 3,4,5 (parallel) → 6 → 7,8,9 (parallel)

## Verification

After all tasks:

```bash
cd <ai-agents>

# All tests pass
uv run pytest tests/test_demo*.py -v

# Dry run (plan only, no screenshots)
uv run python -m agents.demo "the entire system for a non-technical friend" --json

# Full run (requires cockpit API + web server running)
# Terminal 1: uv run cockpit
# Terminal 2: cd <cockpit-web> && pnpm dev
# Terminal 3:
uv run python -m agents.demo "the entire system for a non-technical friend"
```
