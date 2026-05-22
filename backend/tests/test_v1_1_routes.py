# backend/tests/test_v1_1_routes.py

"""
API integration tests for V1.1 endpoints.
Uses the test HTTP client from conftest.py.
"""

import pytest


@pytest.mark.api
def test_session_resume_returns_no_session_on_empty_db(test_client):
    """GET /api/session/resume on fresh DB must return has_session=false."""
    response = test_client.get("/api/session/resume")
    assert response.status_code == 200, (
        f"[route:session/resume] Expected 200, got {response.status_code}. "
        f"Body: {response.text}"
    )
    data = response.json()
    assert data["has_session"] is False, (
        f"[route:session/resume] Empty DB must return has_session=false. Got: {data}"
    )
    assert data["flareon"] is None
    assert data["stream_content"] == ""


@pytest.mark.api
def test_session_resume_returns_full_state_after_activity(test_client):
    """After creating a Flareon and appending content, resume returns full state."""
    # Create flareon
    flareon = test_client.post("/api/flareons", json={"name": "Route Test"}).json()
    flareon_id = flareon["id"]

    # Switch to it
    switch = test_client.get(f"/api/session/switch/{flareon_id}").json()
    burst_id = switch["burst_id"]

    # Append content
    test_client.post("/api/burst/append", json={"burst_id": burst_id, "text": "Test content"})

    # Resume
    response = test_client.get("/api/session/resume")
    data = response.json()

    assert data["has_session"] is True
    assert data["flareon"]["id"] == flareon_id
    assert data["burst_id"] == burst_id
    assert data["stream_content"] == "Test content", (
        f"[route:session/resume] stream_content must equal appended text. "
        f"Expected 'Test content', got {repr(data['stream_content'])}"
    )


@pytest.mark.api
def test_burst_append_accepts_valid_payload(test_client):
    """POST /api/burst/append with valid payload returns success and sequence_number."""
    flareon = test_client.post("/api/flareons", json={"name": "Append Test"}).json()
    switch = test_client.get(f"/api/session/switch/{flareon['id']}").json()
    burst_id = switch["burst_id"]

    response = test_client.post(
        "/api/burst/append",
        json={"burst_id": burst_id, "text": "first chunk"}
    )
    assert response.status_code == 200, (
        f"[route:burst/append] Expected 200, got {response.status_code}. "
        f"Body: {response.text}"
    )
    data = response.json()
    assert data["success"] is True
    assert data["sequence_number"] == 0, (
        f"[route:burst/append] First chunk must have sequence_number 0. Got: {data}"
    )


@pytest.mark.api
def test_burst_append_rejects_empty_text(test_client):
    """POST /api/burst/append with empty text must return 400."""
    flareon = test_client.post("/api/flareons", json={"name": "Empty Reject"}).json()
    switch = test_client.get(f"/api/session/switch/{flareon['id']}").json()

    response = test_client.post(
        "/api/burst/append",
        json={"burst_id": switch["burst_id"], "text": ""}
    )
    assert response.status_code == 400, (
        f"[route:burst/append] Empty text must return 400. "
        f"Got: {response.status_code}. Body: {response.text}"
    )


@pytest.mark.api
def test_session_switch_returns_correct_flareon(test_client):
    """GET /api/session/switch/{id} returns the correct Flareon's data."""
    f1 = test_client.post("/api/flareons", json={"name": "Flareon Alpha"}).json()
    f2 = test_client.post("/api/flareons", json={"name": "Flareon Beta"}).json()

    # Open f1, add content
    switch1 = test_client.get(f"/api/session/switch/{f1['id']}").json()
    test_client.post("/api/burst/append", json={"burst_id": switch1["burst_id"], "text": "Alpha content"})

    # Switch to f2
    switch2 = test_client.get(f"/api/session/switch/{f2['id']}").json()
    assert switch2["flareon"]["id"] == f2["id"], (
        f"[route:session/switch] Must return f2, got: {switch2['flareon']}"
    )
    assert switch2["stream_content"] == "", (
        f"[route:session/switch] f2 should have empty content. Got: {repr(switch2['stream_content'])}"
    )

    # Switch back to f1
    switch_back = test_client.get(f"/api/session/switch/{f1['id']}").json()
    assert switch_back["stream_content"] == "Alpha content", (
        f"[route:session/switch] Switching back to f1 must restore its content. "
        f"Got: {repr(switch_back['stream_content'])}"
    )


@pytest.mark.api
def test_session_switch_returns_404_for_missing_flareon(test_client):
    """GET /api/session/switch/99999 must return 404."""
    response = test_client.get("/api/session/switch/99999")
    assert response.status_code == 404, (
        f"[route:session/switch] Non-existent Flareon must return 404. "
        f"Got: {response.status_code}"
    )
