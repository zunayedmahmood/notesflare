import json

from services.formatting.usage_learning_service import record_diff_decision
from services.formatting.stabilisation_profile_service import reset_profile_cache


def test_usage_learning_updates_profile_from_accept_only(test_db, tmp_path, monkeypatch):
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps({"version": 1, "formatting_preferences": {}}), encoding="utf-8")
    monkeypatch.setenv("NOTESFLARE_STABILISATION_PROFILE", str(profile_path))
    reset_profile_cache()

    accepted_diff = {
        "diff_id": "accepted-1",
        "burst_id": 1,
        "line_id": "line-1",
        "operation": "insert_line_break",
        "raw_before": "need mext interview and api contract",
        "formatted_after": "need:\n- mext interview\n- api contract",
    }
    rejected_diff = {
        "diff_id": "rejected-1",
        "burst_id": 1,
        "line_id": "line-2",
        "operation": "insert_line_break",
        "raw_before": "need poisoned phrase and db migration",
        "formatted_after": "need:\n- poisoned phrase\n- db migration",
    }

    accepted_event = record_diff_decision(accepted_diff, "accepted")
    rejected_event = record_diff_decision(rejected_diff, "rejected")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    learned_phrases = set(profile.get("continuous_list_item_phrases", []))

    assert accepted_event["learned"] is True
    assert rejected_event["learned"] is False
    assert "mext interview" in learned_phrases
    assert "api contract" in learned_phrases
    assert "poisoned phrase" not in learned_phrases

    rows = test_db.execute("SELECT decision, learned FROM stabilisation_usage_events ORDER BY id").fetchall()
    assert [dict(row) for row in rows] == [
        {"decision": "accepted", "learned": 1},
        {"decision": "rejected", "learned": 0},
    ]
