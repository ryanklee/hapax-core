#!/usr/bin/env python3
"""SDLC Axiom Compliance Judge for hapax-constitution.

Structural compliance gate: YAML syntax validation, axiom ID cross-references,
protected path enforcement. No semantic LLM check -- the review handles that
for a spec repo.

Usage::

    uv run python -m scripts.sdlc_axiom_judge --pr-number 10
    uv run python -m scripts.sdlc_axiom_judge --pr-number 10 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sdlc.github import (
    add_pr_labels,
    fetch_pr,
    fetch_pr_changed_files,
    fetch_pr_diff,
    post_pr_comment,
)

# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------

PROTECTED_PATHS = [
    r"^axioms/registry\.yaml$",
    r"^axioms/implications/.*",
]

REQUIRED_AXIOM_FIELDS = {"id", "text", "weight", "type", "status", "scope"}


class StructuralResult(BaseModel):
    passed: bool
    violations: list[str] = []


class AxiomGateResult(BaseModel):
    structural: StructuralResult
    overall: Literal["pass", "block", "advisory"]
    summary: str = ""


# ---------------------------------------------------------------------------
# Structural checks (deterministic, no LLM)
# ---------------------------------------------------------------------------


def _check_yaml_syntax(changed_files: list[str]) -> list[str]:
    """Validate YAML syntax for any changed YAML files."""
    violations = []
    for fpath in changed_files:
        if not fpath.endswith((".yaml", ".yml")):
            continue
        full_path = Path(fpath)
        if not full_path.exists():
            continue
        try:
            yaml.safe_load(full_path.read_text())
        except yaml.YAMLError as exc:
            violations.append(f"YAML syntax error in {fpath}: {exc}")
    return violations


def _check_axiom_cross_references(changed_files: list[str]) -> list[str]:
    """Check that axiom IDs referenced in implications exist in the registry."""
    violations = []
    registry_path = Path("axioms/registry.yaml")
    if not registry_path.exists():
        return violations

    try:
        data = yaml.safe_load(registry_path.read_text())
        known_ids = {a["id"] for a in data.get("axioms", [])}
    except Exception:
        return violations

    implications_dir = Path("axioms/implications")
    if not implications_dir.exists():
        return violations

    for fpath in changed_files:
        if not fpath.startswith("axioms/implications/"):
            continue
        full_path = Path(fpath)
        if not full_path.exists():
            continue
        try:
            impl_data = yaml.safe_load(full_path.read_text())
            if isinstance(impl_data, dict):
                axiom_ref = impl_data.get("axiom_id") or impl_data.get("axiom")
                if axiom_ref and axiom_ref not in known_ids:
                    violations.append(
                        f"Unknown axiom ID '{axiom_ref}' referenced in {fpath}"
                    )
        except Exception:
            pass

    return violations


def _check_registry_schema(changed_files: list[str]) -> list[str]:
    """Validate that registry.yaml axioms have all required fields."""
    violations = []
    if "axioms/registry.yaml" not in changed_files:
        return violations

    registry_path = Path("axioms/registry.yaml")
    if not registry_path.exists():
        return violations

    try:
        data = yaml.safe_load(registry_path.read_text())
    except Exception:
        return violations

    for axiom in data.get("axioms", []):
        missing = REQUIRED_AXIOM_FIELDS - set(axiom.keys())
        if missing:
            violations.append(
                f"Axiom '{axiom.get('id', '???')}' missing required fields: {missing}"
            )
        weight = axiom.get("weight")
        if weight is not None and (not isinstance(weight, (int, float)) or weight < 0 or weight > 100):
            violations.append(
                f"Axiom '{axiom.get('id', '???')}' has invalid weight: {weight} (must be 0-100)"
            )

    return violations


def _check_protected_paths(changed_files: list[str]) -> list[str]:
    """Flag modifications to protected paths as advisory."""
    violations = []
    for fpath in changed_files:
        for pattern in PROTECTED_PATHS:
            if re.match(pattern, fpath):
                violations.append(f"Protected path modified: {fpath}")
                break
    return violations


def _check_structural(changed_files: list[str]) -> StructuralResult:
    """Run all structural checks."""
    violations = []
    violations.extend(_check_yaml_syntax(changed_files))
    violations.extend(_check_axiom_cross_references(changed_files))
    violations.extend(_check_registry_schema(changed_files))

    return StructuralResult(passed=len(violations) == 0, violations=violations)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_axiom_gate(pr_number: int, *, dry_run: bool = False) -> AxiomGateResult:
    """Run axiom compliance gate on a PR."""
    if dry_run:
        return AxiomGateResult(
            structural=StructuralResult(passed=True, violations=[]),
            overall="pass",
            summary="Dry run -- all checks passed.",
        )

    pr = fetch_pr(pr_number)
    changed_files = fetch_pr_changed_files(pr_number)

    # Structural checks.
    structural = _check_structural(changed_files)

    # Protected path check (advisory, not blocking).
    protected_hits = _check_protected_paths(changed_files)

    # Determine overall result.
    if not structural.passed:
        overall: Literal["pass", "block", "advisory"] = "block"
    elif protected_hits:
        overall = "advisory"
    else:
        overall = "pass"

    summary_parts = []
    if not structural.passed:
        summary_parts.append(f"Structural: {len(structural.violations)} violation(s)")
    if protected_hits:
        summary_parts.append(f"Protected paths touched: {len(protected_hits)}")
    if not summary_parts:
        summary_parts.append("All checks passed")

    result = AxiomGateResult(
        structural=structural,
        overall=overall,
        summary=f"Overall: {overall.upper()}. " + ". ".join(summary_parts) + ".",
    )

    t0 = time.monotonic()
    duration_ms = int((time.monotonic() - t0) * 1000)

    _post_gate_results(pr_number, result)

    try:
        from sdlc.log import log_sdlc_event

        log_sdlc_event(
            "axiom-gate",
            pr_number=pr_number,
            result={
                "overall": result.overall,
                "structural_passed": result.structural.passed,
                "structural_violations": result.structural.violations,
                "protected_paths": protected_hits,
            },
            duration_ms=duration_ms,
            dry_run=dry_run,
        )
    except Exception:
        pass

    return result


def _post_gate_results(pr_number: int, result: AxiomGateResult) -> None:
    """Post axiom gate results as PR comment."""
    icon = {"pass": "PASS", "block": "BLOCK", "advisory": "ADVISORY"}[result.overall]
    parts = [f"## Axiom Compliance Gate: {icon}\n"]

    if result.structural.violations:
        parts.append("### Structural Violations")
        for v in result.structural.violations:
            parts.append(f"- {v}")

    parts.append(f"\n{result.summary}")

    post_pr_comment(pr_number, "\n".join(parts))

    if result.overall == "block":
        add_pr_labels(pr_number, "axiom:blocked")
    elif result.overall == "advisory":
        add_pr_labels(pr_number, "axiom:precedent-review")
    else:
        add_pr_labels(pr_number, "sdlc:ready-for-human")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDLC Axiom Compliance Judge")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run_axiom_gate(args.pr_number, dry_run=args.dry_run)
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
