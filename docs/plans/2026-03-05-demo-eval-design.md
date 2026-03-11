# Demo Evaluation Agent — Design Document

**Date:** 2026-03-05
**Status:** Approved

## Problem

The demo quality pipeline (Stage 3: self-critique) evaluates the *script text* before rendering. It cannot assess the actual output — whether screenshots are legible, visuals match narration, the HTML player works, or the overall presentation would meet the operator's standards. There is no end-to-end quality gate and no automated way to iterate until the output is good enough.

## Goal

A fully autonomous evaluation agent that generates a demo end-to-end, evaluates the rendered output against rubrics the operator would apply, diagnoses failures, adjusts planning parameters, and re-generates until quality passes or iteration limit is reached. The operator receives the final output and a structured evaluation report.

## Design Decisions

### Approach: Standalone Evaluation Agent (Tier 2)

A new Pydantic AI agent (`agents/demo_eval.py`) that orchestrates generate → evaluate → heal loops. Chosen over promptfoo (poor image evaluation, no self-healing) and Claude Code scripts (not automated, not reproducible).

### Key Principles

- **Evaluate rendered output, not just text.** Send actual screenshots to a vision-capable LLM.
- **Fix inputs, not code.** The self-healing loop adjusts planning prompt parameters and constraints — not pipeline source code.
- **One golden path first.** Prove the loop works on a single scenario before expanding.
- **Structured reports.** Every evaluation produces a machine-readable report with per-dimension scores.
- **Reuse existing infrastructure.** Gemini Pro via LiteLLM for vision evaluation. Existing quality dimensions as starting point.

---

## Architecture

```
User runs: uv run python -m agents.demo_eval

Phase 1: Generate
    generate_demo("the system for a non-technical friend", format="slides", duration="3m")
    → output/demos/<timestamp>-the-system/

Phase 2: Evaluate (LLM-as-judge via Gemini Pro vision)
    Read: script.json, metadata.json, all screenshots, demo.html
    Send to Gemini Pro: screenshot images + narration text + rubrics
    Produce: DemoEvalReport (per-dimension pass/fail + specific issues)

Phase 3: Heal (if evaluation fails, max 3 iterations)
    Diagnose: LLM analyzes failures against pipeline config
    Adjust: modify planning prompt overrides
    Re-generate: back to Phase 1 with accumulated overrides
    Report: structured output with full iteration history
```

The agent does NOT modify pipeline source code. It adjusts **tunable parameters** passed as overrides to the planning prompt builder.

---

## Evaluation Rubrics

### Text Dimensions (from script.json narration)

| Dimension | What's Checked |
|-----------|---------------|
| **style_compliance** | Narration matches presenter-style.yaml. No corporatisms, hedging, breathless enthusiasm. First-person voice. State-explain-show cadence. |
| **audience_calibration** | Vocabulary appropriate for target audience. Family = no jargon. Technical = precise terminology. |
| **duration_feasibility** | Total word count × speech rate ≈ target duration (±20%). |
| **key_points_quality** | Bullets are substantive and specific. Contain numbers or concrete facts, not vague platitudes. |
| **narrative_coherence** | Scenes follow the selected framework. Logical flow. Clear arc with opening and closing. |

### Visual Dimensions (screenshots sent to Gemini Pro)

| Dimension | What's Checked |
|-----------|---------------|
| **visual_clarity** | Screenshots are legible, not cut off, show relevant UI content. No error pages, loading spinners, or blank screens. |
| **visual_variety** | Not all screenshots look identical. Different pages, views, or data shown across scenes. |
| **theme_compliance** | Diagrams and charts use Gruvbox palette. Consistent visual style across non-screenshot visuals. |
| **visual_narration_alignment** | What's shown in the screenshot relates to what's narrated. The visual serves the scene's purpose. |

### Structural Dimensions (deterministic, no LLM)

| Dimension | What's Checked |
|-----------|---------------|
| **files_present** | script.json, metadata.json, demo.html, all screenshots exist. |
| **metadata_correctness** | Audience matches request, scene count matches script, quality_pass is true, duration is reasonable. |
| **html_integrity** | demo.html contains base64 images, scene titles, expected Gruvbox CSS colors, functional player structure. |

---

## Self-Healing: What "Fix" Means

The agent accumulates `planning_overrides` — additional instructions appended to the planning prompt on each retry.

| Failure | Adjustment Lever |
|---------|-----------------|
| Style violations (corporatisms, hedging) | Explicit "CRITICAL: avoid these exact phrases: [list]" |
| Audience too technical | Tightened vocabulary constraints + examples of appropriate language |
| Duration mismatch | Adjusted scene count or words-per-scene constraints |
| Weak key points | "Each key point must include a specific number or concrete fact" |
| Visual issues (blank, cut off) | Modified screenshot specs (different URLs, viewport sizes, wait conditions) |
| Narrative structure problems | Strengthened framework instructions with explicit scene-by-scene guidance |
| Visual-narration misalignment | Added "ensure each scene's visual directly illustrates the narration" |

Adjustments are generated by an LLM diagnosis step that receives the evaluation report and produces targeted override text.

---

## Data Models

```python
class DemoEvalDimension(BaseModel):
    name: str
    category: Literal["text", "visual", "structural"]
    passed: bool
    score: float  # 0.0-1.0
    issues: list[str]
    evidence: str | None = None  # quote or screenshot description

class DemoEvalReport(BaseModel):
    dimensions: list[DemoEvalDimension]
    overall_pass: bool
    overall_score: float  # weighted average
    iteration: int
    adjustments_applied: list[str]

class DemoEvalResult(BaseModel):
    scenario: str
    passed: bool
    iterations: int
    final_report: DemoEvalReport
    history: list[DemoEvalReport]
    demo_dir: str
    total_duration_seconds: float
```

---

## Vision Model

Gemini Pro via LiteLLM (`gemini-pro` alias). Screenshots loaded as base64 and sent as image content parts in the prompt. LiteLLM handles the format translation to Gemini's multimodal API.

The evaluation prompt sends all screenshots in a single call (typically 3-7 images for a 3-minute demo) with the rubric and narration text, requesting structured evaluation output.

---

## CLI Interface

```bash
# Default golden path (family audience, slides, 3min)
uv run python -m agents.demo_eval

# Custom scenario
uv run python -m agents.demo_eval --scenario "health monitoring for leadership" --duration 10m

# Evaluate existing demo output (no generation)
uv run python -m agents.demo_eval --eval-only output/demos/20260305-the-system/

# Tuning
uv run python -m agents.demo_eval --max-iterations 5
uv run python -m agents.demo_eval --pass-threshold 0.8  # minimum overall score
```

---

## New Files

| File | Purpose |
|------|---------|
| `agents/demo_eval.py` | Evaluation agent — orchestrates generate/evaluate/heal loop |
| `agents/demo_pipeline/eval_rubrics.py` | Rubric definitions, scoring functions, structural checks |
| `tests/test_demo_eval.py` | Unit tests for rubric scoring + evaluation logic |

---

## What This Does NOT Do

- **Modify pipeline source code.** Fixes are prompt/constraint overrides, not code changes.
- **Evaluate audio quality.** TTS perceptual quality is Chatterbox's concern. We evaluate narration *text*.
- **Test multiple scenarios initially.** One golden path first. More scenarios can be added as configurations.
- **Replace the existing self-critique.** Stage 3 (critique.py) evaluates the script before rendering. This agent evaluates the rendered output after the full pipeline. They're complementary.

---

## What Stays the Same

- Demo generation pipeline (demo.py) — unchanged, called as-is
- Quality dimensions in critique.py — existing self-critique still runs during generation
- Output directory structure — evaluation agent reads standard output format
- Model routing via LiteLLM — evaluation uses same infrastructure
