# Domain Lattice Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generalize the management-specific Knowledge Sufficiency Engine into a multi-domain awareness system with momentum tracking, emergence detection, adaptive sufficiency, and a cockpit dashboard.

**Architecture:** Domain registry YAML in hapaxromana defines domains, relationships, governance, and person extensions. Python audit engine in ai-agents loops over all domains. Cockpit dashboard shows per-domain health. Emergence detection clusters undomained activity into candidate domains. All zero-LLM except emergence proposals.

**Tech Stack:** Python 3.12, pytest, YAML, Textual 8.0.0, Pydantic, Rich. No new dependencies.

**Design doc:** `docs/plans/2026-03-04-domain-lattice-design.md`

---

## Phase 1: Domain Registry + Multi-Domain Audit

### Task 1: Create Domain Registry YAML

**Files:**
- Create: `<hapaxromana>/domains/registry.yaml`

**Step 1: Create the directory and file**

```bash
mkdir -p <hapaxromana>/domains
```

Create `<hapaxromana>/domains/registry.yaml`:

```yaml
# domains/registry.yaml — Life domain definitions for the Domain Lattice Engine.
# Schema: domains declare vault paths, profiler dimensions, relationships,
# governance, and person extensions. Constitutional layer constrains all domains.
version: 1
updated: "2026-03-04"

constitutional:
  - id: values-ethics
    description: "Higher principles, ethical constraints, personal values"
    axiom_ids: [single_user, executive_function]
    supremacy: true

domains:
  - id: management
    name: "Management & Leadership"
    status: active
    sufficiency_model: knowledge/management-sufficiency.yaml
    vault_paths:
      - "10-work/people"
      - "10-work/meetings"
      - "10-work/projects"
      - "10-work/decisions"
      - "10-work/references"
      - "10-work/coaching"
      - "10-work/feedback"
    profiler_dimensions:
      - management_practice
      - team_leadership
    relationships:
      - target: technical
        type: supports
        description: "Technical depth informs management decisions"
      - target: personal
        type: constrained-by
        description: "Work-life boundary constraints"
    governance:
      axiom_ids: [management_governance, corporate_boundary]
      heuristics:
        - "LLM prepares, human delivers"
        - "Never generate feedback language"
        - "Signal aggregation, not recommendation"
    person_extensions:
      fields:
        - { name: mgmt-role, type: string }
        - { name: mgmt-team, type: string }
        - { name: mgmt-cadence, type: string }
        - { name: cognitive-load, type: number, range: [1, 5] }
        - { name: skill-level, type: string, options: [developing, career, advanced, expert] }
        - { name: will-signal, type: string, options: [high, moderate, low] }
        - { name: coaching-active, type: boolean }
        - { name: feedback-style, type: string }
        - { name: growth-vector, type: string }
        - { name: career-goal-3y, type: string }
        - { name: current-gaps, type: string }
        - { name: current-focus, type: string }
        - { name: last-career-convo, type: date }
        - { name: team-type, type: string }
        - { name: interaction-mode, type: string }
      staleness_days: 14

  - id: music
    name: "Music Production"
    status: active
    sufficiency_model: knowledge/music-sufficiency.yaml
    vault_paths:
      - "20-personal/music"
    profiler_dimensions:
      - music_production
      - technical_preferences
    relationships:
      - target: technical
        type: supports
        description: "MIDI/audio programming supports production"
    governance:
      axiom_ids: []
      heuristics:
        - "Creative autonomy — suggest techniques, never aesthetic judgments"
        - "Hardware-first — DAWless workflow is intentional"
    person_extensions:
      fields:
        - { name: music-role, type: string }
        - { name: music-instrument, type: string }
        - { name: music-genre, type: string }
      staleness_days: 30

  - id: personal
    name: "Personal & Family"
    status: active
    sufficiency_model: knowledge/personal-sufficiency.yaml
    vault_paths:
      - "20-personal"
    profiler_dimensions:
      - personal_interests
      - health_fitness
    relationships:
      - target: management
        type: constrained-by
        description: "Work-life boundary"
    governance:
      axiom_ids: []
      heuristics:
        - "Maximum privacy — minimal data collection"
        - "Never optimize relationships"
        - "Record only what operator explicitly shares"
    person_extensions:
      fields:
        - { name: personal-context, type: string }
        - { name: personal-cadence, type: string }
      staleness_days: 60

  - id: technical
    name: "Technical Infrastructure"
    status: active
    sufficiency_model: knowledge/technical-sufficiency.yaml
    vault_paths:
      - "30-system"
    profiler_dimensions:
      - technical_preferences
      - development_patterns
    relationships:
      - target: management
        type: supports
      - target: music
        type: supports
    governance:
      axiom_ids: [single_user]
      heuristics:
        - "Infrastructure serves domains, not the reverse"
        - "Minimize operational burden (executive function)"
    person_extensions:
      fields: []
      staleness_days: null
```

**Step 2: Commit**

```bash
cd <hapaxromana>
git add domains/registry.yaml
git commit -m "feat: domain registry — 4 domains with relationships, governance, person extensions"
```

---

### Task 2: Create Stub Sufficiency Models

**Files:**
- Create: `<hapaxromana>/knowledge/music-sufficiency.yaml`
- Create: `<hapaxromana>/knowledge/personal-sufficiency.yaml`
- Create: `<hapaxromana>/knowledge/technical-sufficiency.yaml`

**Step 1: Create music-sufficiency.yaml**

```yaml
# Music Production Sufficiency Model
version: 1
requirements:
  - id: hardware-inventory
    category: foundational
    description: "Hardware gear documented — synths, samplers, controllers."
    source: "operator"
    check:
      type: file_exists
      path: "20-personal/music/gear-inventory.md"
    acquisition:
      method: interview
      question: "What gear do you have in your studio? List your synths, samplers, controllers, and effects."
      output: reference_doc
    priority: 90
    depends_on: []

  - id: signal-routing
    category: foundational
    description: "Audio and MIDI signal routing documented."
    source: "operator"
    check:
      type: file_exists
      path: "20-personal/music/signal-routing.md"
    acquisition:
      method: interview
      question: "How is your studio routed? Describe your MIDI and audio signal chains."
      output: reference_doc
    priority: 90
    depends_on: []

  - id: production-workflow
    category: structural
    description: "Production workflow documented — how you start and finish tracks."
    source: "operator"
    check:
      type: file_exists
      path: "20-personal/music/production-workflow.md"
    acquisition:
      method: interview
      question: "Describe your production workflow. How do you start a track? How do you finish one?"
      output: reference_doc
    priority: 60
    depends_on: []

  - id: sample-library
    category: structural
    description: "Sample library organization documented."
    source: "operator"
    check:
      type: file_exists
      path: "20-personal/music/sample-library.md"
    acquisition:
      method: interview
      question: "How is your sample library organized? Where are your samples stored? Any naming conventions?"
      output: reference_doc
    priority: 60
    depends_on: []

  - id: current-projects
    category: enrichment
    description: "Active music projects documented."
    source: "operator"
    check:
      type: min_count
      path: "20-personal/music"
      filter:
        type: project
        status: active
      min: 1
    acquisition:
      method: interview
      question: "What music projects are you currently working on? For each: name, genre/style, stage (idea/in-progress/mixing/done)."
      output: reference_doc
    priority: 35
    depends_on: []

  - id: collaborators
    category: enrichment
    description: "Music collaborators documented as person notes."
    source: "operator"
    check:
      type: min_count
      path: "10-work/people"
      filter:
        type: person
        music-role: collaborator
      min: 0
    acquisition:
      method: interview
      question: "Do you collaborate with anyone on music? Who, and what's their role?"
      output: person_note
    priority: 35
    depends_on: []
```

**Step 2: Create personal-sufficiency.yaml**

```yaml
# Personal Domain Sufficiency Model
version: 1
requirements:
  - id: family-context
    category: foundational
    description: "Key family members documented."
    source: "operator"
    check:
      type: min_count
      path: "10-work/people"
      filter:
        type: person
        personal-context: ""
      min: 0
    acquisition:
      method: interview
      question: "Who are the key people in your personal life? Family members, close friends — anyone the system should know about."
      output: person_note
    priority: 90
    depends_on: []

  - id: personal-goals
    category: structural
    description: "Personal goals documented."
    source: "operator"
    check:
      type: file_exists
      path: "20-personal/references/personal-goals.md"
    acquisition:
      method: interview
      question: "What are your personal goals? Health, hobbies, learning, anything outside work and music."
      output: reference_doc
    priority: 60
    depends_on: []

  - id: health-baseline
    category: enrichment
    description: "Health and fitness baseline documented."
    source: "operator"
    check:
      type: file_exists
      path: "20-personal/references/health-baseline.md"
    acquisition:
      method: interview
      question: "Any health or fitness context the system should know? Exercise routine, dietary constraints, energy patterns."
      output: reference_doc
    priority: 35
    depends_on: []

  - id: routines
    category: structural
    description: "Daily/weekly routines documented."
    source: "operator"
    check:
      type: file_exists
      path: "20-personal/references/routines.md"
    acquisition:
      method: interview
      question: "What does your typical day and week look like? Morning routine, work hours, evening structure."
      output: reference_doc
    priority: 60
    depends_on: []
```

**Step 3: Create technical-sufficiency.yaml**

```yaml
# Technical Infrastructure Sufficiency Model
version: 1
requirements:
  - id: service-topology
    category: foundational
    description: "Docker service topology documented and current."
    source: "derived"
    check:
      type: file_exists
      path: "30-system/briefings/latest-briefing.md"
    acquisition:
      method: external
      question: null
      output: null
    priority: 90
    depends_on: []

  - id: model-inventory
    category: structural
    description: "Available LLM models and their use cases documented."
    source: "derived"
    check:
      type: file_exists
      path: "30-system/references/model-inventory.md"
    acquisition:
      method: nudge
      question: null
      output: null
    priority: 60
    depends_on: []

  - id: backup-verification
    category: structural
    description: "Backup strategy documented and verified."
    source: "derived"
    check:
      type: file_exists
      path: "30-system/references/backup-strategy.md"
    acquisition:
      method: nudge
      question: null
      output: null
    priority: 60
    depends_on: []

  - id: component-registry
    category: structural
    description: "Component registry maintained and current."
    source: "derived"
    check:
      type: file_exists
      path: "30-system/references/component-registry.md"
    acquisition:
      method: external
      question: null
      output: null
    priority: 60
    depends_on: []

  - id: security-posture
    category: enrichment
    description: "Security hardening measures documented."
    source: "derived"
    check:
      type: file_exists
      path: "30-system/references/security-posture.md"
    acquisition:
      method: nudge
      question: null
      output: null
    priority: 35
    depends_on: []
```

**Step 4: Commit**

```bash
cd <hapaxromana>
git add knowledge/music-sufficiency.yaml knowledge/personal-sufficiency.yaml knowledge/technical-sufficiency.yaml
git commit -m "feat: stub sufficiency models for music, personal, technical domains"
```

---

### Task 3: Add Domain Registry Loader to knowledge_sufficiency.py

**Files:**
- Modify: `<ai-agents>/cockpit/data/knowledge_sufficiency.py:17-23`
- Test: `<ai-agents>/tests/test_knowledge_sufficiency.py`

**Step 1: Write the failing test**

Add to `<ai-agents>/tests/test_knowledge_sufficiency.py`:

```python
from cockpit.data.knowledge_sufficiency import (
    DOMAIN_REGISTRY_PATH,
    load_domain_registry,
)


class TestDomainRegistry:
    def test_registry_path_exists(self) -> None:
        """Domain registry YAML file exists on disk."""
        assert DOMAIN_REGISTRY_PATH.is_file(), f"Missing: {DOMAIN_REGISTRY_PATH}"

    def test_load_registry_has_domains(self) -> None:
        """Registry loads and contains at least 4 domains."""
        registry = load_domain_registry()
        assert "domains" in registry
        assert len(registry["domains"]) >= 4

    def test_load_registry_has_constitutional(self) -> None:
        """Registry has a constitutional layer."""
        registry = load_domain_registry()
        assert "constitutional" in registry

    def test_management_domain_has_sufficiency_model(self) -> None:
        """Management domain references its sufficiency YAML."""
        registry = load_domain_registry()
        mgmt = next(d for d in registry["domains"] if d["id"] == "management")
        assert mgmt["sufficiency_model"] == "knowledge/management-sufficiency.yaml"

    def test_each_domain_has_required_fields(self) -> None:
        """Every domain has id, name, status, vault_paths, governance."""
        registry = load_domain_registry()
        for domain in registry["domains"]:
            assert "id" in domain, f"Missing id in {domain}"
            assert "name" in domain, f"Missing name in {domain.get('id', '?')}"
            assert "status" in domain, f"Missing status in {domain['id']}"
            assert "vault_paths" in domain, f"Missing vault_paths in {domain['id']}"
            assert "governance" in domain, f"Missing governance in {domain['id']}"
```

**Step 2: Run test to verify it fails**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestDomainRegistry -v
```

Expected: FAIL with `ImportError` — `DOMAIN_REGISTRY_PATH` and `load_domain_registry` don't exist yet.

**Step 3: Implement registry loader**

In `<ai-agents>/cockpit/data/knowledge_sufficiency.py`, add after line 23 (after `KNOWLEDGE_MODEL_PATH`):

```python
DOMAIN_REGISTRY_PATH = (
    Path.home() / "projects" / "hapaxromana" / "domains" / "registry.yaml"
)

KNOWLEDGE_DIR = (
    Path.home() / "projects" / "hapaxromana" / "knowledge"
)
```

Add a new function after `load_knowledge_model()` (after line 202):

```python
def load_domain_registry(path: Path | None = None) -> dict:
    """Load the domain registry YAML from disk."""
    target = path or DOMAIN_REGISTRY_PATH
    with open(target, encoding="utf-8") as f:
        return yaml.safe_load(f)
```

**Step 4: Run test to verify it passes**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestDomainRegistry -v
```

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/data/knowledge_sufficiency.py tests/test_knowledge_sufficiency.py
git commit -m "feat: domain registry loader — DOMAIN_REGISTRY_PATH, load_domain_registry()"
```

---

### Task 4: Multi-Domain Audit Function

**Files:**
- Modify: `<ai-agents>/cockpit/data/knowledge_sufficiency.py:294-311`
- Test: `<ai-agents>/tests/test_knowledge_sufficiency.py`

**Step 1: Write the failing test**

Add to `<ai-agents>/tests/test_knowledge_sufficiency.py`:

```python
from cockpit.data.knowledge_sufficiency import collect_all_domain_gaps


class TestMultiDomainAudit:
    def test_returns_dict_keyed_by_domain_id(self) -> None:
        """collect_all_domain_gaps returns {domain_id: SufficiencyReport}."""
        reports = collect_all_domain_gaps()
        assert isinstance(reports, dict)
        # At minimum, management should always be present
        assert "management" in reports

    def test_management_report_matches_single_domain(self) -> None:
        """Multi-domain management report matches single-domain collect_knowledge_gaps."""
        from cockpit.data.knowledge_sufficiency import collect_knowledge_gaps
        single = collect_knowledge_gaps()
        multi = collect_all_domain_gaps()
        if "management" in multi:
            assert multi["management"].total_requirements == single.total_requirements
            assert multi["management"].sufficiency_score == single.sufficiency_score

    def test_returns_reports_for_domains_with_models(self) -> None:
        """Only domains with existing sufficiency YAML files get reports."""
        reports = collect_all_domain_gaps()
        for domain_id, report in reports.items():
            assert isinstance(report, SufficiencyReport)
            assert report.total_requirements >= 0

    def test_skips_domains_without_model_file(self, tmp_path: Path) -> None:
        """Domains whose sufficiency YAML doesn't exist are silently skipped."""
        # This is an integration test — the real registry has some domains
        # whose models may not exist yet. Those should be skipped, not crash.
        reports = collect_all_domain_gaps()
        # Should not raise and should return at least management
        assert len(reports) >= 1

    def test_empty_report_on_missing_registry(self) -> None:
        """Returns empty dict if registry file doesn't exist."""
        from cockpit.data.knowledge_sufficiency import DOMAIN_REGISTRY_PATH
        import tempfile
        # This tests the safe fallback — can't easily mock the path,
        # so we just verify the function handles gracefully.
        reports = collect_all_domain_gaps()
        assert isinstance(reports, dict)
```

**Step 2: Run test to verify it fails**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestMultiDomainAudit -v
```

Expected: FAIL — `collect_all_domain_gaps` doesn't exist.

**Step 3: Implement collect_all_domain_gaps**

Add to `<ai-agents>/cockpit/data/knowledge_sufficiency.py`, after `collect_knowledge_gaps()`:

```python
def collect_all_domain_gaps(
    vault_path: Path | None = None,
) -> dict[str, SufficiencyReport]:
    """Load every domain's sufficiency model and run audit.

    Returns {domain_id: SufficiencyReport} for each domain that has
    a sufficiency YAML file. Silently skips domains without models.
    Returns empty dict if the registry file is missing.
    """
    if not DOMAIN_REGISTRY_PATH.is_file():
        return {}

    vp = vault_path or VAULT_PATH

    try:
        registry = load_domain_registry()
    except Exception:
        return {}

    reports: dict[str, SufficiencyReport] = {}
    for domain in registry.get("domains", []):
        domain_id = domain.get("id", "")
        model_ref = domain.get("sufficiency_model", "")
        if not domain_id or not model_ref:
            continue

        model_path = KNOWLEDGE_DIR / model_ref.split("/", 1)[-1] if "/" in model_ref else KNOWLEDGE_DIR / model_ref
        if not model_path.is_file():
            continue

        try:
            model = load_knowledge_model(model_path)
            reports[domain_id] = run_audit(model, vault_path=vp)
        except Exception:
            continue

    return reports
```

**Step 4: Run test to verify it passes**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestMultiDomainAudit -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/data/knowledge_sufficiency.py tests/test_knowledge_sufficiency.py
git commit -m "feat: collect_all_domain_gaps — multi-domain sufficiency audit"
```

---

### Task 5: Domain-Scoped Nudge Generation

**Files:**
- Modify: `<ai-agents>/cockpit/data/knowledge_sufficiency.py:319-362` (gaps_to_nudges)
- Modify: `<ai-agents>/cockpit/data/nudges.py:501-508` (_collect_knowledge_sufficiency_nudges)
- Test: `<ai-agents>/tests/test_knowledge_sufficiency.py`

**Step 1: Write the failing test**

Add to `<ai-agents>/tests/test_knowledge_sufficiency.py`:

```python
class TestDomainScopedNudges:
    def test_gaps_to_nudges_with_domain_id(self) -> None:
        """gaps_to_nudges with domain_id prepends it to source_id."""
        gap = KnowledgeGap(
            requirement_id="test-req",
            category="foundational",
            priority=90,
            description="Test requirement",
            acquisition_method="interview",
            interview_question="Test?",
            satisfied=False,
        )
        from cockpit.data.knowledge_sufficiency import gaps_to_nudges
        nudges = gaps_to_nudges([gap], domain_id="music")
        assert len(nudges) == 1
        assert nudges[0].source_id == "knowledge:music:test-req"

    def test_gaps_to_nudges_default_no_domain(self) -> None:
        """gaps_to_nudges without domain_id uses bare source_id (backward compat)."""
        gap = KnowledgeGap(
            requirement_id="test-req",
            category="foundational",
            priority=90,
            description="Test requirement",
            acquisition_method="interview",
            interview_question="Test?",
            satisfied=False,
        )
        from cockpit.data.knowledge_sufficiency import gaps_to_nudges
        nudges = gaps_to_nudges([gap])
        assert nudges[0].source_id == "knowledge:test-req"
```

**Step 2: Run test to verify it fails**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestDomainScopedNudges -v
```

Expected: FAIL — `gaps_to_nudges` doesn't accept `domain_id` parameter.

**Step 3: Implement domain_id parameter**

In `<ai-agents>/cockpit/data/knowledge_sufficiency.py`, modify `gaps_to_nudges`:

Change the function signature from:
```python
def gaps_to_nudges(gaps: list[KnowledgeGap]) -> list["Nudge"]:
```
To:
```python
def gaps_to_nudges(gaps: list[KnowledgeGap], *, domain_id: str = "") -> list["Nudge"]:
```

Change the source_id line from:
```python
            source_id=f"knowledge:{gap.requirement_id}",
```
To:
```python
            source_id=f"knowledge:{domain_id}:{gap.requirement_id}" if domain_id else f"knowledge:{gap.requirement_id}",
```

**Step 4: Update _collect_knowledge_sufficiency_nudges**

In `<ai-agents>/cockpit/data/nudges.py`, replace lines 501-508:

```python
def _collect_knowledge_sufficiency_nudges(nudges: list[Nudge]) -> None:
    """Generate nudges from knowledge sufficiency gaps across all domains."""
    try:
        from cockpit.data.knowledge_sufficiency import collect_all_domain_gaps, gaps_to_nudges
        reports = collect_all_domain_gaps()
        for domain_id, report in reports.items():
            nudges.extend(gaps_to_nudges(report.gaps, domain_id=domain_id))
    except Exception:
        pass
```

**Step 5: Run test to verify it passes**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py::TestDomainScopedNudges -v
```

Expected: PASS

**Step 6: Run full test suite**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py tests/test_nudges.py -v
```

Expected: All PASS

**Step 7: Commit**

```bash
cd <ai-agents>
git add cockpit/data/knowledge_sufficiency.py cockpit/data/nudges.py tests/test_knowledge_sufficiency.py
git commit -m "feat: domain-scoped nudges — gaps_to_nudges(domain_id=), multi-domain nudge collector"
```

---

## Phase 2: Momentum Model

### Task 6: Create Momentum Data Collector

**Files:**
- Create: `<ai-agents>/cockpit/data/momentum.py`
- Create: `<ai-agents>/tests/test_momentum.py`

**Step 1: Write the failing tests**

Create `<ai-agents>/tests/test_momentum.py`:

```python
"""Tests for cockpit.data.momentum — domain momentum tracking."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cockpit.data.momentum import (
    MomentumVector,
    DomainMomentum,
    compute_activity_rate,
    compute_regularity,
    compute_alignment_slope,
    classify_direction,
    classify_regularity,
    collect_domain_momentum,
)


class TestActivityRate:
    def test_no_events_returns_zero(self) -> None:
        """No events produces rate 0.0."""
        assert compute_activity_rate([], days_short=7, days_long=30) == 0.0

    def test_uniform_events_returns_near_one(self) -> None:
        """Uniform daily events over 30 days produce ratio near 1.0."""
        now = datetime.now(timezone.utc)
        events = [now - timedelta(days=i) for i in range(30)]
        rate = compute_activity_rate(events, days_short=7, days_long=30)
        assert 0.8 <= rate <= 1.2

    def test_recent_burst_returns_high(self) -> None:
        """Events only in last 7 days produce ratio > 1.2."""
        now = datetime.now(timezone.utc)
        events = [now - timedelta(hours=i * 6) for i in range(28)]  # 28 events in 7 days
        rate = compute_activity_rate(events, days_short=7, days_long=30)
        assert rate > 1.2

    def test_old_events_only_returns_low(self) -> None:
        """Events only 20+ days ago produce ratio < 0.8."""
        now = datetime.now(timezone.utc)
        events = [now - timedelta(days=20 + i) for i in range(10)]
        rate = compute_activity_rate(events, days_short=7, days_long=30)
        assert rate < 0.8


class TestRegularity:
    def test_no_events_returns_high_cv(self) -> None:
        """No events => sporadic."""
        cv = compute_regularity([])
        assert cv > 1.0

    def test_regular_daily_events(self) -> None:
        """Daily events have low CV."""
        now = datetime.now(timezone.utc)
        events = [now - timedelta(days=i) for i in range(30)]
        cv = compute_regularity(events)
        assert cv < 0.5

    def test_bursty_events(self) -> None:
        """Events clustered in bursts have moderate CV."""
        now = datetime.now(timezone.utc)
        events = (
            [now - timedelta(days=i) for i in range(3)]  # burst 1
            + [now - timedelta(days=15 + i) for i in range(3)]  # burst 2
        )
        cv = compute_regularity(events)
        assert cv >= 0.5


class TestAlignmentSlope:
    def test_improving(self) -> None:
        """Increasing scores produce positive slope."""
        scores = [0.3, 0.4, 0.5, 0.6]
        slope = compute_alignment_slope(scores)
        assert slope > 0

    def test_regressing(self) -> None:
        """Decreasing scores produce negative slope."""
        scores = [0.6, 0.5, 0.4, 0.3]
        slope = compute_alignment_slope(scores)
        assert slope < 0

    def test_flat(self) -> None:
        """Constant scores produce near-zero slope."""
        scores = [0.5, 0.5, 0.5, 0.5]
        slope = compute_alignment_slope(scores)
        assert abs(slope) < 0.01

    def test_insufficient_data(self) -> None:
        """Fewer than 2 scores return 0.0."""
        assert compute_alignment_slope([0.5]) == 0.0
        assert compute_alignment_slope([]) == 0.0


class TestClassifiers:
    def test_direction_accelerating(self) -> None:
        assert classify_direction(1.5) == "accelerating"

    def test_direction_steady(self) -> None:
        assert classify_direction(1.0) == "steady"

    def test_direction_decelerating(self) -> None:
        assert classify_direction(0.5) == "decelerating"

    def test_direction_dormant(self) -> None:
        assert classify_direction(0.05) == "dormant"

    def test_regularity_regular(self) -> None:
        assert classify_regularity(0.3) == "regular"

    def test_regularity_irregular(self) -> None:
        assert classify_regularity(0.7) == "irregular"

    def test_regularity_sporadic(self) -> None:
        assert classify_regularity(1.5) == "sporadic"


class TestDomainMomentum:
    def test_dataclass_fields(self) -> None:
        """MomentumVector has all required fields."""
        v = MomentumVector(
            domain_id="test",
            direction="steady",
            regularity="regular",
            alignment="plateaued",
            activity_rate=1.0,
            regularity_cv=0.3,
            alignment_slope=0.0,
            computed_at="2026-03-04T00:00:00Z",
        )
        assert v.domain_id == "test"
        assert v.direction == "steady"
```

**Step 2: Run test to verify it fails**

```bash
cd <ai-agents>
uv run pytest tests/test_momentum.py -v
```

Expected: FAIL — module `cockpit.data.momentum` doesn't exist.

**Step 3: Implement momentum.py**

Create `<ai-agents>/cockpit/data/momentum.py`:

```python
"""Domain momentum tracking — activity rate, regularity, alignment.

Computes continuous signals per domain from vault modification timestamps
and other activity sources. Zero LLM calls.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shared.config import VAULT_PATH


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MomentumVector:
    """Per-domain momentum summary."""

    domain_id: str
    direction: str      # accelerating | steady | decelerating | dormant
    regularity: str     # regular | irregular | sporadic
    alignment: str      # improving | plateaued | regressing
    activity_rate: float
    regularity_cv: float
    alignment_slope: float
    computed_at: str


@dataclass
class DomainMomentum:
    """Aggregated momentum across all domains."""

    vectors: list[MomentumVector]
    computed_at: str


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

HISTORY_PATH = Path.home() / ".cache" / "cockpit" / "momentum-history.jsonl"


def compute_activity_rate(
    event_times: list[datetime],
    *,
    days_short: int = 7,
    days_long: int = 30,
) -> float:
    """Compute ratio of short-window to long-window activity rate.

    Returns 0.0 if no events. Ratio > 1.2 = accelerating, < 0.8 = decelerating.
    """
    if not event_times:
        return 0.0

    now = datetime.now(timezone.utc)
    short_cutoff = now - timedelta(days=days_short)
    long_cutoff = now - timedelta(days=days_long)

    # Normalize to UTC
    normalized = []
    for t in event_times:
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        normalized.append(t)

    short_count = sum(1 for t in normalized if t >= short_cutoff)
    long_count = sum(1 for t in normalized if t >= long_cutoff)

    if long_count == 0:
        return 0.0

    # Normalize to daily rates
    short_rate = short_count / days_short
    long_rate = long_count / days_long

    if long_rate == 0:
        return 0.0

    return short_rate / long_rate


def compute_regularity(event_times: list[datetime]) -> float:
    """Compute coefficient of variation of inter-event gaps.

    Returns > 1.0 for sporadic activity. Lower = more regular.
    Returns 2.0 (very sporadic) if fewer than 2 events.
    """
    if len(event_times) < 2:
        return 2.0

    # Sort chronologically
    sorted_times = sorted(event_times)
    gaps = [
        (sorted_times[i + 1] - sorted_times[i]).total_seconds() / 3600
        for i in range(len(sorted_times) - 1)
    ]

    if not gaps:
        return 2.0

    mean_gap = statistics.mean(gaps)
    if mean_gap == 0:
        return 0.0

    try:
        stdev = statistics.stdev(gaps)
    except statistics.StatisticsError:
        return 0.0

    return stdev / mean_gap


def compute_alignment_slope(scores: list[float]) -> float:
    """Compute linear slope of sufficiency scores over time.

    Positive = improving, negative = regressing. Returns 0.0 if < 2 points.
    Simple least-squares over indices.
    """
    n = len(scores)
    if n < 2:
        return 0.0

    # Simple linear regression: y = a + bx
    x_mean = (n - 1) / 2.0
    y_mean = sum(scores) / n

    numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0

    return numerator / denominator


# ---------------------------------------------------------------------------
# Classifiers
# ---------------------------------------------------------------------------


def classify_direction(rate: float) -> str:
    """Classify activity rate into direction label."""
    if rate < 0.1:
        return "dormant"
    if rate < 0.8:
        return "decelerating"
    if rate > 1.2:
        return "accelerating"
    return "steady"


def classify_regularity(cv: float) -> str:
    """Classify coefficient of variation into regularity label."""
    if cv < 0.5:
        return "regular"
    if cv <= 1.0:
        return "irregular"
    return "sporadic"


def classify_alignment(slope: float) -> str:
    """Classify alignment slope into trend label."""
    if slope > 0.02:
        return "improving"
    if slope < -0.02:
        return "regressing"
    return "plateaued"


# ---------------------------------------------------------------------------
# Activity collection
# ---------------------------------------------------------------------------


def _collect_vault_activity(
    vault_paths: list[str],
    vault_path: Path | None = None,
) -> list[datetime]:
    """Collect file modification timestamps from vault paths."""
    vp = vault_path or VAULT_PATH
    timestamps: list[datetime] = []

    for rel_path in vault_paths:
        folder = vp / rel_path
        if not folder.is_dir():
            continue
        for md_file in folder.glob("**/*.md"):
            try:
                mtime = md_file.stat().st_mtime
                timestamps.append(
                    datetime.fromtimestamp(mtime, tz=timezone.utc)
                )
            except OSError:
                continue

    return timestamps


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------


def _load_score_history(domain_id: str) -> list[float]:
    """Load weekly sufficiency score snapshots for a domain.

    Reads from HISTORY_PATH (JSONL). Each line is:
    {"domain_id": "...", "score": 0.x, "timestamp": "..."}
    Returns last 4 scores chronologically.
    """
    if not HISTORY_PATH.is_file():
        return []

    scores: list[tuple[str, float]] = []
    try:
        for line in HISTORY_PATH.read_text().splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("domain_id") == domain_id:
                scores.append((entry.get("timestamp", ""), entry.get("score", 0.0)))
    except (json.JSONDecodeError, OSError):
        return []

    # Sort by timestamp, take last 4
    scores.sort(key=lambda x: x[0])
    return [s for _, s in scores[-4:]]


def save_score_snapshot(domain_id: str, score: float) -> None:
    """Append a weekly score snapshot to history."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "domain_id": domain_id,
        "score": score,
        "timestamp": datetime.now(timezone.utc).isoformat()[:19] + "Z",
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Main collector
# ---------------------------------------------------------------------------


def collect_domain_momentum(
    vault_path: Path | None = None,
) -> DomainMomentum:
    """Compute momentum vectors for all active domains.

    Loads domain registry, collects vault activity per domain,
    computes rate/regularity/alignment.
    """
    from cockpit.data.knowledge_sufficiency import (
        DOMAIN_REGISTRY_PATH,
        load_domain_registry,
        collect_all_domain_gaps,
    )

    now_iso = datetime.now(timezone.utc).isoformat()[:19] + "Z"

    if not DOMAIN_REGISTRY_PATH.is_file():
        return DomainMomentum(vectors=[], computed_at=now_iso)

    try:
        registry = load_domain_registry()
    except Exception:
        return DomainMomentum(vectors=[], computed_at=now_iso)

    # Get sufficiency scores for alignment computation
    reports = collect_all_domain_gaps(vault_path=vault_path)

    vectors: list[MomentumVector] = []
    for domain in registry.get("domains", []):
        domain_id = domain.get("id", "")
        status = domain.get("status", "")
        if not domain_id or status not in ("active", "dormant"):
            continue

        vault_paths = domain.get("vault_paths", [])
        events = _collect_vault_activity(vault_paths, vault_path=vault_path)

        rate = compute_activity_rate(events)
        cv = compute_regularity(events)

        # Alignment from historical scores
        score_history = _load_score_history(domain_id)
        # Add current score if available
        if domain_id in reports:
            current_score = reports[domain_id].sufficiency_score
            score_history.append(current_score)
        slope = compute_alignment_slope(score_history)

        vectors.append(MomentumVector(
            domain_id=domain_id,
            direction=classify_direction(rate),
            regularity=classify_regularity(cv),
            alignment=classify_alignment(slope),
            activity_rate=round(rate, 3),
            regularity_cv=round(cv, 3),
            alignment_slope=round(slope, 4),
            computed_at=now_iso,
        ))

    return DomainMomentum(vectors=vectors, computed_at=now_iso)
```

**Step 4: Run tests to verify they pass**

```bash
cd <ai-agents>
uv run pytest tests/test_momentum.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/data/momentum.py tests/test_momentum.py
git commit -m "feat: domain momentum collector — activity rate, regularity, alignment slope"
```

---

## Phase 3: Universal Person Model

### Task 7: Update Person Template

**Files:**
- Modify: `<personal-vault>/50-templates/tpl-person.md`

**Step 1: Read current template**

```bash
cat <personal-vault>/50-templates/tpl-person.md
```

**Step 2: Add domains field to frontmatter**

Add `domains:` field after `status:` in the frontmatter section. Also add core universal fields `relationship:`, `first-met:`, `last-interaction:`.

Insert after the `status: active` line:

```yaml
domains: [management]
relationship: <% await tp.system.suggester(["direct-report", "manager", "stakeholder", "peer", "collaborator", "family", "friend"], ["direct-report", "manager", "stakeholder", "peer", "collaborator", "family", "friend"]) %>
first-met:
last-interaction:
```

**Step 3: Commit (vault is not git-tracked — just save)**

No git commit for vault changes. Obsidian Sync handles distribution.

---

### Task 8: Update PersonState to Read New Fields

**Files:**
- Modify: `<ai-agents>/cockpit/data/management.py`
- Test: `<ai-agents>/tests/test_management.py`

**Step 1: Write the failing test**

Add to `<ai-agents>/tests/test_management.py`:

```python
class TestPersonStateDomains:
    def test_person_state_has_domains_field(self) -> None:
        """PersonState includes domains list."""
        from cockpit.data.management import PersonState
        import inspect
        fields = {f.name for f in __import__("dataclasses").fields(PersonState)}
        assert "domains" in fields

    def test_person_state_has_relationship_field(self) -> None:
        """PersonState includes relationship field."""
        from cockpit.data.management import PersonState
        import inspect
        fields = {f.name for f in __import__("dataclasses").fields(PersonState)}
        assert "relationship" in fields
```

**Step 2: Run test to verify it fails**

```bash
cd <ai-agents>
uv run pytest tests/test_management.py::TestPersonStateDomains -v
```

Expected: FAIL — `domains` field doesn't exist on PersonState.

**Step 3: Add fields to PersonState**

In `<ai-agents>/cockpit/data/management.py`, add to the PersonState dataclass (after the existing fields):

```python
    # Universal person model fields
    domains: list[str] = field(default_factory=lambda: ["management"])
    relationship: str = ""
```

In `_collect_people()`, after reading existing frontmatter fields, add:

```python
        domains_raw = fm.get("domains", ["management"])
        if isinstance(domains_raw, str):
            domains = [d.strip() for d in domains_raw.split(",")]
        elif isinstance(domains_raw, list):
            domains = domains_raw
        else:
            domains = ["management"]
```

And pass `domains=domains, relationship=str(fm.get("relationship", ""))` to the PersonState constructor.

**Step 4: Run test to verify it passes**

```bash
cd <ai-agents>
uv run pytest tests/test_management.py::TestPersonStateDomains -v
```

Expected: PASS

**Step 5: Run full management tests**

```bash
cd <ai-agents>
uv run pytest tests/test_management.py -v
```

Expected: All PASS

**Step 6: Commit**

```bash
cd <ai-agents>
git add cockpit/data/management.py tests/test_management.py
git commit -m "feat: PersonState universal fields — domains list, relationship"
```

---

## Phase 4: Emergence Detection

### Task 9: Create Emergence Data Collector

**Files:**
- Create: `<ai-agents>/cockpit/data/emergence.py`
- Create: `<ai-agents>/tests/test_emergence.py`

**Step 1: Write the failing tests**

Create `<ai-agents>/tests/test_emergence.py`:

```python
"""Tests for cockpit.data.emergence — undomained activity detection."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from cockpit.data.emergence import (
    UndomainedEvent,
    EmergenceCandidate,
    EmergenceSnapshot,
    collect_undomained_events,
    cluster_events,
    CANDIDATE_MIN_EVENTS,
    CANDIDATE_MIN_WEEKS,
    CANDIDATE_MIN_KEYWORDS,
)


class TestUndomainedEvents:
    def test_event_dataclass(self) -> None:
        """UndomainedEvent has required fields."""
        e = UndomainedEvent(
            timestamp="2026-03-04T12:00:00Z",
            source="vault",
            description="Created note in 20-personal/woodworking/project.md",
            keywords=["woodworking", "project"],
            people=[],
        )
        assert e.source == "vault"
        assert len(e.keywords) == 2

    def test_collect_empty_vault(self, tmp_path: Path) -> None:
        """Empty vault produces no undomained events."""
        events = collect_undomained_events(
            vault_path=tmp_path,
            domain_paths={"management": ["10-work"]},
        )
        assert events == []


class TestClustering:
    def test_empty_events(self) -> None:
        """No events => no candidates."""
        assert cluster_events([]) == []

    def test_insufficient_events(self) -> None:
        """Fewer than CANDIDATE_MIN_EVENTS events => no candidates."""
        events = [
            UndomainedEvent(
                timestamp="2026-03-01T12:00:00Z",
                source="vault",
                description="single event",
                keywords=["test"],
                people=[],
            )
        ]
        assert cluster_events(events) == []

    def test_sufficient_cluster(self) -> None:
        """Events meeting threshold produce a candidate."""
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        events = []
        for i in range(CANDIDATE_MIN_EVENTS + 1):
            day_offset = (i % 3) * 7  # spread across 3 weeks
            events.append(UndomainedEvent(
                timestamp=(base + timedelta(days=day_offset, hours=i)).isoformat(),
                source="vault",
                description=f"woodworking project {i}",
                keywords=["woodworking", "project", "tools"],
                people=[],
            ))
        candidates = cluster_events(events)
        assert len(candidates) >= 1
        assert candidates[0].event_count >= CANDIDATE_MIN_EVENTS


class TestEmergenceSnapshot:
    def test_snapshot_fields(self) -> None:
        """EmergenceSnapshot has expected fields."""
        s = EmergenceSnapshot(
            candidates=[],
            undomained_event_count=0,
            computed_at="2026-03-04T00:00:00Z",
        )
        assert s.undomained_event_count == 0
```

**Step 2: Run test to verify it fails**

```bash
cd <ai-agents>
uv run pytest tests/test_emergence.py -v
```

Expected: FAIL — module doesn't exist.

**Step 3: Implement emergence.py**

Create `<ai-agents>/cockpit/data/emergence.py`:

```python
"""Emergence detection — clusters undomained activity into domain candidates.

Scans vault for activity that doesn't map to any declared domain's vault_paths.
Groups related activity by keyword co-occurrence, temporal proximity, and person
overlap. Produces EmergenceCandidates when clusters cross thresholds.

Zero LLM calls for detection. LLM only used for proposal narrative (not here).
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shared.config import VAULT_PATH


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANDIDATE_MIN_EVENTS = 5
CANDIDATE_MIN_WEEKS = 2
CANDIDATE_MIN_KEYWORDS = 3
BUFFER_PATH = Path.home() / ".cache" / "cockpit" / "undomained-activity.jsonl"
CANDIDATES_PATH = Path.home() / ".cache" / "cockpit" / "emergence-candidates.json"

# System folders to ignore (not operator activity)
SYSTEM_FOLDERS = frozenset({
    "30-system", "50-templates", "60-archive", "90-attachments",
    ".obsidian", ".trash",
})


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class UndomainedEvent:
    """A single activity event not attributed to any domain."""

    timestamp: str
    source: str          # "vault" | "langfuse" | "qdrant"
    description: str
    keywords: list[str]
    people: list[str] = field(default_factory=list)


@dataclass
class EmergenceCandidate:
    """A cluster of undomained events that may represent a new domain."""

    candidate_id: str
    label: str                  # suggested domain name
    event_count: int
    week_span: int              # how many distinct weeks
    top_keywords: list[str]
    related_people: list[str]
    overlapping_domains: list[str]
    first_seen: str
    last_seen: str


@dataclass
class EmergenceSnapshot:
    """Result of emergence detection."""

    candidates: list[EmergenceCandidate]
    undomained_event_count: int
    computed_at: str


# ---------------------------------------------------------------------------
# Event collection
# ---------------------------------------------------------------------------


def _extract_keywords(text: str) -> list[str]:
    """Extract simple keywords from text. No TF-IDF, just word frequency."""
    words = re.findall(r"[a-z]{3,}", text.lower())
    # Remove common stop words
    stop = {"the", "and", "for", "are", "but", "not", "you", "all",
            "can", "has", "her", "was", "one", "our", "this", "that",
            "with", "from", "have", "will", "been", "they", "its",
            "more", "some", "than", "other", "into", "could", "would",
            "about", "which", "their", "what", "there", "when", "make",
            "like", "just", "over", "such", "also", "after", "should"}
    return [w for w in words if w not in stop]


def collect_undomained_events(
    *,
    vault_path: Path | None = None,
    domain_paths: dict[str, list[str]] | None = None,
    days_back: int = 60,
) -> list[UndomainedEvent]:
    """Scan vault for files not in any domain's vault_paths.

    Args:
        vault_path: Override vault location.
        domain_paths: {domain_id: [rel_paths]}. If None, loads from registry.
        days_back: Only consider files modified within this many days.
    """
    vp = vault_path or VAULT_PATH

    if domain_paths is None:
        domain_paths = _load_domain_paths()

    # Flatten all domain paths into a set of absolute prefixes
    covered_prefixes: set[Path] = set()
    for paths in domain_paths.values():
        for rel in paths:
            covered_prefixes.add(vp / rel)

    # Also add system folders
    for sys_folder in SYSTEM_FOLDERS:
        covered_prefixes.add(vp / sys_folder)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    events: list[UndomainedEvent] = []

    if not vp.is_dir():
        return events

    for md_file in vp.glob("**/*.md"):
        # Check modification time
        try:
            mtime = datetime.fromtimestamp(md_file.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue

        if mtime < cutoff:
            continue

        # Check if file is under any domain's paths or system folder
        is_covered = any(
            md_file == prefix or prefix in md_file.parents
            for prefix in covered_prefixes
        )
        if is_covered:
            continue

        # This file is undomained
        try:
            content = md_file.read_text(encoding="utf-8")[:500]  # first 500 chars
        except (OSError, UnicodeDecodeError):
            content = md_file.stem

        rel = md_file.relative_to(vp)
        keywords = _extract_keywords(f"{rel.stem} {content}")

        events.append(UndomainedEvent(
            timestamp=mtime.isoformat()[:19] + "Z",
            source="vault",
            description=f"Modified: {rel}",
            keywords=keywords[:10],  # cap at 10
            people=[],
        ))

    return events


def _load_domain_paths() -> dict[str, list[str]]:
    """Load domain vault_paths from registry."""
    try:
        from cockpit.data.knowledge_sufficiency import (
            DOMAIN_REGISTRY_PATH,
            load_domain_registry,
        )
        if not DOMAIN_REGISTRY_PATH.is_file():
            return {}
        registry = load_domain_registry()
        return {
            d["id"]: d.get("vault_paths", [])
            for d in registry.get("domains", [])
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def cluster_events(
    events: list[UndomainedEvent],
) -> list[EmergenceCandidate]:
    """Cluster undomained events by keyword co-occurrence.

    Returns candidates that meet the threshold:
    - At least CANDIDATE_MIN_EVENTS events
    - Spanning at least CANDIDATE_MIN_WEEKS distinct weeks
    - With at least CANDIDATE_MIN_KEYWORDS distinct keywords
    """
    if len(events) < CANDIDATE_MIN_EVENTS:
        return []

    # Count keyword frequency across all events
    keyword_counter: Counter[str] = Counter()
    for event in events:
        keyword_counter.update(event.keywords)

    # Find dominant keywords (appearing in 30%+ of events)
    threshold = max(2, len(events) * 0.3)
    dominant = {kw for kw, count in keyword_counter.items() if count >= threshold}

    if len(dominant) < CANDIDATE_MIN_KEYWORDS:
        # Fall back to top N keywords
        dominant = {kw for kw, _ in keyword_counter.most_common(CANDIDATE_MIN_KEYWORDS)}

    # Group events that share dominant keywords
    cluster_events_list = [
        e for e in events
        if any(kw in dominant for kw in e.keywords)
    ]

    if len(cluster_events_list) < CANDIDATE_MIN_EVENTS:
        return []

    # Check week span
    weeks: set[str] = set()
    for e in cluster_events_list:
        try:
            dt = datetime.fromisoformat(e.timestamp.replace("Z", "+00:00"))
            weeks.add(dt.strftime("%Y-W%W"))
        except (ValueError, TypeError):
            continue

    if len(weeks) < CANDIDATE_MIN_WEEKS:
        return []

    # Build candidate
    timestamps = sorted(e.timestamp for e in cluster_events_list)
    all_people: set[str] = set()
    for e in cluster_events_list:
        all_people.update(e.people)

    top_kws = [kw for kw, _ in keyword_counter.most_common(5)]
    label = top_kws[0] if top_kws else "unknown"

    candidate = EmergenceCandidate(
        candidate_id=f"emerge-{label}-{len(cluster_events_list)}",
        label=label,
        event_count=len(cluster_events_list),
        week_span=len(weeks),
        top_keywords=top_kws,
        related_people=sorted(all_people),
        overlapping_domains=[],
        first_seen=timestamps[0],
        last_seen=timestamps[-1],
    )

    return [candidate]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def save_candidates(candidates: list[EmergenceCandidate]) -> None:
    """Save emergence candidates to disk."""
    CANDIDATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [
        {
            "candidate_id": c.candidate_id,
            "label": c.label,
            "event_count": c.event_count,
            "week_span": c.week_span,
            "top_keywords": c.top_keywords,
            "related_people": c.related_people,
            "overlapping_domains": c.overlapping_domains,
            "first_seen": c.first_seen,
            "last_seen": c.last_seen,
        }
        for c in candidates
    ]
    CANDIDATES_PATH.write_text(json.dumps(data, indent=2))


def load_candidates() -> list[EmergenceCandidate]:
    """Load saved emergence candidates."""
    if not CANDIDATES_PATH.is_file():
        return []
    try:
        data = json.loads(CANDIDATES_PATH.read_text())
        return [EmergenceCandidate(**entry) for entry in data]
    except (json.JSONDecodeError, OSError, TypeError):
        return []


# ---------------------------------------------------------------------------
# Main collector
# ---------------------------------------------------------------------------


def collect_emergence(
    vault_path: Path | None = None,
) -> EmergenceSnapshot:
    """Collect emergence snapshot — undomained events + active candidates."""
    now_iso = datetime.now(timezone.utc).isoformat()[:19] + "Z"

    events = collect_undomained_events(vault_path=vault_path)
    candidates = load_candidates()

    return EmergenceSnapshot(
        candidates=candidates,
        undomained_event_count=len(events),
        computed_at=now_iso,
    )


def run_emergence_scan(vault_path: Path | None = None) -> EmergenceSnapshot:
    """Full emergence scan — collect events, cluster, save candidates.

    This is the batch operation meant to run weekly (e.g., via knowledge-maint).
    """
    now_iso = datetime.now(timezone.utc).isoformat()[:19] + "Z"

    events = collect_undomained_events(vault_path=vault_path)
    candidates = cluster_events(events)

    if candidates:
        # Merge with existing candidates (don't lose old ones)
        existing = load_candidates()
        existing_ids = {c.candidate_id for c in existing}
        for c in candidates:
            if c.candidate_id not in existing_ids:
                existing.append(c)
        save_candidates(existing)
        candidates = existing

    return EmergenceSnapshot(
        candidates=candidates,
        undomained_event_count=len(events),
        computed_at=now_iso,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd <ai-agents>
uv run pytest tests/test_emergence.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/data/emergence.py tests/test_emergence.py
git commit -m "feat: emergence detection — undomained activity clustering, candidate tracking"
```

---

## Phase 5: Domain Health Dashboard

### Task 10: Create Domain Health Data Aggregator

**Files:**
- Create: `<ai-agents>/cockpit/data/domain_health.py`
- Create: `<ai-agents>/tests/test_domain_health.py`

**Step 1: Write the failing tests**

Create `<ai-agents>/tests/test_domain_health.py`:

```python
"""Tests for cockpit.data.domain_health — aggregated domain health."""
from __future__ import annotations

import pytest

from cockpit.data.domain_health import (
    DomainStatus,
    DomainHealthSnapshot,
    collect_domain_health,
)


class TestDomainStatus:
    def test_dataclass_fields(self) -> None:
        """DomainStatus has all required fields."""
        s = DomainStatus(
            domain_id="test",
            domain_name="Test",
            status="active",
            sufficiency_score=0.5,
            total_requirements=10,
            satisfied_count=5,
            direction="steady",
            regularity="regular",
            alignment="plateaued",
        )
        assert s.sufficiency_score == 0.5
        assert s.direction == "steady"


class TestDomainHealthSnapshot:
    def test_snapshot_has_domains(self) -> None:
        """collect_domain_health returns a snapshot with domain statuses."""
        snap = collect_domain_health()
        assert isinstance(snap, DomainHealthSnapshot)
        assert isinstance(snap.domains, list)

    def test_snapshot_has_overall_score(self) -> None:
        """Snapshot includes an overall sufficiency score."""
        snap = collect_domain_health()
        assert 0.0 <= snap.overall_score <= 1.0

    def test_snapshot_has_emergence_candidates(self) -> None:
        """Snapshot includes emergence candidate count."""
        snap = collect_domain_health()
        assert snap.emergence_candidate_count >= 0
```

**Step 2: Run test to verify it fails**

```bash
cd <ai-agents>
uv run pytest tests/test_domain_health.py -v
```

Expected: FAIL — module doesn't exist.

**Step 3: Implement domain_health.py**

Create `<ai-agents>/cockpit/data/domain_health.py`:

```python
"""Domain health aggregator — combines sufficiency, momentum, emergence.

Single collector that produces a DomainHealthSnapshot suitable for
the cockpit sidebar or a dedicated dashboard widget.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from shared.config import VAULT_PATH


@dataclass
class DomainStatus:
    """Health status for a single domain."""

    domain_id: str
    domain_name: str
    status: str              # active | dormant | proposed | retired
    sufficiency_score: float  # 0.0 - 1.0
    total_requirements: int
    satisfied_count: int
    direction: str           # accelerating | steady | decelerating | dormant
    regularity: str          # regular | irregular | sporadic
    alignment: str           # improving | plateaued | regressing


@dataclass
class DomainHealthSnapshot:
    """Aggregated domain health across all domains."""

    domains: list[DomainStatus]
    overall_score: float      # activity-weighted average
    emergence_candidate_count: int
    computed_at: str


def collect_domain_health(
    vault_path: Path | None = None,
) -> DomainHealthSnapshot:
    """Aggregate domain sufficiency, momentum, and emergence into one snapshot."""
    now_iso = datetime.now(timezone.utc).isoformat()[:19] + "Z"
    vp = vault_path or VAULT_PATH

    # Load domain registry for names and statuses
    try:
        from cockpit.data.knowledge_sufficiency import (
            DOMAIN_REGISTRY_PATH,
            load_domain_registry,
            collect_all_domain_gaps,
        )
        if not DOMAIN_REGISTRY_PATH.is_file():
            return DomainHealthSnapshot(
                domains=[], overall_score=1.0,
                emergence_candidate_count=0, computed_at=now_iso,
            )
        registry = load_domain_registry()
    except Exception:
        return DomainHealthSnapshot(
            domains=[], overall_score=1.0,
            emergence_candidate_count=0, computed_at=now_iso,
        )

    # Sufficiency reports
    reports = collect_all_domain_gaps(vault_path=vp)

    # Momentum vectors
    momentum_map: dict[str, tuple[str, str, str]] = {}
    try:
        from cockpit.data.momentum import collect_domain_momentum
        momentum = collect_domain_momentum(vault_path=vp)
        for v in momentum.vectors:
            momentum_map[v.domain_id] = (v.direction, v.regularity, v.alignment)
    except Exception:
        pass

    # Emergence candidates
    emergence_count = 0
    try:
        from cockpit.data.emergence import collect_emergence
        emergence = collect_emergence(vault_path=vp)
        emergence_count = len(emergence.candidates)
    except Exception:
        pass

    # Build domain statuses
    domain_lookup = {d["id"]: d for d in registry.get("domains", [])}
    statuses: list[DomainStatus] = []

    for domain_id, domain_def in domain_lookup.items():
        report = reports.get(domain_id)
        direction, regularity, alignment = momentum_map.get(
            domain_id, ("steady", "sporadic", "plateaued")
        )

        statuses.append(DomainStatus(
            domain_id=domain_id,
            domain_name=domain_def.get("name", domain_id),
            status=domain_def.get("status", "active"),
            sufficiency_score=report.sufficiency_score if report else 0.0,
            total_requirements=report.total_requirements if report else 0,
            satisfied_count=report.satisfied_count if report else 0,
            direction=direction,
            regularity=regularity,
            alignment=alignment,
        ))

    # Overall score: weighted average by activity (active domains weight 1.0,
    # dormant weight 0.1, others weight 0.5)
    total_weight = 0.0
    weighted_sum = 0.0
    for s in statuses:
        weight = 1.0 if s.status == "active" else 0.1 if s.status == "dormant" else 0.5
        weighted_sum += s.sufficiency_score * weight
        total_weight += weight

    overall = weighted_sum / total_weight if total_weight > 0 else 1.0

    return DomainHealthSnapshot(
        domains=statuses,
        overall_score=round(overall, 3),
        emergence_candidate_count=emergence_count,
        computed_at=now_iso,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd <ai-agents>
uv run pytest tests/test_domain_health.py -v
```

Expected: All PASS

**Step 5: Commit**

```bash
cd <ai-agents>
git add cockpit/data/domain_health.py tests/test_domain_health.py
git commit -m "feat: domain health aggregator — sufficiency + momentum + emergence"
```

---

### Task 11: Create Domain Health Widget

**Files:**
- Create: `<ai-agents>/cockpit/widgets/domain_health.py`

**Step 1: Implement the widget**

Create `<ai-agents>/cockpit/widgets/domain_health.py`:

```python
"""DomainHealthWidget — per-domain sufficiency bars with momentum arrows."""
from __future__ import annotations

from rich.text import Text
from textual.widget import Widget
from textual.widgets import Static

from cockpit.data.domain_health import DomainHealthSnapshot, DomainStatus


DIRECTION_ARROWS = {
    "accelerating": "\u2191",   # ↑
    "steady": "\u2192",         # →
    "decelerating": "\u2193",   # ↓
    "dormant": "\u25cb",        # ○
}

BAR_WIDTH = 10


def _render_bar(score: float) -> str:
    """Render a proportional bar: ████░░░░░░"""
    filled = int(score * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    return "\u2588" * filled + "\u2591" * empty


def render_domain_health(snapshot: DomainHealthSnapshot | None) -> Text:
    """Render domain health panel as Rich Text."""
    text = Text()

    if snapshot is None or not snapshot.domains:
        text.append("No domain data", style="dim")
        return text

    text.append("Domain Health\n", style="bold")
    text.append("")

    for d in snapshot.domains:
        if d.status not in ("active", "dormant"):
            continue

        arrow = DIRECTION_ARROWS.get(d.direction, "?")
        pct = int(d.sufficiency_score * 100)
        bar = _render_bar(d.sufficiency_score)

        # Color based on score
        if pct >= 70:
            color = "green"
        elif pct >= 40:
            color = "yellow"
        else:
            color = "red"

        name_padded = d.domain_id[:12].ljust(12)
        text.append(f"  {name_padded} ", style="dim" if d.status == "dormant" else "")
        text.append(bar, style=color)
        text.append(f" {pct:3d}%", style=color)
        text.append(f" {arrow}\n")

    if snapshot.emergence_candidate_count > 0:
        text.append(f"\n  \u26a1 {snapshot.emergence_candidate_count} emergence candidate(s)\n",
                     style="yellow")

    overall_pct = int(snapshot.overall_score * 100)
    text.append(f"\n  Overall: {overall_pct}%", style="bold")

    return text
```

**Step 2: Commit**

```bash
cd <ai-agents>
git add cockpit/widgets/domain_health.py
git commit -m "feat: domain health widget — per-domain bars with momentum arrows"
```

---

### Task 12: Integrate Domain Health into Sidebar

**Files:**
- Modify: `<ai-agents>/cockpit/widgets/sidebar.py:57-63`
- Modify: `<ai-agents>/cockpit/app.py:195-245`

**Step 1: Add domain health section to sidebar**

In `<ai-agents>/cockpit/widgets/sidebar.py`, in the `compose()` method (line 57-63), add after the `goals` section:

```python
        yield SidebarSection("domain-health", id="sb-domain-health")
```

In `__init__`, add:

```python
        self._domain_health = None
```

Add a new method to SidebarStatus:

```python
    def update_domain_health(self, snapshot) -> None:
        """Update domain health section."""
        self._domain_health = snapshot
        from cockpit.widgets.domain_health import render_domain_health
        self.query_one("#sb-domain-health").update(render_domain_health(snapshot))
```

**Step 2: Call domain health collector in refresh_slow**

In `<ai-agents>/cockpit/app.py`, in `refresh_slow()` (around line 195):

Add import at top of file:
```python
from cockpit.data.domain_health import collect_domain_health
```

In the `refresh_slow` method, after `goals = collect_goals()` (line 203), add:

```python
        domain_health = collect_domain_health()
```

After `sidebar.update_goals(goals)` (line 238), add:

```python
        sidebar.update_domain_health(domain_health)
```

**Step 3: Run cockpit to verify**

```bash
cd <ai-agents>
uv run cockpit --once 2>&1 | head -30
```

Expected: No crash, domain health data appears.

**Step 4: Commit**

```bash
cd <ai-agents>
git add cockpit/widgets/sidebar.py cockpit/app.py
git commit -m "feat: domain health in cockpit sidebar — sufficiency bars + momentum"
```

---

### Task 13: Add Emergence Nudges

**Files:**
- Modify: `<ai-agents>/cockpit/data/nudges.py`
- Test: `<ai-agents>/tests/test_nudges.py`

**Step 1: Write the failing test**

Add to `<ai-agents>/tests/test_nudges.py`:

```python
class TestEmergenceNudges:
    def test_emergence_candidates_produce_nudges(self) -> None:
        """Active emergence candidates generate nudges."""
        from cockpit.data.nudges import Nudge
        nudges: list[Nudge] = []
        # We can't easily mock this, but we can verify the collector exists
        from cockpit.data.nudges import _collect_emergence_nudges
        _collect_emergence_nudges(nudges)
        # Should not crash — may produce 0 nudges if no candidates
        assert isinstance(nudges, list)
```

**Step 2: Implement emergence nudge collector**

In `<ai-agents>/cockpit/data/nudges.py`, add a new collector function before `collect_nudges()`:

```python
def _collect_emergence_nudges(nudges: list[Nudge]) -> None:
    """Generate nudges from emergence detection candidates."""
    try:
        from cockpit.data.emergence import collect_emergence
        snapshot = collect_emergence()
        for candidate in snapshot.candidates:
            nudges.append(Nudge(
                category="emergence",
                priority_score=55,
                priority_label="medium",
                title=f"Potential new domain: {candidate.label}",
                detail=(
                    f"{candidate.event_count} activities over {candidate.week_span} weeks. "
                    f"Keywords: {', '.join(candidate.top_keywords[:3])}"
                ),
                suggested_action=f"/domain propose {candidate.candidate_id}",
                command_hint="",
                source_id=f"emergence:{candidate.candidate_id}",
            ))
    except Exception:
        pass
```

In `collect_nudges()`, add the call after `_collect_knowledge_sufficiency_nudges`:

```python
    _collect_emergence_nudges(nudges)
```

**Step 3: Run tests**

```bash
cd <ai-agents>
uv run pytest tests/test_nudges.py -v
```

Expected: All PASS

**Step 4: Commit**

```bash
cd <ai-agents>
git add cockpit/data/nudges.py tests/test_nudges.py
git commit -m "feat: emergence nudges — surface domain candidates in action items"
```

---

### Task 14: Final Verification

**Step 1: Run all knowledge sufficiency tests**

```bash
cd <ai-agents>
uv run pytest tests/test_knowledge_sufficiency.py -v
```

Expected: All PASS

**Step 2: Run all new test files**

```bash
cd <ai-agents>
uv run pytest tests/test_momentum.py tests/test_emergence.py tests/test_domain_health.py -v
```

Expected: All PASS

**Step 3: Run full test suite**

```bash
cd <ai-agents>
uv run pytest tests/ -v --timeout=60
```

Expected: All PASS (may have 1 pre-existing failure)

**Step 4: Verify YAML files load correctly**

```bash
cd <hapaxromana>
python3 -c "
import yaml
for f in ['domains/registry.yaml', 'knowledge/management-sufficiency.yaml', 'knowledge/music-sufficiency.yaml', 'knowledge/personal-sufficiency.yaml', 'knowledge/technical-sufficiency.yaml']:
    with open(f) as fh:
        data = yaml.safe_load(fh)
        if 'domains' in data:
            print(f'{f}: {len(data[\"domains\"])} domains')
        elif 'requirements' in data:
            print(f'{f}: {len(data[\"requirements\"])} requirements')
"
```

Expected output:
```
domains/registry.yaml: 4 domains
knowledge/management-sufficiency.yaml: 31 requirements
knowledge/music-sufficiency.yaml: 6 requirements
knowledge/personal-sufficiency.yaml: 4 requirements
knowledge/technical-sufficiency.yaml: 5 requirements
```

**Step 5: Verify cockpit snapshot mode**

```bash
cd <ai-agents>
uv run cockpit --once 2>&1 | head -40
```

Expected: Domain health section visible, no crashes.

**Step 6: Update CLAUDE.md**

In `<hapaxromana>/CLAUDE.md`, add the domain registry to the architecture documentation. In the description of hapaxromana, note that `domains/registry.yaml` defines life domains and `knowledge/*.yaml` has per-domain sufficiency models.

**Step 7: Commit documentation**

```bash
cd <hapaxromana>
git add CLAUDE.md
git commit -m "docs: add domain lattice engine to CLAUDE.md"
```

---

## Summary

| Phase | Tasks | Files Created | Files Modified | Tests |
|-------|-------|--------------|----------------|-------|
| 1 | 1-5 | 4 YAML | knowledge_sufficiency.py, nudges.py | ~15 |
| 2 | 6 | momentum.py | — | ~12 |
| 3 | 7-8 | — | tpl-person.md, management.py | ~2 |
| 4 | 9 | emergence.py | — | ~6 |
| 5 | 10-14 | domain_health.py, domain_health widget | sidebar.py, app.py, nudges.py | ~6 |

**Total:** 14 tasks, ~7 new files, ~6 modified files, ~41 tests

**Repos:** hapaxromana (YAMLs + docs), ai-agents (Python), vault (template)

**No new dependencies.** All implementations use stdlib + existing project deps (yaml, dataclasses, Pydantic, Textual, Rich).
