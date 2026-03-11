# Domain 6: Cockpit — Audit Findings

**Audited**: 2026-03-02
**Scope**: ~7,230 LOC source, ~4,054 LOC tests across 30+ source files and 11 test files
**Files**: `cockpit/` package in `<ai-agents>/`

---

## Inventory

### Core (3,604 LOC)
| File | LOC | Purpose |
|------|-----|---------|
| `cockpit/chat_agent.py` | 985 | Chat agent factory, ChatSession, compaction, persistence |
| `cockpit/interview.py` | 655 | Interview state machine, planner, agent, profiler integration |
| `cockpit/app.py` | 545 | Main dashboard Textual app, refresh loops, copilot integration |
| `cockpit/snapshot.py` | 364 | Plain-text and Rich snapshot generators |
| `cockpit/manual.py` | 280 | Task-oriented operations manual generator |
| `cockpit/copilot.py` | 255 | Priority-ordered copilot rule engine |
| `cockpit/micro_probes.py` | 169 | Experiential question engine with cooldown |
| `cockpit/accommodations.py` | 163 | Negotiated behavior change persistence |
| `cockpit/runner.py` | 160 | Agent subprocess lifecycle with streaming |
| `cockpit/voice.py` | 28 | Operator name and greeting helper |

### Screens (1,377 LOC)
| File | LOC | Purpose |
|------|-----|---------|
| `cockpit/screens/chat.py` | 1,103 | Chat screen UI, slash commands, error diagnostics |
| `cockpit/screens/agent_config.py` | 181 | Agent flag configuration modal |
| `cockpit/screens/detail.py` | 70 | Generic detail viewer modal |
| `cockpit/screens/manual.py` | 23 | Manual viewer screen |

### Widgets (692 LOC)
| File | LOC | Purpose |
|------|-----|---------|
| `cockpit/widgets/sidebar.py` | 326 | Decomposed sidebar status panel |
| `cockpit/widgets/output_pane.py` | 74 | RichLog wrapper for command output |
| `cockpit/widgets/action_items.py` | 70 | Selectable nudge list |
| `cockpit/widgets/scout_panel.py` | 68 | Scout render function + orphaned widget class |
| `cockpit/widgets/infra_panel.py` | 60 | Infra render function + orphaned widget class |
| `cockpit/widgets/agent_launcher.py` | 52 | Selectable agent list |
| `cockpit/widgets/copilot_line.py` | 42 | Single-line copilot observation |

### Data Collectors (1,557 LOC)
| File | LOC | Purpose |
|------|-----|---------|
| `cockpit/data/nudges.py` | 478 | Multi-source nudge priority system |
| `cockpit/data/management.py` | 290 | Vault scanner for management state |
| `cockpit/data/agents.py` | 185 | Static agent registry |
| `cockpit/data/readiness.py` | 173 | Data maturity assessment |
| `cockpit/data/infrastructure.py` | 127 | Docker + systemd timer collectors |
| `cockpit/data/goals.py` | 109 | Operator goal staleness |
| `cockpit/data/briefing.py` | 97 | Briefing markdown parser |
| `cockpit/data/health.py` | 94 | Health check live + history |
| `cockpit/data/cost.py` | 93 | Langfuse cost aggregation |
| `cockpit/data/decisions.py` | 64 | JSONL decision capture |
| `cockpit/data/scout.py` | 60 | Scout report JSON reader |
| `cockpit/data/drift.py` | 51 | Drift report reader |
| `cockpit/data/gpu.py` | 37 | GPU/VRAM snapshot |

### Tests (~4,054 LOC)
| File | LOC | Tests |
|------|-----|-------|
| `tests/test_nudges.py` | 899 | Nudge priority scoring, all sources |
| `tests/test_interview.py` | 578 | Interview models, state machine, profiler integration |
| `tests/test_copilot.py` | 474 | All priority levels and rules |
| `tests/test_cockpit_ui.py` | 374 | Widget rendering, sidebar, action items |
| `tests/test_management.py` | 387 | Vault scanning, staleness computation |
| `tests/test_readiness.py` | 315 | Readiness levels, gap detection |
| `tests/test_chat_agent.py` | 295 | Split logic, repair, error classification, export |
| `tests/test_accommodations.py` | 190 | Load/save, confirm/disable lifecycle |
| `tests/test_goals.py` | 197 | Goal staleness thresholds |
| `tests/test_decisions.py` | 191 | JSONL append/read, cutoff filtering |
| `tests/test_micro_probes.py` | 154 | Probe selection, cooldown, state persistence |

---

## Completeness Findings

### C-6.1: Orphaned Widget Classes (Low)
**Evidence**: `cockpit/widgets/infra_panel.py:44` defines `InfraPanel(Static)` and `cockpit/widgets/scout_panel.py:52` defines `ScoutPanel(Static)`. Neither class is instantiated anywhere in the codebase. Grep confirms zero imports of these class names outside their own files.

However, the `render_infra_detail()` and `render_scout_detail()` functions in the same files ARE used by `app.py:378` and `app.py:270` respectively for drill-down detail views. The widget classes themselves are dead code -- likely remnants from a prior layout that embedded these directly in the dashboard.

**Impact**: Low. No functionality affected. ~30 LOC of dead code across two files.

### C-6.2: Missing Dismiss/Expired Decision Recording (Medium)
**Evidence**: `cockpit/data/decisions.py` defines three action types: `"executed" | "dismissed" | "expired"`. However, searching the codebase for where decisions are recorded:
- `app.py:392` records `action="executed"` when the operator selects an action item.
- No code records `"dismissed"` or `"expired"` decisions.

The `Decision.action` field documents three states, but only one is ever written. The profiler pipeline (`decisions.jsonl`) would see only "executed" actions, giving a skewed view of operator decision patterns.

**Impact**: Medium. Behavioral profiling from decisions is incomplete. Nudges that are ignored or dismissed are never captured.

### C-6.3: No /accommodate Proposal Path From Chat (Low)
**Evidence**: `cockpit/screens/chat.py:656-691` implements `/accommodate` with `confirm` and `disable` subcommands. But there is no way to *propose* new accommodations from the chat interface. `accommodations.py:127` has `propose_accommodation()` but it is never called from the chat or dashboard. New accommodations can only be added programmatically.

**Impact**: Low. The accommodation system works end-to-end for pre-proposed items. The proposal-from-discovery path is not wired up but the architecture supports it.

### C-6.4: Manual Timer Schedule Hardcoded (Low)
**Evidence**: `cockpit/manual.py:200-208` hardcodes `TIMER_SCHEDULE` as a static list of 7 timers. The actual systemd timer set (documented in CLAUDE.md as 10 timers) includes `digest.timer`, `knowledge-maint.timer`, and `scout.timer` which are absent from the manual's timer table.

**Impact**: Low. Documentation drift. The agent reference section is generated dynamically from the registry, but the timer section is not.

---

## Correctness Findings

### R-6.1 (retracted): _send_interview_message return path is correct
**Evidence**: `chat_agent.py:757-826`. Examined all code paths through the retry loop. Every path either returns a string or raises. No silent None return. Not a finding.

### R-6.2: Micro-Probe Cooldown Uses monotonic() -- Does Not Survive Restart (Medium)
**Evidence**: `micro_probes.py:128` checks `time.monotonic() - self._last_probe_time < PROBE_COOLDOWN`. The `_last_probe_time` is initialized to `0.0` (line 114) and only updated via `mark_asked()` (line 149). The `save_state()` method (line 152) persists `asked_topics` but NOT `_last_probe_time`. The `load_state()` method (line 160) restores `asked_topics` but leaves `_last_probe_time` at `0.0`.

**Consequence**: After a cockpit restart, the 600-second cooldown is immediately expired. A probe will be offered on the first idle evaluation after restart, even if one was asked 30 seconds before the restart.

**Impact**: Medium. The operator may see probes too frequently across restarts. Not harmful but potentially annoying.

### R-6.3: Accommodation Persistence is Not Atomic (Medium)
**Evidence**: `accommodations.py:124` uses `_ACCOMMODATIONS_PATH.write_text(json.dumps(data, indent=2))`. This is a direct file write with no atomic pattern (write-to-temp + rename). If the process is interrupted mid-write, the file may be truncated.

The `load_accommodations()` function (line 71) catches `json.JSONDecodeError` and returns an empty `AccommodationSet`, so truncation would silently discard all accommodations.

There is no concurrent access concern in practice (single cockpit process), but the non-atomic write is a robustness gap. The same pattern appears in `micro_probes.py:158` for probe state.

**Impact**: Medium. Data loss on crash during write is unlikely but the consequence (silent accommodation loss) is significant.

### R-6.4: record_observation JSONL Append Has No Locking (Low)
**Evidence**: `chat_agent.py:349` uses `open(facts_path, "a")` to append to `pending-facts.jsonl`. On Unix, `O_APPEND` guarantees atomic writes under PIPE_BUF (4096 bytes) for a single write call. Since each JSON line is well under 4KB, this is effectively safe for single-writer scenarios. Multiple concurrent cockpit instances would still be safe due to the kernel's append atomicity guarantee.

**Impact**: Low. The current single-writer architecture makes this a non-issue in practice.

### R-6.5: ChatSession.save() Writes Non-Atomically (Low)
**Evidence**: `chat_agent.py:844` uses `path.write_text(json.dumps(data, indent=2))`. Same non-atomic pattern as accommodations. A crash during save could corrupt the session file. On next load (line 847-865), `json.loads()` would raise, and the fallback (line 275-276 in chat screen) creates a fresh session. So the consequence is session loss, not a crash.

**Impact**: Low. Session loss on crash is acceptable -- the data is ephemeral by nature.

---

## Robustness Findings

### B-6.1: Chat Streaming -- Network Interruption Handling (Medium)
**Evidence**: `chat_agent.py:675-718` uses `async with self.agent.run_stream(...)` and iterates with `async for response, _is_last in stream.stream_responses()`. If the network drops mid-stream:

1. The `run_stream` context manager will eventually raise an exception (timeout or connection error).
2. The `finally:` block at line 720-721 sets `self.generating = False`.
3. In `screens/chat.py:886-889`, the exception handler calls `classify_chat_error(e)` and displays a diagnostic.

The streaming text widget (`#streaming-text`) is cleaned up in both the success path (line 844-845) and error path (line 887-888). The input widget is re-enabled in the `finally` block (line 891-893).

**Assessment**: The error handling for network interruption is solid. The UI recovers correctly. The `classify_chat_error` function categorizes timeouts and connection errors as `"provider_down"` and suggests switching providers.

One gap: there is no explicit timeout on `stream.stream_responses()`. If the provider holds the connection open but stops sending data, the stream could hang indefinitely. The pydantic-ai library may have internal timeouts, but the cockpit layer does not impose one. This is inherited from the upstream library behavior.

**Impact**: Medium. The common failure modes are handled. An indefinite hang on a stalled stream would require the operator to use `/stop` or `Escape`.

### B-6.2: Data Collector Error Isolation (Low -- Well Handled)
**Evidence**: In `app.py:166-180`, `refresh_fast()` uses `asyncio.gather()` for health, docker, vram, and timers. If any one fails, `asyncio.gather()` with default settings will propagate the first exception, potentially preventing the others from being displayed.

However, examining the collectors themselves: `collect_live_health()` (health.py:40-64), `collect_docker()` (infrastructure.py:26-43), `collect_vram()` (gpu.py:18-37), and `collect_timers()` (infrastructure.py:46-127) all wrap their internals in `try/except` and return empty/default values on failure. So in practice, `asyncio.gather()` will never receive an exception from these collectors.

In `refresh_slow()` (app.py:183-245), collectors are called sequentially and each is individually wrapped.

In `snapshot.py:158-186`, `generate_snapshot()` also uses `asyncio.gather()` for the same four async collectors, with the same guarantee.

The nudge system (`nudges.py:418-461`) calls each source collector inside its own `try/except` block, so a failure in one source (e.g., management vault unavailable) does not prevent other nudge sources from contributing.

**Assessment**: Error isolation is well-implemented through defensive coding in every collector.

**Impact**: Low. This is a strength of the design.

### B-6.3: Interview State Machine -- Stuck States (Medium)
**Evidence**: The interview state machine is implicit, driven by `InterviewState` (interview.py:71-93):
- **States**: Not explicitly enumerated. Derived from `mode` on `ChatSession` and `topics_explored` on `InterviewState`.
- **Transitions**:
  - `chat` -> `interview`: `start_interview()` (chat_agent.py:547). Sets `mode="interview"`, creates `InterviewState`, calls LLM for opening message.
  - `interview` -> `chat`: `end_interview()` (chat_agent.py:587). Flushes facts, clears state.
  - `clear()`: (chat_agent.py:509) resets everything.

**Can it get stuck?**
1. If `start_interview()` raises during plan generation (line 569), the exception handler in `screens/chat.py:953-959` resets `mode` to "chat" and clears `interview_state`. Clean recovery.
2. If the LLM fails mid-interview (during `send_message`), the error handler in `screens/chat.py:886-889` displays the diagnostic but does NOT reset the mode. The interview state is preserved. The operator can retry or `/interview end`.
3. If `end_interview()` raises during `flush_interview_facts`, the error handler in `screens/chat.py:983-984` displays the error. The mode is NOT reset (end_interview raises before `self.mode = "chat"` at line 605). The operator can retry `/interview end` or `/clear`.

**Stuck scenario**: If `flush_interview_facts` consistently fails (e.g., corrupted profile file), `/interview end` will keep failing. The only escape is `/clear`, which discards the accumulated facts and insights. There is no way to save interview facts to a backup location.

**Impact**: Medium. Data loss path exists for accumulated interview facts if the profiler pipeline is broken.

### B-6.4: History Repair -- Retry Logic Correctness (Low)
**Evidence**: `chat_agent.py:774-826`. The `_send_interview_message` method has a 2-attempt retry for `tool_result` errors. On the first attempt, if the error contains "tool_result", `_repair_history()` is called and the loop continues. On the second attempt, any error is re-raised.

The `_repair_history()` method (line 518-538) walks backward through history to find the last clean user turn and trims history to start there. If no safe point is found, it clears history entirely but preserves `interview_state` (facts, insights).

This is a robust recovery mechanism. The history is expendable; the interview state is the valuable data.

**Impact**: Low. Well-designed recovery.

### B-6.5: Compaction Race -- Summary Agent Failure (Low)
**Evidence**: `chat_agent.py:723-755`. The `_maybe_compact()` method checks message count and serialized size thresholds, then attempts to summarize old messages with a separate "fast" model agent. If summarization fails (line 754-755), the `except Exception: pass` silently keeps full history.

This is the correct behavior -- compaction is best-effort. Failure means slightly higher token usage on the next turn, not data loss.

**Impact**: Low. Graceful degradation.

### B-6.6: decisions.jsonl Unbounded Growth (Low)
**Evidence**: `decisions.py:33` appends to `<cache>/cockpit/decisions.jsonl` on every nudge execution. There is no rotation, truncation, or cleanup mechanism. The `collect_decisions()` function (line 39-64) has a time-based filter (default 7 days), but the file itself grows forever.

Over time with frequent nudge interactions, this file could become large. However, the read pattern (read all lines, parse JSON, filter by time) is O(n) in file size, so performance would degrade only gradually.

**Impact**: Low. Practical issue only after months of heavy use.

### B-6.7: pending-facts.jsonl Clear-After-Flush is Not Atomic (Medium)
**Evidence**: `screens/chat.py:246` clears the pending facts file with `facts_path.write_text("")` after flushing. If the cockpit crashes between the flush call (line 244) and the clear (line 246), the facts would be flushed again on next `/flush`, resulting in duplicates in the profile.

The profiler's `merge_facts` function uses key-based deduplication, so exact duplicates would be merged. But if confidence or evidence differs between the flush and a future observation, both would coexist.

**Impact**: Medium. Duplicate fact injection is possible but mitigated by profiler deduplication.

---

## Focus Area Answers

### 1. Orphaned Widgets
**InfraPanel** (`infra_panel.py:44`) and **ScoutPanel** (`scout_panel.py:52`) are dead code. The class names appear nowhere outside their defining files. Only the standalone `render_infra_detail()` and `render_scout_detail()` functions are used, by `app.py` for drill-down modal views. The widget classes can be safely removed. See **C-6.1**.

### 2. Chat Streaming Reliability
Network interruption: handled via exception propagation from pydantic-ai's streaming, caught in `screens/chat.py:886`. LLM timeout: classified as `"provider_down"` by `classify_chat_error()`. Malformed SSE: would surface as a library exception, caught by the same handler. UI recovery: streaming widget cleared in both success and error paths; input re-enabled in `finally` block. One gap: no explicit timeout on the streaming iterator itself -- a stalled-but-open connection would hang. See **B-6.1**.

### 3. Interview State Machine
**States**: `chat` (normal), `interview` (active interview with plan/facts/insights). **Transitions**: `start_interview()` -> interview; `end_interview()` -> chat; `/clear` -> chat. **Stuck paths**: Plan generation failure is recovered (mode reset). LLM failure mid-interview preserves state for retry. `end_interview()` failure leaves mode as "interview" -- operator must retry or `/clear`. Crash mid-interview: session persistence (`save()` called after each turn) preserves interview state to `<cache>/cockpit/chat-session.json`, restored on reload via `InterviewState.model_validate()`. See **B-6.3**.

### 4. Copilot Priority Rules
Priority levels in `copilot.py`:
- **P1 (Immediate transitions)**: Health status change to non-healthy (line 93), agent completion within 10s (line 100), return from chat screen (line 106).
- **P2 (Ongoing concerns)**: Stale briefing with open items (line 112), degraded health (line 122), failed health (line 129), high VRAM (line 132), drift items >5 (line 135), bootstrapping readiness with cooldown (line 138).
- **P3 (Idle nudges)**: >300s idle: rotate readiness messages (line 148), surface micro-probes every 4th eval (line 156), default "quiet session" (line 159).
- **P4 (Ambient)**: Session greeting in first 60s (line 162), ambient status with health + briefing age (line 165).

Rules are evaluated top-to-bottom, first match wins. This matches the documented behavior in `cockpit-ui.md`. The readiness observation pools and cooldown mechanism prevent message repetition.

### 5. Accommodation Persistence
`profiles/accommodations.json` is read with `Path.read_text()` (line 72) and written with `Path.write_text()` (line 124). Neither operation is atomic. Concurrent access is not a concern (single cockpit process). Crash during write would truncate the file; `load_accommodations()` catches `json.JSONDecodeError` and returns an empty set, silently losing all accommodations. See **R-6.3**.

### 6. Data Collector Error Isolation
Excellent. Every async collector (`collect_live_health`, `collect_docker`, `collect_vram`, `collect_timers`) has internal try/except returning defaults on failure. Nudge collectors each have individual try/except blocks. Management vault scanning wraps people/coaching/feedback collection independently. The pattern is consistent across all 13 data collectors. See **B-6.2**.

### 7. Nudge Priority Scoring
Complete scoring map from `nudges.py`:

| Source | Score | Label | Condition |
|--------|-------|-------|-----------|
| Health failures | 100 | critical | Last health check failed/degraded |
| Briefing high-priority items | 80 | high | Briefing has high-priority action items |
| Briefing action items | 80/50/25 | high/med/low | Individual items by priority |
| Stale briefing + open items | 75 | high | >26h old with action items |
| Stale 1:1 | 70 | high | Person.stale_1on1 |
| No interview | 65 | high | readiness.interview_conducted=False |
| Overdue feedback | 65 | high | feedback.overdue |
| Stale primary goals | 60 | medium | Goal.stale, category=primary |
| Profile incomplete (>=3 missing) | 60 | medium | >=3 missing dimensions |
| High cognitive load | 60 | medium | cognitive_load >= 4 |
| No briefing | 55 | medium | Briefing file missing |
| Stale briefing (clean) | 55 | medium | >26h old, no items |
| Priorities not validated | 55 | medium | readiness.priorities_known=False |
| Overdue coaching | 55 | medium | coaching.overdue |
| Neurocognitive unmapped | 50 | medium | readiness.neurocognitive_mapped=False |
| Profile incomplete (<3 missing) | 50 | medium | 1-2 missing dimensions |
| Drift items | 50 | medium | drift_count > 0 |
| Sparse profile | 40 | medium | Sparse dimensions, no missing |
| Stale secondary goals | 35 | low | Goal.stale, category=secondary |
| Scout adopt | 30 | low | adopt_count > 0 |
| Scout/drift stale | 25 | low | >192h old |
| Scout evaluate | 20 | low | evaluate_count > 0 |

Scores are internally consistent. Health is highest (system integrity), management is high (people impact), profile gaps are medium (system effectiveness), scout/drift are low (improvement opportunities). The energy-aware accommodation reduces non-critical/non-high scores by 20% during configured low-energy hours.

### 8. Decision Capture
Only `"executed"` decisions are recorded (`app.py:392`). No `"dismissed"` or `"expired"` actions are captured. The JSONL append uses `open(..., "a")` which is safe for single-writer. The `collect_decisions()` reader filters by timestamp cutoff. The file grows unbounded. See **C-6.2** and **B-6.6**.

### 9. Micro-Probe Cooldown
The 600s cooldown does NOT survive restart. `_last_probe_time` uses `time.monotonic()` and is not persisted. After restart, it resets to `0.0`, making the cooldown immediately expired. The `asked_topics` set IS persisted to `<cache>/cockpit/probe-state.json`, so already-asked probes are not repeated. Clock changes (NTP drift, timezone) do not affect `time.monotonic()` as it is a monotonic clock. See **R-6.2**.

### 10. voice.py
**Working feature, not dead code.** 28 LOC providing two functions:
- `operator_name()`: reads operator name from `shared.operator.get_operator()`, falls back to "Operator". Used by `copilot.py:90` for greeting and `copilot.py:211` for session greeting.
- `greeting()`: time-of-day greeting string. Used by `app.py:89` on mount and `app.py:248` on slow refresh to set the app title.

Both functions are actively called and handle exceptions gracefully with fallbacks.

### 11. Chat Tools End-to-End

**record_observation** (`chat_agent.py:314-352`):
1. Chat agent calls `record_observation(dimension, key, value, evidence)`.
2. Appends JSON line to `<cache>/cockpit/pending-facts.jsonl`.
3. Operator runs `/flush` -> `_flush_pending_facts()` (`screens/chat.py:213-247`) reads JSONL, creates `RecordedFact` objects, calls `flush_interview_facts(facts, insights=[], source="conversation:cockpit")`.
4. Profiler's `flush_interview_facts` merges into `profiles/operator-profile.json`.

**read_profile** (`chat_agent.py:398-439`):
1. Chat agent calls `read_profile(dimension="")` for summary or `read_profile(dimension="workflow")` for detail.
2. Reads `profiles/operator-profile.json` via `load_existing_profile()`.
3. Returns formatted text. No write side-effects.

**correct_profile_fact** (`chat_agent.py:442-470`):
1. Chat agent calls `correct_profile_fact(dimension, key, value)`.
2. Creates correction dict with `value=None` for DELETE or actual value for update.
3. Calls `apply_corrections()` from profiler, which writes to `profiles/operator-profile.json` with source `"operator:correction"` and confidence `1.0`.

All three tools trace end-to-end correctly. The `/pending` and `/flush` commands provide operator visibility into the pending-facts pipeline.

### 12. Slash Commands
All documented commands are implemented in `screens/chat.py:465-588`:

| Command | Line | Status |
|---------|------|--------|
| `/help` | 472 | Implemented |
| `/clear` | 477 | Implemented |
| `/new` | 489 | Implemented |
| `/model <name>` | 504 | Implemented |
| `/context` | 525 | Implemented |
| `/save` | 531 | Implemented |
| `/export` | 542 | Implemented |
| `/stop` | 562 | Implemented |
| `/interview [end\|status\|skip]` | 570 | Implemented |
| `/accommodate [confirm\|disable]` | 573 | Implemented |
| `/pending` | 576 | Implemented |
| `/flush` | 579 | Implemented |
| `/profile [dim\|correct\|delete]` | 582 | Implemented |

All 13 slash commands are fully implemented. The HELP_TEXT (line 87-116) documents most but omits `/accommodate`, `/pending`, and `/flush`.

---

## Test Coverage

### Covered Areas (Strong)
- **Nudge scoring**: 899 LOC of tests cover all 10+ nudge sources, score values, ordering, accommodation adjustments, and edge cases (empty data, partial data).
- **Interview**: 578 LOC covering models, state transitions, serialization/deserialization, profiler integration, summary formatting, plan filtering of well-covered dimensions.
- **Copilot**: 474 LOC covering all 4 priority levels, readiness observations, accommodation post-processing, edge transitions.
- **Chat agent**: 295 LOC covering history split logic, repair, error classification, export formatting, input history.
- **Management**: 387 LOC covering vault scanning, 1:1 staleness, coaching/feedback overdue.
- **Readiness**: 315 LOC covering all three levels, gap computation, interview detection.
- **Accommodations**: 190 LOC covering load/save, confirm/disable lifecycle, derived flags.
- **Goals**: 197 LOC covering staleness thresholds, all status types.
- **Decisions**: 191 LOC covering JSONL append/read, timestamp filtering.
- **Micro-probes**: 154 LOC covering selection, cooldown, state persistence, gap-based prioritization.

### Coverage Gaps
1. **ChatSession streaming**: No tests for `send_message()`, `_send_interview_message()`, or `_maybe_compact()` -- these require an LLM mock. The deterministic helpers around them are tested.
2. **ChatScreen UI**: No Textual app-level tests (mount, message handling, slash command dispatch). Only widget unit tests.
3. **Snapshot generation**: No tests for `generate_snapshot()` or `generate_snapshot_rich()`. All format functions are implicitly tested through the data collectors.
4. **Runner subprocess**: No tests for `AgentRunner.run()` or `run_shell()`. Would require subprocess mocking.
5. **App refresh loops**: No integration tests for `refresh_fast()` or `refresh_slow()`.

The test strategy is appropriate: focus on deterministic logic (scoring, state machines, parsing) rather than async I/O and LLM interactions. The coverage gaps are all in areas that would require significant mocking infrastructure.

---

## Summary

| Severity | Count | IDs |
|----------|-------|-----|
| Critical | 0 | -- |
| High | 0 | -- |
| Medium | 6 | C-6.2, R-6.2, R-6.3, B-6.1, B-6.3, B-6.7 |
| Low | 9 | C-6.1, C-6.3, C-6.4, R-6.4, R-6.5, B-6.2, B-6.4, B-6.5, B-6.6 |

**Key Concerns**:

1. **Decision capture is one-dimensional** (C-6.2): Only "executed" actions are recorded. Dismissed and expired nudges are invisible to the profiler, limiting behavioral analysis.

2. **Micro-probe cooldown does not persist across restarts** (R-6.2): The 600s cooldown resets on cockpit restart. Frequent restarts could lead to probe fatigue.

3. **Non-atomic file writes for persistent state** (R-6.3): Accommodation and session files use direct `write_text()`. A crash during write silently discards data on next load. The write-to-temp-then-rename pattern would eliminate this risk.

4. **Interview fact loss on profiler failure** (B-6.3): If `flush_interview_facts` consistently fails, `/interview end` keeps failing and the only escape (`/clear`) discards all accumulated facts with no backup.

5. **Help text does not document all commands** (C-6.4): `/accommodate`, `/pending`, and `/flush` are implemented but not listed in `/help` output.

**Strengths**:

1. **Error isolation is excellent**: Every data collector has its own try/except boundary. A failure in one subsystem (vault, Langfuse, Docker) never cascades to others.

2. **Chat error diagnostics are thoughtful**: The `classify_chat_error()` + `_format_error_diagnostic()` system provides context-aware guidance (different suggestions for interview vs chat, for rate limits vs corruption).

3. **History repair is well-designed**: The `_repair_history()` mechanism preserves interview state while fixing orphaned tool_result messages. The 2-attempt retry in `_send_interview_message` is a good recovery strategy.

4. **Nudge priority system is comprehensive**: 10+ sources, well-calibrated scores, accommodation-aware adjustments, and thorough test coverage (899 LOC).

5. **Copilot rule engine is clean**: Priority-ordered evaluation with clear separation of concerns. The readiness observation pools with cooldown prevent message fatigue.
