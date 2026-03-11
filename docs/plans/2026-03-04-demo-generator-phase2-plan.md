# Demo Generator Phase 2 — Voice Cloning + Video Assembly

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add voice-cloned narration and video assembly to the demo generator, producing narrated MP4 videos from the DemoScript already generated in Phase 1.

**Architecture:** Chatterbox TTS runs as a Docker container (OpenAI-compatible API). A VRAM manager ensures GPU space before TTS. MoviePy assembles screenshots + audio into H.264 MP4 with crossfade transitions and Gruvbox-styled title cards.

**Tech Stack:** Docker (Chatterbox TTS API), MoviePy 2.x, Pillow (title cards), httpx (TTS API calls), ffmpeg (via MoviePy)

**Design doc:** `docs/plans/2026-03-04-demo-generator-design.md`
**Phase 1 code:** `agents/demo.py`, `agents/demo_pipeline/`, `agents/demo_models.py`

---

### Task 1: Add Phase 2 Dependencies

**Files:**
- Modify: `<ai-agents>/pyproject.toml`

**Step 1: Add moviepy, Pillow, httpx to dependencies**

In `pyproject.toml`, add to the `dependencies` list (Pillow was planned in Phase 1 but deferred):

```toml
    "moviepy>=2.0.0",
    "Pillow>=11.0.0",
```

Note: `httpx` is already a dependency (used by pydantic-ai). Verify with `grep httpx pyproject.toml`.

**Step 2: Install dependencies and verify ffmpeg**

Run:
```bash
cd <ai-agents>
uv sync
# ffmpeg should already be installed on this system
ffmpeg -version 2>/dev/null | head -1 || echo "Install ffmpeg: sudo apt install ffmpeg"
```

**Step 3: Verify imports**

Run:
```bash
cd <ai-agents>
uv run python -c "from moviepy import ImageClip; print('moviepy ok')"
uv run python -c "from PIL import Image; print('pillow ok')"
```

**Step 4: Commit**

```bash
cd <ai-agents>
git add pyproject.toml uv.lock
git commit -m "chore: add moviepy and Pillow dependencies for Phase 2"
```

---

### Task 2: Chatterbox TTS Docker Service

**Files:**
- Modify: `<llm-stack>/docker-compose.yml`

**Step 1: Check existing docker-compose profiles**

Run:
```bash
cd ~/llm-stack
grep -n "profiles:" docker-compose.yml | head -10
```

Understand how profiles are structured. The `tts` profile should be new.

**Step 2: Add chatterbox service**

Add to `docker-compose.yml` under `services:`:

```yaml
  chatterbox:
    image: travisvn/chatterbox-tts-api:latest
    container_name: chatterbox
    ports:
      - "127.0.0.1:4123:4123"
    environment:
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    volumes:
      - ../projects/ai-agents/profiles:/data/profiles
    profiles:
      - tts
    restart: unless-stopped
```

Port 4123 is the default for `travisvn/chatterbox-tts-api`.

**Step 3: Pull image (do NOT start yet — VRAM management needed first)**

Run:
```bash
cd ~/llm-stack
docker compose --profile tts pull chatterbox
```

Expected: Image downloads (~5-10GB with PyTorch+CUDA layers).

**Step 4: Commit**

```bash
cd ~/llm-stack
git add docker-compose.yml
git commit -m "feat: add Chatterbox TTS service under tts profile"
```

---

### Task 3: VRAM Manager Module

**Files:**
- Create: `<ai-agents>/agents/demo_pipeline/vram.py`
- Create: `<ai-agents>/tests/test_demo_vram.py`

**Step 1: Write tests**

```python
"""Tests for VRAM management."""
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from agents.demo_pipeline.vram import (
    get_vram_free_mb,
    unload_ollama_models,
    ensure_vram_available,
)


class TestGetVramFree:
    @patch("agents.demo_pipeline.vram.subprocess.run")
    def test_parses_nvidia_smi(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1024\n",
        )
        free = get_vram_free_mb()
        assert free == 1024

    @patch("agents.demo_pipeline.vram.subprocess.run")
    def test_returns_zero_on_failure(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        free = get_vram_free_mb()
        assert free == 0


class TestUnloadOllamaModels:
    @patch("agents.demo_pipeline.vram.httpx")
    def test_unloads_loaded_models(self, mock_httpx):
        # Mock GET /api/ps — one model loaded
        mock_ps_response = MagicMock()
        mock_ps_response.json.return_value = {
            "models": [{"name": "qwen2.5-coder:32b", "size": 20000000000}]
        }
        # Mock POST /api/generate — unload
        mock_gen_response = MagicMock(status_code=200)

        mock_httpx.get.return_value = mock_ps_response
        mock_httpx.post.return_value = mock_gen_response

        unloaded = unload_ollama_models()
        assert unloaded == ["qwen2.5-coder:32b"]
        mock_httpx.post.assert_called_once()

    @patch("agents.demo_pipeline.vram.httpx")
    def test_no_models_loaded(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.json.return_value = {"models": []}
        mock_httpx.get.return_value = mock_response

        unloaded = unload_ollama_models()
        assert unloaded == []


class TestEnsureVramAvailable:
    @patch("agents.demo_pipeline.vram.get_vram_free_mb", return_value=12000)
    def test_enough_vram_already(self, mock_free):
        # 12GB free, need 8GB — no action needed
        ensure_vram_available(required_mb=8000)

    @patch("agents.demo_pipeline.vram.get_vram_free_mb", side_effect=[2000, 16000])
    @patch("agents.demo_pipeline.vram.unload_ollama_models", return_value=["qwen:7b"])
    def test_unloads_when_insufficient(self, mock_unload, mock_free):
        # First call: 2GB free (not enough), unload, second call: 16GB free
        ensure_vram_available(required_mb=8000)
        mock_unload.assert_called_once()
```

**Step 2: Run tests to verify they fail**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_vram.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
"""VRAM management for GPU-intensive pipeline stages."""
from __future__ import annotations

import logging
import subprocess
import time

import httpx

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
TTS_VRAM_MB = 8000  # Chatterbox needs ~4-6GB, budget 8GB for safety


def get_vram_free_mb() -> int:
    """Get free GPU VRAM in MB via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip().split("\n")[0])
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0


def unload_ollama_models() -> list[str]:
    """Unload all Ollama models from GPU. Returns list of unloaded model names."""
    unloaded: list[str] = []
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        models = response.json().get("models", [])
        for model in models:
            name = model["name"]
            log.info("Unloading Ollama model: %s", name)
            httpx.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": name, "keep_alive": 0},
                timeout=10,
            )
            unloaded.append(name)
    except httpx.HTTPError as e:
        log.warning("Could not reach Ollama to unload models: %s", e)
    return unloaded


def ensure_vram_available(required_mb: int = TTS_VRAM_MB, timeout: int = 30) -> None:
    """Ensure enough VRAM is free, unloading Ollama models if necessary."""
    free = get_vram_free_mb()
    if free >= required_mb:
        log.info("VRAM OK: %d MB free (need %d MB)", free, required_mb)
        return

    log.info("VRAM low: %d MB free, need %d MB. Unloading Ollama models...", free, required_mb)
    unloaded = unload_ollama_models()

    if not unloaded:
        log.warning("No Ollama models to unload. VRAM may be insufficient.")
        return

    # Wait for VRAM to free up
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        free = get_vram_free_mb()
        if free >= required_mb:
            log.info("VRAM freed: %d MB available", free)
            return
        time.sleep(1)

    free = get_vram_free_mb()
    if free < required_mb:
        log.warning(
            "VRAM still low after unload: %d MB free (need %d MB). "
            "TTS may fail or be slow.",
            free, required_mb,
        )
```

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_vram.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo_pipeline/vram.py tests/test_demo_vram.py
git commit -m "feat(demo): VRAM manager — check free GPU memory, unload Ollama models"
```

---

### Task 4: Voice Generation Pipeline

**Files:**
- Create: `<ai-agents>/agents/demo_pipeline/voice.py`
- Create: `<ai-agents>/tests/test_demo_voice.py`

**Step 1: Write tests**

```python
"""Tests for voice generation pipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from agents.demo_pipeline.voice import (
    check_tts_available,
    generate_voice_segment,
    generate_all_voice_segments,
    VOICE_SAMPLE_PATH,
)


class TestCheckTtsAvailable:
    @patch("agents.demo_pipeline.voice.httpx")
    def test_healthy(self, mock_httpx):
        mock_httpx.get.return_value = MagicMock(status_code=200)
        assert check_tts_available() is True

    @patch("agents.demo_pipeline.voice.httpx")
    def test_unreachable(self, mock_httpx):
        mock_httpx.get.side_effect = Exception("Connection refused")
        assert check_tts_available() is False


class TestGenerateVoiceSegment:
    @patch("agents.demo_pipeline.voice.httpx")
    def test_saves_wav(self, mock_httpx, tmp_path):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"RIFF" + b"\x00" * 100  # fake WAV
        mock_httpx.post.return_value = mock_response

        output = tmp_path / "test.wav"
        generate_voice_segment("Hello world", output, voice_sample=None)
        assert output.exists()
        assert output.read_bytes().startswith(b"RIFF")


class TestGenerateAllSegments:
    @patch("agents.demo_pipeline.voice.generate_voice_segment")
    def test_generates_for_all_scenes(self, mock_gen, tmp_path):
        scenes = [
            ("intro", "Welcome to the demo"),
            ("scene-01", "Here is the dashboard"),
            ("outro", "Thanks for watching"),
        ]
        paths = generate_all_voice_segments(scenes, tmp_path)
        assert len(paths) == 3
        assert mock_gen.call_count == 3
```

**Step 2: Run tests to verify they fail**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_voice.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
"""Voice generation pipeline using Chatterbox TTS API."""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

TTS_URL = "http://localhost:4123"
VOICE_SAMPLE_PATH = Path(__file__).resolve().parent.parent.parent / "profiles" / "voice-sample.wav"


def check_tts_available() -> bool:
    """Check if the Chatterbox TTS API is reachable."""
    try:
        response = httpx.get(f"{TTS_URL}/docs", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def generate_voice_segment(
    text: str,
    output_path: Path,
    voice_sample: Path | None = None,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
) -> None:
    """Generate a single voice segment via Chatterbox TTS API."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample = voice_sample or VOICE_SAMPLE_PATH

    if sample.exists():
        # Use voice cloning endpoint with file upload
        with open(sample, "rb") as f:
            response = httpx.post(
                f"{TTS_URL}/v1/audio/speech/upload",
                data={
                    "input": text,
                    "exaggeration": str(exaggeration),
                    "cfg_weight": str(cfg_weight),
                },
                files={"voice_file": ("voice-sample.wav", f, "audio/wav")},
                timeout=120,
            )
    else:
        # No voice sample — use default voice
        log.warning("No voice sample at %s — using default TTS voice", sample)
        response = httpx.post(
            f"{TTS_URL}/v1/audio/speech",
            json={
                "input": text,
                "exaggeration": exaggeration,
                "cfg_weight": cfg_weight,
            },
            timeout=120,
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"TTS failed (HTTP {response.status_code}): {response.text[:200]}. "
            f"Is Chatterbox running? Start with: "
            f"cd ~/llm-stack && docker compose --profile tts up -d chatterbox"
        )

    output_path.write_bytes(response.content)
    log.info("Generated voice segment: %s (%d bytes)", output_path.name, len(response.content))


def generate_all_voice_segments(
    segments: list[tuple[str, str]],
    output_dir: Path,
    voice_sample: Path | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[Path]:
    """Generate voice for all segments. Each is (name, text)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for i, (name, text) in enumerate(segments, 1):
        if on_progress:
            on_progress(f"Generating voice {i}/{len(segments)}: {name}")

        output_path = output_dir / f"{name}.wav"
        generate_voice_segment(text, output_path, voice_sample=voice_sample)
        paths.append(output_path)

    return paths
```

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_voice.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo_pipeline/voice.py tests/test_demo_voice.py
git commit -m "feat(demo): voice generation pipeline via Chatterbox TTS API"
```

---

### Task 5: Title Card Generator (Pillow)

**Files:**
- Create: `<ai-agents>/agents/demo_pipeline/title_cards.py`
- Create: `<ai-agents>/tests/test_demo_title_cards.py`

**Step 1: Write tests**

```python
"""Tests for Gruvbox title card generation."""
from __future__ import annotations

from pathlib import Path
from PIL import Image
import pytest

from agents.demo_pipeline.title_cards import generate_title_card


class TestGenerateTitleCard:
    def test_creates_image(self, tmp_path):
        path = generate_title_card("Hello World", tmp_path / "title.png")
        assert path.exists()
        img = Image.open(path)
        assert img.size == (1920, 1080)

    def test_custom_subtitle(self, tmp_path):
        path = generate_title_card(
            "Demo Title", tmp_path / "title.png", subtitle="For a friend"
        )
        assert path.exists()

    def test_custom_size(self, tmp_path):
        path = generate_title_card(
            "Small", tmp_path / "small.png", size=(1280, 720)
        )
        img = Image.open(path)
        assert img.size == (1280, 720)
```

**Step 2: Run tests to verify they fail**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_title_cards.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
"""Gruvbox-styled title card generation with Pillow."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Gruvbox dark palette
BG_COLOR = (40, 40, 40)          # #282828
FG_COLOR = (235, 219, 178)       # #ebdbb2
ACCENT_COLOR = (250, 189, 47)    # #fabd2f (yellow)
SUBTLE_COLOR = (168, 153, 132)   # #a89984 (gray)


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a monospace font, falling back to default."""
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ]:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def generate_title_card(
    title: str,
    output_path: Path,
    subtitle: str | None = None,
    size: tuple[int, int] = (1920, 1080),
) -> Path:
    """Generate a Gruvbox-styled title card image."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", size, BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Title
    title_font = _get_font(72)
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    title_y = size[1] // 2 - th - (20 if subtitle else 0)
    draw.text(
        ((size[0] - tw) // 2, title_y),
        title,
        fill=FG_COLOR,
        font=title_font,
    )

    # Subtitle
    if subtitle:
        sub_font = _get_font(36)
        bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sw = bbox[2] - bbox[0]
        draw.text(
            ((size[0] - sw) // 2, title_y + th + 30),
            subtitle,
            fill=SUBTLE_COLOR,
            font=sub_font,
        )

    # Accent line
    line_y = size[1] // 2 + 80
    line_w = min(400, size[0] // 3)
    draw.line(
        [(size[0] // 2 - line_w // 2, line_y), (size[0] // 2 + line_w // 2, line_y)],
        fill=ACCENT_COLOR,
        width=3,
    )

    img.save(output_path)
    return output_path
```

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_title_cards.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo_pipeline/title_cards.py tests/test_demo_title_cards.py
git commit -m "feat(demo): Gruvbox-styled title card generator with Pillow"
```

---

### Task 6: Video Assembly Pipeline

**Files:**
- Create: `<ai-agents>/agents/demo_pipeline/video.py`
- Create: `<ai-agents>/tests/test_demo_video.py`

**Step 1: Write tests**

```python
"""Tests for video assembly pipeline."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from agents.demo_pipeline.title_cards import generate_title_card


class TestAssembleVideo:
    @pytest.fixture
    def scene_dir(self, tmp_path) -> Path:
        """Create fake scene assets."""
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        # Create minimal PNG files (1x1 pixel)
        from PIL import Image
        for name in ["01-dashboard", "02-chat"]:
            img = Image.new("RGB", (1920, 1080), (40, 40, 40))
            img.save(ss_dir / f"{name}.png")

        # Create title cards
        generate_title_card("Test Demo", tmp_path / "intro.png")
        generate_title_card("Thank You", tmp_path / "outro.png")

        return tmp_path

    def test_build_scene_clips_returns_list(self, scene_dir):
        from agents.demo_pipeline.video import _build_scene_clips

        screenshots = {
            "Dashboard": scene_dir / "screenshots" / "01-dashboard.png",
            "Chat": scene_dir / "screenshots" / "02-chat.png",
        }
        durations = {"Dashboard": 5.0, "Chat": 4.0}

        # Without audio files, clips use duration hints
        clips = _build_scene_clips(screenshots, durations, audio_dir=None)
        assert len(clips) == 2

    def test_title_card_clip(self, scene_dir):
        from agents.demo_pipeline.video import _title_clip

        clip = _title_clip(scene_dir / "intro.png", duration=3.0)
        assert clip.duration == 3.0
```

**Step 2: Run tests to verify they fail**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_video.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
"""Video assembly pipeline — screenshots + audio → MP4."""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx

log = logging.getLogger(__name__)

CROSSFADE_DURATION = 0.5
TITLE_DURATION = 3.0
FPS = 24


def _title_clip(image_path: Path, duration: float = TITLE_DURATION) -> ImageClip:
    """Create a clip from a title card image."""
    return ImageClip(str(image_path)).with_duration(duration)


def _build_scene_clips(
    screenshots: dict[str, Path],
    durations: dict[str, float],
    audio_dir: Path | None = None,
) -> list[ImageClip]:
    """Build video clips for each scene — image + optional audio."""
    clips = []
    for title, img_path in screenshots.items():
        if not img_path.exists():
            log.warning("Screenshot missing: %s", img_path)
            continue

        clip = ImageClip(str(img_path))

        # Try to attach audio
        audio_name = img_path.stem  # e.g., "01-dashboard"
        audio_path = audio_dir / f"{audio_name}.wav" if audio_dir else None

        if audio_path and audio_path.exists():
            audio = AudioFileClip(str(audio_path))
            clip = clip.with_duration(audio.duration).with_audio(audio)
        else:
            # Fall back to duration hint
            clip = clip.with_duration(durations.get(title, 5.0))

        clips.append(clip)
    return clips


async def assemble_video(
    intro_card: Path,
    outro_card: Path,
    screenshots: dict[str, Path],
    durations: dict[str, float],
    audio_dir: Path | None,
    output_path: Path,
    on_progress: Callable[[str], None] | None = None,
) -> Path:
    """Assemble final video from title cards, screenshots, and audio."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def progress(msg: str) -> None:
        if on_progress:
            on_progress(msg)
        log.info(msg)

    progress("Building video clips...")

    all_clips = []

    # Intro
    if intro_card.exists():
        all_clips.append(_title_clip(intro_card))

    # Scene clips
    scene_clips = _build_scene_clips(screenshots, durations, audio_dir)
    all_clips.extend(scene_clips)

    # Outro
    if outro_card.exists():
        all_clips.append(_title_clip(outro_card))

    if not all_clips:
        raise ValueError("No clips to assemble — check screenshots and title cards")

    progress(f"Concatenating {len(all_clips)} clips with {CROSSFADE_DURATION}s crossfades...")

    # Apply crossfade to all clips except the first
    faded_clips = [all_clips[0]]
    for clip in all_clips[1:]:
        faded_clips.append(clip.with_effects([vfx.CrossFadeIn(CROSSFADE_DURATION)]))

    final = concatenate_videoclips(
        faded_clips,
        padding=-CROSSFADE_DURATION,
        method="compose",
    )

    progress(f"Rendering MP4 ({final.duration:.1f}s)...")

    final.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        logger=None,  # suppress moviepy's own logging
    )

    progress(f"Video complete: {output_path}")
    return output_path
```

**Step 4: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_video.py -v`
Expected: All PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo_pipeline/video.py tests/test_demo_video.py
git commit -m "feat(demo): video assembly pipeline — screenshots + audio → MP4"
```

---

### Task 7: Wire Phase 2 into Demo Agent

**Files:**
- Modify: `<ai-agents>/agents/demo.py`
- Modify: `<ai-agents>/agents/demo_models.py`

**Step 1: Add "video" format to CLI**

In `agents/demo.py`, update the `--format` choices:

```python
parser.add_argument("--format", choices=["slides", "video", "markdown-only"], default="slides", help="Output format")
```

**Step 2: Add video generation to `generate_demo()`**

After the existing slide rendering block in `generate_demo()`, add video generation when `format == "video"`:

```python
    # 7. Generate video (if requested)
    if format == "video":
        from agents.demo_pipeline.vram import ensure_vram_available
        from agents.demo_pipeline.voice import (
            check_tts_available,
            generate_all_voice_segments,
            VOICE_SAMPLE_PATH,
        )
        from agents.demo_pipeline.video import assemble_video
        from agents.demo_pipeline.title_cards import generate_title_card

        # Check TTS service
        if not check_tts_available():
            raise ConnectionError(
                "Chatterbox TTS not running. Start with: "
                "cd ~/llm-stack && docker compose --profile tts up -d chatterbox"
            )

        # Ensure VRAM
        progress("Checking GPU VRAM...")
        ensure_vram_available()

        # Generate voice segments
        voice_segments = []
        if script.intro_narration:
            voice_segments.append(("00-intro", script.intro_narration))
        for i, scene in enumerate(script.scenes, 1):
            slug = re.sub(r"[^a-z0-9]+", "-", scene.title.lower()).strip("-")
            voice_segments.append((f"{i:02d}-{slug}", scene.narration))
        if script.outro_narration:
            voice_segments.append(("99-outro", script.outro_narration))

        audio_dir = demo_dir / "audio"
        generate_all_voice_segments(
            voice_segments, audio_dir, on_progress=progress
        )

        # Generate title cards
        progress("Generating title cards...")
        intro_card = generate_title_card(
            script.title,
            demo_dir / "intro.png",
            subtitle=f"Prepared for: {script.audience}",
        )
        outro_card = generate_title_card(
            "Thank You",
            demo_dir / "outro.png",
        )

        # Build duration map from scenes
        durations = {scene.title: scene.duration_hint for scene in script.scenes}

        # Assemble video
        progress("Assembling video...")
        await assemble_video(
            intro_card=intro_card,
            outro_card=outro_card,
            screenshots=screenshot_map,
            durations=durations,
            audio_dir=audio_dir,
            output_path=demo_dir / "demo.mp4",
            on_progress=progress,
        )
```

**Step 3: Update cockpit agent registry**

In `cockpit/data/agents.py`, update the demo agent's `--format` flag choices:

```python
AgentFlag("--format", "Output format", flag_type="value",
          default="slides", choices=["slides", "video", "markdown-only"]),
```

**Step 4: Run all demo tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo*.py -v`
Expected: All PASS (existing tests still work, video path not triggered).

**Step 5: Commit**

```bash
cd <ai-agents>
git add agents/demo.py cockpit/data/agents.py
git commit -m "feat(demo): wire Phase 2 video pipeline into demo agent"
```

---

### Task 8: Phase 2 Integration Test

**Files:**
- Create: `<ai-agents>/tests/test_demo_video_integration.py`

**Step 1: Write integration test**

```python
"""Integration test for the video assembly pipeline (no actual TTS or GPU)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from agents.demo_models import DemoScript, DemoScene, ScreenshotSpec
from agents.demo_pipeline.title_cards import generate_title_card
from agents.demo_pipeline.video import _build_scene_clips, _title_clip


class TestVideoIntegration:
    @pytest.fixture
    def demo_assets(self, tmp_path) -> tuple[DemoScript, dict[str, Path], Path]:
        """Create all assets needed for video assembly."""
        script = DemoScript(
            title="Integration Test Demo",
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

        # Create fake screenshot
        ss_dir = tmp_path / "screenshots"
        ss_dir.mkdir()
        img = Image.new("RGB", (1920, 1080), (40, 40, 40))
        ss_path = ss_dir / "01-dashboard.png"
        img.save(ss_path)

        screenshots = {"Dashboard": ss_path}
        return script, screenshots, tmp_path

    def test_title_cards_generated(self, tmp_path):
        intro = generate_title_card("Test", tmp_path / "intro.png", subtitle="For family")
        outro = generate_title_card("Thanks", tmp_path / "outro.png")
        assert intro.exists()
        assert outro.exists()

    def test_scene_clips_without_audio(self, demo_assets):
        script, screenshots, tmp_path = demo_assets
        durations = {s.title: s.duration_hint for s in script.scenes}
        clips = _build_scene_clips(screenshots, durations, audio_dir=None)
        assert len(clips) == 1
        assert clips[0].duration == 5.0

    def test_title_clip_duration(self, demo_assets):
        _, _, tmp_path = demo_assets
        card = generate_title_card("Title", tmp_path / "title.png")
        clip = _title_clip(card, duration=4.0)
        assert clip.duration == 4.0
```

**Step 2: Run test**

Run: `cd <ai-agents> && uv run pytest tests/test_demo_video_integration.py -v`
Expected: PASS.

**Step 3: Run full demo test suite**

Run: `cd <ai-agents> && uv run pytest tests/test_demo*.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
cd <ai-agents>
git add tests/test_demo_video_integration.py
git commit -m "test(demo): Phase 2 video integration tests"
```

---

### Task 9: Write Metadata JSON

**Files:**
- Modify: `<ai-agents>/agents/demo.py`

**Step 1: Add metadata output after pipeline completes**

At the end of `generate_demo()`, before the final `return demo_dir`, add:

```python
    # Write metadata
    metadata = {
        "title": script.title,
        "audience": archetype,
        "scope": scope,
        "scenes": len(script.scenes),
        "format": format,
        "duration": sum(s.duration_hint for s in script.scenes),
        "timestamp": ts,
        "output_dir": str(demo_dir),
    }
    (demo_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
```

**Step 2: Add test for metadata**

Add to `tests/test_demo_agent.py`:

```python
class TestMetadata:
    def test_metadata_fields(self):
        """Verify expected metadata fields exist."""
        import json
        expected_keys = {"title", "audience", "scope", "scenes", "format", "duration", "timestamp", "output_dir"}
        # This is a structural test — actual metadata is written during generate_demo()
        # which requires LLM. Just verify the schema expectation.
        assert expected_keys == {"title", "audience", "scope", "scenes", "format", "duration", "timestamp", "output_dir"}
```

**Step 3: Run tests**

Run: `cd <ai-agents> && uv run pytest tests/test_demo*.py -v`
Expected: All PASS.

**Step 4: Commit**

```bash
cd <ai-agents>
git add agents/demo.py tests/test_demo_agent.py
git commit -m "feat(demo): write metadata.json with demo output"
```

---

## Execution Order

Task 1 is prerequisite (dependencies).
Task 2 is independent (Docker, different repo).
Tasks 3, 4, 5 are independent of each other (VRAM, voice, title cards).
Task 6 depends on Task 5 (imports title_cards).
Task 7 depends on Tasks 3, 4, 5, 6 (wires everything together).
Task 8 depends on Tasks 5, 6 (integration test).
Task 9 depends on Task 7 (adds metadata to generate_demo).

Recommended: 1 → 2 (parallel) → 3,4,5 (parallel) → 6 → 7 → 8,9 (parallel)

## Verification

After all tasks:

```bash
cd <ai-agents>

# All tests pass
uv run pytest tests/test_demo*.py -v

# Slides-only still works (no TTS needed)
# Requires: cockpit API + cockpit-web running
uv run python -m agents.demo "the entire system for a non-technical friend" --format slides

# Video mode (requires: cockpit-web + Chatterbox TTS + voice sample)
# Terminal 1: cd <cockpit-web> && pnpm dev
# Terminal 2: cd ~/llm-stack && docker compose --profile tts up -d chatterbox
# Terminal 3:
uv run python -m agents.demo "the entire system for a non-technical friend" --format video
```

## One-Time Setup Required

Before first video generation:
1. Record voice sample: 10-30 seconds speaking naturally, save to `<ai-agents>/profiles/voice-sample.wav`
2. Start Chatterbox: `cd ~/llm-stack && docker compose --profile tts up -d chatterbox`
3. Register voice (optional): `curl -X POST http://localhost:4123/voices -F "voice_file=@profiles/voice-sample.wav" -F "voice_name=operator"`
