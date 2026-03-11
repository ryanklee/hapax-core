# Workspace Vision System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dual-webcam visual awareness to the Hapax voice daemon, evolving screen-only awareness into full workspace awareness with presence detection, hardware monitoring, and activity mode detection.

**Architecture:** WebcamCapturer primitive captures frames from BRIO (operator-facing) and C920 (hardware-facing) cameras. PresenceDetector is upgraded with MediaPipe face detection fused with VAD. WorkspaceMonitor replaces ScreenMonitor, sending multi-image payloads (screen + cameras) to Gemini Flash. Activity mode detection fuses all signals to classify operator state.

**Tech Stack:** Python 3.12, ffmpeg (V4L2 capture), MediaPipe (face detection, CPU-only), Gemini Flash via LiteLLM (vision analysis), Pydantic (config), pytest + asyncio (testing)

**Design doc:** `docs/plans/2026-03-09-workspace-vision-design.md`

**Working directory:** `<ai-agents>/` (all file paths relative to this root unless noted)

**Existing test baseline:** 40 tests passing in `tests/hapax_voice/`

---

## Wave 1: Foundation

### Task 1: WebcamCapturer Data Models

**Files:**
- Modify: `agents/hapax_voice/screen_models.py`
- Test: `tests/hapax_voice/test_screen_models.py`

**Context:** The existing `screen_models.py` has `Issue` and `ScreenAnalysis` dataclasses. We add `CameraConfig` and the extended `WorkspaceAnalysis` model here. We also add `GearObservation` for hardware state tracking.

**Step 1: Write the failing tests**

```python
# Append to tests/hapax_voice/test_screen_models.py

from agents.hapax_voice.screen_models import CameraConfig, GearObservation, WorkspaceAnalysis


def test_camera_config_defaults():
    cfg = CameraConfig(device="/dev/video0", role="operator")
    assert cfg.width == 1280
    assert cfg.height == 720
    assert cfg.input_format == "mjpeg"
    assert cfg.pixel_format is None


def test_camera_config_ir():
    cfg = CameraConfig(
        device="/dev/video2", role="ir",
        width=340, height=340,
        input_format="rawvideo", pixel_format="gray",
    )
    assert cfg.pixel_format == "gray"


def test_gear_observation():
    obs = GearObservation(
        device="MPC Live III", powered=True,
        display_content="Song mode", notes="",
    )
    assert obs.powered is True


def test_workspace_analysis_extends_screen():
    wa = WorkspaceAnalysis(
        app="cosmic-term", context="running pytest", summary="Tests passing.",
        issues=[], suggestions=[], keywords=["pytest"],
        operator_present=True, operator_activity="typing",
        operator_attention="screen", gear_state=[], workspace_change=False,
    )
    assert wa.operator_present is True
    assert wa.app == "cosmic-term"


def test_workspace_analysis_defaults():
    wa = WorkspaceAnalysis(
        app="unknown", context="", summary="",
    )
    assert wa.operator_present is None
    assert wa.operator_activity == "unknown"
    assert wa.gear_state == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_voice/test_screen_models.py -v`
Expected: FAIL — ImportError for CameraConfig, GearObservation, WorkspaceAnalysis

**Step 3: Implement the models**

Add to `agents/hapax_voice/screen_models.py` after the existing `ScreenAnalysis` class:

```python
@dataclass(frozen=True)
class CameraConfig:
    """Configuration for a single webcam device."""
    device: str          # /dev/v4l/by-id/... or /dev/videoN
    role: str            # "operator", "hardware", "ir"
    width: int = 1280
    height: int = 720
    input_format: str = "mjpeg"
    pixel_format: str | None = None  # "gray" for IR sensor


@dataclass
class GearObservation:
    """Observed state of a hardware device from the C920 camera."""
    device: str
    powered: bool | None  # True/False/None(can't tell)
    display_content: str
    notes: str


@dataclass
class WorkspaceAnalysis:
    """Extended analysis covering screen + operator + hardware state."""
    # Screen awareness (same as ScreenAnalysis)
    app: str
    context: str
    summary: str
    issues: list[Issue] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    # Operator awareness
    operator_present: bool | None = None
    operator_activity: str = "unknown"
    operator_attention: str = "unknown"
    # Hardware awareness
    gear_state: list[GearObservation] = field(default_factory=list)
    workspace_change: bool = False
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_screen_models.py -v`
Expected: All PASS (existing 4 + new 5 = 9 tests)

**Step 5: Commit**

```bash
git add agents/hapax_voice/screen_models.py tests/hapax_voice/test_screen_models.py
git commit -m "feat: add webcam data models — CameraConfig, GearObservation, WorkspaceAnalysis"
```

---

### Task 2: WebcamCapturer

**Files:**
- Create: `agents/hapax_voice/webcam_capturer.py`
- Test: `tests/hapax_voice/test_webcam_capturer.py`

**Context:** This is the foundational capture primitive. It manages multiple cameras by role, captures frames via ffmpeg, and returns base64-encoded images. Follow the same patterns as `screen_capturer.py` (subprocess with timeout, temp directory, base64 encoding, cooldown tracking, fail-open on errors).

**Step 1: Write the failing tests**

```python
"""Tests for WebcamCapturer."""
import base64
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.hapax_voice.screen_models import CameraConfig
from agents.hapax_voice.webcam_capturer import WebcamCapturer


def test_capturer_init_with_cameras():
    cameras = [
        CameraConfig(device="/dev/video0", role="operator"),
        CameraConfig(device="/dev/video4", role="hardware"),
    ]
    cap = WebcamCapturer(cameras=cameras)
    assert cap.has_camera("operator")
    assert cap.has_camera("hardware")
    assert not cap.has_camera("ir")


def test_capturer_returns_none_for_missing_role():
    cap = WebcamCapturer(cameras=[])
    assert cap.capture("operator") is None


def test_capturer_respects_cooldown():
    cameras = [CameraConfig(device="/dev/video0", role="operator")]
    cap = WebcamCapturer(cameras=cameras, cooldown_s=60.0)
    # Simulate a recent capture
    cap._last_capture_time["operator"] = time.monotonic()
    assert cap.capture("operator") is None


def test_capturer_returns_base64_on_success(tmp_path):
    cameras = [CameraConfig(device="/dev/video0", role="operator")]
    cap = WebcamCapturer(cameras=cameras, cooldown_s=0)

    fake_jpg = b"\xff\xd8\xff\xe0fake-jpeg-data"
    fake_file = tmp_path / "frame.jpg"
    fake_file.write_bytes(fake_jpg)

    with patch("agents.hapax_voice.webcam_capturer.subprocess.run") as mock_run, \
         patch("agents.hapax_voice.webcam_capturer.tempfile.mkdtemp", return_value=str(tmp_path)):
        mock_run.return_value = MagicMock(returncode=0)
        # Place a fake output file where the capturer expects it
        result = cap.capture("operator")

    if result is not None:
        decoded = base64.b64decode(result)
        assert decoded == fake_jpg


def test_capturer_returns_none_on_ffmpeg_failure():
    cameras = [CameraConfig(device="/dev/video0", role="operator")]
    cap = WebcamCapturer(cameras=cameras, cooldown_s=0)

    with patch("agents.hapax_voice.webcam_capturer.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        result = cap.capture("operator")

    assert result is None


def test_capturer_returns_none_on_missing_device():
    cameras = [CameraConfig(device="/dev/video_nonexistent", role="operator")]
    cap = WebcamCapturer(cameras=cameras, cooldown_s=0)
    result = cap.capture("operator")
    assert result is None


def test_capturer_reset_cooldown():
    cameras = [CameraConfig(device="/dev/video0", role="operator")]
    cap = WebcamCapturer(cameras=cameras, cooldown_s=60.0)
    cap._last_capture_time["operator"] = time.monotonic()
    cap.reset_cooldown("operator")
    assert cap._last_capture_time["operator"] == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_voice/test_webcam_capturer.py -v`
Expected: FAIL — ModuleNotFoundError for webcam_capturer

**Step 3: Implement WebcamCapturer**

Create `agents/hapax_voice/webcam_capturer.py`:

```python
"""Webcam frame capture via ffmpeg V4L2."""
from __future__ import annotations

import base64
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path

from agents.hapax_voice.screen_models import CameraConfig

log = logging.getLogger(__name__)


class WebcamCapturer:
    """Captures frames from one or more webcams by role.

    Uses ffmpeg to grab a single frame from a V4L2 device. Each role
    (operator, hardware, ir) has independent cooldown tracking.
    """

    def __init__(
        self,
        cameras: list[CameraConfig] | None = None,
        cooldown_s: float = 5.0,
    ) -> None:
        self._cameras: dict[str, CameraConfig] = {}
        for cam in cameras or []:
            self._cameras[cam.role] = cam
        self._cooldown_s = cooldown_s
        self._last_capture_time: dict[str, float] = {
            role: 0.0 for role in self._cameras
        }

    def has_camera(self, role: str) -> bool:
        return role in self._cameras

    def reset_cooldown(self, role: str) -> None:
        """Reset cooldown for a specific camera role."""
        self._last_capture_time[role] = 0.0

    def capture(self, role: str) -> str | None:
        """Capture a frame from the camera with the given role.

        Returns base64-encoded JPEG, or None on failure/cooldown.
        """
        cam = self._cameras.get(role)
        if cam is None:
            return None

        now = time.monotonic()
        if (now - self._last_capture_time.get(role, 0.0)) < self._cooldown_s:
            return None

        if not Path(cam.device).exists():
            log.debug("Camera device not found: %s (%s)", cam.device, role)
            return None

        try:
            result = self._do_capture(cam)
            if result is not None:
                self._last_capture_time[role] = time.monotonic()
            return result
        except Exception as exc:
            log.warning("Webcam capture failed for %s: %s", role, exc)
            return None

    def _do_capture(self, cam: CameraConfig) -> str | None:
        """Execute ffmpeg capture and return base64-encoded image."""
        tmpdir = tempfile.mkdtemp(prefix="webcam-")
        outpath = os.path.join(tmpdir, "frame.jpg")

        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "v4l2",
                "-input_format", cam.input_format,
                "-video_size", f"{cam.width}x{cam.height}",
            ]
            if cam.pixel_format:
                cmd.extend(["-pix_fmt", cam.pixel_format])
            cmd.extend([
                "-i", cam.device,
                "-frames:v", "1",
                "-update", "1",
                outpath,
            ])

            proc = subprocess.run(
                cmd, capture_output=True, timeout=10,
            )

            if proc.returncode != 0:
                log.debug("ffmpeg failed for %s: %s", cam.role, proc.stderr[-200:] if proc.stderr else "")
                return None

            path = Path(outpath)
            if not path.exists():
                log.debug("No output file from ffmpeg for %s", cam.role)
                return None

            image_data = path.read_bytes()
            return base64.b64encode(image_data).decode("ascii")
        finally:
            # Cleanup temp directory
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_webcam_capturer.py -v`
Expected: All PASS (7 tests)

Note: `test_capturer_returns_base64_on_success` may need adjustment depending on how the mock interacts with the temp directory. The test should verify the base64 encoding pipeline works when ffmpeg produces a file. If the mock doesn't create the output file, the test should set up the fake file at the expected `outpath` location inside the patched tmpdir. Adjust as needed.

**Step 5: Commit**

```bash
git add agents/hapax_voice/webcam_capturer.py tests/hapax_voice/test_webcam_capturer.py
git commit -m "feat: add WebcamCapturer — role-based multi-camera capture via ffmpeg"
```

---

### Task 3: Webcam Config Fields

**Files:**
- Modify: `agents/hapax_voice/config.py:21-64`
- Test: `tests/hapax_voice/test_daemon_screen_integration.py` (append)

**Context:** Add webcam configuration fields to VoiceConfig. The existing screen monitor fields live at lines 53-58 of config.py.

**Step 1: Write the failing tests**

```python
# Append to tests/hapax_voice/test_daemon_screen_integration.py

def test_voice_config_has_webcam_fields():
    from agents.hapax_voice.config import VoiceConfig
    cfg = VoiceConfig()
    assert cfg.webcam_enabled is True
    assert "BRIO" in cfg.webcam_brio_device
    assert "C920" in cfg.webcam_c920_device
    assert cfg.webcam_capture_width == 1280
    assert cfg.webcam_capture_height == 720
    assert cfg.presence_face_detection is True
    assert cfg.presence_face_interval_s == 8.0
    assert cfg.workspace_analysis_cadence_s == 45.0
    assert cfg.timelapse_enabled is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_voice/test_daemon_screen_integration.py::test_voice_config_has_webcam_fields -v`
Expected: FAIL — AttributeError

**Step 3: Add config fields**

In `agents/hapax_voice/config.py`, after the screen monitor fields (after line 58), add:

```python
    # Webcam settings
    webcam_enabled: bool = True
    webcam_brio_device: str = "/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0"
    webcam_c920_device: str = "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_2657DFCF-video-index0"
    webcam_ir_device: str = ""
    webcam_capture_width: int = 1280
    webcam_capture_height: int = 720
    # Presence face detection
    presence_face_detection: bool = True
    presence_face_interval_s: float = 8.0
    presence_face_decay_s: float = 30.0
    presence_ir_fallback: bool = True
    # Workspace analysis
    workspace_analysis_cadence_s: float = 45.0
    workspace_hardware_cadence_s: float = 60.0
    workspace_multi_image: bool = True
    # Timelapse
    timelapse_enabled: bool = False
    timelapse_interval_s: float = 60.0
    timelapse_retention_days: int = 7
    timelapse_path: str = "<local-share>/hapax-voice/timelapse"
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_daemon_screen_integration.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/hapax_voice/config.py tests/hapax_voice/test_daemon_screen_integration.py
git commit -m "feat: add webcam, presence, workspace, and timelapse config fields"
```

---

## Wave 2: Presence Upgrade

### Task 4: Add mediapipe Dependency

**Files:**
- Modify: `pyproject.toml:14-51`

**Step 1: Add the dependency**

In `pyproject.toml`, add to the dependencies list (after the existing entries, before the closing `]`):

```python
    "mediapipe>=0.10.0",
    "opencv-python-headless>=4.10.0",
```

**Step 2: Sync the environment**

Run: `uv sync`
Expected: Successfully installs mediapipe and opencv-python-headless

**Step 3: Verify import works**

Run: `uv run python -c "import mediapipe; import cv2; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add mediapipe and opencv-python-headless for face detection"
```

Note: If `uv sync` fails due to dependency conflicts, try `uv pip install mediapipe opencv-python-headless` directly and document the conflict. The `uv.lock` file will also change.

---

### Task 5: Face Detector Module

**Files:**
- Create: `agents/hapax_voice/face_detector.py`
- Test: `tests/hapax_voice/test_face_detector.py`

**Context:** A lightweight face detection wrapper around MediaPipe BlazeFace. Runs on CPU only, returns boolean (face detected yes/no) plus count. Must work headless (no display). Designed to process raw image bytes (JPEG/PNG) or numpy arrays.

**Step 1: Write the failing tests**

```python
"""Tests for FaceDetector."""
import numpy as np
from unittest.mock import patch, MagicMock

from agents.hapax_voice.face_detector import FaceDetector


def test_detector_init():
    detector = FaceDetector()
    assert detector is not None


def test_detector_returns_false_on_empty_image():
    detector = FaceDetector()
    result = detector.detect(np.zeros((240, 320, 3), dtype=np.uint8))
    # All-black frame: no face expected
    assert result.detected is False
    assert result.count == 0


def test_detector_result_dataclass():
    from agents.hapax_voice.face_detector import FaceResult
    r = FaceResult(detected=True, count=2)
    assert r.detected is True
    assert r.count == 2


def test_detector_handles_none_gracefully():
    detector = FaceDetector()
    result = detector.detect(None)
    assert result.detected is False


def test_detector_from_base64():
    """Detector should accept base64 JPEG input."""
    detector = FaceDetector()
    # 1x1 pixel white JPEG, base64 encoded — no face
    import base64
    # Minimal valid JPEG
    tiny_jpg = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
        0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
        0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9,
    ])
    b64 = base64.b64encode(tiny_jpg).decode("ascii")
    result = detector.detect_from_base64(b64)
    assert result.detected is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_voice/test_face_detector.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Implement FaceDetector**

Create `agents/hapax_voice/face_detector.py`:

```python
"""Lightweight face detection using MediaPipe BlazeFace (CPU-only)."""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FaceResult:
    detected: bool
    count: int


class FaceDetector:
    """Detects faces in images using MediaPipe BlazeFace.

    Runs entirely on CPU (<5ms per frame). No face recognition —
    only answers "is someone there?" and "how many?".
    """

    def __init__(self, min_confidence: float = 0.5) -> None:
        self._min_confidence = min_confidence
        self._detector = None

    def _get_detector(self):
        """Lazily initialize MediaPipe face detector."""
        if self._detector is None:
            try:
                import mediapipe as mp
                self._detector = mp.solutions.face_detection.FaceDetection(
                    model_selection=0,  # short-range (within 2m)
                    min_detection_confidence=self._min_confidence,
                )
            except Exception as exc:
                log.warning("Failed to initialize MediaPipe: %s", exc)
        return self._detector

    def detect(self, image: np.ndarray | None) -> FaceResult:
        """Detect faces in a numpy BGR image array.

        Returns FaceResult with detected=True if at least one face found.
        """
        if image is None or image.size == 0:
            return FaceResult(detected=False, count=0)

        detector = self._get_detector()
        if detector is None:
            return FaceResult(detected=False, count=0)

        try:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = detector.process(rgb)
            if results.detections:
                count = len(results.detections)
                return FaceResult(detected=True, count=count)
            return FaceResult(detected=False, count=0)
        except Exception as exc:
            log.debug("Face detection failed: %s", exc)
            return FaceResult(detected=False, count=0)

    def detect_from_base64(self, image_b64: str | None) -> FaceResult:
        """Detect faces from a base64-encoded JPEG/PNG image."""
        if not image_b64:
            return FaceResult(detected=False, count=0)
        try:
            raw = base64.b64decode(image_b64)
            arr = np.frombuffer(raw, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if image is None:
                return FaceResult(detected=False, count=0)
            return self.detect(image)
        except Exception as exc:
            log.debug("Base64 face detection failed: %s", exc)
            return FaceResult(detected=False, count=0)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_face_detector.py -v`
Expected: All PASS (5 tests)

**Step 5: Commit**

```bash
git add agents/hapax_voice/face_detector.py tests/hapax_voice/test_face_detector.py
git commit -m "feat: add FaceDetector — MediaPipe BlazeFace CPU-only face detection"
```

---

### Task 6: Upgrade PresenceDetector with Face Fusion

**Files:**
- Modify: `agents/hapax_voice/presence.py:20-94`
- Modify: `tests/hapax_voice/test_presence.py` (create if not exists, or find existing)

**Context:** The current PresenceDetector scores purely on VAD event count. We add a `_face_detected` boolean with a decay timer, and a composite `score` property that fuses both signals. The face detection loop runs separately (driven by WorkspaceMonitor), so PresenceDetector just receives face events via a public method.

**Step 1: Write the failing tests**

Create `tests/hapax_voice/test_presence_face.py`:

```python
"""Tests for PresenceDetector face detection fusion."""
import time
from unittest.mock import patch

from agents.hapax_voice.presence import PresenceDetector


def test_presence_record_face_event():
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    p.record_face_event(detected=True, count=1)
    assert p.face_detected is True


def test_presence_face_decay():
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    p._face_decay_s = 1.0  # Short decay for testing
    p.record_face_event(detected=True, count=1)
    assert p.face_detected is True
    # Simulate time passing beyond decay
    p._last_face_time = time.monotonic() - 2.0
    assert p.face_detected is False


def test_presence_face_not_detected_stays_false():
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    p.record_face_event(detected=False, count=0)
    assert p.face_detected is False


def test_presence_composite_both_present():
    """VAD likely_present + face = definitely_present."""
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    # Add enough VAD events for likely_present
    for _ in range(6):
        p.record_vad_event(confidence=0.9)
    p.record_face_event(detected=True, count=1)
    assert p.score == "definitely_present"


def test_presence_composite_vad_only():
    """VAD likely_present + no face = likely_present (unchanged)."""
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    for _ in range(6):
        p.record_vad_event(confidence=0.9)
    assert p.score == "likely_present"


def test_presence_composite_face_only():
    """No VAD + face = likely_present."""
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    p.record_face_event(detected=True, count=1)
    assert p.score == "likely_present"


def test_presence_composite_uncertain_plus_face():
    """VAD uncertain + face = likely_present."""
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    for _ in range(3):
        p.record_vad_event(confidence=0.9)
    p.record_face_event(detected=True, count=1)
    assert p.score == "likely_present"


def test_presence_composite_absent():
    """No VAD + no face = likely_absent."""
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    assert p.score == "likely_absent"


def test_presence_guest_count():
    """Multiple faces detected = guest count available."""
    p = PresenceDetector(window_minutes=5, vad_threshold=0.4)
    p.record_face_event(detected=True, count=3)
    assert p.face_count == 3
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_voice/test_presence_face.py -v`
Expected: FAIL — AttributeError on record_face_event, face_detected, etc.

**Step 3: Modify PresenceDetector**

In `agents/hapax_voice/presence.py`, modify the class to add face detection fusion. Add these attributes to `__init__`:

```python
        self._face_detected: bool = False
        self._face_count: int = 0
        self._last_face_time: float = 0.0
        self._face_decay_s: float = 30.0
```

Add these methods after the existing `record_vad_event`:

```python
    def record_face_event(self, detected: bool, count: int = 0) -> None:
        """Record a face detection result from the webcam."""
        self._face_detected = detected
        self._face_count = count if detected else 0
        if detected:
            self._last_face_time = time.monotonic()

    @property
    def face_detected(self) -> bool:
        """Whether a face was recently detected (within decay window)."""
        if not self._face_detected:
            return False
        if (time.monotonic() - self._last_face_time) > self._face_decay_s:
            self._face_detected = False
            return False
        return True

    @property
    def face_count(self) -> int:
        """Number of faces detected in the most recent frame."""
        return self._face_count if self.face_detected else 0
```

Modify the existing `score` property to use composite logic:

```python
    @property
    def score(self) -> str:
        self._prune_old_events()
        count = len(self._events)
        face = self.face_detected

        if count >= 5:
            return "definitely_present" if face else "likely_present"
        if count >= 2:
            return "likely_present" if face else "uncertain"
        if face:
            return "likely_present"
        return "likely_absent"
```

Also add `import time` at the top if not already present.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_presence_face.py -v`
Expected: All PASS (9 tests)

Also run existing presence tests to verify no regression:
Run: `uv run pytest tests/hapax_voice/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/hapax_voice/presence.py tests/hapax_voice/test_presence_face.py
git commit -m "feat: upgrade PresenceDetector with face detection fusion scoring"
```

---

### Task 7: Update ContextGate for New Presence Levels

**Files:**
- Modify: `agents/hapax_voice/context_gate.py:43-61`
- Test: append to existing context_gate tests or create `tests/hapax_voice/test_context_gate_presence.py`

**Context:** The ContextGate currently doesn't check presence directly — it only checks session, volume, MIDI, and ambient audio. The proactive delivery loop in `__main__.py` checks presence separately (line 230: `if presence == "likely_absent": continue`). However, `definitely_present` is a stronger signal that could be surfaced. For now, the ContextGate itself doesn't need changes — but the proactive delivery loop in `__main__.py` should recognize the new level. This is wired in Task 11 (daemon integration).

**No code changes needed here — skip to Wave 3.**

---

## Wave 3: Workspace Awareness

### Task 8: WorkspaceAnalyzer (Multi-Image Gemini Flash)

**Files:**
- Create: `agents/hapax_voice/workspace_analyzer.py`
- Test: `tests/hapax_voice/test_workspace_analyzer.py`

**Context:** This replaces the single-image `ScreenAnalyzer` with a multi-image analyzer that sends screen + operator camera + hardware camera frames to Gemini Flash in one API call. It reuses the lazy AsyncOpenAI client pattern from `screen_analyzer.py`. The system prompt is updated to describe three image inputs and request the expanded JSON schema.

**Step 1: Write the failing tests**

```python
"""Tests for WorkspaceAnalyzer (multi-image Gemini Flash)."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.hapax_voice.workspace_analyzer import WorkspaceAnalyzer
from agents.hapax_voice.screen_models import WorkspaceAnalysis


@pytest.mark.asyncio
async def test_analyzer_returns_workspace_analysis():
    analyzer = WorkspaceAnalyzer(model="gemini-flash")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "app": "cosmic-term",
        "context": "Running pytest",
        "summary": "Terminal showing test output.",
        "issues": [],
        "suggestions": [],
        "keywords": ["pytest"],
        "operator_present": True,
        "operator_activity": "typing",
        "operator_attention": "screen",
        "gear_state": [
            {"device": "MPC Live III", "powered": True,
             "display_content": "Song mode", "notes": ""}
        ],
        "workspace_change": False,
    })

    with patch("agents.hapax_voice.workspace_analyzer.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        result = await analyzer.analyze(
            screen_b64="screen-data",
            operator_b64="operator-data",
            hardware_b64="hardware-data",
        )

    assert isinstance(result, WorkspaceAnalysis)
    assert result.app == "cosmic-term"
    assert result.operator_present is True
    assert result.operator_activity == "typing"
    assert len(result.gear_state) == 1
    assert result.gear_state[0].device == "MPC Live III"


@pytest.mark.asyncio
async def test_analyzer_works_with_screen_only():
    """Should work with just a screenshot (cameras unavailable)."""
    analyzer = WorkspaceAnalyzer(model="gemini-flash")

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "app": "firefox",
        "context": "Browsing docs",
        "summary": "Web page.",
        "issues": [],
        "suggestions": [],
        "keywords": [],
    })

    with patch("agents.hapax_voice.workspace_analyzer.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        result = await analyzer.analyze(screen_b64="screen-data")

    assert isinstance(result, WorkspaceAnalysis)
    assert result.operator_present is None  # No camera data
    assert result.gear_state == []


@pytest.mark.asyncio
async def test_analyzer_returns_none_on_failure():
    analyzer = WorkspaceAnalyzer(model="gemini-flash")

    with patch("agents.hapax_voice.workspace_analyzer.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        mock_cls.return_value = mock_client

        result = await analyzer.analyze(screen_b64="data")

    assert result is None


def test_analyzer_builds_multi_image_messages():
    """Verify the message array contains labeled images."""
    analyzer = WorkspaceAnalyzer(model="gemini-flash")
    messages = analyzer._build_messages(
        screen_b64="s", operator_b64="o", hardware_b64="h",
        extra_context=None,
    )
    user_content = messages[1]["content"]
    # Should have 3 image blocks + 3 text labels + 1 instruction
    text_blocks = [b for b in user_content if b["type"] == "text"]
    image_blocks = [b for b in user_content if b["type"] == "image_url"]
    assert len(image_blocks) == 3
    assert any("SCREENSHOT" in b["text"] for b in text_blocks)
    assert any("OPERATOR" in b["text"] for b in text_blocks)
    assert any("HARDWARE" in b["text"] for b in text_blocks)


def test_analyzer_omits_missing_cameras():
    """Message array should only include provided images."""
    analyzer = WorkspaceAnalyzer(model="gemini-flash")
    messages = analyzer._build_messages(
        screen_b64="s", operator_b64=None, hardware_b64=None,
        extra_context=None,
    )
    user_content = messages[1]["content"]
    image_blocks = [b for b in user_content if b["type"] == "image_url"]
    assert len(image_blocks) == 1
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_voice/test_workspace_analyzer.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Implement WorkspaceAnalyzer**

Create `agents/hapax_voice/workspace_analyzer.py`:

```python
"""Workspace analysis via Gemini Flash vision model (multi-image)."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from openai import AsyncOpenAI

from agents.hapax_voice.screen_models import (
    GearObservation,
    Issue,
    WorkspaceAnalysis,
)

log = logging.getLogger(__name__)

DEFAULT_CONTEXT_PATH = Path.home() / ".local" / "share" / "hapax-voice" / "screen_context.md"

_BASE_PROMPT = """\
You are a workspace awareness system for a single-operator music production studio
(Linux/COSMIC/Wayland). You receive up to three images per analysis:

1. SCREENSHOT: The operator's primary monitor
2. OPERATOR CAMERA: Front-facing camera showing the operator at their desk
3. HARDWARE CAMERA: Camera facing the music production hardware rig

Return a JSON object with these fields:
- app: the active application name (from screenshot)
- context: what the user is viewing/doing (1 sentence)
- summary: 2-3 sentence description of workspace state
- issues: list of detected problems, each with severity ("error"/"warning"/"info"), description, confidence (0.0-1.0)
- suggestions: max 2 actionable suggestions, only if high confidence
- keywords: list of relevant terms for documentation lookup
- operator_present: boolean, is the operator visible (null if no operator camera)
- operator_activity: "typing", "using_hardware", "reading", "away", "unknown"
- operator_attention: "screen", "hardware", "away", "unknown"
- gear_state: list of observed hardware devices, each with device (name), powered (bool/null), display_content (str), notes (str)
- workspace_change: boolean, significant physical change from typical state

Rules:
- Do NOT comment on non-work content (browsing, media, personal messages)
- Do NOT suggest unsolicited workflow changes
- Do NOT narrate obvious actions
- Focus on errors, failures, warnings, stack traces in screenshots
- For gear_state, only report devices you can identify with reasonable confidence
- If a camera image is not provided, set corresponding fields to null/unknown
- The hardware rig includes: OXI One MKII, 2x SP-404 MKII, MPC Live III,
  Digitakt II, Digitone II, Analog Rytm MKII, and various effects pedals
- Use system knowledge below to make intelligent observations about service relationships

Return ONLY valid JSON, no markdown fences."""

_CONTEXT_HEADER = "\n\n## System Knowledge\n\n"


class WorkspaceAnalyzer:
    """Analyzes workspace state using Gemini Flash via LiteLLM (multi-image)."""

    def __init__(
        self,
        model: str = "gemini-flash",
        context_path: str | Path = DEFAULT_CONTEXT_PATH,
    ) -> None:
        self.model = model
        self._system_prompt = self._build_prompt(Path(context_path))
        self._client: AsyncOpenAI | None = None

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

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            base_url = os.environ.get("LITELLM_BASE_URL", "http://127.0.0.1:4000")
            api_key = os.environ.get("LITELLM_API_KEY", "not-set")
            self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        return self._client

    async def analyze(
        self,
        screen_b64: str,
        operator_b64: str | None = None,
        hardware_b64: str | None = None,
        extra_context: str | None = None,
    ) -> WorkspaceAnalysis | None:
        """Analyze workspace from multiple image sources."""
        try:
            return await self._call_vision(
                screen_b64, operator_b64, hardware_b64, extra_context,
            )
        except Exception as exc:
            log.warning("Workspace analysis failed: %s", exc)
            return None

    def _build_messages(
        self,
        screen_b64: str,
        operator_b64: str | None,
        hardware_b64: str | None,
        extra_context: str | None,
    ) -> list[dict]:
        system = self._system_prompt
        if extra_context:
            system += "\n\n## Additional Context\n\n" + extra_context

        user_content: list[dict] = []

        # Screenshot (always present)
        user_content.append({"type": "text", "text": "SCREENSHOT:"})
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{screen_b64}"},
        })

        # Operator camera (optional)
        if operator_b64:
            user_content.append({"type": "text", "text": "OPERATOR CAMERA:"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{operator_b64}"},
            })

        # Hardware camera (optional)
        if hardware_b64:
            user_content.append({"type": "text", "text": "HARDWARE CAMERA:"})
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{hardware_b64}"},
            })

        user_content.append({
            "type": "text",
            "text": "Analyze this workspace.",
        })

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

    async def _call_vision(
        self,
        screen_b64: str,
        operator_b64: str | None,
        hardware_b64: str | None,
        extra_context: str | None,
    ) -> WorkspaceAnalysis | None:
        client = self._get_client()
        messages = self._build_messages(
            screen_b64, operator_b64, hardware_b64, extra_context,
        )

        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=1500,
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        data = json.loads(raw)

        gear_state = []
        for g in data.get("gear_state") or []:
            gear_state.append(GearObservation(
                device=g.get("device", "unknown"),
                powered=g.get("powered"),
                display_content=g.get("display_content", ""),
                notes=g.get("notes", ""),
            ))

        return WorkspaceAnalysis(
            app=data.get("app", "unknown"),
            context=data.get("context", ""),
            summary=data.get("summary", ""),
            issues=[Issue(**i) for i in data.get("issues", [])],
            suggestions=data.get("suggestions", []),
            keywords=data.get("keywords", []),
            operator_present=data.get("operator_present"),
            operator_activity=data.get("operator_activity", "unknown"),
            operator_attention=data.get("operator_attention", "unknown"),
            gear_state=gear_state,
            workspace_change=data.get("workspace_change", False),
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_workspace_analyzer.py -v`
Expected: All PASS (5 tests)

**Step 5: Commit**

```bash
git add agents/hapax_voice/workspace_analyzer.py tests/hapax_voice/test_workspace_analyzer.py
git commit -m "feat: add WorkspaceAnalyzer — multi-image Gemini Flash vision analysis"
```

---

### Task 9: WorkspaceMonitor (Replaces ScreenMonitor)

**Files:**
- Create: `agents/hapax_voice/workspace_monitor.py`
- Test: `tests/hapax_voice/test_workspace_monitor.py`

**Context:** WorkspaceMonitor is the evolved ScreenMonitor. It composes ScreenCapturer + WebcamCapturer + WorkspaceAnalyzer + ChangeDetector. It also drives the face detection loop for PresenceDetector. The API surface is identical to ScreenMonitor (same properties, same `run()`, same `set_notification_queue()`) so the daemon can swap it in.

**Step 1: Write the failing tests**

```python
"""Tests for WorkspaceMonitor orchestrator."""
import sys
import time
import types
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from agents.hapax_voice.screen_models import (
    CameraConfig, Issue, WorkspaceAnalysis, GearObservation,
)
from agents.hapax_voice.workspace_monitor import WorkspaceMonitor


def _make_analysis(**kwargs):
    defaults = dict(
        app="chrome", context="browsing", summary="Web page.",
        issues=[], suggestions=[], keywords=[],
        operator_present=True, operator_activity="typing",
        operator_attention="screen", gear_state=[], workspace_change=False,
    )
    defaults.update(kwargs)
    return WorkspaceAnalysis(**defaults)


def test_monitor_caches_latest_analysis():
    monitor = WorkspaceMonitor(enabled=False)
    analysis = _make_analysis()
    monitor._latest_analysis = analysis
    assert monitor.latest_analysis is analysis


def test_monitor_staleness():
    monitor = WorkspaceMonitor(enabled=False, recapture_idle_s=60)
    monitor._latest_analysis = _make_analysis()
    monitor._last_analysis_time = time.monotonic() - 120
    assert monitor.is_analysis_stale is True


def test_monitor_proactive_routing():
    queue = MagicMock()
    monitor = WorkspaceMonitor(enabled=False, proactive_min_confidence=0.8)
    monitor._notification_queue = queue
    analysis = _make_analysis(issues=[
        Issue(severity="error", description="Docker down", confidence=0.95),
    ])
    monitor._route_proactive_issues(analysis)
    assert queue.enqueue.call_count == 1


def test_monitor_proactive_cooldown():
    queue = MagicMock()
    monitor = WorkspaceMonitor(
        enabled=False, proactive_min_confidence=0.8, proactive_cooldown_s=300,
    )
    monitor._notification_queue = queue
    analysis = _make_analysis(issues=[
        Issue(severity="error", description="fail", confidence=0.9),
    ])
    monitor._route_proactive_issues(analysis)
    monitor._route_proactive_issues(analysis)
    assert queue.enqueue.call_count == 1


def test_monitor_reload_context():
    monitor = WorkspaceMonitor(enabled=False)
    mock_analyzer = MagicMock()
    monitor._analyzer = mock_analyzer
    monitor.reload_context()
    mock_analyzer.reload_context.assert_called_once()


def test_monitor_rag_query_empty_keywords():
    monitor = WorkspaceMonitor(enabled=False)
    assert monitor._query_rag([]) is None


def test_monitor_rag_query_returns_chunks():
    monitor = WorkspaceMonitor(enabled=False)
    mock_point = MagicMock()
    mock_point.payload = {"filename": "docker-compose.yml", "text": "config here"}
    mock_results = MagicMock()
    mock_results.points = [mock_point]

    mock_config = types.ModuleType("agents.shared.config")
    mock_config.embed = MagicMock(return_value=[0.1] * 768)
    mock_config.get_qdrant = MagicMock()
    mock_config.get_qdrant.return_value.query_points.return_value = mock_results

    with patch.dict(sys.modules, {
        "agents.shared": types.ModuleType("agents.shared"),
        "agents.shared.config": mock_config,
    }):
        result = monitor._query_rag(["docker"])
    assert result is not None
    assert "docker-compose.yml" in result


def test_monitor_disabled_without_crash():
    monitor = WorkspaceMonitor(enabled=False)
    assert monitor.latest_analysis is None
    assert monitor.has_camera("operator") is False
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_voice/test_workspace_monitor.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Implement WorkspaceMonitor**

Create `agents/hapax_voice/workspace_monitor.py`:

```python
"""Workspace awareness orchestrator composing screen, webcam, and analysis."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from agents.hapax_voice.notification_queue import VoiceNotification
from agents.hapax_voice.screen_capturer import ScreenCapturer
from agents.hapax_voice.screen_change_detector import ChangeDetector, FocusState
from agents.hapax_voice.screen_models import (
    CameraConfig,
    WorkspaceAnalysis,
)
from agents.hapax_voice.webcam_capturer import WebcamCapturer
from agents.hapax_voice.workspace_analyzer import WorkspaceAnalyzer

if TYPE_CHECKING:
    from agents.hapax_voice.face_detector import FaceDetector
    from agents.hapax_voice.notification_queue import NotificationQueue
    from agents.hapax_voice.presence import PresenceDetector

log = logging.getLogger(__name__)

_RAG_COLLECTION = "documents"
_RAG_MAX_CHUNKS = 3
_RAG_SCORE_THRESHOLD = 0.3


class WorkspaceMonitor:
    """Orchestrates workspace awareness: screen + webcams + analysis + routing.

    Drop-in evolution of ScreenMonitor. If webcams are unavailable,
    degrades to screen-only analysis (identical to ScreenMonitor behavior).
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
        cameras: list[CameraConfig] | None = None,
        webcam_cooldown_s: float = 30.0,
        face_interval_s: float = 8.0,
    ) -> None:
        self._enabled = enabled
        self.recapture_idle_s = recapture_idle_s
        self.proactive_min_confidence = proactive_min_confidence
        self.proactive_cooldown_s = proactive_cooldown_s
        self._face_interval_s = face_interval_s

        self._detector = ChangeDetector(poll_interval_s=poll_interval_s) if enabled else None
        self._screen_capturer = ScreenCapturer(cooldown_s=capture_cooldown_s) if enabled else None
        self._webcam_capturer = WebcamCapturer(cameras=cameras, cooldown_s=webcam_cooldown_s) if enabled and cameras else None
        self._analyzer = WorkspaceAnalyzer(model=analyzer_model) if enabled else None
        self._face_detector: FaceDetector | None = None

        self._latest_analysis: WorkspaceAnalysis | None = None
        self._last_analysis_time: float = 0.0
        self._last_proactive_time: float = 0.0
        self._notification_queue: NotificationQueue | None = None
        self._presence: PresenceDetector | None = None

        if self._detector is not None:
            self._detector.on_context_changed = self._on_context_changed

    @property
    def latest_analysis(self) -> WorkspaceAnalysis | None:
        return self._latest_analysis

    @property
    def is_analysis_stale(self) -> bool:
        if self._latest_analysis is None:
            return True
        return (time.monotonic() - self._last_analysis_time) > self.recapture_idle_s

    def has_camera(self, role: str) -> bool:
        if self._webcam_capturer is None:
            return False
        return self._webcam_capturer.has_camera(role)

    def set_notification_queue(self, queue: NotificationQueue) -> None:
        self._notification_queue = queue

    def set_presence(self, presence: PresenceDetector) -> None:
        """Link presence detector for face detection updates."""
        self._presence = presence

    def reload_context(self) -> None:
        """Reload workspace analyzer's static system context."""
        if self._analyzer is not None:
            self._analyzer.reload_context()
            log.info("Workspace analyzer context reloaded")

    def _on_context_changed(self, state: FocusState) -> None:
        log.info("Screen context changed: %s — %s", state.app_name, state.window_title)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._capture_and_analyze())
        except RuntimeError:
            log.debug("No event loop available for workspace capture")

    def _query_rag(self, keywords: list[str]) -> str | None:
        if not keywords:
            return None
        try:
            from agents.shared.config import embed, get_qdrant
            query_text = " ".join(keywords)
            vector = embed(query_text, prefix="search_query")
            client = get_qdrant()
            results = client.query_points(
                _RAG_COLLECTION, query=vector,
                limit=_RAG_MAX_CHUNKS, score_threshold=_RAG_SCORE_THRESHOLD,
            )
            if not results.points:
                return None
            chunks = []
            for p in results.points:
                filename = p.payload.get("filename", "unknown")
                text = p.payload.get("text", "")
                chunks.append(f"[{filename}]\n{text}")
            return "\n\n".join(chunks)
        except Exception as exc:
            log.debug("RAG augmentation failed (non-fatal): %s", exc)
            return None

    async def _capture_and_analyze(self) -> None:
        if self._screen_capturer is None or self._analyzer is None:
            return

        screen_b64 = self._screen_capturer.capture()
        if screen_b64 is None:
            return

        # Capture webcam frames (non-blocking, returns None if unavailable)
        operator_b64 = None
        hardware_b64 = None
        if self._webcam_capturer is not None:
            operator_b64 = self._webcam_capturer.capture("operator")
            hardware_b64 = self._webcam_capturer.capture("hardware")

        # RAG augmentation from previous keywords
        prev_keywords = self._latest_analysis.keywords if self._latest_analysis else []
        rag_context = self._query_rag(prev_keywords)

        analysis = await self._analyzer.analyze(
            screen_b64=screen_b64,
            operator_b64=operator_b64,
            hardware_b64=hardware_b64,
            extra_context=rag_context,
        )
        if analysis is not None:
            self._latest_analysis = analysis
            self._last_analysis_time = time.monotonic()
            log.info(
                "Workspace analysis: %s — %s (operator=%s, gear=%d)",
                analysis.app, analysis.context,
                analysis.operator_present,
                len(analysis.gear_state),
            )
            self._route_proactive_issues(analysis)

    def _route_proactive_issues(self, analysis: WorkspaceAnalysis) -> None:
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
                        title="Workspace Alert",
                        message=issue.description,
                        priority="normal",
                        source="workspace",
                    )
                )
                self._last_proactive_time = now
                log.info(
                    "Proactive workspace alert: %s (confidence=%.2f)",
                    issue.description, issue.confidence,
                )
                return

    async def _face_detection_loop(self) -> None:
        """Periodic face detection from BRIO camera for presence."""
        if self._webcam_capturer is None or self._presence is None:
            return
        if not self._webcam_capturer.has_camera("operator"):
            return

        # Lazy-init face detector
        if self._face_detector is None:
            try:
                from agents.hapax_voice.face_detector import FaceDetector
                self._face_detector = FaceDetector()
            except Exception as exc:
                log.warning("Face detector unavailable: %s", exc)
                return

        while True:
            try:
                frame_b64 = self._webcam_capturer.capture("operator")
                if frame_b64 is not None:
                    result = self._face_detector.detect_from_base64(frame_b64)
                    self._presence.record_face_event(
                        detected=result.detected, count=result.count,
                    )
            except Exception as exc:
                log.debug("Face detection loop error: %s", exc)
            await asyncio.sleep(self._face_interval_s)

    async def run(self) -> None:
        if not self._enabled or self._detector is None:
            log.info("Workspace monitor disabled")
            return

        log.info("Workspace monitor started")

        async def _staleness_loop() -> None:
            while True:
                if self.is_analysis_stale:
                    await self._capture_and_analyze()
                await asyncio.sleep(self._detector.poll_interval_s)

        tasks = [
            self._detector.poll_loop(),
            _staleness_loop(),
        ]
        # Add face detection if presence is linked
        if self._presence is not None:
            tasks.append(self._face_detection_loop())

        await asyncio.gather(*tasks)

    async def capture_fresh(self) -> WorkspaceAnalysis | None:
        if self._screen_capturer is not None:
            self._screen_capturer.reset_cooldown()
        if self._webcam_capturer is not None:
            self._webcam_capturer.reset_cooldown("operator")
            self._webcam_capturer.reset_cooldown("hardware")
        await self._capture_and_analyze()
        return self._latest_analysis
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_workspace_monitor.py -v`
Expected: All PASS (9 tests)

**Step 5: Commit**

```bash
git add agents/hapax_voice/workspace_monitor.py tests/hapax_voice/test_workspace_monitor.py
git commit -m "feat: add WorkspaceMonitor — multi-source workspace awareness orchestrator"
```

---

### Task 10: Update Persona for Workspace Context

**Files:**
- Modify: `agents/hapax_voice/persona.py:64-78`
- Modify: `tests/hapax_voice/test_daemon_screen_integration.py` (update existing tests)

**Context:** The existing `screen_context_block()` function formats `ScreenAnalysis` for the voice daemon system prompt. Update it to accept `WorkspaceAnalysis` and include operator and hardware context when available.

**Step 1: Write the failing test**

```python
# Append to tests/hapax_voice/test_daemon_screen_integration.py

def test_workspace_context_block_with_gear():
    from agents.hapax_voice.persona import screen_context_block
    from agents.hapax_voice.screen_models import WorkspaceAnalysis, GearObservation
    analysis = WorkspaceAnalysis(
        app="cosmic-term", context="running build", summary="Build in progress.",
        operator_present=True, operator_activity="typing",
        operator_attention="screen",
        gear_state=[
            GearObservation(device="MPC Live III", powered=True,
                          display_content="Song mode", notes=""),
        ],
    )
    result = screen_context_block(analysis)
    assert "MPC Live III" in result
    assert "typing" in result
    assert "Operator:" in result or "operator" in result.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/hapax_voice/test_daemon_screen_integration.py::test_workspace_context_block_with_gear -v`
Expected: FAIL — gear state not in output

**Step 3: Update screen_context_block**

In `agents/hapax_voice/persona.py`, modify the `screen_context_block` function to handle both `ScreenAnalysis` and `WorkspaceAnalysis`:

```python
def screen_context_block(analysis: ScreenAnalysis | None) -> str:
    """Format screen/workspace analysis for injection into LLM system prompt."""
    if analysis is None:
        return ""
    lines = [
        "\n## Current Screen Context",
        f"App: {analysis.app}",
        f"Context: {analysis.context}",
        f"Summary: {analysis.summary}",
    ]
    if analysis.issues:
        lines.append("Issues:")
        for issue in analysis.issues:
            lines.append(f"  - [{issue.severity}] {issue.description} (confidence: {issue.confidence:.2f})")

    # WorkspaceAnalysis extensions (duck-type check)
    if hasattr(analysis, "operator_present") and analysis.operator_present is not None:
        lines.append(f"Operator: {analysis.operator_activity}, attention on {analysis.operator_attention}")
    if hasattr(analysis, "gear_state") and analysis.gear_state:
        lines.append("Hardware:")
        for g in analysis.gear_state:
            powered = "on" if g.powered else ("off" if g.powered is False else "unknown")
            lines.append(f"  - {g.device}: {powered}")
            if g.display_content:
                lines.append(f"    Display: {g.display_content}")

    return "\n".join(lines)
```

Update the TYPE_CHECKING import at the top of persona.py to also import WorkspaceAnalysis (or keep the duck-type approach which avoids import changes).

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/hapax_voice/test_daemon_screen_integration.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/hapax_voice/persona.py tests/hapax_voice/test_daemon_screen_integration.py
git commit -m "feat: extend screen_context_block for workspace analysis with gear state"
```

---

### Task 11: Daemon Integration — Swap ScreenMonitor for WorkspaceMonitor

**Files:**
- Modify: `agents/hapax_voice/__main__.py:17,60-68,291-307`
- Test: `tests/hapax_voice/test_daemon_screen_integration.py` (append)

**Context:** Replace the ScreenMonitor import and instantiation with WorkspaceMonitor. Build camera configs from the new config fields. Wire the presence detector for face updates. Update the SIGHUP handler.

**Step 1: Write the failing test**

```python
# Append to tests/hapax_voice/test_daemon_screen_integration.py

def test_daemon_creates_workspace_monitor():
    """VoiceDaemon should use WorkspaceMonitor with camera configs."""
    from agents.hapax_voice.config import VoiceConfig
    cfg = VoiceConfig(screen_monitor_enabled=True, webcam_enabled=True)

    with patch("agents.hapax_voice.__main__.WorkspaceMonitor") as mock_wm, \
         patch("agents.hapax_voice.__main__.ScreenMonitor", side_effect=ImportError):
        from agents.hapax_voice.__main__ import VoiceDaemon
        daemon = VoiceDaemon(cfg=cfg)
        # Should have created a workspace monitor with camera configs
        assert mock_wm.called
```

**Step 2: Run test to verify it fails**

Expected: FAIL — WorkspaceMonitor not imported in __main__.py

**Step 3: Modify __main__.py**

Replace the ScreenMonitor import (line 17):
```python
# Remove:
from agents.hapax_voice.screen_monitor import ScreenMonitor
# Add:
from agents.hapax_voice.screen_models import CameraConfig
from agents.hapax_voice.workspace_monitor import WorkspaceMonitor
```

Replace the ScreenMonitor instantiation in `__init__` (lines 60-68):
```python
        # Build camera configs from config
        cameras = []
        if self.cfg.webcam_enabled:
            cameras.append(CameraConfig(
                device=self.cfg.webcam_brio_device, role="operator",
                width=self.cfg.webcam_capture_width,
                height=self.cfg.webcam_capture_height,
            ))
            cameras.append(CameraConfig(
                device=self.cfg.webcam_c920_device, role="hardware",
                width=self.cfg.webcam_capture_width,
                height=self.cfg.webcam_capture_height,
            ))
            if self.cfg.webcam_ir_device:
                cameras.append(CameraConfig(
                    device=self.cfg.webcam_ir_device, role="ir",
                    width=340, height=340,
                    input_format="rawvideo", pixel_format="gray",
                ))

        self.workspace_monitor = WorkspaceMonitor(
            enabled=self.cfg.screen_monitor_enabled,
            poll_interval_s=self.cfg.screen_poll_interval_s,
            capture_cooldown_s=self.cfg.screen_capture_cooldown_s,
            proactive_min_confidence=self.cfg.screen_proactive_min_confidence,
            proactive_cooldown_s=self.cfg.screen_proactive_cooldown_s,
            recapture_idle_s=self.cfg.screen_recapture_idle_s,
            cameras=cameras if cameras else None,
            face_interval_s=self.cfg.presence_face_interval_s,
        )
        self.workspace_monitor.set_notification_queue(self.notifications)
        self.workspace_monitor.set_presence(self.presence)
```

Update all references to `self.screen_monitor` → `self.workspace_monitor` throughout the file (lines 306, and the SIGHUP handler).

Update the status log line (around line 291-294):
```python
        log.info(
            "  Workspace monitor: %s (cameras: %s)",
            "enabled" if self.cfg.screen_monitor_enabled else "disabled",
            "BRIO+C920" if self.cfg.webcam_enabled else "screen-only",
        )
```

Update the background task (around line 305-307):
```python
        self._background_tasks.append(
            asyncio.create_task(self.workspace_monitor.run())
        )
```

Update the SIGHUP handler (near line 357):
```python
    loop.add_signal_handler(signal.SIGHUP, daemon.workspace_monitor.reload_context)
```

**Step 4: Run all tests to verify no regression**

Run: `uv run pytest tests/hapax_voice/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/hapax_voice/__main__.py tests/hapax_voice/test_daemon_screen_integration.py
git commit -m "feat: swap ScreenMonitor for WorkspaceMonitor in voice daemon"
```

---

## Wave 4: Integration

### Task 12: Document Scanner Hotkey

**Files:**
- Modify: `agents/hapax_voice/hotkey.py:12` (add "scan" to valid commands)
- Modify: `agents/hapax_voice/__main__.py` (add scan handler)
- Test: `tests/hapax_voice/test_hotkey_scan.py`

**Context:** Add a `"scan"` command to the hotkey server. When received, capture a high-res BRIO frame, send to Gemini Flash for OCR, and copy extracted text to clipboard via `wl-copy`.

**Step 1: Write the failing test**

```python
"""Tests for document scanner hotkey."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_scan_command_captures_and_extracts():
    from agents.hapax_voice.__main__ import VoiceDaemon
    from agents.hapax_voice.config import VoiceConfig

    cfg = VoiceConfig(webcam_enabled=False, screen_monitor_enabled=False)
    daemon = VoiceDaemon(cfg=cfg)

    # Mock the workspace monitor's webcam capturer
    daemon.workspace_monitor._webcam_capturer = MagicMock()
    daemon.workspace_monitor._webcam_capturer.capture.return_value = "fake-base64"
    daemon.workspace_monitor._webcam_capturer.has_camera.return_value = True
    daemon.workspace_monitor._webcam_capturer.reset_cooldown = MagicMock()

    with patch("agents.hapax_voice.__main__.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        await daemon._handle_hotkey("scan")
        # Should not crash, even if Gemini call fails
```

**Step 2: Run test to verify it fails**

Expected: FAIL — "scan" not handled in _handle_hotkey

**Step 3: Implement**

Add `"scan"` to the valid commands set in `hotkey.py` line 12.

Add scan handler in `__main__.py` `_handle_hotkey` method:

```python
        elif cmd == "scan":
            await self._handle_scan()
```

Add the `_handle_scan` method to VoiceDaemon:

```python
    async def _handle_scan(self) -> None:
        """Capture a high-res frame from BRIO and extract text via Gemini."""
        import subprocess as _sp

        if not self.workspace_monitor.has_camera("operator"):
            log.warning("Scan requested but no operator camera available")
            return

        self.workspace_monitor._webcam_capturer.reset_cooldown("operator")
        frame_b64 = self.workspace_monitor._webcam_capturer.capture("operator")
        if frame_b64 is None:
            log.warning("Scan: failed to capture frame")
            return

        try:
            from agents.hapax_voice.workspace_analyzer import WorkspaceAnalyzer
            client = self.workspace_monitor._analyzer._get_client()
            response = await client.chat.completions.create(
                model=self.workspace_monitor._analyzer.model,
                messages=[
                    {"role": "system", "content": "Extract all text from this image. Return plain text only."},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{frame_b64}"}},
                        {"type": "text", "text": "Extract text from this document/label."},
                    ]},
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            text = response.choices[0].message.content.strip()
            _sp.run(["wl-copy", text], timeout=5)
            log.info("Scan: extracted %d chars, copied to clipboard", len(text))
        except Exception as exc:
            log.warning("Scan failed: %s", exc)
```

**Step 4: Run tests**

Run: `uv run pytest tests/hapax_voice/test_hotkey_scan.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/hapax_voice/hotkey.py agents/hapax_voice/__main__.py tests/hapax_voice/test_hotkey_scan.py
git commit -m "feat: add document scanner hotkey — OCR via Gemini Flash + clipboard"
```

---

### Task 13: Cockpit API Workspace Endpoint

**Files:**
- Modify: `cockpit/api/routes/data.py`
- Test: Manual verification (cockpit API tests are integration-level)

**Context:** Add a `GET /api/workspace` endpoint that returns the latest WorkspaceAnalysis from the cached data refresh loop. This follows the existing pattern in `data.py` for fast-cadence endpoints.

**Step 1: Add the endpoint**

In `cockpit/api/routes/data.py`, add after the existing fast-cadence endpoints:

```python
@router.get("/workspace")
async def workspace():
    """Latest workspace analysis (screen + camera + hardware state)."""
    return _fast_response(app_state.workspace or {})
```

This requires the cockpit data refresh loop to populate `app_state.workspace`. The exact wiring depends on how the cockpit API gathers data from the voice daemon — this may need a shared state file or a daemon API endpoint.

For the initial implementation, write the latest WorkspaceAnalysis to a JSON file that the cockpit API reads:

**File:** Add to WorkspaceMonitor, after analysis update in `_capture_and_analyze()`:

```python
    def _persist_analysis(self, analysis: WorkspaceAnalysis) -> None:
        """Write latest analysis to shared state file for cockpit API."""
        import json
        state_path = Path.home() / ".local" / "share" / "hapax-voice" / "workspace_state.json"
        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "app": analysis.app,
                "context": analysis.context,
                "summary": analysis.summary,
                "operator_present": analysis.operator_present,
                "operator_activity": analysis.operator_activity,
                "gear_state": [
                    {"device": g.device, "powered": g.powered, "display_content": g.display_content}
                    for g in analysis.gear_state
                ],
                "timestamp": time.time(),
            }
            state_path.write_text(json.dumps(data))
        except Exception as exc:
            log.debug("Failed to persist workspace state: %s", exc)
```

**Step 2: Commit**

```bash
git add cockpit/api/routes/data.py agents/hapax_voice/workspace_monitor.py
git commit -m "feat: add /api/workspace cockpit endpoint + workspace state persistence"
```

---

### Task 14: Update Cross-Repo Documentation

**Files:**
- Modify: `<hapaxromana>/agent-architecture.md` (voice daemon section)
- Modify: `profiles/component-registry.yaml` (update voice-screen-monitor entry)
- Modify: `scripts/generate_screen_context.py` (add webcam device info)

**Context:** Update architecture docs and the component registry to reflect the evolution from screen awareness to workspace awareness. Update the screen context generator to include webcam device information in the static context file.

**Step 1: Update agent-architecture.md**

Update the voice daemon description to reference workspace awareness instead of screen awareness. Add the webcam subsystem description.

**Step 2: Update component-registry.yaml**

Rename `voice-screen-monitor` to `voice-workspace-monitor`. Update the role, constraints, and search_hints to reflect dual-camera workspace awareness.

**Step 3: Update generate_screen_context.py**

Add a section that lists available webcam devices:

```python
def _webcam_info() -> str:
    """Enumerate connected webcam devices."""
    try:
        from pathlib import Path
        by_id = Path("/dev/v4l/by-id")
        if not by_id.exists():
            return "(no V4L2 devices found)"
        devices = sorted(by_id.iterdir())
        return "\n".join(f"  - {d.name} -> {d.resolve()}" for d in devices)
    except Exception as exc:
        return f"(unavailable: {exc})"
```

Add this to the static sections of the generated context file.

**Step 4: Commit**

```bash
git add profiles/component-registry.yaml scripts/generate_screen_context.py
cd <hapaxromana> && git add agent-architecture.md
git commit -m "docs: update architecture + registry for workspace vision system"
```

---

### Task 15: Timelapse Service

**Files:**
- Create: `scripts/webcam_timelapse.py`
- Create: `<systemd-user>/webcam-timelapse.service`
- Create: `<systemd-user>/webcam-timelapse.timer`

**Context:** A lightweight systemd service that captures one frame per minute from each camera. Stores JPEG files with timestamped names. Handles cleanup of files older than the retention period.

**Step 1: Create the capture script**

Create `scripts/webcam_timelapse.py`:

```python
"""Periodic webcam timelapse capture."""
from __future__ import annotations

import argparse
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

CAMERAS = {
    "operator": "/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0",
    "hardware": "/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_2657DFCF-video-index0",
}
DEFAULT_PATH = Path.home() / ".local" / "share" / "hapax-voice" / "timelapse"


def capture_frame(device: str, role: str, output_dir: Path) -> None:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    outfile = output_dir / f"{role}-{ts}.jpg"
    cmd = [
        "ffmpeg", "-y", "-f", "v4l2",
        "-input_format", "mjpeg",
        "-video_size", "1280x720",
        "-i", device,
        "-frames:v", "1", "-update", "1",
        "-q:v", "5",
        str(outfile),
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception:
        pass  # fail-open


def cleanup_old(output_dir: Path, retention_days: int) -> None:
    cutoff = time.time() - (retention_days * 86400)
    for f in output_dir.glob("*.jpg"):
        if f.stat().st_mtime < cutoff:
            f.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=str, default=str(DEFAULT_PATH))
    parser.add_argument("--retention-days", type=int, default=7)
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for role, device in CAMERAS.items():
        if Path(device).exists():
            capture_frame(device, role, output_dir)

    cleanup_old(output_dir, args.retention_days)


if __name__ == "__main__":
    main()
```

**Step 2: Create the systemd units**

Service:
```ini
[Unit]
Description=Webcam timelapse capture
After=default.target

[Service]
Type=oneshot
ExecStart=%h/.local/bin/uv run python %h/projects/ai-agents/scripts/webcam_timelapse.py
WorkingDirectory=%h/projects/ai-agents
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin
```

Timer:
```ini
[Unit]
Description=Webcam timelapse timer (every 1 minute)

[Timer]
OnCalendar=*:0/1
Persistent=true

[Install]
WantedBy=timers.target
```

**Step 3: Enable the timer**

```bash
systemctl --user daemon-reload
systemctl --user enable --now webcam-timelapse.timer
```

**Step 4: Verify**

```bash
systemctl --user status webcam-timelapse.timer
ls -la <local-share>/hapax-voice/timelapse/
```

**Step 5: Commit**

```bash
git add scripts/webcam_timelapse.py
git commit -m "feat: add webcam timelapse capture script + systemd units"
```

---

## Wave 5: Compound Intelligence

### Task 16: Activity Mode Detection

**Files:**
- Create: `agents/hapax_voice/activity_mode.py`
- Test: `tests/hapax_voice/test_activity_mode.py`

**Context:** Classifies the operator's current activity mode based on fused signals: workspace analysis (screen + cameras), presence score, and audio state. The mode feeds into ContextGate for notification suppression and into the voice persona for context-aware responses.

**Step 1: Write the failing tests**

```python
"""Tests for activity mode detection."""
from agents.hapax_voice.activity_mode import classify_activity_mode
from agents.hapax_voice.screen_models import WorkspaceAnalysis, GearObservation


def test_coding_mode():
    analysis = WorkspaceAnalysis(
        app="cosmic-term", context="editing code", summary="IDE open.",
        operator_present=True, operator_activity="typing",
        operator_attention="screen", gear_state=[],
    )
    assert classify_activity_mode(analysis, audio_music=False) == "coding"


def test_production_mode():
    analysis = WorkspaceAnalysis(
        app="cosmic-term", context="terminal", summary="Terminal.",
        operator_present=True, operator_activity="using_hardware",
        operator_attention="hardware",
        gear_state=[
            GearObservation(device="MPC", powered=True, display_content="", notes=""),
        ],
    )
    assert classify_activity_mode(analysis, audio_music=True) == "production"


def test_away_mode():
    analysis = WorkspaceAnalysis(
        app="cosmic-term", context="idle", summary="Screen idle.",
        operator_present=False, operator_activity="away",
        operator_attention="away", gear_state=[],
    )
    assert classify_activity_mode(analysis, audio_music=False) == "away"


def test_meeting_mode():
    analysis = WorkspaceAnalysis(
        app="firefox", context="video call", summary="Video call in browser.",
        operator_present=True, operator_activity="typing",
        operator_attention="screen", gear_state=[],
    )
    assert classify_activity_mode(analysis, audio_music=False, audio_speech=True) == "meeting"


def test_research_mode():
    analysis = WorkspaceAnalysis(
        app="firefox", context="reading docs", summary="Documentation page.",
        operator_present=True, operator_activity="reading",
        operator_attention="screen", gear_state=[],
    )
    assert classify_activity_mode(analysis, audio_music=False) == "research"
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/hapax_voice/test_activity_mode.py -v`
Expected: FAIL — ModuleNotFoundError

**Step 3: Implement**

Create `agents/hapax_voice/activity_mode.py`:

```python
"""Activity mode classification from fused workspace signals."""
from __future__ import annotations

from agents.hapax_voice.screen_models import WorkspaceAnalysis

# Apps that suggest coding/development
_CODE_APPS = {"cosmic-term", "code", "com.visualstudio.code", "neovim", "vim"}
# Apps that suggest browsing/research
_BROWSER_APPS = {"firefox", "chromium", "chrome", "com.google.Chrome"}
# Keywords in context suggesting video calls
_MEETING_KEYWORDS = {"video call", "meeting", "zoom", "teams", "google meet"}


def classify_activity_mode(
    analysis: WorkspaceAnalysis | None,
    audio_music: bool = False,
    audio_speech: bool = False,
) -> str:
    """Classify operator activity mode from workspace analysis + audio signals.

    Returns one of: coding, production, research, meeting, away, idle, unknown.
    """
    if analysis is None:
        return "unknown"

    if analysis.operator_present is False or analysis.operator_activity == "away":
        return "away"

    has_gear = any(g.powered for g in analysis.gear_state)
    context_lower = (analysis.context or "").lower()

    # Meeting detection: video call app + speech
    if audio_speech and any(kw in context_lower for kw in _MEETING_KEYWORDS):
        return "meeting"

    # Production: hardware active + music or hardware attention
    if has_gear and (audio_music or analysis.operator_attention == "hardware"):
        return "production"

    # Coding: terminal/IDE + typing
    if analysis.app in _CODE_APPS and analysis.operator_activity in ("typing", "unknown"):
        return "coding"

    # Research: browser + reading
    if analysis.app in _BROWSER_APPS:
        return "research"

    return "idle" if analysis.operator_present else "unknown"
```

**Step 4: Run tests**

Run: `uv run pytest tests/hapax_voice/test_activity_mode.py -v`
Expected: All PASS (5 tests)

**Step 5: Commit**

```bash
git add agents/hapax_voice/activity_mode.py tests/hapax_voice/test_activity_mode.py
git commit -m "feat: add activity mode classification from fused workspace signals"
```

---

### Task 17: ContextGate Activity Mode Integration

**Files:**
- Modify: `agents/hapax_voice/context_gate.py`
- Test: `tests/hapax_voice/test_context_gate_activity.py`

**Context:** Add an activity mode check to ContextGate. During `production` and `meeting` modes, block non-urgent proactive notifications.

**Step 1: Write the failing test**

```python
"""Tests for ContextGate activity mode integration."""
from unittest.mock import MagicMock
from agents.hapax_voice.context_gate import ContextGate


def test_gate_blocks_during_production():
    session = MagicMock()
    session.is_active = False
    gate = ContextGate(session=session)
    gate._activity_mode = "production"
    result = gate.check()
    assert result.eligible is False
    assert "production" in result.reason.lower()


def test_gate_blocks_during_meeting():
    session = MagicMock()
    session.is_active = False
    gate = ContextGate(session=session)
    gate._activity_mode = "meeting"
    result = gate.check()
    assert result.eligible is False
    assert "meeting" in result.reason.lower()


def test_gate_allows_during_coding():
    session = MagicMock()
    session.is_active = False
    gate = ContextGate(session=session)
    gate._activity_mode = "coding"
    # Should pass the activity check (may fail on other checks like volume)
    # Just verify activity mode doesn't block
    assert gate._check_activity_mode().eligible is True
```

**Step 2: Run tests to verify they fail**

Expected: FAIL — no _activity_mode attribute or _check_activity_mode method

**Step 3: Implement**

Add to ContextGate `__init__`:
```python
        self._activity_mode: str = "unknown"
```

Add a public setter:
```python
    def set_activity_mode(self, mode: str) -> None:
        self._activity_mode = mode
```

Add the check method:
```python
    def _check_activity_mode(self) -> GateResult:
        if self._activity_mode in ("production", "meeting"):
            return GateResult(eligible=False, reason=f"Blocked: {self._activity_mode} mode active")
        return GateResult(eligible=True, reason="")
```

Add this check to the `check()` method, after the session check and before volume:
```python
        result = self._check_activity_mode()
        if not result.eligible:
            return result
```

**Step 4: Run tests**

Run: `uv run pytest tests/hapax_voice/test_context_gate_activity.py -v`
Expected: All PASS

Run full suite: `uv run pytest tests/hapax_voice/ -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add agents/hapax_voice/context_gate.py tests/hapax_voice/test_context_gate_activity.py
git commit -m "feat: add activity mode check to ContextGate — blocks during production/meeting"
```

---

### Task 18: Wire Activity Mode into Daemon Loop

**Files:**
- Modify: `agents/hapax_voice/__main__.py` (main loop, around line 309-320)

**Context:** After each workspace analysis completes, classify the activity mode and update the ContextGate. The classification needs the latest workspace analysis plus audio state (from ambient classifier or audio processor).

**Step 1: Add import and wiring**

Add import at top of `__main__.py`:
```python
from agents.hapax_voice.activity_mode import classify_activity_mode
```

In the main `run()` loop (around line 309-320), after the sleep, add activity mode update:

```python
                # Update activity mode from latest workspace analysis
                analysis = self.workspace_monitor.latest_analysis
                if analysis is not None:
                    mode = classify_activity_mode(analysis)
                    self.gate.set_activity_mode(mode)
```

**Step 2: Run full test suite**

Run: `uv run pytest tests/hapax_voice/ -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add agents/hapax_voice/__main__.py
git commit -m "feat: wire activity mode classification into daemon main loop"
```

---

### Task 19: Drift Detector Update

**Files:**
- Modify: `agents/drift_detector.py` (update screen context drift check)

**Context:** The drift detector already checks screen context freshness. Update it to also check for webcam device availability — if the design doc says cameras are part of the system, they should be detectable.

**Step 1: Add webcam device check**

Add to the `check_screen_context_drift()` function in `agents/drift_detector.py`:

```python
    # Check webcam devices
    brio_path = Path("/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0")
    c920_path = Path("/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_2657DFCF-video-index0")
    if not brio_path.exists():
        issues.append("BRIO webcam not detected at expected device path")
    if not c920_path.exists():
        issues.append("C920 webcam not detected at expected device path")
```

**Step 2: Commit**

```bash
git add agents/drift_detector.py
git commit -m "feat: add webcam device availability check to drift detector"
```

---

### Task 20: Final Integration Test

**Step 1: Run the full test suite**

Run: `uv run pytest tests/hapax_voice/ -v --tb=short`
Expected: All tests PASS

**Step 2: Verify camera capture works end-to-end**

Run: `uv run python -c "
from agents.hapax_voice.screen_models import CameraConfig
from agents.hapax_voice.webcam_capturer import WebcamCapturer
cameras = [
    CameraConfig(device='/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0', role='operator'),
    CameraConfig(device='/dev/v4l/by-id/usb-046d_HD_Pro_Webcam_C920_2657DFCF-video-index0', role='hardware'),
]
cap = WebcamCapturer(cameras=cameras, cooldown_s=0)
for role in ('operator', 'hardware'):
    result = cap.capture(role)
    print(f'{role}: {len(result) if result else None} bytes base64')
"`

Expected: Both cameras return base64 data

**Step 3: Verify face detection works**

Run: `uv run python -c "
from agents.hapax_voice.webcam_capturer import WebcamCapturer
from agents.hapax_voice.screen_models import CameraConfig
from agents.hapax_voice.face_detector import FaceDetector
cap = WebcamCapturer(cameras=[CameraConfig(device='/dev/v4l/by-id/usb-046d_Logitech_BRIO_5342C819-video-index0', role='operator')], cooldown_s=0)
frame = cap.capture('operator')
det = FaceDetector()
result = det.detect_from_base64(frame)
print(f'Face detected: {result.detected}, count: {result.count}')
"`

Expected: `Face detected: True, count: 1`

**Step 4: Commit final state**

```bash
git add -A
git commit -m "test: verify full workspace vision integration"
```

---

## Summary

| Wave | Tasks | What it delivers |
|------|-------|-----------------|
| 1: Foundation | 1-3 | Data models, WebcamCapturer, config fields |
| 2: Presence | 4-6 | MediaPipe face detection, VAD+face fusion scoring |
| 3: Workspace | 8-11 | WorkspaceAnalyzer (multi-image), WorkspaceMonitor, daemon integration |
| 4: Integration | 12-15 | Document scanner, cockpit endpoint, docs, timelapse |
| 5: Compound | 16-19 | Activity modes, ContextGate integration, drift detector |

Total: ~20 tasks, ~20 commits, estimated 40-60 new tests
