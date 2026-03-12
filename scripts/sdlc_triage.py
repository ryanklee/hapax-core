#!/usr/bin/env python3
"""SDLC Issue Triage Agent for hapax-constitution.

Classifies GitHub issues by type and complexity for a governance spec repo.
Outputs structured JSON for workflow consumption.

Usage::

    uv run python -m scripts.sdlc_triage --issue-number 42
    uv run python -m scripts.sdlc_triage --issue-number 42 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# Ensure project root is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.sdlc_github import fetch_issue

# ---------------------------------------------------------------------------
# Structured output model
# ---------------------------------------------------------------------------


class TriageResult(BaseModel):
    type: Literal["spec-update", "new-axiom", "implication-change", "documentation"]
    complexity: Literal["S", "M", "L"]
    reject_reason: str | None = None
    file_hints: list[str] = []


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

PROTECTED_PATHS = [
    "axioms/registry.yaml",
]


def _load_axiom_ids() -> list[str]:
    """Load axiom IDs from the registry for context."""
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
You are the triage agent for hapax-constitution, a governance specification repository.
This repo contains YAML axiom definitions and markdown documentation -- no application code.

Changes to axiom weights or T0 implications are high-risk.

## Known Axioms
{axiom_list}

## Issue Types
- **spec-update**: Modify existing axiom text, weights, or metadata.
- **new-axiom**: Propose a new axiom to the registry.
- **implication-change**: Add, remove, or modify implications for an existing axiom.
- **documentation**: Changes to markdown docs, research, or operational guides.

## Complexity Heuristics
- **S** (small): Single file change, documentation fix, implication wording tweak.
- **M** (medium): Multiple implications changed, new implication tier, cross-references.
- **L** (large): New axiom, weight changes, structural registry changes, always needs human.

## Rejection Criteria (set reject_reason if any apply)
- Complexity is L (too large for automated implementation).
- Adding or removing axioms from registry.yaml (always L).
- Requirements are ambiguous or missing acceptance criteria.
- Changes to axiom weights (always needs human judgment).

## Protected Paths
- axioms/registry.yaml: Adding/removing axioms is always L complexity.

## Output
Return a JSON object with:
- type: "spec-update" | "new-axiom" | "implication-change" | "documentation"
- complexity: "S" | "M" | "L"
- reject_reason: null if agent-eligible, or a string explaining why not
- file_hints: list of file paths likely involved
"""


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _call_llm(system: str, user: str, *, dry_run: bool = False) -> TriageResult:
    if dry_run:
        return TriageResult(
            type="spec-update",
            complexity="S",
            reject_reason=None,
            file_hints=[],
        )

    try:
        import anthropic
    except ImportError:
        from pydantic_ai import Agent

        agent = Agent(
            os.environ.get("SDLC_TRIAGE_MODEL", "anthropic:claude-sonnet-4-6"),
            system_prompt=system,
            output_type=TriageResult,
        )
        result = agent.run_sync(user)
        return result.output

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ.get("SDLC_TRIAGE_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = response.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return TriageResult.model_validate_json(text.strip())


# ---------------------------------------------------------------------------
# Similar-issue search
# ---------------------------------------------------------------------------

_TRIAGE_STOP_WORDS = frozenset(
    "the a an is are was were be been being have has had do does did will would "
    "could should may might can shall to of in for on with at by from as into "
    "through during before after above below between out off over under again "
    "further then once this that these those it its not no nor and but or so "
    "if when where how what which who whom why".split()
)


def _extract_search_keywords(title: str, body: str, max_keywords: int = 5) -> list[str]:
    """Extract salient keywords from issue text for search."""
    text = f"{title} {body}"
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for w in words:
        if w not in _TRIAGE_STOP_WORDS and w not in seen:
            seen.add(w)
            keywords.append(w)
        if len(keywords) >= max_keywords:
            break
    return keywords


def find_similar_closed(
    issue_title: str,
    issue_body: str,
    *,
    skip_github: bool = False,
) -> list[dict]:
    """Find closed issues/PRs similar to the given issue."""
    keywords = _extract_search_keywords(issue_title, issue_body)
    if not keywords:
        return []

    results: list[dict] = []

    if not skip_github:
        try:
            from shared.sdlc_github import search_closed_issues

            query = " ".join(keywords[:4])
            gh_results = search_closed_issues(query, limit=5)
            for item in gh_results:
                item["source"] = "github"
                results.append(item)
        except Exception:
            pass

    return results


def _format_similar_issues(similar: list[dict]) -> str:
    """Format similar closed issues as context for the triage prompt."""
    if not similar:
        return ""
    lines = ["\n## Similar Past Issues (Closed)"]
    for item in similar[:5]:
        labels_str = ", ".join(item.get("labels", []))
        suffix = f" [{labels_str}]" if labels_str else ""
        lines.append(f"- #{item['number']}: {item['title']}{suffix}")
    lines.append("")
    lines.append("Consider whether this issue is a duplicate or regression of the above.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_triage(
    issue_number: int, *, dry_run: bool = False, skip_similar: bool = False
) -> TriageResult:
    """Triage a GitHub issue and return structured result."""
    if dry_run:
        # In dry-run mode, skip GitHub API calls entirely.
        system_prompt = _build_system_prompt()
        return _call_llm(system_prompt, "Dry run", dry_run=True)

    issue = fetch_issue(issue_number)
    system_prompt = _build_system_prompt()
    user_prompt = f"# {issue.title}\n\n{issue.body}"

    similar = find_similar_closed(issue.title, issue.body, skip_github=skip_similar)
    similar_context = _format_similar_issues(similar)
    if similar_context:
        user_prompt += similar_context

    model = os.environ.get("SDLC_TRIAGE_MODEL", "claude-sonnet-4-6")
    t0 = time.monotonic()
    result = _call_llm(system_prompt, user_prompt, dry_run=False)
    duration_ms = int((time.monotonic() - t0) * 1000)

    try:
        from shared.sdlc_log import log_sdlc_event

        log_sdlc_event(
            "triage",
            issue_number=issue_number,
            result={
                "type": result.type,
                "complexity": result.complexity,
                "reject_reason": result.reject_reason,
                "file_hints": result.file_hints[:10],
            },
            duration_ms=duration_ms,
            model_used=model,
            dry_run=dry_run,
        )
    except Exception:
        pass

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="SDLC Issue Triage Agent")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Use fixture response")
    parser.add_argument("--skip-similar", action="store_true", help="Skip similar-issue search")
    args = parser.parse_args()

    result = run_triage(args.issue_number, dry_run=args.dry_run, skip_similar=args.skip_similar)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
