"""POST /tests/{id}/voice-variants. Owner: C (calls D)."""
from fastapi import APIRouter
router = APIRouter()

@router.post("/tests/{test_id}/voice-variants")
def voice_variants(test_id: str, body: dict):
    raise NotImplementedError  # TODO(C->D): generate_voice_variants(base, script)
