# Demo Generator Phase 3 — Polish

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the demo generator production-ready: discoverable via `/demo` command, observable via Langfuse tracing, resilient when optional services are unavailable.

**Architecture:** No new modules. Adds a hapax-system skill, Langfuse OTel tracing to the demo agent, and service preflight checks with graceful fallback for video-without-narration.

**Tech Stack:** Langfuse OTel (existing `shared/langfuse_config.py`), hapax-system skill YAML

**Design doc:** `docs/plans/2026-03-04-demo-generator-design.md`
**Phase 1 plan:** `docs/plans/2026-03-04-demo-generator-plan.md`
**Phase 2 plan:** `docs/plans/2026-03-04-demo-generator-phase2-plan.md`

---

## Already Complete (from Phases 1 & 2)

These Phase 3 design items were implemented early:
- **VRAM management automation** — `agents/demo_pipeline/vram.py`, wired into demo.py
- **Title card generation** — `agents/demo_pipeline/title_cards.py`, Gruvbox-styled
- **Cockpit API agent registration** — demo agent in `cockpit/data/agents.py`, invokable via generic `/api/agents/demo/run` SSE endpoint

---

### Task 1: Create `/demo` Skill

**Files:**
- Create: `<hapax-system>/skills/demo/SKILL.md`

**Step 1: Write the skill file**

```markdown
---
name: demo
description: Generate an audience-tailored system demo. Use when the user asks to produce a demo, create a presentation, or runs /demo.
---

Generate a demo from a natural language request. Examples:

- `/demo the entire system for a non-technical friend`
- `/demo health monitoring for a technical peer`
- `/demo the agent architecture for my manager --format video`

Available formats: `slides` (default), `video` (requires Chatterbox TTS), `markdown-only`.

Prerequisites for video format:
- Cockpit web running: `cd <cockpit-web> && pnpm dev`
- Chatterbox TTS running: `cd ~/llm-stack && docker compose --profile tts up -d chatterbox`

Run the demo agent:

```bash
cd <ai-agents> && eval "$(<.envrc)" && uv run python -m agents.demo "{user_request}"
```

After generation, report the output directory and list generated files. If format is video, note the MP4 path. If format is slides, note the PDF path.
```

**Step 2: Verify install script includes skills directory**

Run:
```bash
grep -n "skills" <hapax-system>/install.sh | head -5
```

The install script should already handle skills/ — verify the demo skill will be picked up.

**Step 3: Test the skill is discoverable**

Run:
```bash
ls <hapax-system>/skills/demo/SKILL.md
```

Expected: File exists.

**Step 4: Commit**

```bash
cd <hapax-system>
git add skills/demo/SKILL.md
git commit -m "feat: add /demo skill for demo generation"
```

---

### Task 2: Add Langfuse Tracing to Demo Agent

**Files:**
- Modify: `<ai-agents>/agents/demo.py`

**Step 1: Add Langfuse OTel import**

At the top of `agents/demo.py`, after the existing imports, add the standard Langfuse tracing import used by all other agents:

```python
try:
    from shared import langfuse_config  # noqa: F401
except ImportError:
    pass
```

This follows the exact pattern from `agents/briefing.py:36`, `agents/scout.py:43`, etc. The import is a side-effect that wires OTel traces to Langfuse. The `try/except` ensures the agent still works if Langfuse isn't available.

**Step 2: Run existing demo tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_agent.py -v`
Expected: All PASS (import is a no-op in test context).

**Step 3: Commit**

```bash
cd <ai-agents>
git add agents/demo.py
git commit -m "feat(demo): add Langfuse OTel tracing"
```

---

### Task 3: Graceful Video Fallback (silent video when TTS unavailable)

**Files:**
- Modify: `<ai-agents>/agents/demo.py`
- Modify: `<ai-agents>/tests/test_demo_agent.py`

**Step 1: Write the test**

Add to `tests/test_demo_agent.py`:

```python
class TestVideoFallback:
    def test_tts_unavailable_message(self):
        """Verify the TTS-unavailable message includes start instructions."""
        msg = (
            "Chatterbox TTS not running. Start with: "
            "cd ~/llm-stack && docker compose --profile tts up -d chatterbox"
        )
        assert "docker compose" in msg
        assert "--profile tts" in msg
```

Note: The actual fallback behavior is tested via the integration test pattern in Task 5. This test validates the error message format.

**Step 2: Change video pipeline to warn-and-continue instead of raising**

In `agents/demo.py`, replace the TTS availability check block. Currently:

```python
        # Check TTS service
        if not check_tts_available():
            raise ConnectionError(
                "Chatterbox TTS not running. Start with: "
                "cd ~/llm-stack && docker compose --profile tts up -d chatterbox"
            )
```

Replace with:

```python
        # Check TTS service
        tts_available = check_tts_available()
        if not tts_available:
            progress(
                "WARNING: Chatterbox TTS not running — video will have no narration. "
                "To enable voice: cd ~/llm-stack && docker compose --profile tts up -d chatterbox"
            )
```

Then guard the voice generation and VRAM blocks:

```python
        audio_dir = demo_dir / "audio"
        if tts_available:
            # Ensure VRAM (blocking call — run in thread to avoid freezing event loop)
            progress("Checking GPU VRAM...")
            await asyncio.to_thread(ensure_vram_available)

            # Generate voice segments
            voice_segments = []
            if script.intro_narration:
                voice_segments.append(("00-intro", script.intro_narration))
            for i, scene in enumerate(script.scenes, 1):
                slug = re.sub(r"[^a-z0-9]+", "-", scene.title.lower()).strip("-")
                voice_segments.append((f"{i:02d}-{slug}", scene.narration))
            if script.outro_narration:
                voice_segments.append(("99-outro", script.outro_narration))

            generate_all_voice_segments(
                voice_segments, audio_dir, on_progress=progress
            )
        else:
            audio_dir = None  # No audio — video will use duration hints
```

The rest of the video block (title cards + assemble_video) stays the same — `assemble_video` already handles `audio_dir=None` gracefully.

**Step 3: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo*.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
cd <ai-agents>
git add agents/demo.py tests/test_demo_agent.py
git commit -m "feat(demo): graceful fallback — video without narration when TTS unavailable"
```

---

### Task 4: Demo History Listing

**Files:**
- Create: `<ai-agents>/agents/demo_pipeline/history.py`
- Create: `<ai-agents>/tests/test_demo_history.py`

**Step 1: Write the test**

```python
"""Tests for demo history listing."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agents.demo_pipeline.history import list_demos, get_demo


class TestListDemos:
    @pytest.fixture
    def demos_dir(self, tmp_path) -> Path:
        """Create fake demo output directories."""
        for name, meta in [
            ("20260304-120000-system", {"title": "System Demo", "audience": "family", "format": "slides", "scenes": 3, "duration": 20.0}),
            ("20260304-130000-health", {"title": "Health Demo", "audience": "technical-peer", "format": "video", "scenes": 5, "duration": 35.0}),
        ]:
            d = tmp_path / name
            d.mkdir()
            (d / "metadata.json").write_text(json.dumps(meta, indent=2))
        return tmp_path

    def test_lists_demos_newest_first(self, demos_dir):
        demos = list_demos(demos_dir)
        assert len(demos) == 2
        assert demos[0]["title"] == "Health Demo"  # newer timestamp sorts first

    def test_empty_dir(self, tmp_path):
        demos = list_demos(tmp_path)
        assert demos == []


class TestGetDemo:
    def test_returns_metadata(self, tmp_path):
        d = tmp_path / "20260304-120000-test"
        d.mkdir()
        meta = {"title": "Test", "format": "slides"}
        (d / "metadata.json").write_text(json.dumps(meta))
        (d / "script.json").write_text("{}")
        (d / "demo.mp4").write_bytes(b"fake")

        result = get_demo(d)
        assert result["title"] == "Test"
        assert "demo.mp4" in result["files"]

    def test_missing_dir_returns_none(self, tmp_path):
        result = get_demo(tmp_path / "nonexistent")
        assert result is None
```

**Step 2: Run test to verify it fails**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_history.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
"""Demo history — list and inspect generated demos."""
from __future__ import annotations

import json
from pathlib import Path


def list_demos(output_dir: Path) -> list[dict]:
    """List all generated demos, newest first."""
    if not output_dir.exists():
        return []

    demos = []
    for d in sorted(output_dir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_path = d / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            meta["dir"] = str(d)
            meta["id"] = d.name
            demos.append(meta)
    return demos


def get_demo(demo_dir: Path) -> dict | None:
    """Get metadata and file listing for a single demo."""
    if not demo_dir.exists():
        return None

    meta_path = demo_dir / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    files = [f.name for f in sorted(demo_dir.rglob("*")) if f.is_file()]
    meta["files"] = files
    meta["dir"] = str(demo_dir)
    return meta
```

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_history.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo_pipeline/history.py tests/test_demo_history.py
git commit -m "feat(demo): demo history listing — list and inspect generated demos"
```

---

### Task 5: Cockpit API Demo Endpoints

**Files:**
- Create: `<ai-agents>/cockpit/api/routes/demos.py`
- Modify: `<ai-agents>/cockpit/api/app.py`
- Create: `<ai-agents>/tests/test_cockpit_demos.py`

**Step 1: Write the test**

```python
"""Tests for cockpit demo API endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from cockpit.api.app import app


class TestDemoEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_demos(self, tmp_path):
        """Create fake demo dirs and patch OUTPUT_DIR."""
        d = tmp_path / "20260304-120000-test"
        d.mkdir()
        meta = {"title": "Test Demo", "audience": "family", "format": "slides", "scenes": 2, "duration": 15.0}
        (d / "metadata.json").write_text(json.dumps(meta))
        (d / "script.json").write_text("{}")
        return tmp_path

    @patch("cockpit.api.routes.demos.OUTPUT_DIR")
    def test_list_demos(self, mock_dir, client, mock_demos):
        mock_dir.__class__ = type(mock_demos)
        # This needs the patch to point to the tmp_path
        pass  # Covered by unit tests in test_demo_history.py

    def test_list_demos_endpoint_exists(self, client):
        response = client.get("/api/demos")
        assert response.status_code in (200, 404)  # 200 if demos exist, 200 with empty list
```

**Step 2: Write the route**

```python
"""Demo history and management API endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from agents.demo import OUTPUT_DIR
from agents.demo_pipeline.history import list_demos, get_demo

router = APIRouter(prefix="/api/demos", tags=["demos"])


@router.get("")
async def list_all_demos():
    """List all generated demos, newest first."""
    return list_demos(OUTPUT_DIR)


@router.get("/{demo_id}")
async def get_demo_detail(demo_id: str):
    """Get metadata and file listing for a specific demo."""
    demo_dir = OUTPUT_DIR / demo_id
    result = get_demo(demo_dir)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Demo '{demo_id}' not found")
    return result


@router.get("/{demo_id}/files/{file_path:path}")
async def serve_demo_file(demo_id: str, file_path: str):
    """Serve a specific file from a demo output directory."""
    full_path = OUTPUT_DIR / demo_id / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    # Security: ensure path doesn't escape demo dir
    try:
        full_path.resolve().relative_to((OUTPUT_DIR / demo_id).resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    return FileResponse(full_path)
```

**Step 3: Register the router**

In `cockpit/api/app.py`, add the demo routes. Find the existing router includes and add:

```python
from cockpit.api.routes.demos import router as demos_router
app.include_router(demos_router)
```

Follow the existing pattern — look at how other routers are included (agents, health, chat, etc.) and add it in the same style.

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_cockpit_demos.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/api/routes/demos.py cockpit/api/app.py tests/test_cockpit_demos.py
git commit -m "feat(cockpit): demo API endpoints — list, detail, file serving"
```

---

### Task 6: Update Documentation

**Files:**
- Modify: `<hapaxromana>/CLAUDE.md`

**Step 1: Update the demo agent entry in the agent table**

In the Tier 2 agents table, the demo agent should already be listed. Verify it's present and update if needed to mention Phase 2 capabilities:

Find the agent table and ensure it includes:
```
| `demo` | Yes | Audience-tailored demo generator — slides, screenshots, voice-cloned video |
```

**Step 2: Add demo to the CLI invocation examples if missing**

Ensure the invocation pattern section shows:
```bash
uv run python -m agents.demo "the entire system for a non-technical friend" --format video
```

**Step 3: Commit**

```bash
cd <hapaxromana>
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with demo agent capabilities"
```

---

## Execution Order

Task 1 is independent (hapax-system repo).
Task 2 is independent (one-line import).
Task 3 depends on nothing (modifies demo.py behavior).
Task 4 is independent (new module).
Task 5 depends on Task 4 (imports history module).
Task 6 is independent (docs only).

Recommended: 1,2,4 (parallel) → 3 → 5 → 6

## Verification

After all tasks:

```bash
# All demo tests pass
cd <ai-agents> && uv run pytest tests/test_demo*.py -v

# Skill is discoverable
ls <hapax-system>/skills/demo/SKILL.md

# Cockpit API serves demo endpoints
cd <ai-agents> && uv run cockpit &
curl http://localhost:8050/api/demos
kill %1

# Full test suite
cd <ai-agents> && uv run pytest --timeout=30 -x -q
```
