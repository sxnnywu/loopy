"""Reeled In API — FastAPI app (served on Modal as an ASGI endpoint). Owner: C (Seb).
Run locally: uvicorn backend.main:app --reload
"""
from fastapi import FastAPI
from backend.api import routes_tests, routes_score, routes_voice, routes_history

app = FastAPI(title="Reeled In API")
for m in (routes_tests, routes_score, routes_voice, routes_history):
    app.include_router(m.router, prefix="/api")

@app.get("/api/health")
def health():
    return {"ok": True}
