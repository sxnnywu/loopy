"""Modal app: serves the FastAPI ASGI app (CPU, scale-to-zero) + hosts the TRIBE GPU fn.
Owner: C wires the app; B fills score_gpu.
"""
import modal

app = modal.App("reeled-in")
image = modal.Image.debian_slim().pip_install_from_requirements("backend/requirements.txt")

@app.function(image=image)
@modal.asgi_app()
def api():
    from backend.main import app as fastapi_app
    return fastapi_app

@app.function(image=image, gpu="A100", timeout=600)
def score_gpu(media_key: str) -> dict:
    from backend.scoring.score import score
    return score(media_key)
