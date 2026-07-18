# backend/app/services/analysis/tier2.py
#
# Person C — Tier-2 checks: correctness vs the ANSWER KEY (ground truth planted
# in seed_input.answer_key). Tier-1 (pipelines.py) needs no config and works on
# any loop; Tier-2 is what proves a run that LOOKED successful was actually
# wrong. These are the demo's money findings.
#
# Checks:
#   1. nod_rate         — evaluator PASSed a fix the oracle says is broken
#                         ("approved-but-broken"; the paper's Nodding Loop)
#   2. triage_accuracy  — triage's classification vs the true failure kind
#                         (proves the misroute cluster is a triage defect,
#                          not an infra_fixer defect)
#
# Both scan events per sandbox in seq order. Fine at MVP fleet sizes; move to
# aggregation pipelines if 1,000x makes it slow.

from __future__ import annotations

from typing import Any


def nod_rate(db, run_id: str) -> dict[str, Any]:
    """Of all runs the evaluator passed, how many did the oracle say were broken?"""
    approvals, nods, nod_ids = 0, 0, []
    for sr in db.sandbox_runs.find(
        {"run_id": run_id, "termination_reason": "goal_reached"}, {"sandbox_id": 1}
    ):
        sb = sr["sandbox_id"]
        evs = list(db.events.find({"run_id": run_id, "sandbox_id": sb}).sort("seq", 1))
        passed = any(
            e["type"] == "agent_message" and e.get("payload", {}).get("verdict") == "pass"
            for e in evs
        )
        if not passed:
            continue
        approvals += 1
        oracle_results = [
            e["payload"]["must_pass_ok"]
            for e in evs
            if e["type"] == "tool_result" and "must_pass_ok" in e.get("payload", {})
        ]
        # the LAST oracle check before the pass is the one that counts
        if oracle_results and oracle_results[-1] is False:
            nods += 1
            nod_ids.append(sb)
    return {
        "nod_rate": round(nods / approvals, 4) if approvals else 0.0,
        "nodded": nods,
        "approvals": approvals,
        "evidence_sandbox_ids": nod_ids,
    }


def triage_accuracy(db, run_id: str) -> dict[str, Any]:
    """Triage's first classification vs answer_key.true_kind, plus the confusion pairs."""
    total, correct = 0, 0
    confusion: dict[str, int] = {}
    for sr in db.sandbox_runs.find({"run_id": run_id}, {"sandbox_id": 1, "seed_input": 1}):
        truth = ((sr.get("seed_input") or {}).get("answer_key") or {}).get("true_kind")
        if not truth:
            continue
        ev = db.events.find_one(
            {"run_id": run_id, "sandbox_id": sr["sandbox_id"],
             "from_agent": "triage_agent", "payload.classified": {"$exists": True}},
            sort=[("seq", 1)],
        )
        if not ev:
            continue
        classified = ev["payload"]["classified"]
        total += 1
        if classified == truth:
            correct += 1
        else:
            key = f"{truth} -> {classified}"
            confusion[key] = confusion.get(key, 0) + 1
    return {
        "accuracy": round(correct / total, 4) if total else 0.0,
        "n": total,
        "misclassified": confusion,
    }


def compute_tier2(db, run_id: str) -> dict[str, Any]:
    """One call for report_builder, same shape-idea as pipelines.compute_stats."""
    return {
        "nod": nod_rate(db, run_id),
        "triage": triage_accuracy(db, run_id),
    }
