# backend/scripts/run_analysis_demo.py
#
# End-to-end smoke test of Person C's deterministic analysis, standalone.
# Runs every pipeline over whatever is in Mongo for the demo run and prints
# the numbers a Report would carry. No FastAPI, no other workstream needed.
#
# Usage:  python -m scripts.run_analysis_demo     (run from backend/, after seeding)

from __future__ import annotations

import json
import os
import sys

from pymongo import MongoClient

from app.services.analysis import pipelines, tier2

# pick the run: CLI arg > env > CI-triage demo default
RUN_ID = (sys.argv[1] if len(sys.argv) > 1
          else os.environ.get("LOOPY_RUN_ID", "run_demo_ci_triage"))


def main():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    db = MongoClient(uri)[os.environ.get("LOOPY_DB", "loopy")]

    stats = pipelines.compute_stats(db, RUN_ID)

    print("=" * 64)
    print(f"  LOOPY — deterministic QA stats for {RUN_ID}")
    print("=" * 64)
    c = stats["completion"]
    print(f"Completion rate : {c['completion_rate']*100:.1f}%  "
          f"({c['goal_reached']}/{c['total']} reached goal)")
    s = stats["stall"]
    print(f"Stall rate      : {s['stall_rate']*100:.1f}%  ({s['stalled']}/{s['total']} stalled)")
    print(f"Outcomes        : {stats['outcomes']}")
    it = stats["iterations"]
    print(f"Iterations      : median {it['median_iterations']}, {it['n']} runs")
    co = stats["cost"]
    print(f"Cost / run      : mean {co['mean_tokens']:,} tok, p95 {co['p95_tokens']:,} tok")
    dv = stats["divergence"]
    print(f"Divergence      : {dv['divergence_rate']*100:.1f}%  "
          f"({dv['diverged_groups']}/{dv['seed_groups']} seed-groups disagreed)")
    print("\nPer-handoff fragility (worst first):")
    for h in stats["per_handoff"]:
        print(f"  {h['handoff']:<32} fragility {h['fragility']*100:5.1f}%  "
              f"({h['sandboxes_ended_bad']}/{h['sandboxes_seen']} sandboxes ended bad)")

    t2 = tier2.compute_tier2(db, RUN_ID)
    nr, ta = t2["nod"], t2["triage"]
    print("\nTier-2 — answer-key (ground truth) checks:")
    print(f"Nodding evaluator : {nr['nod_rate']*100:.1f}% of approvals passed a BROKEN fix "
          f"({nr['nodded']}/{nr['approvals']})  evidence: {nr['evidence_sandbox_ids'][:5]}")
    print(f"Triage accuracy   : {ta['accuracy']*100:.1f}% vs ground truth "
          f"(misclassified: {ta['misclassified']})")
    print("=" * 64)
    print("\nFull stats dict (this is what report_builder consumes):")
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
