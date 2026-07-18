# backend/app/services/analysis/pipelines.py
#
# Person C — the DETERMINISTIC analysis core. "Math decides, the LLM only
# narrates." Every number in the QA report comes from here, computed with
# MongoDB aggregation pipelines over the `events` and `sandbox_runs`
# collections (shapes: SHARED_CONTRACTS.md §3–§4).
#
# These functions take a pymongo-style Database handle. They work unchanged
# whether that handle comes from B's Motor `core/database.py` (async: add
# `await` at call sites) or from a plain sync pymongo client in a dev script.
# The aggregation *pipeline dicts* are identical either way — that's the point.
#
# Contract facts these rely on:
#   - sandbox_runs.termination_reason ∈ goal_reached|max_iterations|stall_detected|timeout|error
#   - sandbox_runs.iterations, .total_tokens, .seed_input
#   - events.type == "agent_message" carries .from_agent / .to_agent (a "handoff")
#   - STALL_WINDOW / DEFAULT_MAX_ITERATIONS live in models.py

from __future__ import annotations

from typing import Any


# ── 1. Completion rate ────────────────────────────────────────────────────
def completion_rate(db, run_id: str) -> dict[str, Any]:
    """What fraction of sandboxes reached the goal? The headline number."""
    pipeline = [
        {"$match": {"run_id": run_id}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "goal_reached": {
                "$sum": {"$cond": [{"$eq": ["$termination_reason", "goal_reached"]}, 1, 0]}
            },
        }},
    ]
    row = next(iter(db.sandbox_runs.aggregate(pipeline)), None)
    if not row or row["total"] == 0:
        return {"completion_rate": 0.0, "total": 0, "goal_reached": 0}
    return {
        "completion_rate": round(row["goal_reached"] / row["total"], 4),
        "total": row["total"],
        "goal_reached": row["goal_reached"],
    }


# ── 2. Outcome breakdown (every termination reason) ───────────────────────
def outcome_breakdown(db, run_id: str) -> dict[str, int]:
    """Count of sandboxes by how they ended. Feeds stall_rate + the fleet pie."""
    pipeline = [
        {"$match": {"run_id": run_id}},
        {"$group": {"_id": "$termination_reason", "n": {"$sum": 1}}},
    ]
    out: dict[str, int] = {}
    for row in db.sandbox_runs.aggregate(pipeline):
        out[row["_id"] or "unknown"] = row["n"]
    return out


def stall_rate(db, run_id: str) -> dict[str, Any]:
    """Fraction of runs that stalled (ping-pong / no-progress). Loopy's signature finding."""
    breakdown = outcome_breakdown(db, run_id)
    total = sum(breakdown.values())
    stalled = breakdown.get("stall_detected", 0)
    return {
        "stall_rate": round(stalled / total, 4) if total else 0.0,
        "stalled": stalled,
        "total": total,
    }


# ── 3. Iteration histogram ────────────────────────────────────────────────
def iteration_histogram(db, run_id: str, bucket_size: int = 5) -> dict[str, Any]:
    """Distribution of loop lengths. Median + a long tail = the 'some runs never converge' story."""
    pipeline = [
        {"$match": {"run_id": run_id}},
        {"$bucketAuto": {"groupBy": "$iterations", "buckets": 8}},
    ]
    buckets = [
        {"min": b["_id"]["min"], "max": b["_id"]["max"], "count": b["count"]}
        for b in db.sandbox_runs.aggregate(pipeline)
    ]
    # median via a simple sorted pull (fleet sizes are small enough at MVP scale)
    vals = sorted(d["iterations"] for d in db.sandbox_runs.find({"run_id": run_id}, {"iterations": 1}))
    median = vals[len(vals) // 2] if vals else 0
    return {"buckets": buckets, "median_iterations": median, "n": len(vals)}


# ── 4. Token / cost distribution ──────────────────────────────────────────
def cost_stats(db, run_id: str) -> dict[str, Any]:
    """Token spend per run: mean + p95. The Green-AI / 'wasted tokens' finding lives here."""
    vals = sorted(d.get("total_tokens", 0) for d in
                  db.sandbox_runs.find({"run_id": run_id}, {"total_tokens": 1}))
    if not vals:
        return {"mean_tokens": 0, "p95_tokens": 0, "total_tokens": 0, "n": 0}
    n = len(vals)
    p95 = vals[min(n - 1, int(round(0.95 * (n - 1))))]
    return {
        "mean_tokens": round(sum(vals) / n),
        "p95_tokens": p95,
        "total_tokens": sum(vals),
        "n": n,
    }


# ── 5. Cross-seed divergence ──────────────────────────────────────────────
def divergence(db, run_id: str) -> dict[str, Any]:
    """
    Non-determinism metric. Group sandboxes that ran the SAME seed input; a
    group whose members disagree on outcome (termination_reason) is a
    divergence. High divergence = the loop isn't reproducible.

    Requires a way to know which runs share a seed. Convention (confirm w/ A):
    identical seed_input dicts == a control group. seed_strategy "identical"
    makes every run one big group; "varied" makes many small groups.
    """
    groups: dict[str, set[str]] = {}
    for d in db.sandbox_runs.find(
        {"run_id": run_id}, {"seed_input": 1, "termination_reason": 1}
    ):
        # stable signature for the seed dict
        seed = d.get("seed_input") or {}
        sig = repr(sorted(seed.items())) if isinstance(seed, dict) else repr(seed)
        groups.setdefault(sig, set()).add(d.get("termination_reason") or "unknown")

    multi = [outcomes for outcomes in groups.values()]  # every group
    comparable = [o for o in multi if True]  # all groups count toward the denominator
    diverged = sum(1 for o in comparable if len(o) > 1)
    denom = len([g for g in groups])  # number of distinct seed groups
    return {
        "divergence_rate": round(diverged / denom, 4) if denom else 0.0,
        "diverged_groups": diverged,
        "seed_groups": denom,
    }


# ── 6. Per-handoff fragility ──────────────────────────────────────────────
def per_handoff_stats(db, run_id: str) -> list[dict[str, Any]]:
    """
    For every agent->agent handoff (from_agent -> to_agent in agent_message
    events), how often does it appear in a sandbox that ended badly?
    Galileo calls inter-agent handoff fragility the #1 unsolved problem —
    this is the number that answers it.
    """
    # sandboxes that ended badly
    bad_states = {"stall_detected", "error", "timeout", "max_iterations"}
    bad_sandboxes = {
        d["sandbox_id"] for d in db.sandbox_runs.find(
            {"run_id": run_id, "termination_reason": {"$in": list(bad_states)}},
            {"sandbox_id": 1},
        )
    }

    pipeline = [
        {"$match": {"run_id": run_id, "type": "agent_message",
                    "from_agent": {"$ne": None}, "to_agent": {"$ne": None}}},
        {"$group": {
            "_id": {"from": "$from_agent", "to": "$to_agent"},
            "messages": {"$sum": 1},
            "sandboxes": {"$addToSet": "$sandbox_id"},
        }},
    ]
    out = []
    for row in db.events.aggregate(pipeline):
        sandboxes = set(row["sandboxes"])
        in_bad = len(sandboxes & bad_sandboxes)
        out.append({
            "handoff": f'{row["_id"]["from"]} -> {row["_id"]["to"]}',
            "messages": row["messages"],
            "sandboxes_seen": len(sandboxes),
            "sandboxes_ended_bad": in_bad,
            "fragility": round(in_bad / len(sandboxes), 4) if sandboxes else 0.0,
        })
    out.sort(key=lambda r: r["fragility"], reverse=True)
    return out


# ── Top-level: assemble every deterministic stat for a run ────────────────
def compute_stats(db, run_id: str) -> dict[str, Any]:
    """The one call report_builder uses. Pure math, no LLM."""
    return {
        "completion": completion_rate(db, run_id),
        "outcomes": outcome_breakdown(db, run_id),
        "stall": stall_rate(db, run_id),
        "iterations": iteration_histogram(db, run_id),
        "cost": cost_stats(db, run_id),
        "divergence": divergence(db, run_id),
        "per_handoff": per_handoff_stats(db, run_id),
    }
