# backend/scripts/seed_fake_run.py
#
# Person C's OWN fake-data generator. It writes contract-shaped `sandbox_runs`
# and `events` straight into Mongo so C can build and test every pipeline
# WITHOUT waiting on Person A's real loop runner or Person B's collector.
#
# It plants the demo's "money moment": a cluster of sandboxes that STALL on
# multi-currency payments (risk_agent <-> settle_agent ping-pong), exactly the
# failure EXAMPLE_RUN_FLOW.md describes. When the real pipeline runs over this,
# stall_rate and per-handoff fragility should light up on that handoff.
#
# Usage:  python -m scripts.seed_fake_run            (run from backend/)
# Env:    MONGODB_URI (default mongodb://localhost:27017), LOOPY_DB (default loopy)

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

RUN_ID = "run_demo_finflow"
SPEC_ID = "spec_finflow_01"
N_SANDBOXES = 60
AGENTS = ["intake_agent", "risk_agent", "settle_agent"]
CURRENCIES = ["USD", "USD", "USD", "EUR", "GBP", "JPY"]  # USD common, others = edge cases
rng = random.Random(42)  # fixed seed → reproducible demo


def _now():
    return datetime.now(timezone.utc)


def _event(run_id, sb, seq, etype, ts, frm=None, to=None, payload=None, tokens=0):
    return {
        "event_id": f"evt_{uuid.uuid4().hex[:12]}",
        "run_id": run_id, "sandbox_id": sb, "seq": seq, "type": etype,
        "ts": ts, "from_agent": frm, "to_agent": to,
        "payload": payload or {}, "tokens": tokens,
    }


def build_sandbox(i: int):
    """Return (sandbox_run_doc, [event_docs]) for one fake FinFlow run."""
    sb = f"sb_{i:03d}"
    currency = rng.choice(CURRENCIES)
    amount = rng.choice([50, 120, 480, 999, 5000, 12000])
    seed_input = {"amount": amount, "currency": currency}
    is_multicurrency = currency != "USD"

    # Multi-currency payments stall ~65% of the time (the planted failure cluster).
    # USD payments almost always settle. A few random errors sprinkled in.
    roll = rng.random()
    if is_multicurrency and roll < 0.65:
        outcome = "stall_detected"
    elif roll < 0.05:
        outcome = "error"
    else:
        outcome = "goal_reached"

    t0 = _now() - timedelta(minutes=rng.randint(1, 30))
    events = []
    seq = 0
    ts = t0

    def step(etype, frm=None, to=None, payload=None, tokens=0):
        nonlocal seq, ts
        ts = ts + timedelta(seconds=rng.randint(1, 4))
        seq += 1
        events.append(_event(RUN_ID, sb, seq, etype, ts, frm, to, payload, tokens))

    # ---- the FinFlow loop: intake -> risk -> settle ----
    step("loop_iteration", payload={"iteration": 1})
    step("agent_message", "intake_agent", "risk_agent",
         {"content": f"Parsed payment {amount} {currency}"}, tokens=rng.randint(150, 300))
    step("state_update", "risk_agent", payload={"memory": "recorded intake"}, tokens=0)

    if outcome == "goal_reached":
        iterations = rng.randint(3, 8)
        step("agent_message", "risk_agent", "settle_agent",
             {"content": "Approved, within limits"}, tokens=rng.randint(180, 260))
        step("agent_message", "settle_agent", "intake_agent",
             {"content": "Settled"}, tokens=rng.randint(120, 200))
        step("termination", payload={"reason": "goal_reached"})

    elif outcome == "stall_detected":
        # risk <-> settle bounce the multi-currency payment back and forth
        iterations = rng.randint(20, 30)
        for k in range(rng.randint(5, 7)):
            step("loop_iteration", payload={"iteration": k + 2})
            step("agent_message", "risk_agent", "settle_agent",
                 {"content": f"Flagging: {currency} exceeds velocity limit, re-verify"},
                 tokens=rng.randint(200, 260))
            step("agent_message", "settle_agent", "risk_agent",
                 {"content": f"Cannot settle {currency} without risk sign-off, bouncing back"},
                 tokens=rng.randint(200, 260))
        step("termination", payload={"reason": "stall_detected"})

    else:  # error
        iterations = rng.randint(2, 6)
        step("error", "settle_agent", payload={"error": "Gemini call failed mid-loop"})
        step("termination", payload={"reason": "error"})

    total_tokens = sum(e["tokens"] for e in events)
    sandbox_run = {
        "sandbox_id": sb, "run_id": RUN_ID,
        "state": "completed" if outcome == "goal_reached" else
                 ("stalled" if outcome == "stall_detected" else "failed"),
        "seed_input": seed_input,
        "iterations": iterations,
        "termination_reason": outcome,
        "total_tokens": total_tokens,
        "started_at": t0, "ended_at": ts,
    }
    return sandbox_run, events


def main():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    dbname = os.environ.get("LOOPY_DB", "loopy")
    client = MongoClient(uri)
    db = client[dbname]

    # fresh slate for this demo run
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

    # indexes from SHARED_CONTRACTS.md §4 (index before scale-testing, not after)
    db.events.create_index([("run_id", 1), ("sandbox_id", 1), ("seq", 1)], unique=True)
    db.events.create_index([("run_id", 1), ("type", 1)])
    db.sandbox_runs.create_index([("run_id", 1), ("sandbox_id", 1)], unique=True)

    print(f"Seeded run_id={RUN_ID}: {len(all_runs)} sandboxes, {len(all_events)} events "
          f"into {dbname} @ {uri}")


if __name__ == "__main__":
    main()
