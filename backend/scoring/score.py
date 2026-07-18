"""score(media_key) -> ScoreObject dict. Public entrypoint. Owner: B (Jay).

Pipeline: media_key -> local file -> TRIBE predict (vertices/sec)
  -> networks.reduce_to_networks -> metrics (engagement + composite)
  -> regions.region_timeline -> brain_frames -> ScoreObject (CONTRACTS.md §3).
"""

from pathlib import Path

from backend.scoring import metrics
from backend.scoring.networks import reduce_to_networks
from backend.scoring.regions import region_timeline
from backend.scoring.tribe_model import CACHE_DIR, load_model

# Where C mounts variant media on the GPU worker (media_key = "media/<variant_id>.mp4").
MEDIA_ROOT = f"{CACHE_DIR}/media"

# Process-wide model cache so batch/precompute doesn't reload weights per clip.
_MODEL = None


def _resolve_media(media_key: str) -> str:
    """media_key -> local file path. Accepts an already-absolute/existing path,
    else resolves under MEDIA_ROOT (strips a leading 'media/')."""
    if Path(media_key).is_file():
        return media_key
    rel = media_key[len("media/") :] if media_key.startswith("media/") else media_key
    return str(Path(MEDIA_ROOT) / rel)


def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = load_model(CACHE_DIR)
    return _MODEL


def score(media_key: str) -> dict:
    variant_id = Path(media_key).stem  # "media/var_x.mp4" -> "var_x"
    video_path = _resolve_media(media_key)

    model = _get_model()
    events = model.get_events_dataframe(video_path=video_path)
    preds, _segments = model.predict(events=events)  # (n_timesteps, ~20k vertices)

    networks = reduce_to_networks(preds)
    engagement = metrics.compute_engagement(networks)
    m = metrics.compute_metrics(engagement)
    timeline = region_timeline(preds)
    n_timesteps = len(engagement)

    return {
        "variant_id": variant_id,
        "networks": networks,
        "engagement": engagement,
        "metrics": m,
        # PHASE 2: brain_render.render_frames(preds, variant_id) -> per-second PNGs.
        "brain_frames": [],
        "region_timeline": timeline,
        "duration_sec": float(n_timesteps),  # 1 Hz -> length == duration_sec
        "sample_rate_hz": 1,
    }
