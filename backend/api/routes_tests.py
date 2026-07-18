"""POST /tests, POST /tests/{id}/variants, GET /tests/{id}. Owner: C (Seb)."""
from fastapi import APIRouter
router = APIRouter()

@router.post("/tests")
def create_test(body: dict):
    raise NotImplementedError  # TODO(C): create Test in Mongo -> return Test

@router.post("/tests/{test_id}/variants")
def add_variant(test_id: str):
    raise NotImplementedError  # TODO(C): store uploaded variant -> return Variant

@router.get("/tests/{test_id}")
def get_test(test_id: str):
    raise NotImplementedError  # TODO(C): return {test, variants, scores}
