"""
Unit and Integration Tests for Structured Crop Problem Diagnostic Workflow.
Tests:
- Identification of crop problem queries (English & Telugu)
- Multi-turn workflow:
  1. Farmer reports symptom (e.g. paddy leaves turning yellow)
  2. Assistant asks max 3 relevant diagnostic questions (crop age, location, water conditions)
  3. Farmer answers
  4. Assistant summarizes causes, evidence, safe next steps, uncertainty warnings
  5. Mandates KVK / agricultural officer physical inspection
- Knowledge layer retrieval (ICAR-IIRR, ICAR-CICR, etc.)
- Fallback for unverified symptoms / unknown crops
- Telugu language multi-turn support
"""

import pytest
from unittest.mock import MagicMock, patch

from agrisaarthi.chat_protocol import (
    process_chat_message,
    get_session,
    reset_session,
    is_crop_problem_query,
)
from agrisaarthi.data.crop_diagnostics import (
    find_matching_crop_disorder,
    CROP_DISORDER_DATABASE,
    CropDisorderReference,
)
from agrisaarthi.ollama_client import OllamaClient


def test_trusted_knowledge_layer_structure():
    """Verify CROP_DISORDER_DATABASE contains required fields and authentic ICAR citations."""
    assert len(CROP_DISORDER_DATABASE) >= 4
    for disorder in CROP_DISORDER_DATABASE:
        assert isinstance(disorder, CropDisorderReference)
        assert disorder.crop_name

        assert disorder.symptom_name
        assert len(disorder.possible_causes) >= 2
        for cause in disorder.possible_causes:
            assert cause.name_en
            assert cause.evidence_en
            assert cause.distinguishing_clues_en

        assert len(disorder.safe_actions) >= 2
        assert len(disorder.follow_up_questions) == 3  # Strictly 3 diagnostic questions
        assert len(disorder.follow_up_questions_te) == 3
        assert disorder.source_name
        assert "ICAR" in disorder.source_name
        assert disorder.source_reference


def test_find_matching_crop_disorder():
    """Verify search finds appropriate disorder reference for common symptoms."""
    # Paddy yellowing
    match1 = find_matching_crop_disorder("My paddy leaves are turning yellow")
    assert match1 is not None
    assert match1.crop_name == "Paddy / Rice"
    assert "yellowing" in match1.symptom_name.lower()

    # Cotton reddening
    match2 = find_matching_crop_disorder("cotton leaves are turning red and curling")
    assert match2 is not None
    assert match2.crop_name == "Cotton"

    # Chilli curl
    match3 = find_matching_crop_disorder("chilli leaf curl upward")
    assert match3 is not None
    assert match3.crop_name == "Chilli"

    # Telugu query
    match4 = find_matching_crop_disorder("వరి ఆకులు పసుపు రంగులోకి మారుతున్నాయి")
    assert match4 is not None
    assert match4.crop_name == "Paddy / Rice"

    # Unknown crop / symptom returns None
    match5 = find_matching_crop_disorder("My avocado tree has purple circles")
    assert match5 is None


def test_is_crop_problem_query_detection():
    """Verify detection distinguishes crop problems from recommendation queries."""
    # Symptom queries
    assert is_crop_problem_query("My paddy leaves are turning yellow")
    assert is_crop_problem_query("Cotton leaf reddening and drying")
    assert is_crop_problem_query("Chilli leaves are curling and stunted")
    assert is_crop_problem_query("వరి ఆకులు పసుపు రంగులోకి మారాయి")
    assert is_crop_problem_query("పత్తిలో ఆకు ముడత తెగులు")

    # Regular recommendation queries should NOT be detected as crop problem
    assert not is_crop_problem_query("5 acres in Telangana, black soil, kharif, budget 50000")
    assert not is_crop_problem_query("recommend crops for rabi season in Punjab")


def test_crop_problem_turn_1_asks_max_3_questions():
    """Turn 1: Farmer reports paddy leaves turning yellow. Assistant asks max 3 questions."""
    sender = "test_farmer_turn1"
    reset_session(sender)

    # Use a dummy mock client that returns a controlled response
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.check_availability.return_value = (True, "Ready")
    mock_client.chat.return_value = "Hello farmer, let us investigate your paddy yellowing. Please tell me the age, where it appears, and recent water."

    response = process_chat_message(
        text="My paddy leaves are turning yellow.",
        sender=sender,
        ollama_client=mock_client,
    )

    session = get_session(sender)
    assert session.active_crop_problem is not None
    assert session.active_crop_problem.get("stage") == "awaiting_answers"
    assert session.active_crop_problem.get("crop") == "Paddy / Rice"

    # Must contain exactly max 3 follow-up diagnostic questions in checklist
    assert "❓ **[Diagnostic Follow-Up Questions (Max 3)]**" in response
    assert "1. **" in response
    assert "2. **" in response
    assert "3. **" in response
    assert "4. **" not in response  # Must never ask more than 3 questions

    # Must include uncertainty warning and KVK recommendation
    assert "Krishi Vigyan Kendra" in response or "KVK" in response
    assert "Do not apply chemical pesticides" in response or "laboratory" in response

    # Must include trusted source reference
    assert "ICAR-IIRR" in response


def test_crop_problem_turn_2_diagnosis_and_safe_actions():
    """Turn 2: Farmer provides answers. Assistant summarizes causes, evidence, and safe actions."""
    sender = "test_farmer_turn2"
    reset_session(sender)

    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.check_availability.return_value = (True, "Ready")
    mock_client.chat.return_value = "Based on your answers, here is the diagnosis synthesis."

    # Turn 1: Farmer reports problem
    process_chat_message(
        text="My paddy leaves are turning yellow.",
        sender=sender,
        ollama_client=mock_client,
    )

    # Turn 2: Farmer answers the 3 questions
    farmer_answers = (
        "1. The crop is 28 days old after transplanting. "
        "2. The yellowing started at the bottom older leaves first. "
        "3. The field was flooded under deep standing water after heavy rains."
    )
    diagnosis_response = process_chat_message(
        text=farmer_answers,
        sender=sender,
        ollama_client=mock_client,
    )

    # Session active problem should now be cleared
    session = get_session(sender)
    assert session.active_crop_problem is None

    # Must contain summarized verified causes and evidence
    assert "🔍 **[Possible Causes Based on Verified Evidence]**" in diagnosis_response
    assert "Nitrogen" in diagnosis_response
    assert "Zinc Deficiency" in diagnosis_response or "Khaira" in diagnosis_response

    assert "Water Stagnation" in diagnosis_response or "Iron Chlorosis" in diagnosis_response

    # Must contain safe next steps (cultural / non-chemical)
    assert "🛡️ **[Safe Next Steps (Cultural & Non-Chemical Management)]**" in diagnosis_response
    assert "drain" in diagnosis_response.lower()

    # Must state uncertainty and mandate KVK / VAO physical sample inspection
    assert "⚠️ **[Uncertainty Warning & Required Expert Inspection]**" in diagnosis_response
    assert "Krishi Vigyan Kendra" in diagnosis_response or "KVK" in diagnosis_response
    assert "laboratory" in diagnosis_response.lower() or "physical verification" in diagnosis_response.lower()

    # Must cite verified agricultural institution
    assert "📚 **[Verified Agricultural Reference]**" in diagnosis_response
    assert "ICAR-IIRR" in diagnosis_response


def test_crop_problem_telugu_flow():
    """Test bilingual support for Telugu farmers reporting crop issues."""
    sender = "test_farmer_telugu"
    reset_session(sender)

    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.check_availability.return_value = (True, "Ready")
    mock_client.chat.return_value = "నమస్కారం రైతు సోదరా, మీ వరి ఆకుల సమస్యను పరిశీలిద్దాం."

    # Turn 1 in Telugu
    response_te = process_chat_message(
        text="నా వరి ఆకులు పసుపు రంగులోకి మారుతున్నాయి",
        sender=sender,
        ollama_client=mock_client,
    )

    assert "❓ **[రోగనిర్ధారణ ప్రశ్నలు (గరిష్టంగా 3)]**" in response_te
    assert "1. **" in response_te
    assert "2. **" in response_te
    assert "3. **" in response_te
    assert "కృషి విజ్ఞాన కేంద్రం" in response_te or "KVK" in response_te

    # Turn 2 in Telugu
    answers_te = "పంట వయస్సు 25 రోజులు, కింది ఆకులు పసుపుబారాయి, నీరు నిలిచి ఉంది"
    diag_te = process_chat_message(
        text=answers_te,
        sender=sender,
        ollama_client=mock_client,
    )

    assert "🔍 **[శాస్త్రీయ ఆధారాల ప్రకారం సాధ్యమైన కారణాలు]**" in diag_te
    assert "🛡️ **[సురక్షిత తక్షణ చర్యలు" in diag_te
    assert "⚠️ **[అనిశ్చితి & తప్పనిసరి నిపుణుల తనిఖీ]**" in diag_te
    assert "కృషి విజ్ఞాన కేంద్రం" in diag_te or "KVK" in diag_te


def test_unsupported_crop_or_symptom_fallback():
    """Test unknown or unsupported crops safely triage without hallucinating fake facts."""
    sender = "test_farmer_unsupported"
    reset_session(sender)

    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.check_availability.return_value = (True, "Ready")
    mock_client.chat.return_value = "We will safely evaluate your plant."

    response = process_chat_message(
        text="My dragonfruit crop has strange black spots and rotting leaves",
        sender=sender,
        ollama_client=mock_client,
    )

    # Must ask max 3 questions
    assert "❓ **[Diagnostic Follow-Up Questions (Max 3)]**" in response
    assert "1. **" in response
    assert "2. **" in response
    assert "3. **" in response
    assert "4. **" not in response

    # Must include uncertainty warning and not invent dosages
    assert "KVK" in response or "Krishi Vigyan Kendra" in response
    assert "chemical" in response.lower() or "laboratory" in response.lower()


def test_cross_crop_generic_symptom_does_not_match_paddy():
    """
    Regression test:
    A generic symptom like 'yellow leaves' on another crop (e.g. Groundnut, Maize)
    must NOT match Paddy / Rice disorders, and must preserve safe fallback triage.
    """
    # 1. Direct lookup checks
    assert find_matching_crop_disorder("My groundnut leaves are turning yellow") is None
    assert find_matching_crop_disorder("Groundnut yellow leaves") is None
    assert find_matching_crop_disorder("వేరుశనగ ఆకులు పసుపు రంగులోకి మారుతున్నాయి") is None

    assert find_matching_crop_disorder("My maize has yellow leaves") is None
    assert find_matching_crop_disorder("Maize leaves turning yellow") is None
    assert find_matching_crop_disorder("మొక్కజొన్న ఆకులు పసుపు రంగులోకి మారుతున్నాయి") is None

    # Token boundary checks ('price' != 'rice', 'చివరి' != 'వరి')
    assert find_matching_crop_disorder("Groundnut price is low and yellow leaves") is None
    assert find_matching_crop_disorder("మొక్కజొన్న చివరి ఆకులు పసుపు రంగులో ఉన్నాయి") is None

    # Paddy + matching symptoms continue working properly
    paddy_en = find_matching_crop_disorder("My paddy leaves are turning yellow")
    assert paddy_en is not None and paddy_en.crop_name == "Paddy / Rice"
    paddy_te = find_matching_crop_disorder("వరి ఆకులు పసుపు రంగులోకి మారుతున్నాయి")
    assert paddy_te is not None and paddy_te.crop_name == "Paddy / Rice"

    # 2. Conversational workflow checks (Groundnut & Maize use safe fallback, not Paddy)
    mock_client = MagicMock(spec=OllamaClient)
    mock_client.model = "qwen2.5:0.5b"
    mock_client.check_availability.return_value = (True, "Ready")
    mock_client.chat.return_value = "Let us safely evaluate your crop symptom."

    for crop_query, sender_id in [
        ("My groundnut leaves are turning yellow", "test_groundnut_yellow"),
        ("My maize leaves are turning yellow", "test_maize_yellow"),
    ]:
        reset_session(sender_id)
        reply = process_chat_message(
            text=crop_query,
            sender=sender_id,
            ollama_client=mock_client,
        )
        session = get_session(sender_id)
        assert session.active_crop_problem is not None
        assert session.active_crop_problem.get("disorder_ref") is None
        assert session.active_crop_problem.get("crop") != "Paddy / Rice"
        assert "Paddy / Rice" not in reply
        assert "ICAR-IIRR" not in reply
        assert "❓ **[Diagnostic Follow-Up Questions (Max 3)]**" in reply
        assert "KVK" in reply or "Krishi Vigyan Kendra" in reply
