"""Modal app for Reeled In — Person B (scoring engine).

Phase 0 smoke test: confirm an A100 boots and CUDA is visible.
Run:  python3 -m modal run backend/modal_app.py
"""

import modal

app = modal.App("reeled-in-scoring")

# Minimal GPU image — torch only, enough to prove the A100 comes up.
image = modal.Image.debian_slim(python_version="3.11").pip_install("torch")


@app.function(gpu="A100", image=image, timeout=600)
def smoke_test() -> dict:
    import torch

    info = {
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "torch_version": str(torch.__version__),
    }
    print("A100 smoke test:", info)
    return info


@app.local_entrypoint()
def main():
    result = smoke_test.remote()
    assert result["cuda_available"], "CUDA not available on the GPU worker"
    print("PASS — A100 booted:", result)
