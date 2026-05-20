# api/routes.py

import os
from pathlib import Path
from database.db import get_db
from fastapi import APIRouter, HTTPException
from models.schemas import (
    FlareonCreate, FlareonListResponse, FlareonDetailResponse,
    FlareonResponse, BurstResponse,
    SaveContentRequest, SaveContentResponse,
    AppStateResponse, AppStateUpdate,
)
from services import flareon_service, burst_service, storage_service

router = APIRouter()



# ─── Health ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    """Simple liveness check. Frontend polls this on startup."""
    return {"status": "ok"}


# ─── App State ────────────────────────────────────────────────────────────────

@router.get("/state", response_model=AppStateResponse)
def get_app_state():
    """
    Return the last-opened Flareon and Burst IDs.
    Frontend calls this on startup to know where to resume.
    Returns null IDs if the user has never opened a Flareon.
    """
    state = storage_service.get_app_state()
    return AppStateResponse(
        last_opened_flareon_id=state.get("last_opened_flareon_id"),
        last_opened_burst_id=state.get("last_opened_burst_id"),
    )


# ─── Flareons ─────────────────────────────────────────────────────────────────

@router.get("/flareons", response_model=FlareonListResponse)
def list_flareons():
    """Return all Flareons, ordered by most recently opened."""
    flareons = flareon_service.list_flareons()
    return FlareonListResponse(
        flareons=[FlareonResponse(**f) for f in flareons]
    )


@router.post("/flareons", response_model=FlareonResponse, status_code=201)
def create_flareon(body: FlareonCreate):
    """
    Create a new Flareon.
    Returns 400 if a Flareon with the same name already exists.
    """
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Flareon name cannot be empty.")
    try:
        flareon = flareon_service.create_flareon(body.name)
        return FlareonResponse(**flareon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/flareons/{flareon_id}", response_model=FlareonDetailResponse)
def open_flareon(flareon_id: int):
    """
    Open a Flareon. This is the main data-loading endpoint.

    On call:
    1. Verifies the Flareon exists
    2. Touches last_opened_at
    3. Resolves active burst (30-min continuity rule)
    4. Updates app_state
    5. Returns all bursts + active burst ID

    The frontend renders all bursts and focuses the active one.
    """
    flareon = flareon_service.get_flareon_by_id(flareon_id)
    if not flareon:
        raise HTTPException(status_code=404, detail="Flareon not found.")

    flareon_service.touch_flareon(flareon_id)

    active_burst = burst_service.get_or_create_active_burst(flareon_id)
    all_bursts = burst_service.get_all_bursts_for_flareon(flareon_id)

    storage_service.update_app_state(flareon_id, active_burst["id"])

    return FlareonDetailResponse(
        flareon=FlareonResponse(**flareon),
        bursts=[BurstResponse(**b) for b in all_bursts],
        active_burst_id=active_burst["id"],
    )


# ─── Content Save ─────────────────────────────────────────────────────────────

@router.post("/save", response_model=SaveContentResponse)
def save_content(body: SaveContentRequest):
    """
    Save content for a burst. Called by the frontend's debounced autosave.
    This endpoint must be fast — it is called every time the user pauses typing.
    """
    entry_id = storage_service.save_content(body.burst_id, body.content)
    return SaveContentResponse(success=True, burst_entry_id=entry_id)


@router.post("/test/reset", include_in_schema=False)
def reset_test_database():
    """
    Wipe and re-initialize the database. Only available in NOTESFLARE_ENV=test.
    Used by E2E tests to guarantee a clean state before each test run.
    """
    if os.getenv("NOTESFLARE_ENV") != "test":
        raise HTTPException(
            status_code=403,
            detail=(
                "[/api/test/reset] This endpoint is only available in test mode. "
                "Set NOTESFLARE_ENV=test to enable it. "
                "Never call this endpoint in production or development."
            )
        )

    db = get_db()
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    db.execute("PRAGMA foreign_keys=OFF")
    db.executescript("DROP TABLE IF EXISTS burst_entries; DROP TABLE IF EXISTS bursts; "
                     "DROP TABLE IF EXISTS flareons; DROP TABLE IF EXISTS app_state;")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(schema_path.read_text())
    db.commit()

    return {"reset": True}

