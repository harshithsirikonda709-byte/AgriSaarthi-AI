"""
Unit tests for local open-weight Ollama integration in AgriSaarthi AI.
Mocks the Ollama HTTP API (http://localhost:11434) to verify:
  1. Successful model responses
  2. Connection failures & offline handling
  3. Timeouts
  4. Model not found / uninstalled error detection
  5. Bilingual support (Telugu & English)
  6. Integration with conversational ACP chat workflow
  7. Graceful fallback without UI crashing
"""

import io
import json
import urllib.error
from unittest.mock import patch, MagicMock
import pytest

from agrisaarthi.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaResponseError,
    explain_crop_recommendation_with_ollama,
    answer_follow_up_with_ollama,
    ask_missing_info_with_ollama,
)
from agrisaarthi.chat_protocol import (
    process_chat_message,
    reset_session,
    get_session,
)
from agrisaarthi.models import (
    FarmerProfileRequest,
    Season,
    SoilType,
    WaterAvailability,
    RiskTolerance,
)
from agrisaarthi.engine import AgriSaarthiEngine


# =============================================================================
# Helper Fixtures & Mock Responses
# =============================================================================

def make_mock_http_response(status: int, data_dict: dict):
    """Creates a mock urllib response object."""
    body_bytes = json.dumps(data_dict).encode("utf-8")
    resp = MagicMock()
    resp.status = status
    resp.read.return_value = body_bytes
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = None
    return resp


@pytest.fixture
def sample_profile_request():
    return FarmerProfileRequest(
        state="Telangana",
        district="Warangal",
        land_size_acres=4.0,
        soil_type=SoilType.BLACK,
        water_availability=WaterAvailability.MODERATE,
        season=Season.KHARIF,
        budget_inr=100000.0,
        risk_tolerance=RiskTolerance.MODERATE,
    )


# =============================================================================
# 1. OllamaClient Initialization & Configuration Tests
# =============================================================================

def test_ollama_client_custom_and_env_config(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "25.0")

    client = OllamaClient()
    assert client.model == "qwen2.5:0.5b"
    assert client.base_url == "http://127.0.0.1:11434"
    assert client.timeout == 25.0

    # Custom override
    client_custom = OllamaClient(
        base_url="http://custom:11434",
        model="custom-llama",
        timeout=10.0,
    )
    assert client_custom.model == "custom-llama"
    assert client_custom.base_url == "http://custom:11434"
    assert client_custom.timeout == 10.0


# =============================================================================
# 2. Model Availability Checks (Tags Endpoint)
# =============================================================================

def test_check_availability_success():
    client = OllamaClient(model="qwen2.5:0.5b")
    mock_resp = make_mock_http_response(
        200,
        {"models": [{"name": "qwen2.5:0.5b"}, {"name": "llama3.2:1b"}]},
    )

    with patch("urllib.request.urlopen", return_value=mock_resp):
        is_ready, msg = client.check_availability()
        assert is_ready is True
        assert "online" in msg
        assert "qwen2.5:0.5b" in msg


def test_check_availability_model_missing():
    client = OllamaClient(model="qwen2.5:0.5b")
    mock_resp = make_mock_http_response(
        200,
        {"models": [{"name": "mistral:latest"}]},
    )

    with patch("urllib.request.urlopen", return_value=mock_resp):
        is_ready, msg = client.check_availability()
        assert is_ready is False
        assert "not installed" in msg
        assert "ollama pull qwen2.5:0.5b" in msg


def test_check_availability_connection_refused():
    client = OllamaClient()

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        is_ready, msg = client.check_availability()
        assert is_ready is False
        assert "unreachable" in msg or "Connection refused" in msg


# =============================================================================
# 3. Chat Endpoint: Success, Failures, Timeouts
# =============================================================================

def test_ollama_chat_success():
    client = OllamaClient(model="qwen2.5:0.5b")
    mock_resp = make_mock_http_response(
        200,
        {"message": {"role": "assistant", "content": "Wheat is optimal for your alluvial soil in Rabi."}},
    )

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
        reply = client.chat(
            messages=[{"role": "user", "content": "Explain wheat suitability"}],
            system="You are AgriSaarthi AI.",
        )
        assert "Wheat is optimal" in reply

        # Verify request structure
        call_args = mock_url.call_args[0]
        req = call_args[0]
        assert req.get_full_url() == "http://localhost:11434/api/chat"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["model"] == "qwen2.5:0.5b"
        assert payload["stream"] is False
        assert any(m["role"] == "system" for m in payload["messages"])


def test_ollama_chat_timeout():
    client = OllamaClient(timeout=2.0)

    with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
        with pytest.raises(OllamaConnectionError) as exc_info:
            client.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "timed out" in str(exc_info.value)


def test_ollama_chat_model_not_found_404():
    client = OllamaClient(model="nonexistent-model")
    http_error = urllib.error.HTTPError(
        url="http://localhost:11434/api/chat",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=io.BytesIO(b'{"error": "model \'nonexistent-model\' not found"}'),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(OllamaModelNotFoundError) as exc_info:
            client.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "not found in Ollama" in str(exc_info.value)
        assert "ollama pull nonexistent-model" in str(exc_info.value)


def test_ollama_chat_server_error_500():
    client = OllamaClient()
    http_error = urllib.error.HTTPError(
        url="http://localhost:11434/api/chat",
        code=500,
        msg="Internal Server Error",
        hdrs={},
        fp=io.BytesIO(b'{"error": "CUDA out of memory"}'),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(OllamaResponseError) as exc_info:
            client.chat(messages=[{"role": "user", "content": "Hello"}])
        assert "HTTP 500" in str(exc_info.value)


# =============================================================================
# 4. Agricultural Workflow Functions with Grounding
# =============================================================================

def test_explain_crop_recommendation_grounded(sample_profile_request):
    engine_response = AgriSaarthiEngine.execute(sample_profile_request)
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.chat.return_value = (
        "Based on your 4 acres of black soil in Telangana for Kharif season, "
        "Cotton is strongly recommended with an 88/100 suitability score."
    )

    text, err = explain_crop_recommendation_with_ollama(
        profile=sample_profile_request,
        response=engine_response,
        client=mock_client,
        lang="en",
    )
    assert err is None
    assert "Cotton" in text
    assert mock_client.chat.called

    # Ensure context passed to LLM included verified engine figures
    called_prompt = mock_client.chat.call_args[1]["messages"][0]["content"]
    assert "VERIFIED ENGINE OUTPUT FOR FARMER" in called_prompt
    assert "Telangana" in called_prompt
    assert "BLACK" in called_prompt or "Black" in called_prompt
    assert "Cotton" in called_prompt


def test_explain_crop_recommendation_telugu(sample_profile_request):
    engine_response = AgriSaarthiEngine.execute(sample_profile_request)
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.chat.return_value = "మీ తెలంగాణ 4 ఎకరాల నల్ల నేలకు పత్తి అత్యంత అనుకూలమైన పంట."

    text, err = explain_crop_recommendation_with_ollama(
        profile=sample_profile_request,
        response=engine_response,
        client=mock_client,
        lang="te",
    )
    assert err is None
    assert "పత్తి" in text


def test_answer_follow_up_with_ollama(sample_profile_request):
    engine_response = AgriSaarthiEngine.execute(sample_profile_request)
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.chat.return_value = "The estimated net profit for Cotton is ₹28,000/acre under normal conditions."

    text, err = answer_follow_up_with_ollama(
        query="What is the profit for Cotton?",
        profile=sample_profile_request,
        response=engine_response,
        client=mock_client,
        lang="en",
    )
    assert err is None
    assert "profit" in text.lower()


def test_ask_missing_info_with_ollama():
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.chat.return_value = "Namaste! To give you accurate advice, could you please share your soil type and season?"

    text, err = ask_missing_info_with_ollama(
        missing_fields=["soil_type", "season"],
        user_message="I have 3 acres in Andhra Pradesh, budget 50000",
        client=mock_client,
        lang="en",
    )
    assert err is None
    assert "soil type" in text.lower()


# =============================================================================
# 5. E2E Conversational Integration with Graceful Degradation
# =============================================================================

def test_process_chat_message_with_ollama_success():
    sender = "test_farmer_ollama_success"
    reset_session(sender)

    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.check_availability.return_value = (True, "Ollama online")
    mock_client.chat.return_value = (
        "Namaste! For your 5 acres of alluvial soil in Punjab during Rabi, "
        "Wheat is recommended with an estimated cost of ₹16,000/acre."
    )

    prompt = "I have 5 acres of alluvial soil in Punjab with tubewell water for Rabi season, budget 100000"
    reply = process_chat_message(text=prompt, sender=sender, ollama_client=mock_client)

    # Must contain the Ollama identifier tag
    assert "🤖 **[Ollama: qwen2.5:0.5b]**" in reply
    assert "Namaste! For your 5 acres" in reply
    # Must preserve verified structured recommendation
    assert "AgriSaarthi Crop Advisory: Punjab" in reply
    assert "Top Primary Recommendations" in reply
    assert "Wheat" in reply


def test_process_chat_message_with_ollama_failure_graceful_fallback():
    sender = "test_farmer_ollama_offline"
    reset_session(sender)

    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    # Ollama is offline
    mock_client.check_availability.return_value = (
        False,
        "Cannot connect to Ollama at http://localhost:11434 (Connection refused)",
    )

    prompt = "I have 5 acres of alluvial soil in Punjab with tubewell water for Rabi season, budget 100000"
    reply = process_chat_message(text=prompt, sender=sender, ollama_client=mock_client)

    # Must NOT claim response is from Ollama
    assert "🤖 **[Ollama:" not in reply
    # Must explicitly inform the farmer/evaluator that Ollama was unavailable
    assert "⚠️ *[Ollama Notice: Local model 'qwen2.5:0.5b' unavailable" in reply
    # Must preserve the complete verified agricultural recommendation
    assert "AgriSaarthi Crop Advisory: Punjab" in reply
    assert "Wheat" in reply


def test_telugu_follow_up_with_ollama():
    sender = "test_farmer_telugu_ollama"
    reset_session(sender)

    # Turn 1: Deterministic initial recommendation
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.check_availability.return_value = (True, "Ollama online")
    mock_client.chat.return_value = "మీ 4 ఎకరాల పొలానికి పత్తి సాగు అత్యంత లాభదాయకం."

    t1_prompt = "తెలంగాణలో 4 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ సీజన్, బోరు బావి నీరు, బడ్జెట్ 1 లక్ష"
    t1_reply = process_chat_message(text=t1_prompt, sender=sender, ollama_client=mock_client)
    assert "అగ్రిసారథి పంటల సిఫార్సు: Telangana" in t1_reply

    # Turn 2: Follow-up question about cotton
    mock_client.chat.return_value = "పత్తి పంటకు గులాబీ రంగు పురుగు నివారణ కోసం లింగాకర్షక బుట్టలు అమర్చండి."
    t2_reply = process_chat_message(text="పత్తి పురుగుల గురించి చెప్పండి", sender=sender, ollama_client=mock_client)

    assert "🤖 **[Ollama: qwen2.5:0.5b]**" in t2_reply
    assert "గులాబీ రంగు పురుగు" in t2_reply
