"""
Unit tests for Agent Chat Protocol (ACP v0.3.0) integration in AgriSaarthi AI.
"""

import asyncio
from uuid import uuid4
from uagents import Agent
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    StartSessionContent,
    EndSessionContent,
    chat_protocol_spec,
)

from agrisaarthi.chat_protocol import (
    create_chat_protocol,
    parse_chat_query,
    format_acp_recommendation,
    process_chat_message,
    reset_session,
    get_session,
)
from agrisaarthi.agent import create_agent
from agrisaarthi.models import (
    FarmerProfileRequest,
    Season,
    SoilType,
    WaterAvailability,
)
from agrisaarthi.engine import AgriSaarthiEngine


def test_acp_protocol_verification_and_inclusion():
    """Verify that chat_proto satisfies chat_protocol_spec and can be included in an Agent."""
    chat_proto = create_chat_protocol(engine_cls=AgriSaarthiEngine)

    # Must pass protocol interaction verification
    assert chat_proto.verify() is True
    assert chat_proto.canonical_name == "AgentChatProtocol:0.3.0"

    test_agent = create_agent(
        name="test_acp_agent",
        seed="test_acp_seed_123",
        port=8044,
        endpoint="http://127.0.0.1:8044/submit",
        enable_mailbox=False,
        publish_manifest=False,
    )

    # Ensure protocol digest is registered in agent
    assert any("AgentChatProtocol" in p.canonical_name for p in test_agent.protocols.values())


def test_parse_valid_json_chat_query():
    """Valid JSON payload in ACP message should parse directly into FarmerProfileRequest."""
    json_text = """
    {
        "state": "Punjab",
        "district": "Ludhiana",
        "land_size_acres": 5.0,
        "soil_type": "alluvial",
        "water_availability": "moderate",
        "season": "rabi",
        "budget_inr": 100000
    }
    """
    req, err = parse_chat_query(json_text)
    assert req is not None
    assert err == ""
    assert req.state == "Punjab"
    assert req.season == Season.RABI
    assert req.soil_type == SoilType.ALLUVIAL
    assert req.land_size_acres == 5.0
    assert req.budget_inr == 100000.0


def test_parse_markdown_fenced_json_chat_query():
    """JSON inside markdown code blocks (typical from LLMs or web clients) should parse cleanly."""
    md_text = """Here is my farm profile:
    ```json
    {
        "state": "Rajasthan",
        "land_size_acres": 6.0,
        "soil_type": "sandy_loam",
        "water_availability": "low",
        "season": "kharif",
        "budget_inr": 65000
    }
    ```
    Please recommend crops.
    """
    req, err = parse_chat_query(md_text)
    assert req is not None
    assert err == ""
    assert req.state == "Rajasthan"
    assert req.soil_type == SoilType.SANDY_LOAM
    assert req.season == Season.KHARIF


def test_parse_natural_language_chat_query():
    """Natural language query with conversational parameters should be extracted correctly."""
    nl_text = (
        "Hello AgriSaarthi, I am a farmer in Maharashtra. I have 4 acres of black soil "
        "with moderate water availability. I plan to sow during Kharif season with a budget of ₹120,000."
    )
    req, err = parse_chat_query(nl_text)
    assert req is not None
    assert err == ""
    assert req.state == "Maharashtra"
    assert req.land_size_acres == 4.0
    assert req.soil_type == SoilType.BLACK
    assert req.water_availability == WaterAvailability.MODERATE
    assert req.season == Season.KHARIF
    assert req.budget_inr == 120000.0


def test_parse_incomplete_chat_query_returns_guidance():
    """Incomplete text (missing budget and soil) should return a helpful guidance response."""
    incomplete_text = "I have 5 acres in Punjab for Kharif season."
    req, err = parse_chat_query(incomplete_text)
    assert req is None
    assert "Incomplete Farm Profile" in err
    assert "soil_type" in err
    assert "budget_inr" in err


def test_parse_malformed_json_returns_error_message():
    """Malformed JSON syntax should return diagnostic feedback with example syntax."""
    bad_json = '{"state": "Punjab", "land_size_acres": }'
    req, err = parse_chat_query(bad_json)
    assert req is None
    assert "Malformed JSON syntax" in err
    assert "Example JSON format" in err


def test_format_acp_recommendation_output():
    """Engine response formatted for ACP should contain markdown headings, crop cards, and advisories."""
    req = FarmerProfileRequest(
        state="Punjab",
        land_size_acres=5.0,
        soil_type=SoilType.ALLUVIAL,
        water_availability=WaterAvailability.MODERATE,
        season=Season.RABI,
        budget_inr=110000.0,
    )
    resp = AgriSaarthiEngine.execute(req)
    formatted = format_acp_recommendation(resp, req)

    assert "### 🌾 AgriSaarthi Crop Advisory: Punjab" in formatted
    assert "Top Primary Recommendations" in formatted
    assert "Wheat" in formatted or "Mustard" in formatted
    assert "Multi-Step Decision Reasoning" in formatted
    assert "Agronomic Advisory" in formatted


class MockContext:
    """Mock context to capture messages sent by protocol handlers."""
    def __init__(self):
        self.sent_messages = []
        self.logger = self

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def exception(self, msg):
        pass

    async def send(self, destination: str, message):
        self.sent_messages.append((destination, message))


def test_e2e_acp_chat_handler_flow():
    """Verify that handle_chat_message sends ChatAcknowledgement and response ChatMessage."""
    chat_proto = create_chat_protocol(engine_cls=AgriSaarthiEngine)

    # Extract the ChatMessage handler from the protocol
    chat_model_digest = list(chat_proto.signed_message_handlers.keys())[0]
    handler = chat_proto.signed_message_handlers[chat_model_digest]

    incoming_msg_id = uuid4()
    incoming_chat = ChatMessage(
        msg_id=incoming_msg_id,
        content=[
            TextContent(
                text='{"state": "Punjab", "land_size_acres": 5.0, "soil_type": "alluvial", '
                     '"water_availability": "moderate", "season": "rabi", "budget_inr": 100000}'
            )
        ],
    )

    ctx = MockContext()
    sender_addr = "agent1q_sender_test_address"

    asyncio.run(handler(ctx, sender_addr, incoming_chat))

    # Expect exactly two sent messages:
    # 1. ChatAcknowledgement with matching acknowledged_msg_id
    # 2. ChatMessage with formatted recommendation
    assert len(ctx.sent_messages) == 2

    # Verify message 1: ChatAcknowledgement
    ack_dest, ack_msg = ctx.sent_messages[0]
    assert ack_dest == sender_addr
    assert isinstance(ack_msg, ChatAcknowledgement)
    assert ack_msg.acknowledged_msg_id == incoming_msg_id

    # Verify message 2: ChatMessage response
    reply_dest, reply_msg = ctx.sent_messages[1]
    assert reply_dest == sender_addr
    assert isinstance(reply_msg, ChatMessage)
    reply_text = reply_msg.text()
    assert "AgriSaarthi Crop Advisory" in reply_text
    assert "Wheat" in reply_text or "Mustard" in reply_text


def test_acp_start_session_lifecycle():
    """StartSessionContent in ACP should return a welcome guidance message."""
    chat_proto = create_chat_protocol(engine_cls=AgriSaarthiEngine)
    chat_model_digest = list(chat_proto.signed_message_handlers.keys())[0]
    handler = chat_proto.signed_message_handlers[chat_model_digest]

    msg_id = uuid4()
    session_msg = ChatMessage(msg_id=msg_id, content=[StartSessionContent()])
    ctx = MockContext()

    asyncio.run(handler(ctx, "agent_client", session_msg))

    assert len(ctx.sent_messages) == 2
    assert isinstance(ctx.sent_messages[0][1], ChatAcknowledgement)
    reply_text = ctx.sent_messages[1][1].text()
    assert "Namaste! I am AgriSaarthi AI" in reply_text


def test_acp_end_session_lifecycle():
    """EndSessionContent in ACP should acknowledge and send a polite closure."""
    chat_proto = create_chat_protocol(engine_cls=AgriSaarthiEngine)
    chat_model_digest = list(chat_proto.signed_message_handlers.keys())[0]
    handler = chat_proto.signed_message_handlers[chat_model_digest]

    msg_id = uuid4()
    end_msg = ChatMessage(msg_id=msg_id, content=[EndSessionContent()])
    ctx = MockContext()

    asyncio.run(handler(ctx, "agent_client", end_msg))

    assert len(ctx.sent_messages) == 2
    assert isinstance(ctx.sent_messages[0][1], ChatAcknowledgement)
    reply_text = ctx.sent_messages[1][1].text()
    assert "Thank you for consulting" in reply_text


def test_water_availability_limited_irrigation_maps_to_low():
    """Verify that 'limited irrigation' faithfully maps to WaterAvailability.LOW without silent coercion."""
    query_limited = (
        "I have 5 acres of sandy loam soil in Rajasthan with limited irrigation "
        "for Kharif season, budget 60000."
    )
    req, err = parse_chat_query(query_limited)
    assert req is not None
    assert err == ""
    assert req.water_availability == WaterAvailability.LOW

    # Also verify 'water is limited'
    query_water_limited = (
        "I am in Punjab with 4 acres alluvial soil, water is limited, rabi season, budget 80000"
    )
    req2, _ = parse_chat_query(query_water_limited)
    assert req2 is not None
    assert req2.water_availability == WaterAvailability.LOW

    # Verify 'tubewell' maps to MODERATE
    query_tubewell = (
        "I have 3 acres alluvial soil in Haryana with tubewell water for rabi season, budget 90000"
    )
    req3, _ = parse_chat_query(query_tubewell)
    assert req3 is not None
    assert req3.water_availability == WaterAvailability.MODERATE

    # Verify 'canal water' maps to HIGH
    query_canal = (
        "I have 4 acres clayey soil in Punjab with canal water for kharif season, budget 100000"
    )
    req4, _ = parse_chat_query(query_canal)
    assert req4 is not None
    assert req4.water_availability == WaterAvailability.HIGH


def test_source_and_live_data_query_answers_without_requesting_farm_profile():
    """
    Asking whether live weather or mandi prices were retrieved should answer directly
    without returning 'Incomplete Farm Profile'.
    """
    reset_session("test_user_source_probe")
    response = process_chat_message(
        text="Were live weather or mandi prices retrieved?",
        sender="test_user_source_probe",
    )

    # Must honestly report that live APIs are not called
    assert "Live Weather API" in response
    assert "Not retrieved" in response or "Not called" in response
    assert "Live Mandi Prices" in response
    assert "External APIs Called: Zero" in response or "Zero (0)" in response

    # Must NOT ask for farm profile parameters
    assert "Incomplete Farm Profile" not in response
    assert "land_size_acres" not in response


def test_source_methodology_and_unknown_sources_not_invented():
    """
    Source and calculation inquiries must cite official CACP/ICAR reference benchmarks
    and explicitly clarify that live Agmarknet / live weather APIs are not called.
    """
    reset_session("test_user_method_probe")
    response = process_chat_message(
        text="Where did you get these prices and what are your data sources?",
        sender="test_user_method_probe",
    )

    # Must cite authentic reference bodies
    assert "CACP" in response
    assert "ICAR" in response
    assert "Minimum Support Price" in response or "MSP" in response
    assert "Agmarknet" in response  # clarifies not scraped live

    # Must NOT invent fake APIs or demand farm profile
    assert "Incomplete Farm Profile" not in response


def test_new_recommendation_with_missing_fields_requests_them():
    """A new crop recommendation prompt missing required fields must explicitly request them."""
    reset_session("test_user_incomplete")
    response = process_chat_message(
        text="I have 5 acres in Punjab for Kharif season.",
        sender="test_user_incomplete",
    )

    assert "Incomplete Farm Profile" in response
    assert "soil_type" in response
    assert "budget_inr" in response


def test_conversation_context_preserved_for_follow_up_and_source_questions():
    """
    Verify complete multi-turn conversation flow:
    1. Initial farm profile receives recommendations.
    2. Follow-up query about a specific crop uses context without asking for farm details.
    3. Follow-up summary request uses context.
    4. Follow-up question about live feeds answers truthfully without asking for farm details.
    """
    sender = "test_multi_turn_farmer"
    reset_session(sender)

    # Turn 1: Initial recommendation
    initial_prompt = (
        "I have 5 acres of alluvial soil in Punjab with tubewell water "
        "for Rabi season, budget ₹110,000."
    )
    turn1_reply = process_chat_message(text=initial_prompt, sender=sender)

    assert "AgriSaarthi Crop Advisory: Punjab" in turn1_reply
    assert "Top Primary Recommendations" in turn1_reply
    assert "Wheat" in turn1_reply or "Mustard" in turn1_reply

    # Verify session context was recorded
    session = get_session(sender)
    assert session.last_request is not None
    assert session.last_request.state == "Punjab"
    assert session.last_response is not None

    # Turn 2: Follow-up question about Wheat
    turn2_reply = process_chat_message(text="Why did you recommend Wheat?", sender=sender)

    assert "Crop Deep-Dive: Wheat" in turn2_reply or "Wheat" in turn2_reply
    assert "Suitability Score" in turn2_reply
    assert "Incomplete Farm Profile" not in turn2_reply

    # Turn 3: Follow-up asking for summary of previous recommendations
    turn3_reply = process_chat_message(text="Summarize my previous recommendation", sender=sender)

    assert "Summary of Previous Recommendations for Punjab" in turn3_reply
    assert "5.0 Acres" in turn3_reply
    assert "Incomplete Farm Profile" not in turn3_reply

    # Turn 4: Follow-up asking about live weather and mandi prices
    turn4_reply = process_chat_message(
        text="Did you check live weather or mandi prices for this advice?",
        sender=sender,
    )

    assert "Live Weather API" in turn4_reply
    assert "Live Mandi Prices" in turn4_reply
    assert "Not retrieved" in turn4_reply or "Not called" in turn4_reply
    assert "Incomplete Farm Profile" not in turn4_reply


def test_session_isolation_across_different_senders():
    """Ensure conversation contexts between different senders do not leak."""
    sender_a = "farmer_punjab"
    sender_b = "farmer_rajasthan"
    reset_session(sender_a)
    reset_session(sender_b)

    # Farmer A submits profile
    process_chat_message(
        text="I have 4 acres of alluvial soil in Punjab with canal water for Rabi season, budget 90000.",
        sender=sender_a,
    )
    session_a = get_session(sender_a)
    assert session_a.last_request.state == "Punjab"

    # Farmer B has not submitted profile yet
    session_b = get_session(sender_b)
    assert session_b.last_request is None
    assert session_b.last_response is None

    # Farmer B asking follow-up should get prompt to submit profile, not Farmer A's context
    b_reply = process_chat_message(text="What was my recommended crop?", sender=sender_b)
    assert "No Active Farm Profile Found" in b_reply
    assert "Punjab" not in b_reply


def test_telugu_natural_farm_conversation_e2e():
    """
    Farmer provides complete farm profile in Telugu script.
    AgriSaarthi must parse parameters, calculate recommendations, and reply in Telugu.
    """
    sender = "farmer_telugu_e2e"
    reset_session(sender)

    telugu_prompt = "తెలంగాణలో 4 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ సీజన్, బోరు బావి నీరు, బడ్జెట్ 1 లక్ష"
    req, err = parse_chat_query(telugu_prompt)

    assert req is not None
    assert err == ""
    assert req.state == "Telangana"
    assert req.land_size_acres == 4.0
    assert req.soil_type == SoilType.BLACK
    assert req.water_availability == WaterAvailability.MODERATE
    assert req.season == Season.KHARIF
    assert req.budget_inr == 100000.0

    # End-to-end chat message response
    reply = process_chat_message(text=telugu_prompt, sender=sender)
    assert "అగ్రిసారథి పంటల సిఫార్సు: Telangana" in reply
    assert "అత్యంత అనుకూలమైన ప్రధాన పంటలు" in reply
    assert "పత్తి" in reply or "సోయాబీన్" in reply or "మొక్కజొన్న" in reply
    assert "ఎకరానికి ఖర్చు" in reply
    assert "అంచనా నికర లాభం" in reply


def test_telugu_missing_farm_details_guidance():
    """Telugu input with missing parameters must return polite Telugu guidance with no raw internal keys."""
    sender = "farmer_telugu_incomplete"
    reset_session(sender)

    incomplete_telugu = "తెలంగాణలో 4 ఎకరాల భూమి ఉంది ఖరీఫ్ సీజన్"
    req, err = parse_chat_query(incomplete_telugu)

    assert req is None
    assert "అసంపూర్ణ వ్యవసాయ వివరాలు" in err
    assert "నేల రకం" in err
    assert "పెట్టుబడి" in err
    assert "soil_type" not in err
    assert "budget_inr" not in err
    assert "land_size_acres" not in err

    reply = process_chat_message(text=incomplete_telugu, sender=sender)
    assert "అసంపూర్ణ వ్యవసాయ వివరాలు" in reply
    assert "నీటి వసతి" in reply
    assert "water_availability" not in reply


def test_mixed_language_telenglish_extraction():
    """Natural transliterated Telenglish sentences should parse seamlessly."""
    sender = "farmer_telenglish"
    reset_session(sender)

    mixed_prompt = "Telangana lo 4 acres black soil undi, kharif season, borewell water, budget 1 lakh"
    req, err = parse_chat_query(mixed_prompt)

    assert req is not None
    assert err == ""
    assert req.state == "Telangana"
    assert req.land_size_acres == 4.0
    assert req.soil_type == SoilType.BLACK
    assert req.water_availability == WaterAvailability.MODERATE
    assert req.season == Season.KHARIF
    assert req.budget_inr == 100000.0


def test_district_level_state_mapping():
    """Mentioning a district like Warangal or Guntur maps to the correct state."""
    warangal_prompt = "4 acres red soil in Warangal, kharif season, borewell water, budget 70000"
    req, err = parse_chat_query(warangal_prompt)
    assert req is not None
    assert req.state == "Telangana"

    guntur_prompt = "గుంటూరులో 3 ఎకరాలు నల్ల నేల, ఖరీఫ్, కాలువ నీరు, బడ్జెట్ 80 వేలు"
    req2, err2 = parse_chat_query(guntur_prompt)
    assert req2 is not None
    assert req2.state == "Andhra Pradesh"
    assert req2.budget_inr == 80000.0


def test_telugu_follow_up_on_recommended_crop():
    """Asking follow-up questions in Telugu about a recommended crop uses preserved context."""
    sender = "farmer_telugu_followup"
    reset_session(sender)

    # Turn 1: Initial recommendation
    initial = "తెలంగాణలో 4 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ సీజన్, బోరు బావి నీరు, బడ్జెట్ 1 లక్ష"
    t1_reply = process_chat_message(text=initial, sender=sender)
    assert "అగ్రిసారథి పంటల సిఫార్సు: Telangana" in t1_reply

    # Turn 2: Follow-up question about Cotton in Telugu
    t2_reply = process_chat_message(text="పత్తి గురించి చెప్పండి", sender=sender)
    assert "పంట సమగ్ర వివరాలు: పత్తి" in t2_reply or "పత్తి" in t2_reply
    assert "అనుకూలత స్కోర్" in t2_reply
    assert "పెట్టుబడి వ్యయం" in t2_reply
    assert "అసంపూర్ణ వ్యవసాయ వివరాలు" not in t2_reply

    # Turn 3: Follow-up question asking for summary in Telugu
    t3_reply = process_chat_message(text="మునుపటి సిఫార్సుల సారాంశం చెప్పండి", sender=sender)
    assert "మునుపటి పంటల సిఫార్సుల సారాంశం" in t3_reply
    assert "4.0 ఎకరాలు" in t3_reply
    assert "అసంపూర్ణ వ్యవసాయ వివరాలు" not in t3_reply


def test_telugu_source_and_live_data_honesty():
    """Inquiring about live weather or mandi prices in Telugu receives transparent truthful answers."""
    sender = "farmer_telugu_source"
    reset_session(sender)

    reply = process_chat_message(text="లైవ్ వాతావరణం లేదా మండి ధరలు చూశారా?", sender=sender)
    assert "లైవ్ వాతావరణం" in reply
    assert "ఉపయోగించలేదు" in reply or "పిలవలేదు" in reply
    assert "లైవ్ మండి ధరలు" in reply
    assert "బాహ్య APIలు" in reply
    assert "సున్నా (0)" in reply
    assert "MSP" in reply or "CACP" in reply


def test_explicit_language_switching_between_english_and_telugu():
    """
    Users can explicitly switch language on-the-fly using 'Reply in English' or
    'తెలుగులో సమాధానం చెప్పండి' without losing conversation context.
    """
    sender = "farmer_bilingual_switch"
    reset_session(sender)

    # Turn 1: Started in English
    t1 = process_chat_message(
        text="I have 5 acres of alluvial soil in Punjab with tubewell water for Rabi season, budget 100000",
        sender=sender,
    )
    assert "AgriSaarthi Crop Advisory: Punjab" in t1

    # Turn 2: Explicitly switch to Telugu
    t2 = process_chat_message(text="తెలుగులో సమాధానం చెప్పండి", sender=sender)
    assert "అగ్రిసారథి పంటల సిఫార్సు: Punjab" in t2 or "గోధుమ" in t2
    session = get_session(sender)
    assert session.preferred_language == "te"

    # Turn 3: Explicitly switch back to English
    t3 = process_chat_message(text="Reply in English", sender=sender)
    assert "AgriSaarthi Crop Advisory: Punjab" in t3 or "Wheat" in t3
    assert session.preferred_language == "en"


def test_leading_agent_handle_mention_stripped_for_asi_one():
    """ASI:One prepends @agrisaarthi-ai to chat messages; ensure it strips cleanly."""
    sender = "asi_one_farmer"
    reset_session(sender)

    asi_prompt = "@agrisaarthi-ai I have 4 acres of black soil in Telangana with borewell water for Kharif season, budget 100000"
    reply = process_chat_message(text=asi_prompt, sender=sender)

    assert "AgriSaarthi Crop Advisory: Telangana" in reply
    assert "Top Primary Recommendations" in reply
    assert "Cotton" in reply or "Soybean" in reply or "Maize" in reply


# =============================================================================
# Regression Tests for Telugu Farm Profile Extraction (2 Acres, ₹40,000, Multi-Turn)
# =============================================================================

def test_telugu_farm_detail_extraction_2acres_40k_digits():
    """
    Regression Test:
    Farmer supplies: Telangana, 2 acres, black soil, Kharif season, moderate water, and ₹40,000 budget.
    Must parse faithfully without changing 2 acres to 4 acres or inventing details.
    Runs crop recommendation workflow with costs, yield ranges, risks, and reasoning.
    """
    sender = "farmer_2acres_40k_digits"
    reset_session(sender)

    prompt = "తెలంగాణ, 2 ఎకరాలు, నల్ల నేల, ఖరీఫ్ సీజన్, మోస్తరు నీరు, ₹40,000 బడ్జెట్"
    req, err = parse_chat_query(prompt)

    assert err == ""
    assert req is not None
    assert req.state == "Telangana"
    assert req.land_size_acres == 2.0
    assert req.land_size_acres != 4.0
    assert req.soil_type == SoilType.BLACK
    assert req.season == Season.KHARIF
    assert req.water_availability == WaterAvailability.MODERATE
    assert req.budget_inr == 40000.0

    # Full E2E recommendation execution
    reply = process_chat_message(text=prompt, sender=sender)
    assert "అగ్రిసారథి పంటల సిఫార్సు: Telangana" in reply
    assert "2.0 ఎకరాలు" in reply
    assert "4.0 ఎకరాలు" not in reply
    assert "₹40,000" in reply
    # No internal field names leaked
    assert "land_size_acres" not in reply
    assert "budget_inr" not in reply
    assert "soil_type" not in reply
    # Suitable crop options, costs, yields, risks, reasoning, advisory
    assert "అత్యంత అనుకూలమైన ప్రధాన పంటలు" in reply
    assert "ఎకరానికి ఖర్చు" in reply
    assert "మొత్తం 2.0 ఎకరాలకు" in reply
    assert "ఆశించే దిగుబడి" in reply
    assert "అంచనా నికర లాభం" in reply
    assert "గమనించవలసిన రిస్క్" in reply
    assert "నిర్ణయ విశ్లేషణ & కారణాలు" in reply
    assert "రైతులకు ముఖ్య గమనిక & పరిమితులు" in reply


def test_telugu_farm_detail_extraction_words_rendu_nalabhai():
    """
    Regression Test:
    Voice transcript with Telugu number words: 'రెండు ఎకరాలు' (2 acres) and 'నలభై వేలు' (40 thousand).
    Must parse 2.0 acres and ₹40,000 budget correctly.
    """
    sender = "farmer_telugu_words"
    reset_session(sender)

    prompt = "తెలంగాణ, రెండు ఎకరాలు, నల్ల నేల, ఖరీఫ్ సీజన్, మోస్తరు నీరు, నలభై వేలు బడ్జెట్"
    req, err = parse_chat_query(prompt)

    assert err == ""
    assert req is not None
    assert req.state == "Telangana"
    assert req.land_size_acres == 2.0
    assert req.soil_type == SoilType.BLACK
    assert req.season == Season.KHARIF
    assert req.water_availability == WaterAvailability.MODERATE
    assert req.budget_inr == 40000.0

    reply = process_chat_message(text=prompt, sender=sender)
    assert "2.0 ఎకరాలు" in reply
    assert "₹40,000" in reply
    assert "అత్యంత అనుకూలమైన ప్రధాన పంటలు" in reply


def test_telugu_farm_detail_extraction_budget_variations():
    """Verify various natural transcript formats for ₹40,000 budget in Telugu."""
    variations = [
        ("తెలంగాణలో 2 ఎకరాల నల్ల నేల, ఖరీఫ్, మోస్తరు నీరు, 40 వేలు", 40000.0),
        ("తెలంగాణలో 2 ఎకరాల నల్ల నేల, ఖరీఫ్, మోస్తరు నీరు, 40వేలు బడ్జెట్", 40000.0),
        ("తెలంగాణలో 2 ఎకరాల నల్ల నేల, ఖరీఫ్, మోస్తరు నీరు, 40,000 రూపాయలు", 40000.0),
        ("తెలంగాణలో 2 ఎకరాల నల్ల నేల, ఖరీఫ్, మోస్తరు నీరు, బడ్జెట్ 40000", 40000.0),
        ("తెలంగాణలో 2 ఎకరాల నల్ల నేల, ఖరీఫ్, మోస్తరు నీరు, ₹ 40,000", 40000.0),
    ]
    for prompt, expected_budget in variations:
        req, err = parse_chat_query(prompt)
        assert err == "", f"Failed on prompt: {prompt}, error: {err}"
        assert req is not None
        assert req.land_size_acres == 2.0
        assert req.budget_inr == expected_budget, f"Expected {expected_budget} for {prompt}, got {req.budget_inr}"


def test_single_missing_field_asks_only_for_that_value():
    """
    Regression Test:
    When farmer supplies 5 of 6 fields (only budget is missing),
    the assistant must ask ONLY for that specific missing value, without asking to repeat other details.
    """
    sender = "farmer_missing_only_budget"
    reset_session(sender)

    partial_prompt = "తెలంగాణలో 2 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ సీజన్, మోస్తరు నీరు"
    reply = process_chat_message(text=partial_prompt, sender=sender)

    assert "పెట్టుబడి బడ్జెట్" in reply
    assert "మీరు అందించిన మిగతా పొలం వివరాలు నమోదయ్యాయి" in reply
    # Must NOT ask for land size or soil or season again
    assert "భూమి విస్తీర్ణం" not in reply
    assert "land_size_acres" not in reply
    assert "budget_inr" not in reply


def test_avoid_repeated_questions_multi_turn_profile_completion():
    """
    Regression Test:
    Turn 1: Farmer supplies Telangana, 2 acres, black soil, Kharif, moderate water (missing budget).
    Assistant asks ONLY for budget.
    Turn 2: Farmer supplies '₹40,000'.
    Assistant must NOT ask to repeat any info; runs recommendation workflow immediately for 2.0 acres and ₹40,000.
    """
    sender = "farmer_multiturn_completion"
    reset_session(sender)

    # Turn 1: 5 fields provided
    t1_reply = process_chat_message(
        text="తెలంగాణలో 2 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ కాలం, మోస్తరు నీరు",
        sender=sender,
    )
    assert "పెట్టుబడి బడ్జెట్" in t1_reply
    assert "నమోదయ్యాయి" in t1_reply

    # Turn 2: Farmer provides only the missing budget
    t2_reply = process_chat_message(text="₹40,000", sender=sender)
    # Must run the crop recommendation workflow directly
    assert "అగ్రిసారథి పంటల సిఫార్సు: Telangana" in t2_reply
    assert "2.0 ఎకరాలు" in t2_reply
    assert "₹40,000" in t2_reply
    assert "అసంపూర్ణ వ్యవసాయ వివరాలు" not in t2_reply
    assert "land_size_acres" not in t2_reply
    assert "budget_inr" not in t2_reply



