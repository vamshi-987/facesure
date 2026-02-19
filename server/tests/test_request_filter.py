"""
Minimal tests for Custom View Requests filter (role-aware).
Run from server dir: python -m pytest tests/test_request_filter.py -v
Requires: pytest, and MongoDB available (or mock extensions.mongo).
"""
import pytest


class TestStatusFilterMapping:
    """Unit: _status_filter_to_db maps UI statuses to DB status lists."""

    def test_approved_maps_to_db_statuses(self):
        from services.request_service import _status_filter_to_db
        result = _status_filter_to_db(["approved"])
        assert "APPROVED" in result
        assert "LEFT_CAMPUS" in result

    def test_pending_maps_to_requested_and_pending_states(self):
        from services.request_service import _status_filter_to_db
        result = _status_filter_to_db(["pending"])
        assert "REQUESTED" in result
        assert "PENDING_MENTOR" in result
        assert "PENDING_HOD" in result

    def test_rejected_maps_to_rejected_statuses(self):
        from services.request_service import _status_filter_to_db
        result = _status_filter_to_db(["rejected"])
        assert "REJECTED" in result
        assert "REJECTED_BY_MENTOR" in result

    def test_empty_or_unknown_returns_none(self):
        from services.request_service import _status_filter_to_db
        assert _status_filter_to_db([]) is None
        assert _status_filter_to_db(None) is None


# Integration tests require FastAPI TestClient and auth; skipped if no deps or DB.
@pytest.mark.skip(reason="Integration: needs TestClient + JWT + MongoDB")
def test_filter_endpoint_admin_returns_200():
    from fastapi.testclient import TestClient
    from app import app
    client = TestClient(app)
    # Add Admin token to headers
    resp = client.post("/request/filter", json={"statuses": ["approved"], "pageSize": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "items" in data["data"]
    assert "total" in data["data"]


@pytest.mark.skip(reason="Integration: needs TestClient + JWT + MongoDB")
def test_filter_endpoint_student_returns_403():
    from fastapi.testclient import TestClient
    from app import app
    client = TestClient(app)
    # Add Student token
    resp = client.post("/request/filter", json={})
    assert resp.status_code == 403
