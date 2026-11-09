"""
Unit tests for the farmer voice demo web server (scripts/run_farmer_ui.py).
"""

import json
from io import BytesIO
from unittest.mock import MagicMock

from scripts.run_farmer_ui import AgriFarmerUIHandler


def test_ui_server_get_index():
    """GET / should serve index.html with 200 OK and text/html."""
    handler = AgriFarmerUIHandler.__new__(AgriFarmerUIHandler)
    handler.path = "/"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = BytesIO()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    handler.send_header.assert_called_with("Content-Type", "text/html; charset=utf-8")
    content = handler.wfile.getvalue().decode("utf-8")
    assert "<title>AgriSaarthi AI" in content
    assert "SpeechRecognition" in content or "webkitSpeechRecognition" in content


def test_ui_server_post_chat_telugu():
    """POST /api/chat should accept Telugu text and return JSON with Telugu recommendation."""
    handler = AgriFarmerUIHandler.__new__(AgriFarmerUIHandler)
    handler.path = "/api/chat"

    payload = json.dumps({
        "text": "తెలంగాణలో 4 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ సీజన్, బోరు బావి నీరు, బడ్జెట్ 1 లక్ష",
        "sender": "test_web_telugu_user"
    }).encode("utf-8")

    handler.headers = {"Content-Length": str(len(payload))}
    handler.rfile = BytesIO(payload)
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = BytesIO()

    handler.do_POST()

    handler.send_response.assert_called_with(200)
    response_body = json.loads(handler.wfile.getvalue().decode("utf-8"))
    assert "reply" in response_body
    reply = response_body["reply"]
    assert "అగ్రిసారథి పంటల సిఫార్సు: Telangana" in reply
    assert "అత్యంత అనుకూలమైన ప్రధాన పంటలు" in reply


def test_voice_recognition_frontend_configuration():
    """Verify that index.html contains correct speech recognition parameters and error handlers."""
    handler = AgriFarmerUIHandler.__new__(AgriFarmerUIHandler)
    handler.path = "/"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = BytesIO()

    handler.do_GET()
    html = handler.wfile.getvalue().decode("utf-8")

    # 1. te-IN and en-IN locales configured
    assert "te-IN" in html
    assert "en-IN" in html

    # 2. continuous = true to prevent premature cutoff during pauses
    assert "rec.continuous = true" in html or "continuous = true" in html

    # 3. isFinal transcript handling to prevent duplicate / overwritten transcripts
    assert "res.isFinal" in html or "result.isFinal" in html

    # 4. Error handlers for not-allowed, no-speech, network, audio-capture
    assert "not-allowed" in html
    assert "no-speech" in html
    assert "network" in html
    assert "audio-capture" in html

    # 5. Stop listening controls and TTS buttons preserved
    assert "stopSpeechRecognition" in html
    assert "speakMessage" in html
    assert "stopSpeech" in html


def test_voice_recording_states_and_input_preservation():
    """Verify that index.html implements listening, processing, unavailable states and input editing."""
    handler = AgriFarmerUIHandler.__new__(AgriFarmerUIHandler)
    handler.path = "/"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = BytesIO()

    handler.do_GET()
    html = handler.wfile.getvalue().decode("utf-8")

    # 1. Clear recording states: Listening, Processing, and Microphone unavailable
    assert "listening" in html
    assert "processing" in html
    assert "unavailable" in html
    assert "setVoiceState" in html

    # 2. Mic button must have type="button" to prevent accidental form submission
    assert 'type="button" id="mic-btn"' in html or 'id="mic-btn" class="mic-button"' in html
    assert 'type="button"' in html

    # 3. Interim results and pre-typed input preservation
    assert "interimChunk" in html or "interimResults" in html
    assert "baseInputText" in html

    # 4. Stop button stops speech recognition correctly
    assert "stopSpeechRecognition()" in html


def test_theme_and_agricultural_dashboard_elements():
    """Verify that index.html features the agricultural palette, crop advisory, crop health, ACP and Ollama integration."""
    handler = AgriFarmerUIHandler.__new__(AgriFarmerUIHandler)
    handler.path = "/"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.wfile = BytesIO()

    handler.do_GET()
    html = handler.wfile.getvalue().decode("utf-8")

    # 1. Forest green, leaf green, warm cream palette
    assert "--forest-800" in html or "--primary-green" in html
    assert "--leaf-500" in html or "--leaf-600" in html
    assert "--cream-bg" in html or "--bg-cream" in html

    # 2. Branding and Core features preserved
    assert "AgriSaarthi AI" in html
    assert "Crop Advisory" in html
    assert "Crop Health" in html
    assert "ACP v0.3.0" in html
    assert "Ollama" in html


def _invoke_handler(method: str, path: str, body: dict = None, headers: dict = None):
    """Helper to invoke AgriFarmerUIHandler in-memory without opening network sockets."""
    handler = AgriFarmerUIHandler.__new__(AgriFarmerUIHandler)
    handler.path = path
    req_headers = dict(headers or {})
    if body is not None:
        raw_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req_headers["Content-Length"] = str(len(raw_bytes))
        handler.rfile = BytesIO(raw_bytes)
    else:
        handler.rfile = BytesIO(b"")
    handler.headers = req_headers
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.send_error = MagicMock()
    handler.wfile = BytesIO()

    if method == "GET":
        handler.do_GET()
    elif method == "POST":
        handler.do_POST()
    elif method == "PUT":
        handler.do_PUT()
    return handler


def test_all_nine_portal_pages_and_static_assets():
    """Verify all 9 required farmer portal pages exist in index.html and static assets serve cleanly."""
    h_index = _invoke_handler("GET", "/")
    html = h_index.wfile.getvalue().decode("utf-8")

    for page_id in (
        'id="page-home"',
        'id="page-login"',
        'id="page-register"',
        'id="page-dashboard"',
        'id="page-advisory"',
        'id="page-health"',
        'id="page-weather"',
        'id="page-voice"',
        'id="page-profile"',
    ):
        assert page_id in html, f"Missing required page section: {page_id}"

    # Verify external config and static assets
    h_cfg = _invoke_handler("GET", "/config.js")
    h_cfg.send_response.assert_called_with(200)
    assert "window.AGRISAARTHI_CONFIG" in h_cfg.wfile.getvalue().decode("utf-8")

    h_css = _invoke_handler("GET", "/css/portal.css")
    h_css.send_response.assert_called_with(200)

    h_js = _invoke_handler("GET", "/js/portal.js")
    h_js.send_response.assert_called_with(200)

    # Verify path traversal protection blocks access outside web/
    h_traversal = _invoke_handler("GET", "/css/../../.env")
    h_traversal.send_error.assert_called_with(403, "Forbidden")

    # Verify root with query string and SPA direct routes serve index.html (200 OK)
    for spa_path in ("/?lang=te", "/home", "/login", "/register", "/dashboard", "/advisory", "/health", "/weather", "/voice", "/profile"):
        h_spa = _invoke_handler("GET", spa_path)
        h_spa.send_response.assert_called_with(200)

    # Verify /favicon.ico returns 204 No Content instead of 404
    h_fav = _invoke_handler("GET", "/favicon.ico")
    h_fav.send_response.assert_called_with(204)


def test_farmer_auth_onboarding_dashboard_and_logout_flow(tmp_path, monkeypatch):
    """Verify secure registration, PBKDF2 hashing, login, protected routes, profile setup, history, and logout."""
    db_file = str(tmp_path / "test_farmers.db")
    monkeypatch.setenv("AGRI_DB_PATH", db_file)
    monkeypatch.setenv("DISABLE_LIVE_WEATHER", "true")

    # 1. Protected route rejects unauthenticated access with 401
    h_unauth = _invoke_handler("GET", "/api/farmer/dashboard")
    h_unauth.send_response.assert_called_with(401)

    # 2. Register a new farmer
    h_reg = _invoke_handler(
        "POST",
        "/api/auth/register",
        body={
            "full_name": "Rama Rao",
            "identifier": "9876543210",
            "password": "securePassword123",
            "preferred_language": "te",
        },
    )
    h_reg.send_response.assert_called_with(201)
    reg_data = json.loads(h_reg.wfile.getvalue().decode("utf-8"))
    token = reg_data["token"]
    assert token
    assert reg_data["farmer"]["full_name"] == "Rama Rao"
    assert reg_data["farmer"]["profile_completed"] is False
    assert "password" not in reg_data["farmer"]
    assert "password_hash" not in reg_data["farmer"]

    # 3. Duplicate registration is rejected with 400
    h_dup = _invoke_handler(
        "POST",
        "/api/auth/register",
        body={
            "full_name": "Rama Rao",
            "identifier": "9876543210",
            "password": "securePassword123",
        },
    )
    h_dup.send_response.assert_called_with(400)

    # 4. Wrong password login is rejected with 401
    h_bad_login = _invoke_handler(
        "POST",
        "/api/auth/login",
        body={"identifier": "9876543210", "password": "wrongPassword"},
    )
    h_bad_login.send_response.assert_called_with(401)

    # 5. Valid login succeeds with 200
    h_login = _invoke_handler(
        "POST",
        "/api/auth/login",
        body={"identifier": "9876543210", "password": "securePassword123"},
    )
    h_login.send_response.assert_called_with(200)
    login_token = json.loads(h_login.wfile.getvalue().decode("utf-8"))["token"]
    auth_headers = {"Authorization": f"Bearer {login_token}"}

    # 6. Complete farm profile setup (PUT /api/farmer/profile)
    h_prof = _invoke_handler(
        "PUT",
        "/api/farmer/profile",
        body={
            "state": "Telangana",
            "district": "Warangal",
            "village": "Parkal",
            "land_size_acres": 4.0,
            "soil_type": "black",
            "water_availability": "moderate",
            "season": "kharif",
            "budget_inr": 100000,
            "risk_tolerance": "moderate",
        },
        headers=auth_headers,
    )
    h_prof.send_response.assert_called_with(200)
    prof_data = json.loads(h_prof.wfile.getvalue().decode("utf-8"))["farmer"]
    assert prof_data["profile_completed"] is True
    assert prof_data["state"] == "Telangana"
    assert prof_data["district"] == "Warangal"
    assert prof_data["land_size_acres"] == 4.0

    # 7. Run structured crop recommendation (/api/recommend) and crop health (/api/crop-health)
    h_rec = _invoke_handler(
        "POST",
        "/api/recommend",
        body={
            "state": "Telangana",
            "district": "Warangal",
            "land_size_acres": 4.0,
            "soil_type": "black",
            "water_availability": "moderate",
            "season": "kharif",
            "budget_inr": 100000,
            "risk_tolerance": "moderate",
        },
        headers=auth_headers,
    )
    h_rec.send_response.assert_called_with(200)
    rec_json = json.loads(h_rec.wfile.getvalue().decode("utf-8"))
    assert rec_json["recommendation"]["workflow_status"] == "SUCCESS"
    assert len(rec_json["recommendation"]["primary_recommendations"]) >= 1

    h_health = _invoke_handler(
        "POST",
        "/api/crop-health",
        body={
            "crop": "Paddy / Rice",
            "symptom": "yellow leaves",
            "field_notes": "25 days after transplanting, bottom leaves yellow",
            "lang": "te",
        },
        headers=auth_headers,
    )
    h_health.send_response.assert_called_with(200)
    health_json = json.loads(h_health.wfile.getvalue().decode("utf-8"))
    assert health_json["matched"] is True
    assert health_json["symptom_key"] == "paddy_yellowing"

    # 8. Verify Farmer Dashboard returns profile, recorded advisory history, and honest weather state
    h_dash = _invoke_handler("GET", "/api/farmer/dashboard", headers=auth_headers)
    h_dash.send_response.assert_called_with(200)
    dash_json = json.loads(h_dash.wfile.getvalue().decode("utf-8"))
    assert dash_json["farmer"]["full_name"] == "Rama Rao"
    assert len(dash_json["history"]) == 2
    assert dash_json["weather"]["available"] is False  # Honest unavailable state when DISABLE_LIVE_WEATHER=true

    # 9. Logout revokes session token
    h_logout = _invoke_handler("POST", "/api/auth/logout", headers=auth_headers)
    h_logout.send_response.assert_called_with(200)

    h_after = _invoke_handler("GET", "/api/farmer/profile", headers=auth_headers)
    h_after.send_response.assert_called_with(401)



