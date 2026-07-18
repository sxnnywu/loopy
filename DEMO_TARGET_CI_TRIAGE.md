# Demo Target: CI/CD Failure-Triage Loop (replaces FinFlow)

**Decision (2026-07-17, Jay):** the loop Loopy QAs in the demo is a **CI/CD
failure-triage loop**, not FinFlow. FinFlow (3 agents, near-linear) undersold the
analysis; the triage loop is a real *graph* with routing, specialists, and an
adversarial evaluator — and it mirrors, agent-for-agent, the annotated "first
loop" in the **Loop Engineering IEEE working note (§XII, p.9)**. That citation is
part of the pitch. (FinFlow code/seed stays in the repo as a second registered
spec — proof Loopy is target-agnostic.)

## The loop under test

```
ci_monitor ──finding──► triage_agent ──classified──► test_fixer ──┐
   ▲                        ▲  ▲                     infra_fixer ─┼──► evaluator
   │                        │  └──misrouted bounce── dep_fixer  ──┘      │ │
   │                        └───────────────────────────────REJECT───────┘ │
   └────────────────────────PASS: merged / human inbox─────────────────────┘
```

Six agents (spec: `backend/examples/ci_triage_spec.json`):
- **ci_monitor** — discovery: reads failed CI runs/issues/commits (the paper's *skill*)
- **triage_agent** — classifies each finding (flaky_test | infra | regression | dependency) and routes it
- **test_fixer / infra_fixer / dep_fixer** — specialist *generators*, each fixing in an isolated worktree (paper: *handoff*)
- **evaluator** — adversarial reviewer, "assume broken until proven otherwise" (paper: *verification*, the generator/evaluator split)
- `state_update` events = the paper's *persistence* (state file); each loop tick = *scheduling*

## Why this wins with judges

1. **Citable**: "This loop is the canonical first-loop from the Loop Engineering
   paper. The paper also catalogs five ways loops go wrong — and says nobody
   catches them until they've compounded. Loopy catches them empirically."
2. **Familiar pain**: every technical judge has debugged red CI at 2am.
3. **Graph, not line**: 12 distinct handoffs get fragility-ranked (FinFlow had 4).
4. **The paper's failure taxonomy → Loopy findings** (the demo's thesis):

| Paper failure/cost | How it manifests in the loop | Loopy stat that catches it |
|---|---|---|
| Tangled/misrouting (handoff quality) | triage classifies a flaky test as "infra"; infra bounces it back; triage re-classifies it "infra" again (missing context) — forever | per-handoff fragility: `infra_fixer→triage_agent` at 100%, `triage_agent→infra_fixer` elevated |
| Nodding-loop's mirror: reject ping-pong | dep_fixer resubmits the same fix; evaluator REJECTs for the same uncovered edge case — forever | stall detection + `evaluator→dep_fixer` fragility |
| Token blowout (silent cost #4) | stalled runs burn 4–6× tokens of clean runs | cost p95 ≫ mean |
| Non-determinism | identical incident sometimes routes right, sometimes wrong | cross-seed divergence rate |
| Verification debt | would-be premature PASSes | (stretch) plant a low-rate bad-merge cluster |

## Demo numbers (current fake-data run, 80 sandboxes, reproducible seed)

```
Completion 62.5% · Stall 32.5% · Divergence 70.8% · cost p95 4,052 vs mean 1,866 tok
Fragility top-3: infra_fixer→triage 100% · evaluator→dep_fixer 62.5% · triage→infra_fixer 56.5%
```

The narrative line: *"One manual run of this triage loop looked fine. 80 runs
showed a third of them never terminate — and the fragility ranking points at the
exact two edges responsible: triage's misrouting bounce and the dep-fix reject
cycle. The paper predicted these failure classes; Loopy measured them."*

## Impact on other workstreams (small)
- **A**: real loop runner executes `ci_triage_spec.json` instead of FinFlow — same
  LoopSpec contract, zero platform changes. Fake tool calls (read_ci_runs etc.)
  can be stubbed; agents are Gemini as before.
- **B**: nothing changes (same Event shape).
- **C**: done — pipelines already produce the numbers above
  (`python -m scripts.seed_ci_triage_run && python -m scripts.run_analysis_demo`).
- **D**: fleet grid unchanged; report view gets the table above as its story;
  demo script anchors on the paper (bring the PDF page 9 as a slide).
