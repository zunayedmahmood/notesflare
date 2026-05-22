# backend/tests/test_routes.py
"""
Tests: API route integration (api/routes.py)

These tests go through the full HTTP stack: request → route → service → DB → response.
Every endpoint is tested for:
  - Correct status codes
  - Correct response shape
  - Correct error responses
"""

import pytest
from httpx import AsyncClient


@pytest.mark.api
async def test_health_check(client: AsyncClient):
    response = await client.get("/api/health")

    assert response.status_code == 200, (
        f"[GET /api/health] Expected 200 OK.\n"
        f"  Status   : {response.status_code}\n"
        f"  Body     : {response.text}\n"
        f"  Fix      : Ensure @router.get('/health') is registered and FastAPI app starts."
    )
    assert response.json() == {"status": "ok"}, (
        f"[GET /api/health] Unexpected response body.\n"
        f"  Expected : {{\"status\": \"ok\"}}\n"
        f"  Got      : {response.json()}"
    )


@pytest.mark.api
async def test_get_state_fresh(client: AsyncClient):
    response = await client.get("/api/state")
    data = response.json()

    assert response.status_code == 200, (
        f"[GET /api/state] Expected 200 on fresh DB.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}"
    )
    assert data["last_opened_flareon_id"] is None, (
        f"[GET /api/state] Expected null flareon_id on fresh start.\n"
        f"  Got : {data}"
    )


@pytest.mark.api
async def test_create_flareon_success(client: AsyncClient):
    response = await client.post("/api/flareons", json={"name": "Physics"})

    assert response.status_code == 201, (
        f"[POST /api/flareons] Expected 201 Created.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}\n"
        f"  Fix    : Route must return JSONResponse with status_code=201, not 200."
    )
    data = response.json()
    assert data["name"] == "Physics", (
        f"[POST /api/flareons] Name mismatch in response.\n"
        f"  Sent   : 'Physics'\n"
        f"  Got    : {data}"
    )
    assert isinstance(data["id"], int) and data["id"] > 0, (
        f"[POST /api/flareons] Response must include a positive integer 'id'.\n"
        f"  Got id : {data.get('id')}"
    )


@pytest.mark.api
async def test_create_flareon_duplicate_returns_400(client: AsyncClient):
    await client.post("/api/flareons", json={"name": "Cooking"})
    response = await client.post("/api/flareons", json={"name": "Cooking"})

    assert response.status_code == 400, (
        f"[POST /api/flareons] Duplicate name must return 400.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}\n"
        f"  Fix    : Route must catch ValueError from flareon_service and return "
        f"HTTPException(status_code=400, detail=str(e))."
    )
    assert "Cooking" in response.json().get("detail", ""), (
        f"[POST /api/flareons] 400 error detail must include the duplicate name.\n"
        f"  Got : {response.json()}"
    )


@pytest.mark.api
async def test_get_flareon_returns_bursts_array(client: AsyncClient):
    create_resp = await client.post("/api/flareons", json={"name": "Biology"})
    fid = create_resp.json()["id"]

    response = await client.get(f"/api/flareons/{fid}")
    data = response.json()

    assert response.status_code == 200, (
        f"[GET /api/flareons/{{id}}] Expected 200.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}"
    )
    assert "bursts" in data, (
        f"[GET /api/flareons/{{id}}] Response must include 'bursts' array.\n"
        f"  Keys found : {list(data.keys())}"
    )
    assert "active_burst_id" in data, (
        f"[GET /api/flareons/{{id}}] Response must include 'active_burst_id'.\n"
        f"  This field tells the frontend which burst to write into.\n"
        f"  Keys found : {list(data.keys())}"
    )
    assert isinstance(data["bursts"], list), (
        f"[GET /api/flareons/{{id}}] 'bursts' must be a list.\n"
        f"  Type found : {type(data['bursts'])}"
    )


@pytest.mark.api
async def test_get_flareon_not_found_returns_404(client: AsyncClient):
    response = await client.get("/api/flareons/99999")

    assert response.status_code == 404, (
        f"[GET /api/flareons/{{id}}] Non-existent Flareon must return 404.\n"
        f"  Status : {response.status_code}\n"
        f"  Body   : {response.text}\n"
        f"  Fix    : Route must check if flareon_service.get_flareon_by_id returns None "
        f"and raise HTTPException(status_code=404)."
    )


@pytest.mark.api
async def test_save_endpoint_persists_content(client: AsyncClient):
    create_resp = await client.post("/api/flareons", json={"name": "Mechanics"})
    fid = create_resp.json()["id"]
    open_resp = await client.get(f"/api/flareons/{fid}")
    burst_id = open_resp.json()["active_burst_id"]

    save_resp = await client.post("/api/save", json={
        "burst_id": burst_id,
        "content": "Force equals mass times acceleration."
    })

    assert save_resp.status_code == 200, (
        f"[POST /api/save] Expected 200.\n"
        f"  Status : {save_resp.status_code}\n"
        f"  Body   : {save_resp.text}"
    )
    assert save_resp.json().get("success") is True, (
        f"[POST /api/save] Response must include {{\"success\": true}}.\n"
        f"  Got : {save_resp.json()}"
    )

    # Re-open to verify content was persisted
    verify_resp = await client.get(f"/api/flareons/{fid}")
    active_burst = next(
        (b for b in verify_resp.json()["bursts"]
         if b["id"] == burst_id), None
    )

    assert active_burst is not None, (
        f"[POST /api/save → GET /api/flareons/{{id}}] Burst not found in re-fetch.\n"
        f"  burst_id : {burst_id}\n"
        f"  Bursts in response : {[b['id'] for b in verify_resp.json()['bursts']]}"
    )
    assert active_burst["content"] == "Force equals mass times acceleration.", (
        f"[POST /api/save] Content not persisted after save.\n"
        f"  Saved    : 'Force equals mass times acceleration.'\n"
        f"  Retrieved: '{active_burst['content']}'\n"
        f"  Fix      : Verify storage_service.save_content is correctly updating "
        f"the burst_entries row and that the GET endpoint reads the content back via JOIN."
    )


@pytest.mark.api
async def test_list_flareons_returns_ordered_list(client: AsyncClient):
    await client.post("/api/flareons", json={"name": "Alpha"})
    await client.post("/api/flareons", json={"name": "Beta"})

    response = await client.get("/api/flareons")
    data = response.json()

    assert "flareons" in data, (
        f"[GET /api/flareons] Response must have 'flareons' key.\n"
        f"  Got : {list(data.keys())}"
    )
    assert isinstance(data["flareons"], list), (
        f"[GET /api/flareons] 'flareons' must be a list.\n"
        f"  Type : {type(data['flareons'])}"
    )
    assert len(data["flareons"]) >= 2, (
        f"[GET /api/flareons] Expected at least 2 Flareons after creating two.\n"
        f"  Found : {len(data['flareons'])}"
    )


# ─── V1.1 Route Tests ─────────────────────────────────────────────────────────

@pytest.mark.api
async def test_session_resume_fresh(client: AsyncClient):
    response = await client.get("/api/session/resume")
    assert response.status_code == 200
    data = response.json()
    assert data["has_session"] is False
    assert data["flareon"] is None
    assert data["stream_content"] == ""


@pytest.mark.api
async def test_session_resume_existing(client: AsyncClient):
    # 1. Create a Flareon
    create_resp = await client.post("/api/flareons", json={"name": "Instant Resume Test"})
    fid = create_resp.json()["id"]

    # 2. Open it to set app_state
    await client.get(f"/api/flareons/{fid}")

    # 3. Resume session
    response = await client.get("/api/session/resume")
    assert response.status_code == 200
    data = response.json()
    assert data["has_session"] is True
    assert data["flareon"]["id"] == fid
    assert data["flareon"]["name"] == "Instant Resume Test"
    assert isinstance(data["burst_id"], int)
    assert data["stream_content"] == ""


@pytest.mark.api
async def test_burst_append_persists_chunks(client: AsyncClient):
    # 1. Create and open Flareon
    create_resp = await client.post("/api/flareons", json={"name": "Append Test"})
    fid = create_resp.json()["id"]
    await client.get(f"/api/flareons/{fid}")

    # 2. Resume to get burst_id
    res_resp = await client.get("/api/session/resume")
    burst_id = res_resp.json()["burst_id"]

    # 3. Append chunks
    app1 = await client.post("/api/burst/append", json={"burst_id": burst_id, "text": "Continuous "})
    assert app1.status_code == 200
    assert app1.json()["success"] is True
    assert app1.json()["sequence_number"] == 0

    app2 = await client.post("/api/burst/append", json={"burst_id": burst_id, "text": "Stream!"})
    assert app2.status_code == 200
    assert app2.json()["sequence_number"] == 1

    # 4. Resume to verify reconstructed content
    res_resp2 = await client.get("/api/session/resume")
    assert res_resp2.json()["stream_content"] == "Continuous Stream!"


@pytest.mark.api
async def test_burst_append_rejects_empty(client: AsyncClient):
    app = await client.post("/api/burst/append", json={"burst_id": 1, "text": ""})
    assert app.status_code == 400
    assert "empty" in app.json()["detail"]


@pytest.mark.api
async def test_switch_flareon(client: AsyncClient):
    # 1. Create F1 and F2
    f1_resp = await client.post("/api/flareons", json={"name": "F1"})
    f1_id = f1_resp.json()["id"]
    f2_resp = await client.post("/api/flareons", json={"name": "F2"})
    f2_id = f2_resp.json()["id"]

    # 2. Open F1
    await client.get(f"/api/flareons/{f1_id}")

    # 3. Switch to F2
    switch_resp = await client.get(f"/api/session/switch/{f2_id}")
    assert switch_resp.status_code == 200
    data = switch_resp.json()
    assert data["flareon"]["id"] == f2_id
    assert data["flareon"]["name"] == "F2"

    # 4. Resume to verify it now returns F2
    res_resp = await client.get("/api/session/resume")
    assert res_resp.json()["flareon"]["id"] == f2_id

