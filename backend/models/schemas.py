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
