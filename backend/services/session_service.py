# services/session_service.py

"""
Session service for NotesFlare V1.1.

Responsibility: given the current app_state, reconstruct a full session
context that the frontend can render immediately. This is the backend half
of the "instant resume" experience.

This service calls into burst_service and stream_service.
It does NOT write to the database — it only reads.
"""

from database.db import get_db
from services import flareon_service, burst_service, stream_service
from services.storage_service import get_app_state, update_app_state


def resume_session() -> dict:
    """
    Called by GET /api/session/resume on frontend startup.

    Flow:
    1. Read app_state to find last_opened_flareon_id
    2. If none → return has_session=False
    3. If found → call burst_service.get_or_create_active_burst(flareon_id)
    4. Update app_state with potentially new burst ID
    5. Reconstruct full stream content via stream_service
    6. Return everything

    Returns a dict matching SessionResumeResponse.
    """
    state = get_app_state()
    flareon_id = state.get("last_opened_flareon_id")

    if not flareon_id:
        return {
            "has_session": False,
            "flareon": None,
            "burst_id": None,
            "stream_content": "",
            "started_at": None,
        }

    flareon = flareon_service.get_flareon_by_id(flareon_id)
    if not flareon:
        # Flareon was deleted since last session — treat as no session
        return {
            "has_session": False,
            "flareon": None,
            "burst_id": None,
            "stream_content": "",
            "started_at": None,
        }

    flareon_service.touch_flareon(flareon_id)
    active_burst = burst_service.get_or_create_active_burst(flareon_id)
    update_app_state(flareon_id, active_burst["id"])

    stream_content = stream_service.reconstruct_burst(active_burst["id"])

    return {
        "has_session": True,
        "flareon": flareon,
        "burst_id": active_burst["id"],
        "stream_content": stream_content,
        "started_at": active_burst["started_at"],
    }


def switch_to_flareon(flareon_id: int) -> dict:
    """
    Called when the user clicks a different Flareon in the sidebar.

    Same as resume_session but for an explicit Flareon ID.
    Returns a dict matching FlareonSwitchResponse.
    """
    flareon = flareon_service.get_flareon_by_id(flareon_id)
    if not flareon:
        raise ValueError(f"Flareon {flareon_id} not found.")

    flareon_service.touch_flareon(flareon_id)
    active_burst = burst_service.get_or_create_active_burst(flareon_id)
    update_app_state(flareon_id, active_burst["id"])

    stream_content = stream_service.reconstruct_burst(active_burst["id"])

    return {
        "flareon": flareon,
        "burst_id": active_burst["id"],
        "stream_content": stream_content,
        "started_at": active_burst["started_at"],
    }
