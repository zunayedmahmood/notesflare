# api/routes.py

import os
import sqlite3
from pathlib import Path
from database.db import get_db
from fastapi import APIRouter, HTTPException
from models.schemas import (
    FlareonCreate, FlareonListResponse, FlareonDetailResponse,
    FlareonResponse, BurstResponse,
    SaveContentRequest, SaveContentResponse,
    AppStateResponse, AppStateUpdate,
    SessionResumeResponse, AppendChunkRequest, AppendChunkResponse,
    FlareonSwitchResponse,
)
from services import flareon_service, burst_service, storage_service, session_service, append_service

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
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error occurred: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


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
    try:
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
    except HTTPException:
        raise
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error occurred: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


# ─── Content Save ─────────────────────────────────────────────────────────────

@router.post("/save", response_model=SaveContentResponse)
def save_content(body: SaveContentRequest):
    """
    DEPRECATED in V1.1. Use POST /api/burst/append instead.
    This endpoint remains to avoid breaking any V1 clients during transition.
    It now appends the content as a single chunk rather than overwriting.
    """
    seq = append_service.append_chunk(body.burst_id, body.content)
    return SaveContentResponse(success=True, burst_entry_id=seq)


# ─── V1.1 Session & Append Endpoints ──────────────────────────────────────────

@router.get("/session/resume", response_model=SessionResumeResponse)
def session_resume():
    """
    Called by the frontend Stream Page on startup.

    Returns the full session state in one request:
    - The last-opened Flareon
    - The active burst ID (new or continued, per 30-min rule)
    - The full reconstructed stream content of the active burst
    - has_session=False if the user has never opened a Flareon

    This replaces the V1 two-step startup (/api/state then /api/flareons/{id}).
    """
    try:
        result = session_service.resume_session()
        return SessionResumeResponse(
            has_session=result["has_session"],
            flareon=FlareonResponse(**result["flareon"]) if result["flareon"] else None,
            burst_id=result["burst_id"],
            stream_content=result["stream_content"],
            started_at=result["started_at"],
        )
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error occurred: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/burst/append", response_model=AppendChunkResponse)
def append_to_burst(body: AppendChunkRequest):
    """
    Append a text delta to a burst's entry log.

    Called by the frontend's debounced autosave. The payload is the NEW text
    typed since the last append — NOT the full content.

    Rejects empty text strings to avoid polluting the entry log.
    This endpoint must be fast. It is called every ~1 second while typing.
    """
    if not body.text:
        raise HTTPException(status_code=400, detail="text must not be empty.")

    try:
        seq = append_service.append_chunk(body.burst_id, body.text)
        return AppendChunkResponse(success=True, sequence_number=seq)
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error occurred: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/session/switch/{flareon_id}", response_model=FlareonSwitchResponse)
def switch_flareon(flareon_id: int):
    """
    Switch the active Flareon from the stream page sidebar.

    Returns the same shape as session/resume but for the specified Flareon.
    Updates app_state so the next resume returns this Flareon.
    """
    try:
        result = session_service.switch_to_flareon(flareon_id)
        return FlareonSwitchResponse(
            flareon=FlareonResponse(**result["flareon"]),
            burst_id=result["burst_id"],
            stream_content=result["stream_content"],
            started_at=result["started_at"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error occurred: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


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

    import database.db as db_mod
    db_mod.close_all_connections()

    db = get_db()
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    db.execute("PRAGMA foreign_keys=OFF")
    db.executescript(
        "DROP TABLE IF EXISTS line_history; "
        "DROP TABLE IF EXISTS burst_diffs; "
        "DROP TABLE IF EXISTS burst_lines; "
        "DROP TABLE IF EXISTS burst_entries; "
        "DROP TABLE IF EXISTS bursts; "
        "DROP TABLE IF EXISTS flareons; "
        "DROP TABLE IF EXISTS app_state;"
    )
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(schema_path.read_text())
    db.commit()

    return {"reset": True}




