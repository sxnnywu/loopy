"""GET /history. Owner: C (Seb)."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/history")
def history():
    raise NotImplementedError  # TODO(C): return {tests: [...]} for the user
