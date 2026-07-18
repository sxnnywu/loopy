# backend/scripts/seed_ci_triage_run.py
#
# Fake-data generator for the CI/CD TRIAGE demo loop (replaces FinFlow as the
# primary demo target — see examples/ci_triage_spec.json and the Loop
# Engineering paper §XII p.9 / §VI "Five Ways a Loop Goes Wrong").
#
# Each sandbox = one CI incident flowing through:
#   ci_monitor -> triage -> specialist(worktree) -> evaluator -> merged | bounce
#
# PLANTED failure clusters (what Loopy should *discover*, mapped to the paper):
#   1. MISROUTING STALL — flaky-test incidents get classified "infra"; the
#      infra specialist bounces them back; triage re-classifies "infra" again
#      (it lacks the specialist's evidence in context) -> ping-pong -> stall.
#      Shows up as: high fragility on triage_agent -> infra_fixer.
#   2. NODDING-LOOP PING-PONG — dependency fixes bounce evaluator <-> dep_fixer:
#      evaluator REJECTs the same fix repeatedly because the specialist never
#      addresses the uncovered edge case -> stall. ("verification is the move
#      the loop can't skip" — and here it's verification that catches it.)
#   3. TOKEN BLOWOUT TAIL — stalled runs burn 4-6x the tokens of clean runs
#      (the paper's 4th silent cost). Shows up in the p95 cost stat.
#   4. DIVERGENCE — identical incidents sometimes route correctly and
#      sometimes not (probabilistic triage) -> identical-seed disagreement.
#
# Usage:  python -m scripts.seed_ci_triage_run     (run from backend/)
# Env:    MONGODB_URI (default mongodb://localhost:27017), LOOPY_DB (default loopy)

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

RUN_ID = "run_demo_ci_triage"
SPEC_ID = "spec_ci_triage_01"
N_SANDBOXES = 80
rng = random.Random(1337)  # fixed seed -> reproducible demo

FAILURE_KINDS = ["flaky_test", "flaky_test", "infra", "regression", "dependency", "dependency"]
SPECIALIST_FOR = {
    "flaky_test": "test_fixer",
    "infra": "infra_fixer",
    "regression": "dep_fixer",
    "dependency": "dep_fixer",
}
INCIDENTS = [
    "auth test flaky on retry", "null deref in payments", "runner out of disk",
    "lockfile conflict on urllib3", "timeout in checkout e2e", "stale docker cache",
    "breaking minor bump of sdk", "race in websocket test",
]


def _now():
    return datetime.now(timezone.utc)


def _event(sb, seq, etype, ts, frm=None, to=None, payload=None, tokens=0):
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "run_id": RUN_ID, "sandbox_id": sb, "seq": seq, "type": etype,
        "ts": ts, "from_agent": frm, "to_agent": to,
        "payload": payload or {}, "tokens": tokens,
    }


def build_sandbox(i: int):
    sb = f"sb_{i:03d}"
    kind = rng.choice(FAILURE_KINDS)
    incident = rng.choice(INCIDENTS)
    # ANSWER KEY = ground truth Loopy can score against (idea adopted from the
    # team's EXAMPLE_LOOP_SPEC.md §7). We know the real failure kind, which
    # test must pass, and which file the fix must not touch.
    seed_input = {
        "failure_kind": kind, "incident": incident,
        "answer_key": {
            "true_kind": kind,
            "must_pass": ["test_" + incident.split()[0]],
            "must_not_touch": ["billing.py"],
        },
    }

    # outcome logic — the planted clusters
    roll = rng.random()
    if kind == "flaky_test" and roll < 0.55:
        outcome, mode = "stall_detected", "misroute"        # cluster 1
    elif kind == "dependency" and roll < 0.45:
        outcome, mode = "stall_detected", "reject_pingpong"  # cluster 2
    elif kind == "regression" and roll < 0.40:
        outcome, mode = "goal_reached", "nod"                # cluster 3: nodding evaluator
    elif roll < 0.06:
        outcome, mode = "error", "error"
    else:
        outcome, mode = "goal_reached", "clean"

    t0 = _now() - timedelta(minutes=rng.randint(2, 45))
    events, seq, ts = [], 0, t0

    def step(etype, frm=None, to=None, payload=None, tokens=0):
        nonlocal seq, ts
        ts += timedelta(seconds=rng.randint(1, 5))
        seq += 1
        events.append(_event(sb, seq, etype, ts, frm, to, payload, tokens))

    # ---- discovery: ci_monitor finds the incident and hands to triage ----
    step("loop_iteration", payload={"iteration": 1})
    step("tool_call", "ci_monitor", payload={"tool": "read_ci_runs"}, tokens=0)
    step("tool_result", "ci_monitor", payload={"failed_runs": 1})
    step("agent_message", "ci_monitor", "triage_agent",
         {"content": f"Finding: {incident} ({kind})"}, tokens=rng.randint(180, 320))
    step("state_update", "ci_monitor", payload={"state_file": "triage.md", "row": incident})

    specialist = SPECIALIST_FOR[kind]

    if mode == "clean":
        iterations = rng.randint(3, 8)
        step("agent_message", "triage_agent", specialist,
             {"content": f"Classified {kind}; routing with evidence", "classified": kind},
             tokens=rng.randint(200, 300))
        step("tool_call", specialist, payload={"tool": "worktree", "action": "open"})
        step("agent_message", specialist, "evaluator",
             {"content": "Fix drafted in worktree, tests added"}, tokens=rng.randint(250, 400))
        step("tool_call", "evaluator", payload={"tool": "run_tests"})
        step("tool_result", "evaluator", payload={"must_pass_ok": True})   # oracle: fix is good
        if rng.random() < 0.25:  # one honest reject-then-fix round
            step("agent_message", "evaluator", specialist,
                 {"content": "REJECT: edge case uncovered, add test"}, tokens=rng.randint(200, 300))
            step("agent_message", specialist, "evaluator",
                 {"content": "Edge case covered, re-submitting"}, tokens=rng.randint(200, 300))
        step("agent_message", "evaluator", "ci_monitor",
             {"content": "PASS — merged, ticket updated", "verdict": "pass"},
             tokens=rng.randint(150, 250))
        step("state_update", "evaluator", payload={"state_file": "triage.md", "status": "fixed"})
        step("termination", payload={"reason": "goal_reached"})

    elif mode == "nod":
        # cluster 3: the NODDING EVALUATOR — oracle says the fix is broken
        # (must_pass_ok False), evaluator passes it anyway. Run looks like a
        # clean goal_reached; only the answer key exposes it.
        iterations = rng.randint(3, 7)
        step("agent_message", "triage_agent", specialist,
             {"content": f"Classified {kind}; routing", "classified": kind},
             tokens=rng.randint(200, 300))
        step("tool_call", specialist, payload={"tool": "worktree", "action": "open"})
        step("agent_message", specialist, "evaluator",
             {"content": "Fix drafted (multi-file change)",
              "files_touched": ["api.py", "handlers.py", "billing.py"]},
             tokens=rng.randint(300, 450))
        step("tool_call", "evaluator", payload={"tool": "run_tests"})
        step("tool_result", "evaluator", payload={"must_pass_ok": False})  # oracle: broken
        step("agent_message", "evaluator", "ci_monitor",
             {"content": "PASS — merged, ticket updated", "verdict": "pass"},  # nod
             tokens=rng.randint(150, 250))
        step("state_update", "evaluator", payload={"state_file": "triage.md", "status": "fixed"})
        step("termination", payload={"reason": "goal_reached"})

    elif mode == "misroute":
        # cluster 1: triage keeps classifying the flaky test as infra
        iterations = rng.randint(18, 30)
        for k in range(rng.randint(4, 6)):
            step("loop_iteration", payload={"iteration": k + 2})
            step("agent_message", "triage_agent", "infra_fixer",
                 {"content": f"Classified infra (runner suspected): {incident}",
                  "classified": "infra"},
                 tokens=rng.randint(220, 320))
            step("agent_message", "infra_fixer", "triage_agent",
                 {"content": "Not infra — runners healthy. Bouncing back."},
                 tokens=rng.randint(220, 320))
        step("termination", payload={"reason": "stall_detected", "pattern": "misroute_pingpong"})

    elif mode == "reject_pingpong":
        # cluster 2: evaluator honestly rejects, specialist never addresses it
        iterations = rng.randint(18, 30)
        step("agent_message", "triage_agent", "dep_fixer",
             {"content": f"Classified dependency: {incident}", "classified": "dependency"},
             tokens=rng.randint(200, 300))
        for k in range(rng.randint(4, 6)):
            step("loop_iteration", payload={"iteration": k + 2})
            step("agent_message", "dep_fixer", "evaluator",
                 {"content": "Pinned version, resubmitting same fix"}, tokens=rng.randint(240, 360))
            step("agent_message", "evaluator", "dep_fixer",
                 {"content": "REJECT: transitive dep still broken, fix does not address it"},
                 tokens=rng.randint(240, 360))
        step("termination", payload={"reason": "stall_detected", "pattern": "reject_pingpong"})

    else:  # error
        iterations = rng.randint(2, 5)
        step("agent_message", "triage_agent", specialist,
             {"content": f"Classified {kind}", "classified": kind}, tokens=rng.randint(200, 300))
        step("error", specialist, payload={"error": "LLM call failed mid-fix"})
        step("termination", payload={"reason": "error"})

    total_tokens = sum(e["tokens"] for e in events)
    sandbox_run = {
        "sandbox_id": sb, "run_id": RUN_ID,
        "state": {"goal_reached": "completed", "stall_detected": "stalled",
                  "error": "failed"}[outcome],
        "seed_input": seed_input,
        "iterations": iterations,
        "termination_reason": outcome,
        "total_tokens": total_tokens,
        "started_at": t0, "ended_at": ts,
    }
    return sandbox_run, events


def main():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db = MongoClient(uri)[os.environ.get("LOOPY_DB", "loopy")]

    db.sandbox_runs.delete_many({"run_id": RUN_ID})
    db.events.delete_many({"run_id": RUN_ID})
    db.run_batches.delete_many({"run_id": RUN_ID})

    all_runs, all_events = [], []
    for i in range(N_SANDBOXES):
        sr, evs = build_sandbox(i)
        all_runs.append(sr)
        all_events.extend(evs)

    db.run_batches.insert_one({
        "run_id": RUN_ID, "spec_id": SPEC_ID, "n_sandboxes": N_SANDBOXES,
        "seed_strategy": "varied", "state": "completed", "created_at": _now(),
    })
    db.sandbox_runs.insert_many(all_runs)
    db.events.insert_many(all_events)

    db.events.create_index([("run_id", 1), ("sandbox_id", 1), ("seq", 1)], unique=True)
    db.events.create_index([("run_id", 1), ("type", 1)])
    db.sandbox_runs.create_index([("run_id", 1), ("sandbox_id", 1)], unique=True)

    print(f"Seeded run_id={RUN_ID}: {len(all_runs)} sandboxes, {len(all_events)} events")


if __name__ == "__main__":
    main()
