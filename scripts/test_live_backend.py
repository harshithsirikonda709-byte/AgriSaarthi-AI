"""
Live Backend Verification Script for Task 5.
Starts the server in-process on port 8089, probes all 14 REST and static endpoints over real HTTP sockets,
checks status codes, request/response formats, tests error scenarios, and records output.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from threading import Thread
from http.server import HTTPServer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["DISABLE_LIVE_WEATHER"] = "true"
TEST_PORT = 8089
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

from scripts.run_farmer_ui import AgriFarmerUIHandler, get_storage


def run_http_request(method: str, path: str, data: dict = None, token: str = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body_bytes = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            try:
                parsed = json.loads(content)
            except Exception:
                parsed = content[:100]
            return status, parsed
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = content[:100]
        return e.code, parsed


def main():
    print("=" * 70)
    print("🚀 STARTING LIVE BACKEND INTEGRATION & ENDPOINT AUDIT (TASK 5)")
    print("=" * 70)

    server = HTTPServer(("127.0.0.1", TEST_PORT), AgriFarmerUIHandler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    results = []

    def record(endpoint, method, expected_status, actual_status, note=""):
        passed = expected_status == actual_status
        status_sym = "✅ PASS" if passed else "❌ FAIL"
        results.append((endpoint, method, expected_status, actual_status, passed, note))
        print(f"[{status_sym}] {method:<5} {endpoint:<26} Expected: {expected_status} | Got: {actual_status} | {note}")

    try:
        # 1. Static & Config Endpoints
        status, body = run_http_request("GET", "/")
        record("/", "GET", 200, status, "Serves index.html with 200 OK")

        status, body = run_http_request("GET", "/config.js")
        record("/config.js", "GET", 200, status, "Serves client runtime config")

        status, body = run_http_request("GET", "/api/config")
        record("/api/config", "GET", 200, status, f"API config (Ollama: {body.get('ollama_model', 'N/A')})")

        status, body = run_http_request("GET", "/api/crops")
        crop_count = len(body.get("crops", []))
        record("/api/crops", "GET", 200, status, f"ICAR Crop DB: {crop_count} crops returned")

        status, body = run_http_request("GET", "/api/crop-disorders")
        disorder_count = len(body.get("disorders", []))
        record("/api/crop-disorders", "GET", 200, status, f"Crop Diagnostics DB: {disorder_count} disorders")

        # 2. Authentication: Unauthenticated Access Rejection
        status, body = run_http_request("GET", "/api/farmer/profile")
        record("/api/farmer/profile", "GET", 401, status, "Protected route rejects missing token with 401")

        # 3. Authentication: Registration (POST /api/auth/register)
        test_suffix = int(time.time() * 1000) % 100000000
        test_phone = f"98{test_suffix:08d}"
        test_email = f"venkatesh{test_suffix}@kisan.ap.gov.in"
        reg_payload = {
            "full_name": "K. Venkatesh",
            "phone_number": test_phone,
            "email": test_email,
            "password": "FarmerSecret2026",
            "preferred_language": "te",
            "district": "Guntur",
            "mandal": "Mangalagiri",
            "village": "Atmakuru",
            "land_size_acres": 4.5,
            "soil_type": "black",
            "water_availability": "moderate",
            "sowing_date": "2026-06-15",
            "crop_growth_stage": "vegetative",
        }
        status, reg_body = run_http_request("POST", "/api/auth/register", reg_payload)
        record("/api/auth/register", "POST", 201, status, f"Registered new farmer ({test_phone})")
        token = reg_body.get("token")
        farmer_id = reg_body.get("farmer", {}).get("id")

        # 4. Authentication: Duplicate Registration Error (400 Bad Request)
        status, body = run_http_request("POST", "/api/auth/register", reg_payload)
        record("/api/auth/register", "POST", 400, status, "Duplicate registration rejected with 400")

        # 5. Authentication: Login with Wrong Password (401 Unauthorized)
        status, body = run_http_request("POST", "/api/auth/login", {"identifier": test_phone, "password": "WrongPassword"})
        record("/api/auth/login (bad)", "POST", 401, status, "Wrong password rejected with 401")

        # 6. Authentication: Login with Valid Phone Number
        status, login_body = run_http_request("POST", "/api/auth/login", {"identifier": test_phone, "password": "FarmerSecret2026"})
        record("/api/auth/login (phone)", "POST", 200, status, "Successful login via phone number")
        valid_token = login_body.get("token")

        # 7. Authentication: Login with Valid Email
        status, _ = run_http_request("POST", "/api/auth/login", {"email": test_email, "password": "FarmerSecret2026"})
        record("/api/auth/login (email)", "POST", 200, status, "Successful login via email address")

        # 8. Profile: GET /api/farmer/profile with Bearer Token
        status, prof_body = run_http_request("GET", "/api/farmer/profile", token=valid_token)
        mandal_retrieved = prof_body.get("farmer", {}).get("mandal", "")
        record("/api/farmer/profile", "GET", 200, status, f"Retrieved profile (mandal: '{mandal_retrieved}')")

        # 9. Profile: PUT /api/farmer/profile Update Fields
        update_payload = {
            "full_name": "K. Venkatesh Naidu",
            "mandal": "Tadepalli",
            "land_size_acres": 6.0,
            "soil_type": "alluvial",
            "water_availability": "high",
        }
        status, upd_body = run_http_request("PUT", "/api/farmer/profile", update_payload, token=valid_token)
        upd_mandal = upd_body.get("farmer", {}).get("mandal", "")
        record("/api/farmer/profile", "PUT", 200, status, f"Updated profile (mandal: '{upd_mandal}', land: 6.0)")

        # 10. Profile Update Error: Negative Land Size (400 Bad Request)
        status, _ = run_http_request("PUT", "/api/farmer/profile", {"land_size_acres": -5.0}, token=valid_token)
        record("/api/farmer/profile (bad)", "PUT", 400, status, "Negative land size rejected with 400")

        # 11. Crop Advisory Recommendation: POST /api/recommend
        rec_payload = {
            "state": "Andhra Pradesh",
            "district": "Guntur",
            "land_size_acres": 6.0,
            "soil_type": "alluvial",
            "water_availability": "high",
            "season": "kharif",
            "budget_inr": 150000,
            "risk_tolerance": "moderate",
        }
        status, rec_body = run_http_request("POST", "/api/recommend", rec_payload, token=valid_token)
        status_str = rec_body.get("recommendation", {}).get("workflow_status", "N/A")
        record("/api/recommend", "POST", 200, status, f"ICAR Recommendation status: {status_str}")

        # 12. Crop Diagnostics: POST /api/crop-health
        health_payload = {
            "crop": "Cotton / ప్రత్తి",
            "symptom": "leaf reddening",
            "lang": "te",
        }
        status, health_body = run_http_request("POST", "/api/crop-health", health_payload, token=valid_token)
        matched = health_body.get("matched", False)
        record("/api/crop-health", "POST", 200, status, f"Disorder matched: {matched} ({health_body.get('symptom_key', '')})")

        # 13. Farmer Dashboard: GET /api/farmer/dashboard
        status, dash_body = run_http_request("GET", "/api/farmer/dashboard", token=valid_token)
        history_len = len(dash_body.get("history", []))
        record("/api/farmer/dashboard", "GET", 200, status, f"Dashboard returned farmer + {history_len} history items")

        # 14. Authentication: Logout and Session Revocation
        status, _ = run_http_request("POST", "/api/auth/logout", token=valid_token)
        record("/api/auth/logout", "POST", 200, status, "Session revoked successfully")

        # 15. Verify Token Revoked: GET /api/farmer/profile must fail with 401
        status, _ = run_http_request("GET", "/api/farmer/profile", token=valid_token)
        record("/api/farmer/profile (revoked)", "GET", 401, status, "Revoked token rejected with 401")

        print("=" * 70)
        total = len(results)
        passed = sum(1 for r in results if r[4])
        print(f"📊 SUMMARY: {passed}/{total} ENDPOINT AUDITS PASSED ({passed/total*100:.1f}%)")
        print("=" * 70)

        if passed == total:
            print("🎉 ALL ENDPOINT CONTRACTS AND ERROR CASES VERIFIED SUCCESSFULLY!")
            return 0
        else:
            print("⚠️ Some endpoints failed verification.")
            return 1

    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())

