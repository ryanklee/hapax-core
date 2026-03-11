# Full System Audit — Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit the entire system for completeness, correctness, and robustness at the part level, then for coherence, unity, flow, and purpose at the whole level — producing 10 findings documents and a prioritized fix plan.

**Architecture:** 8 sequential domain audits (foundation → infrastructure), each producing a standalone findings document. Then a holistic pass reading all 8 findings plus the code itself. The operator is a first-class component — the holistic pass treats the human-system boundary as a system interface. All output goes to `docs/audit/` in the hapaxromana repo.

**Tech Stack:** Python (ai-agents), TypeScript (cockpit-web, obsidian-hapax), Docker Compose (llm-stack), systemd (user services), n8n (workflows), Obsidian (vault)

**Design doc:** `docs/plans/2026-03-02-system-audit-design.md`

---

## Prerequisites

Before starting:

```bash
# Ensure you're in the hapaxromana repo
cd <hapaxromana>

# Create output directory
mkdir -p docs/audit

# Verify access to all repos
ls <ai-agents>/shared/config.py
ls <rag-pipeline>/ingest.py
ls <cockpit-web>/src/App.tsx
ls <obsidian-hapax>/src/main.ts
ls <llm-stack>/docker-compose.yml
ls <systemd-user>/
```

## Findings Document Template

Every domain findings doc uses this structure:

```markdown
# Domain N: [Name] — Audit Findings

## Inventory

| File | LOC | Test File | Test LOC |
|------|-----|-----------|----------|
| ... | ... | ... | ... |

**Total:** N source LOC, M test LOC, test:source ratio X.XX

## Completeness Findings

> Missing, dead, or assumed-but-absent.

### C-N.1: [Title]
**File:** `path/to/file.py:123`
**Severity:** critical | high | medium | low
**Finding:** [What's missing or dead]
**Impact:** [What breaks or is at risk]

## Correctness Findings

> Wrong, fragile, or accidental.

### R-N.1: [Title]
**File:** `path/to/file.py:45-67`
**Severity:** critical | high | medium | low
**Finding:** [What's wrong]
**Impact:** [What could go wrong]

## Robustness Findings

> Failure modes, silent errors, missing recovery.

### B-N.1: [Title]
**File:** `path/to/file.py:89`
**Severity:** critical | high | medium | low
**Finding:** [What fails silently or has no recovery]
**Impact:** [What happens when it fails]

## Test Coverage Assessment

| Area | Status | Notes |
|------|--------|-------|
| ... | tested / untested / badly tested | ... |

## Summary

- Completeness: N findings (X critical, Y high, Z medium)
- Correctness: N findings (X critical, Y high, Z medium)
- Robustness: N findings (X critical, Y high, Z medium)
```

Finding IDs follow the pattern: `C-N.X` (completeness), `R-N.X` (correctness), `B-N.X` (robustness) where N is the domain number. This enables cross-referencing in the holistic pass.

---

## Task 1: Domain 1 — Shared Foundation

**Scope:** The shared utilities that every other component depends on. Bugs here propagate everywhere.

**Files to read** (all paths relative to `<ai-agents>/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `shared/config.py` | 116 | `tests/test_config.py` | 64 |
| `shared/operator.py` | 178 | `tests/test_operator.py` | 169 |
| `shared/notify.py` | 173 | `tests/test_notify.py` | 224 |
| `shared/vault_writer.py` | 284 | `tests/test_vault_writer.py` | 200 |
| `shared/vault_utils.py` | 35 | — | — |
| `shared/langfuse_client.py` | 58 | — | — |
| `shared/langfuse_config.py` | 25 | — | — |
| `shared/email_utils.py` | 108 | — | — |

**Total:** 977 source LOC, 657 test LOC.

**Step 1: Read every source file**

Read all 8 source files listed above. For each, note:
- What it does (single sentence)
- What it exports (public functions/classes)
- What it depends on (imports from shared/ or external)
- Initialization pattern (module-level singletons? lazy init? required env vars?)

**Step 2: Read every test file**

Read all 4 test files. For each, note:
- What's tested (which functions, which scenarios)
- What's NOT tested (compare to exports from Step 1)
- Test quality (do mocks reflect reality? are edge cases covered?)

**Step 3: Audit for specific focus areas**

These are the questions from the design doc. Answer each with evidence:

1. **Model alias correctness** (`config.py`): Check `MODEL_ALIASES` dict. Are all aliases from CLAUDE.md represented? Do any point to nonexistent LiteLLM routes? Is the `get_model()` function's fallback behavior correct?

2. **Embedding functions** (`config.py`): Check `embed()` and `embed_batch()`. Do they add the `search_document:` / `search_query:` prefix correctly? What happens on Ollama timeout? On empty input? On batch with one failure?

3. **operator.json schema** (`operator.py`): Is `operator.json` validated on load or trusted blindly? What happens if a field is missing? What if `agent_context_map` references a nonexistent category? Check `get_system_prompt_fragment()`, `get_constraints()`, `get_patterns()`.

4. **Notification degradation** (`notify.py`): What happens when ntfy is unreachable? When `notify-send` has no desktop session? Does `send_webhook()` timeout? Are errors swallowed or propagated?

5. **Vault writer safety** (`vault_writer.py`): What happens on missing target directory? Permission error? Concurrent writes from multiple agents? Does it create directories or fail? Check all `write_*` functions.

6. **Langfuse auth** (`langfuse_client.py`, `langfuse_config.py`): How are credentials loaded? What happens on auth failure? On Langfuse being down? Timeout behavior?

7. **Singleton patterns**: Which modules use module-level singletons? What's the initialization order? Can circular imports occur?

8. **vault_utils.py and email_utils.py**: Are these used? By what? Are they tested indirectly? Dead code?

**Step 4: Write findings**

Write findings to `docs/audit/01-shared-foundation.md` using the template.

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/01-shared-foundation.md
git commit -m "audit: domain 1 — shared foundation findings"
```

---

## Task 2: Domain 2 — Data Ingestion

**Scope:** Everything that gets external data into the system — Google Takeout, Proton mail, LLM exports, RAG pipeline.

**Files to read:**

**Takeout** (`<ai-agents>/shared/takeout/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `processor.py` | 418 | `tests/test_takeout_processor.py` | 458 |
| `progress.py` | 159 | (tested in processor tests) | — |
| `chunker.py` | 136 | (tested in processor tests) | — |
| `models.py` | 53 | `tests/test_takeout_models.py` | 356 |
| `parsers/chrome.py` | 178 | `tests/test_takeout_parsers.py` | 797 |
| `parsers/calendar.py` | 206 | (in parsers tests) | — |
| `parsers/activity.py` | 216 | (in parsers tests) | — |
| `parsers/chat.py` | 184 | (in parsers tests) | — |
| `parsers/contacts.py` | 191 | (in parsers tests) | — |
| `parsers/drive.py` | 166 | (in parsers tests) | — |
| `parsers/gmail.py` | 177 | (in parsers tests) | — |
| `parsers/keep.py` | 141 | (in parsers tests) | — |
| `parsers/location.py` | 300 | (in parsers tests) | — |
| `parsers/photos.py` | 145 | (in parsers tests) | — |
| `parsers/purchases.py` | 193 | (in parsers tests) | — |
| `parsers/tasks.py` | 133 | (in parsers tests) | — |
| `profiler_bridge.py` | — | `tests/test_takeout_profiler_bridge.py` | 449 |

**Proton** (`<ai-agents>/shared/proton/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `parser.py` | 205 | `tests/test_proton.py` | 434 |
| `processor.py` | 207 | (in proton tests) | — |
| `labels.py` | 97 | (in proton tests) | — |

**Other ingestion:**

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `shared/llm_export_converter.py` | 386 | `tests/test_llm_export_converter.py` | 557 |

**RAG Pipeline** (`<rag-pipeline>/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `ingest.py` | 525 | — | — |
| `query.py` | 120 | — | — |

**Total:** ~5,124 source LOC, ~3,051 test LOC.

**Step 1: Read every source file**

Read all source files above. For the 13 takeout parsers, focus on: input format assumptions, output schema (`NormalizedRecord` fields populated), error handling on malformed data.

For `ingest.py`, focus on: watchdog event handling, Qdrant upsert logic, retry queue, frontmatter parsing.

**Step 2: Read every test file**

Read all 6 test files. Note coverage gaps — especially for parsers that handle real-world format variation.

**Step 3: Audit for specific focus areas**

1. **Parser correctness** — especially the Gemini parser (written speculatively without real data). Check each parser's input format assumptions against what Google Takeout / Proton / Claude.ai actually export.

2. **Resume/progress tracking** (`progress.py`): Does it survive Ctrl+C? What about partial writes? Is the JSONL progress file atomic? Check `ProgressTracker` — when is state flushed?

3. **Memory on large inputs**: Does `processor.py` stream or load entire ZIPs? The 500GB/14-zip scenario — does `process_batch()` open all ZIPs simultaneously? Check `zipfile.ZipFile` usage patterns.

4. **JSONL corruption**: What happens if `profiler_bridge.py` reads a partial line? If encoding is wrong? Check all JSONL read/write paths.

5. **RAG ingest recovery** (`ingest.py`): After crash, does the watchdog re-process files already ingested? Duplicate detection? The retry queue — is `30s→2m→10m→1h→1h` actually implemented correctly? Check `_retry_delay()` or equivalent.

6. **Frontmatter enrichment fidelity**: When `ingest.py` parses YAML frontmatter and writes to Qdrant, do the payload fields match the source metadata? Any fields dropped or renamed?

7. **`process_batch()` aggregation**: When processing multiple ZIPs, do progress trackers interfere? Are output directories shared safely?

8. **Email parsing** (`gmail.py`, `proton/parser.py`): Do they handle multipart MIME correctly? Encoded headers? HTML-only emails? The `email_utils.py` functions — `is_automated()`, `extract_body()`, `decode_header()` — are they robust?

**Step 4: Write findings to `docs/audit/02-data-ingestion.md`**

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/02-data-ingestion.md
git commit -m "audit: domain 2 — data ingestion findings"
```

---

## Task 3: Domain 3 — Operator Profile System

**Scope:** The profiler, its sources, the profile store (Qdrant), context tools, and management bridge.

**Files to read** (all paths relative to `<ai-agents>/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `agents/profiler.py` | 1,862 | `tests/test_profiler.py` | 1,225 |
| `agents/profiler_sources.py` | 958 | (tested in profiler tests) | — |
| `shared/profile_store.py` | 178 | `tests/test_profile_store.py` | 315 |
| `shared/context_tools.py` | 162 | `tests/test_context_tools.py` | 212 |
| `shared/management_bridge.py` | 298 | `tests/test_management_bridge.py` | 230 |

**Total:** 3,458 source LOC, 1,982 test LOC.

**Step 1: Read every source file**

The profiler is the largest single file (1,862 LOC). Read carefully. Map the `run_auto()` pipeline end-to-end: source discovery → fact extraction → deduplication → merge → save → digest → index.

**Step 2: Read every test file**

5 test files, 1,982 LOC. Check: are all 14 reader functions tested? (3 bridged sources have both text + structured paths.) Are edge cases (empty sources, malformed data, Qdrant down) covered?

**Step 3: Audit for specific focus areas**

1. **Source discovery completeness** (`profiler_sources.py`): List all readers. Do they each have a test? Do they handle their source data being absent gracefully? There are 14 distinct reader functions (3 bridged sources — takeout, proton, management — have both text + structured paths but share reader logic). Verify each handles absent data gracefully.

2. **Fact deduplication**: How does `profiler.py` deduplicate facts? Same key + same dimension = replace? Or accumulate? What about confidence conflicts — does higher confidence win?

3. **Confidence scoring consistency**: Different sources assign different confidence levels. Is there a documented rationale? Do `operator:correction` facts (1.0) actually override all others? Check `apply_corrections()`.

4. **Digest generation** (`generate_digest()`): Does it sample facts correctly? Does it handle empty dimensions? What if the LLM call fails mid-digest? Is the output structure what `ProfileStore.get_digest()` expects?

5. **Profile indexing to Qdrant** (`ProfileStore.index_profile()`): Deterministic IDs via `uuid5` — verify the namespace and format. Batch upsert — what's the batch size? What if Qdrant is down mid-batch?

6. **Structured fact loading** (`load_structured_facts()`): Loads from `takeout-structured-facts.json`, `proton-structured-facts.json`, `management-structured-facts.json`. What if one is missing? What if one is corrupt?

7. **Context tools error handling**: When Qdrant is down, `search_profile()` should fail gracefully. When `operator-digest.json` is missing, `get_profile_summary()` should fail gracefully. Verify.

8. **Management bridge vault scanning** (`management_bridge.py`): What happens with missing vault files? Malformed frontmatter? Empty properties? Check all `_extract_*` functions.

**Step 4: Write findings to `docs/audit/03-operator-profile.md`**

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/03-operator-profile.md
git commit -m "audit: domain 3 — operator profile system findings"
```

---

## Task 4: Domain 4 — Health & Observability

**Scope:** Health monitoring, infrastructure introspection, drift detection, activity analysis, knowledge maintenance.

**Files to read** (all paths relative to `<ai-agents>/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `agents/health_monitor.py` | 1,439 | `tests/test_health_monitor.py` | 689 |
| `agents/introspect.py` | 486 | `tests/test_introspect.py` | 679 |
| `agents/drift_detector.py` | 352 | `tests/test_drift_detector.py` | 453 |
| `agents/activity_analyzer.py` | 666 | `tests/test_activity_analyzer.py` | 371 |
| `agents/knowledge_maint.py` | 535 | `tests/test_knowledge_maint.py` | 401 |

**Total:** 3,478 source LOC, 2,593 test LOC. Highest test:source ratio (0.75).

**Step 1: Read every source file**

Focus on the health monitor first — it's the most critical (runs every 15 min, has auto-fix). Map all 49 checks across the 11 groups.

**Step 2: Read every test file**

All 5 agents have dedicated test files. Check: are all 49 health checks tested? Are auto-fix actions tested for safety?

**Step 3: Audit for specific focus areas**

1. **All 49 health checks** (`health_monitor.py`): List every check group and its checks. For each, verify: does it test what it claims? Are thresholds sensible (not too tight = false alarms, not too loose = missed failures)? Are there checks that always pass or always fail?

2. **Auto-fix safety**: Which checks have auto-fix? For each auto-fix action: what does it do? Can it make things worse? What's the blast radius? Is there a dry-run or confirmation step? Check the `auto_fix()` function and its callsites.

3. **Connectivity checks** (11th group): What's the timeout? Can a slow DNS lookup cause a false positive? Are the endpoints checked still valid?

4. **Drift detector accuracy** (`drift_detector.py`): Does it actually compare documentation to live system state, or does it pattern-match? How does `--fix` mode work? Could it generate incorrect doc fragments?

5. **Near-duplicate detection** (`knowledge_maint.py`): The 0.98 cosine similarity threshold — is this too aggressive (merging distinct items) or too lenient (missing near-duplicates)? How is the comparison done — pairwise across all vectors? Performance implications?

6. **Stale source pruning** (`knowledge_maint.py`): What criteria determine "stale"? Could it delete important data that just hasn't been updated recently? Is there a confirmation step or dry-run default?

7. **Manifest completeness** (`introspect.py`): Does it capture everything Docker/systemd/Qdrant actually has? Run `docker ps`, `systemctl --user list-units`, Qdrant collection list and compare to what introspect reports. Are there blind spots?

8. **Activity analyzer Langfuse queries** (`activity_analyzer.py`): URL encoding correctness (ISO timestamps with +00:00). Date range filtering. What happens when Langfuse is down or returns empty results?

9. **Health history growth**: Where is `profiles/health-history.jsonl` written? Is it bounded? Pruned? What happens after 6 months of 15-minute writes?

**Step 4: Write findings to `docs/audit/04-health-observability.md`**

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/04-health-observability.md
git commit -m "audit: domain 4 — health & observability findings"
```

---

## Task 5: Domain 5 — Intelligence Agents

**Scope:** LLM-using agents that produce analysis, content, or recommendations.

**Files to read** (all paths relative to `<ai-agents>/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `agents/research.py` | 181 | — | — |
| `agents/code_review.py` | 120 | — | — |
| `agents/briefing.py` | 385 | `tests/test_briefing.py` | 208 |
| `agents/scout.py` | 544 | — | — |
| `agents/digest.py` | 385 | `tests/test_digest.py` | 345 |
| `agents/management_prep.py` | 505 | `tests/test_management_prep.py` | 281 |

**Total:** 2,120 source LOC, 834 test LOC. **Lowest test coverage** — 3 agents have no test file at all.

**Also reference** (D6 tests that cover management data):

| Test File | LOC | Notes |
|-----------|-----|-------|
| `tests/test_management.py` | 387 | Tests management data collectors used by management_prep |

**Step 1: Read every source file**

For each agent, map: system prompt, tools registered, model used, input sources, output format, error handling.

**Step 2: Read every test file**

Only 3 of 6 agents have test files. For the untested ones (research, code_review, scout), note this as a completeness finding.

**Step 3: Audit for specific focus areas**

1. **Context tool registration**: After the context management refactoring (Stage 3), every LLM agent should have context tools registered. Verify each agent calls `get_context_tools()` and registers them. Check the agent creation pattern — is it consistent across all 6?

2. **LLM fallback behavior**: What model does each agent use? (`get_model("balanced")`, `get_model("fast")`, etc.) When the primary model is down, does LiteLLM's fallback chain engage transparently? Or does the agent crash?

3. **Output validation**: Do agents validate LLM output structure, or trust it blindly? For structured output agents (briefing, management_prep, scout), check if the output is parsed/validated before being written to disk.

4. **Briefing data freshness** (`briefing.py`): What input data does it consume? What happens when health data, activity data, or scout data is stale or missing?

5. **Scout web search** (`scout.py`): How does it call Tavily API? What happens on API failure, rate limit, empty results? Does it handle the Tavily response schema correctly?

6. **Management prep vault dependency** (`management_prep.py`): What happens when the vault has no people notes? No meetings? Malformed frontmatter? Does it gracefully degrade or crash?

7. **Digest content collection** (`digest.py`): How does it find recently-ingested RAG content? Qdrant query by timestamp? What if nothing was ingested recently?

8. **Research agent quality** (`research.py`): How does it query Qdrant? Are search results filtered or ranked? Does it handle empty results?

**Step 4: Write findings to `docs/audit/05-intelligence-agents.md`**

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/05-intelligence-agents.md
git commit -m "audit: domain 5 — intelligence agents findings"
```

---

## Task 6: Domain 6 — Cockpit

**Scope:** The TUI application — dashboard, chat, interview, copilot, accommodations, data collectors, all screens and widgets. Largest domain.

**Files to read** (all paths relative to `<ai-agents>/`):

**Core:**

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `cockpit/app.py` | 545 | `tests/test_cockpit_ui.py` | 374 |
| `cockpit/chat_agent.py` | 985 | `tests/test_chat_agent.py` | 295 |
| `cockpit/interview.py` | 655 | `tests/test_interview.py` | 578 |
| `cockpit/copilot.py` | 255 | `tests/test_copilot.py` | 474 |
| `cockpit/accommodations.py` | 163 | `tests/test_accommodations.py` | 190 |
| `cockpit/micro_probes.py` | 169 | `tests/test_micro_probes.py` | 154 |
| `cockpit/snapshot.py` | 364 | — | — |
| `cockpit/manual.py` | 280 | — | — |
| `cockpit/runner.py` | 160 | — | — |
| `cockpit/voice.py` | 28 | — | — |

**Screens:**

| Source File | LOC |
|-------------|-----|
| `cockpit/screens/chat.py` | 1,103 |
| `cockpit/screens/agent_config.py` | 181 |
| `cockpit/screens/detail.py` | 70 |
| `cockpit/screens/manual.py` | 23 |

**Widgets:**

| Source File | LOC |
|-------------|-----|
| `cockpit/widgets/sidebar.py` | 326 |
| `cockpit/widgets/output_pane.py` | 74 |
| `cockpit/widgets/action_items.py` | 70 |
| `cockpit/widgets/scout_panel.py` | 68 |
| `cockpit/widgets/infra_panel.py` | 60 |
| `cockpit/widgets/agent_launcher.py` | 52 |
| `cockpit/widgets/copilot_line.py` | 42 |

**Data collectors:**

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `cockpit/data/nudges.py` | 478 | `tests/test_nudges.py` | 899 |
| `cockpit/data/management.py` | 290 | `tests/test_management.py` | 387 |
| `cockpit/data/agents.py` | 185 | — | — |
| `cockpit/data/readiness.py` | 173 | `tests/test_readiness.py` | 315 |
| `cockpit/data/infrastructure.py` | 127 | — | — |
| `cockpit/data/goals.py` | 109 | `tests/test_goals.py` | 197 |
| `cockpit/data/briefing.py` | 97 | — | — |
| `cockpit/data/health.py` | 94 | — | — |
| `cockpit/data/cost.py` | 93 | — | — |
| `cockpit/data/decisions.py` | 64 | `tests/test_decisions.py` | 191 |
| `cockpit/data/scout.py` | 60 | — | — |
| `cockpit/data/gpu.py` | 37 | — | — |

**Total:** ~7,230 source LOC, ~4,054 test LOC.

**Step 1: Read every source file**

This is the largest domain. Prioritize:
1. `chat_agent.py` (985 LOC) — the primary operator interaction surface
2. `interview.py` (655 LOC) — complex state machine
3. `screens/chat.py` (1,103 LOC) — the UI for chat
4. `app.py` (545 LOC) — the main dashboard
5. `data/nudges.py` (478 LOC) — the attention priority system
6. All remaining files

**Step 2: Read every test file**

8 test files covering core + data collectors. Note the gaps — screens, widgets, snapshot, manual, runner, voice have no tests.

**Step 3: Audit for specific focus areas**

1. **Orphaned widgets**: `infra_panel.py` (60 LOC) and `scout_panel.py` (68 LOC) — are these imported anywhere? Used in any screen? If not, they're dead code. Check imports across all screens and `app.py`.

2. **Chat streaming reliability** (`chat_agent.py`, `screens/chat.py`): What happens on network interruption mid-stream? LLM timeout? Malformed SSE chunk? Does the UI recover or freeze?

3. **Interview state machine** (`interview.py`): Map all states and transitions. Can it get stuck in an unrecoverable state? What happens on crash mid-interview? Is state persisted or lost?

4. **Copilot priority rules** (`copilot.py`): What are the priority levels (P1-P4)? Do the rules match the documented behavior in the design docs? Is the logic correct?

5. **Accommodation persistence** (`accommodations.py`): Is `profiles/accommodations.json` read and written atomically? What happens on concurrent read+write?

6. **Data collector error isolation**: In `cockpit/data/`, if one collector crashes (e.g., `collect_docker()` when Docker is down), does it break other collectors? Check the `snapshot.py` or cache aggregation logic.

7. **Nudge priority scoring** (`data/nudges.py`, 478 LOC): Map all nudge sources and their priority scores. Are scores correct relative to each other? Does the priority ladder (critical > high > medium > low) make sense for an ADHD operator?

8. **Decision capture** (`data/decisions.py`): Are all operator actions on nudges recorded? What if the JSONL file is locked or full?

9. **Micro-probe cooldown** (`micro_probes.py`): Does the 600s cooldown survive restart? What if the system clock changes (NTP adjustment, timezone change)?

10. **voice.py** (28 LOC): Is this a placeholder, dead code, or a working feature? What does it actually do?

11. **Chat tools**: `record_observation`, `read_profile`, `correct_profile_fact` — trace each end-to-end. Does `record_observation` actually write to `pending-facts.jsonl`? Does `correct_profile_fact` actually call `apply_corrections()`?

12. **Slash commands**: `/pending`, `/flush`, `/profile`, `/export`, `/stop`, `/accommodate` — are all implemented and functional?

**Step 4: Write findings to `docs/audit/06-cockpit.md`**

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/06-cockpit.md
git commit -m "audit: domain 6 — cockpit findings"
```

---

## Task 7: Domain 7 — Web Layer

**Scope:** The new FastAPI backend and React SPA. Brand new code from Phase 1.

**Files to read:**

**Backend** (`<ai-agents>/cockpit/api/`):

| Source File | LOC | Test File | Test LOC |
|-------------|-----|-----------|----------|
| `app.py` | 48 | `tests/test_api.py` | 104 |
| `cache.py` | 124 | `tests/test_api_cache.py` | 46 |
| `routes/data.py` | 105 | (tested in test_api.py) | — |
| `__main__.py` | 41 | — | — |
| `__init__.py` | 1 | — | — |
| `routes/__init__.py` | 1 | — | — |

**Frontend** (`<cockpit-web>/src/`):

| Source File | LOC |
|-------------|-----|
| `api/types.ts` | 142 |
| `api/hooks.ts` | 35 |
| `api/client.ts` | 20 |
| `components/Sidebar.tsx` | 109 |
| `components/MainPanel.tsx` | 76 |
| `components/Header.tsx` | 29 |
| `App.tsx` | 15 |
| `main.tsx` | 19 |

**Also:** `<ai-agents>/Dockerfile.api` (20 LOC)

**Total:** ~722 source LOC, ~150 test LOC.

**Step 1: Read every source file**

Read all backend files, then all frontend files. Also read the `Dockerfile.api`.

**Step 2: Read test files**

Only 2 test files (150 LOC for 722 source LOC). Note coverage gaps.

**Step 3: Audit for specific focus areas**

1. **`_to_dict()` handling** (`routes/data.py`): Does `dataclasses.asdict()` work for ALL real dataclass shapes from ALL 13 collectors? Check for: nested dataclasses, lists of dataclasses, optional fields, enum values, datetime objects. Run through each collector's return type mentally.

2. **CORS configuration** (`app.py`): Are the allowed origins correct? No wildcard `*`? Are localhost:5173 and localhost:8050 the only legitimate origins?

3. **Cache thread safety** (`cache.py`): The `DataCache` singleton is accessed from asyncio tasks and request handlers concurrently. Is this safe? Are there race conditions between `refresh_fast()` writing and endpoint reads?

4. **Lifespan startup** (`app.py`): What happens if a collector fails during `start_refresh_loop()`'s initial `refresh_fast()` / `refresh_slow()`? Does the app start in a degraded state or crash?

5. **TypeScript types** (`api/types.ts`): Compare each TypeScript interface to its Python dataclass counterpart. Check: field names match, nullability matches, enum values match, no missing fields.

6. **Polling intervals** (`api/hooks.ts`): Do TanStack Query refetch intervals (FAST=30s, SLOW=5min) match the backend cache refresh intervals?

7. **Vite proxy** (`vite.config.ts`): Does `/api` proxy to `127.0.0.1:8050` correctly? What about WebSocket upgrades (for future SSE)?

8. **Missing endpoints**: List all 13 data collectors. For each, verify there's a corresponding API endpoint in `routes/data.py`. Any missing?

9. **Error responses**: When cache is empty (initial state), what does each endpoint return? When a collector fails, what does the client see? Is there differentiation between "no data yet" and "data collection failed"?

10. **Dockerfile.api**: Does it copy all required files? The `profiles/` directory is `COPY`'d — but at runtime, does the container have write access? Does `uv sync --frozen --no-dev` install all required deps?

**Step 4: Write findings to `docs/audit/07-web-layer.md`**

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/07-web-layer.md
git commit -m "audit: domain 7 — web layer findings"
```

---

## Task 8: Domain 8 — Infrastructure

**Scope:** Docker Compose, systemd services/timers, n8n workflows, secrets, vault structure, Dockerfile.

**Files to read:**

| Source File | LOC |
|-------------|-----|
| `<llm-stack>/docker-compose.yml` | 350 |
| `<systemd-user>/*.service` (14 files) | ~240 |
| `<systemd-user>/*.timer` (8 files) | ~79 |
| `<ai-agents>/n8n-workflows/briefing-push.json` | 109 |
| `<ai-agents>/n8n-workflows/health-relay.json` | 106 |
| `<ai-agents>/n8n-workflows/nudge-digest.json` | 80 |
| `<ai-agents>/n8n-workflows/quick-capture.json` | 249 |
| `<ai-agents>/Dockerfile.api` | 20 |
| `<ai-agents>/.envrc` | 20 |

**Also inspect live state:**

```bash
docker compose -f <llm-stack>/docker-compose.yml ps
systemctl --user list-timers
systemctl --user list-units --type=service --state=running
```

**Total:** ~1,240 LOC configuration.

**Step 1: Read docker-compose.yml**

Map every service: image, ports, volumes, healthcheck, environment variables, resource limits, restart policy, dependencies.

**Step 2: Read all systemd units**

For each service+timer pair, check: ExecStart command, WorkingDirectory, Environment/EnvironmentFile, MemoryMax, CPUQuota, Restart/RestartSec, OnFailure, timer OnCalendar schedule.

**Step 3: Read n8n workflows**

Read each JSON workflow. Map: trigger, nodes, connections, credentials referenced, error handling.

**Step 4: Read .envrc and check secrets**

Check for plaintext secrets in: `.envrc` files, `docker-compose.yml` env sections, n8n workflow JSONs, any `.env` files.

**Step 5: Audit for specific focus areas**

1. **Docker resource limits**: Which services have `mem_limit` or `cpus` set? Which don't? Are the limits sensible for a 24GB VRAM / consumer-grade machine?

2. **Healthcheck correctness**: For each Docker service with a healthcheck, verify it actually tests service functionality (not just process liveness). For services without healthchecks, note the gap.

3. **Systemd hardening**: For each service, check MemoryMax, CPUQuota, PrivateTmp, ProtectSystem, etc. Which services are unhardened?

4. **Timer scheduling conflicts**: Map all timers to a timeline. Sunday 02:00-04:30 has llm-backup (02:00), manifest-snapshot (02:30), drift-detector (03:00), knowledge-maint (04:30). Are there overlaps? Resource contention? Check if any two agents access the same resources simultaneously.

5. **n8n workflow correctness**: For each workflow (briefing-push, health-relay, nudge-digest, quick-capture/Telegram bot): Is the trigger correct? Are credentials valid? What happens on failure?

6. **Secret management**: Search for plaintext API keys, passwords, tokens in all config files. Check `.env` files in `<llm-stack>/`. Are all secrets coming from `pass` via `direnv`?

7. **Vault folder structure**: Compare what `vault_writer.py` expects (30-system/briefings, 30-system/nudges, etc.) with what actually exists in `<personal-vault>/`. Any mismatches?

8. **Dockerfile.api build**: Can it actually build? Run `docker build -f <ai-agents>/Dockerfile.api <ai-agents>/` mentally — are all COPY sources present? Does `uv sync --frozen --no-dev` succeed?

9. **Docker socket mount**: The cockpit-api container mounts `/var/run/docker.sock:ro`. What can it do with this? Is read-only sufficient protection?

10. **Langfuse v3 stack**: ClickHouse + Redis + MinIO — are they correctly configured to talk to each other? Volume persistence correct?

11. **Ollama GPU passthrough**: Is `deploy.resources.reservations.devices` correctly configured? Does `nvidia-container-toolkit` work?

12. **Log rotation**: All Docker services should use json-file driver with max-size 50m, max-file 3. Check each service.

13. **Boot sequence**: Does `llm-stack.service` (ExecStart=docker compose up -d) start everything in the right order? Are `depends_on` + healthchecks sufficient for ordered startup?

**Step 6: Write findings to `docs/audit/08-infrastructure.md`**

**Step 7: Commit**

```bash
cd <hapaxromana>
git add docs/audit/08-infrastructure.md
git commit -m "audit: domain 8 — infrastructure findings"
```

---

## Task 9: Holistic Pass

**Scope:** Examine the system as an integrated whole through 5 lenses. The operator is a first-class component.

**Inputs:** All 8 domain findings documents plus the code itself.

**Step 1: Re-read all 8 findings documents**

```bash
cat docs/audit/01-shared-foundation.md
cat docs/audit/02-data-ingestion.md
cat docs/audit/03-operator-profile.md
cat docs/audit/04-health-observability.md
cat docs/audit/05-intelligence-agents.md
cat docs/audit/06-cockpit.md
cat docs/audit/07-web-layer.md
cat docs/audit/08-infrastructure.md
```

Also re-read the design doc for the holistic methodology: `docs/plans/2026-03-02-system-audit-design.md` (lines 188-225).

**Step 2: Coherence analysis**

> Do the parts agree on what the system is and who the operator is?

Trace the operator model across all touchpoints:
- **Profiler** (`agents/profiler.py`): 13-dimension profile → `profiles/operator-profile.json`
- **Context tools** (`shared/context_tools.py`): reads `profiles/operator-digest.json`
- **System prompts** (`shared/operator.py`): `SYSTEM_CONTEXT` + `get_system_prompt_fragment()`
- **Accommodations** (`cockpit/accommodations.py`): `profiles/accommodations.json`
- **Nudge priorities** (`cockpit/data/nudges.py`): priority scoring for ADHD operator
- **Copilot** (`cockpit/copilot.py`): observational mode
- **Interview** (`cockpit/interview.py`): profile gap-filling

Question: When the system prompt says "ADHD and autism — task initiation and sustained attention are genuine cognitive challenges," does every agent actually behave as though that's true? Or do some agents demand sustained attention, overload with information, or ignore accommodations?

**Step 3: Unity analysis**

> One operator model or several? One way to do things or parallel approaches?

Map all representations of operator state:
- `profiles/operator-profile.json` — profiler output
- `profiles/operator-digest.json` — digest for context tools
- `profiles/accommodations.json` — negotiated system behavior changes
- `<cache>/cockpit/probe-state.json` — micro-probe cooldowns
- `<cache>/cockpit/pending-facts.jsonl` — unconfirmed observations
- `<cache>/cockpit/decisions.jsonl` — nudge action history

Do these inform each other, or are they parallel silos?

Also check for parallel approaches:
- Notification: `shared/notify.py` vs n8n webhooks vs `notify-send` direct calls
- Embedding: is `embed()` / `embed_batch()` used consistently, or do some modules call Ollama directly?
- Configuration: `shared/config.py` vs `.envrc` vs `operator.json` — one source of truth or three?
- Naming conventions: snake_case vs kebab-case vs camelCase across Python/TypeScript/YAML

**Step 4: Flow analysis**

> Does data move through the system without bottlenecks, dead ends, or orphaned paths?

Trace these flows end-to-end:

**Operator → System:**
1. Vault inbox note → RAG ingest → Qdrant → profiler reads → profile updated?
2. Chat observation (`record_observation`) → `pending-facts.jsonl` → profiler reads → profile updated?
3. Nudge decision → `decisions.jsonl` → profiler reads → behavioral insight?
4. Profile correction (`correct_profile_fact`) → profiler `apply_corrections()` → actually applied?
5. Probe response → where does it go?

**System → Operator:**
1. Health failure → notification → reaches operator when?
2. Briefing → vault + notification → operator reads when?
3. Nudge → TUI/web display → operator sees when? Are attention demands reasonable?
4. Copilot → TUI display → is observational mode actually low-interruption?
5. Accommodation proposal → confirmation → behavior change actually applied?

**Full lifecycle:**
Raw data → ingestion → Qdrant → retrieval → agent reasoning → output → operator attention → operator action → back into the system. Identify any breaks.

**Step 5: Part-to-whole purpose analysis**

> Does every part justify its existence?

For each component, ask:
- Does this serve externalized executive function? How?
- Would the operator notice if it disappeared?
- Is there cognitive overhead the operator still carries that this component could offload?

Check for unjustified components (built because they could be, not because they're needed). Check for gaps (things the operator still does manually that the system should handle).

**Step 6: Interface integrity analysis**

> Where domains meet, do they meet cleanly? Where the system meets the operator, is the interface well-designed?

Map all inter-domain interfaces:
- Shared foundation ↔ every other domain (config, operator context, notifications)
- Data ingestion ↔ profile system (structured facts, RAG content)
- Profile system ↔ intelligence agents (context tools, digest)
- Health ↔ cockpit (data collectors, nudges)
- Cockpit ↔ web layer (API cache, data endpoints)
- Infrastructure ↔ everything (Docker, systemd, secrets)

For each interface: Is the contract explicit (typed, documented) or implicit (convention, assumption)? What breaks if one side changes?

Operator interfaces:
- TUI (cockpit) — is it designed for ADHD? Low-distraction? Scannable?
- Web (cockpit-web) — same questions
- Mobile (Telegram bot, ntfy) — appropriate for mobile attention?
- Vault (Obsidian) — is the folder structure intuitive? Does it match mental model?

**Step 7: Write findings to `docs/audit/09-holistic.md`**

Use this structure:

```markdown
# Holistic Audit Findings

## Coherence Findings
(contradictions, disagreements between parts)

## Unity Findings
(parallel approaches, inconsistencies, naming drift)

## Flow Findings
(dead ends, orphaned data, broken chains, attention overload)

## Purpose Findings
(unjustified components, missing components, cognitive gaps)

## Interface Findings
(implicit contracts, fragile seams, mismatched assumptions)
```

**Step 8: Commit**

```bash
cd <hapaxromana>
git add docs/audit/09-holistic.md
git commit -m "audit: holistic findings — coherence, unity, flow, purpose, interface"
```

---

## Task 10: Consolidated Fix Plan

**Scope:** Consolidate all findings from Tasks 1-9 into a single prioritized action list.

**Inputs:** All 9 findings documents.

**Step 1: Extract all findings**

Read all 9 findings documents. Collect every finding ID (C-N.X, R-N.X, B-N.X, and holistic findings).

**Step 2: Prioritize**

Sort all findings into priority tiers:

| Priority | Criteria | Action Timeline |
|----------|----------|-----------------|
| **P0 — Critical** | Data loss risk, security vulnerability, silent corruption | Fix immediately |
| **P1 — High** | Incorrect behavior, missing error handling on critical paths | Fix this week |
| **P2 — Medium** | Dead code, missing tests, fragile assumptions | Fix this month |
| **P3 — Low** | Style inconsistency, minor gaps, nice-to-have hardening | Fix when convenient |

**Step 3: Group by work stream**

Organize fixes into logical work streams (not by domain — a single fix may address findings across multiple domains):

- **Error handling hardening** — all robustness findings about missing error handling
- **Test coverage gaps** — all completeness findings about missing tests
- **Dead code removal** — all completeness findings about unused code
- **Operator model unification** — holistic unity findings about parallel representations
- **Flow repairs** — holistic flow findings about broken data paths
- **Infrastructure hardening** — all Domain 8 findings about resource limits, secrets, healthchecks
- **Documentation updates** — drift findings, outdated docs

**Step 4: Write fix plan**

Write to `docs/audit/10-fix-plan.md` using this structure:

```markdown
# Audit Fix Plan

## Summary

- Total findings: N
- P0 (Critical): N
- P1 (High): N
- P2 (Medium): N
- P3 (Low): N

## P0 — Critical (fix immediately)

### Fix 1: [Title]
**Findings:** C-1.3, B-4.7
**Files:** `path/to/file.py`
**Action:** [Specific fix]
**Verification:** [How to verify the fix]

## P1 — High (fix this week)
...

## P2 — Medium (fix this month)
...

## P3 — Low (fix when convenient)
...

## Work Streams

### WS-1: Error Handling Hardening
**Findings:** B-1.2, B-2.5, B-3.1, ...
**Estimated scope:** N files, ~M LOC changes

### WS-2: Test Coverage Gaps
...
```

**Step 5: Commit**

```bash
cd <hapaxromana>
git add docs/audit/10-fix-plan.md
git commit -m "audit: consolidated fix plan — prioritized findings and work streams"
```

---

## Sequencing Rules

1. **Tasks 1-8 are strictly sequential** — each domain audit may reference findings from earlier domains
2. **Task 9 (holistic) requires all 8 domain audits complete** — it reads all findings
3. **Task 10 (fix plan) requires Task 9 complete** — it consolidates everything
4. **Commit after every task** — each findings doc is independently valuable
5. **Don't fix anything during the audit** — the audit produces findings, the fix plan produces actions. Mixing audit and fix muddles both

## Time Estimates

These are not code implementation tasks — they're deep reading + analysis tasks. Each domain audit requires reading and understanding every line of source code in that domain.

| Task | Source LOC to read | Relative effort |
|------|-------------------|-----------------|
| Task 1 (D1: Foundation) | 977 | Small |
| Task 2 (D2: Ingestion) | 5,124 | Large |
| Task 3 (D3: Profile) | 3,458 | Large |
| Task 4 (D4: Health) | 3,478 | Large |
| Task 5 (D5: Agents) | 2,120 | Medium |
| Task 6 (D6: Cockpit) | 7,230 | Very large |
| Task 7 (D7: Web) | 722 | Small |
| Task 8 (D8: Infra) | 1,240 | Medium |
| Task 9 (Holistic) | All findings | Large |
| Task 10 (Fix Plan) | All findings | Medium |
