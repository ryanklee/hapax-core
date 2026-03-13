# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Governance architecture for LLM agent systems — constitutional axioms, derived implications, interpretive canon, sufficiency probes, and precedent store. This is a **specification repo**: YAML definitions and markdown documentation, not application code. Two reference implementations: hapax-council (personal OS) and hapax-officium (management support).

## Repository Layout

```
axioms/              Axiom definitions (registry.yaml) + implications/ per axiom
domains/             Domain-specific axiom extensions
knowledge/           Interpretive canon and governance knowledge base
docs/                Design documents (governance contract, primitives, perception interface)
research/            Governance research and analysis
scripts/             SDLC pipeline scripts (triage, review, axiom gate)
shared/              Shared modules for SDLC scripts
tests/               Test suite
```

## Key Files

- **`axioms/registry.yaml`** — Canonical axiom definitions (IDs, weights, scope, text)
- **`axioms/implications/`** — Per-axiom derived implications with tier (T0/T1/T2), enforcement mode, sufficiency levels
- **`domains/`** — Domain-scoped axiom extensions (infrastructure, management)
- **`knowledge/interpretive-canon.md`** — Rules for axiom interpretation in novel situations
- **`pattern-guide.md`** — Guide for implementing the governance pattern
- **`agent-architecture.md`** — Agent tier architecture specification
- **`operations-manual.md`** — Operational reference

## Conventions

- **NEVER switch branches in the primary worktree.** The primary checkout (`~/projects/hapax-constitution`) stays on `main`. For any feature branch, use `git worktree add ../hapax-constitution--<branch-slug> <branch>`. This prevents concurrent Claude sessions from clobbering each other's state. When done, `git worktree remove`.
- **Always PR completed work before moving on.** When you finish a coherent batch of work (feature, fix, refactor), create a PR immediately — do not wait to be asked. Only skip the PR if the work is genuinely incomplete or broken. Push and PR freely; this is expected behavior. **Do NOT start new work until the current work is resolved** — resolved means either a PR has been submitted or there is no branch/changes remaining to PR. This is a blocking requirement.
- **This is a spec repo.** Changes to `axioms/registry.yaml` are always high-complexity and require human review.
- **YAML is the source of truth** for axiom definitions and implications. Markdown documents describe; YAML defines.
- **Weight ordering matters.** Higher weight = higher precedence. Constitutional axioms always outweigh domain axioms (supremacy clause).
- **Tier semantics are strict.** T0 = block (existential violation), T1 = review (requires awareness), T2 = warn (quality preference).

## SDLC Pipeline

Spec-focused SDLC pipeline adapted for a specification repository. No implement workflow — spec changes are authored by humans or domain experts.

```
Issue opened (labeled "agent-eligible")
  → Triage (Sonnet): classify as spec-update | new-axiom | implication-change | documentation
  → Review (Sonnet): YAML validity, weight consistency, tier correctness, cross-references
  → Axiom Gate (structural only): YAML validation, axiom ID cross-references, no LLM semantic check
  → Auto-merge (squash) on pass, block on structural violation
```

**Scripts** (`scripts/`): `sdlc_triage.py`, `sdlc_review.py`, `sdlc_axiom_judge.py`. All support `--dry-run`.

**Workflows** (`.github/workflows/`): `sdlc-triage.yml`, `sdlc-review.yml`, `sdlc-axiom-gate.yml`.

**Key constraint**: Changes touching `axioms/registry.yaml` are always classified as L complexity (too large for automated implementation). CODEOWNERS protects `axioms/`, `domains/`, `knowledge/`.

## Build and Test

```bash
uv sync

# Run tests
uv run pytest tests/ -q

# Dry-run SDLC scripts
uv run python -m scripts.sdlc_triage --issue-number 1 --dry-run
uv run python -m scripts.sdlc_review --pr-number 1 --dry-run
uv run python -m scripts.sdlc_axiom_judge --pr-number 1 --dry-run
```
