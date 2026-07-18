"""Score a video variant into a Score Object — Person B (scoring engine).

Produces the exact shape defined in CONTRACTS.md §3:
  { variant_id, networks{5 series}, metrics{peak,sustained,retention,overall},
    duration_sec, sample_rate_hz }

Runs inside the Modal A100 container.
"""

import numpy as np

# Exact keys/order from CONTRACTS.md §2 — do not rename.
NETWORKS = ["visual", "auditory", "language", "motion", "default_mode"]


def _normalize01(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = float(np.nanmin(x)), float(np.nanmax(x))
    if hi - lo < 1e-9:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def reduce_to_networks(preds: np.ndarray) -> dict:
    """PHASE 1 PLACEHOLDER reduction: partition the ~20k cortical vertices into
    5 contiguous groups and take mean absolute activation per timestep,
    normalized to [0,1].

    PHASE 2 replaces this with the real ICA-based 5-network mapping
    (visual/auditory/language/motion/default-mode) described in
    HOW_TRIBE_V2_WORKS.md. The output SHAPE here is already contract-final;
    only the vertex→network assignment becomes principled.
    """
    _, n_vertices = preds.shape
    bounds = np.linspace(0, n_vertices, len(NETWORKS) + 1, dtype=int)
    series = {}
    for i, name in enumerate(NETWORKS):
        chunk = preds[:, bounds[i] : bounds[i + 1]]
        raw = np.abs(chunk).mean(axis=1)
        series[name] = [round(float(v), 4) for v in _normalize01(raw)]
    return series


def compute_metrics(series: dict) -> dict:
    """Engagement metrics per CONTRACTS.md §3, all floats in [0,1]."""
    arrs = np.array([series[n] for n in NETWORKS])  # (5, T)
    engagement = arrs.mean(axis=0)  # overall engagement over time
    n = engagement.shape[0]
    third = max(1, n // 3)

    peak = float(engagement.max())
    sustained = float(engagement.mean())
    retention = float(engagement[-third:].mean())  # held through the CTA window
    overall = 0.4 * retention + 0.4 * sustained + 0.2 * peak

    clip = lambda v: round(min(1.0, max(0.0, float(v))), 4)
    return {
        "peak": clip(peak),
        "sustained": clip(sustained),
        "retention": clip(retention),
        "overall": clip(overall),
    }


def build_score_object(variant_id: str, preds: np.ndarray) -> dict:
    series = reduce_to_networks(preds)
    metrics = compute_metrics(series)
    n_timesteps = len(next(iter(series.values())))
    return {
        "variant_id": variant_id,
        "networks": series,
        "metrics": metrics,
        "duration_sec": float(n_timesteps),  # 1 Hz → length == duration_sec
        "sample_rate_hz": 1,
    }


def score(video_path: str, cache_dir: str, variant_id: str = "var_000000000000", model=None) -> dict:
    """Public entrypoint: video file → Score Object. Reuses a loaded model if
    given (so batch/precompute doesn't reload weights per clip)."""
    if model is None:
        from scoring.tribe_model import load_tribe

        model = load_tribe(cache_dir)
    events = model.get_events_dataframe(video_path=video_path)
    preds, _segments = model.predict(events=events)
    return build_score_object(variant_id, preds)
