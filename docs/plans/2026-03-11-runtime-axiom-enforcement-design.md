# Runtime Axiom Enforcement Engine — Design Spec

**Goal:** Cross-cutting runtime validation of all LLM-generated text against constitutional axiom implications, with tier-appropriate enforcement actions.

**Scope:** Pattern specification in hapax-constitution. Implementation order: hapax-council first, then hapax-officium.

**Status:** Approved 2026-03-11.

---

## Problem

Static enforcement (git hooks, pattern scanning at commit time) catches code-level axiom violations. Runtime LLM output has no enforcement. System prompts contain axiom-derived warnings, but compliance depends entirely on LLM adherence. No post-generation validation exists anywhere in the system.

13 agent files make LLM calls. All write output to the filesystem, Qdrant, or operator-facing notifications without any content validation. The demo pipeline generates full narration scripts rendered to audio via TTS. The reactive engine synthesizes briefings and snapshots delivered via push notification.

Existing text artifacts (briefings, prep docs, documentation, Qdrant entries) were generated without runtime enforcement and may contain violations.

## Architecture

Two layers with different responsibilities:

### Layer 1 — LiteLLM Audit Callback (universal monitoring)

A custom LiteLLM callback that fires on every completion response. Runs the pattern checker against raw response text. Logs all violations to Langfuse (as span annotations on the existing trace) and Qdrant (axiom-precedents collection). Cannot block delivery — it is an observer. Its job is to guarantee that no LLM-generated text in the system goes unaudited, regardless of whether the calling agent opted into enforcement.

### Layer 2 — Application Enforcer (active enforcement)

A module (`shared/axiom_enforcer.py`) that wraps agent output paths. Agents declare their path classification at registration. After each LLM call, the enforcer:

- Runs pattern checks (all paths, always, sub-millisecond)
- Runs LLM-as-judge (path-dependent: sync for `full`, async-deferred for `deferred`, skipped for `fast`)
- On T0 violation: block, retry with amended prompt (up to 2 retries), quarantine if retries exhausted
- On T1 violation: log warning, deliver output, include violation metadata in Langfuse trace
- On T2+ violation: log only

### Layer Relationship

Layer 1 catches what Layer 2 misses (unenforced agents, ad-hoc LLM calls). Layer 2 acts on what Layer 1 can only observe. A healthy system shows zero violations in Layer 1 that weren't already caught by Layer 2. Divergence between the two layers is itself an alert condition — it means an agent is bypassing enforcement.

The application enforcer tags its LLM requests with `x-axiom-enforced: true` in LiteLLM's `metadata` dict (passed via the `metadata` parameter on LLM calls, which LiteLLM forwards to callbacks as `kwargs["litellm_params"]["metadata"]`). When the audit callback sees a violation on a request without this tag, it fires an infrastructure integrity alert via ntfy.

## Path Classifications

Three enforcement levels, declared per output path at registration time:

| Classification | Pattern Check | LLM Judge | Blocking |
|---|---|---|---|
| `full` | Sync | Sync | T0 violations block delivery |
| `fast` | Sync | Skip | T0 pattern violations block |
| `deferred` | Sync | Async post-hoc | Pattern T0 blocks sync; judge T0 flags post-hoc |

**Default is `full`.** Every path starts at the strictest classification. No grandfathering. All existing agents start at `full`.

### Exceptions

Downgrading a path below `full` requires a recorded exception in `axioms/enforcement-exceptions.yaml`:

```yaml
exceptions:
- path: reactive-engine/notification
  classification: fast
  default: full
  reason: >
    Reactive engine notifications must fire within the 300ms debounce
    window. Synchronous LLM-as-judge adds 1-2s latency, pushing
    notification delivery outside usability requirements. Notifications
    are operator-facing summaries derived from deterministic nudge
    collectors, limiting the LLM generation surface.
  compensating_control: >
    Layer 1 audit callback catches all violations post-hoc.
    Violations trigger operator notification via ntfy.
  approved: 2026-03-11
```

Each exception must state:
- What the default classification would be
- Why enforcement at that level would push the flow outside usability requirements
- Why those usability requirements are fundamental to system operation
- What compensating control exists
- When the exception was approved

Exceptions are precedent rulings — recorded, reasoned, reviewable. Convenience is not a valid justification. Only a demonstrated conflict between axioms (enforcement fidelity vs. decision_support usability) qualifies.

## Pattern Layer

The fast, deterministic detection layer. Sub-millisecond per check. Runs on every path classification.

### Pattern Registry

`axioms/enforcement-patterns.yaml` — maps regex patterns to specific axiom implications:

```yaml
patterns:
  - axiom: executive_function
    implication: ex-prose-001
    tier: T0
    patterns:
      - regex: "This isn't .{1,50} — it's"
        label: rhetorical-pivot
      - regex: "The question becomes"
        label: performative-insight
      - regex: "That's not .{1,50} — that's"
        label: dramatic-restatement
      - regex: "What .{1,80} really means is"
        label: false-revelation
      - regex: "It turns out"
        label: false-discovery
      - regex: "Here's the thing"
        label: performative-setup

  - axiom: management_safety
    implication: mg-boundary-001
    tier: T0
    patterns:
      - regex: "you should (tell|say to|ask) \\w+"
        label: delivery-language
      - regex: "feedback for \\w+:"
        label: directed-feedback
      - regex: "(suggest|recommend).*saying"
        label: scripted-delivery
```

### Pattern Checker Module

`shared/axiom_pattern_checker.py`:

- Loads `enforcement-patterns.yaml` once at startup
- `check_text(text: str, tier_filter: set[str] | None = None) -> list[PatternViolation]`
- Each `PatternViolation` carries: axiom_id, implication_id, tier, label, matched_text, position
- Case-insensitive matching by default
- Patterns are additive — new implications add entries to the YAML
- Not all prohibited patterns are regex-expressible. ex-prose-001 prohibits "dramatic restatement of known information" and "contrast structures that exist for rhythm rather than content" — these require semantic judgment and are judge-layer-only detections. The pattern registry covers the regex-expressible subset; the judge covers the full implication text.

### Relationship to Existing axiom_patterns.txt

`axiom_patterns.txt` continues to serve git hooks for static code scanning (Python code patterns like `class FeedbackGenerator`). `enforcement-patterns.yaml` serves runtime text validation (natural language output patterns). Different purposes, different files, no migration needed.

## LLM-as-Judge Layer

Semantic detection for violations that regex cannot catch. Runs a cheap/fast model against output text with relevant axiom implications as evaluation criteria.

### Judge Agent

`shared/axiom_judge.py` — a pydantic-ai Agent using the `fast` model alias (claude-haiku via LiteLLM):

```python
class JudgeVerdict(BaseModel):
    compliant: bool
    violations: list[JudgeViolation]

class JudgeViolation(BaseModel):
    implication_id: str
    tier: str
    excerpt: str        # the violating passage
    reasoning: str      # why this violates the implication
```

### Judge Prompt Construction

- Receives output text + applicable axiom implications filtered by tier threshold
- Prompt contains implication text verbatim — judge evaluates against constitutional language, not paraphrase
- Direct evaluation, structured output, no elaborate reasoning framework

### What the Judge Catches That Patterns Cannot

- Novel rhetorical structures not in the pattern list
- Subtle feedback language that violates mg-boundary-001 without keyword matches (e.g., "Sarah might benefit from hearing...")
- Contextual violations where the same text is clean in one context and violating in another

### What the Judge Does Not Do

- Replace pattern checking (patterns run first, always)
- Make architectural decisions or create precedents
- Self-evaluate (judge output is structured verdict data, not operator-facing prose; not recursively validated)

### Call Frequency

- `full` paths: every output, synchronous before delivery
- `fast` paths: pattern-only. No judge call, sync or async. Layer 1 audit callback provides pattern-level post-hoc coverage.
- `deferred` paths: judge runs as a background task immediately after delivery. Results logged to Langfuse. T0 violations trigger operator notification via ntfy. The background task is dispatched by the enforcer, not by Layer 1.
- Cost: ~$0.001/check with haiku, negligible relative to primary agent LLM costs

## Application Enforcer

`shared/axiom_enforcer.py` — wraps agent output paths with tier-appropriate enforcement actions.

### Interface

```python
class EnforcementResult(BaseModel):
    passed: bool
    violations: list[PatternViolation | JudgeViolation]
    action_taken: Literal["delivered", "retried", "quarantined"]
    retries_used: int

class OutputPath(BaseModel):
    name: str                                    # e.g. "management-briefing"
    classification: Literal["full", "fast", "deferred"]
    agent_name: str
    output_destination: str                      # e.g. "data/briefings/"

async def enforce(
    text: str,
    path: OutputPath,
    retry_fn: Callable[[list[PatternViolation | JudgeViolation]], Awaitable[str]] | None = None,
) -> EnforcementResult:
```

### Enforcement Flow

1. Run pattern checker. Collect violations by tier.
2. If path is `full`: run LLM judge. Collect violations.
3. Evaluate combined violations:
   - T0 + retry_fn provided: pass violation list to `retry_fn(violations)`. The caller is responsible for amending its prompt with violation context (see Retry Prompt Amendment below for the standard amendment text). Validate the new output. Up to 2 retries.
   - T0 + retries exhausted or no retry_fn: write to `profiles/.quarantine/{path.name}/{timestamp}.md` with violation metadata in frontmatter. Return `quarantined`.
   - T1: log warning to Langfuse, deliver, return `delivered` with violations.
   - T2+: log only, deliver.
4. No violations: return `delivered`, empty violations.

### Text Extraction

`extract_text_fields()` utility recursively extracts all string-typed fields from a Pydantic model instance and concatenates them. The enforcer validates aggregate text, not individual fields. A violation in any field blocks the whole output.

### Quarantine

`profiles/.quarantine/` — gitignored, organized by path name and timestamp. Each quarantined file includes full output text plus frontmatter with violation details.

## LiteLLM Audit Callback

`shared/axiom_litellm_callback.py` — universal monitoring backstop.

### Behavior

- Fires on every LLM completion via LiteLLM's custom callback interface
- Runs pattern checker only (no LLM judge — avoids recursive LLM calls at proxy level)
- Annotates existing Langfuse trace with violation data
- Records violations to Qdrant axiom-precedents collection
- Detects Layer 1/Layer 2 divergence via `x-axiom-enforced` request metadata
- Divergence triggers ntfy alert

### Recursion Prevention

The LLM judge tags its requests with `x-axiom-judge: true` metadata. The audit callback skips these requests.

### Deployment

Callback registered in `litellm-config.yaml`:

```yaml
litellm_settings:
  success_callback: ["langfuse", "axiom_litellm_callback.AxiomAuditCallback"]
```

The callback module is mounted into the LiteLLM Docker container via a bind mount in `docker-compose.yml`:

```yaml
services:
  litellm:
    volumes:
      - ./shared/axiom_litellm_callback.py:/app/axiom_litellm_callback.py
      - ./shared/axiom_pattern_checker.py:/app/axiom_pattern_checker.py
      - ./axioms/enforcement-patterns.yaml:/app/enforcement-patterns.yaml
```

The callback references the module as `axiom_litellm_callback.AxiomAuditCallback` (no `shared.` prefix — mounted at container root `/app/`). The callback's only dependencies are `re` and `pyyaml` (both available in LiteLLM's Python environment). Qdrant and Langfuse writes use HTTP calls, not client libraries, to avoid dependency on `qdrant-client` in the container.

## Extant Text Sweep

One-time audit of existing text artifacts plus ongoing coverage via existing agents.

### Initial Sweep

`scripts/axiom-sweep.py` — standalone script, runs once, produces a report.

Scans:
- `data/` contents (prose only, skipping YAML frontmatter keys/values)
- `profiles/` generated files
- `docs/` and root `.md` files
- `demo-data/` seed corpus
- `shared/operator.py` system prompt fragments
- Qdrant collections (all 4: claude-memory, profile-facts, documents, axiom-precedents)

Produces `profiles/axiom-sweep-report.json` with per-violation detail (source, implication, label, excerpt, line number) and summary statistics by implication and source type.

### Ongoing Coverage

1. **drift_detector** (weekly): gains a second pass running pattern checker against all documentation text. Axiom violations appear in drift report alongside factual drift.
2. **knowledge_maint** (weekly): gains a compliance check during staleness/dedup pass. Flags violating Qdrant entries in its report. "Report only" refers to the scanned existing content — knowledge_maint does not modify or delete violating entries it finds. knowledge_maint's own LLM-generated output (if any) goes through the enforcer like any other agent.

### Scope

- Current state on disk and in Qdrant
- Not git history
- Report only, no auto-remediation

## Error Handling

### Pattern Registry Failure

If `enforcement-patterns.yaml` fails to load, the enforcer refuses to start. No silent degradation. Error message includes the file path and next action.

### Judge Unavailability

- `full` paths: block delivery. Quarantine with reason "judge unavailable."
- `fast` paths: unaffected.
- `deferred` paths: queue for retry. Alert if unavailable >1 hour.

Fail closed, not open. A `full` path that cannot be validated cannot ship.

### Retry Prompt Amendment

On T0 violation retry, the enforcer appends to the system prompt:

```
Your previous output violated axiom implication {id}: {text}
Specific violation: {excerpt}
Regenerate your response without this violation.
```

Factual and directive. No rhetorical framing.

### Systemic Failure Alert

If an agent produces >3 quarantined outputs in 24 hours for the same path, the enforcer fires a systemic alert via ntfy. This indicates a system prompt problem requiring revision, not more retries.

## Observability and Metrics

### Enforcement Metrics

Recorded per `enforce()` call, attached to Langfuse trace spans:

| Metric | Type | Tags |
|---|---|---|
| `axiom.enforce.duration_ms` | histogram | `path`, `classification`, `check_type` |
| `axiom.enforce.violations` | counter | `path`, `implication_id`, `tier`, `action` |
| `axiom.enforce.retries` | counter | `path`, `implication_id` |
| `axiom.enforce.judge_unavailable` | counter | `path` |
| `axiom.audit.divergence` | counter | `agent_name` |

### Distributed Tracing

The enforcer enriches every LLM call's Langfuse trace with enforcement metadata:

```python
{
    "axiom_enforcement": {
        "path": "management-briefing",
        "classification": "full",
        "pattern_duration_ms": 0.4,
        "judge_duration_ms": 380.2,
        "total_duration_ms": 380.6,
        "violations_found": 1,
        "action_taken": "retried",
        "retries_used": 1,
        "retry_succeeded": True,
    }
}
```

End-to-end enforcement latency is visible per workflow in Langfuse trace explorer.

### Alert Thresholds

Configurable in `axioms/enforcement-config.yaml`:

```yaml
alerts:
  enforcement_latency_p95_ms: 1000
  quarantine_rate_24h: 3
  divergence_any: true
```

Alerts fire via ntfy.

If `enforcement-config.yaml` is missing or fails to parse, the enforcer uses these defaults and logs a warning. Unlike the pattern registry (which is required for enforcement to function), alert thresholds have safe defaults.

## Testing Strategy

All tests follow existing conventions: `unittest.mock`, no conftest fixtures, each test file self-contained, `asyncio_mode = "auto"`.

### Pattern Checker Tests

- Each pattern against known-violating and known-clean text
- Edge cases (e.g., "This isn't working" is not a rhetorical pivot)
- Registry loader: malformed YAML, missing fields, duplicate IDs
- `check_text()` with tier filtering

### Judge Tests (mocked LLM)

- Structured verdict responses at each tier trigger correct enforcement action
- Judge unavailability handling
- Judge requests carry `x-axiom-judge: true` metadata

### Enforcer Integration Tests (mocked LLM, real patterns)

- Full flow: text → pattern → judge → enforcement decision
- Retry logic: violation → retry → success
- Retry exhaustion → quarantine
- Each path classification behaves correctly
- Quarantine file creation with correct frontmatter
- T1/T2 violations log but deliver

### Audit Callback Tests (mocked LiteLLM interface)

- Violations annotated on Langfuse traces
- Divergence detection on un-tagged requests
- `x-axiom-judge: true` requests skipped

### Sweep Tests (mocked filesystem and Qdrant)

- File walking logic, frontmatter skipping
- Report generation format
- Qdrant entry scanning

## Implementation Order

1. hapax-constitution: this spec (reference pattern)
2. hapax-council: full implementation (largest surface, voice pipeline, all agents)
3. hapax-officium: port management-relevant subset (no voice, no sync agents)

## Design Decisions

| Decision | Rationale |
|---|---|
| Two layers (audit + enforcer) | Neither alone is sufficient: audit can't block, enforcer can be skipped |
| Default `full`, exceptions require reasoning | No grandfathering; exceptions must prove axiom conflict |
| Pattern layer + LLM judge | Patterns are fast/deterministic but can't catch novel violations; judge catches semantics |
| Fail closed on judge unavailability | A `full` path that can't be validated can't ship |
| Extant text sweep is report-only | Re-running agents loses original context; remediation is a separate future capability |
| Metrics via Langfuse trace enrichment | No new infrastructure; uses existing observability stack |
