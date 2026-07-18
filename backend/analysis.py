"""Presentation analysis for GET /tests/{id}. Encodes the display semantics of
CONTRACTS §3a / SCORING_SCIENCE.md §6-§7 server-side, so the frontend just renders
what it's told instead of re-deriving science. Owner: C (Seb).

- **profile** (1 variant): mode only. No winner, grade, or ranking — a single clip is a
  profile, not a verdict (SCORING_SCIENCE §6).
- **comparison** (2+): winner + per-network signal deltas ("which brain system separated
  them") + ranking.

⚠️ SCORING_SCIENCE §7 (added 2026-07-18) says a comparison ranks on the *real measured
signals* — the 5 brain networks (family A, IN the Score Object, surfaced here) PLUS the
observable production signals (family B: facial expression, hand gestures, speech rate,
motion, clarity — measured by B's analyze_objective but NOT in the Score Object yet), and
that peak/sustained/retention/overall are NOT the ranking basis. Until B adds family B to
the Score Object (a §3 contract change) and a signal-based winner is defined, `ranking`
still orders by the test's `objective` metric (interim), and `signal_advantage` is a
placeholder for family B. `network_advantage` (family A) is real and available today.
"""
from statistics import mean

from backend.models.schemas import NETWORKS


def _net_mean(score: dict, net: str) -> float:
    arr = score.get("networks", {}).get(net) or [0.0]
    return mean(arr)


def build_analysis(test: dict, variants: list, scores: list) -> dict:
    if len(variants) <= 1:
        return {"mode": "profile"}  # §3a: profile only — no winner/grade/ranking

    objective = test.get("objective", "retention")
    analysis = {"mode": "comparison", "objective": objective}

    by_vid = {s["variant_id"]: s for s in scores}
    scored = [v for v in variants if v["id"] in by_vid]
    if len(scored) < 2:
        return analysis  # not enough scored variants yet (status pending/scoring)

    ranking = sorted(
        ({"variant_id": v["id"], "label": v["label"],
          "score": round(by_vid[v["id"]]["metrics"][objective], 4)} for v in scored),
        key=lambda r: r["score"], reverse=True,
    )
    winner, runner_up = by_vid[ranking[0]["variant_id"]], by_vid[ranking[1]["variant_id"]]
    # Family A (SCORING_SCIENCE §7): winner's mean activation minus runner-up's, per network.
    network_advantage = {
        net: round(_net_mean(winner, net) - _net_mean(runner_up, net), 4) for net in NETWORKS
    }
    analysis.update({
        "ranking": ranking,
        "network_advantage": network_advantage,
        "decisive_network": max(network_advantage, key=network_advantage.get),
        "signal_advantage": None,  # family B placeholder — awaits B adding signals to §3
    })
    return analysis
