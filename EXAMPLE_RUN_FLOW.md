# Example Run Flow — One Full QA Batch, Step by Step

This walks one concrete example through the whole system. Shapes reference `SHARED_CONTRACTS.md`. The loop under test is defined in `example-loops/morning-triage.md`.

## The target system under test

**Morning-Triage** — the canonical dev-automation loop from the *Loop Engineering* paper (our demo guinea pig; built by Orchestration as a controlled loop):

- `triage_agent` — reads the morning backlog (CI failures, issues, commits, prior state), judges each item (actionable? blocks a release? already tracked → skip), prioritizes, writes findings to the state file, hands off one item at a time.
- `fixer_agent` — a sub-agent given one finding + a goal (stop-condition); drafts a fix in an isolated worktree.
- `reviewer_agent` — a fresh-model judge that "assumes broken"; runs the tests, approves → opens a PR (mocked), or rejects → back to the fixer (bounded retries).

Loop: triage → fixer → reviewer → (PR opened | back to fixer), then triage moves to the next item. Termination: `goal_reached` (all items resolved) or `max_iterations` or `stall_detected`.

**Why this loop is controllable:** each sandbox is seeded with a **synthetic backlog containing planted bugs and an answer key** (which test must pass, which files must not change, correct priority). "Open a PR" is mocked; "tests pass" is a deterministic checker we own. So we get real agent behavior *and* a ground-truth oracle.

## Step 1 — Register the spec

`POST /api/specs` with the Morning-Triage `LoopSpec` (3 `AgentDef`s, topology edges, termination `{max_iterations: 30, goal_check: "all_items_resolved"}`). Returns `spec_id: "spec_morning_triage_01"`.

## Step 2 — Launch the batch

`POST /api/runs` with `{spec_id: "spec_morning_triage_01", n_sandboxes: 100, seed_strategy: "varied"}`.

Fan-out controller creates `run_id: "run_abc"`, 100 `SandboxRun` docs in `pending`, and starts provisioning. Seed variation: 100 different synthetic backlogs (different mixes of CI failures / issues / commits, each with its own answer key), remixed from a library of bug archetypes.

## Step 3 — Sandboxes run

Each sandbox executes the loop. Sandbox #37, iteration 4, `triage_agent` hands the "auth token TTL" CI failure to `fixer_agent` — the runner emits:

```json
{
  "event_id": "evt_...", "run_id": "run_abc", "sandbox_id": "sb_037",
  "seq": 19, "type": "agent_message", "ts": "...",
  "from_agent": "triage_agent", "to_agent": "fixer_agent",
  "payload": {"content": "Item ci_1: auth token expires too early. Goal: make test_auth_token pass without touching billing.py."},
  "tokens": 214
}
```

Backboard memory writes (the loop's `./state/triage.md` equivalent) surface as `state_update` events. "Open PR" and "run tests" surface as `tool_call` / `tool_result`. Events batch (25 at a time) to `POST /api/events`. Dashboard's fleet view shows state counts shifting: 100 pending → running → mix of completed/stalled.

## Step 4 — Failures are data

- **Sandbox #12 (stall):** `fixer_agent` and `reviewer_agent` bounce the same fix back and forth 6 times — reviewer keeps rejecting, fixer keeps re-drafting the same approach, no progress → runner emits `termination` with `stall_detected`. Not retried.
- **Sandbox #44 (nodding reviewer — the money finding):** `reviewer_agent` **approves** the fix and "opens a PR," but the deterministic oracle says the fix does **not** make `test_auth_token` pass. Recorded as a Tier-2 correctness failure: *approved-but-broken*. Not retried.
- **Sandbox #58 (error):** a Gemini call errors mid-loop → `termination: error`. Not retried.
- **Sandbox #71 (infra):** provisioning failure → infra retry (the ONLY retried class).

## Step 5 — Batch completes, analysis runs

Aggregation pipelines over `events` + `sandbox_runs` for `run_abc`:

- **Completion rate:** 78% reached `goal_reached` (all items resolved)
- **Nodding-reviewer rate (Tier-2, vs answer key):** **9%** of runs had ≥1 fix the reviewer approved that the oracle marks broken — clustered on multi-file changes
- **Stall rate:** 12% — clustering shows most stalls are the fixer↔reviewer bounce when the failing test is flaky
- **Iteration histogram:** median 6, long tail to 30
- **Cost:** mean 41k tokens/run, p95 118k
- **Divergence:** identical-seed control pairs picked a different top-priority item 14% of the time (triage is non-deterministic)
- **Per-handoff fragility:** the `triage_agent → fixer_agent` handoff drops the "must not touch" constraint in 6% of handoffs

Gemini summarizes the approved-but-broken cluster into a `Finding`:

> **critical — Reviewer approves broken fixes on multi-file changes.** In 9% of runs, `reviewer_agent` approved and "merged" a fix that fails the planted test, concentrated where the fix spans >1 file. The reviewer runs tests but trusts a passing compile over a failing assertion. Harden the reviewer's stop condition ("all tests pass" must be checked, not assumed) or swap in a stronger reviewer model — the A/B run shows that drops the nod rate to ~1%.

## Step 6 — Report

`GET /api/runs/run_abc/report` returns the `Report` (summary, findings, stats). Dashboard renders it; demo narrative walks from "one run opened a clean-looking PR" to "100 runs found the reviewer nods 9% of the time — and here's exactly when."

## Why this demo lands

One anecdote vs a distribution. We show a loop whose single run looks perfect — a PR gets opened, tests "pass" — then show Loopy proving, with a ground-truth answer key, that the reviewer rubber-stamps broken fixes 9% of the time. That's the paper's hardest, most-skipped move (verification) caught with data — in minutes.
