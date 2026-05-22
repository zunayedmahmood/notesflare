# models/schemas.py

from pydantic import BaseModel
from typing import Optional


# --- Flareon Models ---

class FlareonCreate(BaseModel):
    name: str

class FlareonResponse(BaseModel):
    id: int
    name: str
    created_at: str
    last_opened_at: Optional[str] = None

class FlareonListResponse(BaseModel):
    flareons: list[FlareonResponse]


# --- Burst Models ---

class BurstResponse(BaseModel):
    id: int
    flareon_id: int
    started_at: str
    content: str  # Aggregated content from burst_entries

class FlareonDetailResponse(BaseModel):
    flareon: FlareonResponse
    bursts: list[BurstResponse]
    active_burst_id: int  # The burst the user should be typing into


# --- Save Models ---

class SaveContentRequest(BaseModel):
    burst_id: int
    content: str

class SaveContentResponse(BaseModel):
    success: bool
    burst_entry_id: int


# --- App State Models ---

class AppStateResponse(BaseModel):
    last_opened_flareon_id: Optional[int] = None
    last_opened_burst_id: Optional[int] = None

class AppStateUpdate(BaseModel):
    flareon_id: int
    burst_id: int


# ─── V1.1 Session Resume ──────────────────────────────────────────────────────

class SessionResumeResponse(BaseModel):
    """
    Single-shot response returned by GET /api/session/resume.
    Contains everything the stream page needs to render without further requests.
    """
    has_session: bool                     # False if user has never opened a Flareon
    flareon: Optional[FlareonResponse] = None    # The last-opened Flareon, or None
    burst_id: Optional[int] = None               # The active burst ID, or None
    stream_content: str                   # Full reconstructed content of active burst
    started_at: Optional[str] = None             # ISO timestamp of the active burst


# ─── V1.1 Append ─────────────────────────────────────────────────────────────

class AppendChunkRequest(BaseModel):
    """
    Payload for POST /api/burst/append.
    The frontend sends only the new characters since the last append.
    """
    burst_id: int
    text: str                             # The new delta text only — NOT the full content

class AppendChunkResponse(BaseModel):
    success: bool
    sequence_number: int                  # The sequence number assigned to this chunk


# ─── V1.1 Flareon Switch ──────────────────────────────────────────────────────

class FlareonSwitchResponse(BaseModel):
    """
    Returned when the user switches to a different Flareon from the stream page.
    Mirrors SessionResumeResponse but is always has_session=True.
    """
    flareon: FlareonResponse
    burst_id: int
    stream_content: str
    started_at: str
