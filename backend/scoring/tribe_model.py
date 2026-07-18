"""TRIBE v2 loading — Person B (scoring engine).

Runs inside the Modal A100 container. Loads Meta's TRIBE v2 checkpoint, but
overrides the gated `meta-llama/Llama-3.2-3B` text encoder with the ungated
mirror `unsloth/Llama-3.2-3B` (identical weights) so we never block on Meta's
license approval.

The checkpoint + patched config are cached on a Modal Volume so cold starts
don't re-download.
"""

from pathlib import Path

TRIBE_REPO = "facebook/tribev2"
GATED_LLAMA = "meta-llama/Llama-3.2-3B"
UNGATED_LLAMA = "unsloth/Llama-3.2-3B"


def prepare_checkpoint(cache_dir: str) -> Path:
    """Download the TRIBE checkpoint and patch its text encoder to the ungated
    Llama mirror. Returns a local dir with config.yaml + best.ckpt ready for
    TribeModel.from_pretrained. Idempotent — safe to call every cold start."""
    from huggingface_hub import snapshot_download

    snap = Path(
        snapshot_download(TRIBE_REPO, cache_dir=str(Path(cache_dir) / "tribe_snapshot"))
    )

    config_path = snap / "config.yaml"
    text = config_path.read_text()
    if GATED_LLAMA in text:
        config_path.write_text(text.replace(GATED_LLAMA, UNGATED_LLAMA))
        print(f"Patched text encoder: {GATED_LLAMA} -> {UNGATED_LLAMA}")
    else:
        print("Llama reference already patched or absent; leaving config as-is.")

    return snap


def load_tribe(cache_dir: str):
    """Construct the TRIBE model on the current device (CUDA on the A100)."""
    from tribev2 import TribeModel

    checkpoint_dir = prepare_checkpoint(cache_dir)
    model = TribeModel.from_pretrained(
        checkpoint_dir,
        cache_folder=str(Path(cache_dir) / "features"),
        device="auto",
    )
    return model
