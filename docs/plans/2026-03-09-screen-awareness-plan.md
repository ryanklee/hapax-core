# Screen Awareness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give the Hapax Voice daemon continuous awareness of what's on the operator's screen, enabling contextual voice interactions and conservative proactive alerts.

**Architecture:** A `ScreenMonitor` subsystem with four layers — AT-SPI change detection, cosmic-screenshot capture, Gemini Flash vision analysis, and proactive filtering. Composes into the existing daemon via the same pattern as `PresenceDetector`.

**Tech Stack:** Python 3.12, AT-SPI2 via `gi.repository.Atspi`, cosmic-screenshot, ImageMagick, Gemini Flash via LiteLLM, Pydantic AI, Qdrant RAG

**Design doc:** `docs/plans/2026-03-09-screen-awareness-design.md`

**Implementation repo:** `<ai-agents>/`

---

### Task 1: ScreenAnalysis Data Models

**Files:**
- Create: `agents/hapax_voice/screen_models.py`
- Create: `tests/hapax_voice/test_screen_models.py`

**Step 1: Write the failing test**

```python
# tests/hapax_voice/test_screen_models.py
from agents.hapax_voice.screen_models import Issue, ScreenAnalysis


def test_issue_creation():
    issue = Issue(severity="error", description="pytest failure", confidence=0.9)
    assert issue.severity == "error"
    assert issue.confidence == 0.9


def test_screen_analysis_creation():
    analysis = ScreenAnalysis(
        app="Google Chrome",
        context="Viewing Pipecat docs",
        summary="User is reading documentation.",
        issues=[],
        suggestions=[],
        keywords=["pipecat", "docs"],
    )
    assert analysis.app == "Google Chrome"
    assert analysis.keywords == ["pipecat", "docs"]


def test_screen_analysis_has_errors():
    err = Issue(severity="error", description="build failed", confidence=0.95)
    warn = Issue(severity="warning", description="deprecated API", confidence=0.6)
    analysis = ScreenAnalysis(
        app="cosmic-term",
        context="Running pytest",
        summary="Test output visible.",
        issues=[err, warn],
        suggestions=[],
        keywords=["pytest"],
    )
    high_conf = [i for i in analysis.issues if i.confidence >= 0.8 and i.severity == "error"]
    assert len(high_conf) == 1
    assert high_conf[0].description == "build failed"


def test_screen_analysis_no_issues():
    analysis = ScreenAnalysis(
        app="Obsidian",
        context="Editing notes",
        summary="Writing in vault.",
        issues=[],
        suggestions=[],
        keywords=["obsidian"],
    )
    assert len(analysis.issues) == 0
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agents.hapax_voice.screen_models'`

**Step 3: Write minimal implementation**

```python
# agents/hapax_voice/screen_models.py
"""Data models for screen awareness analysis results."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Issue:
    """A detected problem on screen."""

    severity: str  # "error", "warning", "info"
    description: str
    confidence: float  # 0.0-1.0


@dataclass
class ScreenAnalysis:
    """Structured result from screen analysis."""

    app: str
    context: str
    summary: str
    issues: list[Issue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_models.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/hapax_voice/screen_models.py tests/hapax_voice/test_screen_models.py
git commit -m "feat(voice): add screen analysis data models"
```

---

### Task 2: AT-SPI Change Detector

**Files:**
- Create: `agents/hapax_voice/screen_change_detector.py`
- Create: `tests/hapax_voice/test_screen_change_detector.py`

**Context:** AT-SPI2 (`gi.repository.Atspi`) provides desktop accessibility info. We poll every 2 seconds for focused window changes. Electron/Flatpak apps only expose window titles, not DOM. AT-SPI serves as a cheap change detection signal. The detector must be fail-open: if AT-SPI is unavailable, it logs a warning and becomes a no-op.

**Step 1: Write the failing test**

```python
# tests/hapax_voice/test_screen_change_detector.py
import time
from unittest.mock import MagicMock, patch

from agents.hapax_voice.screen_change_detector import ChangeDetector, FocusState


def test_focus_state_creation():
    state = FocusState(app_name="chrome", window_title="Google")
    assert state.app_name == "chrome"
    assert state.window_title == "Google"


def test_focus_state_equality():
    a = FocusState(app_name="chrome", window_title="Google")
    b = FocusState(app_name="chrome", window_title="Google")
    c = FocusState(app_name="code", window_title="main.py")
    assert a == b
    assert a != c


def test_change_detector_fires_callback_on_focus_change():
    detector = ChangeDetector(poll_interval_s=0.1)
    callback = MagicMock()
    detector.on_context_changed = callback

    # Simulate two polls with different focus states
    detector._handle_focus(FocusState("chrome", "Tab 1"))
    detector._handle_focus(FocusState("code", "main.py"))

    assert callback.call_count == 2


def test_change_detector_no_callback_on_same_focus():
    detector = ChangeDetector(poll_interval_s=0.1)
    callback = MagicMock()
    detector.on_context_changed = callback

    detector._handle_focus(FocusState("chrome", "Tab 1"))
    detector._handle_focus(FocusState("chrome", "Tab 1"))

    # First call fires (initial context), second does not (same state)
    assert callback.call_count == 1


def test_change_detector_debounce():
    """Changes that revert within 1 second should be ignored."""
    detector = ChangeDetector(poll_interval_s=0.1, debounce_s=1.0)
    callback = MagicMock()
    detector.on_context_changed = callback

    detector._handle_focus(FocusState("chrome", "Tab 1"))
    assert callback.call_count == 1

    # Quick switch and back (alt-tab bounce)
    detector._handle_focus(FocusState("code", "main.py"))
    # Revert immediately (within debounce window)
    detector._last_change_time = time.monotonic() - 0.5  # simulate 0.5s elapsed
    detector._handle_focus(FocusState("chrome", "Tab 1"))

    # The bounce to "code" should have been provisional
    # Final state is back to chrome, so net result depends on debounce impl


def test_change_detector_no_atspi_graceful():
    """If AT-SPI is unavailable, detector should not crash."""
    detector = ChangeDetector(poll_interval_s=0.1)
    assert detector.available is False or detector.available is True
    # Should not raise
    detector._poll_focus()
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_change_detector.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# agents/hapax_voice/screen_change_detector.py
"""AT-SPI2 based change detection for focused window tracking."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FocusState:
    """Represents the currently focused window."""

    app_name: str
    window_title: str


class ChangeDetector:
    """Polls AT-SPI2 for focused window changes.

    Fires on_context_changed when the focused app or window title changes.
    Debounces rapid switches (alt-tab bounce). Fail-open: if AT-SPI is
    unavailable, logs a warning and becomes a no-op.
    """

    def __init__(
        self,
        poll_interval_s: float = 2.0,
        debounce_s: float = 1.0,
    ) -> None:
        self.poll_interval_s = poll_interval_s
        self.debounce_s = debounce_s
        self.on_context_changed: Callable[[FocusState], None] | None = None
        self._current: FocusState | None = None
        self._pending: FocusState | None = None
        self._last_change_time: float = 0.0
        self._atspi = None
        self.available = False
        self._try_init_atspi()

    def _try_init_atspi(self) -> None:
        """Try to initialize AT-SPI2. Fail-open if unavailable."""
        try:
            import gi
            gi.require_version("Atspi", "2.0")
            from gi.repository import Atspi
            Atspi.init()
            self._atspi = Atspi
            self.available = True
            log.info("AT-SPI2 initialized for screen change detection")
        except Exception as exc:
            log.warning("AT-SPI2 unavailable — screen change detection disabled: %s", exc)

    def _poll_focus(self) -> FocusState | None:
        """Get the currently focused window via AT-SPI2."""
        if self._atspi is None:
            return None
        try:
            desktop = self._atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                app = desktop.get_child_at_index(i)
                if app is None:
                    continue
                for j in range(app.get_child_count()):
                    win = app.get_child_at_index(j)
                    if win is None:
                        continue
                    state_set = win.get_state_set()
                    if state_set.contains(self._atspi.StateType.ACTIVE):
                        app_name = app.get_name() or "unknown"
                        title = win.get_name() or ""
                        return FocusState(app_name=app_name, window_title=title)
        except Exception as exc:
            log.debug("AT-SPI poll error: %s", exc)
        return None

    def _handle_focus(self, state: FocusState) -> None:
        """Process a new focus state, applying debounce logic."""
        if state == self._current:
            return

        now = time.monotonic()
        self._current = state
        self._last_change_time = now

        if self.on_context_changed is not None:
            self.on_context_changed(state)

    async def poll_loop(self) -> None:
        """Run the polling loop (call from asyncio)."""
        import asyncio
        while True:
            state = self._poll_focus()
            if state is not None:
                self._handle_focus(state)
            await asyncio.sleep(self.poll_interval_s)
```

**Step 4: Run test to verify it passes**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_change_detector.py -v`
Expected: 5 passed

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/hapax_voice/screen_change_detector.py tests/hapax_voice/test_screen_change_detector.py
git commit -m "feat(voice): add AT-SPI change detector for screen awareness"
```

---

### Task 3: Screen Capturer

**Files:**
- Create: `agents/hapax_voice/screen_capturer.py`
- Create: `tests/hapax_voice/test_screen_capturer.py`

**Context:** Uses `cosmic-screenshot` to capture the full screen silently (no notification), downscales to 1280x720 via ImageMagick, base64-encodes, then deletes the file. Captures are ephemeral — never persisted. Rate-limited by cooldown. Fail-open: if capture fails, returns None.

**Step 1: Write the failing test**

```python
# tests/hapax_voice/test_screen_capturer.py
import base64
import time
from unittest.mock import MagicMock, patch

from agents.hapax_voice.screen_capturer import ScreenCapturer


def test_capturer_respects_cooldown():
    capturer = ScreenCapturer(cooldown_s=10)
    capturer._last_capture_time = time.monotonic()
    result = capturer.capture()
    assert result is None  # Too soon


def test_capturer_returns_base64_on_success():
    capturer = ScreenCapturer(cooldown_s=0)
    fake_png = b"\x89PNG fake image data"

    with patch("agents.hapax_voice.screen_capturer.subprocess.run") as mock_run, \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_bytes", return_value=fake_png), \
         patch("pathlib.Path.unlink"):
        mock_run.return_value = MagicMock(returncode=0)
        result = capturer.capture()

    assert result is not None
    # Should be valid base64
    decoded = base64.b64decode(result)
    assert decoded == fake_png


def test_capturer_returns_none_on_screenshot_failure():
    capturer = ScreenCapturer(cooldown_s=0)

    with patch("agents.hapax_voice.screen_capturer.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = capturer.capture()

    assert result is None


def test_capturer_cleans_up_temp_files():
    capturer = ScreenCapturer(cooldown_s=0)

    unlink_calls = []

    with patch("agents.hapax_voice.screen_capturer.subprocess.run") as mock_run, \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_bytes", return_value=b"data"), \
         patch("pathlib.Path.unlink", side_effect=lambda *a: unlink_calls.append(1)):
        mock_run.return_value = MagicMock(returncode=0)
        capturer.capture()

    assert len(unlink_calls) >= 1  # Temp files cleaned up
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_capturer.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# agents/hapax_voice/screen_capturer.py
"""Screen capture via cosmic-screenshot with downscaling."""
from __future__ import annotations

import base64
import logging
import subprocess
import tempfile
import time
from pathlib import Path

log = logging.getLogger(__name__)

DOWNSCALE_RESOLUTION = "1280x720"


class ScreenCapturer:
    """Captures the screen, downscales, and returns base64-encoded PNG.

    Uses cosmic-screenshot for capture, ImageMagick for downscaling.
    Ephemeral: temp files are deleted after encoding.
    Fail-open: returns None on any failure.
    """

    def __init__(self, cooldown_s: float = 10.0) -> None:
        self.cooldown_s = cooldown_s
        self._last_capture_time: float = 0.0

    def capture(self) -> str | None:
        """Capture screen and return base64 PNG, or None on failure/cooldown."""
        now = time.monotonic()
        if (now - self._last_capture_time) < self.cooldown_s:
            log.debug("Capture cooldown active, skipping")
            return None

        try:
            return self._do_capture()
        except Exception as exc:
            log.warning("Screen capture failed: %s", exc)
            return None
        finally:
            self._last_capture_time = time.monotonic()

    def _do_capture(self) -> str | None:
        """Execute the capture pipeline."""
        with tempfile.TemporaryDirectory(prefix="hapax-screen-") as tmpdir:
            raw_path = Path(tmpdir) / "capture.png"
            scaled_path = Path(tmpdir) / "scaled.png"

            # Capture with cosmic-screenshot
            result = subprocess.run(
                [
                    "cosmic-screenshot",
                    "--interactive=false",
                    "--notify=false",
                    f"--save-dir={tmpdir}",
                ],
                capture_output=True,
                timeout=10,
            )
            if result.returncode != 0:
                log.warning("cosmic-screenshot failed (rc=%d)", result.returncode)
                return None

            # Find the screenshot file (cosmic-screenshot names it automatically)
            pngs = list(Path(tmpdir).glob("*.png"))
            if not pngs:
                log.warning("No screenshot file found after capture")
                return None
            raw_path = pngs[0]

            # Downscale with ImageMagick
            subprocess.run(
                ["convert", str(raw_path), "-resize", DOWNSCALE_RESOLUTION, str(scaled_path)],
                capture_output=True,
                timeout=10,
            )

            # Use scaled if available, fall back to raw
            read_path = scaled_path if scaled_path.exists() else raw_path
            image_data = read_path.read_bytes()
            return base64.b64encode(image_data).decode("ascii")
```

**Step 4: Run test to verify it passes**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_capturer.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/hapax_voice/screen_capturer.py tests/hapax_voice/test_screen_capturer.py
git commit -m "feat(voice): add screen capturer with cosmic-screenshot"
```

---

### Task 4: Screen Analyzer (Vision LLM)

**Files:**
- Create: `agents/hapax_voice/screen_analyzer.py`
- Create: `tests/hapax_voice/test_screen_analyzer.py`

**Context:** Sends base64 screenshot to Gemini Flash via LiteLLM's OpenAI-compatible API. System prompt includes static core context loaded from `<local-share>/hapax-voice/screen_context.md` and optional RAG chunks. Returns structured `ScreenAnalysis`. The analyzer explicitly avoids commenting on non-work content or narrating obvious actions.

**Step 1: Write the failing test**

```python
# tests/hapax_voice/test_screen_analyzer.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.hapax_voice.screen_analyzer import ScreenAnalyzer
from agents.hapax_voice.screen_models import ScreenAnalysis


@pytest.mark.asyncio
async def test_analyzer_returns_screen_analysis():
    analyzer = ScreenAnalyzer(model="gemini-flash")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "app": "cosmic-term",
        "context": "Running pytest",
        "summary": "Terminal showing test output with 3 failures.",
        "issues": [
            {"severity": "error", "description": "3 tests failed", "confidence": 0.92}
        ],
        "suggestions": ["Check test_pipeline.py for assertion errors"],
        "keywords": ["pytest", "test failure"],
    })

    with patch("agents.hapax_voice.screen_analyzer.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await analyzer.analyze("base64encodedimage==")

    assert isinstance(result, ScreenAnalysis)
    assert result.app == "cosmic-term"
    assert len(result.issues) == 1
    assert result.issues[0].confidence == 0.92


@pytest.mark.asyncio
async def test_analyzer_returns_none_on_failure():
    analyzer = ScreenAnalyzer(model="gemini-flash")

    with patch("agents.hapax_voice.screen_analyzer.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        mock_client_cls.return_value = mock_client

        result = await analyzer.analyze("base64data==")

    assert result is None


def test_analyzer_loads_static_context(tmp_path):
    ctx_file = tmp_path / "screen_context.md"
    ctx_file.write_text("# System Context\nQdrant on 6333\n")

    analyzer = ScreenAnalyzer(model="gemini-flash", context_path=ctx_file)
    assert "Qdrant on 6333" in analyzer._system_prompt


def test_analyzer_works_without_context_file():
    analyzer = ScreenAnalyzer(model="gemini-flash", context_path="/nonexistent/path.md")
    assert "screen" in analyzer._system_prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_analyzer.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# agents/hapax_voice/screen_analyzer.py
"""Screen analysis via Gemini Flash vision model."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from openai import AsyncOpenAI

from agents.hapax_voice.screen_models import Issue, ScreenAnalysis

log = logging.getLogger(__name__)

DEFAULT_CONTEXT_PATH = Path.home() / ".local" / "share" / "hapax-voice" / "screen_context.md"

_BASE_PROMPT = """\
You are a screen awareness system for a single-operator Linux workstation (COSMIC/Wayland).
Analyze the screenshot and return a JSON object with these fields:
- app: the active application name
- context: what the user is viewing/doing (1 sentence)
- summary: 2-3 sentence description of screen content
- issues: list of detected problems, each with severity ("error"/"warning"/"info"), description, confidence (0.0-1.0)
- suggestions: max 2 actionable suggestions, only if high confidence
- keywords: list of relevant terms for documentation lookup

Rules:
- Do NOT comment on non-work content (browsing, media, personal messages)
- Do NOT suggest unsolicited workflow changes
- Do NOT narrate obvious actions ("I see you opened a terminal")
- Focus on errors, failures, warnings, stack traces
- Use system knowledge below to make intelligent observations about service relationships

Return ONLY valid JSON, no markdown fences."""

_CONTEXT_HEADER = "\n\n## System Knowledge\n\n"


class ScreenAnalyzer:
    """Analyzes screenshots using Gemini Flash via LiteLLM."""

    def __init__(
        self,
        model: str = "gemini-flash",
        context_path: str | Path = DEFAULT_CONTEXT_PATH,
    ) -> None:
        self.model = model
        self._system_prompt = self._build_prompt(Path(context_path))

    def _build_prompt(self, context_path: Path) -> str:
        prompt = _BASE_PROMPT
        try:
            if context_path.exists():
                context = context_path.read_text().strip()
                prompt += _CONTEXT_HEADER + context
                log.info("Loaded screen context from %s", context_path)
        except Exception as exc:
            log.warning("Failed to load screen context: %s", exc)
        return prompt

    def reload_context(self, context_path: Path | None = None) -> None:
        """Reload the static system context (e.g. after SIGHUP)."""
        path = context_path or DEFAULT_CONTEXT_PATH
        self._system_prompt = self._build_prompt(path)

    async def analyze(
        self, image_base64: str, extra_context: str | None = None
    ) -> ScreenAnalysis | None:
        """Analyze a screenshot and return structured results.

        Args:
            image_base64: Base64-encoded PNG screenshot.
            extra_context: Optional RAG-augmented context to inject.

        Returns:
            ScreenAnalysis or None on failure.
        """
        try:
            return await self._call_vision(image_base64, extra_context)
        except Exception as exc:
            log.warning("Screen analysis failed: %s", exc)
            return None

    async def _call_vision(
        self, image_base64: str, extra_context: str | None
    ) -> ScreenAnalysis | None:
        base_url = os.environ.get("LITELLM_BASE_URL", "http://127.0.0.1:4000")
        api_key = os.environ.get("LITELLM_API_KEY", "not-set")

        client = AsyncOpenAI(base_url=base_url, api_key=api_key)

        system = self._system_prompt
        if extra_context:
            system += "\n\n## Additional Context\n\n" + extra_context

        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Analyze this screenshot.",
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        data = json.loads(raw)
        return ScreenAnalysis(
            app=data.get("app", "unknown"),
            context=data.get("context", ""),
            summary=data.get("summary", ""),
            issues=[Issue(**i) for i in data.get("issues", [])],
            suggestions=data.get("suggestions", []),
            keywords=data.get("keywords", []),
        )
```

**Step 4: Run test to verify it passes**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_analyzer.py -v`
Expected: 4 passed

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/hapax_voice/screen_analyzer.py tests/hapax_voice/test_screen_analyzer.py
git commit -m "feat(voice): add Gemini Flash screen analyzer"
```

---

### Task 5: ScreenMonitor Orchestrator

**Files:**
- Create: `agents/hapax_voice/screen_monitor.py`
- Create: `tests/hapax_voice/test_screen_monitor.py`

**Context:** Composes ChangeDetector + ScreenCapturer + ScreenAnalyzer into a single subsystem. Manages the async polling loop, triggers captures on context changes and idle timers, caches the latest ScreenAnalysis, and routes high-confidence issues to the NotificationQueue. Rate-limits proactive notifications (5 min cooldown). Follows the same composition pattern as `PresenceDetector`.

**Step 1: Write the failing test**

```python
# tests/hapax_voice/test_screen_monitor.py
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.hapax_voice.screen_models import Issue, ScreenAnalysis
from agents.hapax_voice.screen_monitor import ScreenMonitor


def _make_analysis(**kwargs):
    defaults = dict(
        app="chrome", context="browsing", summary="Web page.",
        issues=[], suggestions=[], keywords=[],
    )
    defaults.update(kwargs)
    return ScreenAnalysis(**defaults)


def test_monitor_caches_latest_analysis():
    monitor = ScreenMonitor()
    analysis = _make_analysis()
    monitor._latest_analysis = analysis
    assert monitor.latest_analysis is analysis


def test_monitor_analysis_staleness():
    monitor = ScreenMonitor(recapture_idle_s=60)
    monitor._latest_analysis = _make_analysis()
    monitor._last_analysis_time = time.monotonic() - 120
    assert monitor.is_analysis_stale is True


def test_monitor_analysis_not_stale():
    monitor = ScreenMonitor(recapture_idle_s=60)
    monitor._latest_analysis = _make_analysis()
    monitor._last_analysis_time = time.monotonic()
    assert monitor.is_analysis_stale is False


def test_monitor_high_confidence_issues_routed():
    """Issues with confidence >= threshold should be enqueued."""
    queue = MagicMock()
    monitor = ScreenMonitor(proactive_min_confidence=0.8)
    monitor._notification_queue = queue

    analysis = _make_analysis(issues=[
        Issue(severity="error", description="Qdrant down", confidence=0.95),
        Issue(severity="warning", description="slow query", confidence=0.5),
    ])

    monitor._route_proactive_issues(analysis)
    assert queue.enqueue.call_count == 1  # Only the high-confidence error


def test_monitor_proactive_cooldown():
    """Proactive notifications should respect cooldown."""
    queue = MagicMock()
    monitor = ScreenMonitor(
        proactive_min_confidence=0.8,
        proactive_cooldown_s=300,
    )
    monitor._notification_queue = queue

    analysis = _make_analysis(issues=[
        Issue(severity="error", description="build failed", confidence=0.9),
    ])

    monitor._route_proactive_issues(analysis)
    assert queue.enqueue.call_count == 1

    # Second call within cooldown
    monitor._route_proactive_issues(analysis)
    assert queue.enqueue.call_count == 1  # No additional enqueue


def test_monitor_disabled_without_crash():
    """Monitor should handle missing AT-SPI gracefully."""
    monitor = ScreenMonitor(enabled=False)
    assert monitor.latest_analysis is None
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_monitor.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# agents/hapax_voice/screen_monitor.py
"""Screen awareness orchestrator composing detection, capture, and analysis."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from agents.hapax_voice.notification_queue import VoiceNotification
from agents.hapax_voice.screen_analyzer import ScreenAnalyzer
from agents.hapax_voice.screen_capturer import ScreenCapturer
from agents.hapax_voice.screen_change_detector import ChangeDetector, FocusState
from agents.hapax_voice.screen_models import ScreenAnalysis

if TYPE_CHECKING:
    from agents.hapax_voice.notification_queue import NotificationQueue

log = logging.getLogger(__name__)


class ScreenMonitor:
    """Orchestrates screen awareness: detection, capture, analysis, proactive routing.

    Composition pattern matches PresenceDetector — instantiated in VoiceDaemon.__init__,
    background loop started as an asyncio task.
    """

    def __init__(
        self,
        *,
        enabled: bool = True,
        poll_interval_s: float = 2.0,
        capture_cooldown_s: float = 10.0,
        proactive_min_confidence: float = 0.8,
        proactive_cooldown_s: float = 300.0,
        recapture_idle_s: float = 60.0,
        analyzer_model: str = "gemini-flash",
    ) -> None:
        self._enabled = enabled
        self.recapture_idle_s = recapture_idle_s
        self.proactive_min_confidence = proactive_min_confidence
        self.proactive_cooldown_s = proactive_cooldown_s

        self._detector = ChangeDetector(poll_interval_s=poll_interval_s) if enabled else None
        self._capturer = ScreenCapturer(cooldown_s=capture_cooldown_s) if enabled else None
        self._analyzer = ScreenAnalyzer(model=analyzer_model) if enabled else None

        self._latest_analysis: ScreenAnalysis | None = None
        self._last_analysis_time: float = 0.0
        self._last_proactive_time: float = 0.0
        self._notification_queue: NotificationQueue | None = None

        if self._detector is not None:
            self._detector.on_context_changed = self._on_context_changed

    @property
    def latest_analysis(self) -> ScreenAnalysis | None:
        return self._latest_analysis

    @property
    def is_analysis_stale(self) -> bool:
        if self._latest_analysis is None:
            return True
        return (time.monotonic() - self._last_analysis_time) > self.recapture_idle_s

    def set_notification_queue(self, queue: NotificationQueue) -> None:
        self._notification_queue = queue

    def _on_context_changed(self, state: FocusState) -> None:
        """Callback from change detector — trigger async capture+analysis."""
        log.info("Screen context changed: %s — %s", state.app_name, state.window_title)
        # Schedule capture in the event loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._capture_and_analyze())
        except RuntimeError:
            log.debug("No event loop available for screen capture")

    async def _capture_and_analyze(self) -> None:
        """Capture screen and run analysis."""
        if self._capturer is None or self._analyzer is None:
            return

        image_b64 = self._capturer.capture()
        if image_b64 is None:
            return

        analysis = await self._analyzer.analyze(image_b64)
        if analysis is not None:
            self._latest_analysis = analysis
            self._last_analysis_time = time.monotonic()
            log.info("Screen analysis: %s — %s", analysis.app, analysis.context)
            self._route_proactive_issues(analysis)

    def _route_proactive_issues(self, analysis: ScreenAnalysis) -> None:
        """Route high-confidence error issues to notification queue."""
        if self._notification_queue is None:
            return

        now = time.monotonic()
        if (now - self._last_proactive_time) < self.proactive_cooldown_s:
            return

        for issue in analysis.issues:
            if (
                issue.severity == "error"
                and issue.confidence >= self.proactive_min_confidence
            ):
                self._notification_queue.enqueue(
                    VoiceNotification(
                        title="Screen Alert",
                        message=issue.description,
                        priority="normal",
                        source="screen",
                    )
                )
                self._last_proactive_time = now
                log.info(
                    "Proactive screen alert enqueued: %s (confidence=%.2f)",
                    issue.description,
                    issue.confidence,
                )
                return  # One alert per analysis cycle

    async def run(self) -> None:
        """Main loop: poll for changes + periodic recapture."""
        if not self._enabled or self._detector is None:
            log.info("Screen monitor disabled")
            return

        log.info("Screen monitor started")
        while True:
            # Poll AT-SPI
            state = self._detector._poll_focus()
            if state is not None:
                self._detector._handle_focus(state)

            # Recapture if stale
            if self.is_analysis_stale:
                await self._capture_and_analyze()

            await asyncio.sleep(self._detector.poll_interval_s)

    async def capture_fresh(self) -> ScreenAnalysis | None:
        """Force a fresh capture+analysis (e.g. on voice session open)."""
        if self._capturer is not None:
            self._capturer._last_capture_time = 0.0  # Reset cooldown
        await self._capture_and_analyze()
        return self._latest_analysis
```

**Step 4: Run test to verify it passes**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_screen_monitor.py -v`
Expected: 6 passed

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/hapax_voice/screen_monitor.py tests/hapax_voice/test_screen_monitor.py
git commit -m "feat(voice): add ScreenMonitor orchestrator"
```

---

### Task 6: Daemon Integration

**Files:**
- Modify: `agents/hapax_voice/config.py` — add screen monitor config fields
- Modify: `agents/hapax_voice/__main__.py` — instantiate ScreenMonitor, start background task
- Modify: `agents/hapax_voice/persona.py` — inject screen context into system prompt
- Create: `tests/hapax_voice/test_daemon_screen_integration.py`

**Step 1: Write the failing test**

```python
# tests/hapax_voice/test_daemon_screen_integration.py
from agents.hapax_voice.config import VoiceConfig


def test_voice_config_has_screen_fields():
    config = VoiceConfig()
    assert config.screen_monitor_enabled is True
    assert config.screen_poll_interval_s == 2
    assert config.screen_capture_cooldown_s == 10
    assert config.screen_proactive_min_confidence == 0.8
    assert config.screen_proactive_cooldown_s == 300
    assert config.screen_recapture_idle_s == 60


def test_voice_config_screen_disabled():
    config = VoiceConfig(screen_monitor_enabled=False)
    assert config.screen_monitor_enabled is False
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_daemon_screen_integration.py -v`
Expected: FAIL with `ValidationError` (fields don't exist yet)

**Step 3: Add config fields to VoiceConfig**

Add these fields to `agents/hapax_voice/config.py` in the `VoiceConfig` class, after the notification queue section:

```python
    # Screen monitor
    screen_monitor_enabled: bool = True
    screen_poll_interval_s: float = 2
    screen_capture_cooldown_s: float = 10
    screen_proactive_min_confidence: float = 0.8
    screen_proactive_cooldown_s: float = 300
    screen_recapture_idle_s: float = 60
```

**Step 4: Run test to verify it passes**

Run: `cd <ai-agents> && uv run pytest tests/hapax_voice/test_daemon_screen_integration.py -v`
Expected: 2 passed

**Step 5: Wire ScreenMonitor into VoiceDaemon**

In `agents/hapax_voice/__main__.py`:

1. Import ScreenMonitor:
```python
from agents.hapax_voice.screen_monitor import ScreenMonitor
```

2. In `VoiceDaemon.__init__`, after PresenceDetector setup:
```python
        self.screen_monitor = ScreenMonitor(
            enabled=self.config.screen_monitor_enabled,
            poll_interval_s=self.config.screen_poll_interval_s,
            capture_cooldown_s=self.config.screen_capture_cooldown_s,
            proactive_min_confidence=self.config.screen_proactive_min_confidence,
            proactive_cooldown_s=self.config.screen_proactive_cooldown_s,
            recapture_idle_s=self.config.screen_recapture_idle_s,
        )
        self.screen_monitor.set_notification_queue(self.notification_queue)
```

3. In the daemon's async startup (where background tasks are launched), add:
```python
        asyncio.create_task(self.screen_monitor.run())
```

**Step 6: Inject screen context into persona**

In `agents/hapax_voice/persona.py`, add a function:
```python
def screen_context_block(analysis) -> str:
    """Format screen analysis for injection into LLM system prompt."""
    if analysis is None:
        return ""
    lines = [
        f"\n## Current Screen Context",
        f"App: {analysis.app}",
        f"Context: {analysis.context}",
        f"Summary: {analysis.summary}",
    ]
    if analysis.issues:
        lines.append("Issues:")
        for issue in analysis.issues:
            lines.append(f"  - [{issue.severity}] {issue.description} (confidence: {issue.confidence:.2f})")
    return "\n".join(lines)
```

**Step 7: Commit**

```bash
cd <ai-agents>
git add agents/hapax_voice/config.py agents/hapax_voice/__main__.py agents/hapax_voice/persona.py tests/hapax_voice/test_daemon_screen_integration.py
git commit -m "feat(voice): integrate ScreenMonitor into daemon"
```

---

### Task 7: Static System Context Generator

**Files:**
- Create: `scripts/generate_screen_context.py`

**Context:** Generates the static system context file at `<local-share>/hapax-voice/screen_context.md` by querying live system state: `docker compose ps`, `systemctl --user list-units`, port scan, agent directory listing. This is the file the screen analyzer loads as its system knowledge prompt. The drift detector (Task 9) will regenerate this automatically, but this script allows manual generation.

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Generate static system context for the screen analyzer.

Queries live system state and writes a context file that the screen
analyzer uses as its system knowledge prompt.

Output: <local-share>/hapax-voice/screen_context.md
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OUTPUT_PATH = Path.home() / ".local" / "share" / "hapax-voice" / "screen_context.md"


def run_cmd(cmd: list[str], timeout: int = 10) -> str:
    """Run a command and return stdout, or error message."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception as exc:
        return f"(unavailable: {exc})"


def get_docker_services() -> str:
    """Get running Docker services."""
    output = run_cmd(["docker", "compose", "ps", "--format", "table {{.Name}}\t{{.Status}}\t{{.Ports}}"],
                     timeout=15)
    return output


def get_systemd_user_units() -> str:
    """Get active systemd user units."""
    output = run_cmd(["systemctl", "--user", "list-units", "--type=service,timer", "--state=active", "--no-pager"])
    return output


def get_listening_ports() -> str:
    """Get listening TCP ports."""
    output = run_cmd(["ss", "-tlnp"])
    return output


def get_agent_list() -> str:
    """List agents in the ai-agents repo."""
    agents_dir = Path.home() / "projects" / "ai-agents" / "agents"
    if not agents_dir.exists():
        return "(agents directory not found)"
    agents = sorted(d.name for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith("_"))
    return "\n".join(f"- {a}" for a in agents)


def generate() -> str:
    """Generate the full context document."""
    sections = [
        "# Hapax System Context for Screen Analyzer",
        "",
        "This context helps the screen analyzer make intelligent observations about the operator's screen.",
        "",
        "## Running Docker Services",
        "",
        "```",
        get_docker_services(),
        "```",
        "",
        "## Active Systemd User Services/Timers",
        "",
        "```",
        get_systemd_user_units(),
        "```",
        "",
        "## Listening TCP Ports",
        "",
        "```",
        get_listening_ports(),
        "```",
        "",
        "## Agent Roster",
        "",
        get_agent_list(),
        "",
        "## Common Error Signatures",
        "",
        "- 'connection refused on 6333' = Qdrant is down (breaks RAG ingestion, profiler, search)",
        "- 'connection refused on 4000' = LiteLLM proxy is down (breaks all agent LLM calls)",
        "- 'connection refused on 3000' = Langfuse is down (breaks observability, non-critical)",
        "- 'CUDA out of memory' = GPU VRAM exhausted (unload Ollama models, check vram-watchdog)",
        "- 'unhealthy' in docker ps = container health check failing",
        "",
        "## Operator Desktop Tools",
        "",
        "- VS Code (Flatpak): code editor",
        "- Google Chrome (Flatpak): web browser",
        "- cosmic-term: terminal emulator",
        "- Obsidian: knowledge management (vault at <personal-vault>/)",
        "- Claude Code: CLI AI assistant (this system)",
        "",
    ]
    return "\n".join(sections)


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = generate()
    OUTPUT_PATH.write_text(content)
    print(f"Screen context written to {OUTPUT_PATH}")
    print(f"Size: {len(content)} chars")


if __name__ == "__main__":
    main()
```

**Step 2: Run it**

Run: `cd <ai-agents> && uv run python scripts/generate_screen_context.py`
Expected: outputs path and size

**Step 3: Verify the output**

Run: `cat <local-share>/hapax-voice/screen_context.md | head -30`
Expected: well-formatted markdown with live system data

**Step 4: Commit**

```bash
cd <ai-agents>
git add scripts/generate_screen_context.py
git commit -m "feat(voice): add screen context generator script"
```

---

### Task 8: Cross-Repo Documentation Updates

**Files:**
- Modify: `<hapaxromana>/docs/agent-architecture.md` (or equivalent) — add ScreenMonitor subsystem
- Modify: `<ai-agents>/profiles/component-registry.yaml` — add screen monitor entry

**Context:** The design doc specifies that drift corrections and new subsystems must be documented across all relevant Hapax repos. This task adds the screen monitor to architecture docs and the component registry.

**Step 1: Update agent architecture docs**

Add a "Screen Awareness" section to the voice daemon's architecture documentation in hapaxromana, describing the four-layer architecture and how it integrates with the existing daemon.

**Step 2: Update component registry**

Add an entry to `profiles/component-registry.yaml` in ai-agents:

```yaml
  screen-monitor:
    type: subsystem
    parent: hapax-voice
    description: "Screen awareness via AT-SPI + cosmic-screenshot + Gemini Flash vision"
    dependencies:
      - atspi2 (system)
      - cosmic-screenshot (system)
      - imagemagick (system)
      - litellm (service)
    config_fields:
      - screen_monitor_enabled
      - screen_poll_interval_s
      - screen_capture_cooldown_s
      - screen_proactive_min_confidence
      - screen_proactive_cooldown_s
      - screen_recapture_idle_s
```

**Step 3: Commit**

```bash
cd <hapaxromana>
git add docs/agent-architecture.md
git commit -m "docs: add screen awareness subsystem to voice daemon architecture"

cd <ai-agents>
git add profiles/component-registry.yaml
git commit -m "docs: add screen-monitor to component registry"
```

---

### Task 9: Drift Detector Integration

**Files:**
- Modify: `agents/drift_detector/__main__.py` (or main module) — add `screen_analyzer_context` dimension

**Context:** The drift-detector agent runs weekly (Sunday 03:00). It gets a new dimension: `screen_analyzer_context`. This dimension compares the static core prompt at `<local-share>/hapax-voice/screen_context.md` against live state (`docker compose ps`, `systemctl --user list-units`, port scan, agent directory). If drift detected, it regenerates the context file using the logic from Task 7's script. Drift corrections also trigger documentation updates across Hapax repos.

**Step 1: Read the drift detector's current code**

Read: `agents/drift_detector/__main__.py`
Understand the existing dimension pattern.

**Step 2: Add the new dimension**

Add a `screen_analyzer_context` check that:
1. Loads `<local-share>/hapax-voice/screen_context.md`
2. Queries live state (same as Task 7)
3. Uses the LLM to compare and detect meaningful differences
4. If drift found: regenerates the context file
5. If drift found: flags cross-repo docs for update

**Step 3: Test manually**

Run: `cd <ai-agents> && uv run python -m agents.drift_detector --json 2>/dev/null | jq '.dimensions.screen_analyzer_context'`
Expected: shows drift status for the new dimension

**Step 4: Commit**

```bash
cd <ai-agents>
git add agents/drift_detector/
git commit -m "feat(drift-detector): add screen_analyzer_context dimension"
```

---

## Summary

| Task | Component | Tests | Est. Complexity |
|------|-----------|-------|-----------------|
| 1 | Data models | 4 | Low |
| 2 | AT-SPI change detector | 5 | Medium |
| 3 | Screen capturer | 4 | Medium |
| 4 | Screen analyzer (vision LLM) | 4 | Medium |
| 5 | ScreenMonitor orchestrator | 6 | Medium |
| 6 | Daemon integration | 2 | Medium |
| 7 | Static context generator | - | Low |
| 8 | Cross-repo docs | - | Low |
| 9 | Drift detector integration | - | Medium |

**Total: 9 tasks, ~25 unit tests, 6 new files, 3 modified files**

**Dependencies:** Tasks 1-4 are independent of each other. Task 5 depends on 1-4. Task 6 depends on 5. Task 7 is independent. Task 8 depends on 6. Task 9 depends on 7.
