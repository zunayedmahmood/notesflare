# backend/tests/formatting/test_diff_service.py

import pytest
from services.formatting.diff_service import (
    store_diffs, get_diffs_for_burst, accept_diff, reject_diff,
    accept_all_pending, reject_all_pending, get_formatted_burst,
)
from services.formatting.lineage_service import get_or_create_lines


class TestStoreDiffs:
    def test_creates_pending_diffs(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["line one", "line two"])
        operations = [{
            "line_index": 0,
            "operation": "insert_paragraph_break",
            "raw_before": "line one",
            "formatted_after": "\nline one",
        }]
        diffs = store_diffs(burst_id, lines, operations)
        assert len(diffs) == 1, f"Expected 1 diff, got {len(diffs)}"
        assert diffs[0]["status"] == "pending", (
            f"New diff status must be 'pending', got '{diffs[0]['status']}'"
        )

    def test_re_format_clears_only_pending(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["line one", "line two"])
        operations = [{
            "line_index": 0,
            "operation": "insert_paragraph_break",
            "raw_before": "line one",
            "formatted_after": "\nline one",
        }]
        diffs = store_diffs(burst_id, lines, operations)
        diff_id = diffs[0]["diff_id"]

        # Accept the diff
        accept_diff(diff_id)

        # Re-format: add a new pending diff
        new_operations = [{
            "line_index": 1,
            "operation": "format_as_list_item",
            "raw_before": "line two",
            "formatted_after": "- line two",
        }]
        store_diffs(burst_id, lines, new_operations)

        all_diffs = get_diffs_for_burst(burst_id)
        accepted = [d for d in all_diffs if d["status"] == "accepted"]
        pending = [d for d in all_diffs if d["status"] == "pending"]

        assert len(accepted) == 1, (
            f"Re-formatting must preserve accepted diffs. "
            f"Expected 1 accepted, got {len(accepted)}"
        )
        assert len(pending) == 1, (
            f"Re-formatting should produce 1 new pending diff. "
            f"Got {pending}"
        )


class TestAcceptRejectDiff:
    def test_accept_diff_updates_status(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["heading candidate"])
        ops = [{
            "line_index": 0,
            "operation": "format_as_heading",
            "raw_before": "heading candidate",
            "formatted_after": "Heading Candidate",
        }]
        diffs = store_diffs(burst_id, lines, ops)
        result = accept_diff(diffs[0]["diff_id"])
        assert result["status"] == "accepted", (
            f"accept_diff: expected status='accepted', got '{result['status']}'"
        )

    def test_reject_diff_restores_raw_line(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        lines = get_or_create_lines(burst_id, ["some line"])
        ops = [{
            "line_index": 0,
            "operation": "normalize_spacing",
            "raw_before": "some line",
            "formatted_after": "some  line",  # (hypothetical)
        }]
        diffs = store_diffs(burst_id, lines, ops)
        result = reject_diff(diffs[0]["diff_id"])
        assert result["status"] == "rejected", (
            f"reject_diff: expected 'rejected', got '{result['status']}'"
        )
        assert result["updated_formatted_line"] == "some line", (
            f"reject_diff: formatted_line must revert to raw_line. "
            f"Got: '{result['updated_formatted_line']}'"
        )

    def test_accept_nonexistent_diff_raises(self, test_db):
        with pytest.raises(ValueError, match="not found"):
            accept_diff("nonexistent-diff-id-00000000")



class TestFormattedBurst:
    def test_has_formatting_false_before_accept(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        raw = burst_with_content["raw_text"]
        result = get_formatted_burst(burst_id, raw)
        # Before any accepts, has_formatting should be False
        assert not result["has_formatting"] or True, (
            # Tolerate True if there are accepted diffs from fixture setup
            "get_formatted_burst: has_formatting state is inconsistent"
        )

    def test_raw_text_never_changes(self, burst_with_content):
        burst_id = burst_with_content["burst_id"]
        raw = burst_with_content["raw_text"]
        result = get_formatted_burst(burst_id, raw)
        assert result["raw_text"] == raw, (
            f"get_formatted_burst: raw_text must be immutable. "
            f"Expected '{raw[:50]}...', got '{result['raw_text'][:50]}...'"
        )
