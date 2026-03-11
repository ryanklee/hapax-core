# Knowledge Sufficiency Engine — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a system that detects missing management knowledge in the Obsidian vault and acquires it through guided interviews.

**Architecture:** A YAML knowledge model (hapaxromana) defines 27 requirements across 3 tiers. A deterministic Python audit (ai-agents) scans the vault and produces a prioritized gap list, feeding nudges. An Obsidian plugin interview engine (obsidian-hapax) conducts guided conversations to populate missing data, writing vault notes via the Obsidian API.

**Tech Stack:** Python 3.12 (pydantic, pyyaml, pytest), TypeScript (Obsidian API, esbuild), YAML

**Repos:** `<hapaxromana>/`, `<ai-agents>/`, `<obsidian-hapax>/`

**Design doc:** `docs/plans/2026-03-04-knowledge-sufficiency-design.md`

---

## Task 1: Create Knowledge Model YAML

**Repo:** `<hapaxromana>/`

**Files:**
- Create: `knowledge/management-sufficiency.yaml`

**Step 1: Create the knowledge directory**

```bash
mkdir -p <hapaxromana>/knowledge
```

**Step 2: Write the knowledge model**

Create `<hapaxromana>/knowledge/management-sufficiency.yaml` with all 27 requirements. Each entry has: `id`, `category`, `description`, `source`, `check` (type + params), `acquisition` (method, question, extraction_schema, output), `priority`, `depends_on`.

```yaml
# Knowledge Sufficiency Model
# Defines what the management system needs to know to function.
# Categories: foundational (system non-functional without), structural (features degrade), enrichment (quality improves)
# Sources: TT = Team Topologies, SP = Scaling People, EP = An Elegant Puzzle
version: 1

requirements:
  # ── Foundational (priority 90–100) ────────────────────────────
  - id: direct-reports
    category: foundational
    description: >
      Person notes for all direct reports with type, role, team, status.
      Every management feature depends on these existing.
    source: "All 3 books"
    check:
      type: min_count
      path: "10-work/people"
      filter: { type: person, status: active }
      min: 1
    acquisition:
      method: interview
      question: >
        Let's set up your team. Who are your direct reports?
        For each person, I need their name, role, and which team they're on.
      extraction_schema:
        type: array
        items: { name: string, role: string, team: string }
      output: person_note
    priority: 100
    depends_on: []

  - id: team-assignment
    category: foundational
    description: >
      Every active person note has a team field populated.
      Required for team-level aggregation and Larson state classification.
    source: "TT"
    check:
      type: field_populated
      path: "10-work/people"
      filter: { type: person, status: active }
      field: team
    acquisition:
      method: interview
      question: "What team is {name} on?"
      extraction_schema:
        type: object
        properties: { person: string, team: string }
      output: frontmatter_update
    priority: 95
    depends_on: [direct-reports]

  - id: 1on1-cadence
    category: foundational
    description: >
      Every active person note has cadence set.
      Without cadence, the stale-1:1 nudge never fires.
    source: "SP, EP"
    check:
      type: field_populated
      path: "10-work/people"
      filter: { type: person, status: active }
      field: cadence
    acquisition:
      method: interview
      question: "How often do you meet with {name} for 1:1s? (weekly, biweekly, monthly)"
      extraction_schema:
        type: object
        properties: { person: string, cadence: string }
      output: frontmatter_update
    priority: 95
    depends_on: [direct-reports]

  - id: manager-context
    category: foundational
    description: >
      Operator's manager is documented as a person note.
      Required for upward management prep.
    source: "SP"
    check:
      type: min_count
      path: "10-work/people"
      filter: { type: person, role: manager }
      min: 1
    acquisition:
      method: interview
      question: "Who is your manager? What's their role/title?"
      extraction_schema:
        type: object
        properties: { name: string, role: string, title: string }
      output: person_note
    priority: 90
    depends_on: []

  - id: company-mission
    category: foundational
    description: >
      Company mission documented for context in management decisions.
    source: "SP"
    check:
      type: file_exists
      path: "10-work/references/company-mission.md"
    acquisition:
      method: interview
      question: "What's your company's mission or purpose statement? Even a rough version helps."
      extraction_schema:
        type: object
        properties: { mission: string }
      output: reference_doc
    priority: 90
    depends_on: []

  # ── Structural (priority 60) ──────────────────────────────────
  - id: operating-principles
    category: structural
    description: >
      Company or team values/operating principles documented.
    source: "SP"
    check:
      type: file_exists
      path: "10-work/references/operating-principles.md"
    acquisition:
      method: interview
      question: "Does your company or team have documented values or operating principles? What are they?"
      extraction_schema:
        type: object
        properties: { principles: { type: array, items: string } }
      output: reference_doc
    priority: 60
    depends_on: []

  - id: org-structure
    category: structural
    description: >
      Org hierarchy documented — reporting lines, spans of control.
    source: "EP"
    check:
      type: file_exists
      path: "10-work/references/org-chart.md"
    acquisition:
      method: interview
      question: >
        Let's map your org structure. Who reports to you? Who do you report to?
        Are there peer managers? What's the broader reporting chain?
      extraction_schema:
        type: object
        properties:
          reports_to: string
          peers: { type: array, items: string }
          org_notes: string
      output: reference_doc
    priority: 60
    depends_on: [direct-reports, manager-context]

  - id: team-topology-type
    category: structural
    description: >
      Team type set for each team (stream-aligned, enabling, complicated-subsystem, platform).
    source: "TT"
    check:
      type: field_coverage
      path: "10-work/people"
      filter: { type: person, status: active }
      field: team-type
      threshold: 80
    acquisition:
      method: interview
      question: >
        What type of team is {team}? Options:
        - Stream-aligned (delivers end-to-end value to users)
        - Enabling (helps other teams adopt new capabilities)
        - Complicated-subsystem (handles complex domain requiring specialist knowledge)
        - Platform (provides internal services to reduce cognitive load)
      extraction_schema:
        type: object
        properties: { team: string, team_type: string }
      output: frontmatter_update
    priority: 60
    depends_on: [direct-reports, team-assignment]

  - id: team-interaction-modes
    category: structural
    description: >
      Interaction modes between team pairs documented (collaboration, X-as-a-Service, facilitating).
    source: "TT"
    check:
      type: file_exists
      path: "10-work/references/team-interactions.md"
    acquisition:
      method: interview
      question: >
        How do your teams interact with each other? For each pair of teams that work together,
        what's the interaction mode?
        - Collaboration (working closely together, high bandwidth)
        - X-as-a-Service (one team provides a service, clear API)
        - Facilitating (one team helps another build a capability)
      extraction_schema:
        type: object
        properties:
          interactions: { type: array, items: { team_a: string, team_b: string, mode: string } }
      output: reference_doc
    priority: 60
    depends_on: [team-topology-type]

  - id: operating-cadence
    category: structural
    description: >
      Meeting cadences documented — what recurring meetings exist and their purposes.
    source: "SP"
    check:
      type: file_exists
      path: "10-work/references/operating-cadence.md"
    acquisition:
      method: interview
      question: >
        What recurring meetings do you have? For each, what's the purpose, frequency, and attendees?
        (e.g., team standup daily, sprint planning biweekly, all-hands monthly)
      extraction_schema:
        type: object
        properties:
          meetings: { type: array, items: { name: string, frequency: string, purpose: string } }
      output: reference_doc
    priority: 60
    depends_on: []

  - id: meeting-ceremonies
    category: structural
    description: >
      At least one meeting note per ceremony type exists.
    source: "All 3 books"
    check:
      type: min_count
      path: "10-work/meetings"
      filter: { type: meeting-ceremony }
      min: 1
    acquisition:
      method: nudge
      question: null
      extraction_schema: null
      output: null
    priority: 60
    depends_on: [operating-cadence]

  - id: key-stakeholders
    category: structural
    description: >
      Person notes for non-report stakeholders (skip-levels, cross-functional partners).
    source: "SP"
    check:
      type: min_count
      path: "10-work/people"
      filter: { type: person, role: stakeholder }
      min: 1
    acquisition:
      method: interview
      question: >
        Who are key stakeholders outside your direct reports?
        Think: skip-levels, cross-functional partners, executives you interact with regularly.
      extraction_schema:
        type: array
        items: { name: string, role: string, relationship: string }
      output: person_note
    priority: 60
    depends_on: []

  - id: decision-approach
    category: structural
    description: >
      Decision framework documented — how decisions get made.
    source: "SP"
    check:
      type: file_exists
      path: "10-work/references/decision-framework.md"
    acquisition:
      method: interview
      question: >
        How are decisions typically made on your team?
        Is there a framework (RAPID, DACI, consensus, autocratic)?
        Who has decision rights for different domains?
      extraction_schema:
        type: object
        properties: { framework: string, notes: string }
      output: reference_doc
    priority: 60
    depends_on: []

  - id: team-charters
    category: structural
    description: >
      Per-team mission and scope documented.
    source: "SP"
    check:
      type: file_exists
      path: "10-work/references/team-charters.md"
    acquisition:
      method: interview
      question: >
        For each team you manage, what's their mission and scope?
        What are they responsible for? What's explicitly outside their scope?
      extraction_schema:
        type: object
        properties:
          charters: { type: array, items: { team: string, mission: string, scope: string } }
      output: reference_doc
    priority: 60
    depends_on: [team-assignment]

  - id: team-sizing
    category: structural
    description: >
      Team sizes documented and within healthy range (6-8 per Larson).
    source: "EP"
    check:
      type: derived
      logic: "Count active people per team, check 6-8 range"
    acquisition:
      method: nudge
      question: null
      extraction_schema: null
      output: null
    priority: 60
    depends_on: [direct-reports, team-assignment]

  # ── Enrichment (priority 35) ──────────────────────────────────
  - id: career-goals
    category: enrichment
    description: >
      Person notes have 3-year career goal documented.
    source: "SP, EP"
    check:
      type: field_coverage
      path: "10-work/people"
      filter: { type: person, status: active }
      field: career-goal-3y
      threshold: 50
    acquisition:
      method: interview
      question: "What's {name}'s career goal for the next 3 years, as you understand it?"
      extraction_schema:
        type: object
        properties: { person: string, career_goal_3y: string }
      output: frontmatter_update
    priority: 35
    depends_on: [direct-reports]

  - id: skill-will
    category: enrichment
    description: >
      Person notes have skill-level and will-signal populated.
    source: "SP"
    check:
      type: field_coverage
      path: "10-work/people"
      filter: { type: person, status: active }
      field: skill-level
      threshold: 50
    acquisition:
      method: interview
      question: >
        For {name}, how would you assess their:
        - Skill level: developing, career, advanced, or expert?
        - Will/motivation signal: high, moderate, or low?
      extraction_schema:
        type: object
        properties: { person: string, skill_level: string, will_signal: string }
      output: frontmatter_update
    priority: 35
    depends_on: [direct-reports]

  - id: cognitive-load
    category: enrichment
    description: >
      Person notes have numeric cognitive-load (1-5).
    source: "TT, EP"
    check:
      type: field_coverage
      path: "10-work/people"
      filter: { type: person, status: active }
      field: cognitive-load
      threshold: 80
    acquisition:
      method: interview
      question: >
        For {name}, how would you rate their cognitive load right now on a 1-5 scale?
        1 = very light, 3 = balanced, 5 = overwhelmed
      extraction_schema:
        type: object
        properties: { person: string, cognitive_load: integer }
      output: frontmatter_update
    priority: 35
    depends_on: [direct-reports]

  - id: coaching-hypotheses
    category: enrichment
    description: >
      Active coaching docs for coaching-active people.
    source: "SP"
    check:
      type: min_count
      path: "10-work/coaching"
      filter: {}
      min: 1
    acquisition:
      method: nudge
      question: null
      extraction_schema: null
      output: null
    priority: 35
    depends_on: [direct-reports]

  - id: working-with-me
    category: enrichment
    description: >
      Operator management style document.
    source: "SP"
    check:
      type: file_exists
      path: "10-work/references/working-with-me.md"
    acquisition:
      method: interview
      question: >
        Let's create your "working with me" doc. How do you prefer to:
        - Communicate (async vs sync, written vs verbal)?
        - Receive feedback (direct, sandwiched, written)?
        - Make decisions (data-driven, intuition, consensus)?
        What should people know about your working style?
      extraction_schema:
        type: object
        properties:
          communication: string
          feedback_preference: string
          decision_style: string
          other_notes: string
      output: reference_doc
    priority: 35
    depends_on: []

  - id: feedback-style
    category: enrichment
    description: >
      Per-person feedback preferences documented.
    source: "SP"
    check:
      type: field_coverage
      path: "10-work/people"
      filter: { type: person, status: active }
      field: feedback-style
      threshold: 50
    acquisition:
      method: interview
      question: "How does {name} prefer to receive feedback? (direct, written, in-person, with examples, etc.)"
      extraction_schema:
        type: object
        properties: { person: string, feedback_style: string }
      output: frontmatter_update
    priority: 35
    depends_on: [direct-reports]

  - id: growth-vectors
    category: enrichment
    description: >
      Per-person development areas documented.
    source: "EP"
    check:
      type: field_coverage
      path: "10-work/people"
      filter: { type: person, status: active }
      field: growth-vector
      threshold: 50
    acquisition:
      method: interview
      question: "What's {name}'s primary growth vector right now? What skill or area are they actively developing?"
      extraction_schema:
        type: object
        properties: { person: string, growth_vector: string }
      output: frontmatter_update
    priority: 35
    depends_on: [direct-reports]

  - id: cross-team-deps
    category: enrichment
    description: >
      Cross-team interaction patterns and dependencies documented.
    source: "TT"
    check:
      type: file_exists
      path: "10-work/references/cross-team-deps.md"
    acquisition:
      method: interview
      question: >
        What are the key dependencies between your teams and other teams?
        Where do handoffs happen? Where are the friction points?
      extraction_schema:
        type: object
        properties:
          dependencies: { type: array, items: { from_team: string, to_team: string, dependency: string } }
      output: reference_doc
    priority: 35
    depends_on: [team-assignment]

  - id: team-api
    category: enrichment
    description: >
      Team boundaries and interfaces documented (Team API concept from Team Topologies).
    source: "TT"
    check:
      type: file_exists
      path: "10-work/references/team-api.md"
    acquisition:
      method: interview
      question: >
        For each team, what's their "API" — what do they provide to other teams?
        What do they consume? What's the preferred communication channel?
      extraction_schema:
        type: object
        properties:
          apis: { type: array, items: { team: string, provides: string, consumes: string, channel: string } }
      output: reference_doc
    priority: 35
    depends_on: [team-assignment]

  - id: performance-framework
    category: enrichment
    description: >
      Career ladder and performance designations documented.
    source: "SP, EP"
    check:
      type: file_exists
      path: "10-work/references/career-ladder.md"
    acquisition:
      method: interview
      question: >
        Does your company have a career ladder or performance framework?
        What are the levels? What's the promotion process?
      extraction_schema:
        type: object
        properties: { levels: string, process: string, notes: string }
      output: reference_doc
    priority: 35
    depends_on: []

  # ── External Data (not interview-acquirable) ──────────────────
  - id: dora-metrics
    category: enrichment
    description: >
      DORA metrics tracked (deployment frequency, MTTR, lead time, change failure rate).
    source: "EP"
    check:
      type: file_exists
      path: "10-work/references/dora-metrics.md"
    acquisition:
      method: interview
      question: "Do you track DORA metrics? Where? What are current values for your team(s)?"
      extraction_schema:
        type: object
        properties:
          tracked: boolean
          source: string
          notes: string
      output: reference_doc
    priority: 35
    depends_on: []
```

**Step 3: Commit**

```bash
cd <hapaxromana>
git add knowledge/management-sufficiency.yaml
git commit -m "feat: knowledge sufficiency model — 27 requirements across 3 tiers

Defines foundational (5), structural (10), and enrichment (12) knowledge
requirements derived from Team Topologies, Scaling People, and An
Elegant Puzzle. Each requirement has check type, acquisition method,
priority, and dependency chain."
```

---

## Task 2: Sufficiency Audit — Check Functions (TDD)

**Repo:** `<ai-agents>/`

**Files:**
- Create: `cockpit/data/knowledge_sufficiency.py`
- Create: `tests/test_knowledge_sufficiency.py`

This task implements the 5 check types. The audit orchestrator comes in Task 3.

**Step 1: Write the failing tests**

Create `tests/test_knowledge_sufficiency.py`:

```python
"""Tests for knowledge sufficiency audit check functions."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cockpit.data.knowledge_sufficiency import (
    KnowledgeGap,
    SufficiencyReport,
    check_file_exists,
    check_min_count,
    check_field_populated,
    check_field_coverage,
    check_any_content,
)


# ── file_exists ─────────────────────────────────────────────────

class TestCheckFileExists:
    def test_file_exists_with_content(self, tmp_path: Path) -> None:
        target = tmp_path / "10-work" / "references" / "company-mission.md"
        target.parent.mkdir(parents=True)
        target.write_text("---\ntype: reference\n---\nOur mission is to build great things." * 3)
        assert check_file_exists(tmp_path, "10-work/references/company-mission.md") is True

    def test_file_exists_empty(self, tmp_path: Path) -> None:
        target = tmp_path / "10-work" / "references" / "company-mission.md"
        target.parent.mkdir(parents=True)
        target.write_text("")
        assert check_file_exists(tmp_path, "10-work/references/company-mission.md") is False

    def test_file_exists_too_short(self, tmp_path: Path) -> None:
        target = tmp_path / "10-work" / "references" / "company-mission.md"
        target.parent.mkdir(parents=True)
        target.write_text("stub")
        assert check_file_exists(tmp_path, "10-work/references/company-mission.md") is False

    def test_file_missing(self, tmp_path: Path) -> None:
        assert check_file_exists(tmp_path, "10-work/references/company-mission.md") is False


# ── min_count ────────────────────────────────────────────────────

class TestCheckMinCount:
    def _make_person(self, folder: Path, name: str, team: str = "alpha", status: str = "active") -> None:
        f = folder / f"{name}.md"
        f.write_text(f"---\ntype: person\nstatus: {status}\nteam: {team}\n---\n# {name}\n")

    def test_min_count_met(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice")
        self._make_person(people, "bob")
        assert check_min_count(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            min_count=1,
        ) is True

    def test_min_count_not_met(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        assert check_min_count(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            min_count=1,
        ) is False

    def test_min_count_filters(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice", status="active")
        self._make_person(people, "charlie", status="departed")
        assert check_min_count(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            min_count=2,
        ) is False

    def test_min_count_no_filter(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice")
        self._make_person(people, "bob")
        assert check_min_count(
            tmp_path, "10-work/people",
            filter_fields={},
            min_count=2,
        ) is True


# ── field_populated ──────────────────────────────────────────────

class TestCheckFieldPopulated:
    def _make_person(self, folder: Path, name: str, **extra_fields: str) -> None:
        fm_lines = ["type: person", "status: active"]
        for k, v in extra_fields.items():
            fm_lines.append(f"{k}: {v}")
        f = folder / f"{name}.md"
        f.write_text(f"---\n" + "\n".join(fm_lines) + "\n---\n# " + name + "\n")

    def test_all_populated(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice", team="alpha")
        self._make_person(people, "bob", team="beta")
        assert check_field_populated(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            field="team",
        ) is True

    def test_some_missing(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice", team="alpha")
        self._make_person(people, "bob")  # no team
        assert check_field_populated(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            field="team",
        ) is False

    def test_empty_string_counts_as_missing(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice", team="")
        assert check_field_populated(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            field="team",
        ) is False

    def test_no_matching_notes(self, tmp_path: Path) -> None:
        """No matching notes = vacuously true (nothing to check)."""
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        assert check_field_populated(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            field="team",
        ) is True


# ── field_coverage ───────────────────────────────────────────────

class TestCheckFieldCoverage:
    def _make_person(self, folder: Path, name: str, **extra_fields: str) -> None:
        fm_lines = ["type: person", "status: active"]
        for k, v in extra_fields.items():
            fm_lines.append(f"{k}: {v}")
        f = folder / f"{name}.md"
        f.write_text("---\n" + "\n".join(fm_lines) + "\n---\n# " + name + "\n")

    def test_above_threshold(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice", **{"career-goal-3y": "lead a team"})
        self._make_person(people, "bob", **{"career-goal-3y": "IC track"})
        self._make_person(people, "charlie")  # missing
        # 2/3 = 66.7% >= 50%
        assert check_field_coverage(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            field="career-goal-3y",
            threshold=50,
        ) is True

    def test_below_threshold(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        self._make_person(people, "alice", **{"career-goal-3y": "lead a team"})
        self._make_person(people, "bob")
        self._make_person(people, "charlie")
        self._make_person(people, "dave")
        # 1/4 = 25% < 50%
        assert check_field_coverage(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            field="career-goal-3y",
            threshold=50,
        ) is False

    def test_no_matching_notes(self, tmp_path: Path) -> None:
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        assert check_field_coverage(
            tmp_path, "10-work/people",
            filter_fields={"type": "person", "status": "active"},
            field="career-goal-3y",
            threshold=50,
        ) is False  # 0 notes = no data = not satisfied


# ── any_content ──────────────────────────────────────────────────

class TestCheckAnyContent:
    def test_substantive(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntype: reference\n---\n" + "This is substantive content. " * 10)
        assert check_any_content(tmp_path, "doc.md") is True

    def test_stub_only(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("---\ntype: reference\n---\nTODO")
        assert check_any_content(tmp_path, "doc.md") is False

    def test_missing(self, tmp_path: Path) -> None:
        assert check_any_content(tmp_path, "doc.md") is False
```

**Step 2: Run tests to verify they fail**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py -v
```

Expected: FAIL — `ImportError: cannot import name 'check_file_exists' from 'cockpit.data.knowledge_sufficiency'`

**Step 3: Write the implementation**

Create `cockpit/data/knowledge_sufficiency.py`:

```python
"""Knowledge sufficiency audit — detects missing management knowledge in the vault.

Zero LLM calls. Reads a YAML knowledge model, scans vault state, and produces
a prioritized gap list. Integrates with the nudge system via collect_knowledge_gaps().

Design doc: docs/plans/2026-03-04-knowledge-sufficiency-design.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from shared.config import VAULT_PATH
from shared.vault_utils import parse_frontmatter


# ── Data classes ─────────────────────────────────────────────────

@dataclass
class KnowledgeGap:
    """A single unsatisfied knowledge requirement."""
    requirement_id: str
    category: str           # foundational | structural | enrichment
    priority: int           # 90, 60, or 35
    description: str
    acquisition_method: str # interview | nudge | external
    interview_question: str | None
    depends_on: list[str]
    satisfied: bool


@dataclass
class SufficiencyReport:
    """Result of a full knowledge audit."""
    gaps: list[KnowledgeGap]
    total_requirements: int
    satisfied_count: int
    foundational_complete: bool
    structural_complete: bool
    sufficiency_score: float  # 0.0 - 1.0


# ── Constants ────────────────────────────────────────────────────

KNOWLEDGE_MODEL_PATH = Path.home() / "projects" / "hapaxromana" / "knowledge" / "management-sufficiency.yaml"

PRIORITY_MAP = {
    "foundational": 90,
    "structural": 60,
    "enrichment": 35,
}

MIN_BODY_LENGTH = 50  # characters of body content to count as substantive


# ── Check functions ──────────────────────────────────────────────

def _get_matching_notes(
    vault_path: Path,
    rel_path: str,
    filter_fields: dict[str, str],
) -> list[tuple[Path, dict]]:
    """Glob markdown files in rel_path, filter by frontmatter fields."""
    folder = vault_path / rel_path
    if not folder.is_dir():
        return []

    results = []
    for md in sorted(folder.rglob("*.md")):
        fm = parse_frontmatter(md)
        if not fm:
            continue
        match = True
        for k, v in filter_fields.items():
            if str(fm.get(k, "")).lower() != str(v).lower():
                match = False
                break
        if match:
            results.append((md, fm))
    return results


def _get_body(path: Path) -> str:
    """Return the body of a markdown file (content after frontmatter)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""

    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].strip()
    return text.strip()


def check_file_exists(vault_path: Path, rel_path: str) -> bool:
    """Check that a file exists and has substantive content (>50 chars body)."""
    target = vault_path / rel_path
    if not target.is_file():
        return False
    body = _get_body(target)
    return len(body) > MIN_BODY_LENGTH


def check_min_count(
    vault_path: Path,
    rel_path: str,
    *,
    filter_fields: dict[str, str],
    min_count: int,
) -> bool:
    """Check that at least min_count notes match the filter."""
    matches = _get_matching_notes(vault_path, rel_path, filter_fields)
    return len(matches) >= min_count


def check_field_populated(
    vault_path: Path,
    rel_path: str,
    *,
    filter_fields: dict[str, str],
    field: str,
) -> bool:
    """Check that ALL matching notes have a non-empty value for field."""
    matches = _get_matching_notes(vault_path, rel_path, filter_fields)
    if not matches:
        return True  # vacuously true — no notes to check

    for _, fm in matches:
        val = fm.get(field)
        if val is None or str(val).strip() == "":
            return False
    return True


def check_field_coverage(
    vault_path: Path,
    rel_path: str,
    *,
    filter_fields: dict[str, str],
    field: str,
    threshold: float,
) -> bool:
    """Check that >= threshold% of matching notes have a non-empty field."""
    matches = _get_matching_notes(vault_path, rel_path, filter_fields)
    if not matches:
        return False  # no data = not satisfied

    populated = sum(
        1 for _, fm in matches
        if fm.get(field) is not None and str(fm.get(field)).strip() != ""
    )
    coverage = (populated / len(matches)) * 100
    return coverage >= threshold


def check_any_content(vault_path: Path, rel_path: str) -> bool:
    """Check that a file exists with substantive body content."""
    return check_file_exists(vault_path, rel_path)
```

**Step 4: Run tests to verify they pass**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py -v
```

Expected: All 15 tests PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/data/knowledge_sufficiency.py tests/test_knowledge_sufficiency.py
git commit -m "feat(sufficiency): knowledge audit check functions — 5 check types, 15 tests

Implements file_exists, min_count, field_populated, field_coverage,
and any_content check types for vault knowledge audit. Each scans
real vault frontmatter via shared.vault_utils."
```

---

## Task 3: Sufficiency Audit — Orchestrator (TDD)

**Repo:** `<ai-agents>/`

**Files:**
- Modify: `cockpit/data/knowledge_sufficiency.py`
- Modify: `tests/test_knowledge_sufficiency.py`

This task adds the audit orchestrator that loads the YAML model, runs all checks, and produces a `SufficiencyReport`.

**Step 1: Write the failing tests**

Append to `tests/test_knowledge_sufficiency.py`:

```python
from unittest.mock import patch


class TestRunAudit:
    """Test the full audit orchestrator."""

    MINIMAL_MODEL = {
        "version": 1,
        "requirements": [
            {
                "id": "test-file",
                "category": "foundational",
                "description": "Test file check",
                "source": "test",
                "check": {"type": "file_exists", "path": "10-work/references/test.md"},
                "acquisition": {
                    "method": "interview",
                    "question": "Tell me about test",
                    "extraction_schema": None,
                    "output": "reference_doc",
                },
                "priority": 100,
                "depends_on": [],
            },
            {
                "id": "test-count",
                "category": "structural",
                "description": "Test count check",
                "source": "test",
                "check": {
                    "type": "min_count",
                    "path": "10-work/people",
                    "filter": {"type": "person", "status": "active"},
                    "min": 1,
                },
                "acquisition": {
                    "method": "interview",
                    "question": "Who works here?",
                    "extraction_schema": None,
                    "output": "person_note",
                },
                "priority": 60,
                "depends_on": ["test-file"],
            },
        ],
    }

    def test_all_gaps(self, tmp_path: Path) -> None:
        from cockpit.data.knowledge_sufficiency import run_audit

        report = run_audit(self.MINIMAL_MODEL, vault_path=tmp_path)
        assert report.total_requirements == 2
        assert report.satisfied_count == 0
        assert report.sufficiency_score == 0.0
        assert report.foundational_complete is False
        assert len(report.gaps) == 2

    def test_partial_satisfaction(self, tmp_path: Path) -> None:
        from cockpit.data.knowledge_sufficiency import run_audit

        # Satisfy the file_exists check
        ref = tmp_path / "10-work" / "references" / "test.md"
        ref.parent.mkdir(parents=True)
        ref.write_text("---\ntype: reference\n---\n" + "Substantive content here. " * 5)

        report = run_audit(self.MINIMAL_MODEL, vault_path=tmp_path)
        assert report.satisfied_count == 1
        assert report.sufficiency_score == 0.5
        assert report.foundational_complete is True

    def test_all_satisfied(self, tmp_path: Path) -> None:
        from cockpit.data.knowledge_sufficiency import run_audit

        # Satisfy file_exists
        ref = tmp_path / "10-work" / "references" / "test.md"
        ref.parent.mkdir(parents=True)
        ref.write_text("---\ntype: reference\n---\n" + "Substantive content here. " * 5)

        # Satisfy min_count
        people = tmp_path / "10-work" / "people"
        people.mkdir(parents=True)
        (people / "alice.md").write_text("---\ntype: person\nstatus: active\nteam: alpha\n---\n# Alice\n")

        report = run_audit(self.MINIMAL_MODEL, vault_path=tmp_path)
        assert report.satisfied_count == 2
        assert report.sufficiency_score == 1.0
        assert report.structural_complete is True
        assert len([g for g in report.gaps if not g.satisfied]) == 0

    def test_gap_has_correct_fields(self, tmp_path: Path) -> None:
        from cockpit.data.knowledge_sufficiency import run_audit

        report = run_audit(self.MINIMAL_MODEL, vault_path=tmp_path)
        gap = report.gaps[0]  # test-file (foundational, priority 100)
        assert gap.requirement_id == "test-file"
        assert gap.category == "foundational"
        assert gap.priority == 100
        assert gap.acquisition_method == "interview"
        assert gap.interview_question == "Tell me about test"
        assert gap.satisfied is False

    def test_loads_yaml_file(self, tmp_path: Path) -> None:
        from cockpit.data.knowledge_sufficiency import run_audit, load_knowledge_model

        # Write a YAML file
        model_path = tmp_path / "model.yaml"
        model_path.write_text(yaml.dump(self.MINIMAL_MODEL))

        model = load_knowledge_model(model_path)
        assert model["version"] == 1
        assert len(model["requirements"]) == 2

    def test_derived_check_skipped(self, tmp_path: Path) -> None:
        """Derived checks (like team-sizing) are always unsatisfied but non-blocking."""
        from cockpit.data.knowledge_sufficiency import run_audit

        model = {
            "version": 1,
            "requirements": [
                {
                    "id": "test-derived",
                    "category": "structural",
                    "description": "Derived check",
                    "source": "test",
                    "check": {"type": "derived", "logic": "custom logic"},
                    "acquisition": {"method": "nudge", "question": None, "extraction_schema": None, "output": None},
                    "priority": 60,
                    "depends_on": [],
                },
            ],
        }
        report = run_audit(model, vault_path=tmp_path)
        assert report.gaps[0].satisfied is False
        assert report.gaps[0].acquisition_method == "nudge"


class TestCollectKnowledgeGaps:
    """Test the public entry point that loads the real YAML model."""

    def test_returns_report(self, tmp_path: Path) -> None:
        from cockpit.data.knowledge_sufficiency import collect_knowledge_gaps

        with patch("cockpit.data.knowledge_sufficiency.VAULT_PATH", tmp_path), \
             patch("cockpit.data.knowledge_sufficiency.KNOWLEDGE_MODEL_PATH") as mock_path:
            # Use a minimal model
            model_file = tmp_path / "model.yaml"
            model_file.write_text(yaml.dump(TestRunAudit.MINIMAL_MODEL))
            mock_path.__fspath__ = lambda self: str(model_file)
            mock_path.is_file.return_value = True

            # Patch load_knowledge_model to use our file
            with patch("cockpit.data.knowledge_sufficiency.load_knowledge_model") as mock_load:
                mock_load.return_value = TestRunAudit.MINIMAL_MODEL
                report = collect_knowledge_gaps()

        assert isinstance(report, SufficiencyReport)
        assert report.total_requirements == 2

    def test_missing_model_returns_empty(self) -> None:
        from cockpit.data.knowledge_sufficiency import collect_knowledge_gaps

        with patch("cockpit.data.knowledge_sufficiency.KNOWLEDGE_MODEL_PATH") as mock_path:
            mock_path.is_file.return_value = False
            report = collect_knowledge_gaps()

        assert report.total_requirements == 0
        assert report.sufficiency_score == 1.0
```

**Step 2: Run tests to verify they fail**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestRunAudit -v
uv run pytest tests/test_knowledge_sufficiency.py::TestCollectKnowledgeGaps -v
```

Expected: FAIL — `ImportError: cannot import name 'run_audit'`

**Step 3: Append orchestrator to `cockpit/data/knowledge_sufficiency.py`**

Add at the bottom of the file:

```python
# ── Model loading ────────────────────────────────────────────────

def load_knowledge_model(path: Path | None = None) -> dict:
    """Load the YAML knowledge model from disk."""
    target = path or KNOWLEDGE_MODEL_PATH
    with open(target, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Audit orchestrator ───────────────────────────────────────────

def _run_check(vault_path: Path, check: dict) -> bool:
    """Dispatch a single check against the vault."""
    check_type = check.get("type", "")

    if check_type == "file_exists":
        return check_file_exists(vault_path, check["path"])

    if check_type == "min_count":
        return check_min_count(
            vault_path,
            check["path"],
            filter_fields=check.get("filter", {}),
            min_count=check.get("min", 1),
        )

    if check_type == "field_populated":
        return check_field_populated(
            vault_path,
            check["path"],
            filter_fields=check.get("filter", {}),
            field=check["field"],
        )

    if check_type == "field_coverage":
        return check_field_coverage(
            vault_path,
            check["path"],
            filter_fields=check.get("filter", {}),
            field=check["field"],
            threshold=check.get("threshold", 50),
        )

    if check_type == "any_content":
        return check_any_content(vault_path, check["path"])

    # Unknown or 'derived' type — always unsatisfied
    return False


def run_audit(
    model: dict,
    *,
    vault_path: Path | None = None,
) -> SufficiencyReport:
    """Run the full knowledge sufficiency audit.

    Loads each requirement from the model, runs its check against the vault,
    and produces a SufficiencyReport with all gaps.
    """
    vp = vault_path or VAULT_PATH
    requirements = model.get("requirements", [])
    gaps: list[KnowledgeGap] = []

    for req in requirements:
        check = req.get("check", {})
        satisfied = _run_check(vp, check)
        acq = req.get("acquisition", {})

        gaps.append(KnowledgeGap(
            requirement_id=req["id"],
            category=req.get("category", "enrichment"),
            priority=req.get("priority", PRIORITY_MAP.get(req.get("category", "enrichment"), 35)),
            description=req.get("description", ""),
            acquisition_method=acq.get("method", "nudge"),
            interview_question=acq.get("question"),
            depends_on=req.get("depends_on", []),
            satisfied=satisfied,
        ))

    total = len(gaps)
    satisfied_count = sum(1 for g in gaps if g.satisfied)
    foundational = [g for g in gaps if g.category == "foundational"]
    structural = [g for g in gaps if g.category == "structural"]

    return SufficiencyReport(
        gaps=gaps,
        total_requirements=total,
        satisfied_count=satisfied_count,
        foundational_complete=all(g.satisfied for g in foundational) if foundational else True,
        structural_complete=all(g.satisfied for g in structural) if structural else True,
        sufficiency_score=satisfied_count / total if total > 0 else 1.0,
    )


def collect_knowledge_gaps(vault_path: Path | None = None) -> SufficiencyReport:
    """Public entry point — loads the real knowledge model and runs audit.

    Returns an empty report (score=1.0) if the model file is missing.
    Safe to call from the nudge system.
    """
    if not KNOWLEDGE_MODEL_PATH.is_file():
        return SufficiencyReport(
            gaps=[],
            total_requirements=0,
            satisfied_count=0,
            foundational_complete=True,
            structural_complete=True,
            sufficiency_score=1.0,
        )

    model = load_knowledge_model()
    return run_audit(model, vault_path=vault_path or VAULT_PATH)
```

**Step 4: Run tests to verify they pass**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py -v
```

Expected: All 22 tests PASS.

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/data/knowledge_sufficiency.py tests/test_knowledge_sufficiency.py
git commit -m "feat(sufficiency): audit orchestrator — load YAML model, run checks, produce report

Adds run_audit() and collect_knowledge_gaps() entry points.
Dispatches to 5 check types per requirement. Returns SufficiencyReport
with gap list, scores, and foundational/structural completion flags."
```

---

## Task 4: Nudge Integration (TDD)

**Repo:** `<ai-agents>/`

**Files:**
- Modify: `cockpit/data/nudges.py` (lines 29, 574-575)
- Modify: `tests/test_knowledge_sufficiency.py`

**Step 1: Write the failing test**

Append to `tests/test_knowledge_sufficiency.py`:

```python
from cockpit.data.nudges import Nudge


class TestSufficiencyNudges:
    """Test nudge generation from knowledge gaps."""

    def test_generates_nudges_for_unsatisfied_foundational(self) -> None:
        from cockpit.data.knowledge_sufficiency import gaps_to_nudges

        gaps = [
            KnowledgeGap(
                requirement_id="direct-reports",
                category="foundational",
                priority=100,
                description="Person notes for all direct reports",
                acquisition_method="interview",
                interview_question="Who are your direct reports?",
                depends_on=[],
                satisfied=False,
            ),
        ]
        nudges = gaps_to_nudges(gaps)
        assert len(nudges) == 1
        assert nudges[0].category == "knowledge"
        assert nudges[0].priority_score == 100
        assert nudges[0].priority_label == "high"
        assert "/setup direct-reports" in nudges[0].command_hint

    def test_skips_satisfied(self) -> None:
        from cockpit.data.knowledge_sufficiency import gaps_to_nudges

        gaps = [
            KnowledgeGap(
                requirement_id="direct-reports",
                category="foundational",
                priority=100,
                description="Already have direct reports",
                acquisition_method="interview",
                interview_question="Who are your direct reports?",
                depends_on=[],
                satisfied=True,
            ),
        ]
        nudges = gaps_to_nudges(gaps)
        assert len(nudges) == 0

    def test_skips_blocked_by_dependency(self) -> None:
        from cockpit.data.knowledge_sufficiency import gaps_to_nudges

        gaps = [
            KnowledgeGap(
                requirement_id="direct-reports",
                category="foundational",
                priority=100,
                description="Direct reports",
                acquisition_method="interview",
                interview_question="Who?",
                depends_on=[],
                satisfied=False,
            ),
            KnowledgeGap(
                requirement_id="team-assignment",
                category="foundational",
                priority=95,
                description="Team assignments",
                acquisition_method="interview",
                interview_question="Which team?",
                depends_on=["direct-reports"],
                satisfied=False,
            ),
        ]
        nudges = gaps_to_nudges(gaps)
        # team-assignment depends on direct-reports which is unsatisfied → skip
        assert len(nudges) == 1
        assert nudges[0].source_id == "knowledge:direct-reports"

    def test_priority_labels(self) -> None:
        from cockpit.data.knowledge_sufficiency import gaps_to_nudges

        gaps = [
            KnowledgeGap("f", "foundational", 90, "F", "interview", "Q?", [], False),
            KnowledgeGap("s", "structural", 60, "S", "interview", "Q?", [], False),
            KnowledgeGap("e", "enrichment", 35, "E", "interview", "Q?", [], False),
        ]
        nudges = gaps_to_nudges(gaps)
        labels = {n.source_id.split(":")[1]: n.priority_label for n in nudges}
        assert labels["f"] == "high"
        assert labels["s"] == "medium"
        assert labels["e"] == "low"

    def test_nudge_method_nudge(self) -> None:
        """Non-interview gaps get different suggested_action."""
        from cockpit.data.knowledge_sufficiency import gaps_to_nudges

        gaps = [
            KnowledgeGap("x", "structural", 60, "Meeting notes", "nudge", None, [], False),
        ]
        nudges = gaps_to_nudges(gaps)
        assert len(nudges) == 1
        assert "/setup" not in nudges[0].command_hint
```

**Step 2: Run tests to verify they fail**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestSufficiencyNudges -v
```

Expected: FAIL — `ImportError: cannot import name 'gaps_to_nudges'`

**Step 3: Add `gaps_to_nudges` to `cockpit/data/knowledge_sufficiency.py`**

Append to the file:

```python
# ── Nudge generation ─────────────────────────────────────────────

def gaps_to_nudges(gaps: list[KnowledgeGap]) -> list["Nudge"]:
    """Convert unsatisfied knowledge gaps to nudges.

    Skips satisfied gaps and gaps whose dependencies are unsatisfied.
    Returns Nudge objects compatible with the nudge system.
    """
    from cockpit.data.nudges import Nudge

    satisfied_ids = {g.requirement_id for g in gaps if g.satisfied}
    nudges: list[Nudge] = []

    for gap in gaps:
        if gap.satisfied:
            continue

        # Skip if any dependency is unsatisfied
        if any(dep not in satisfied_ids for dep in gap.depends_on):
            continue

        label = (
            "high" if gap.category == "foundational"
            else "medium" if gap.category == "structural"
            else "low"
        )

        if gap.acquisition_method == "interview":
            action = f"Run /setup {gap.requirement_id} in Obsidian chat"
            hint = f"/setup {gap.requirement_id}"
        else:
            action = f"Create: {gap.description.strip()}"
            hint = ""

        nudges.append(Nudge(
            category="knowledge",
            priority_score=gap.priority,
            priority_label=label,
            title=f"Missing: {gap.description.strip()[:80]}",
            detail=gap.description.strip(),
            suggested_action=action,
            command_hint=hint,
            source_id=f"knowledge:{gap.requirement_id}",
        ))

    return nudges
```

**Step 4: Modify `cockpit/data/nudges.py` to integrate the new collector**

In `nudges.py`, add the new collector function after `_collect_sufficiency_nudges` (after line 498):

```python
def _collect_knowledge_sufficiency_nudges(nudges: list[Nudge]) -> None:
    """Generate nudges from knowledge sufficiency gaps."""
    try:
        from cockpit.data.knowledge_sufficiency import collect_knowledge_gaps, gaps_to_nudges
        report = collect_knowledge_gaps()
        nudges.extend(gaps_to_nudges(report.gaps))
    except Exception:
        pass
```

In `collect_nudges()`, add the call after `_collect_sufficiency_nudges(nudges)` (after line 575):

```python
    _collect_knowledge_sufficiency_nudges(nudges)
```

Update the Nudge docstring category list (line 29) to include `"knowledge"`:

```python
    category: str        # "health" | "briefing" | "readiness" | "profile" | "scout" | "drift" | "action" | "knowledge"
```

**Step 5: Run tests to verify they pass**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py -v
```

Expected: All 27 tests PASS.

**Step 6: Run full test suite**

```bash
cd <ai-agents>
uv run pytest --tb=short -q
```

Expected: All existing tests still pass (no regressions). The new knowledge sufficiency collector is wrapped in try/except so it won't break if YAML file is missing.

**Step 7: Commit**

```bash
cd <ai-agents>
git add cockpit/data/knowledge_sufficiency.py cockpit/data/nudges.py tests/test_knowledge_sufficiency.py
git commit -m "feat(sufficiency): knowledge gap nudge integration — priority-ordered, dependency-aware

Adds gaps_to_nudges() that converts unsatisfied knowledge gaps to
nudges. Skips gaps blocked by unsatisfied dependencies. Integrates
with nudge collector as 'knowledge' category. Foundational=high,
structural=medium, enrichment=low."
```

---

## Task 5: Interview Question Templates (Obsidian Plugin)

**Repo:** `<obsidian-hapax>/`

**Files:**
- Create: `src/interview/knowledge-model.ts`
- Create: `src/interview/questions.ts`

No test framework in this repo — verify via `pnpm run build`.

**Step 1: Create the interview directory**

```bash
mkdir -p <obsidian-hapax>/src/interview
```

**Step 2: Create the knowledge model TypeScript module**

Create `src/interview/knowledge-model.ts`. This is the bundled version of the YAML model — the plugin cannot read YAML at runtime. Contains the same requirements but typed.

```typescript
/**
 * Knowledge model — bundled version of hapaxromana/knowledge/management-sufficiency.yaml.
 *
 * This is the single source of interview questions and requirement metadata
 * for the plugin. When the YAML model changes, this file must be updated.
 */

export interface Requirement {
  id: string;
  category: "foundational" | "structural" | "enrichment";
  description: string;
  source: string;
  check: {
    type: "file_exists" | "min_count" | "field_populated" | "field_coverage" | "any_content" | "derived";
    path?: string;
    filter?: Record<string, string>;
    field?: string;
    min?: number;
    threshold?: number;
  };
  acquisition: {
    method: "interview" | "nudge" | "external";
    question: string | null;
    outputType: "person_note" | "reference_doc" | "frontmatter_update" | null;
    personScoped: boolean; // true = ask per-person, false = ask once
  };
  priority: number;
  dependsOn: string[];
}

export const REQUIREMENTS: Requirement[] = [
  // ── Foundational ──────────────────────────────────────────
  {
    id: "direct-reports",
    category: "foundational",
    description: "Person notes for all direct reports with type, role, team, status.",
    source: "All 3 books",
    check: { type: "min_count", path: "10-work/people", filter: { type: "person", status: "active" }, min: 1 },
    acquisition: {
      method: "interview",
      question: "Let's set up your team. Who are your direct reports? For each person, I need their name, role, and which team they're on.",
      outputType: "person_note",
      personScoped: false,
    },
    priority: 100,
    dependsOn: [],
  },
  {
    id: "team-assignment",
    category: "foundational",
    description: "Every active person note has a team field populated.",
    source: "TT",
    check: { type: "field_populated", path: "10-work/people", filter: { type: "person", status: "active" }, field: "team" },
    acquisition: {
      method: "interview",
      question: "What team is {name} on?",
      outputType: "frontmatter_update",
      personScoped: true,
    },
    priority: 95,
    dependsOn: ["direct-reports"],
  },
  {
    id: "1on1-cadence",
    category: "foundational",
    description: "Every active person note has cadence set.",
    source: "SP, EP",
    check: { type: "field_populated", path: "10-work/people", filter: { type: "person", status: "active" }, field: "cadence" },
    acquisition: {
      method: "interview",
      question: "How often do you meet with {name} for 1:1s? (weekly, biweekly, monthly)",
      outputType: "frontmatter_update",
      personScoped: true,
    },
    priority: 95,
    dependsOn: ["direct-reports"],
  },
  {
    id: "manager-context",
    category: "foundational",
    description: "Operator's manager is documented as a person note.",
    source: "SP",
    check: { type: "min_count", path: "10-work/people", filter: { type: "person", role: "manager" }, min: 1 },
    acquisition: {
      method: "interview",
      question: "Who is your manager? What's their role/title?",
      outputType: "person_note",
      personScoped: false,
    },
    priority: 90,
    dependsOn: [],
  },
  {
    id: "company-mission",
    category: "foundational",
    description: "Company mission documented.",
    source: "SP",
    check: { type: "file_exists", path: "10-work/references/company-mission.md" },
    acquisition: {
      method: "interview",
      question: "What's your company's mission or purpose statement? Even a rough version helps.",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 90,
    dependsOn: [],
  },

  // ── Structural ────────────────────────────────────────────
  {
    id: "operating-principles",
    category: "structural",
    description: "Company or team values/operating principles documented.",
    source: "SP",
    check: { type: "file_exists", path: "10-work/references/operating-principles.md" },
    acquisition: {
      method: "interview",
      question: "Does your company or team have documented values or operating principles? What are they?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 60,
    dependsOn: [],
  },
  {
    id: "org-structure",
    category: "structural",
    description: "Org hierarchy documented — reporting lines, spans of control.",
    source: "EP",
    check: { type: "file_exists", path: "10-work/references/org-chart.md" },
    acquisition: {
      method: "interview",
      question: "Let's map your org structure. Who reports to you? Who do you report to? Are there peer managers? What's the broader reporting chain?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 60,
    dependsOn: ["direct-reports", "manager-context"],
  },
  {
    id: "team-topology-type",
    category: "structural",
    description: "Team type set for each team.",
    source: "TT",
    check: { type: "field_coverage", path: "10-work/people", filter: { type: "person", status: "active" }, field: "team-type", threshold: 80 },
    acquisition: {
      method: "interview",
      question: "What type of team is {team}? Options: stream-aligned (delivers end-to-end value), enabling (helps others adopt capabilities), complicated-subsystem (specialist domain), platform (internal services).",
      outputType: "frontmatter_update",
      personScoped: false,
    },
    priority: 60,
    dependsOn: ["direct-reports", "team-assignment"],
  },
  {
    id: "team-interaction-modes",
    category: "structural",
    description: "Interaction modes between team pairs documented.",
    source: "TT",
    check: { type: "file_exists", path: "10-work/references/team-interactions.md" },
    acquisition: {
      method: "interview",
      question: "How do your teams interact with each other? For each pair of teams that work together, what's the interaction mode? (collaboration, X-as-a-Service, facilitating)",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 60,
    dependsOn: ["team-topology-type"],
  },
  {
    id: "operating-cadence",
    category: "structural",
    description: "Meeting cadences documented.",
    source: "SP",
    check: { type: "file_exists", path: "10-work/references/operating-cadence.md" },
    acquisition: {
      method: "interview",
      question: "What recurring meetings do you have? For each, what's the purpose, frequency, and attendees?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 60,
    dependsOn: [],
  },
  {
    id: "key-stakeholders",
    category: "structural",
    description: "Person notes for non-report stakeholders.",
    source: "SP",
    check: { type: "min_count", path: "10-work/people", filter: { type: "person", role: "stakeholder" }, min: 1 },
    acquisition: {
      method: "interview",
      question: "Who are key stakeholders outside your direct reports? Think: skip-levels, cross-functional partners, executives you interact with regularly.",
      outputType: "person_note",
      personScoped: false,
    },
    priority: 60,
    dependsOn: [],
  },
  {
    id: "decision-approach",
    category: "structural",
    description: "Decision framework documented.",
    source: "SP",
    check: { type: "file_exists", path: "10-work/references/decision-framework.md" },
    acquisition: {
      method: "interview",
      question: "How are decisions typically made on your team? Is there a framework (RAPID, DACI, consensus)? Who has decision rights for different domains?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 60,
    dependsOn: [],
  },
  {
    id: "team-charters",
    category: "structural",
    description: "Per-team mission and scope documented.",
    source: "SP",
    check: { type: "file_exists", path: "10-work/references/team-charters.md" },
    acquisition: {
      method: "interview",
      question: "For each team you manage, what's their mission and scope? What are they responsible for? What's explicitly outside their scope?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 60,
    dependsOn: ["team-assignment"],
  },

  // ── Enrichment ────────────────────────────────────────────
  {
    id: "career-goals",
    category: "enrichment",
    description: "Person notes have 3-year career goal documented.",
    source: "SP, EP",
    check: { type: "field_coverage", path: "10-work/people", filter: { type: "person", status: "active" }, field: "career-goal-3y", threshold: 50 },
    acquisition: {
      method: "interview",
      question: "What's {name}'s career goal for the next 3 years, as you understand it?",
      outputType: "frontmatter_update",
      personScoped: true,
    },
    priority: 35,
    dependsOn: ["direct-reports"],
  },
  {
    id: "skill-will",
    category: "enrichment",
    description: "Person notes have skill-level and will-signal populated.",
    source: "SP",
    check: { type: "field_coverage", path: "10-work/people", filter: { type: "person", status: "active" }, field: "skill-level", threshold: 50 },
    acquisition: {
      method: "interview",
      question: "For {name}, how would you assess their skill level (developing, career, advanced, expert) and will/motivation signal (high, moderate, low)?",
      outputType: "frontmatter_update",
      personScoped: true,
    },
    priority: 35,
    dependsOn: ["direct-reports"],
  },
  {
    id: "cognitive-load",
    category: "enrichment",
    description: "Person notes have numeric cognitive-load (1-5).",
    source: "TT, EP",
    check: { type: "field_coverage", path: "10-work/people", filter: { type: "person", status: "active" }, field: "cognitive-load", threshold: 80 },
    acquisition: {
      method: "interview",
      question: "For {name}, how would you rate their cognitive load right now on a 1-5 scale? 1 = very light, 3 = balanced, 5 = overwhelmed",
      outputType: "frontmatter_update",
      personScoped: true,
    },
    priority: 35,
    dependsOn: ["direct-reports"],
  },
  {
    id: "working-with-me",
    category: "enrichment",
    description: "Operator management style document.",
    source: "SP",
    check: { type: "file_exists", path: "10-work/references/working-with-me.md" },
    acquisition: {
      method: "interview",
      question: "Let's create your \"working with me\" doc. How do you prefer to communicate, receive feedback, and make decisions? What should people know about your working style?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 35,
    dependsOn: [],
  },
  {
    id: "feedback-style",
    category: "enrichment",
    description: "Per-person feedback preferences documented.",
    source: "SP",
    check: { type: "field_coverage", path: "10-work/people", filter: { type: "person", status: "active" }, field: "feedback-style", threshold: 50 },
    acquisition: {
      method: "interview",
      question: "How does {name} prefer to receive feedback? (direct, written, in-person, with examples, etc.)",
      outputType: "frontmatter_update",
      personScoped: true,
    },
    priority: 35,
    dependsOn: ["direct-reports"],
  },
  {
    id: "growth-vectors",
    category: "enrichment",
    description: "Per-person development areas documented.",
    source: "EP",
    check: { type: "field_coverage", path: "10-work/people", filter: { type: "person", status: "active" }, field: "growth-vector", threshold: 50 },
    acquisition: {
      method: "interview",
      question: "What's {name}'s primary growth vector right now? What skill or area are they actively developing?",
      outputType: "frontmatter_update",
      personScoped: true,
    },
    priority: 35,
    dependsOn: ["direct-reports"],
  },
  {
    id: "performance-framework",
    category: "enrichment",
    description: "Career ladder and performance designations documented.",
    source: "SP, EP",
    check: { type: "file_exists", path: "10-work/references/career-ladder.md" },
    acquisition: {
      method: "interview",
      question: "Does your company have a career ladder or performance framework? What are the levels? What's the promotion process?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 35,
    dependsOn: [],
  },
  {
    id: "dora-metrics",
    category: "enrichment",
    description: "DORA metrics tracked.",
    source: "EP",
    check: { type: "file_exists", path: "10-work/references/dora-metrics.md" },
    acquisition: {
      method: "interview",
      question: "Do you track DORA metrics? Where? What are current values for your team(s)?",
      outputType: "reference_doc",
      personScoped: false,
    },
    priority: 35,
    dependsOn: [],
  },
];

export function getInterviewableRequirements(): Requirement[] {
  return REQUIREMENTS.filter((r) => r.acquisition.method === "interview");
}
```

**Step 3: Create the questions module**

Create `src/interview/questions.ts`:

```typescript
/**
 * Question templates for the knowledge sufficiency interview.
 *
 * Maps requirement IDs to conversational questions with follow-up prompts
 * and extraction instructions.
 */
import type { Requirement } from "./knowledge-model";
import { REQUIREMENTS } from "./knowledge-model";

export interface QuestionContext {
  requirement: Requirement;
  question: string;          // Resolved question text (with {name}/{team} substituted)
  followUp: string;          // Follow-up prompt if answer is incomplete
  extractionPrompt: string;  // Prompt sent to LLM for structured extraction
}

/**
 * Build a question context for a requirement.
 * For person-scoped questions, pass the person name to substitute {name}.
 * For team-scoped questions, pass the team name to substitute {team}.
 */
export function buildQuestion(
  req: Requirement,
  context?: { name?: string; team?: string }
): QuestionContext {
  let question = req.acquisition.question || req.description;
  if (context?.name) {
    question = question.replace(/\{name\}/g, context.name);
  }
  if (context?.team) {
    question = question.replace(/\{team\}/g, context.team);
  }

  const followUp = getFollowUp(req.id);
  const extractionPrompt = buildExtractionPrompt(req, question);

  return { requirement: req, question, followUp, extractionPrompt };
}

function getFollowUp(requirementId: string): string {
  const followUps: Record<string, string> = {
    "direct-reports": "Can you list any more? I want to make sure I have everyone.",
    "team-assignment": "Got it. Are there any people on multiple teams or in transition?",
    "1on1-cadence": "And do you have a preferred day/time for this 1:1?",
    "manager-context": "How often do you meet with your manager?",
    "company-mission": "Is there a more formal version, or is this the working statement?",
    "operating-principles": "Are there any unwritten norms that matter as much as the formal values?",
    "org-structure": "Are there any dotted-line relationships I should know about?",
    "key-stakeholders": "Anyone else who significantly impacts your team's work?",
  };
  return followUps[requirementId] || "Anything else to add on this topic?";
}

function buildExtractionPrompt(req: Requirement, question: string): string {
  const outputDesc = req.acquisition.outputType === "person_note"
    ? "person notes with frontmatter fields: name, type (person), role, team, status (active), cadence"
    : req.acquisition.outputType === "frontmatter_update"
    ? "frontmatter field updates"
    : "a reference document with the extracted content";

  return `Extract structured data from the user's answer. The user was asked:
"${question}"

Return valid JSON. Only extract what was explicitly stated. Do not infer, guess, or add information.
If the answer is incomplete, include "incomplete": true in your response.

The extracted data will be used to create ${outputDesc}.`;
}

/**
 * Get the next question to ask based on unsatisfied requirements.
 * Respects dependency ordering — won't ask about team-assignment
 * if direct-reports hasn't been satisfied yet.
 */
export function getNextQuestion(
  satisfiedIds: Set<string>,
  skippedIds: Set<string>,
  context?: { name?: string; team?: string }
): QuestionContext | null {
  const interviewable = REQUIREMENTS.filter(
    (r) => r.acquisition.method === "interview"
  );

  // Sort by priority descending
  const sorted = [...interviewable].sort((a, b) => b.priority - a.priority);

  for (const req of sorted) {
    // Skip already satisfied or skipped
    if (satisfiedIds.has(req.id) || skippedIds.has(req.id)) continue;

    // Check dependencies are satisfied
    const depsReady = req.dependsOn.every((dep) => satisfiedIds.has(dep));
    if (!depsReady) continue;

    return buildQuestion(req, context);
  }

  return null;
}
```

**Step 4: Verify build**

```bash
cd <obsidian-hapax>
pnpm run build
```

Expected: Build succeeds (unused modules are tree-shaken but must compile).

**Step 5: Commit**

```bash
cd <obsidian-hapax>
git add src/interview/knowledge-model.ts src/interview/questions.ts
git commit -m "feat(interview): knowledge model + question templates

Bundles 21 interview-acquirable requirements as typed constants.
Question builder resolves {name}/{team} placeholders and generates
LLM extraction prompts. Dependency-aware next-question selection."
```

---

## Task 6: Interview Vault Writer (Obsidian Plugin)

**Repo:** `<obsidian-hapax>/`

**Files:**
- Create: `src/interview/vault-writer.ts`

**Step 1: Write the vault writer**

Create `src/interview/vault-writer.ts`:

```typescript
/**
 * Vault writer for interview-extracted data.
 *
 * Creates or updates vault notes via the Obsidian API.
 * Three output types: person_note, reference_doc, frontmatter_update.
 *
 * Respects mg-boundary-001/002 — writes factual data only,
 * never generates management advice or feedback language.
 */
import { App, TFile, Notice, normalizePath } from "obsidian";

export interface PersonData {
  name: string;
  role?: string;
  team?: string;
  status?: string;
  cadence?: string;
  [key: string]: string | number | boolean | undefined;
}

export interface ReferenceDocData {
  id: string;
  title: string;
  content: string;
}

/**
 * Create a person note in 10-work/people/{name}.md
 */
export async function createPersonNote(
  app: App,
  data: PersonData
): Promise<TFile | null> {
  const kebabName = data.name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-");
  const path = normalizePath(`10-work/people/${kebabName}.md`);

  // Don't overwrite existing notes
  const existing = app.vault.getAbstractFileByPath(path);
  if (existing instanceof TFile) {
    new Notice(`Person note already exists: ${path}`);
    return existing;
  }

  // Ensure directory exists
  const dir = normalizePath("10-work/people");
  if (!app.vault.getAbstractFileByPath(dir)) {
    await app.vault.createFolder(dir);
  }

  const frontmatter = [
    "---",
    "type: person",
    `status: ${data.status || "active"}`,
    `role: ${data.role || "direct-report"}`,
    `team: ${data.team || ""}`,
    `cadence: ${data.cadence || ""}`,
    `cognitive-load: `,
    `growth-vector: `,
    `feedback-style: `,
    `coaching-active: false`,
    `skill-level: `,
    `will-signal: `,
    `career-goal-3y: `,
    `current-gaps: `,
    `current-focus: `,
    `last-career-convo: `,
    `team-type: `,
    `interaction-mode: `,
    "---",
  ].join("\n");

  const body = `\n# ${data.name}\n\n## Contact\n\n## Status\n\n## Notes\n`;
  const content = frontmatter + body;

  try {
    const file = await app.vault.create(path, content);
    new Notice(`Created person note: ${data.name}`);
    return file;
  } catch (err: any) {
    new Notice(`Failed to create person note: ${err.message}`);
    return null;
  }
}

/**
 * Create a reference document in 10-work/references/{id}.md
 */
export async function createReferenceDoc(
  app: App,
  data: ReferenceDocData
): Promise<TFile | null> {
  const path = normalizePath(`10-work/references/${data.id}.md`);

  // Don't overwrite existing
  const existing = app.vault.getAbstractFileByPath(path);
  if (existing instanceof TFile) {
    new Notice(`Reference doc already exists: ${path}`);
    return existing;
  }

  // Ensure directory exists
  const dir = normalizePath("10-work/references");
  if (!app.vault.getAbstractFileByPath(dir)) {
    await app.vault.createFolder(dir);
  }

  const content = [
    "---",
    "type: reference",
    `date: ${new Date().toISOString().split("T")[0]}`,
    "---",
    "",
    `# ${data.title}`,
    "",
    data.content,
    "",
  ].join("\n");

  try {
    const file = await app.vault.create(path, content);
    new Notice(`Created reference doc: ${data.title}`);
    return file;
  } catch (err: any) {
    new Notice(`Failed to create reference doc: ${err.message}`);
    return null;
  }
}

/**
 * Update frontmatter fields on an existing person note.
 */
export async function updateFrontmatter(
  app: App,
  personName: string,
  fields: Record<string, string | number | boolean>
): Promise<boolean> {
  const kebabName = personName
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-");
  const path = normalizePath(`10-work/people/${kebabName}.md`);

  const file = app.vault.getAbstractFileByPath(path);
  if (!(file instanceof TFile)) {
    new Notice(`Person note not found: ${personName}`);
    return false;
  }

  try {
    await app.fileManager.processFrontMatter(file, (fm) => {
      for (const [key, value] of Object.entries(fields)) {
        fm[key] = value;
      }
    });
    new Notice(`Updated ${personName}: ${Object.keys(fields).join(", ")}`);
    return true;
  } catch (err: any) {
    new Notice(`Failed to update frontmatter: ${err.message}`);
    return false;
  }
}
```

**Step 2: Verify build**

```bash
cd <obsidian-hapax>
pnpm run build
```

Expected: Build succeeds.

**Step 3: Commit**

```bash
cd <obsidian-hapax>
git add src/interview/vault-writer.ts
git commit -m "feat(interview): vault writer — person notes, reference docs, frontmatter updates

Creates vault notes via Obsidian API (app.vault.create, processFrontMatter).
Three output types matching knowledge model: person_note, reference_doc,
frontmatter_update. Respects mg-boundary-001/002."
```

---

## Task 7: Interview Extractor (Obsidian Plugin)

**Repo:** `<obsidian-hapax>/`

**Files:**
- Create: `src/interview/extractor.ts`

**Step 1: Write the extractor**

Create `src/interview/extractor.ts`:

```typescript
/**
 * LLM structured extraction for interview answers.
 *
 * Sends user answer + extraction prompt to the configured LLM provider.
 * Extracts structured JSON matching the requirement's schema.
 *
 * Respects mg-boundary-001/002 — extraction only, never generates
 * management advice or feedback language.
 */
import type { HapaxSettings } from "../types";
import { createProvider } from "../providers";

export interface ExtractionResult {
  data: Record<string, unknown>;
  incomplete: boolean;
  raw: string;
}

/**
 * Extract structured data from a user's interview answer.
 *
 * @param answer - The user's natural language answer
 * @param extractionPrompt - The prompt describing what to extract
 * @param settings - LLM provider settings
 * @returns Parsed extraction result, or null on failure
 */
export async function extractFromAnswer(
  answer: string,
  extractionPrompt: string,
  settings: HapaxSettings
): Promise<ExtractionResult | null> {
  const provider = createProvider(settings);

  const messages = [
    {
      role: "system",
      content: `You are a structured data extractor. ${extractionPrompt}

CRITICAL RULES:
- Return ONLY valid JSON, no markdown fences, no explanation
- Only extract what was explicitly stated
- Do not infer, guess, or add information
- If the answer is incomplete, set "incomplete": true
- Never generate feedback language, coaching advice, or management recommendations`,
    },
    {
      role: "user",
      content: answer,
    },
  ];

  let fullResponse = "";
  try {
    for await (const chunk of provider.streamChat(messages, settings.model)) {
      fullResponse += chunk;
    }
  } catch (err: any) {
    console.error("Extraction failed:", err.message);
    return null;
  }

  // Parse JSON from response — handle markdown fences if present
  const jsonStr = fullResponse
    .replace(/^```json?\n?/m, "")
    .replace(/\n?```$/m, "")
    .trim();

  try {
    const parsed = JSON.parse(jsonStr);
    return {
      data: parsed,
      incomplete: parsed.incomplete === true,
      raw: fullResponse,
    };
  } catch {
    console.error("Failed to parse extraction JSON:", fullResponse);
    return null;
  }
}
```

**Step 2: Verify build**

```bash
cd <obsidian-hapax>
pnpm run build
```

Expected: Build succeeds.

**Step 3: Commit**

```bash
cd <obsidian-hapax>
git add src/interview/extractor.ts
git commit -m "feat(interview): LLM structured extractor — JSON extraction from natural language

Sends answer + extraction prompt to configured LLM provider.
Parses structured JSON response. Handles markdown fences in output.
Respects mg-boundary-001/002 — extraction only, no advice."
```

---

## Task 8: Interview Engine State Machine (Obsidian Plugin)

**Repo:** `<obsidian-hapax>/`

**Files:**
- Create: `src/interview/engine.ts`

**Step 1: Write the engine**

Create `src/interview/engine.ts`:

```typescript
/**
 * Interview engine — state machine for guided knowledge acquisition.
 *
 * Manages the interview lifecycle: detecting gaps, presenting questions,
 * extracting answers, writing to vault, and tracking progress.
 *
 * State persists in plugin data.json via Obsidian Sync.
 */
import { App, TFile, Notice } from "obsidian";
import type { HapaxSettings } from "../types";
import { REQUIREMENTS, getInterviewableRequirements, type Requirement } from "./knowledge-model";
import { getNextQuestion, buildQuestion, type QuestionContext } from "./questions";
import { extractFromAnswer, type ExtractionResult } from "./extractor";
import {
  createPersonNote,
  createReferenceDoc,
  updateFrontmatter,
  type PersonData,
  type ReferenceDocData,
} from "./vault-writer";

// ── State ───────────────────────────────────────────────────────

export interface InterviewState {
  active: boolean;
  currentRequirement: string | null;
  completed: string[];
  skipped: string[];
  lastUpdated: string;
}

const EMPTY_STATE: InterviewState = {
  active: false,
  currentRequirement: null,
  completed: [],
  skipped: [],
  lastUpdated: new Date().toISOString(),
};

// ── Progress ────────────────────────────────────────────────────

export interface InterviewProgress {
  foundational: { done: number; total: number };
  structural: { done: number; total: number };
  enrichment: { done: number; total: number };
  foundationalComplete: boolean;
}

// ── Engine ──────────────────────────────────────────────────────

export class InterviewEngine {
  private app: App;
  private settings: HapaxSettings;
  private state: InterviewState;
  private loadData: () => Promise<Record<string, unknown>>;
  private saveData: (data: Record<string, unknown>) => Promise<void>;

  constructor(
    app: App,
    settings: HapaxSettings,
    loadData: () => Promise<Record<string, unknown>>,
    saveData: (data: Record<string, unknown>) => Promise<void>
  ) {
    this.app = app;
    this.settings = settings;
    this.state = { ...EMPTY_STATE };
    this.loadData = loadData;
    this.saveData = saveData;
  }

  // ── State persistence ───────────────────────────────────────

  async load(): Promise<void> {
    const data = await this.loadData();
    const stored = data?.interviewState as InterviewState | undefined;
    if (stored) {
      this.state = { ...EMPTY_STATE, ...stored };
    }
  }

  async save(): Promise<void> {
    const data = await this.loadData();
    data.interviewState = { ...this.state, lastUpdated: new Date().toISOString() };
    await this.saveData(data);
  }

  // ── Vault scanning (local sufficiency check) ────────────────

  async scanVaultSatisfaction(): Promise<Set<string>> {
    const satisfied = new Set<string>(this.state.completed);

    for (const req of REQUIREMENTS) {
      if (satisfied.has(req.id)) continue;
      if (await this.checkRequirement(req)) {
        satisfied.add(req.id);
      }
    }

    return satisfied;
  }

  private async checkRequirement(req: Requirement): Promise<boolean> {
    const check = req.check;

    if (check.type === "file_exists" && check.path) {
      const file = this.app.vault.getAbstractFileByPath(check.path);
      if (!(file instanceof TFile)) return false;
      const content = await this.app.vault.cachedRead(file);
      // Strip frontmatter, check body length
      const body = content.replace(/^---[\s\S]*?---\n?/, "").trim();
      return body.length > 50;
    }

    if (check.type === "min_count" && check.path) {
      const files = this.app.vault.getMarkdownFiles().filter(
        (f) => f.path.startsWith(check.path!)
      );
      if (files.length === 0) return false;

      let count = 0;
      for (const file of files) {
        const cache = this.app.metadataCache.getFileCache(file);
        const fm = cache?.frontmatter;
        if (!fm) continue;
        const filter = check.filter || {};
        const matches = Object.entries(filter).every(
          ([k, v]) => String(fm[k] || "").toLowerCase() === String(v).toLowerCase()
        );
        if (matches) count++;
      }
      return count >= (check.min || 1);
    }

    if (check.type === "field_populated" && check.path && check.field) {
      const files = this.app.vault.getMarkdownFiles().filter(
        (f) => f.path.startsWith(check.path!)
      );
      const matching: Array<Record<string, unknown>> = [];
      for (const file of files) {
        const cache = this.app.metadataCache.getFileCache(file);
        const fm = cache?.frontmatter;
        if (!fm) continue;
        const filter = check.filter || {};
        const matches = Object.entries(filter).every(
          ([k, v]) => String(fm[k] || "").toLowerCase() === String(v).toLowerCase()
        );
        if (matches) matching.push(fm);
      }
      if (matching.length === 0) return true; // vacuously true
      return matching.every((fm) => {
        const val = fm[check.field!];
        return val != null && String(val).trim() !== "";
      });
    }

    if (check.type === "field_coverage" && check.path && check.field) {
      const files = this.app.vault.getMarkdownFiles().filter(
        (f) => f.path.startsWith(check.path!)
      );
      const matching: Array<Record<string, unknown>> = [];
      for (const file of files) {
        const cache = this.app.metadataCache.getFileCache(file);
        const fm = cache?.frontmatter;
        if (!fm) continue;
        const filter = check.filter || {};
        const matches = Object.entries(filter).every(
          ([k, v]) => String(fm[k] || "").toLowerCase() === String(v).toLowerCase()
        );
        if (matches) matching.push(fm);
      }
      if (matching.length === 0) return false; // no data = unsatisfied
      const populated = matching.filter((fm) => {
        const val = fm[check.field!];
        return val != null && String(val).trim() !== "";
      }).length;
      return (populated / matching.length) * 100 >= (check.threshold || 50);
    }

    return false;
  }

  // ── Interview control ───────────────────────────────────────

  async start(): Promise<QuestionContext | null> {
    this.state.active = true;
    await this.save();
    return this.nextQuestion();
  }

  async stop(): Promise<void> {
    this.state.active = false;
    this.state.currentRequirement = null;
    await this.save();
  }

  async skip(): Promise<QuestionContext | null> {
    if (this.state.currentRequirement) {
      this.state.skipped.push(this.state.currentRequirement);
      this.state.currentRequirement = null;
      await this.save();
    }
    return this.nextQuestion();
  }

  async nextQuestion(): Promise<QuestionContext | null> {
    const satisfied = await this.scanVaultSatisfaction();
    const skippedSet = new Set(this.state.skipped);

    const q = getNextQuestion(satisfied, skippedSet);
    if (!q) {
      this.state.active = false;
      this.state.currentRequirement = null;
      await this.save();
      return null;
    }

    this.state.currentRequirement = q.requirement.id;
    await this.save();
    return q;
  }

  // ── Answer processing ───────────────────────────────────────

  async processAnswer(answer: string): Promise<{
    success: boolean;
    message: string;
    nextQuestion: QuestionContext | null;
  }> {
    if (!this.state.currentRequirement) {
      return { success: false, message: "No active question.", nextQuestion: null };
    }

    const req = REQUIREMENTS.find((r) => r.id === this.state.currentRequirement);
    if (!req) {
      return { success: false, message: "Requirement not found.", nextQuestion: null };
    }

    const qCtx = buildQuestion(req);

    // Extract structured data from answer
    const extraction = await extractFromAnswer(answer, qCtx.extractionPrompt, this.settings);
    if (!extraction) {
      return {
        success: false,
        message: "I couldn't extract structured data from that answer. Could you try rephrasing?",
        nextQuestion: null,
      };
    }

    // Write to vault based on output type
    const writeResult = await this.writeToVault(req, extraction);
    if (!writeResult.success) {
      return { success: false, message: writeResult.message, nextQuestion: null };
    }

    // Mark completed
    this.state.completed.push(req.id);
    this.state.currentRequirement = null;
    await this.save();

    // Get next question
    const next = await this.nextQuestion();

    return {
      success: true,
      message: writeResult.message,
      nextQuestion: next,
    };
  }

  private async writeToVault(
    req: Requirement,
    extraction: ExtractionResult
  ): Promise<{ success: boolean; message: string }> {
    const data = extraction.data;
    const outputType = req.acquisition.outputType;

    try {
      if (outputType === "person_note") {
        // Could be a single person or an array
        const people: PersonData[] = Array.isArray(data)
          ? data as PersonData[]
          : data.people
            ? (data.people as PersonData[])
            : [data as PersonData];

        const created: string[] = [];
        for (const person of people) {
          if (!person.name) continue;
          const file = await createPersonNote(this.app, person);
          if (file) created.push(person.name);
        }
        return {
          success: created.length > 0,
          message: created.length > 0
            ? `Created person notes: ${created.join(", ")}`
            : "No person notes created — check the answer format.",
        };
      }

      if (outputType === "reference_doc") {
        // Build reference doc content from extracted data
        const title = req.description.trim().split(".")[0];
        const content = typeof data === "object"
          ? Object.entries(data)
              .filter(([k]) => k !== "incomplete")
              .map(([k, v]) => {
                if (Array.isArray(v)) {
                  return `## ${k}\n\n${v.map((item) =>
                    typeof item === "object"
                      ? Object.entries(item).map(([ik, iv]) => `- **${ik}**: ${iv}`).join("\n")
                      : `- ${item}`
                  ).join("\n\n")}`;
                }
                return `## ${k}\n\n${v}`;
              })
              .join("\n\n")
          : String(data);

        const file = await createReferenceDoc(this.app, {
          id: req.id,
          title,
          content,
        });
        return {
          success: file !== null,
          message: file ? `Created reference doc: ${title}` : "Failed to create reference doc.",
        };
      }

      if (outputType === "frontmatter_update") {
        const person = (data as Record<string, unknown>).person as string;
        if (!person) {
          return { success: false, message: "No person name in extracted data." };
        }
        const fields: Record<string, string | number | boolean> = {};
        for (const [k, v] of Object.entries(data)) {
          if (k === "person" || k === "incomplete") continue;
          fields[k] = v as string | number | boolean;
        }
        const ok = await updateFrontmatter(this.app, person, fields);
        return {
          success: ok,
          message: ok ? `Updated ${person}: ${Object.keys(fields).join(", ")}` : `Failed to update ${person}.`,
        };
      }

      return { success: false, message: `Unknown output type: ${outputType}` };
    } catch (err: any) {
      return { success: false, message: `Vault write error: ${err.message}` };
    }
  }

  // ── Progress ────────────────────────────────────────────────

  async getProgress(): Promise<InterviewProgress> {
    const satisfied = await this.scanVaultSatisfaction();
    const interviewable = getInterviewableRequirements();

    const count = (cat: string) => {
      const reqs = interviewable.filter((r) => r.category === cat);
      const done = reqs.filter((r) => satisfied.has(r.id)).length;
      return { done, total: reqs.length };
    };

    const foundational = count("foundational");

    return {
      foundational,
      structural: count("structural"),
      enrichment: count("enrichment"),
      foundationalComplete: foundational.done === foundational.total,
    };
  }

  // ── Status ──────────────────────────────────────────────────

  isActive(): boolean {
    return this.state.active;
  }

  hasFoundationalGaps(): boolean {
    const foundational = REQUIREMENTS.filter((r) => r.category === "foundational");
    return foundational.some((r) => !this.state.completed.includes(r.id));
  }

  getState(): InterviewState {
    return { ...this.state };
  }
}
```

**Step 2: Verify build**

```bash
cd <obsidian-hapax>
pnpm run build
```

Expected: Build succeeds.

**Step 3: Commit**

```bash
cd <obsidian-hapax>
git add src/interview/engine.ts
git commit -m "feat(interview): engine state machine — gap detection, answer processing, vault writing

InterviewEngine manages full lifecycle: vault scanning for satisfaction,
dependency-ordered question selection, LLM extraction, vault write dispatch,
progress tracking. State persists in data.json via Obsidian Sync."
```

---

## Task 9: Chat Integration — /setup Commands + Banner

**Repo:** `<obsidian-hapax>/`

**Files:**
- Modify: `src/slash-commands.ts`
- Modify: `src/chat-view.ts`
- Modify: `src/main.ts`

**Step 1: Add /setup commands to slash-commands.ts**

In `src/slash-commands.ts`, add 3 new entries to the `COMMANDS` array (after `/team-risks`):

```typescript
  {
    name: "/setup",
    description: "Start or resume management data setup interview",
    template: "__SETUP_START__",
  },
  {
    name: "/setup skip",
    description: "Skip the current setup question",
    template: "__SETUP_SKIP__",
  },
  {
    name: "/setup status",
    description: "Show setup progress",
    template: "__SETUP_STATUS__",
  },
```

These use sentinel template values that `chat-view.ts` will intercept.

**Step 2: Add interview engine to chat-view.ts**

At the top of `src/chat-view.ts`, add the import (after line 10):

```typescript
import { InterviewEngine, type InterviewProgress } from "./interview/engine";
```

Add a new property to the `ChatView` class (after line 23):

```typescript
  private interviewEngine: InterviewEngine | null = null;
```

In the `onOpen()` method (find it in the file — it creates the chat container), add interview engine initialization after the existing setup:

```typescript
    // Initialize interview engine
    this.interviewEngine = new InterviewEngine(
      this.app,
      this.plugin.settings,
      () => this.plugin.loadData() as Promise<Record<string, unknown>>,
      (data) => this.plugin.saveData(data),
    );
    await this.interviewEngine.load();

    // Show setup banner if foundational gaps exist
    if (this.interviewEngine.hasFoundationalGaps()) {
      this.showSetupBanner();
    }
```

Add new methods to the `ChatView` class:

```typescript
  // ── Interview UI ────────────────────────────────────────────

  private showSetupBanner(): void {
    const existing = this.containerEl.querySelector(".hapax-setup-banner");
    if (existing) return;

    const banner = document.createElement("div");
    banner.addClass("hapax-setup-banner");

    const text = document.createElement("span");
    text.setText("Your management system needs setup data");
    banner.appendChild(text);

    const btn = document.createElement("button");
    btn.setText("Start Setup");
    btn.addClass("hapax-setup-btn");
    btn.addEventListener("click", () => this.handleSetupStart());
    banner.appendChild(btn);

    // Insert after header, before messages
    const header = this.containerEl.querySelector(".hapax-chat-header");
    if (header?.nextSibling) {
      header.parentElement?.insertBefore(banner, header.nextSibling);
    } else {
      this.containerEl.prepend(banner);
    }
  }

  private removeSetupBanner(): void {
    const banner = this.containerEl.querySelector(".hapax-setup-banner");
    banner?.remove();
  }

  private async showSetupProgress(): Promise<void> {
    if (!this.interviewEngine) return;
    const progress = await this.interviewEngine.getProgress();
    const text = `**Setup Progress**\n` +
      `- Foundational: ${progress.foundational.done}/${progress.foundational.total}\n` +
      `- Structural: ${progress.structural.done}/${progress.structural.total}\n` +
      `- Enrichment: ${progress.enrichment.done}/${progress.enrichment.total}`;

    const statusMsg: ChatMessage = {
      role: "assistant",
      content: text,
      timestamp: Date.now(),
    };
    this.messages.push(statusMsg);
    this.renderMessage(statusMsg);
  }

  private async handleSetupStart(): Promise<void> {
    if (!this.interviewEngine) return;

    const q = await this.interviewEngine.start();
    if (!q) {
      const doneMsg: ChatMessage = {
        role: "assistant",
        content: "All interview-acquirable requirements are satisfied! Your management system is operational.",
        timestamp: Date.now(),
      };
      this.messages.push(doneMsg);
      this.renderMessage(doneMsg);
      this.removeSetupBanner();
      return;
    }

    await this.showSetupProgress();

    const questionMsg: ChatMessage = {
      role: "assistant",
      content: q.question,
      timestamp: Date.now(),
    };
    this.messages.push(questionMsg);
    this.renderMessage(questionMsg);
  }

  private async handleSetupSkip(): Promise<void> {
    if (!this.interviewEngine) return;

    const next = await this.interviewEngine.skip();
    if (next) {
      const msg: ChatMessage = {
        role: "assistant",
        content: `Skipped. Next question:\n\n${next.question}`,
        timestamp: Date.now(),
      };
      this.messages.push(msg);
      this.renderMessage(msg);
    } else {
      const msg: ChatMessage = {
        role: "assistant",
        content: "No more questions. Setup complete!",
        timestamp: Date.now(),
      };
      this.messages.push(msg);
      this.renderMessage(msg);
      this.removeSetupBanner();
    }
  }
```

In the `sendMessage()` method, add an intercept at the very beginning (before the existing message processing) to detect setup commands and interview-mode answers:

```typescript
    // Intercept setup commands
    if (text === "__SETUP_START__") {
      await this.handleSetupStart();
      return;
    }
    if (text === "__SETUP_SKIP__") {
      await this.handleSetupSkip();
      return;
    }
    if (text === "__SETUP_STATUS__") {
      await this.showSetupProgress();
      return;
    }

    // If interview is active, process answer through interview engine
    if (this.interviewEngine?.isActive()) {
      // Show user message
      const userMsg: ChatMessage = { role: "user", content: text, timestamp: Date.now() };
      this.messages.push(userMsg);
      this.renderMessage(userMsg);

      // Process through interview engine
      const result = await this.interviewEngine.processAnswer(text);

      const resultMsg: ChatMessage = {
        role: "assistant",
        content: result.message,
        timestamp: Date.now(),
      };
      this.messages.push(resultMsg);
      this.renderMessage(resultMsg);

      if (result.nextQuestion) {
        const nextMsg: ChatMessage = {
          role: "assistant",
          content: result.nextQuestion.question,
          timestamp: Date.now(),
        };
        this.messages.push(nextMsg);
        this.renderMessage(nextMsg);
      } else if (result.success) {
        const doneMsg: ChatMessage = {
          role: "assistant",
          content: "Setup interview complete! All acquirable requirements satisfied.",
          timestamp: Date.now(),
        };
        this.messages.push(doneMsg);
        this.renderMessage(doneMsg);

        // Check if foundational complete
        const progress = await this.interviewEngine.getProgress();
        if (progress.foundationalComplete) {
          this.removeSetupBanner();
          const opMsg: ChatMessage = {
            role: "assistant",
            content: "Management system is now operational. All foundational data is in place.",
            timestamp: Date.now(),
          };
          this.messages.push(opMsg);
          this.renderMessage(opMsg);
        }
      }

      this.scrollToBottom();
      await this.saveChatHistory();
      return;
    }
```

**Step 3: Verify build**

```bash
cd <obsidian-hapax>
pnpm run build
```

Expected: Build succeeds.

**Step 4: Commit**

```bash
cd <obsidian-hapax>
git add src/slash-commands.ts src/chat-view.ts
git commit -m "feat(interview): /setup commands + banner + chat integration

Adds /setup, /setup skip, /setup status slash commands. Shows persistent
banner when foundational gaps exist. Interview-mode answers route through
InterviewEngine instead of normal LLM chat. Progress display after each
answer. Banner removed when foundational requirements met."
```

---

## Task 10: Interview CSS Styles

**Repo:** `<obsidian-hapax>/`

**Files:**
- Modify: `styles.css`

**Step 1: Append interview styles to `styles.css`**

Add at the end of `<obsidian-hapax>/styles.css`:

```css
/* Interview setup banner */
.hapax-setup-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--background-secondary);
  border-bottom: 2px solid var(--interactive-accent);
  font-size: 13px;
  color: var(--text-normal);
}

.hapax-setup-btn {
  background: var(--interactive-accent);
  color: var(--text-on-accent);
  border: none;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
}

.hapax-setup-btn:hover {
  opacity: 0.9;
}
```

**Step 2: Verify build**

```bash
cd <obsidian-hapax>
pnpm run build
```

Expected: Build succeeds.

**Step 3: Commit**

```bash
cd <obsidian-hapax>
git add styles.css
git commit -m "feat(interview): setup banner CSS styles

Persistent banner with accent border and Start Setup button.
Uses Obsidian CSS custom properties for theme compatibility."
```

---

## Task 11: Final Build and Cross-Repo Verification

**Step 1: Build obsidian-hapax plugin**

```bash
cd <obsidian-hapax>
pnpm run build
```

Expected: Build succeeds with no errors.

**Step 2: Verify TypeScript compiles**

```bash
cd <obsidian-hapax>
npx -y tsc --noEmit
```

Expected: No type errors.

**Step 3: Run ai-agents full test suite**

```bash
cd <ai-agents>
uv run pytest --tb=short -q
```

Expected: All tests pass including the ~27 new knowledge sufficiency tests.

**Step 4: Validate YAML model**

```bash
cd <hapaxromana>
python3 -c "import yaml; d = yaml.safe_load(open('knowledge/management-sufficiency.yaml')); print(f'{len(d[\"requirements\"])} requirements loaded')"
```

Expected: `27 requirements loaded`

**Step 5: Verify QuickAdd config is still valid JSON**

```bash
python3 -c "import json; json.load(open('$HOME/Documents/Personal/.obsidian/plugins/quickadd/data.json'))"
```

Expected: No error.

**Step 6: Final commits**

If any files were missed, add and commit them. Then tag:

```bash
cd <hapaxromana>
git add -A
git status  # verify only expected files
# commit if needed

cd <ai-agents>
git add -A
git status
# commit if needed
```

---

## Post-Implementation Manual Steps

1. **Reload hapax plugin**: Obsidian → Settings → Community Plugins → toggle obsidian-hapax off/on
2. **Test /setup**: Open chat sidebar, type `/setup` → should show progress + first question
3. **Test banner**: If no person notes exist in `10-work/people/`, banner should appear
4. **Test extraction**: Answer the first question with team member names → verify person notes created
5. **Verify nudges**: Run `uv run cockpit --once` from `<ai-agents>/` → should show knowledge gaps in nudges

---

## Summary

| Task | Repo | Files | Tests |
|------|------|-------|-------|
| 1. Knowledge Model YAML | hapaxromana | 1 new | — |
| 2. Check Functions | ai-agents | 2 new | 15 |
| 3. Audit Orchestrator | ai-agents | 2 modified | 7 |
| 4. Nudge Integration | ai-agents | 2 modified | 5 |
| 5. Question Templates | obsidian-hapax | 2 new | build |
| 6. Vault Writer | obsidian-hapax | 1 new | build |
| 7. Extractor | obsidian-hapax | 1 new | build |
| 8. Engine State Machine | obsidian-hapax | 1 new | build |
| 9. Chat Integration | obsidian-hapax | 2 modified | build |
| 10. CSS Styles | obsidian-hapax | 1 modified | build |
| 11. Final Verification | all 3 | — | full suite |
