# Screen Awareness for Hapax Voice — Design

**Date:** 2026-03-09
**Status:** Approved
**Repo:** ai-agents (implementation), hapaxromana (architecture docs)

## Goal

Give the Hapax Voice daemon continuous awareness of what's on the operator's screen, enabling contextual voice interactions ("help me with this") and conservative proactive alerts when high-confidence issues are visible (errors, failures, stack traces).

## Architecture

A new `ScreenMonitor` subsystem in the voice daemon with four layers:

```
Change Detector (AT-SPI, 2s poll)
  → focused app + window title
  → fires on_context_changed

Screen Capturer (cosmic-screenshot, on-demand)
  → triggered by context change, session open, or idle timer
  → downscales to 1280x720, base64 encodes, ephemeral

Screen Analyzer (Gemini Flash via LiteLLM)
  → system prompt: static core + RAG context
  → structured output: scene, issues, suggestions
  → result cached until next context change

Proactive Filter + Context Provider
  → issues with confidence >0.8 route to TTS via context gate
  → cached analysis injected into voice session context
```

Two modes of operation:

- **Passive context**: Current screen state is always available during voice sessions. "What's on my screen" or "help me with this" work without the user describing their screen.
- **Proactive alerts**: Conservative — only errors, stack traces, build failures with high confidence. Must pass the full context gate (session idle, volume OK, no MIDI studio activity, ambient sound classification clear).

## Change Detection Layer

AT-SPI2 polling via `gi.repository.Atspi` at 2-second intervals:

- Track `(app_name, window_title, is_active)` for all desktop windows
- Fire `on_context_changed` when focused window changes (different app or different title)
- Debounce: ignore changes that revert within 1 second (alt-tab bounce, popup dismiss)

**Triggers for screenshot capture:**

| Trigger | Rationale |
|---------|-----------|
| Focused window changed | New app or new tab — content is different |
| Voice session opened | LLM needs immediate context for the conversation |
| Same window >60s since last capture | Content may have changed (scrolling, new output) |

**Does NOT trigger:** same title + <60s elapsed, screen locked, context gate blocked.

Typical capture rate: 1-3/minute during active use, zero when idle.

### AT-SPI Depth

Research confirmed that Electron/Flatpak apps (Chrome, Obsidian, VS Code) expose window titles only — no DOM or text content via AT-SPI. Native GTK/Qt apps may expose deeper widget trees. AT-SPI serves as a cheap change detection signal, not a content source.

## System Context for the Analyzer

The screen analyzer LLM needs deep Hapax system knowledge to make intelligent observations.

### Static Core Prompt (~500 tokens)

Embedded in the analyzer, loaded from `<local-share>/hapax-voice/screen_context.md`:

- Service topology (service → port → purpose)
- Agent roster (name → function → invocation)
- Key directories and what lives where
- Common error signatures (e.g. "connection refused on 6333" = Qdrant down)
- Operator's desktop tools (VS Code flatpak, Chrome flatpak, cosmic-term, Obsidian)

### RAG Augmentation (per-capture)

- Extract keywords from the screen analysis
- Query Qdrant `documents` collection for relevant architecture docs, past solutions
- Inject top 2-3 chunks as additional context before proactive assessment

### Drift Detection for Static Core

The drift-detector agent (runs weekly) gets a new dimension: `screen_analyzer_context`.

- Compares static core prompt against live state: `docker compose ps`, `systemctl --user list-units`, port scan, agent directory listing
- If drift detected → auto-generates updated static core → writes to `<local-share>/hapax-voice/screen_context.md`
- Screen analyzer reloads on SIGHUP or next startup
- Drift corrections also update all relevant documentation across Hapax repos (hapaxromana/agent-architecture.md, ai-agents/README.md, component registry, etc.)

## Screen Analyzer (Vision LLM)

**Model:** Gemini Flash via LiteLLM (`gemini-flash` alias).
**Performance:** ~3s round-trip, ~800 tokens per analysis, ~$0.0001 per capture.

### Structured Output

```python
@dataclass
class ScreenAnalysis:
    app: str              # "Google Chrome"
    context: str          # "Viewing Pipecat docs — frame processors section"
    summary: str          # 2-3 sentence description
    issues: list[Issue]   # detected problems
    suggestions: list[str]  # max 2, only if high confidence
    keywords: list[str]   # for RAG lookup

@dataclass
class Issue:
    severity: str         # "error", "warning", "info"
    description: str      # "pytest failure: 3 tests failed in test_pipeline.py"
    confidence: float     # 0.0-1.0, only surface if >0.8
```

### Analyzer Prompt Asks For

1. What application is active and what the user is viewing/doing
2. Any errors, failures, warnings, or stack traces visible
3. Based on system knowledge, anything actionable the user might not realize

### Explicitly Does NOT

- Comment on non-work content (browsing, media, personal messages)
- Suggest unsolicited workflow changes ("you should use X instead")
- Narrate obvious actions ("I see you opened a terminal")

## Proactive Delivery and Session Integration

### Proactive Path (screen → voice, unprompted)

1. Screen analyzer detects an issue with confidence >0.8, severity "error"
2. Issue is enqueued in `NotificationQueue` with priority "normal", source "screen"
3. Proactive delivery loop checks `ContextGate.check()` — same four-layer gate used for all voice interruptions:
   - Session idle (not interrupting active conversation)
   - System volume below threshold
   - No MIDI studio connections active
   - Ambient sound classification passes (no music, speech, instruments)
4. If gate passes + rate limit clear (>5 min since last screen proactive) + presence detected → deliver via TTS
5. Example: "Heads up — your health monitor shows Qdrant is unreachable on 6333. That'll break RAG ingestion and the profiler agent."

### Passive Context Path (screen → voice session)

- On voice session open, most recent `ScreenAnalysis` injected into LLM system prompt
- "help me with this", "what's that error", "explain what I'm looking at" all work
- If analysis is stale (>60s), trigger fresh capture before LLM responds

### Daemon Integration

- `ScreenMonitor` follows existing composition pattern (same as `PresenceDetector`)
- Instantiated in `VoiceDaemon.__init__`, config fields in `VoiceConfig`
- Background async loop for AT-SPI polling
- Proactive issues route through existing `NotificationQueue` + `ContextGate`

## Configuration

```yaml
screen_monitor_enabled: true
screen_poll_interval_s: 2
screen_capture_cooldown_s: 10
screen_proactive_min_confidence: 0.8
screen_proactive_cooldown_s: 300    # 5 min between screen proactives
screen_recapture_idle_s: 60         # re-capture if same window >60s
```

## Error Handling

**Fail-open** (opposite of context gate — screen awareness is an enhancement, not a gate):

- AT-SPI unavailable → screen monitor disabled, daemon runs fine
- `cosmic-screenshot` fails → no capture, no analysis, no crash
- Gemini Flash down → skip analysis, log warning, try next cycle
- Nothing breaks if screen awareness is missing

## Constraints

- **VRAM:** Zero local impact. Gemini Flash is remote. AT-SPI and screenshot are CPU-only.
- **Privacy:** Screenshots are ephemeral (written to /tmp, deleted after encoding). Never persisted. Traces land in Langfuse (acceptable for single-operator). No screen content stored in Qdrant.

## Dependencies

- `python3-gi` + `gir1.2-atspi-2.0` (system packages, likely installed)
- `cosmic-screenshot` (installed)
- `imagemagick` for downscaling (installed)
- No new Python venv packages

## Testing Strategy

- Unit tests: mock AT-SPI, mock screenshot capture, mock Gemini responses
- Integration: daemon starts with screen monitor enabled, doesn't crash
- Degradation: AT-SPI unavailable → graceful disable
- Rate limiting: proactive delivery respects cooldowns
- Context gate: screen proactives pass all four gate layers
