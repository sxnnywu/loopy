"""Reduce ~20k cortical vertices -> the 5 functional networks. Owner: B.

PHASE 1 reduction: partition the ~20k cortical vertices into 5 contiguous
groups and take mean absolute activation per timestep, normalized to [0,1].
The output SHAPE is contract-final (CONTRACTS.md §3); PHASE 2 swaps the
partition for the real ICA-based network mapping (HOW_TRIBE_V2_WORKS.md) —
only the vertex->network assignment becomes principled.
"""

import numpy as np

NETWORKS = ["visual", "auditory", "language", "motion", "default_mode"]


def _normalize01(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    lo, hi = float(np.nanmin(x)), float(np.nanmax(x))
    if hi - lo < 1e-9:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def reduce_to_networks(vertex_timeseries) -> dict:
    """(n_timesteps, ~20k vertices) -> {network: [float per second]}, normalized [0,1]."""
    preds = np.asarray(vertex_timeseries, dtype=float)
    _, n_vertices = preds.shape
    bounds = np.linspace(0, n_vertices, len(NETWORKS) + 1, dtype=int)
    series = {}
    for i, name in enumerate(NETWORKS):
        chunk = preds[:, bounds[i] : bounds[i + 1]]
        raw = np.abs(chunk).mean(axis=1)
        series[name] = [round(float(v), 4) for v in _normalize01(raw)]
    return series
