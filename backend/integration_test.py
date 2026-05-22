# backend/integration_test.py

import urllib.request
import urllib.error
import json
import sqlite3
import os
import time
from datetime import datetime, timezone, timedelta

BASE_URL = "http://127.0.0.1:8000/api"
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "notesflare.db"))

def make_request(path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_body = str(e)
        return e.code, err_body

def print_result(name, success, detail=""):
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    status = "PASS" if success else "FAIL"
    print(f"[{color}{status}{reset}] {name} {f'({detail})' if detail else ''}")

def run_tests():
    print("\n" + "="*60)
    print("  NotesFlare — Automated Integration & Data Flow Tests")
    print("="*60 + "\n")

    # TEST 1: Health Liveness
    code, body = make_request("/health")
    test1_success = (code == 200 and body.get("status") == "ok")
    print_result("TEST 1: Health Liveness", test1_success, f"Status: {code}")
    if not test1_success: return

    # Generate a unique name for this test run to avoid unique constraint issues
    run_id = int(time.time())
    flareon_name = f"Test Flareon {run_id}"

    # TEST 2: Create a Flareon
    code, body = make_request("/flareons", method="POST", data={"name": flareon_name})
    test2_success = (code == 201 and body.get("name") == flareon_name)
    flareon_id = body.get("id") if test2_success else None
    print_result("TEST 2: Create a Flareon", test2_success, f"ID: {flareon_id}, Name: '{flareon_name}'")
    if not test2_success: return

    # TEST 3: Duplicate Name Validation
    code, body = make_request("/flareons", method="POST", data={"name": flareon_name})
    test3_success = (code == 400 and "already exists" in body.get("detail", "").lower())
    print_result("TEST 3: Duplicate Name Check", test3_success, f"Returned code: {code}, Detail: '{body.get('detail')}'")

    # TEST 4: Open Flareon (Autoresolves active burst)
    code, body = make_request(f"/flareons/{flareon_id}")
    test4_success = (code == 200 and len(body.get("bursts", [])) == 1)
    active_burst_id = body.get("active_burst_id") if test4_success else None
    print_result("TEST 4: Open Flareon & Resolve Burst", test4_success, f"Active Burst ID: {active_burst_id}")
    if not test4_success: return

    # TEST 5: Verify App State Singleton
    code, body = make_request("/state")
    test5_success = (code == 200 and body.get("last_opened_flareon_id") == flareon_id and body.get("last_opened_burst_id") == active_burst_id)
    print_result("TEST 5: App State Persistence", test5_success, f"Last Opened Flareon ID: {body.get('last_opened_flareon_id')}")

    # TEST 6: Autosave Content
    save_content = "Integration testing our beautiful debounced autosave feature."
    code, body = make_request("/save", method="POST", data={"burst_id": active_burst_id, "content": save_content})
    test6_success = (code == 200 and body.get("success") is True)
    print_result("TEST 6: Autosave Content to Burst", test6_success, f"Save successful: {body.get('success')}")

    # TEST 7: 30-Minute Session Continuity (Simulate < 30 minutes)
    code, body = make_request(f"/flareons/{flareon_id}")
    test7_success = (code == 200 and body.get("active_burst_id") == active_burst_id)
    print_result("TEST 7: Continuity Check (< 30 minutes)", test7_success, f"Kept existing burst ID: {body.get('active_burst_id')}")

    # TEST 8: 30-Minute Session Continuity (Simulate > 30 minutes)
    try:
        conn = sqlite3.connect(DB_PATH)
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
        conn.execute("UPDATE bursts SET updated_at = ? WHERE id = ?", (past_time, active_burst_id))
        conn.commit()
        conn.close()
        
        # Open Flareon again, it should resolve to a new burst ID!
        code, body = make_request(f"/flareons/{flareon_id}")
        new_active_burst_id = body.get("active_burst_id")
        test8_success = (code == 200 and new_active_burst_id != active_burst_id and len(body.get("bursts", [])) == 2)
        print_result("TEST 8: Continuity Check (> 30 minutes)", test8_success, f"Generated new burst ID: {new_active_burst_id}")
    except Exception as e:
        print_result("TEST 8: Continuity Check (> 30 minutes)", False, f"Error: {e}")

    # TEST 9: List Flareons Sorting
    other_flareon_name = f"Test Flareon Other {run_id}"
    _, other_flareon = make_request("/flareons", method="POST", data={"name": other_flareon_name})
    other_flareon_id = other_flareon.get("id")
    make_request(f"/flareons/{other_flareon_id}")
    
    code, body = make_request("/flareons")
    flareons_list = body.get("flareons", [])
    test9_success = (code == 200 and len(flareons_list) >= 2 and flareons_list[0].get("id") == other_flareon_id)
    print_result("TEST 9: List Flareons Sorting (Recently Opened)", test9_success, f"Top Flareon: '{flareons_list[0].get('name')}'")

    # TEST 10: Session Resume
    code, body = make_request("/session/resume")
    test10_success = (code == 200 and body.get("has_session") is True and body.get("flareon", {}).get("id") == other_flareon_id)
    print_result("TEST 10: Session Resume Flow", test10_success, f"Resumed Flareon ID: {body.get('flareon', {}).get('id')}")

    # TEST 11: Burst Append
    res_burst_id = body.get("burst_id")
    code, body = make_request("/burst/append", method="POST", data={"burst_id": res_burst_id, "text": "Appending V1.1 continuous data."})
    # Note: because other_flareon was just opened/created, sequence_number should be 0
    test11_success = (code == 200 and body.get("success") is True and body.get("sequence_number") == 0)
    print_result("TEST 11: V1.1 Append Chunk", test11_success, f"Assigned seq: {body.get('sequence_number')}")

    # TEST 12: Switch Flareon
    code, body = make_request(f"/session/switch/{flareon_id}")
    test12_success = (code == 200 and body.get("flareon", {}).get("id") == flareon_id)
    print_result("TEST 12: Switch Flareon", test12_success, f"Switched to Flareon: '{body.get('flareon', {}).get('name')}'")

    print("\n" + "="*60)
    print("  All Integration Tests Complete.")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_tests()
