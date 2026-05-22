# backend/tests/test_session_service.py

"""
Unit tests for session_service.py.
"""

import pytest
from freezegun import freeze_time


@pytest.mark.unit
def test_resume_with_no_app_state(test_db):
    """
    resume_session with no previous session must return has_session=False.
    """
    from services.session_service import resume_session

    result = resume_session()

    assert result["has_session"] is False, (
        f"[session_service] No prior session must return has_session=False. "
        f"Got: {result}"
    )
    assert result["flareon"] is None
    assert result["burst_id"] is None
    assert result["stream_content"] == ""


@pytest.mark.unit
def test_resume_restores_last_flareon(test_db, create_flareon, create_burst):
    """
    After opening a Flareon (which updates app_state), resume_session
    must return that Flareon and the active burst.
    """
    from services.session_service import resume_session, switch_to_flareon
    from services.append_service import append_chunk

    flareon = create_flareon("Resume Test")
    # Switch to it so app_state is updated
    switch_result = switch_to_flareon(flareon["id"])
    burst_id = switch_result["burst_id"]

    # Add content
    append_chunk(burst_id, "Some content")

    # Now resume
    result = resume_session()

    assert result["has_session"] is True, "[session_service] must find prior session."
    assert result["flareon"]["id"] == flareon["id"], (
        f"[session_service] resume must return the last-opened Flareon. "
        f"Expected id={flareon['id']}, got {result['flareon']['id']}"
    )
    assert result["stream_content"] == "Some content", (
        f"[session_service] resume must return full reconstructed stream content. "
        f"Expected 'Some content', got {repr(result['stream_content'])}"
    )


@pytest.mark.unit
@freeze_time("2025-01-15 14:00:00", tz_offset=0)
def test_resume_creates_new_burst_after_30_minutes(test_db, create_flareon):
    """
    If last burst was more than 30 minutes ago, resume_session must
    return a new burst, not the old one.
    """
    from services.session_service import resume_session, switch_to_flareon

    flareon = create_flareon("30-min Test")
    switch_result = switch_to_flareon(flareon["id"])
    old_burst_id = switch_result["burst_id"]

    # Move time forward by 31 minutes
    with freeze_time("2025-01-15 14:31:00"):
        result = resume_session()

    assert result["burst_id"] != old_burst_id, (
        f"[session_service] After 31 minutes, resume must create a new burst. "
        f"Expected new burst_id != {old_burst_id}. "
        f"Got burst_id = {result['burst_id']}. "
        f"Fix: ensure burst_service.get_or_create_active_burst checks updated_at correctly."
    )
    assert result["stream_content"] == "", (
        f"[session_service] New burst content must be empty. "
        f"Got: {repr(result['stream_content'])}"
    )
