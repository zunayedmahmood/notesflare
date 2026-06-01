# models/formatting_schemas.py

from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class LineStatus(str, Enum):
    untouched = "untouched"
    pending   = "pending"
    accepted  = "accepted"
    rejected  = "rejected"


class DiffOperationType(str, Enum):
    insert_paragraph_break = "insert_paragraph_break"
    insert_line_break      = "insert_line_break"
    format_as_list_item    = "format_as_list_item"
    format_as_heading      = "format_as_heading"
    format_as_quote        = "format_as_quote"
    normalize_spacing      = "normalize_spacing"


# ─── Line ─────────────────────────────────────────────────────────────────────

class BurstLineResponse(BaseModel):
    line_id:        str
    line_index:     int
    raw_line:       str
    formatted_line: str
    status:         LineStatus
    checksum:       str


# ─── Diff ─────────────────────────────────────────────────────────────────────

class FormattingDiffResponse(BaseModel):
    diff_id:         str
    line_id:         str
    operation:       DiffOperationType
    status:          str              # "pending" | "accepted" | "rejected"
    raw_before:      str
    formatted_after: str


# ─── Format Request / Response ────────────────────────────────────────────────

class FormatBurstRequest(BaseModel):
    burst_id: int

class FormatBurstResponse(BaseModel):
    burst_id:     int
    lines:        List[BurstLineResponse]
    diffs:        List[FormattingDiffResponse]
    diff_count:   int
    processed_at: str


# ─── Diff Action ─────────────────────────────────────────────────────────────

class DiffActionRequest(BaseModel):
    diff_id: str

class DiffActionResponse(BaseModel):
    diff_id:               str
    status:                str
    line_id:               str
    updated_formatted_line: str


# ─── Bulk Action ─────────────────────────────────────────────────────────────

class BulkDiffActionRequest(BaseModel):
    burst_id: int

class BulkDiffActionResponse(BaseModel):
    updated_count: int
    diffs:         List[DiffActionResponse]


# ─── Formatted Burst Fetch ───────────────────────────────────────────────────

class FormattedBurstResponse(BaseModel):
    burst_id:       int
    has_formatting: bool
    lines:          List[BurstLineResponse]
    formatted_text: str
    raw_text:       str
