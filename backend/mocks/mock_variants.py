"""Canned variant list for stubbing generation. Owner: D (Sunny)."""
def mock_variants(test_id: str = "test_demo0001") -> list:
    return [
        {"id": "var_demoA", "test_id": test_id, "label": "A", "media_key": "media/var_demoA.mp4", "params": {}, "created_at": "2026-07-19T04:20:00Z"},
        {"id": "var_demoB", "test_id": test_id, "label": "B", "media_key": "media/var_demoB.mp4", "params": {}, "created_at": "2026-07-19T04:20:00Z"},
    ]
