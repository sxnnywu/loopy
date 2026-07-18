"""POST /tests/{id}/score, POST /tests/{id}/explain. Owner: C (calls B + D)."""
from fastapi import APIRouter
router = APIRouter()

@router.post("/tests/{test_id}/score")
def score_test(test_id: str):
    raise NotImplementedError  # TODO(C): call scoring (B) per variant, store, set winner

@router.post("/tests/{test_id}/explain")
def explain_test(test_id: str):
    raise NotImplementedError  # TODO(C->D): region_timeline -> captions via explainer
