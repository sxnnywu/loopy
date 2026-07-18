"""Load TRIBE v2 on the Modal A100 (weights cached on a Modal volume). Owner: B (Jay).

Overrides the gated `meta-llama/Llama-3.2-3B` text encoder with the ungated
mirror `unsloth/Llama-3.2-3B` (identical weights) so we never block on Meta's
license approval. Checkpoint + patched config are cached on the volume so cold
starts don't re-download ~20GB of encoders.
"""

from pathlib import Path

CACHE_DIR = "/cache"  # Modal volume mount (see modal_app.py)

TRIBE_REPO = "facebook/tribev2"
GATED_LLAMA = "meta-llama/Llama-3.2-3B"
UNGATED_LLAMA = "unsloth/Llama-3.2-3B"


def prepare_checkpoint(cache_dir: str = CACHE_DIR) -> Path:
    """Download the TRIBE checkpoint and patch its text encoder to the ungated
    Llama mirror. Returns a local dir with config.yaml + best.ckpt. Idempotent."""
    from huggingface_hub import snapshot_download

    snap = Path(
        snapshot_download(TRIBE_REPO, cache_dir=str(Path(cache_dir) / "tribe_snapshot"))
    )
    config_path = snap / "config.yaml"
    text = config_path.read_text()
    if GATED_LLAMA in text:
        config_path.write_text(text.replace(GATED_LLAMA, UNGATED_LLAMA))
        print(f"Patched text encoder: {GATED_LLAMA} -> {UNGATED_LLAMA}")
    return snap


def load_model(cache_dir: str = CACHE_DIR):
    """Construct the TRIBE model on the current device (CUDA on the A100)."""
    from tribev2 import TribeModel

    checkpoint_dir = prepare_checkpoint(cache_dir)
    return TribeModel.from_pretrained(
        checkpoint_dir,
        cache_folder=str(Path(cache_dir) / "features"),
        device="auto",
    )
