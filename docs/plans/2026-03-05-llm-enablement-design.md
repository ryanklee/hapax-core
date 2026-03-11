# LLM Enablement Across CLI, Desktop, and Applications

**Date:** 2026-03-05
**Status:** Approved
**Scope:** Tier 1 Interactive surface expansion
**Implementation repo:** `<distro-work>/`

## Motivation

Extend LLM availability beyond Claude Code and Obsidian to every interaction surface: shell, editor, browser, voice, and sysadmin workflows. Reduces task initiation friction (executive_function axiom) and pushes the system toward ambient LLM availability.

## Architectural Principle

All new tools are **Tier 1 Interactive surfaces**, not new tiers or agents. They route through LiteLLM at :4000 for model access and Langfuse tracing. No new orchestration patterns.

```
TIER 1: INTERACTIVE (expanded)
+-- Claude Code              (primary, unchanged)
+-- System Cockpit            (dashboard, unchanged)
+-- Obsidian + plugin         (knowledge surface, unchanged)
+-- Shell LLM layer           (NEW: mods, llm plugins, shell functions)
+-- Editor LLM layer          (NEW: Continue.dev in VS Code)
+-- Browser LLM layer         (NEW: Lumos extension)
+-- Voice input layer         (NEW: STT -> existing surfaces)
+-- Desktop hotkeys           (ENHANCED: existing fuzzel scripts)
```

## Axiom Compliance

| Axiom | Impact |
|-------|--------|
| single_user (100) | No auth on any tool. Single-operator configs. |
| executive_function (95) | Primary driver. Zero-config installs. NL->command, voice input, ambient availability. |
| corporate_boundary (90) | All tools on home machine only. No Obsidian plugin changes. |
| management_governance (85) | No management features in any new tool. |

## Waves

### Wave 1: CLI Foundation

**Tools:**

| Tool | Install | Purpose | LiteLLM |
|------|---------|---------|---------|
| mods (Charmbracelet) | `go install` | Unix pipe LLM (`stdin \| mods "prompt"`) | Yes |
| Fabric (Miessler) | `go install` | 200+ curated prompt patterns | Yes |
| llm-cmd | `llm install llm-cmd` | NL to shell command | Yes (inherits) |
| llm-ollama | `llm install llm-ollama` | Ollama models from `llm` CLI | Via LiteLLM |
| llm-templates-fabric | `llm install llm-templates-fabric` | Fabric patterns as `llm` templates | Yes (inherits) |

**Shell functions:** `explain()` (error explanation), `diagnose()` (log diagnosis), `how()` (NL to command).

**Configuration:** mods pointed at localhost:4000/v1, llm default model set to claude-sonnet via LiteLLM, Fabric pointed at LiteLLM as OpenAI-compatible endpoint.

### Wave 2: Editor + Browser

**Continue.dev** in VS Code pointed at LiteLLM proxy (localhost:4000/v1). Models: claude-sonnet (chat), claude-haiku (autocomplete), qwen-coder-32b (local coding). All traced in Langfuse.

**Lumos** Chrome extension for page RAG. Points at Ollama directly (localhost:11434) for embedding API compatibility. Acceptable observability gap — ad-hoc browser usage.

### Wave 3: Voice Input

**STT:** Voxtype (Rust, Wayland, push-to-talk, whisper.cpp). Fallback: custom faster-whisper + ydotool if COSMIC key-release events fail. Voice becomes another input to existing surfaces, not a new surface.

**TTS:** Piper (CPU-only, no VRAM competition). `speak()` shell function pipes LLM output to audio.

### Wave 4: Automation + Sysadmin

**LLM-enriched health alerts:** Enhance `shared/notify.py` in ai-agents to pipe diagnostic context through claude-haiku before sending ntfy notifications. Actionable alerts, not raw status.

**n8n LLM workflows:** Document auto-summarization on RAG ingest, smart notification filtering.

**Diagnostic aliases:** `docker-diagnose()`, `security-audit()`, `diagnose()` — pipe system tools through LLM.

## Artifact Locations

| Artifact | Location |
|----------|----------|
| This design doc | `hapaxromana/docs/plans/` |
| Install scripts, configs, setup notes | `distro-work/` |
| Component registry entries (for scout) | `ai-agents/profiles/component-registry.yaml` |
| Shell functions/aliases | `~/.zshrc` or sourced file |
| Tool configs (mods, fabric, continue, llm) | `~/.config/` per tool |
| LLM-enriched alerts | `ai-agents/shared/notify.py` |

## Scout Integration

All new tools added to `profiles/component-registry.yaml` in ai-agents so the weekly scout evaluates them for external fitness. Fields: name, role, category (tier1-cli, tier1-editor, tier1-browser, tier1-voice), installed_version_cmd, search_strategies, constraints.

## Dependencies

- LiteLLM running at :4000 (core service, always on)
- Ollama at :11434 for Lumos and local models
- Go toolchain for mods/Fabric install
- VS Code flatpak (already installed)
- Chrome flatpak (already installed)

## Non-Goals

- No new Tier 2 agents (existing agents sufficient)
- No COSMIC panel applets or desktop assistants (Wave C, future)
- No input method engine integration (Wave C, future)
- No changes to Obsidian plugin (corporate_boundary scope)
