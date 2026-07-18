"""Canned ScoreObject matching CONTRACTS.md — for A (Kimi) & C (Seb) to build against."""
import math

_W = {"default_mode": 0.30, "visual": 0.25, "language": 0.20, "auditory": 0.15, "motion": 0.10}
_REGION = {"visual": "fusiform_face_area", "auditory": "primary_auditory",
           "language": "broca_area", "motion": "motion_mt", "default_mode": "prefrontal_dmn"}

def mock_score(variant_id: str = "var_demo0001", n: int = 18) -> dict:
    def curve(phase, amp):
        return [round(max(0.0, min(1.0, amp * (0.55 + 0.45 * math.sin(t / 2.0 + phase)))), 3)
                for t in range(n)]
    networks = {"visual": curve(0.0, 0.85), "auditory": curve(0.6, 0.6),
                "language": curve(1.1, 0.7), "motion": curve(1.7, 0.5),
                "default_mode": curve(0.3, 0.9)}
    eng = [round(sum(_W[k] * networks[k][t] for k in _W), 3) for t in range(n)]
    third = max(1, n // 3)
    first = sum(eng[:third]) / third; last = sum(eng[-third:]) / third
    metrics = {"peak": round(max(eng), 3), "sustained": round(sum(eng) / n, 3),
               "retention": round(min(1.0, last / first) if first else 0.0, 3)}
    metrics["overall"] = round(0.5 * metrics["sustained"] + 0.3 * metrics["retention"] + 0.2 * metrics["peak"], 3)
    rt = [{"t": t, "top_network": max(networks, key=lambda k: networks[k][t]),
           "top_region": _REGION[max(networks, key=lambda k: networks[k][t])],
           "activation": round(max(networks[k][t] for k in networks), 3)} for t in range(n)]
    return {"variant_id": variant_id, "networks": networks, "engagement": eng, "metrics": metrics,
            "brain_frames": [f"media/{variant_id}_brain_{t:03d}.png" for t in range(n)],
            "region_timeline": rt, "duration_sec": float(n), "sample_rate_hz": 1}
