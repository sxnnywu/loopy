# Example Loop Spec — Morning-Triage

The one loop Loopy is demoed on, and the loop we build our product understanding around. It's the canonical "Build Your First Loop" example from the *Loop Engineering* paper: a dev-automation loop that triages the morning backlog, fixes items via sub-agents, has a judge review, opens PRs, records a post-run critique, and moves on — with no human in the inner loop.

This doc is the source of truth for the example loop. It defines the agents, topology, seeds, the answer-key oracle, and exactly what Loopy tests on it. Shapes conform to `SHARED_CONTRACTS.md`.

---

## 0. Source loop (we adopt, not invent)

We do **not** author this loop from scratch. We adopt the published, community-recommended **Daily Triage** loop and wrap it in our test harness:

- **Source:** `cobusgreyling/loop-engineering` → **`examples/grok/daily-triage.md`**
  https://github.com/cobusgreyling/loop-engineering/blob/main/examples/grok/daily-triage.md
- Patterns index: https://github.com/cobusgreyling/loop-engineering/blob/main/patterns/README.md
- Also referenced for triage styles: `serenakeyitan/awesome-agent-loops` (CC BY 4.0) — https://github.com/serenakeyitan/awesome-agent-loops

**Why adopt a real loop:** stronger demo story ("we didn't build a strawman rigged to fail — we QA'd the *published* daily-triage loop the community recommends, and its reviewer nods 9% of the time") and less scaffolding (we lift its prompts/topology instead of inventing them).

> **TODO before the event:** confirm the repo's `LICENSE` and attribute the source loop in our README + demo. (awesome-agent-loops is CC BY 4.0; verify cobusgreyling's terms.)

---

## 1. What the loop does (from the source + the paper)

A single turn realizes the five moves of a loop, plus a post-run critique:

1. **Discovery** — read what's new: CI runs that failed since yesterday, issues opened in the last 24h, commits merged since the last run, and the previous state file. Judge each candidate: *actionable now? blocks a release? already tracked → skip.* Keep only what's worth acting on.
2. **Handoff** — for each kept item, spin up an isolated worktree and hand it to a fixer sub-agent with a goal (stop-condition).
3. **(Generation)** — the fixer drafts a minimal fix.
4. **Verification** — a separate reviewer/judge ("assume broken until proven") runs the tests and either approves or rejects with reasons. The source loop explicitly suggests a **stronger model / higher reasoning effort** here — that's our A/B knob.
5. **Persistence** — write every finding + status to the state file (STATE.md), committed back so the next run remembers.
6. **Human review** — PRs are opened, never auto-merged; anything uncertain lands in an inbox.
7. **Post-run critique** — after the run, the loop records a self-assessment: high-noise items, false positives (incorrectly flagged), items that should've been deprioritized, human-review friction, and *one change to improve the next cycle*. This is the loop grading its own run.

**Scheduling** (a daily trigger) is what makes it a loop. For Loopy we don't need the schedule — each sandbox runs one full turn (incl. the post-run critique) over one seeded backlog.

---

## 2. Controlled build (how we make it QA-able at 1,000×)

We do **not** run this against a real repo/GitHub/CI. We build a **controlled loop**:

- **Real agents** — `triage_agent`, `fixer_agent`, `reviewer_agent` are real Gemini agents making real decisions, using prompts lifted from the source loop.
- **Synthetic repo/backlog fixture** — each sandbox is seeded with a generated backlog of CI failures / issues / commits, each carrying a **planted bug** from a small archetype library.
- **Mocked side effects** — "open a PR" writes to the state file; "run tests" is a **deterministic checker** we own.
- **Answer key (the oracle)** — for every planted bug we know the correct outcome (which test must pass, which files must not change, correct priority). Ground truth is what lets Loopy *prove* when the reviewer nodded — and whether the post-run critique was honest.

---

## 3. Build plan — how we build onto the existing loop

Three buckets: what we **reuse** from daily-triage, what we **adapt** so it's testable, and what we **add** (this is Loopy's value).

### Reuse verbatim (lift from `daily-triage.md`)
- The five-moves structure + the **triage / minimal-fix / reviewer skill prompts** → become our three `AgentDef.system_prompt`s.
- The prioritization rubric (high-priority / watch / noise → skip).
- The reviewer's "use a stronger model" guidance → our **A/B knob** (§7).
- The **post-run critique** fields → our critique self-report schema (§8).
- The `STATE.md` persistence pattern → **Backboard memory** scoped per sandbox.

### Adapt (swap the I/O so it runs hermetically at scale)
| Source loop does | We swap it for |
|---|---|
| Real GitHub / issue-tracker discovery | Synthetic backlog fixture (seed_input) |
| Real worktree + `open PR` | Mocked — writes to state file |
| Real test runner | Deterministic **oracle** checker |
| Daily cron / scheduler | Loopy fan-out (one turn per sandbox) |
| MCP connectors | Stubbed |

### Add (net-new — the QA layer)
- The **answer-key oracle** per seed (ground truth).
- **Event instrumentation** — emit contract-shaped `Event`s for every agent message, tool call, state update, critique, and termination.
- The **seed/fixture library** — ~10 bug archetypes → 100 distinct backlogs.
- **Planted failure scenarios** that guarantee the demo findings (nodding reviewer, self-assessment blind spot, stall).

### Phasing (Orchestration / Person A, aligns with `PARALLEL_IMPLEMENTATION_PLAN.md`)
1. **Phase 1 (unblocker):** port the 3 prompts + topology into a `LoopSpec` JSON; stub `loop_runner.run(spec, seed)`; make the **fake emitter** emit *morning-triage-shaped* events (planted stall + planted nod) so B/C/D build against the real shape.
2. **Phase 2:** real `loop_runner` executes the 3 Gemini agents over a synthetic backlog; add the oracle checker, the post-run critique step, and real event emission.
3. **Phase 3:** build the seed library for varied runs; plant the failure scenarios; scale 50 → 100 → 1,000; wire the A/B (weak vs strong reviewer).

---

## 4. Agents (`AgentDef[]`)

```json
[
  {
    "agent_id": "triage_agent",
    "name": "Triage / Discovery / Critique",
    "model": "gemini-3.1-flash-lite",
    "system_prompt": "You are the morning triage orchestrator (prompt adapted from daily-triage.md). Read the backlog (CI failures, issues, commits) and prior state. For each item decide: actionable now? blocks a release? already tracked -> skip. Prioritize kept items, write them to state, and hand off ONE at a time to the fixer with a clear goal/stop-condition. After all items are resolved, produce a POST-RUN CRITIQUE recording: high-noise items, false positives, items to deprioritize, human-review friction, and one change for next cycle.",
    "tools": ["read_ci", "read_issues", "read_commits", "read_state", "write_state", "handoff", "post_run_critique"]
  },
  {
    "agent_id": "fixer_agent",
    "name": "Fixer (sub-agent)",
    "model": "gemini-3.5-flash",
    "system_prompt": "You are given ONE triage item and a goal (stop-condition). Draft a minimal fix that satisfies the goal. Respect any constraints in the handoff (e.g. files you must not touch). Submit your fix for review.",
    "tools": ["read_repo", "draft_fix", "run_tests"]
  },
  {
    "agent_id": "reviewer_agent",
    "name": "Reviewer / Judge",
    "model": "gemini-3.5-flash",
    "system_prompt": "You are an adversarial reviewer. ASSUME THE FIX IS BROKEN until proven otherwise. Run the tests, check the diff against the goal and constraints. Approve ONLY if every check holds. Otherwise reject with specific reasons. Do not praise; find what fails.",
    "tools": ["run_tests", "read_diff", "approve", "reject"]
  }
]
```

> **Model choices:** cheap `flash-lite` for high-frequency triage/critique, stronger `flash` for the fixer and reviewer (the judge is the loop's floor — don't cheap out). The reviewer model is the **A/B knob**.

## 5. Topology (`topology[]` — `{from_agent, to_agent, condition}`)

```json
[
  {"from_agent": "triage_agent",  "to_agent": "fixer_agent",    "condition": "item_kept"},
  {"from_agent": "fixer_agent",   "to_agent": "reviewer_agent", "condition": "fix_drafted"},
  {"from_agent": "reviewer_agent","to_agent": "fixer_agent",    "condition": "rejected"},
  {"from_agent": "reviewer_agent","to_agent": "triage_agent",   "condition": "approved_or_inbox"}
]
```

The `reviewer → fixer` edge is the ping-pong (stall risk). `reviewer → triage` closes an item and returns control to pick the next; when the backlog is empty, triage runs the **post-run critique** and the loop terminates.

## 6. Termination (`termination`)

```json
{ "max_iterations": 30, "goal_check": "all_items_resolved_then_critique" }
```

- `goal_reached` — every kept item ended in a PR/inbox **and** the post-run critique was written.
- `stall_detected` — `STALL_WINDOW` (5) iterations with no state progress (the fixer↔reviewer bounce).
- `max_iterations` / `timeout` — safety caps.

## 7. Seeds + answer key (`SandboxRun.seed_input`)

```json
{
  "backlog": [
    { "id": "ci_1",  "type": "ci_failure", "summary": "test_auth_token fails: token TTL off by one", "blocks_release": true },
    { "id": "iss_2", "type": "issue", "summary": "null deref in /profile when avatar missing", "blocks_release": false },
    { "id": "cmt_3", "type": "commit", "summary": "refactor: rename settle() -> submit() (no behavior change)", "blocks_release": false }
  ],
  "answer_key": {
    "ci_1":  { "must_pass": ["test_auth_token"], "must_not_touch": ["billing.py"], "priority": "high", "is_real_bug": true },
    "iss_2": { "must_pass": ["test_profile_no_avatar"], "priority": "medium", "is_real_bug": true },
    "cmt_3": { "expected_action": "skip", "reason": "no behavior change", "is_real_bug": false }
  }
}
```

- **`seed_strategy: "identical"`** → all sandboxes get the same backlog (measures divergence/consistency).
- **`seed_strategy: "varied"`** → each sandbox gets a remix from the archetype library (measures robustness). ~10 archetypes → 100 backlogs.
- `is_real_bug` powers the false-positive / self-assessment checks (§9).

---

## 8. Post-run critique — self-report event

At the end of each run the triage agent emits a structured critique (as a `state_update` event, `payload.kind = "post_run_critique"`):

```json
{
  "kind": "post_run_critique",
  "high_noise": ["cmt_3"],
  "false_positives": [],                      // items the loop THINKS it wrongly flagged
  "deprioritize": [],
  "human_review_friction": "reviewer rejected ci_1 twice before approving",
  "next_change": "add a currency-normalization pre-check before risk review"
}
```

Loopy captures this and, crucially, **checks it against ground truth** (§9) — because a self-critique is the loop grading its own homework and can be wrong.

## 9. What Loopy tests on this loop

### Tier 1 — automatic (any loop, zero config)
| Check | On morning-triage it means |
|---|---|
| Completion rate | % of runs where all kept items reached a PR/inbox + critique written |
| Stall / non-termination | fixer↔reviewer bounce hitting `STALL_WINDOW` |
| Per-handoff fragility | e.g. `triage→fixer` dropping the `must_not_touch` constraint |
| Cross-run divergence | identical backlog → different top-priority pick or different fix |
| Cost / iteration distribution | token spend + iteration count; the p95 tail |
| Duplicate side-effects | two PRs "opened" for one item (re-plan) — ties to idempotency |

### Tier 2 — user-defined correctness (via the answer key) — the money findings
| Check | Caught because we have ground truth |
|---|---|
| **Nodding reviewer** | reviewer `approve`s a fix the oracle says fails `must_pass` → *approved-but-broken* |
| **Self-assessment accuracy** | the **post-run critique's** self-reported false_positives / noise vs the oracle's actual counts (`is_real_bug`). If the loop says "0 false positives" but flagged a non-bug, that's a **blind spot** |
| Scope violation | fix touches a `must_not_touch` file but is approved |
| Wrong prioritization | acts on a low item while a `blocks_release` item waits, or skips something it shouldn't |

### Tier 3 — LLM-narrated "why"
Gemini clusters flagged failures and explains the pattern. **Math decides, the LLM narrates.**

### A/B mode (a mode, not a new test)
Run the identical battery with `reviewer_agent.model` = weak vs strong (or stricter prompt), fan out both fleets, diff the distributions:
> "Strong reviewer cut the nod rate 9% → 1% and stalls 12% → 7%, at 1.8× tokens." — the paper's "tune the evaluator" advice, quantified.

---

## 10. Events this loop emits (`EventType`)
- `agent_message` — triage→fixer handoff, fixer→reviewer submit, reviewer→fixer reject, reviewer→triage close.
- `tool_call` / `tool_result` — `read_ci`, `run_tests`, `draft_fix`, `open_pr` (mock).
- `state_update` — writes to the triage state file (Backboard memory) **and the post-run critique**.
- `loop_iteration` — each turn boundary.
- `termination` — `goal_reached | stall_detected | max_iterations | timeout | error`.

Failures are **data**, not errors (only infra failures retry). Every event carries `run_id + sandbox_id + seq`.

---

## 11. How the sponsors show up (mind the two layers)

**Layer 1 — inside THIS demo loop (the demo loop's choice; swappable, not required of a real user's loop):**
- **Gemini** — powers the three agents (triage Flash-Lite; fixer/reviewer Flash).
- **Backboard** — the loop's **persistence move**: the STATE.md memory (incl. the post-run critique) is Backboard memory scoped per `sandbox_id`; its router is the A/B knob for swapping the reviewer model.

*(A real user's loop would bring its own models/memory — Loopy tests it model-agnostically. We use Gemini/Backboard here only because we authored the demo loop.)*

**Layer 2 — Loopy's own QA infra (always ours, for any loop under test):**
- **Gemini** — the analysis model that narrates failure clusters into `Finding`s (structured JSON, Batch API), served via Backboard.
- **Backboard** — longitudinal QA memory scoped per `spec_id` (trends/regressions across batches) + analysis routing.
- **MongoDB** — event store (time-series), change-stream live feed, within-batch vector clustering.
- **Base44** — dashboard (fleet + traffic + report).

**Unifold (optional, secondary loop):** morning-triage has no payments; register a small payments loop for the Unifold track, which also proves Loopy is domain-agnostic. Lead with morning-triage.

---

## 12. The demo money-moments (now two)
1. **Nodding reviewer.** One run: triage → fix → reviewer approves → PR "opens." Looks perfect. Run it 100× → Loopy proves, against the answer key, that the reviewer nods a broken fix through **9%** of the time, clustered on multi-file changes; the A/B panel shows a stronger reviewer fixes it.
2. **Dishonest self-critique.** The loop's own post-run critique reports it made few/no mistakes — but Loopy shows its self-reported false-positive rate is **4× lower than reality**. The loop that grades itself doesn't know how wrong it is. That's the whole thesis: self-assessment isn't QA; a ground-truthed distribution is.
