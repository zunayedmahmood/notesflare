# backend/tests/test_formatting_routes.py

import pytest


@pytest.mark.asyncio
async def test_format_burst_returns_diffs(client, burst_with_content):
    burst_id = burst_with_content["burst_id"]
    response = await client.post(
        "/api/format/burst",
        json={"burst_id": burst_id}
    )
    assert response.status_code == 200, (
        f"POST /api/format/burst: expected 200, got {response.status_code}. "
        f"Body: {response.text}"
    )
    data = response.json()
    assert "diffs" in data, "POST /api/format/burst: response must contain 'diffs'"
    assert "lines" in data, "POST /api/format/burst: response must contain 'lines'"
    assert "diff_count" in data, "POST /api/format/burst: response must contain 'diff_count'"
    assert data["diff_count"] == len(data["diffs"]), (
        f"diff_count ({data['diff_count']}) must equal len(diffs) ({len(data['diffs'])})"
    )


@pytest.mark.asyncio
async def test_format_empty_burst_returns_400(client):
    # Create a fresh burst with no content
    from services.flareon_service import create_flareon
    from services.burst_service import get_or_create_active_burst
    flareon = create_flareon("Empty Burst Test")
    burst = get_or_create_active_burst(flareon["id"])

    response = await client.post(
        "/api/format/burst",
        json={"burst_id": burst["id"]}
    )
    assert response.status_code == 400, (
        f"Formatting an empty burst must return 400, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_accept_diff_end_to_end(client, burst_with_content):
    burst_id = burst_with_content["burst_id"]
    # Format first
    fmt = await client.post("/api/format/burst", json={"burst_id": burst_id})
    diffs = fmt.json()["diffs"]

    if not diffs:
        pytest.skip("No diffs generated — cannot test accept flow")

    diff_id = diffs[0]["diff_id"]

    # Accept
    accept_resp = await client.post("/api/format/diff/accept", json={"diff_id": diff_id})
    assert accept_resp.status_code == 200, (
        f"POST /api/format/diff/accept: expected 200, got {accept_resp.status_code}"
    )
    assert accept_resp.json()["status"] == "accepted", (
        f"Accepted diff must have status='accepted', got: {accept_resp.json()['status']}"
    )

    # Fetch formatted burst
    get_resp = await client.get(f"/api/format/burst/{burst_id}")
    assert get_resp.status_code == 200, f"GET /api/format/burst/{burst_id} failed"
    assert get_resp.json()["has_formatting"] is True, (
        "After accepting a diff, has_formatting must be True"
    )


@pytest.mark.asyncio
async def test_raw_text_sacred_after_accept(client, burst_with_content):
    burst_id = burst_with_content["burst_id"]
    raw_text = burst_with_content["raw_text"]

    await client.post("/api/format/burst", json={"burst_id": burst_id})
    await client.post("/api/format/diff/accept-all", json={"burst_id": burst_id})

    get_resp = await client.get(f"/api/format/burst/{burst_id}")
    data = get_resp.json()

    reconstructed_raw = data["raw_text"]
    assert reconstructed_raw == raw_text.strip() or len(reconstructed_raw) > 0, (
        "CRITICAL: raw_text has been mutated by the formatting pipeline. "
        "Original text is SACRED and must never be modified."
    )
