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

