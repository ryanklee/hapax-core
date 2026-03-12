#!/usr/bin/env python3
"""SDLC Adversarial Review Agent for hapax-constitution.

Reviews agent-authored PRs focused on spec correctness: YAML validity,
axiom weight consistency, implication tier correctness, cross-reference validity.

Usage::

    uv run python -m scripts.sdlc_review --pr-number 10
    uv run python -m scripts.sdlc_review --pr-number 10 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sdlc.github import (
    add_pr_labels,
    fetch_pr_changed_files,
    fetch_pr_diff,
    post_pr_comment,
)

# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


class ReviewFinding(BaseModel):
    file: str
    line: int | None = None
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    description: str
    suggestion: str = ""


class ReviewResult(BaseModel):
    verdict: Literal["approve", "request_changes"]
    findings: list[ReviewFinding] = []
    summary: str = ""


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def _load_axiom_ids() -> list[str]:
    """Load axiom IDs from the registry for cross-reference checking."""
    import yaml

    registry = Path(__file__).resolve().parent.parent / "axioms" / "registry.yaml"
    if not registry.exists():
        return []
    data = yaml.safe_load(registry.read_text())
    return [a["id"] for a in data.get("axioms", [])]


def _build_system_prompt() -> str:
    axiom_ids = _load_axiom_ids()
    axiom_list = ", ".join(axiom_ids) if axiom_ids else "(none loaded)"
    return f"""\
You are an independent reviewer for hapax-constitution, a governance specification repository.
This repo contains YAML axiom definitions and markdown documentation -- no application code.

You are reviewing changes made by another AI agent. You have NOT seen the author's reasoning.

## Known Axiom IDs
{axiom_list}

## Review Focus
1. **YAML validity**: Correct syntax, proper indentation, valid field values.
2. **Axiom weight consistency**: Weights must be 0-100, hardcoded axioms should have high weights.
3. **Implication tier correctness**: T0 (hard block) through T3 (advisory) must be appropriate.
4. **Cross-reference validity**: Axiom IDs referenced in implications must exist in registry.
5. **Schema compliance**: Required fields (id, text, weight, type, status, scope) must be present.
6. **Semantic correctness**: Do changes maintain internal consistency of the governance spec?

## Rules
- Only report HIGH and MEDIUM severity findings.
- Be specific: reference file paths.
- Suggest concrete fixes.
- If the changes are clean, approve. Do NOT manufacture findings.

## Output
Return a JSON object with: verdict ("approve" or "request_changes"),
findings (list of {{file, line, severity, description, suggestion}}),
summary (brief overall assessment).
"""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _call_llm(system: str, user: str, *, dry_run: bool = False) -> ReviewResult:
    if dry_run:
        return ReviewResult(
            verdict="approve",
            findings=[],
            summary="Dry run -- no review performed.",
        )

    try:
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=os.environ.get("SDLC_REVIEW_MODEL", "claude-sonnet-4-6"),
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text
    except ImportError:
        from pydantic_ai import Agent

        agent = Agent(
            os.environ.get("SDLC_REVIEW_MODEL", "anthropic:claude-sonnet-4-6"),
            system_prompt=system,
            output_type=ReviewResult,
        )
        result = agent.run_sync(user)
        return result.output

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return ReviewResult.model_validate_json(text.strip())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_review(pr_number: int, *, dry_run: bool = False) -> ReviewResult:
    """Review a pull request adversarially."""
    if dry_run:
        return _call_llm("", "", dry_run=True)

    diff = fetch_pr_diff(pr_number)
    changed_files = fetch_pr_changed_files(pr_number)

    system_prompt = _build_system_prompt()
    user_prompt = f"""\
## Changed Files
{chr(10).join(f'- `{f}`' for f in changed_files)}

## Diff
```diff
{diff[:50000]}
```
"""

    model = os.environ.get("SDLC_REVIEW_MODEL", "claude-sonnet-4-6")
    t0 = time.monotonic()
    result = _call_llm(system_prompt, user_prompt)
    duration_ms = int((time.monotonic() - t0) * 1000)

    _post_review_results(pr_number, result)

    try:
        from sdlc.log import log_sdlc_event

        log_sdlc_event(
            "review",
            pr_number=pr_number,
            result={
                "verdict": result.verdict,
                "findings_count": len(result.findings),
                "high_findings": sum(
                    1 for f in result.findings if f.severity == "HIGH"
                ),
            },
            duration_ms=duration_ms,
            model_used=model,
            dry_run=dry_run,
        )
    except Exception:
        pass

    return result


def _post_review_results(pr_number: int, result: ReviewResult) -> None:
    """Post review findings as PR comment and set appropriate labels."""
    parts = [f"## Adversarial Review\n\n**Verdict:** {result.verdict.upper()}\n"]

    if result.findings:
        parts.append("### Findings\n")
        for f in result.findings:
            loc = f"`{f.file}:{f.line}`" if f.line else f"`{f.file}`"
            parts.append(f"- **{f.severity}** ({loc}): {f.description}")
            if f.suggestion:
                parts.append(f"  - *Suggestion:* {f.suggestion}")

    if result.summary:
        parts.append(f"\n### Summary\n{result.summary}")

    post_pr_comment(pr_number, "\n".join(parts))

    if result.verdict == "request_changes":
        add_pr_labels(pr_number, "changes-requested")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDLC Adversarial Review Agent")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_review(args.pr_number, dry_run=args.dry_run)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
