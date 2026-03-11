# Demo Quality System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Replace the demo generator's single-shot LLM planning with a multi-stage pipeline: system readiness gate, subject research, narrative-aware script planning, self-critique loop, and supplementary visual generation (D2 diagrams, Matplotlib charts).

**Architecture:** Six new pipeline modules inserted before the existing screenshot/voice/video stages. The planning LLM call is enriched with audience-filtered research, a presenter style guide, narrative framework selection, and duration-driven constraints. A critique stage evaluates 8 quality dimensions and loops up to 3 times. Visual generation adds D2 architecture diagrams and Matplotlib data charts alongside existing screenshots.

**Tech Stack:** Python, Pydantic AI, Matplotlib, D2 (CLI binary), Tavily (web search), existing agents as libraries (health_monitor, introspect, activity_analyzer, briefing).

---

## Key Files (existing, read before implementing)

- `agents/demo.py` — pipeline orchestrator, system prompt at line 153, build_planning_prompt at line 98
- `agents/demo_models.py` — DemoScript, DemoScene, ScreenshotSpec, AudiencePersona
- `agents/demo_pipeline/slides.py` — AUDIENCE_LABELS dict
- `agents/health_monitor.py` — `run_checks()`, `HealthReport` model, `--fix` mode
- `agents/introspect.py` — `generate_manifest()`, `InfrastructureManifest` model
- `agents/activity_analyzer.py` — `LangfuseActivity`, `ModelUsage` models
- `agents/briefing.py` — imports from activity_analyzer + health_monitor
- `shared/langfuse_client.py` — `langfuse_get()` for Langfuse API access
- `shared/config.py` — `get_model()`, `get_qdrant()`, `PROFILES_DIR`
- `profiles/demo-personas.yaml` — audience archetypes
- `profiles/component-registry.yaml` — 16 tracked components

## Execution Order

```
Task 1 (models) ─────────────────────────────────────────────┐
Task 2 (style guide + narrative) ─────────────────────────────┤
Task 3 (readiness gate) ──────────────────────────────────────┤─→ Task 7 (integration)
Task 4 (research stage) ──────────────────────────────────────┤      │
Task 5 (critique loop) ───────────────────────────────────────┤      ▼
Task 6 (visual generation: diagrams + charts) ────────────────┘   Task 8 (cockpit-web)
```

Tasks 1-6 are independent of each other. Task 7 integrates them into demo.py. Task 8 updates cockpit-web.

---

## Task 1: Extend DemoScene and DemoScript models + add duration parsing

**Files:**
- Modify: `agents/demo_models.py`
- Modify: `agents/demo.py` — add `--duration` CLI arg
- Create: `tests/test_demo_models_extended.py`

**demo_models.py changes:**

Add to imports:
```python
from typing import Literal
```

Extend `DemoScene` with three new optional fields (backward-compatible):
```python
class DemoScene(BaseModel):
    """A single scene in a demo — one screenshot with narration."""

    title: str = Field(description="Scene title (used in slide heading)")
    narration: str = Field(description="Spoken narration text for this scene")
    duration_hint: float = Field(ge=1.0, description="Estimated duration in seconds")
    key_points: list[str] = Field(default_factory=list, description="Bullet points to display on the slide")
    screenshot: ScreenshotSpec = Field(description="How to capture the visual")
    visual_type: Literal["screenshot", "diagram", "chart"] = Field(
        default="screenshot",
        description="Type of visual: screenshot (Playwright), diagram (D2), or chart (Matplotlib)",
    )
    diagram_spec: str | None = Field(
        default=None,
        description="D2 source code for diagrams, or chart specification JSON for charts",
    )
    research_notes: str | None = Field(
        default=None,
        description="Factual grounding for this scene's claims — used by critique stage",
    )
```

Add `DemoQualityReport` model (used by critique stage):
```python
class QualityDimension(BaseModel):
    """Evaluation of one quality dimension."""
    name: str
    passed: bool
    severity: Literal["critical", "important", "minor"] | None = None
    issues: list[str] = Field(default_factory=list)

class DemoQualityReport(BaseModel):
    """Output of the self-critique evaluation."""
    dimensions: list[QualityDimension]
    overall_pass: bool
    revision_notes: str | None = None
```

**demo.py CLI changes:**

Add `--duration` argument to the argparse block (after `--format`):
```python
parser.add_argument(
    "--duration", type=str, default=None,
    help="Target duration (e.g., '5m', '10m', '90s'). Defaults based on audience.",
)
```

Add duration parsing function:
```python
def parse_duration(duration_str: str | None, audience: str) -> int:
    """Parse duration string to seconds. Falls back to audience defaults."""
    AUDIENCE_DEFAULTS = {"family": 180, "team-member": 420, "leadership": 600, "technical-peer": 720}
    if duration_str is None:
        return AUDIENCE_DEFAULTS.get(audience, 420)
    duration_str = duration_str.strip().lower()
    if duration_str.endswith("m"):
        return int(float(duration_str[:-1]) * 60)
    if duration_str.endswith("s"):
        return int(float(duration_str[:-1]))
    return int(float(duration_str))
```

**Tests (test_demo_models_extended.py):**

```python
"""Tests for extended demo models and duration parsing."""
from agents.demo_models import DemoScene, ScreenshotSpec, DemoQualityReport, QualityDimension

class TestDemoSceneExtended:
    def test_visual_type_default(self):
        scene = DemoScene(
            title="Test", narration="test", duration_hint=5.0,
            screenshot=ScreenshotSpec(url="http://localhost"),
        )
        assert scene.visual_type == "screenshot"
        assert scene.diagram_spec is None
        assert scene.research_notes is None

    def test_visual_type_diagram(self):
        scene = DemoScene(
            title="Architecture", narration="test", duration_hint=8.0,
            screenshot=ScreenshotSpec(url="http://localhost"),
            visual_type="diagram",
            diagram_spec="direction: right\nA -> B -> C",
        )
        assert scene.visual_type == "diagram"
        assert scene.diagram_spec is not None

    def test_backward_compatible_serialization(self):
        """Old scripts without new fields still parse."""
        data = {
            "title": "Test", "narration": "test", "duration_hint": 5.0,
            "screenshot": {"url": "http://localhost"},
        }
        scene = DemoScene.model_validate(data)
        assert scene.visual_type == "screenshot"

class TestQualityReport:
    def test_all_pass(self):
        report = DemoQualityReport(
            dimensions=[QualityDimension(name="narrative", passed=True)],
            overall_pass=True,
        )
        assert report.overall_pass

    def test_failure(self):
        report = DemoQualityReport(
            dimensions=[
                QualityDimension(name="style", passed=False, severity="critical", issues=["Corporatism detected"]),
            ],
            overall_pass=False,
            revision_notes="Fix corporate language",
        )
        assert not report.overall_pass

class TestParseDuration:
    def test_minutes(self):
        from agents.demo import parse_duration
        assert parse_duration("5m", "family") == 300

    def test_seconds(self):
        from agents.demo import parse_duration
        assert parse_duration("90s", "family") == 90

    def test_audience_default_family(self):
        from agents.demo import parse_duration
        assert parse_duration(None, "family") == 180

    def test_audience_default_peers(self):
        from agents.demo import parse_duration
        assert parse_duration(None, "technical-peer") == 720

    def test_bare_number(self):
        from agents.demo import parse_duration
        assert parse_duration("300", "family") == 300
```

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo_models_extended.py -v`

---

## Task 2: Presenter style guide + narrative framework module

**Files:**
- Create: `profiles/presenter-style.yaml`
- Create: `agents/demo_pipeline/narrative.py`
- Create: `tests/test_demo_narrative.py`

**profiles/presenter-style.yaml:**
```yaml
# Presenter style guide — encodes the operator's natural presentation voice.
# Loaded into every LLM call that generates demo narration.

voice: first-person  # "I built this because..." not passive/third

cadence: state-explain-show  # State the thing → explain why → show it working

transitions: functional  # "That handles monitoring. Next is agent coordination."

avoid:
  - "Corporate filler: leverage, synergize, best-in-class, robust, scalable, ecosystem, paradigm, holistic"
  - "Hedging: kind of, sort of, basically, essentially, just, simply"
  - "Breathless enthusiasm: amazing, incredible, game-changing, exciting, powerful"
  - "Rhetorical questions as transitions"
  - "'Today I'm going to show you...' openings"
  - "'Any questions?' or 'Thank you' closings"
  - "Passive voice where active is clearer"
  - "Buzzword stacking (multiple adjectives before a noun)"

embrace:
  - "Precise vocabulary and concrete numbers"
  - "Honest trade-offs: 'works well for X but I'd do Y differently'"
  - "Short, declarative sentences"
  - "Occasional dry humor — understated, never forced"
  - "Design rationale: why this way, not just what"
  - "First-person experience: 'I noticed...', 'The problem was...'"

opening: "Start with the problem or the thing itself. No preamble, no agenda slide."

closing: "Land on impact or next step. No ceremony, no recap."
```

**agents/demo_pipeline/narrative.py:**

```python
"""Narrative framework selection and duration-driven planning constraints."""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

STYLE_PATH = Path(__file__).resolve().parent.parent.parent / "profiles" / "presenter-style.yaml"


# ── Narrative Frameworks ──────────────────────────────────────────────────────

FRAMEWORKS: dict[str, dict] = {
    "problem-solution-benefit": {
        "name": "Problem → Solution → Benefit",
        "when": "Leadership audiences, architecture reviews, executive briefings",
        "structure": [
            "Open by framing a challenge the audience recognizes or feels",
            "Show how the system addresses that challenge — specific, concrete",
            "Close with measurable impact: numbers, time saved, risk reduced",
        ],
        "section_flow": "problem → approach → implementation → results → next steps",
        "transitions": "Each section answers 'so what?' from the previous one",
    },
    "guided-tour": {
        "name": "Guided Tour",
        "when": "Family, team members, anyone seeing the system for the first time",
        "structure": [
            "Start with the big picture — what is this thing, in one sentence",
            "Walk through capabilities in order of impact (most impressive first)",
            "End with what it means for the viewer — personal relevance",
        ],
        "section_flow": "overview → capability 1 → capability 2 → ... → 'what this means'",
        "transitions": "Natural flow: 'That handles X. The next piece is Y.'",
    },
    "design-rationale": {
        "name": "Design Rationale",
        "when": "Technical peers, architecture discussions, code reviews",
        "structure": [
            "Start with what exists — the system as built",
            "For each component: what it does, then WHY it's built this way",
            "Include trade-offs considered and alternatives rejected",
            "End with what you'd change or what's next",
        ],
        "section_flow": "current state → component deep-dives → trade-offs → future direction",
        "transitions": "Design-decision driven: 'The reason for X is...'",
    },
    "operational-cadence": {
        "name": "Operational Cadence",
        "when": "Team members, leadership interested in day-to-day operations",
        "structure": [
            "Frame around time: what happens every 15 minutes, daily, weekly",
            "Show the automation rhythm — timers, agents, notifications",
            "Demonstrate how issues surface and get handled",
            "End with toil reduction — what the operator doesn't have to do",
        ],
        "section_flow": "timing overview → automated cycles → issue handling → toil metrics",
        "transitions": "Time-based: 'Every 15 minutes...', 'Each morning at 7...'",
    },
}

# Map audience archetypes to their default narrative framework
AUDIENCE_FRAMEWORK: dict[str, str] = {
    "family": "guided-tour",
    "technical-peer": "design-rationale",
    "leadership": "problem-solution-benefit",
    "team-member": "operational-cadence",
}

# Duration → planning constraints
DURATION_TIERS: list[dict] = [
    {"max_seconds": 180,  "scenes": (3, 4),  "words_per_scene": (15, 25), "depth": "headlines only"},
    {"max_seconds": 420,  "scenes": (5, 7),  "words_per_scene": (30, 50), "depth": "key points with context"},
    {"max_seconds": 900,  "scenes": (8, 12), "words_per_scene": (50, 80), "depth": "detailed explanations"},
    {"max_seconds": 1200, "scenes": (10, 15), "words_per_scene": (60, 100), "depth": "full rationale with trade-offs"},
]


def load_style_guide(path: Path | None = None) -> dict:
    """Load the presenter style guide from YAML."""
    p = path or STYLE_PATH
    if not p.exists():
        log.warning("Style guide not found at %s — using empty style", p)
        return {}
    return yaml.safe_load(p.read_text())


def select_framework(audience: str) -> dict:
    """Select narrative framework based on audience archetype."""
    key = AUDIENCE_FRAMEWORK.get(audience, "design-rationale")
    return FRAMEWORKS[key]


def get_duration_constraints(target_seconds: int) -> dict:
    """Get planning constraints for a target duration."""
    for tier in DURATION_TIERS:
        if target_seconds <= tier["max_seconds"]:
            return tier
    return DURATION_TIERS[-1]  # longest tier


def format_planning_context(
    style_guide: dict,
    framework: dict,
    duration_constraints: dict,
    target_seconds: int,
) -> str:
    """Format style guide, narrative framework, and duration constraints into LLM prompt text."""
    lines: list[str] = []

    # Style guide
    lines.append("## Presenter Style Guide")
    lines.append(f"Voice: {style_guide.get('voice', 'first-person')}")
    lines.append(f"Cadence: {style_guide.get('cadence', 'state-explain-show')}")
    lines.append(f"Opening: {style_guide.get('opening', '')}")
    lines.append(f"Closing: {style_guide.get('closing', '')}")
    if style_guide.get("avoid"):
        lines.append("AVOID: " + "; ".join(style_guide["avoid"]))
    if style_guide.get("embrace"):
        lines.append("EMBRACE: " + "; ".join(style_guide["embrace"]))
    lines.append("")

    # Narrative framework
    lines.append(f"## Narrative Framework: {framework['name']}")
    lines.append(f"Flow: {framework['section_flow']}")
    lines.append(f"Transitions: {framework['transitions']}")
    for i, step in enumerate(framework["structure"], 1):
        lines.append(f"  {i}. {step}")
    lines.append("")

    # Duration constraints
    minutes = target_seconds / 60
    scene_min, scene_max = duration_constraints["scenes"]
    words_min, words_max = duration_constraints["words_per_scene"]
    lines.append(f"## Duration Constraints: {minutes:.0f} minutes")
    lines.append(f"Scene count: {scene_min}-{scene_max} scenes")
    lines.append(f"Narration per scene: {words_min}-{words_max} words (~{words_min // 2.5:.0f}-{words_max // 2.5:.0f} seconds of speech)")
    lines.append(f"Depth: {duration_constraints['depth']}")
    lines.append(f"Total narration budget: ~{int(minutes * 2.5 * 25)} words across all scenes")
    lines.append("")

    return "\n".join(lines)
```

**Tests (test_demo_narrative.py):**

```python
"""Tests for narrative framework selection and planning constraints."""
from agents.demo_pipeline.narrative import (
    load_style_guide, select_framework, get_duration_constraints,
    format_planning_context, FRAMEWORKS, AUDIENCE_FRAMEWORK,
)

class TestSelectFramework:
    def test_family_gets_guided_tour(self):
        fw = select_framework("family")
        assert fw["name"] == "Guided Tour"

    def test_leadership_gets_psb(self):
        fw = select_framework("leadership")
        assert fw["name"] == "Problem → Solution → Benefit"

    def test_peers_get_design_rationale(self):
        fw = select_framework("technical-peer")
        assert fw["name"] == "Design Rationale"

    def test_team_gets_operational_cadence(self):
        fw = select_framework("team-member")
        assert fw["name"] == "Operational Cadence"

    def test_unknown_defaults_to_design_rationale(self):
        fw = select_framework("stranger")
        assert fw["name"] == "Design Rationale"

class TestDurationConstraints:
    def test_3_minute_demo(self):
        c = get_duration_constraints(180)
        assert c["scenes"] == (3, 4)
        assert c["depth"] == "headlines only"

    def test_10_minute_demo(self):
        c = get_duration_constraints(600)
        assert c["scenes"] == (8, 12)

    def test_20_minute_demo(self):
        c = get_duration_constraints(1200)
        assert c["scenes"] == (10, 15)

    def test_beyond_max_uses_longest(self):
        c = get_duration_constraints(3600)
        assert c["scenes"] == (10, 15)

class TestLoadStyleGuide:
    def test_loads_from_default_path(self):
        guide = load_style_guide()
        assert "voice" in guide
        assert "avoid" in guide
        assert "embrace" in guide

    def test_missing_file_returns_empty(self, tmp_path):
        guide = load_style_guide(tmp_path / "nonexistent.yaml")
        assert guide == {}

class TestFormatPlanningContext:
    def test_contains_all_sections(self):
        guide = load_style_guide()
        fw = select_framework("leadership")
        dc = get_duration_constraints(600)
        text = format_planning_context(guide, fw, dc, 600)
        assert "Presenter Style Guide" in text
        assert "Narrative Framework" in text
        assert "Duration Constraints" in text
        assert "10 minutes" in text

    def test_includes_avoid_list(self):
        guide = load_style_guide()
        fw = select_framework("family")
        dc = get_duration_constraints(180)
        text = format_planning_context(guide, fw, dc, 180)
        assert "AVOID" in text
```

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo_narrative.py -v`

---

## Task 3: System readiness gate

**Files:**
- Create: `agents/demo_pipeline/readiness.py`
- Create: `tests/test_demo_readiness.py`

**agents/demo_pipeline/readiness.py:**

The readiness gate checks system health and starts required services. Uses direct imports from existing agents (following the codebase pattern — agents call agent functions directly, not via subprocess).

```python
"""System readiness gate — ensures system is presentable before demo generation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ReadinessResult:
    """Result of the system readiness check."""
    ready: bool
    health_score: str = ""  # e.g., "74/75"
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    health_report: object | None = None  # HealthReport if available
    briefing_summary: str = ""


def check_readiness(
    require_tts: bool = False,
    auto_fix: bool = True,
    on_progress: callable | None = None,
) -> ReadinessResult:
    """Run system readiness checks. Returns ReadinessResult.

    Checks:
    1. Health monitor (with --fix if auto_fix=True)
    2. Cockpit API (:8050) reachable
    3. Cockpit web (:5173) reachable
    4. TTS service (if require_tts=True)
    5. Voice sample exists (if require_tts=True)
    """
    # Implementation uses:
    # from agents.health_monitor import run_checks, HealthReport
    # from agents.health_monitor import http_get (for service checks)
    # ...health_monitor.run_checks(auto_fix=auto_fix) returns HealthReport
    # Check cockpit API: http_get("http://localhost:8050/health")
    # Check cockpit web: http_get("http://localhost:5173")
    # Check TTS: http_get("http://localhost:4123/docs")
    # Check voice sample: Path("profiles/voice-sample.wav").exists()
```

The full implementation should:
1. Import `run_checks` from `agents.health_monitor` and call it with `auto_fix=auto_fix`
2. Extract health score from the report (e.g., `f"{report.healthy_count}/{report.total_checks}"`)
3. Check cockpit API reachability via `http_get("http://localhost:8050/health")`
4. Check cockpit web reachability via `http_get("http://localhost:5173")`
5. If `require_tts`: check Chatterbox at `http://localhost:4123/docs` and voice sample at `PROFILES_DIR / "voice-sample.wav"`
6. Collect issues (critical = stops demo) and warnings (informational)
7. Return `ReadinessResult` with `ready=True` only if zero critical issues

Use `agents.health_monitor.http_get` for HTTP checks (it returns response text or empty string on failure) — look at how `introspect.py` and `health_monitor.py` use it.

**Tests (test_demo_readiness.py):**

- `test_readiness_all_healthy` — mock run_checks returning full health, mock http_get succeeding → ready=True
- `test_readiness_health_failures` — mock run_checks with failures → ready=False, issues populated
- `test_readiness_cockpit_down` — mock http_get returning empty for cockpit → ready=False
- `test_readiness_tts_not_required` — require_tts=False, TTS down → still ready=True
- `test_readiness_tts_required_but_down` — require_tts=True, TTS down → ready=False

Mock `agents.health_monitor.run_checks` and `agents.health_monitor.http_get` via `@patch`. Create minimal `HealthReport` or mock objects with the needed attributes.

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo_readiness.py -v`

---

## Task 4: Subject matter research stage

**Files:**
- Create: `agents/demo_pipeline/research.py`
- Create: `tests/test_demo_research.py`

**agents/demo_pipeline/research.py:**

Gathers rich, audience-filtered context from multiple live sources. Returns a structured context document string.

Key function:
```python
async def gather_research(
    scope: str,
    audience: str,
    on_progress: callable | None = None,
) -> str:
    """Gather audience-filtered research context for demo planning.

    Sources (audience-dependent):
    - Component registry (always)
    - Health monitor summary (always)
    - Introspect manifest (peers, leadership)
    - Langfuse metrics (peers, leadership)
    - Qdrant collection stats (peers)
    - CLAUDE.md full text (peers, leadership)
    - Operator profile facts (family)
    - Web research via Tavily (leadership, peers — for industry context)

    Returns a formatted context document string.
    """
```

**Source gathering functions** (private, one per source):

1. `_gather_component_registry() -> str` — reads `profiles/component-registry.yaml`, formats as summary
2. `_gather_health_summary() -> str` — calls `run_checks()` from health_monitor, formats score + key findings
3. `_gather_introspect() -> str` — calls `generate_manifest()` from introspect, formats containers + timers + collections
4. `_gather_langfuse_metrics(hours: int = 168) -> str` — uses `langfuse_get` from `shared/langfuse_client` to get traces and generations from last week, formats model usage + costs + trace names
5. `_gather_qdrant_stats() -> str` — uses `get_qdrant()` from `shared/config` to list collections and point counts
6. `_gather_system_docs() -> str` — reads CLAUDE.md (full, not truncated) from hapaxromana repo
7. `_gather_profile_facts(scope: str) -> str` — semantic search of `profile-facts` collection in Qdrant for facts relevant to the demo scope
8. `_gather_web_research(scope: str, audience: str) -> str` — Tavily web search for industry context relevant to the scope (e.g., "LLM observability best practices" for a Langfuse demo to leadership). Use `mcp__tavily__tavily_search` or direct httpx call to Tavily API.

**Audience filtering matrix** (which sources to call):

```python
AUDIENCE_SOURCES: dict[str, list[str]] = {
    "family": ["component_registry", "health_summary", "profile_facts"],
    "team-member": ["component_registry", "health_summary", "introspect_partial", "system_docs_summary"],
    "leadership": ["component_registry", "health_summary", "introspect", "langfuse_metrics", "system_docs", "web_research"],
    "technical-peer": ["component_registry", "health_summary", "introspect", "langfuse_metrics", "qdrant_stats", "system_docs", "web_research"],
}
```

Each `_gather_*` function should catch exceptions and return `""` on failure (research is best-effort — a failed Langfuse query shouldn't kill the demo).

The final context document is formatted with clear section headers:
```
## System Components
[from component registry]

## Current Health
[from health monitor]

## Infrastructure State
[from introspect]
...
```

**Tests (test_demo_research.py):**

- `test_gather_research_family` — mock all sources, verify only family-appropriate sources called
- `test_gather_research_leadership` — verify web_research and langfuse called
- `test_gather_research_source_failure_graceful` — mock one source raising exception → still returns partial context
- `test_gather_component_registry` — verify reads YAML, returns formatted string
- `test_audience_filtering` — verify AUDIENCE_SOURCES keys match persona archetypes
- `test_context_document_has_sections` — verify output has section headers

For web research tests, mock the Tavily call. For Langfuse/Qdrant, mock the clients.

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo_research.py -v`

---

## Task 5: Self-critique and revision loop

**Files:**
- Create: `agents/demo_pipeline/critique.py`
- Create: `tests/test_demo_critique.py`

**agents/demo_pipeline/critique.py:**

A Pydantic AI agent that evaluates a DemoScript against 8 quality dimensions and returns a `DemoQualityReport`. If issues are found, it revises the script and re-evaluates. Max 3 iterations.

```python
"""Self-critique and revision loop for demo script quality."""
from __future__ import annotations

import logging
from pydantic_ai import Agent
from agents.demo_models import DemoScript, DemoQualityReport
from shared.config import get_model

log = logging.getLogger(__name__)

MAX_ITERATIONS = 3

QUALITY_DIMENSIONS = [
    "narrative_coherence",    # Follows framework? Logical arc?
    "audience_calibration",   # Vocabulary appropriate? Respects show/skip?
    "content_adequacy",       # Enough substance? Each scene justified?
    "duration_feasibility",   # Word count × speech rate ≈ target?
    "style_compliance",       # Matches style guide? No corporatisms?
    "factual_grounding",      # Claims match research context?
    "visual_appropriateness", # Right mix of screenshots/diagrams/charts?
    "key_points_quality",     # Bullets substantive, not vague?
]
```

Two Pydantic AI agents:

1. **Critique agent** — takes script + context, outputs `DemoQualityReport`
   ```python
   critique_agent = Agent(
       get_model("balanced"),
       system_prompt="You are a presentation quality reviewer...",
       output_type=DemoQualityReport,
   )
   ```

2. **Revision agent** — takes script + quality report + context, outputs revised `DemoScript`
   ```python
   revision_agent = Agent(
       get_model("balanced"),
       system_prompt="You are revising a demo script based on quality feedback...",
       output_type=DemoScript,
   )
   ```

Main function:
```python
async def critique_and_revise(
    script: DemoScript,
    research_context: str,
    style_guide: dict,
    framework: dict,
    target_seconds: int,
    on_progress: callable | None = None,
) -> tuple[DemoScript, DemoQualityReport]:
    """Evaluate script quality and revise if needed. Returns (final_script, final_report)."""
```

Loop logic:
- Evaluate → if 0 Critical AND ≤1 Important → return
- Otherwise → revise → re-evaluate
- After MAX_ITERATIONS → return best version with warning

The critique prompt must include: the style guide, research context, narrative framework name, duration target, and the full script JSON. The prompt should enumerate each dimension with specific questions to answer.

The revision prompt must include: the original script, the critique report, and instructions to fix only the identified issues (not rewrite from scratch).

**Tests (test_demo_critique.py):**

- `test_critique_all_pass` — mock critique_agent returning all-pass report → returns script unchanged
- `test_critique_triggers_revision` — mock critique returning critical issue → mock revision → verify revised script returned
- `test_max_iterations_reached` — mock critique always failing → verify stops at MAX_ITERATIONS
- `test_critique_prompt_includes_dimensions` — verify the critique prompt mentions all 8 dimensions
- `test_revision_preserves_scene_count` — mock revision that keeps same scene count → verify no scenes lost

Mock the Pydantic AI agents using `@patch` on the `agent.run()` method. Create mock `RunResult` objects with `.output` attributes.

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo_critique.py -v`

---

## Task 6: Visual generation — D2 diagrams + Matplotlib charts

**Files:**
- Create: `agents/demo_pipeline/diagrams.py`
- Create: `agents/demo_pipeline/charts.py`
- Create: `profiles/gruvbox.mplstyle`
- Create: `tests/test_demo_diagrams.py`
- Create: `tests/test_demo_charts.py`
- Modify: `pyproject.toml` — add `"matplotlib>=3.9"`

### 6a: D2 Diagrams (`diagrams.py`)

```python
"""D2 architecture diagram generation with Gruvbox theme."""
from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

# Gruvbox dark theme for D2
GRUVBOX_D2_THEME = """
vars: {
  d2-config: {
    theme-id: 200
    dark-theme-id: 200
    layout-engine: elk
    pad: 50
  }
}

style: {
  fill: "#282828"
  stroke: "#ebdbb2"
  font-color: "#ebdbb2"
}

classes: {
  service: {
    style: {
      fill: "#3c3836"
      stroke: "#fe8019"
      font-color: "#ebdbb2"
      border-radius: 8
    }
  }
  highlight: {
    style: {
      fill: "#3c3836"
      stroke: "#fabd2f"
      font-color: "#fabd2f"
      border-radius: 8
    }
  }
}
"""


def is_d2_available() -> bool:
    """Check if D2 CLI is installed."""
    return shutil.which("d2") is not None


def render_d2(d2_source: str, output_path: Path, size: tuple[int, int] = (1920, 1080)) -> Path:
    """Render D2 source to PNG. Returns output_path.

    Prepends Gruvbox theme variables to the source.
    Falls back to generating a simple title card if D2 is not installed.
    """
```

If D2 is not available, fall back to generating a Pillow image with the diagram title text (reuse `_get_font` and colors from `title_cards.py`). This ensures the pipeline never fails just because D2 isn't installed.

D2 rendering: write source to temp `.d2` file, run `d2 --theme 200 --dark-theme 200 -s --pad 50 input.d2 output.png`, check return code.

### 6b: Matplotlib Charts (`charts.py`)

```python
"""Gruvbox-themed data visualization for demos."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

MPLSTYLE_PATH = Path(__file__).resolve().parent.parent.parent / "profiles" / "gruvbox.mplstyle"


def render_chart(chart_spec: str, output_path: Path, size: tuple[int, int] = (1920, 1080)) -> Path:
    """Render a chart from a JSON specification string.

    chart_spec is a JSON string with:
    {
        "type": "bar" | "line" | "gauge",
        "title": str,
        "data": {...},   # type-specific data
        "xlabel": str,
        "ylabel": str,
    }

    Returns output_path.
    """
```

Chart types:
- **bar** — `data: {"labels": [...], "values": [...], "colors": [...] | None}`
- **line** — `data: {"x": [...], "y": [...], "label": str}`
- **gauge** — `data: {"value": float, "max": float, "label": str}` — semicircle gauge

All charts use the Gruvbox mplstyle and render at the specified size.

### 6c: Gruvbox mplstyle (`profiles/gruvbox.mplstyle`)

```
# Gruvbox Dark theme for Matplotlib
# Used by demo pipeline charts

# Figure
figure.facecolor: "#282828"
figure.edgecolor: "#282828"

# Axes
axes.facecolor: "#282828"
axes.edgecolor: "#ebdbb2"
axes.labelcolor: "#ebdbb2"
axes.titlesize: 20
axes.labelsize: 14
axes.prop_cycle: cycler('color', ['#fe8019', '#fabd2f', '#b8bb26', '#83a598', '#d3869b', '#8ec07c', '#fb4934'])

# Text
text.color: "#ebdbb2"

# Ticks
xtick.color: "#a89984"
ytick.color: "#a89984"
xtick.labelsize: 12
ytick.labelsize: 12

# Grid
grid.color: "#3c3836"
grid.linewidth: 0.5
axes.grid: True

# Legend
legend.facecolor: "#3c3836"
legend.edgecolor: "#3c3836"
legend.fontsize: 12

# Lines
lines.linewidth: 2.5

# Savefig
savefig.facecolor: "#282828"
savefig.edgecolor: "#282828"
savefig.dpi: 150
savefig.bbox: tight
savefig.pad_inches: 0.3
```

**Tests (test_demo_diagrams.py):**

- `test_is_d2_available` — just calls function, checks bool return
- `test_render_d2_fallback_no_d2` — mock `shutil.which` returning None → verify fallback image generated (PNG exists, nonzero size)
- `test_render_d2_with_d2_installed` — if D2 available, test with simple source `"A -> B"` → verify PNG output exists. Mark with `@pytest.mark.skipif(not is_d2_available(), reason="D2 not installed")`
- `test_gruvbox_theme_prepended` — verify the D2 source passed to subprocess includes theme variables

**Tests (test_demo_charts.py):**

- `test_render_bar_chart` — simple bar chart with 3 labels → verify PNG exists
- `test_render_line_chart` — simple line with 5 data points → verify PNG exists
- `test_render_gauge_chart` — gauge at 74/75 → verify PNG exists
- `test_gruvbox_style_applied` — verify matplotlib uses gruvbox.mplstyle (check figure facecolor after loading)
- `test_invalid_chart_type` — unknown type → raises ValueError

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo_diagrams.py tests/test_demo_charts.py -v`

---

## Task 7: Integration into demo.py pipeline

**Files:**
- Modify: `agents/demo.py` — insert new stages, rewrite build_planning_prompt, update system prompt
- Modify: `agents/demo_pipeline/screenshots.py` — handle visual_type routing (call diagrams/charts for non-screenshot scenes)
- Create: `tests/test_demo_quality_integration.py`

This is the integration task. Changes to `demo.py`:

### 7a: Rewrite `build_planning_prompt()`

Replace the current 25-line prompt with one that includes:
- The research context document (from Stage 1)
- The style guide + narrative framework + duration constraints (from `narrative.format_planning_context()`)
- The existing audience persona info
- Visual type guidance ("For each scene, choose the visual type: 'screenshot' for UI, 'diagram' for architecture, 'chart' for data. Include D2 source in diagram_spec for diagrams, or chart spec JSON for charts.")

### 7b: Rewrite system prompt

Replace the 3-sentence system prompt with one that emphasizes quality:
```python
system_prompt = (
    "You are an expert presentation planner producing demo scripts for a personal "
    "agent infrastructure system. You plan scenes with precise narration, "
    "audience-appropriate vocabulary, and deliberate visual choices. "
    "Follow the narrative framework provided. Respect the duration constraints exactly. "
    "Match the presenter's style guide. Ground every claim in the research context. "
    "Each scene must justify its inclusion."
)
```

### 7c: Insert new stages into `generate_demo()`

Insert between step 1 (parse request) and the current screenshot capture:

```python
    # 2. Parse duration
    target_seconds = parse_duration(duration, archetype)

    # 3. System readiness gate
    with tracer.start_as_current_span("demo.readiness"):
        from agents.demo_pipeline.readiness import check_readiness
        progress("Checking system readiness...")
        readiness = check_readiness(
            require_tts=(format == "video"),
            auto_fix=True,
            on_progress=progress,
        )
        if not readiness.ready:
            issues_str = "\n".join(f"  - {i}" for i in readiness.issues)
            raise RuntimeError(
                f"System not ready for demo. Issues:\n{issues_str}\n"
                f"Fix these issues and retry."
            )

    # 4. Subject research
    with tracer.start_as_current_span("demo.research"):
        from agents.demo_pipeline.research import gather_research
        progress("Researching subject matter...")
        research_context = await gather_research(
            scope=scope, audience=archetype, on_progress=progress,
        )

    # 5. Load narrative context
    from agents.demo_pipeline.narrative import (
        load_style_guide, select_framework,
        get_duration_constraints, format_planning_context,
    )
    style_guide = load_style_guide()
    framework = select_framework(archetype)
    duration_constraints = get_duration_constraints(target_seconds)
    planning_context = format_planning_context(style_guide, framework, duration_constraints, target_seconds)

    # 6. Plan demo (LLM) — using enriched prompt
    with tracer.start_as_current_span("demo.plan"):
        progress("Planning demo scenes...")
        prompt = build_planning_prompt(
            scope, archetype, persona, research_context, planning_context,
        )
        if extra_context:
            prompt += f"\n\nAdditional audience context: {extra_context}"
        result = await agent.run(prompt)
        script = result.output

    # 7. Self-critique & revision
    with tracer.start_as_current_span("demo.critique"):
        from agents.demo_pipeline.critique import critique_and_revise
        progress("Evaluating script quality...")
        script, quality_report = await critique_and_revise(
            script=script,
            research_context=research_context,
            style_guide=style_guide,
            framework=framework,
            target_seconds=target_seconds,
            on_progress=progress,
        )
        if not quality_report.overall_pass:
            progress(f"WARNING: Script quality check has {sum(1 for d in quality_report.dimensions if not d.passed)} issues remaining")
```

### 7d: Update visual generation

Modify the screenshot capture section to handle `visual_type`:

```python
    # 8. Generate visuals (screenshots + diagrams + charts)
    with tracer.start_as_current_span("demo.visuals"):
        progress("Generating visuals...")
        screenshot_specs = []
        diagram_scenes = []
        chart_scenes = []

        for i, scene in enumerate(script.scenes, 1):
            slug = re.sub(r"[^a-z0-9]+", "-", scene.title.lower()).strip("-")
            name = f"{i:02d}-{slug}"
            if scene.visual_type == "screenshot":
                screenshot_specs.append((name, scene.screenshot))
            elif scene.visual_type == "diagram":
                diagram_scenes.append((name, scene))
            elif scene.visual_type == "chart":
                chart_scenes.append((name, scene))

        # Screenshots via Playwright
        screenshot_paths = await capture_screenshots(
            screenshot_specs, demo_dir / "screenshots", on_progress=progress
        ) if screenshot_specs else []

        # Diagrams via D2
        if diagram_scenes:
            from agents.demo_pipeline.diagrams import render_d2
            for name, scene in diagram_scenes:
                path = demo_dir / "screenshots" / f"{name}.png"
                render_d2(scene.diagram_spec or "", path)
                screenshot_paths.append(path)

        # Charts via Matplotlib
        if chart_scenes:
            from agents.demo_pipeline.charts import render_chart
            for name, scene in chart_scenes:
                path = demo_dir / "screenshots" / f"{name}.png"
                render_chart(scene.diagram_spec or "{}", path)
                screenshot_paths.append(path)
```

Also update the `screenshot_map` construction to handle all visual types.

### 7e: Pass `duration` through from CLI

Add `duration` parameter to `generate_demo()` signature and pass it from CLI args.

### 7f: Update metadata

Add to metadata dict:
```python
"target_duration": target_seconds,
"quality_pass": quality_report.overall_pass,
"quality_iterations": len([d for d in quality_report.dimensions if not d.passed]),
"narrative_framework": framework["name"],
```

**Tests (test_demo_quality_integration.py):**

These are integration-level tests. Mock the LLM calls and external services:

- `test_parse_duration_integrated` — verify duration arg flows through to planning context
- `test_readiness_failure_stops_demo` — mock readiness returning not-ready → verify RuntimeError
- `test_planning_prompt_includes_research` — mock research, verify research context appears in prompt
- `test_planning_prompt_includes_style_guide` — verify style guide text in prompt
- `test_visual_type_routing` — create script with mixed visual types → verify diagram/chart render functions called
- `test_metadata_includes_quality_fields` — verify new metadata fields present

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo_quality_integration.py tests/test_demo_agent.py -v`

---

## Task 8: Install D2 + matplotlib dependency + smoke test

**Files:**
- Modify: `pyproject.toml` — add `"matplotlib>=3.9"`

**Steps:**

1. Add `"matplotlib>=3.9"` to pyproject.toml dependencies (alphabetically)
2. Install D2: `curl -fsSL https://d2lang.com/install.sh | sh -s --` (or check if available via package manager)
3. Run the full demo test suite: `uv run pytest tests/test_demo*.py -v`
4. Verify cockpit-web still builds: `cd <cockpit-web> && pnpm build`

**Run:** `cd <ai-agents> && uv run pytest tests/test_demo*.py -v`

---

## Verification

```bash
# All demo tests pass
cd <ai-agents> && uv run pytest tests/test_demo*.py -v

# Full test suite still passes
cd <ai-agents> && uv run pytest -x --timeout=30 2>&1 | tail -5

# Cockpit-web builds
cd <cockpit-web> && pnpm build

# D2 installed
d2 --version

# Manual smoke test (if services running):
# 1. Short demo: uv run python -m agents.demo "the dashboard for a non-technical friend" --duration 3m
# 2. Long demo: uv run python -m agents.demo "health monitoring for leadership" --duration 10m --format video
# 3. Check output: demo.html opens, has architecture diagrams, charts, proper narration
```
