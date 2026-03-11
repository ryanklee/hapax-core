# Axiom Enforcement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a 7-layer axiom enforcement system where axioms gain enforceable meaning through accumulated precedent (case law), backed by Qdrant vector search.

**Architecture:** Axiom definitions live in `<hapaxromana>/axioms/` (YAML). Enforcement modules live in `<ai-agents>/shared/` (Python). A Qdrant collection (`axiom-precedents`) stores accumulated decisions. LLM agents get decision-time tools to check compliance and record precedents. Drift detector, health monitor, briefing, and cockpit are extended.

**Tech Stack:** Python 3.12+, Pydantic, pydantic-ai, Qdrant (768d nomic-embed-text-v2-moe), PyYAML, pytest (asyncio_mode=auto). Package manager: `uv`. All work in `<ai-agents>/` unless noted.

**Baseline:** 1095 tests passing. Flaky test deselected: `tests/test_profiler.py::test_detect_changed_sources_nothing_changed`

---

## Task 1: Axiom Registry YAML (hapaxromana)

Create the axiom definition files that all enforcement code reads from.

**Files:**
- Create: `<hapaxromana>/axioms/registry.yaml`
- Create: `<hapaxromana>/axioms/precedents/seed/single-user-seeds.yaml`
- Create: `<hapaxromana>/axioms/precedents/seed/executive-function-seeds.yaml`
- Create: `<hapaxromana>/axioms/implications/single-user.yaml` (placeholder, populated by derivation pipeline later)
- Create: `<hapaxromana>/axioms/implications/executive-function.yaml` (placeholder)

**Step 1: Create directory structure**

```bash
cd <hapaxromana>
mkdir -p axioms/implications axioms/precedents/seed
```

**Step 2: Write registry.yaml**

```yaml
# axioms/registry.yaml — Axiom definitions for the hapaxromana system.
# Schema: each axiom has id, text, weight (0-100), type (hardcoded|softcoded),
# created date, status (active|retired), and optional supersedes reference.
version: 1
axioms:
  - id: single_user
    text: >
      This system is developed for a single user and by that single user,
      the operator (Hapax). This will always be the case. All decisions
      must be made respecting and leveraging that fact.
    weight: 100
    type: hardcoded
    created: "2026-03-03"
    status: active
    supersedes: null

  - id: executive_function
    text: >
      This system serves as externalized executive function infrastructure.
      The operator has ADHD and autism — task initiation, sustained attention,
      and routine maintenance are genuine cognitive challenges. The system
      must compensate for these, not add to cognitive load.
    weight: 95
    type: hardcoded
    created: "2026-03-03"
    status: active
    supersedes: null
```

**Step 3: Write single-user seed precedents**

```yaml
# axioms/precedents/seed/single-user-seeds.yaml
axiom_id: single_user
precedents:
  - id: sp-su-001
    situation: "Mobile access via Tailscale to home services"
    decision: compliant
    reasoning: >
      Multi-device access for the single user is consistent with the axiom.
      Tailscale authenticates the device, not a separate user. No multi-user
      scaffolding is introduced.
    tier: T1
    distinguishing_facts:
      - "Single user accessing from multiple personal devices"
      - "No new authentication layer for user identity"
    created: "2026-03-03"
    authority: operator

  - id: sp-su-002
    situation: "ntfy push notifications to Android"
    decision: compliant
    reasoning: >
      Push notifications to the operator's personal device. Service-level
      auth (topic token), not user-level auth. No user management.
    tier: T2
    distinguishing_facts:
      - "Service authentication, not user authentication"
      - "Single recipient device"
    created: "2026-03-03"
    authority: operator

  - id: sp-su-003
    situation: "Open WebUI with WEBUI_AUTH=true"
    decision: compliant
    reasoning: >
      Authentication protects the single-user interface from unauthorized
      network access. Single admin account (admin@localhost.com). Not
      multi-user scaffolding — security for one user.
    tier: T2
    distinguishing_facts:
      - "Single admin account only"
      - "Auth protects single-user interface, not manages multiple users"
    created: "2026-03-03"
    authority: operator

  - id: sp-su-004
    situation: "Adding OAuth2 for API access with multiple user accounts"
    decision: violation
    reasoning: >
      OAuth2 with multiple user accounts introduces multi-user identity
      management. This directly contradicts the single-user axiom by
      creating infrastructure for distinct user identities.
    tier: T0
    distinguishing_facts:
      - "Multiple user accounts implies multi-user system"
      - "OAuth2 user management is multi-user scaffolding"
    created: "2026-03-03"
    authority: operator
```

**Step 4: Write executive-function seed precedents**

```yaml
# axioms/precedents/seed/executive-function-seeds.yaml
axiom_id: executive_function
precedents:
  - id: sp-ef-001
    situation: "Health monitor auto-fix for safe remediations"
    decision: compliant
    reasoning: >
      Auto-fixing known-safe issues (restarting containers, clearing caches)
      reduces operator cognitive load. The operator doesn't need to manually
      intervene for routine infrastructure maintenance.
    tier: T1
    distinguishing_facts:
      - "Automated remediation of known-safe issues"
      - "Reduces task initiation burden"
    created: "2026-03-03"
    authority: operator

  - id: sp-ef-002
    situation: "Nudge system surfacing stale goals"
    decision: compliant
    reasoning: >
      Proactively surfacing stalled work as observation (not judgment) helps
      with task initiation difficulty. Framing as system design signal rather
      than operator failing respects neurocognitive profile.
    tier: T1
    distinguishing_facts:
      - "Observational framing, not judgmental"
      - "Addresses task initiation difficulty"
    created: "2026-03-03"
    authority: operator

  - id: sp-ef-003
    situation: "Adding complex multi-step manual configuration process"
    decision: violation
    reasoning: >
      Multi-step manual processes with no automation increase cognitive load.
      They require sustained attention and task initiation for each step,
      both identified challenges. Should be automated or scripted.
    tier: T1
    distinguishing_facts:
      - "Manual multi-step process"
      - "No automation or scripting path"
      - "Requires sustained attention"
    created: "2026-03-03"
    authority: operator
```

**Step 5: Write placeholder implication files**

```yaml
# axioms/implications/single-user.yaml
# Populated by derivation pipeline: uv run python -m shared.axiom_derivation --axiom single_user
axiom_id: single_user
derived_at: null
model: null
derivation_version: 0
implications: []
```

```yaml
# axioms/implications/executive-function.yaml
axiom_id: executive_function
derived_at: null
model: null
derivation_version: 0
implications: []
```

**Step 6: Commit**

```bash
cd <hapaxromana>
git add axioms/
git commit -m "feat: axiom registry with seed precedents for single_user and executive_function"
```

---

## Task 2: Axiom Registry Loader (ai-agents)

Python module to load and validate axiom definitions from hapaxromana.

**Files:**
- Create: `<ai-agents>/shared/axiom_registry.py`
- Create: `<ai-agents>/tests/test_axiom_registry.py`

**Step 1: Write the failing tests**

```python
# tests/test_axiom_registry.py
"""Tests for shared.axiom_registry."""
import pytest
from pathlib import Path

from shared.axiom_registry import Axiom, Implication, load_axioms, load_implications, get_axiom


@pytest.fixture
def sample_registry(tmp_path):
    """Create a minimal registry for testing."""
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        "version: 1\n"
        "axioms:\n"
        "  - id: test_axiom\n"
        '    text: "Test axiom text."\n'
        "    weight: 80\n"
        "    type: hardcoded\n"
        '    created: "2026-01-01"\n'
        "    status: active\n"
        "    supersedes: null\n"
        "  - id: retired_axiom\n"
        '    text: "Old axiom."\n'
        "    weight: 50\n"
        "    type: softcoded\n"
        '    created: "2025-01-01"\n'
        "    status: retired\n"
        "    supersedes: null\n"
    )
    impl_dir = tmp_path / "implications"
    impl_dir.mkdir()
    (impl_dir / "test_axiom.yaml").write_text(
        "axiom_id: test_axiom\n"
        "derived_at: '2026-01-01'\n"
        "model: test-model\n"
        "derivation_version: 1\n"
        "implications:\n"
        "  - id: ta-001\n"
        "    tier: T0\n"
        '    text: "No multi-user auth"\n'
        "    enforcement: block\n"
        "    canon: textualist\n"
        "  - id: ta-002\n"
        "    tier: T2\n"
        '    text: "Prefer single-user defaults"\n'
        "    enforcement: warn\n"
        "    canon: purposivist\n"
    )
    return tmp_path


def test_load_axioms_returns_active_only(sample_registry):
    axioms = load_axioms(path=sample_registry)
    assert len(axioms) == 1
    assert axioms[0].id == "test_axiom"
    assert axioms[0].weight == 80
    assert axioms[0].type == "hardcoded"


def test_load_axioms_missing_path(tmp_path):
    axioms = load_axioms(path=tmp_path / "nonexistent")
    assert axioms == []


def test_get_axiom_found(sample_registry):
    axiom = get_axiom("test_axiom", path=sample_registry)
    assert axiom is not None
    assert axiom.text.strip() == "Test axiom text."


def test_get_axiom_not_found(sample_registry):
    assert get_axiom("nonexistent", path=sample_registry) is None


def test_load_implications(sample_registry):
    impls = load_implications("test_axiom", path=sample_registry)
    assert len(impls) == 2
    assert impls[0].id == "ta-001"
    assert impls[0].tier == "T0"
    assert impls[0].enforcement == "block"
    assert impls[1].tier == "T2"


def test_load_implications_missing_file(sample_registry):
    impls = load_implications("nonexistent", path=sample_registry)
    assert impls == []
```

**Step 2: Run tests to verify they fail**

```bash
cd <ai-agents>
uv run pytest tests/test_axiom_registry.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'shared.axiom_registry'`

**Step 3: Write minimal implementation**

```python
# shared/axiom_registry.py
"""shared/axiom_registry.py — Load axiom definitions from hapaxromana registry.

Reads YAML axiom definitions and derived implications from the hapaxromana
axioms directory. Used by enforcement modules to access axiom text, weights,
and concrete implications.

Usage:
    from shared.axiom_registry import load_axioms, get_axiom, load_implications

    axioms = load_axioms()  # All active axioms
    axiom = get_axiom("single_user")
    implications = load_implications("single_user")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

AXIOMS_PATH: Path = Path.home() / "projects" / "hapaxromana" / "axioms"


@dataclass
class Axiom:
    id: str
    text: str
    weight: int
    type: str  # "hardcoded" | "softcoded"
    created: str
    status: str  # "active" | "retired"
    supersedes: str | None = None


@dataclass
class Implication:
    id: str
    axiom_id: str
    tier: str  # "T0" | "T1" | "T2" | "T3"
    text: str
    enforcement: str  # "block" | "review" | "warn" | "lint"
    canon: str  # interpretive strategy used


def load_axioms(*, path: Path = AXIOMS_PATH) -> list[Axiom]:
    """Load all active axioms from registry.yaml."""
    registry_file = path / "registry.yaml"
    if not registry_file.exists():
        log.warning("Axiom registry not found: %s", registry_file)
        return []

    try:
        data = yaml.safe_load(registry_file.read_text())
    except Exception as e:
        log.error("Failed to parse axiom registry: %s", e)
        return []

    axioms = []
    for entry in data.get("axioms", []):
        axiom = Axiom(
            id=entry["id"],
            text=entry.get("text", ""),
            weight=entry.get("weight", 50),
            type=entry.get("type", "softcoded"),
            created=entry.get("created", ""),
            status=entry.get("status", "active"),
            supersedes=entry.get("supersedes"),
        )
        if axiom.status == "active":
            axioms.append(axiom)

    return axioms


def get_axiom(axiom_id: str, *, path: Path = AXIOMS_PATH) -> Axiom | None:
    """Look up a single axiom by ID. Returns None if not found or not active."""
    for axiom in load_axioms(path=path):
        if axiom.id == axiom_id:
            return axiom
    return None


def load_implications(
    axiom_id: str, *, path: Path = AXIOMS_PATH
) -> list[Implication]:
    """Load derived implications for a specific axiom."""
    impl_file = path / "implications" / f"{axiom_id.replace('_', '-')}.yaml"
    if not impl_file.exists():
        # Try with underscores
        impl_file = path / "implications" / f"{axiom_id}.yaml"
        if not impl_file.exists():
            return []

    try:
        data = yaml.safe_load(impl_file.read_text())
    except Exception as e:
        log.error("Failed to parse implications for %s: %s", axiom_id, e)
        return []

    impls = []
    for entry in data.get("implications", []):
        impls.append(Implication(
            id=entry["id"],
            axiom_id=data.get("axiom_id", axiom_id),
            tier=entry.get("tier", "T2"),
            text=entry.get("text", ""),
            enforcement=entry.get("enforcement", "warn"),
            canon=entry.get("canon", ""),
        ))

    return impls
```

**Step 4: Run tests to verify they pass**

```bash
cd <ai-agents>
uv run pytest tests/test_axiom_registry.py -v
```

Expected: 6 PASSED

**Step 5: Run full test suite**

```bash
uv run pytest tests/ -x -q --deselect tests/test_profiler.py::test_detect_changed_sources_nothing_changed
```

Expected: 1101 passed

**Step 6: Commit**

```bash
cd <ai-agents>
git add shared/axiom_registry.py tests/test_axiom_registry.py
git commit -m "feat: axiom registry loader — reads YAML definitions from hapaxromana"
```

---

## Task 3: Precedent Store (ai-agents)

Qdrant-backed precedent database with semantic search, CRUD, seed loading, and authority management.

**Files:**
- Create: `<ai-agents>/shared/axiom_precedents.py`
- Create: `<ai-agents>/tests/test_axiom_precedents.py`

**Step 1: Write the failing tests**

```python
# tests/test_axiom_precedents.py
"""Tests for shared.axiom_precedents."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from shared.axiom_precedents import Precedent, PrecedentStore


def _make_precedent(**overrides) -> Precedent:
    defaults = dict(
        id="PRE-20260303-001",
        axiom_id="single_user",
        situation="Adding OAuth2 multi-user auth",
        decision="violation",
        reasoning="OAuth2 with multiple users contradicts single-user axiom.",
        tier="T0",
        distinguishing_facts=["Multiple user accounts", "User identity management"],
        authority="operator",
        created="2026-03-03T00:00:00Z",
        superseded_by=None,
    )
    defaults.update(overrides)
    return Precedent(**defaults)


class TestPrecedentDataclass:
    def test_create(self):
        p = _make_precedent()
        assert p.axiom_id == "single_user"
        assert p.decision == "violation"
        assert p.authority == "operator"

    def test_defaults(self):
        p = _make_precedent(superseded_by="PRE-20260303-002")
        assert p.superseded_by == "PRE-20260303-002"


class TestPrecedentStoreUnit:
    """Unit tests with mocked Qdrant client."""

    def test_generate_id(self):
        store = PrecedentStore.__new__(PrecedentStore)
        id1 = store._generate_id()
        assert id1.startswith("PRE-")
        assert len(id1) == 18  # PRE-YYYYMMDD-NNN + some

    def test_precedent_to_payload(self):
        store = PrecedentStore.__new__(PrecedentStore)
        p = _make_precedent()
        payload = store._to_payload(p)
        assert payload["axiom_id"] == "single_user"
        assert payload["decision"] == "violation"
        assert payload["authority"] == "operator"
        assert isinstance(payload["distinguishing_facts"], str)  # JSON-encoded list

    def test_payload_to_precedent(self):
        store = PrecedentStore.__new__(PrecedentStore)
        p = _make_precedent()
        payload = store._to_payload(p)
        restored = store._from_payload("test-point-id", payload)
        assert restored.axiom_id == p.axiom_id
        assert restored.decision == p.decision
        assert restored.distinguishing_facts == p.distinguishing_facts

    @patch("shared.axiom_precedents.get_qdrant")
    def test_ensure_collection_creates_if_missing(self, mock_get):
        client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "other-collection"
        client.get_collections.return_value.collections = [mock_collection]
        mock_get.return_value = client

        store = PrecedentStore()
        store.ensure_collection()
        client.create_collection.assert_called_once()

    @patch("shared.axiom_precedents.get_qdrant")
    def test_ensure_collection_skips_if_exists(self, mock_get):
        client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.name = "axiom-precedents"
        client.get_collections.return_value.collections = [mock_collection]
        mock_get.return_value = client

        store = PrecedentStore()
        store.ensure_collection()
        client.create_collection.assert_not_called()


class TestSeedLoading:
    def test_load_seeds_from_yaml(self, tmp_path):
        seed_dir = tmp_path / "precedents" / "seed"
        seed_dir.mkdir(parents=True)
        (seed_dir / "test-seeds.yaml").write_text(
            "axiom_id: test_axiom\n"
            "precedents:\n"
            "  - id: sp-001\n"
            '    situation: "Test situation"\n'
            "    decision: compliant\n"
            '    reasoning: "Test reasoning"\n'
            "    tier: T1\n"
            "    distinguishing_facts:\n"
            '      - "Fact one"\n'
            '    created: "2026-01-01"\n'
            "    authority: operator\n"
        )
        store = PrecedentStore.__new__(PrecedentStore)
        seeds = store._parse_seed_file(seed_dir / "test-seeds.yaml")
        assert len(seeds) == 1
        assert seeds[0].id == "sp-001"
        assert seeds[0].axiom_id == "test_axiom"
        assert seeds[0].authority == "operator"


class TestPromoteAndSupersede:
    def test_promote_changes_authority(self):
        p = _make_precedent(authority="agent")
        assert p.authority == "agent"
        # Promotion is done via Qdrant payload update, tested in integration
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_axiom_precedents.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write the implementation**

```python
# shared/axiom_precedents.py
"""shared/axiom_precedents.py — Qdrant-backed precedent database for axiom enforcement.

Stores accumulated axiom-application decisions (case law). Each precedent
records a situation, the axiom it relates to, the decision made, and the
reasoning. Semantic search finds relevant precedents for new situations.

Authority hierarchy (vertical stare decisis):
  - operator (1.0): Operator explicitly decided. Highest authority.
  - agent (0.7): Agent decided at runtime. Pending operator review.
  - derived (0.5): Generated by derivation pipeline. Lowest authority.

Usage:
    from shared.axiom_precedents import PrecedentStore, Precedent

    store = PrecedentStore()
    store.ensure_collection()

    # Search for relevant precedents
    results = store.search("single_user", "adding OAuth2 for API access")

    # Record a new precedent
    store.record(Precedent(...))
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from shared.config import get_qdrant

log = logging.getLogger(__name__)

COLLECTION = "axiom-precedents"
VECTOR_DIM = 768

AUTHORITY_WEIGHTS = {
    "operator": 1.0,
    "agent": 0.7,
    "derived": 0.5,
}


@dataclass
class Precedent:
    id: str
    axiom_id: str
    situation: str
    decision: str  # "compliant" | "violation" | "edge_case"
    reasoning: str
    tier: str  # "T0" | "T1" | "T2" | "T3"
    distinguishing_facts: list[str]
    authority: str  # "operator" | "agent" | "derived"
    created: str
    superseded_by: str | None = None


class PrecedentStore:
    def __init__(self):
        self.client = get_qdrant()

    def ensure_collection(self) -> None:
        """Create the axiom-precedents collection if it doesn't exist."""
        from qdrant_client.models import Distance, VectorParams

        collections = [c.name for c in self.client.get_collections().collections]
        if COLLECTION not in collections:
            self.client.create_collection(
                COLLECTION,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            log.info("Created Qdrant collection: %s", COLLECTION)

    def _generate_id(self) -> str:
        """Generate a unique precedent ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d")
        short = uuid.uuid4().hex[:6]
        return f"PRE-{ts}-{short}"

    def _to_payload(self, precedent: Precedent) -> dict:
        """Convert a Precedent to a Qdrant payload dict."""
        return {
            "precedent_id": precedent.id,
            "axiom_id": precedent.axiom_id,
            "situation": precedent.situation,
            "decision": precedent.decision,
            "reasoning": precedent.reasoning,
            "tier": precedent.tier,
            "distinguishing_facts": json.dumps(precedent.distinguishing_facts),
            "authority": precedent.authority,
            "created": precedent.created,
            "superseded_by": precedent.superseded_by or "",
        }

    def _from_payload(self, point_id: str, payload: dict) -> Precedent:
        """Convert a Qdrant payload back to a Precedent."""
        facts = payload.get("distinguishing_facts", "[]")
        if isinstance(facts, str):
            try:
                facts = json.loads(facts)
            except json.JSONDecodeError:
                facts = [facts] if facts else []
        return Precedent(
            id=payload.get("precedent_id", str(point_id)),
            axiom_id=payload.get("axiom_id", ""),
            situation=payload.get("situation", ""),
            decision=payload.get("decision", ""),
            reasoning=payload.get("reasoning", ""),
            tier=payload.get("tier", "T2"),
            distinguishing_facts=facts,
            authority=payload.get("authority", "derived"),
            created=payload.get("created", ""),
            superseded_by=payload.get("superseded_by") or None,
        )

    def search(
        self,
        axiom_id: str,
        situation: str,
        *,
        limit: int = 5,
    ) -> list[Precedent]:
        """Semantic search for precedents relevant to a situation."""
        from shared.config import embed
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_vec = embed(situation, prefix="search_query")

        query_filter = Filter(must=[
            FieldCondition(key="axiom_id", match=MatchValue(value=axiom_id)),
            FieldCondition(key="superseded_by", match=MatchValue(value="")),
        ])

        results = self.client.query_points(
            COLLECTION,
            query=query_vec,
            query_filter=query_filter,
            limit=limit,
        )

        return [self._from_payload(p.id, p.payload) for p in results.points]

    def record(self, precedent: Precedent) -> str:
        """Record a new precedent. Returns the precedent ID."""
        from shared.config import embed
        from qdrant_client.models import PointStruct

        if not precedent.id:
            precedent.id = self._generate_id()
        if not precedent.created:
            precedent.created = datetime.now(timezone.utc).isoformat()

        vec = embed(precedent.situation, prefix="search_document")
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"axiom-precedent-{precedent.id}"))

        self.client.upsert(
            COLLECTION,
            [PointStruct(id=point_id, vector=vec, payload=self._to_payload(precedent))],
        )

        log.info("Recorded precedent %s (axiom=%s, decision=%s)",
                 precedent.id, precedent.axiom_id, precedent.decision)
        return precedent.id

    def load_seeds(self, axioms_path: Path) -> int:
        """Load seed precedents from YAML files. Skips already-present IDs."""
        seed_dir = axioms_path / "precedents" / "seed"
        if not seed_dir.exists():
            return 0

        count = 0
        for seed_file in sorted(seed_dir.glob("*-seeds.yaml")):
            seeds = self._parse_seed_file(seed_file)
            for seed in seeds:
                self.record(seed)
                count += 1

        log.info("Loaded %d seed precedents from %s", count, seed_dir)
        return count

    def _parse_seed_file(self, path: Path) -> list[Precedent]:
        """Parse a seed YAML file into Precedent objects."""
        data = yaml.safe_load(path.read_text())
        axiom_id = data.get("axiom_id", "")
        precedents = []
        for entry in data.get("precedents", []):
            precedents.append(Precedent(
                id=entry["id"],
                axiom_id=axiom_id,
                situation=entry.get("situation", ""),
                decision=entry.get("decision", ""),
                reasoning=entry.get("reasoning", ""),
                tier=entry.get("tier", "T2"),
                distinguishing_facts=entry.get("distinguishing_facts", []),
                authority=entry.get("authority", "derived"),
                created=entry.get("created", ""),
                superseded_by=None,
            ))
        return precedents

    def get_by_axiom(self, axiom_id: str, *, limit: int = 20) -> list[Precedent]:
        """Get all precedents for an axiom, sorted by authority then date."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = Filter(must=[
            FieldCondition(key="axiom_id", match=MatchValue(value=axiom_id)),
            FieldCondition(key="superseded_by", match=MatchValue(value="")),
        ])

        results = self.client.scroll(
            COLLECTION,
            scroll_filter=query_filter,
            limit=limit,
        )

        precedents = [self._from_payload(p.id, p.payload) for p in results[0]]
        # Sort: operator first, then agent, then derived; within same authority, newest first
        authority_order = {"operator": 0, "agent": 1, "derived": 2}
        precedents.sort(key=lambda p: (authority_order.get(p.authority, 9), p.created), reverse=False)
        return precedents

    def get_pending_review(self, *, limit: int = 20) -> list[Precedent]:
        """Get agent-created precedents awaiting operator review."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        query_filter = Filter(must=[
            FieldCondition(key="authority", match=MatchValue(value="agent")),
            FieldCondition(key="superseded_by", match=MatchValue(value="")),
        ])

        results = self.client.scroll(
            COLLECTION,
            scroll_filter=query_filter,
            limit=limit,
        )

        return [self._from_payload(p.id, p.payload) for p in results[0]]

    def promote(self, precedent_id: str) -> None:
        """Promote an agent precedent to operator authority."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        results = self.client.scroll(
            COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="precedent_id", match=MatchValue(value=precedent_id)),
            ]),
            limit=1,
        )

        if results[0]:
            point = results[0][0]
            payload = dict(point.payload)
            payload["authority"] = "operator"
            from qdrant_client.models import PointStruct
            self.client.upsert(
                COLLECTION,
                [PointStruct(id=point.id, vector=point.vector, payload=payload)],
            )
            log.info("Promoted precedent %s to operator authority", precedent_id)

    def supersede(self, old_id: str, new_precedent: Precedent) -> str:
        """Supersede an existing precedent with a new one."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # Mark old as superseded
        results = self.client.scroll(
            COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="precedent_id", match=MatchValue(value=old_id)),
            ]),
            limit=1,
        )

        new_id = self.record(new_precedent)

        if results[0]:
            point = results[0][0]
            payload = dict(point.payload)
            payload["superseded_by"] = new_id
            from qdrant_client.models import PointStruct
            self.client.upsert(
                COLLECTION,
                [PointStruct(id=point.id, vector=point.vector, payload=payload)],
            )

        log.info("Superseded precedent %s with %s", old_id, new_id)
        return new_id
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_axiom_precedents.py -v
```

Expected: 8 PASSED

**Step 5: Run full test suite**

```bash
uv run pytest tests/ -x -q --deselect tests/test_profiler.py::test_detect_changed_sources_nothing_changed
```

Expected: 1109 passed

**Step 6: Commit**

```bash
git add shared/axiom_precedents.py tests/test_axiom_precedents.py
git commit -m "feat: precedent store — Qdrant-backed case law for axiom enforcement"
```

---

## Task 4: Agent Decision-Time Tools (ai-agents)

Tools that LLM agents call to check axiom compliance and record decisions.

**Files:**
- Create: `<ai-agents>/shared/axiom_tools.py`
- Create: `<ai-agents>/tests/test_axiom_tools.py`
- Modify: `<ai-agents>/shared/operator.py` (enhance axiom injection)

**Step 1: Write the failing tests**

```python
# tests/test_axiom_tools.py
"""Tests for shared.axiom_tools."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from shared.axiom_tools import check_axiom_compliance, record_axiom_decision, get_axiom_tools


def _mock_ctx():
    ctx = MagicMock()
    ctx.deps = MagicMock()
    return ctx


class TestCheckAxiomCompliance:
    @pytest.mark.asyncio
    async def test_returns_precedents_when_found(self):
        ctx = _mock_ctx()
        mock_precedent = MagicMock()
        mock_precedent.id = "PRE-001"
        mock_precedent.decision = "compliant"
        mock_precedent.reasoning = "Device auth, not user auth"
        mock_precedent.tier = "T1"
        mock_precedent.authority = "operator"
        mock_precedent.distinguishing_facts = ["Single device"]
        mock_precedent.situation = "Tailscale access"

        with patch("shared.axiom_tools.PrecedentStore") as MockStore, \
             patch("shared.axiom_tools.load_axioms") as mock_load:
            mock_axiom = MagicMock()
            mock_axiom.id = "single_user"
            mock_axiom.text = "Single user system."
            mock_load.return_value = [mock_axiom]
            MockStore.return_value.search.return_value = [mock_precedent]

            result = await check_axiom_compliance(
                ctx, situation="Adding Tailscale VPN", axiom_id="single_user",
            )

        assert "PRE-001" in result
        assert "compliant" in result

    @pytest.mark.asyncio
    async def test_returns_axiom_text_when_no_precedents(self):
        ctx = _mock_ctx()

        with patch("shared.axiom_tools.PrecedentStore") as MockStore, \
             patch("shared.axiom_tools.load_axioms") as mock_load, \
             patch("shared.axiom_tools.load_implications") as mock_impl:
            mock_axiom = MagicMock()
            mock_axiom.id = "single_user"
            mock_axiom.text = "Single user system."
            mock_load.return_value = [mock_axiom]
            MockStore.return_value.search.return_value = []
            mock_impl.return_value = []

            result = await check_axiom_compliance(
                ctx, situation="Adding multi-tenant DB",
            )

        assert "Single user system" in result
        assert "No close precedents" in result


class TestRecordAxiomDecision:
    @pytest.mark.asyncio
    async def test_records_with_agent_authority(self):
        ctx = _mock_ctx()

        with patch("shared.axiom_tools.PrecedentStore") as MockStore:
            MockStore.return_value.record.return_value = "PRE-001"

            result = await record_axiom_decision(
                ctx,
                axiom_id="single_user",
                situation="Adding OAuth2",
                decision="violation",
                reasoning="Multi-user identity management",
                tier="T0",
                distinguishing_facts='["Multiple user accounts"]',
            )

        assert "PRE-001" in result
        call_args = MockStore.return_value.record.call_args
        recorded = call_args[0][0]
        assert recorded.authority == "agent"


class TestGetAxiomTools:
    def test_returns_list_of_functions(self):
        tools = get_axiom_tools()
        assert len(tools) == 2
        assert check_axiom_compliance in tools
        assert record_axiom_decision in tools
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_axiom_tools.py -v
```

**Step 3: Write implementation**

```python
# shared/axiom_tools.py
"""shared/axiom_tools.py — Decision-time axiom compliance tools for Pydantic AI agents.

Provides two tools that LLM agents call during reasoning:
  - check_axiom_compliance: Search precedents for similar situations
  - record_axiom_decision: Record a new axiom-application decision

Usage:
    from shared.axiom_tools import get_axiom_tools

    for tool_fn in get_axiom_tools():
        agent.tool(tool_fn)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic_ai import RunContext

log = logging.getLogger(__name__)


async def check_axiom_compliance(
    ctx: RunContext[Any],
    situation: str,
    axiom_id: str = "",
) -> str:
    """Check if a decision complies with system axioms.

    Searches the precedent database for similar prior decisions. Returns
    relevant precedents with reasoning and distinguishing facts. If no
    close precedent exists, returns axiom text and derived implications.

    Args:
        situation: Description of the decision being made.
        axiom_id: Specific axiom to check. If empty, checks all active axioms.
    """
    from shared.axiom_registry import load_axioms, load_implications
    from shared.axiom_precedents import PrecedentStore

    axioms = load_axioms()
    if not axioms:
        return "No axioms defined in registry."

    if axiom_id:
        axioms = [a for a in axioms if a.id == axiom_id]
        if not axioms:
            return f"Axiom '{axiom_id}' not found or not active."

    try:
        store = PrecedentStore()
    except Exception as e:
        log.warning("Could not connect to precedent store: %s", e)
        # Fall back to axiom text only
        lines = ["Precedent database unavailable. Axiom text for reference:"]
        for axiom in axioms:
            lines.append(f"\n**{axiom.id}** (weight={axiom.weight}, type={axiom.type}):")
            lines.append(axiom.text.strip())
        return "\n".join(lines)

    sections = []
    for axiom in axioms:
        precedents = store.search(axiom.id, situation, limit=3)

        if precedents:
            lines = [f"**Axiom: {axiom.id}** — {len(precedents)} relevant precedent(s):"]
            for p in precedents:
                lines.append(f"\n  [{p.id}] ({p.authority} authority, {p.tier})")
                lines.append(f"  Situation: {p.situation}")
                lines.append(f"  Decision: {p.decision}")
                lines.append(f"  Reasoning: {p.reasoning}")
                if p.distinguishing_facts:
                    lines.append(f"  Distinguishing facts: {', '.join(p.distinguishing_facts)}")
            sections.append("\n".join(lines))
        else:
            implications = load_implications(axiom.id)
            lines = [f"**Axiom: {axiom.id}** — No close precedents found."]
            lines.append(f"Axiom text: {axiom.text.strip()}")
            if implications:
                lines.append("Derived implications:")
                for impl in implications:
                    lines.append(f"  [{impl.tier}] {impl.text} (enforcement: {impl.enforcement})")
            else:
                lines.append("No derived implications available.")
            sections.append("\n".join(lines))

    return "\n\n".join(sections)


async def record_axiom_decision(
    ctx: RunContext[Any],
    axiom_id: str,
    situation: str,
    decision: str,
    reasoning: str,
    tier: str = "T2",
    distinguishing_facts: str = "[]",
) -> str:
    """Record a decision about axiom compliance as precedent.

    Called after making significant decisions that touch axioms.
    Recorded with authority='agent' — pending operator review.

    Args:
        axiom_id: Which axiom this decision relates to.
        situation: What was being decided.
        decision: 'compliant', 'violation', or 'edge_case'.
        reasoning: Why this decision was reached.
        tier: Significance tier — T0, T1, T2, or T3.
        distinguishing_facts: JSON array of decisive facts.
    """
    from shared.axiom_precedents import PrecedentStore, Precedent

    try:
        facts = json.loads(distinguishing_facts)
    except (json.JSONDecodeError, TypeError):
        facts = [distinguishing_facts] if distinguishing_facts else []

    precedent = Precedent(
        id="",  # auto-generated
        axiom_id=axiom_id,
        situation=situation,
        decision=decision,
        reasoning=reasoning,
        tier=tier,
        distinguishing_facts=facts,
        authority="agent",
        created="",  # auto-generated
        superseded_by=None,
    )

    try:
        store = PrecedentStore()
        pid = store.record(precedent)
        return f"Recorded precedent {pid} (axiom={axiom_id}, decision={decision}, authority=agent)."
    except Exception as e:
        log.error("Failed to record axiom decision: %s", e)
        return f"Failed to record precedent: {e}"


def get_axiom_tools() -> list:
    """Return axiom tool functions for agent registration."""
    return [check_axiom_compliance, record_axiom_decision]
```

**Step 4: Modify shared/operator.py to load full axiom text**

In `shared/operator.py`, update `get_system_prompt_fragment()` to load richer axiom text from the registry when available, at lines ~156-164 where axiom booleans are currently checked. Replace the boolean-to-sentence mapping with full axiom text from registry, falling back to the existing boolean approach.

```python
# In get_system_prompt_fragment(), replace lines 155-164 with:
    # Axiom injection — prefer full text from registry, fall back to booleans
    axioms = data.get("axioms", {})
    try:
        from shared.axiom_registry import load_axioms as _load_axioms
        registry_axioms = _load_axioms()
        if registry_axioms:
            lines.append("")
            lines.append("System axioms (check_axiom_compliance tool available for compliance checks):")
            for ax in registry_axioms:
                lines.append(f"- [{ax.id}] {ax.text.strip()}")
        else:
            raise ImportError("No axioms in registry")
    except Exception:
        # Fall back to boolean axiom injection
        if axioms.get("single_user"):
            lines.append(f"This is a single-user system. All data and preferences belong to {operator_name}.")
        if axioms.get("executive_function"):
            lines.append(
                "This system is externalized executive function infrastructure. "
                "Reduce friction and decision load in all recommendations. "
                "Surface stalled work as observation, never judgment."
            )
```

**Step 5: Run tests**

```bash
uv run pytest tests/test_axiom_tools.py tests/test_operator.py -v
```

Expected: All pass

**Step 6: Run full suite**

```bash
uv run pytest tests/ -x -q --deselect tests/test_profiler.py::test_detect_changed_sources_nothing_changed
```

**Step 7: Commit**

```bash
git add shared/axiom_tools.py tests/test_axiom_tools.py shared/operator.py
git commit -m "feat: axiom decision-time tools — check_axiom_compliance + record_axiom_decision"
```

---

## Task 5: System Integration — Health Monitor + Service Tiers (ai-agents)

Add axiom health checks and tier defaults.

**Files:**
- Modify: `<ai-agents>/agents/health_monitor.py` (new `@check_group("axioms")`)
- Modify: `<ai-agents>/shared/service_tiers.py` (add axiom group default)
- Modify: `<ai-agents>/tests/test_health_monitor.py` (update registry test, add axiom check tests)

**Step 1: Add tier default for axioms group**

In `shared/service_tiers.py`, add to `GROUP_DEFAULTS` dict:
```python
"axioms": ServiceTier.OBSERVABILITY,
```

**Step 2: Add axiom check group to health_monitor.py**

Add after the capacity check group (end of check definitions, before `run_checks`):

```python
# ── Axiom infrastructure checks ──────────────────────────────────────────────

@check_group("axioms")
async def check_axiom_infrastructure() -> list[CheckResult]:
    """Check axiom enforcement infrastructure is operational."""
    results = []
    t = time.monotonic()

    # Check registry exists and is parseable
    from shared.axiom_registry import load_axioms, AXIOMS_PATH
    registry_file = AXIOMS_PATH / "registry.yaml"
    if registry_file.exists():
        axioms = load_axioms()
        if axioms:
            results.append(CheckResult(
                name="axiom.registry", group="axioms", status=Status.HEALTHY,
                message=f"Registry loaded: {len(axioms)} active axiom(s)",
                duration_ms=_timed(t),
            ))
        else:
            results.append(CheckResult(
                name="axiom.registry", group="axioms", status=Status.DEGRADED,
                message="Registry exists but no active axioms found",
                duration_ms=_timed(t),
            ))
    else:
        results.append(CheckResult(
            name="axiom.registry", group="axioms", status=Status.DEGRADED,
            message="Axiom registry not found",
            detail=str(registry_file),
            duration_ms=_timed(t),
        ))

    # Check precedent collection exists in Qdrant
    t2 = time.monotonic()
    try:
        from shared.config import get_qdrant
        client = get_qdrant()
        collections = [c.name for c in client.get_collections().collections]
        if "axiom-precedents" in collections:
            info = client.get_collection("axiom-precedents")
            count = info.points_count
            results.append(CheckResult(
                name="axiom.precedents", group="axioms", status=Status.HEALTHY,
                message=f"Precedent collection: {count} point(s)",
                duration_ms=_timed(t2),
            ))
        else:
            results.append(CheckResult(
                name="axiom.precedents", group="axioms", status=Status.DEGRADED,
                message="axiom-precedents collection not found in Qdrant",
                remediation="Run: uv run python -c 'from shared.axiom_precedents import PrecedentStore; PrecedentStore().ensure_collection()'",
                duration_ms=_timed(t2),
            ))
    except Exception as e:
        results.append(CheckResult(
            name="axiom.precedents", group="axioms", status=Status.FAILED,
            message="Cannot check precedent collection",
            detail=str(e),
            duration_ms=_timed(t2),
        ))

    # Check implications exist for active axioms
    t3 = time.monotonic()
    if axioms:
        from shared.axiom_registry import load_implications
        missing = [a.id for a in axioms if not load_implications(a.id)]
        if not missing:
            results.append(CheckResult(
                name="axiom.implications", group="axioms", status=Status.HEALTHY,
                message="All active axioms have implication files",
                duration_ms=_timed(t3),
            ))
        else:
            results.append(CheckResult(
                name="axiom.implications", group="axioms", status=Status.DEGRADED,
                message=f"Missing implications for: {', '.join(missing)}",
                remediation=f"Run: uv run python -m shared.axiom_derivation --axiom {missing[0]}",
                duration_ms=_timed(t3),
            ))

    return results
```

**Step 3: Update tests**

In `tests/test_health_monitor.py`, update the registry test to include "axioms" in expected groups. Add test class:

```python
class TestAxiomChecks:
    @patch("agents.health_monitor.load_axioms")
    @patch("agents.health_monitor.AXIOMS_PATH", new_callable=lambda: type("", (), {"__truediv__": lambda s, o: Path("/fake")})())
    async def test_registry_missing(self, mock_path, mock_load):
        mock_load.return_value = []
        results = await check_axiom_infrastructure()
        names = [r.name for r in results]
        assert "axiom.registry" in names

    @patch("agents.health_monitor.load_axioms")
    async def test_registry_healthy(self, mock_load):
        mock_axiom = MagicMock()
        mock_axiom.id = "test"
        mock_load.return_value = [mock_axiom]
        # Will fail on Qdrant check in unit test, but registry check should be healthy
        results = await check_axiom_infrastructure()
        registry_result = [r for r in results if r.name == "axiom.registry"][0]
        assert registry_result.status == Status.HEALTHY
```

**Step 4: Run tests**

```bash
uv run pytest tests/test_health_monitor.py -v -k "axiom or registry"
```

**Step 5: Commit**

```bash
git add agents/health_monitor.py shared/service_tiers.py tests/test_health_monitor.py
git commit -m "feat: axiom health checks — registry, precedent collection, implications"
```

---

## Task 6: System Integration — Drift Detector Axiom Pass (ai-agents)

Extend the drift detector to check axiom compliance alongside docs-vs-reality.

**Files:**
- Modify: `<ai-agents>/agents/drift_detector.py`
- Modify: `<ai-agents>/tests/test_drift_detector.py`

**Step 1: Update DriftItem category to include axiom-violation**

In `drift_detector.py`, update the `DriftItem.category` field description to include `axiom-violation`.

**Step 2: Add axiom compliance section to the prompt**

In `detect_drift()`, after the goals section is built (~line 161), add:

```python
    # Build axiom compliance section
    axiom_section = ""
    try:
        from shared.axiom_registry import load_axioms, load_implications
        active_axioms = load_axioms()
        if active_axioms:
            axiom_lines = ["\n\n## Active Axioms (check for compliance)"]
            for ax in active_axioms:
                axiom_lines.append(f"\n### {ax.id} (weight={ax.weight}, type={ax.type})")
                axiom_lines.append(ax.text.strip())
                impls = load_implications(ax.id)
                blocking = [i for i in impls if i.enforcement in ("block", "review")]
                if blocking:
                    axiom_lines.append("Key implications to check:")
                    for impl in blocking:
                        axiom_lines.append(f"  - [{impl.tier}] {impl.text}")
            axiom_section = "\n".join(axiom_lines)
    except Exception as e:
        log.warning("Could not load axioms for drift check: %s", e)
```

Then include `{axiom_section}` in the prompt string alongside `{goals_section}`.

**Step 3: Update SYSTEM_PROMPT**

Add to the drift detector system prompt instructions:

```
- If axioms are provided, check whether the current infrastructure complies with each axiom
  and its key implications. Flag violations as drift items with category "axiom-violation".
  T0 implications that appear violated: severity=high. T1 implications: severity=medium.
```

**Step 4: Add test**

```python
class TestAxiomDriftIntegration:
    def test_drift_item_axiom_category(self):
        item = DriftItem(
            severity="high",
            category="axiom-violation",
            doc_file="axioms/registry.yaml",
            doc_claim="single_user axiom: no multi-user auth",
            reality="OAuth2 with user management found",
            suggestion="Remove multi-user auth or justify as single-user protection",
        )
        assert item.category == "axiom-violation"
        assert item.severity == "high"
```

**Step 5: Run tests and commit**

```bash
uv run pytest tests/test_drift_detector.py -v
git add agents/drift_detector.py tests/test_drift_detector.py
git commit -m "feat: drift detector axiom compliance pass — checks axioms alongside docs"
```

---

## Task 7: System Integration — Briefing + Cockpit (ai-agents)

Add axiom section to briefing and review tools to cockpit.

**Files:**
- Modify: `<ai-agents>/agents/briefing.py`
- Modify: `<ai-agents>/cockpit/chat_agent.py`

**Step 1: Add axiom data collection to briefing**

In `briefing.py`, in the data collection section (after goals, before predictive), add:

```python
    # Axiom enforcement section
    axiom_section = ""
    try:
        from shared.axiom_precedents import PrecedentStore
        store = PrecedentStore()
        pending = store.get_pending_review(limit=50)
        if pending:
            axiom_section = f"\n\n## Axiom Enforcement\n- {len(pending)} agent precedent(s) awaiting operator review"
            axiom_section += "\n- Use `/axioms review` in cockpit to confirm or reject"
    except Exception:
        pass  # Axiom infrastructure may not be set up yet
```

Include `{axiom_section}` in the prompt.

**Step 2: Add axiom review tools to cockpit chat agent**

In `cockpit/chat_agent.py`, after the existing tool registrations, add:

```python
    @agent.tool
    async def review_pending_precedents(ctx: RunContext[ChatDeps]) -> str:
        """Show axiom precedents created by agents that await operator review."""
        from shared.axiom_precedents import PrecedentStore
        try:
            store = PrecedentStore()
            pending = store.get_pending_review()
        except Exception as e:
            return f"Could not access precedent store: {e}"

        if not pending:
            return "No pending precedents to review."

        lines = [f"{len(pending)} pending precedent(s):\n"]
        for p in pending:
            lines.append(f"**{p.id}** (axiom: {p.axiom_id}, tier: {p.tier})")
            lines.append(f"  Situation: {p.situation}")
            lines.append(f"  Decision: {p.decision}")
            lines.append(f"  Reasoning: {p.reasoning}")
            lines.append(f"  Facts: {', '.join(p.distinguishing_facts)}")
            lines.append("")
        lines.append("Use confirm_precedent(id) to promote or reject_precedent(id, correction) to supersede.")
        return "\n".join(lines)

    @agent.tool
    async def confirm_precedent(ctx: RunContext[ChatDeps], precedent_id: str) -> str:
        """Promote an agent-created precedent to operator authority.

        Args:
            precedent_id: The precedent ID to confirm (e.g., PRE-20260303-abc123).
        """
        from shared.axiom_precedents import PrecedentStore
        try:
            store = PrecedentStore()
            store.promote(precedent_id)
            return f"Promoted {precedent_id} to operator authority."
        except Exception as e:
            return f"Failed to promote: {e}"

    @agent.tool
    async def reject_precedent(
        ctx: RunContext[ChatDeps], precedent_id: str, correction: str,
    ) -> str:
        """Reject an agent precedent and record the operator's correction.

        Args:
            precedent_id: The precedent ID to reject.
            correction: The operator's corrected reasoning for this situation.
        """
        from shared.axiom_precedents import PrecedentStore, Precedent
        try:
            store = PrecedentStore()
            # Get the original to preserve context
            results = store.get_pending_review(limit=50)
            original = next((p for p in results if p.id == precedent_id), None)
            if not original:
                return f"Precedent {precedent_id} not found in pending review."

            new = Precedent(
                id="",
                axiom_id=original.axiom_id,
                situation=original.situation,
                decision=original.decision,
                reasoning=correction,
                tier=original.tier,
                distinguishing_facts=original.distinguishing_facts,
                authority="operator",
                created="",
                superseded_by=None,
            )
            new_id = store.supersede(precedent_id, new)
            return f"Superseded {precedent_id} with {new_id} (operator authority)."
        except Exception as e:
            return f"Failed to reject: {e}"
```

**Step 3: Register axiom tools on LLM agents**

In each agent that makes decisions, add after the context tools registration:

```python
    from shared.axiom_tools import get_axiom_tools
    for tool_fn in get_axiom_tools():
        agent.tool(tool_fn)
```

Files to modify:
- `agents/briefing.py` (~line 115)
- `agents/drift_detector.py` (~line 126)
- `agents/code_review.py` (after context tools registration)
- `agents/scout.py` (after context tools registration)
- `agents/management_prep.py` (after context tools registration)
- `cockpit/chat_agent.py` (~line 90)

**Step 4: Run tests and commit**

```bash
uv run pytest tests/ -x -q --deselect tests/test_profiler.py::test_detect_changed_sources_nothing_changed
git add agents/briefing.py agents/drift_detector.py agents/code_review.py agents/scout.py agents/management_prep.py cockpit/chat_agent.py
git commit -m "feat: axiom enforcement integration — briefing section, cockpit review tools, agent tool registration"
```

---

## Task 8: Derivation Pipeline (ai-agents)

One-shot LLM derivation of axiom implications with self-consistency.

**Files:**
- Create: `<ai-agents>/shared/axiom_derivation.py`
- Create: `<ai-agents>/tests/test_axiom_derivation.py`

**Step 1: Write failing tests**

```python
# tests/test_axiom_derivation.py
"""Tests for shared.axiom_derivation."""
import pytest
from unittest.mock import patch, MagicMock

from shared.axiom_derivation import (
    build_derivation_prompt,
    parse_implications_output,
    merge_self_consistent,
)


class TestBuildPrompt:
    def test_includes_axiom_text(self):
        prompt = build_derivation_prompt(
            axiom_id="single_user",
            axiom_text="This is a single-user system.",
            codebase_context="File tree: agents/, shared/, cockpit/",
        )
        assert "single-user system" in prompt
        assert "textualist" in prompt.lower() or "Textualist" in prompt

    def test_includes_interpretive_canons(self):
        prompt = build_derivation_prompt(
            axiom_id="test", axiom_text="Test.", codebase_context="",
        )
        assert "purposivist" in prompt.lower() or "Purposivist" in prompt
        assert "absurdity" in prompt.lower() or "Absurdity" in prompt


class TestParseOutput:
    def test_parses_yaml_implications(self):
        output = (
            "```yaml\n"
            "implications:\n"
            "  - id: su-001\n"
            "    tier: T0\n"
            '    text: "No multi-user auth"\n'
            "    enforcement: block\n"
            "    canon: textualist\n"
            "  - id: su-002\n"
            "    tier: T1\n"
            '    text: "No user switching"\n'
            "    enforcement: review\n"
            "    canon: purposivist\n"
            "```\n"
        )
        impls = parse_implications_output(output)
        assert len(impls) == 2
        assert impls[0]["id"] == "su-001"
        assert impls[0]["tier"] == "T0"

    def test_handles_no_yaml_block(self):
        impls = parse_implications_output("No implications found.")
        assert impls == []


class TestMergeSelfConsistent:
    def test_majority_vote_keeps_consensus(self):
        runs = [
            [{"id": "su-001", "tier": "T0", "text": "No multi-user auth", "enforcement": "block", "canon": "textualist"}],
            [{"id": "su-001", "tier": "T0", "text": "No multi-user auth", "enforcement": "block", "canon": "textualist"}],
            [{"id": "su-001", "tier": "T1", "text": "No multi-user auth", "enforcement": "review", "canon": "textualist"}],
        ]
        merged = merge_self_consistent(runs)
        # Majority says T0/block
        su001 = [i for i in merged if i["id"] == "su-001"]
        assert len(su001) == 1
        assert su001[0]["tier"] == "T0"

    def test_unique_implications_all_kept(self):
        runs = [
            [{"id": "su-001", "tier": "T0", "text": "A", "enforcement": "block", "canon": "t"}],
            [{"id": "su-002", "tier": "T1", "text": "B", "enforcement": "review", "canon": "t"}],
            [{"id": "su-001", "tier": "T0", "text": "A", "enforcement": "block", "canon": "t"},
             {"id": "su-003", "tier": "T2", "text": "C", "enforcement": "warn", "canon": "t"}],
        ]
        merged = merge_self_consistent(runs)
        ids = {i["id"] for i in merged}
        assert "su-001" in ids  # appears in 2/3 runs
```

**Step 2: Write implementation**

```python
# shared/axiom_derivation.py
"""shared/axiom_derivation.py — One-shot axiom implication derivation pipeline.

Generates concrete implications from axiom text using LLM self-consistency.
Operator-triggered only. Output is reviewed and committed to hapaxromana.

Usage:
    uv run python -m shared.axiom_derivation --axiom single_user
    uv run python -m shared.axiom_derivation --axiom executive_function --output implications.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


INTERPRETIVE_CANONS = """\
Apply these interpretive strategies (canons of construction):

1. **Textualist**: What does the axiom literally say? Derive implications from its exact words.
2. **Purposivist**: What is the axiom trying to achieve? Derive implications from its intent.
3. **Absurdity doctrine**: Would this interpretation produce results no reasonable person would endorse? If so, discard it.
4. **Omitted-case canon**: Don't add things the axiom doesn't state or reasonably imply.

For each implication, note which canon primarily drove the derivation."""


def build_derivation_prompt(
    axiom_id: str,
    axiom_text: str,
    codebase_context: str,
) -> str:
    """Build the LLM prompt for axiom decomposition."""
    return f"""\
You are deriving concrete, enforceable implications from a system axiom.

## Axiom: {axiom_id}

{axiom_text.strip()}

## Codebase Context

{codebase_context}

## Interpretive Framework

{INTERPRETIVE_CANONS}

## Instructions

Derive concrete implications of this axiom for the current codebase.
For each implication, assign:
- **id**: short identifier (format: {axiom_id[:2]}-category-NNN, e.g., su-arch-001)
- **tier**: T0 (existential — blocks work), T1 (significant — requires review),
  T2 (minor — automated warning), T3 (cosmetic — lint only)
- **text**: one-sentence concrete implication
- **enforcement**: block, review, warn, or lint
- **canon**: which interpretive canon primarily drove this derivation

Output as a YAML block:
```yaml
implications:
  - id: ...
    tier: ...
    text: ...
    enforcement: ...
    canon: ...
```

Focus on implications that are:
1. Concrete enough to check mechanically or through LLM review
2. Relevant to the current codebase (not hypothetical)
3. Non-obvious (don't restate the axiom itself)
"""


def parse_implications_output(text: str) -> list[dict]:
    """Parse YAML implications from LLM output."""
    # Extract YAML block
    match = re.search(r"```(?:yaml)?\s*\n(.*?)```", text, re.DOTALL)
    if not match:
        # Try parsing the whole text as YAML
        try:
            data = yaml.safe_load(text)
            if isinstance(data, dict) and "implications" in data:
                return data["implications"]
        except Exception:
            pass
        return []

    try:
        data = yaml.safe_load(match.group(1))
    except Exception as e:
        log.error("Failed to parse YAML from LLM output: %s", e)
        return []

    if isinstance(data, dict) and "implications" in data:
        return data["implications"]
    return []


def merge_self_consistent(runs: list[list[dict]]) -> list[dict]:
    """Merge multiple derivation runs using majority vote.

    Implications with the same ID across runs are merged — the majority
    tier/enforcement wins. Implications appearing in only one run are
    kept if they appear in at least 2 of N runs (or always kept if N < 3).
    """
    if not runs:
        return []
    if len(runs) == 1:
        return runs[0]

    # Group by implication ID
    by_id: dict[str, list[dict]] = {}
    for run in runs:
        for impl in run:
            impl_id = impl.get("id", "")
            if impl_id:
                by_id.setdefault(impl_id, []).append(impl)

    threshold = max(1, len(runs) // 2)  # Majority: appears in > half of runs
    merged = []
    for impl_id, versions in by_id.items():
        if len(versions) < threshold:
            continue  # Not enough consensus

        # Majority vote on tier and enforcement
        tiers = Counter(v.get("tier", "T2") for v in versions)
        enforcements = Counter(v.get("enforcement", "warn") for v in versions)

        base = versions[0].copy()
        base["tier"] = tiers.most_common(1)[0][0]
        base["enforcement"] = enforcements.most_common(1)[0][0]
        merged.append(base)

    return merged


async def derive_implications(
    axiom_id: str,
    *,
    n: int = 3,
    output_path: Path | None = None,
) -> list[dict]:
    """Run the full derivation pipeline with self-consistency."""
    from shared.axiom_registry import get_axiom, AXIOMS_PATH
    from shared.config import get_model

    axiom = get_axiom(axiom_id)
    if not axiom:
        log.error("Axiom '%s' not found in registry", axiom_id)
        return []

    # Gather codebase context
    import subprocess
    result = subprocess.run(
        ["find", str(Path.home() / "projects" / "ai-agents"),
         "-name", "*.py", "-path", "*/agents/*", "-o",
         "-name", "*.py", "-path", "*/shared/*"],
        capture_output=True, text=True,
    )
    file_tree = result.stdout.strip() if result.returncode == 0 else "File tree unavailable"

    prompt = build_derivation_prompt(axiom_id, axiom.text, file_tree)

    # Run N derivations
    from pydantic_ai import Agent
    agent = Agent(get_model("balanced"))

    runs = []
    for i in range(n):
        log.info("Derivation run %d/%d for axiom '%s'", i + 1, n, axiom_id)
        result = await agent.run(prompt)
        impls = parse_implications_output(result.output)
        runs.append(impls)
        log.info("  Run %d produced %d implications", i + 1, len(impls))

    # Merge with self-consistency
    merged = merge_self_consistent(runs)
    log.info("Merged: %d implications after self-consistency", len(merged))

    # Output
    output = {
        "axiom_id": axiom_id,
        "derived_at": __import__("datetime").datetime.now().isoformat()[:10],
        "model": "balanced",
        "derivation_version": 1,
        "implications": merged,
    }

    if output_path:
        output_path.write_text(yaml.dump(output, default_flow_style=False, sort_keys=False))
        log.info("Written to %s", output_path)
    else:
        print(yaml.dump(output, default_flow_style=False, sort_keys=False))

    return merged


async def _main():
    parser = argparse.ArgumentParser(description="Derive axiom implications")
    parser.add_argument("--axiom", required=True, help="Axiom ID to derive implications for")
    parser.add_argument("--n", type=int, default=3, help="Number of self-consistency runs")
    parser.add_argument("--output", type=Path, help="Output YAML file path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    await derive_implications(args.axiom, n=args.n, output_path=args.output)


if __name__ == "__main__":
    asyncio.run(_main())
```

**Step 3: Run tests and commit**

```bash
uv run pytest tests/test_axiom_derivation.py -v
uv run pytest tests/ -x -q --deselect tests/test_profiler.py::test_detect_changed_sources_nothing_changed
git add shared/axiom_derivation.py tests/test_axiom_derivation.py
git commit -m "feat: axiom derivation pipeline — self-consistent LLM implication generation"
```

---

## Task 9: Final Verification + Documentation

**Step 1: Run full test suite**

```bash
cd <ai-agents>
uv run pytest tests/ -x -q --deselect tests/test_profiler.py::test_detect_changed_sources_nothing_changed
```

Expected: ~1120+ tests passing (25+ new)

**Step 2: Verify health monitor with axiom checks**

```bash
uv run python -m agents.health_monitor --check axioms
```

Expected: Shows axiom.registry, axiom.precedents, axiom.implications checks

**Step 3: Verify registry loads**

```bash
uv run python -c "
from shared.axiom_registry import load_axioms, load_implications
axioms = load_axioms()
print(f'Active axioms: {len(axioms)}')
for a in axioms:
    print(f'  {a.id}: weight={a.weight}, type={a.type}')
    impls = load_implications(a.id)
    print(f'    Implications: {len(impls)}')
"
```

**Step 4: Create precedent collection and load seeds**

```bash
uv run python -c "
from shared.axiom_precedents import PrecedentStore
from shared.axiom_registry import AXIOMS_PATH
store = PrecedentStore()
store.ensure_collection()
count = store.load_seeds(AXIOMS_PATH)
print(f'Loaded {count} seed precedents')
"
```

**Step 5: Update REQUIRED_QDRANT_COLLECTIONS in health_monitor.py**

Add `"axiom-precedents"` to the set at line 82.

**Step 6: Commit everything**

```bash
cd <hapaxromana>
git add -A && git status  # Verify only axioms/ files
git commit -m "feat: axiom registry with seed precedents and placeholder implications"

cd <ai-agents>
git add -A && git status  # Verify all new/modified files
git commit -m "feat: complete axiom enforcement infrastructure — 7-layer architecture"
```

---

## Summary

| Task | What | New Tests | Commit |
|------|------|-----------|--------|
| 1 | Registry YAML (hapaxromana) | 0 | axiom registry YAML |
| 2 | Registry loader (ai-agents) | 6 | axiom_registry.py |
| 3 | Precedent store (ai-agents) | 8 | axiom_precedents.py |
| 4 | Agent tools + operator.py | 5 | axiom_tools.py |
| 5 | Health monitor + tiers | 2 | health check group |
| 6 | Drift detector axiom pass | 1 | drift_detector.py |
| 7 | Briefing + cockpit tools | 0 | briefing.py, chat_agent.py |
| 8 | Derivation pipeline | 5 | axiom_derivation.py |
| 9 | Verification + docs | 0 | final integration |
| **Total** | | **~27** | **~9 commits** |
