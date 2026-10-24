"""
Agent Chat Protocol (ACP) Implementation for AgriSaarthi AI.
Compliant with official Fetch.ai / ASI:One chat_protocol_spec (v0.3.0).
Provides bilingual (English & Telugu) multi-intent natural language and JSON orchestration:
  1. New Farm Profile & Multi-Step Crop Recommendations (Telugu, English, Telenglish).
  2. Follow-Up Consultations & Deep-Dives preserving conversation context.
  3. Transparent Inquiries on Sources, Formulas, Live Feeds, and Limitations.
  4. Language switching (English <-> Telugu) on-the-fly.
"""

import re
import json
import logging
from typing import Tuple, Optional, Dict, Any, List
from enum import Enum

from uagents import Protocol, Context
from uagents_core.contrib.protocols.chat import (
    chat_protocol_spec,
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    StartSessionContent,
    EndSessionContent,
)

from agrisaarthi.models import (
    FarmerProfileRequest,
    RecommendationResponse,
    Season,
    SoilType,
    WaterAvailability,
    RiskTolerance,
)
from agrisaarthi.engine import AgriSaarthiEngine
from agrisaarthi.data.crops import CROP_DATABASE, CropProfile

logger = logging.getLogger("agrisaarthi.chat")


# =============================================================================
# Bilingual Support: Telugu & English Mappings & Knowledge
# =============================================================================

TELUGU_CROPS: Dict[str, Dict[str, Any]] = {
    "Paddy / Rice": {
        "name_te": "వరి (వరి ధాన్యం)",
        "category_te": "ధాన్యపు పంట",
        "sowing_notes": "నీరు సమృద్ధిగా ఉన్నప్పుడు మాత్రమే నాట్లు వేయండి. బోరు నీరు తక్కువగా ఉంటే వెదజల్లే పద్ధతి (DSR) పరిశీలించండి.",
        "advantage_te": "ప్రభుత్వ కనీస మద్దతు ధర (MSP) కొనుగోలు మరియు విస్తారమైన మార్కెట్ హామీ.",
        "risk_te": "అధిక నీటి వినియోగం, కాండం తొలిచే పురుగు మరియు ఎండాకు తెగులు ముప్పు.",
    },
    "Wheat": {
        "name_te": "గోధుమ",
        "category_te": "ధాన్యపు పంట",
        "sowing_notes": "నవంబర్ 1 నుండి 20 మధ్య విత్తుకోవాలి. మొదటి నీటి తడి (CRI దశ - 21 రోజులకు) చాలా కీలకం.",
        "advantage_te": "ప్రభుత్వ కొనుగోలు హామీ, తక్కువ మార్కెటింగ్ రిస్క్ మరియు నాణ్యమైన గడ్డి లభ్యత.",
        "risk_te": "మార్చి నెలలో వచ్చే వేడి గాలుల వల్ల దిగుబడి తగ్గే అవకాశం.",
    },
    "Cotton (Bt Cotton)": {
        "name_te": "పత్తి (కాటన్)",
        "category_te": "వాణిజ్య పంట",
        "sowing_notes": "నల్ల రేగడి నేలల్లో అత్యంత అనుకూలం. లింగాకర్షక బుట్టలు (ఫెరమోన్ ట్రాప్స్) ముందుగానే అమర్చండి.",
        "advantage_te": "అధిక మార్కెట్ డిమాండ్ మరియు ఎక్కువ నికర ఆదాయం లభించే అవకాశం.",
        "risk_te": "గులాబీ రంగు పురుగు (పింక్ బోల్ వార్మ్) మరియు అధిక పురుగుమందుల ఖర్చు.",
    },
    "Mustard / Rapeseed": {
        "name_te": "ఆవాలు",
        "category_te": "నూనెగింజల పంట",
        "sowing_notes": "రబీలో తక్కువ నీటితో పండించవచ్చు (2-3 తడులు సరిపోతాయి).",
        "advantage_te": "తక్కువ నీటి వినియోగం, తక్కువ పెట్టుబడి మరియు శీఘ్ర కాల పరిమితి.",
        "risk_te": "తేమ వాతావరణంలో పేనుబంక (ఆఫిడ్స్) ఆశించే ప్రమాదం.",
    },
    "Chickpea / Bengal Gram (Chana)": {
        "name_te": "శనగలు (హరభరా)",
        "category_te": "పప్పుధాన్యపు పంట",
        "sowing_notes": "విత్తన శుద్ధి కోసం రైజోబియం కల్చర్ తప్పనిసరిగా వాడండి.",
        "advantage_te": "భూమికి నత్రజని అందించి నేల సారాన్ని పెంచుతుంది, బెట్టను తట్టుకుంటుంది.",
        "risk_te": "కాయ తొలిచే పురుగు మరియు నీరు నిలిచే నేలల్లో పంట దెబ్బతినడం.",
    },
    "Pearl Millet (Bajra)": {
        "name_te": "సజ్జలు",
        "category_te": "చిరుధాన్య పంట",
        "sowing_notes": "వర్షాభావ పరిస్థితుల్లో మరియు తేలికపాటి నేలల్లో సులభంగా పండించవచ్చు.",
        "advantage_te": "అద్భుతమైన కరవు తట్టుకునే శక్తి, అతి తక్కువ పెట్టుబడి ఖర్చు.",
        "risk_te": "పత్తితో పోలిస్తే వాణిజ్య రాబడి కొంత తక్కువగా ఉండటం.",
    },
    "Soybean": {
        "name_te": "సోయాబీన్",
        "category_te": "నూనెగింజల పంట",
        "sowing_notes": "మురుగు నీరు పోయేలా ఎత్తైన బోదెలు (BBF) పద్ధతిలో విత్తండి.",
        "advantage_te": "స్వల్ప కాలిక పంట (90-100 రోజులు), తర్వాత రబీ పంటకు భూమిని సిద్ధం చేస్తుంది.",
        "risk_te": "కాయ ఏర్పడే దశలో వర్షాలు లేకపోతే దిగుబడి బాగా తగ్గుతుంది.",
    },
    "Groundnut / Peanut": {
        "name_te": "వేరుశనగ (పల్లీ)",
        "category_te": "నూనెగింజల పంట",
        "sowing_notes": "ఇసుక లేదా తేలికపాటి ఎర్ర నేలలు ఉత్తమం. బంకమట్టి నేలల్లో ఊడలు దిగడం కష్టం.",
        "advantage_te": "క్వింటాలుకు మంచి ధర, పశువులకు బలమైన పోషక దాణా.",
        "risk_te": "విత్తన ఖర్చు ఎక్కువ, వేరు పురుగు (వైట్ గ్రబ్) సమస్య రావచ్చు.",
    },
    "Maize / Corn": {
        "name_te": "మొక్కజొన్న",
        "category_te": "ధాన్యపు పంట",
        "sowing_notes": "పౌల్ట్రీ ఫీడ్ పరిశ్రమకు ఎల్లప్పుడూ మంచి డిమాండ్ ఉంటుంది. నీరు నిలవకుండా చూసుకోండి.",
        "advantage_te": "ఎక్కువ బయోమాస్ దిగుబడి మరియు ఖరీఫ్, రబీ రెండింటికీ అనుకూలం.",
        "risk_te": "కత్తెర పురుగు (ఫాల్ ఆర్మీవార్మ్) తీవ్రత ఎక్కువగా ఉంటుంది.",
    },
    "Green Gram / Moong": {
        "name_te": "పెసలు (పెసర)",
        "category_te": "పప్పుధాన్యపు పంట",
        "sowing_notes": "కేవలం 60-70 రోజుల్లో పంట చేతికి వస్తుంది. వేసవిలో కూడా అనుకూలం.",
        "advantage_te": "తక్కువ రోజుల్లో పూర్తి కావడం, మంచి మార్కెట్ విలువ, భూమికి పచ్చిరొట్ట ఎరువు.",
        "risk_te": "కోత ఆలస్యమైతే కాయలు పగిలి గింజలు రాలిపోయే ప్రమాదం.",
    },
    "Sugarcane": {
        "name_te": "చెరకు",
        "category_te": "వాణిజ్య పంట",
        "sowing_notes": "నిరంతరాయంగా నీరు అందించగల కాలువ లేదా బోరు వసతి ఉన్నప్పుడే వేయాలి. డ్రిప్ విధానం మంచిది.",
        "advantage_te": "ప్రభుత్వ FRP ధర భద్రత, కార్ఖానాలకు నిర్దిష్ట అమ్మకం.",
        "risk_te": "అధిక నీటి అవసరం, 10-14 నెలల పాటు భూమి బ్లాక్ కావడం.",
    },
}

TELUGU_SOIL_MAP: Dict[SoilType, str] = {
    SoilType.ALLUVIAL: "ఒండ్రు నేల",
    SoilType.BLACK: "నల్ల రేగడి నేల",
    SoilType.RED: "ఎర్ర నేల",
    SoilType.SANDY_LOAM: "ఇసుక నేల (ఇసుక రేగడి)",
    SoilType.CLAYEY: "బంకమట్టి నేల",
    SoilType.LATERITE: "లేటరైట్ నేల",
}

TELUGU_SEASON_MAP: Dict[Season, str] = {
    Season.KHARIF: "ఖరీఫ్ (వానాకాలం)",
    Season.RABI: "రబీ (యాసంగి)",
    Season.ZAID: "జైద్ (వేసవి)",
    Season.YEAR_ROUND: "వార్షిక (ఏడాది పొడవునా)",
}

TELUGU_WATER_MAP: Dict[WaterAvailability, str] = {
    WaterAvailability.LOW: "పరిమిత / తక్కువ నీరు (వర్షాధారం)",
    WaterAvailability.MODERATE: "మధ్యస్థ నీరు (బోరు బావి)",
    WaterAvailability.HIGH: "సమృద్ధిగా నీరు (కాలువ నీరు)",
}

TELUGU_TO_ASCII_DIGITS = str.maketrans("౦౧౨౩౪౫౬౭౮౯", "0123456789")

TELUGU_WORD_TO_NUMBER: Dict[str, float] = {
    "అర": 0.5,
    "ఒక": 1.0, "ఒకటి": 1.0, "ఒకటిన్నర": 1.5,
    "రెండు": 2.0, "రెండున్నర": 2.5,
    "మూడు": 3.0, "మూడున్నర": 3.5,
    "నాలుగు": 4.0, "నాలుగున్నర": 4.5,
    "ఐదు": 5.0, "ఐదున్నర": 5.5,
    "ఆరు": 6.0,
    "ఏడు": 7.0,
    "ఎనిమిది": 8.0,
    "తొమ్మిది": 9.0,
    "పది": 10.0,
    "పదకొండు": 11.0,
    "పన్నెండు": 12.0,
    "ఇరవై": 20.0,
    "ముప్పై": 30.0,
    "నలభై": 40.0,
    "యాభై": 50.0,
    "అరవై": 60.0,
    "డెబ్బై": 70.0,
    "ఎనభై": 80.0,
    "తొంభై": 90.0,
    "వంద": 100.0,
    # Transliterated / English word numbers
    "half": 0.5,
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "twenty": 20.0, "thirty": 30.0, "forty": 40.0, "fifty": 50.0,
}


# =============================================================================
# Conversation Context Store
# =============================================================================

class SessionContext:
    """Stores per-sender conversational state, language preference, and previous recommendations."""

    def __init__(self, sender_id: str = "default"):
        self.sender_id: str = sender_id
        self.preferred_language: str = "en"
        self.last_request: Optional[FarmerProfileRequest] = None
        self.last_response: Optional[RecommendationResponse] = None
        self.pending_profile: Dict[str, Any] = {}
        self.history: List[Dict[str, str]] = []

    def update(self, req: FarmerProfileRequest, resp: RecommendationResponse) -> None:
        self.last_request = req
        self.last_response = resp
        self.pending_profile.clear()

    def update_pending_profile(self, partial: Dict[str, Any]) -> None:
        self.pending_profile.update(partial)

    def clear_pending_profile(self) -> None:
        self.pending_profile.clear()

    def set_language(self, lang: str) -> None:
        if lang in ("en", "te"):
            self.preferred_language = lang


_SESSIONS: Dict[str, SessionContext] = {}


def get_session(sender: str) -> SessionContext:
    """Retrieve or create a conversation session for a sender address."""
    if sender not in _SESSIONS:
        _SESSIONS[sender] = SessionContext(sender_id=sender)
    return _SESSIONS[sender]


def reset_session(sender: str) -> None:
    """Reset a conversation session for a sender address."""
    if sender in _SESSIONS:
        del _SESSIONS[sender]


# =============================================================================
# Language Detection & Directives
# =============================================================================

def is_telugu_script(text: str) -> bool:
    """Check if string contains any Telugu Unicode characters (\u0C00-\u0C7F)."""
    return bool(re.search(r"[\u0C00-\u0C7F]", text))


def detect_language(text: str, session: Optional[SessionContext] = None) -> str:
    """
    Detect whether text is in Telugu ('te') or English ('en').
    Prioritizes explicit language directives, Telugu script, and transliterated terms.
    Falls back to active session preference.
    """
    lower = text.lower().strip()

    # Explicit switch to English
    english_triggers = [
        "reply in english", "speak in english", "english please", "in english",
        "english lo cheppandi", "english lo", "switch to english", "answer in english",
    ]
    if any(t in lower for t in english_triggers):
        return "en"

    # Explicit switch to Telugu
    telugu_triggers = [
        "తెలుగులో సమాధానం చెప్పండి", "తెలుగులో చెప్పండి", "తెలుగులో మాట్లాడండి",
        "తెలుగులో", "తెలుగు", "reply in telugu", "speak in telugu", "telugu please",
        "in telugu", "telugu lo", "telugulo", "switch to telugu", "answer in telugu",
    ]
    if any(t in lower for t in telugu_triggers):
        return "te"

    # Telugu script detection
    if is_telugu_script(text):
        return "te"

    # Transliterated Telugu phrases
    telugu_transliterated = [
        "cheppandi", "undi", "unayi", "naaku", "bhoomi", "neellu", "pettubadi",
        "pantalu", "kharif lo", "rabi lo", "telugulo", "polam", "chala",
    ]
    if any(w in lower for w in telugu_transliterated):
        return "te"

    # Fallback to session preference if set and user didn't write purely English sentence
    if session and session.preferred_language == "te":
        return "te"

    return "en"


def is_pure_language_switch(text: str) -> Optional[str]:
    """Detect if message is ONLY an instruction to change the response language."""
    lower = text.lower().strip()
    en_phrases = [
        "reply in english", "speak in english", "in english", "english please",
        "switch to english", "answer in english", "english",
    ]
    te_phrases = [
        "తెలుగులో సమాధానం చెప్పండి", "తెలుగులో చెప్పండి", "తెలుగులో మాట్లాడండి",
        "తెలుగులో", "తెలుగు", "reply in telugu", "speak in telugu", "in telugu",
        "telugu please", "switch to telugu", "telugu lo cheppandi", "telugu lo",
    ]

    for p in en_phrases:
        if lower == p or (lower.startswith(p) and len(lower.replace(p, "").strip(" .,!?:-")) == 0):
            return "en"
    for p in te_phrases:
        if lower == p or (lower.startswith(p) and len(lower.replace(p, "").strip(" .,!?:-")) == 0):
            return "te"

    return None


# =============================================================================
# Intent Classification
# =============================================================================

class ChatIntent(str, Enum):
    GREETING = "GREETING"
    SOURCE_OR_DATA_QUERY = "SOURCE_OR_DATA_QUERY"
    FOLLOW_UP = "FOLLOW_UP"
    NEW_RECOMMENDATION = "NEW_RECOMMENDATION"
    GENERAL_GUIDANCE = "GENERAL_GUIDANCE"


def is_greeting(text: str) -> bool:
    """Detect greeting, help, or intro queries in English and Telugu."""
    clean = text.strip().lower()
    words = clean.split()
    if len(words) > 5:
        return False
    greetings = [
        "hi", "hello", "hey", "namaste", "namaskar", "help", "start",
        "who are you", "what can you do", "introduce yourself", "greetings",
        "నమస్కారం", "నమస్తే", "హలో", "సహాయం", "స్వాగతం", "బాగున్నారా",
    ]
    return clean in greetings or (len(words) <= 3 and any(words[0] == g for g in greetings))


def is_source_or_data_query(text: str) -> bool:
    """
    Detect whether user is asking about sources, live feeds, mandi prices,
    weather retrieval, calculation methodologies, APIs, or limitations in English or Telugu.
    """
    lower = text.lower()

    # Direct questions about live weather, mandi prices, APIs
    live_patterns = [
        "live weather", "current weather", "real-time weather", "weather api", "forecast api",
        "mandi price", "mandi prices", "live price", "live prices", "market price", "market prices",
        "agmarknet", "apmc", "external api", "did you call", "api called", "did you retrieve",
        "were live", "did you check", "are these live", "is live", "live data", "real-time data",
        "any api", "which api", "calling api", "call api",
        # Telugu patterns
        "లైవ్ వాతావరణం", "వాతావరణం", "మండి ధరలు", "మార్కెట్ ధరలు", "లైవ్ ధరలు",
        "ఏపీఐ", "api", "నిజ సమయం", "రియల్ టైమ్",
    ]
    if any(p in lower for p in live_patterns):
        return True

    # Source and dataset questions
    source_patterns = [
        "source", "sources", "dataset", "data source", "where did you get", "where do you get",
        "where does the data", "reference data", "what data", "which data", "built-in data",
        "reference catalog", "database", "cacp", "icar", "msp",
        # Telugu patterns
        "మూలాలు", "డేటా మూలాలు", "ఎక్కడి నుండి", "డేటా ఎక్కడిది", "ఆధారాలు",
    ]
    if any(p in lower for p in source_patterns):
        return True

    # Calculation, formula, methodology
    method_patterns = [
        "how do you calculate", "how is it calculated", "how did you calculate",
        "calculation formula", "scoring formula", "how is suitability",
        "how do you score", "methodology", "algorithm", "how was this calculated",
        # Telugu patterns
        "ఎలా లెక్కించారు", "లెక్కింపు విధానం", "సూత్రం", "లెక్కింపు",
    ]
    if any(p in lower for p in method_patterns):
        return True

    # Limitations
    limit_patterns = [
        "limitation", "limitations", "disclaimer", "what are your limits",
        "assumptions", "accuracy", "how accurate", "how reliable",
        # Telugu patterns
        "పరిమితులు", "నిబంధనలు", "రిస్క్", "సలహా",
    ]
    if any(p in lower for p in limit_patterns):
        return True

    return False


def is_follow_up_query(text: str, session: SessionContext) -> bool:
    """Detect follow-up questions referencing previous recommendation context in English and Telugu."""
    if session.last_response is None:
        return False

    lower = text.lower()

    # Mentions a crop from the database or recommended crops (English and Telugu)
    crops = [
        "wheat", "paddy", "rice", "cotton", "mustard", "chickpea", "gram", "chana",
        "bajra", "millet", "soybean", "groundnut", "peanut", "maize", "corn", "moong",
        "sugarcane",
        # Telugu crop names
        "వరి", "గోధుమ", "పత్తి", "ఆవాలు", "శనగలు", "సజ్జలు", "సోయాబీన్",
        "వేరుశనగ", "పల్లీ", "మొక్కజొన్న", "పెసలు", "చెరకు",
    ]
    if any(c in lower for c in crops):
        return True

    follow_up_triggers = [
        "why", "tell me more", "explain", "first crop", "second crop", "top crop",
        "primary", "alternative", "hedge", "diversification", "option", "options",
        "profit", "yield", "cost", "risk", "risks", "summarize", "summary",
        "earlier", "previous", "what did you suggest", "what did you recommend",
        "can i grow", "can i plant", "is it safe", "which is better", "more details",
        # Telugu triggers
        "ఎందుకు", "వివరించండి", "మరిన్ని వివరాలు", "ఖర్చు ఎంత", "లాభం ఎంత", "దిగుబడి",
        "సారాంశం", "మునుపటి", "గత సిఫార్సు", "మళ్ళీ చెప్పండి", "మొదటి పంట",
        "రెండవ పంట", "వేయవచ్చా", "సాగు చేయవచ్చా", "ఏది మంచిది", "వివరాలు",
    ]
    return any(t in lower for t in follow_up_triggers)


def is_query_about_previous_recommendation(text: str) -> bool:
    """Detect queries explicitly asking about previous or existing recommendations in English and Telugu."""
    lower = text.lower()
    triggers = [
        "my recommended crop", "my recommendation", "what was my", "what were my",
        "what did you recommend", "what did you suggest", "previous recommendation",
        "earlier recommendation", "summarize my", "repeat recommendation", "my previous",
        # Telugu triggers
        "నా సిఫార్సు", "నా పంట", "మునుపటి సిఫార్సు", "గత సిఫార్సు", "ఏ పంట సిఫార్సు చేశారు",
        "నాకు చెప్పిన పంటలు", "సిఫార్సుల సారాంశం", "గత సిఫార్సులు",
    ]
    return any(t in lower for t in triggers)


def is_new_recommendation_attempt(text: str) -> bool:
    """Detect if user is actively providing farm parameters or requesting recommendations."""
    if is_query_about_previous_recommendation(text):
        return False

    lower = text.lower()

    # JSON indicators
    if "{" in text and "}" in text:
        return True

    # Agricultural holding indicators (2 or more parameter keywords in English or Telugu)
    param_signals = 0
    if any(s in lower for s in ["acres", "acre", "bigha", "hectare", "ఎకరాలు", "ఎకరం", "ఎకరాల", "భూమి", "పొలం"]):
        param_signals += 1
    if any(s in lower for s in ["budget", "inr", "rs", "₹", "capital", "cost", "లక్ష", "లక్షలు", "వేలు", "పెట్టుబడి", "బడ్జెట్", "రూపాయలు"]):
        param_signals += 1
    if any(s in lower for s in ["soil", "alluvial", "black", "red", "sandy", "clayey", "laterite", "నేల", "మట్టి", "రేగడి"]):
        param_signals += 1
    if any(s in lower for s in ["season", "kharif", "rabi", "zaid", "సీజన్", "ఖరీఫ్", "రబీ", "యాసంగి", "వానాకాలం", "వేసవి"]):
        param_signals += 1
    if any(s in lower for s in ["punjab", "haryana", "rajasthan", "maharashtra", "gujarat", "karnataka", "up", "mp", "telangana", "andhra", "తెలంగాణ", "ఆంధ్రప్రదేశ్", "ఆంధ్ర", "వరంగల్", "గుంటూరు"]):
        param_signals += 1
    if any(s in lower for s in ["water", "irrigation", "borewell", "tubewell", "canal", "rainfed", "నీరు", "నీటిపారుదల", "బోరు", "కాలువ", "వర్షాధారం", "బావి"]):
        param_signals += 1

    if param_signals >= 2:
        return True

    # Explicit prompt triggers
    explicit_triggers = [
        "recommend crops", "crop recommendation", "suggest crops", "give me advice",
        "what should i grow", "what should i plant", "new farm", "crop advisory",
        "advise crops", "which crop should i",
        # Telugu explicit triggers
        "పంటల సిఫార్సు", "ఏ పంట వేయాలి", "ఏ పంటలు వేయాలి", "వ్యవసాయ సలహా", "మంచి పంట ఏది", "పంటల సూచన",
    ]
    return any(t in lower for t in explicit_triggers)


# =============================================================================
# Water Availability Extraction (Precise & Faithful to User Wording)
# =============================================================================

def extract_water_availability(lower: str) -> Optional[WaterAvailability]:
    """
    Extract water availability without silent coercion.
    Faithfully recognizes limited irrigation and rainfed as LOW.
    Supports English, Telugu, and transliterated terms.
    """
    # 1. LOW: Explicit rainfed, scarce, arid, or limited irrigation
    low_keywords = [
        "limited irrigation", "limited water", "water is limited", "irrigation is limited",
        "low water", "water scarce", "scarce water", "water is scarce", "scarce irrigation",
        "rainfed", "rain-fed", "rain fed", "dryland", "arid", "drought", "dry",
        "minimal irrigation", "minimal water", "poor irrigation", "unirrigated", "no irrigation",
        "deficit irrigation", "restricted irrigation", "scanty", "water constraint",
        "low irrigation",
        # Telugu keywords
        "వర్షాధారం", "వర్షాధార", "తక్కువ నీరు", "తక్కువ నీటిపారుదల", "పరిమిత నీటిపారుదల",
        "పరిమిత నీరు", "నీటి ఎద్దడి", "నీటి కొరత", "ఎండిన", "బోరు లేదు", "బోర్ లేదు",
        "నీరు తక్కువ",
        # Transliterated
        "varshadharam", "takkuva neellu", "neeru takkuva", "parimitha",
    ]
    if any(k in lower for k in low_keywords):
        return WaterAvailability.LOW

    # 2. HIGH: Abundant, canal, heavy, or perennial irrigation
    high_keywords = [
        "high water", "abundant water", "abundant", "heavy irrigation", "fully irrigated",
        "assured irrigation", "canal water", "canal irrigation", "flood irrigation",
        "perennial irrigation", "plenty of water", "excess water", "high irrigation",
        # Telugu keywords
        "కాలువ నీరు", "కాలువ", "సమృద్ధిగా నీరు", "ఎక్కువ నీరు", "పుష్కలంగా నీరు",
        "పూర్తి నీటిపారుదల", "బాగా నీరు ఉంది", "కాలువ ద్వారా", "పుష్కలం",
        # Transliterated
        "kaluva", "kaluva neellu", "samruddhiga", "ekkuva neellu",
    ]
    if any(k in lower for k in high_keywords):
        return WaterAvailability.HIGH

    # 3. MODERATE: Borewell, tubewell, average, or medium irrigation
    mod_keywords = [
        "moderate water", "moderate irrigation", "medium water", "medium irrigation",
        "tube well", "tubewell", "borewell", "well water", "semi-irrigated",
        "intermittent irrigation", "average water", "moderate",
        # Telugu keywords
        "బోరు బావి నీరు", "బోరు బావి", "బోరుబావి", "బోరు నీరు", "బోరు", "బోర్",
        "బావి నీరు", "బావి", "మధ్యస్థ నీరు", "మధ్యస్థ నీటి వసతి", "మధ్యస్థ నీటిపారుదల",
        "మధ్యస్థం", "మధ్యస్థ", "మోస్తరు నీరు", "మోస్తరు నీటి వసతి", "మోస్తరు నీటిపారుదల",
        "మోస్తరు", "మోస్తారు నీరు", "మోస్తారు",
        # Transliterated
        "borewell", "bore baavi", "bavi neellu", "madhyastham", "mostharu",
    ]
    if any(k in lower for k in mod_keywords):
        return WaterAvailability.MODERATE

    # 4. Check standalone single-word tokens
    tokens = set(re.findall(r"\b\w+\b", lower))
    if "low" in tokens or "తక్కువ" in lower:
        return WaterAvailability.LOW
    if "high" in tokens or "కాలువ" in lower:
        return WaterAvailability.HIGH
    if "moderate" in tokens or "మోస్తరు" in lower or "బోరు" in lower:
        return WaterAvailability.MODERATE

    return None


# =============================================================================
# Natural Language & JSON Profile Parsing (English, Telugu, Telenglish)
# =============================================================================

def parse_chat_query(text: str, session: Optional[SessionContext] = None) -> Tuple[Optional[FarmerProfileRequest], str]:
    """
    Parses an incoming ACP chat message into a validated FarmerProfileRequest.
    Supports:
      1. Raw JSON payloads.
      2. Markdown-fenced JSON blocks (```json ... ```).
      3. Natural language text entity extraction (English, Telugu, and mixed).
    Returns:
      (FarmerProfileRequest, "") if successful, or (None, guidance_or_error_message).
    """
    clean_text = text.strip()
    lang = detect_language(clean_text, session)

    if not clean_text:
        return None, _generate_welcome_message(lang=lang)

    lower = clean_text.lower()
    if is_greeting(lower):
        return None, _generate_welcome_message(lang=lang)

    # 1. Try direct or markdown-fenced JSON
    json_candidate = None
    if "```" in clean_text:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, re.DOTALL)
        if match:
            json_candidate = match.group(1)
    elif clean_text.startswith("{") and clean_text.endswith("}"):
        json_candidate = clean_text

    if json_candidate:
        try:
            data = json.loads(json_candidate)
            return _dict_to_profile(data)
        except json.JSONDecodeError as e:
            return None, _generate_help_message(f"Malformed JSON syntax: {str(e)}")
        except Exception as e:
            return None, _generate_help_message(f"Input validation error: {str(e)}")

    # 2. Natural language entity extraction (English, Telugu, Telenglish)
    extracted, missing = _extract_entities_from_text(clean_text)

    # If session has pending partial details, merge them
    if session and session.pending_profile:
        merged = dict(session.pending_profile)
        merged.update(extracted)
        extracted = merged
        required_keys = ["state", "season", "soil_type", "water_availability", "land_size_acres", "budget_inr"]
        missing = [k for k in required_keys if k not in extracted]

    if missing:
        if session:
            session.update_pending_profile(extracted)
        return None, _generate_missing_fields_message(missing, clean_text, lang=lang)

    try:
        req = FarmerProfileRequest(**extracted)
        if session:
            session.clear_pending_profile()
        return req, ""
    except Exception as e:
        return None, _generate_help_message(f"Could not build valid farm profile: {str(e)}")


def _dict_to_profile(data: Dict[str, Any]) -> Tuple[Optional[FarmerProfileRequest], str]:
    """Convert dictionary to FarmerProfileRequest with error handling."""
    try:
        if "season" in data and isinstance(data["season"], str):
            data["season"] = data["season"].lower().strip()
        if "soil_type" in data and isinstance(data["soil_type"], str):
            data["soil_type"] = data["soil_type"].lower().strip().replace(" ", "_")
        if "water_availability" in data and isinstance(data["water_availability"], str):
            data["water_availability"] = data["water_availability"].lower().strip()
        if "risk_tolerance" in data and isinstance(data["risk_tolerance"], str):
            data["risk_tolerance"] = data["risk_tolerance"].lower().strip()

        req = FarmerProfileRequest(**data)
        return req, ""
    except Exception as e:
        return None, _generate_help_message(f"Validation error in profile parameters: {str(e)}")


def _extract_entities_from_text(text: str) -> Tuple[Dict[str, Any], List[str]]:
    """Extract agricultural parameters from natural conversational text (English, Telugu, Telenglish)."""
    normalized_text = text.translate(TELUGU_TO_ASCII_DIGITS)
    lower = normalized_text.lower()
    extracted: Dict[str, Any] = {}
    missing: List[str] = []

    # State & District matching
    telangana_indicators = [
        "telangana", "తెలంగాణ", "తెలంగాణలో", "తెలంగాణా", "తెలంగాణ రాష్ట్రం", "tg",
        "వరంగల్", "warangal", "కరీంనగర్", "karimnagar", "ఖమ్మం", "khammam",
        "నల్గొండ", "nalgonda", "నిజామాబాద్", "nizamabad", "మహబూబ్ నగర్",
        "mahabubnagar", "మహబూబ్‌నగర్", "రంగారెడ్డి", "rangareddy", "మెదక్", "medak",
        "అదిలాబాద్", "adilabad", "సిద్ధిపేట", "siddipet", "సూర్యాపేట", "suryapet",
        "భద్రాద్రి", "bhadradri"
    ]
    andhra_indicators = [
        "andhra pradesh", "andhra", "ఆంధ్రప్రదేశ్", "ఆంధ్ర ప్రదేశ్", "ఆంధ్ర", "ఆంధ్ర రాష్ట్రం", "ap",
        "గుంటూరు", "guntur", "కృష్ణా", "krishna", "గోదావరి", "godavari",
        "నెల్లూరు", "nellore", "ప్రకాశం", "prakasam", "కర్నూలు", "kurnool",
        "అనంతపురం", "anantapur", "కడప", "kadapa", "చిత్తూరు", "chittoor",
        "విశాఖపట్నం", "visakhapatnam", "వైజాగ్", "vizag"
    ]

    detected_state = None
    if any(k in lower for k in telangana_indicators):
        detected_state = "Telangana"
    elif any(k in lower for k in andhra_indicators):
        detected_state = "Andhra Pradesh"
    else:
        state_map = {
            "punjab": "Punjab", "పంజాబ్": "Punjab",
            "haryana": "Haryana", "హర్యానా": "Haryana",
            "rajasthan": "Rajasthan", "రాజస్థాన్": "Rajasthan",
            "maharashtra": "Maharashtra", "మహారాష్ట్ర": "Maharashtra",
            "gujarat": "Gujarat", "గుజరాత్": "Gujarat",
            "karnataka": "Karnataka", "కర్ణాటక": "Karnataka",
            "tamil nadu": "Tamil Nadu", "తమిళనాడు": "Tamil Nadu",
            "uttar pradesh": "Uttar Pradesh", "ఉత్తర ప్రదేశ్": "Uttar Pradesh",
            "madhya pradesh": "Madhya Pradesh", "మధ్యప్రదేశ్": "Madhya Pradesh",
            "bihar": "Bihar", "బీహార్": "Bihar",
            "west bengal": "West Bengal", "పశ్చిమ బెంగాల్": "West Bengal",
            "odisha": "Odisha", "ఒడిశా": "Odisha", "ఒరిస్సా": "Odisha",
        }
        for pattern, st_name in state_map.items():
            if pattern in lower:
                detected_state = st_name
                break

    if detected_state:
        extracted["state"] = detected_state
    else:
        if "up" in re.findall(r"\bup\b", lower):
            extracted["state"] = "Uttar Pradesh"
        elif "mp" in re.findall(r"\bmp\b", lower):
            extracted["state"] = "Madhya Pradesh"
        else:
            missing.append("state")

    # Season matching
    if any(k in lower for k in ["kharif", "monsoon", "rainy", "summer crop", "ఖరీఫ్", "వానాకాలం", "వర్షాకాలం", "ఖరీఫ్ కాలం", "ఖరీఫ్ సీజన్"]):
        extracted["season"] = Season.KHARIF
    elif any(k in lower for k in ["rabi", "winter", "రబీ", "యాసంగి", "చలికాలం", "రబీ కాలం", "రబీ సీజన్"]):
        extracted["season"] = Season.RABI
    elif any(k in lower for k in ["zaid", "summer short", "summer", "జైద్", "వేసవి", "ఎండాకాలం", "జైద్ కాలం"]):
        extracted["season"] = Season.ZAID
    elif any(k in lower for k in ["year round", "annual", "వార్షిక", "ఏడాది పొడవునా"]):
        extracted["season"] = Season.YEAR_ROUND
    else:
        missing.append("season")

    # Soil type matching
    if any(k in lower for k in ["alluvial", "ఒండ్రు నేల", "ఒండ్రు మట్టి", "ఒండ్రు"]):
        extracted["soil_type"] = SoilType.ALLUVIAL
    elif any(k in lower for k in ["black", "regur", "నల్ల నేల", "నల్ల రేగడి", "నల్లరేగడి", "నల్లమట్టి", "నల్ల రేగడి నేల", "నల్లరేగడి నేల", "నల్ల"]):
        extracted["soil_type"] = SoilType.BLACK
    elif any(k in lower for k in ["sandy loam", "sandy-loam", "sandy", "ఇసుక నేల", "ఇసుక", "ఇసుక రేగడి"]):
        extracted["soil_type"] = SoilType.SANDY_LOAM
    elif any(k in lower for k in ["clay", "clayey", "బంకమట్టి", "బంక నేల", "బంక"]):
        extracted["soil_type"] = SoilType.CLAYEY
    elif any(k in lower for k in ["laterite", "లేటరైట్"]):
        extracted["soil_type"] = SoilType.LATERITE
    elif any(k in lower for k in ["red", "ఎర్ర నేల", "ఎర్ర మట్టి", "ఎర్రనేల", "ఎర్రమట్టి", "చెలక నేల", "చెలక", "ఎరుపు"]):
        extracted["soil_type"] = SoilType.RED
    else:
        missing.append("soil_type")

    # Water availability matching
    water_tier = extract_water_availability(lower)
    if water_tier is not None:
        extracted["water_availability"] = water_tier
    else:
        missing.append("water_availability")

    # Land size (acres) - strictly parses user-supplied number or word without defaulting to 4.0
    word_keys_sorted = sorted(TELUGU_WORD_TO_NUMBER.keys(), key=len, reverse=True)
    acre_units = r"(?:acres?|acre|ac\b|bigha|hectares?|ఎకరాలు|ఎకరం|ఎకరాల|ఎకరము|ఎకరాల్లో|ఎకరాలకు)"
    acre_digit_match = re.search(r"(\d+(?:\.\d+)?)\s*" + acre_units, lower)
    if acre_digit_match:
        extracted["land_size_acres"] = float(acre_digit_match.group(1))
    else:
        # Match Telugu/English word numbers before acre units (e.g. "రెండు ఎకరాలు")
        word_acre_pattern = r"\b(" + "|".join(re.escape(k) for k in word_keys_sorted) + r")\s*" + acre_units
        word_acre_match = re.search(word_acre_pattern, lower)
        if word_acre_match:
            extracted["land_size_acres"] = float(TELUGU_WORD_TO_NUMBER[word_acre_match.group(1)])
        else:
            alt_digit_match = re.search(r"(?:భూమి|పొలం|విస్తీర్ణం|land|farm|holding|area)\s*(?:is|of|ఉంది|గల)?\s*(\d+(?:\.\d+)?)", lower)
            if alt_digit_match:
                extracted["land_size_acres"] = float(alt_digit_match.group(1))
            else:
                alt_word_match = re.search(r"(?:భూమి|పొలం|విస్తీర్ణం|land|farm|holding|area)\s*(?:is|of|ఉంది|గల)?\s*(" + "|".join(re.escape(k) for k in word_keys_sorted) + r")\b", lower)
                if alt_word_match:
                    extracted["land_size_acres"] = float(TELUGU_WORD_TO_NUMBER[alt_word_match.group(1)])
                else:
                    missing.append("land_size_acres")

    # Budget in INR (supports Lakhs, Thousands, Currency symbols, and Raw amounts)
    # 1. Lakhs
    lakh_digit_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:లక్షలు|లక్షల|లక్ష|lakhs?|lac|lacs?)", lower)
    lakh_word_match = re.search(r"\b(" + "|".join(re.escape(k) for k in word_keys_sorted) + r")\s*(?:లక్షలు|లక్షల|లక్ష|lakhs?|lac|lacs?)", lower)

    # 2. Thousands
    thousand_digit_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:వేలు|వేయి|వేల|thousands?|k\b)", lower)
    thousand_word_match = re.search(r"\b(" + "|".join(re.escape(k) for k in word_keys_sorted) + r")\s*(?:వేలు|వేయి|వేల|thousands?)", lower)

    if lakh_digit_match:
        extracted["budget_inr"] = float(lakh_digit_match.group(1)) * 100000.0
    elif lakh_word_match:
        extracted["budget_inr"] = float(TELUGU_WORD_TO_NUMBER[lakh_word_match.group(1)]) * 100000.0
    elif thousand_digit_match:
        extracted["budget_inr"] = float(thousand_digit_match.group(1)) * 1000.0
    elif thousand_word_match:
        extracted["budget_inr"] = float(TELUGU_WORD_TO_NUMBER[thousand_word_match.group(1)]) * 1000.0
    else:
        # 3. Currency / budget prefix: ₹40,000, బడ్జెట్ 40000, రూ. 40,000, Rs. 40,000
        budget_prefix_match = re.search(
            r"(?:₹|rs\.?|inr|రూ\.?|రూపాయలు|రూపాయల|బడ్జెట్|పెట్టుబడి|budget|capital|funds|investment)\s*[:=]?\s*(\d[\d,]*(?:\.\d+)?)",
            lower
        )
        # 4. Currency / budget suffix: 40,000 రూపాయలు, 40000 బడ్జెట్, 40,000/-, 40,000
        budget_suffix_match = re.search(
            r"(\d[\d,]*(?:\.\d+)?)\s*(?:₹|rs\.?|inr|రూ\.?|రూపాయలు|రూపాయల|బడ్జెట్|పెట్టుబడి|/-)",
            lower
        )

        if budget_prefix_match:
            extracted["budget_inr"] = float(budget_prefix_match.group(1).replace(",", ""))
        elif budget_suffix_match:
            extracted["budget_inr"] = float(budget_suffix_match.group(1).replace(",", ""))
        else:
            # 5. Standalone 4 to 8 digit numbers (with or without comma, >= 1000)
            raw_nums = re.findall(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{4,8}\b", lower)
            valid_candidates = []
            for n in raw_nums:
                try:
                    val = float(n.replace(",", ""))
                    if "land_size_acres" in extracted and abs(val - extracted["land_size_acres"]) < 0.01:
                        continue
                    if val >= 1000.0:
                        valid_candidates.append(val)
                except ValueError:
                    pass
            if valid_candidates:
                extracted["budget_inr"] = valid_candidates[0]
            else:
                missing.append("budget_inr")

    # Risk tolerance
    if any(k in lower for k in ["low risk", "safe", "conservative", "తక్కువ రిస్క్", "భద్రమైన"]):
        extracted["risk_tolerance"] = RiskTolerance.LOW
    elif any(k in lower for k in ["high risk", "commercial", "cash crop", "ఎక్కువ రిస్క్", "వాణిజ్య"]):
        extracted["risk_tolerance"] = RiskTolerance.HIGH
    else:
        extracted["risk_tolerance"] = RiskTolerance.MODERATE

    return extracted, missing


# =============================================================================
# Response Handlers: Sources, Follow-ups, and Recommendations
# =============================================================================

def _handle_source_or_data_query(query: str, session: SessionContext, lang: str = "en") -> str:
    """
    Answer questions about data sources, calculations, live feeds, and limitations honestly.
    Explicitly clarifies that NO live weather or live mandi APIs were called.
    Supports English and Telugu responses.
    """
    lower = query.lower()

    is_live_query = any(k in lower for k in [
        "live", "weather", "mandi", "market price", "agmarknet", "apmc", "api", "current price",
        "real-time", "retrieved", "check", "వాతావరణం", "మండి", "మార్కెట్", "ఏపీఐ",
    ])
    is_calc_query = any(k in lower for k in [
        "calculate", "formula", "scoring", "how is", "suitability score", "algorithm", "methodology", "score",
        "లెక్కించారు", "లెక్కింపు", "సూత్రం",
    ])
    is_limitation_query = any(k in lower for k in [
        "limitation", "limitations", "disclaimer", "accuracy", "reliable", "assumption",
        "పరిమితులు", "నిబంధనలు", "సలహా",
    ])

    if lang == "te":
        sections = []
        if is_live_query:
            sections.append(
                "🌾 **అగ్రిసారథి AI — లైవ్ డేటా & ఏపీఐ (API) వివరాలు**\n\n"
                "**1. లైవ్ వాతావరణం (Live Weather API)**: **ఉపయోగించలేదు / పిలవలేదు**.\n"
                "- అగ్రిసారథి శాటిలైట్ లేదా IMD నిజ-సమయ వాతావరణ APIలను ఉపయోగించదు.\n"
                "- వాతావరణ మరియు ప్రాంతీయ అనుకూలతను మీరు పేర్కొన్న పంట కాలం (ఖరీఫ్/రబీ/జైద్), "
                "స్థానిక ప్రాంతం మరియు మీ నీటి లభ్యత (`low`, `moderate`, `high`) ఆధారంగా లెక్కిస్తాము.\n\n"
                "**2. లైవ్ మండి ధరలు (Live Mandi Prices)**: **ఉపయోగించలేదు / పిలవలేదు**.\n"
                "- అగ్రిసారథి Agmarknet లేదా APMC రోజువారీ స్పాట్ వేలం ధరలను లైవ్‌గా సేకరించదు.\n"
                "- లాభం మరియు రాబడి లెక్కలు భారత ప్రభుత్వ అధికారిక కనీస మద్దతు ధరలు (MSP 2024–2025) "
                "మరియు CACP ప్రామాణిక నివేదికల ఆధారంగా రూపొందించిన అంచనాలు మాత్రమే.\n\n"
                "**3. బాహ్య APIలు (External APIs Called)**: **సున్నా (0)**.\n"
                "- ఎటువంటి దాచిన బాహ్య కాల్స్ లేకుండా ధృవీకరించబడిన వ్యవసాయ డేటా ఆధారంగా మాత్రమే ఏజెంట్ పనిచేస్తుంది."
            )

        if is_calc_query or not is_live_query:
            sections.append(
                "📊 **డేటా మూలాలు & లెక్కింపు పద్ధతులు**\n\n"
                "- **సాగు వ్యయం (Cost of Cultivation)**: **CACP** (వ్యవసాయ ఖర్చులు మరియు ధరల కమిషన్) మరియు "
                "**ICAR** రాష్ట్రాల వారీ అధికారిక సమగ్ర వ్యయ సర్వేల నుండి తీసుకోబడింది.\n"
                "- **దిగుబడి & ధరలు**: రాష్ట్ర వ్యవసాయ విశ్వవిద్యాలయాల ప్రామాణిక నివేదికలు మరియు ప్రభుత్వ MSP నోటిఫికేషన్లు.\n"
                "- **లైవ్ మండి / వాతావరణం లేదు**: Agmarknet లేదా వాతావరణ సమాచారాన్ని లైవ్‌గా సేకరించలేదు; "
                "అన్ని గణాంకాలు వ్యవసాయ శాస్త్ర అంచనాలు మరియు 2024–2025 కనీస మద్దతు ధర (MSP) బెంచ్‌మార్క్‌లు మాత్రమే.\n"
                "- **అనుకూలత స్కోర్ (0–100)**:\n"
                "  - **సీజన్ సరిపోలిక**: ఖచ్చితమైన సీజన్ ప్రాథమిక అవసరం (ఖరీఫ్, రబీ, జైద్).\n"
                "  - **నేల రకం**: +25 పాయింట్లు (ఉత్తమం), +15 పాయింట్లు (సహనం).\n"
                "  - **నీటి లభ్యత**: +25 పాయింట్లు (సరిపోతే), నీటి కొరత ఉంటే జరిమానా (-10).\n"
                "  - **ప్రాంతీయ అనుకూలత**: వాణిజ్య సాగు రాష్ట్రాలకు +15 బోనస్ పాయింట్లు.\n"
                "  - **రిస్క్ ప్రాధాన్యత**: రైతు రిస్క్ ఎంపికకు తగినట్టు +10 బోనస్ పాయింట్లు.\n"
                "- **బడ్జెట్ సాధ్యత**: ఎకరానికి అయ్యే ఖర్చును మొత్తం విస్తీర్ణంతో పోల్చి చూస్తాము."
            )

        if is_limitation_query or is_live_query:
            sections.append(
                "⚠️ **రైతులకు ముఖ్య గమనిక & సలహాలు**\n\n"
                "1. **సాయిల్ హెల్త్ కార్డ్ (మట్టి పరీక్ష)**: పంట వేసే ముందు స్థానిక రైతు సేవా కేంద్రం లేదా వ్యవసాయ శాఖ ద్వారా మట్టి పరీక్ష చేయించి ఎరువుల మోతాదు నిర్ణయించుకోండి.\n"
                "2. **స్థానిక మండి ధరల హెచ్చుతగ్గులు**: స్థానిక APMC మార్కెట్ ధరలు రాక మరియు తేమ శాతాన్ని బట్టి రోజూ మారుతుంటాయి.\n"
                "3. **వాతావరణ పరిస్థితులు**: విత్తే సమయాన్ని స్థానిక వాతావరణ శాఖ (IMD) వర్ష సూచనలకు అనుగుణంగా నిర్ణయించుకోండి."
            )

        return "\n\n---\n\n".join(sections)

    # Standard English handler
    sections = []

    if is_live_query:
        sections.append(
            "🌾 **AgriSaarthi AI — Live Feeds & API Verification**\n\n"
            "**1. Live Weather API**: **Not retrieved / Not called**.\n"
            "- AgriSaarthi does **not** query real-time satellite, meteorological, or IMD weather APIs.\n"
            "- Agro-climatic suitability is evaluated using the planting season you specify (`Kharif`, `Rabi`, or `Zaid`), "
            "established state-level agro-ecological zones, and your reported water availability (`low`, `moderate`, `high`).\n\n"
            "**2. Live Mandi Prices**: **Not retrieved / Not called**.\n"
            "- AgriSaarthi does **not** scrape or query live Agmarknet / APMC daily spot auction prices.\n"
            "- Financial returns and net profit figures are **estimates** calculated from official Government of India "
            "Minimum Support Prices (MSP 2024–2025) and CACP benchmark modal farmgate prices.\n\n"
            "**3. External APIs Called**: **Zero (0)**.\n"
            "- The agent runs deterministically on curated, verified agronomic reference datasets without hidden external API calls."
        )

    if is_calc_query or not is_live_query:
        sections.append(
            "📊 **Data Sources & Calculation Methodology**\n\n"
            "- **Cost of Cultivation**: Derived from **CACP** (Commission for Agricultural Costs and Prices) and "
            "**ICAR** (Indian Council of Agricultural Research) state-wise comprehensive cost surveys.\n"
            "- **Yield & Price Benchmarks**: Standard average quintals/acre from state agricultural universities and official MSP reports.\n"
            "- **No Live Mandi / Weather APIs**: AgriSaarthi does not scrape live Agmarknet daily spot auction prices or live meteorological forecasts; all figures are baseline agronomic estimates and official 2024–2025 Government Minimum Support Price (MSP) benchmarks.\n"
            "- **Suitability Scoring Model (0–100)**:\n"
            "  - **Season Match**: Prerequisite strict match (Kharif, Rabi, Zaid).\n"
            "  - **Soil Compatibility**: +25 points (optimal), +15 points (tolerated).\n"
            "  - **Water Alignment**: +25 points (exact match), penalty (-10) for manageable deficit, disqualification for severe water stress.\n"
            "  - **Regional Affinity**: +15 bonus points for prominent commercial cultivation states.\n"
            "  - **Risk Tolerance**: +10 bonus points when crop risk profile matches farmer preference.\n"
            "- **Financial Feasibility**: Cultivation cost/acre is multiplied by plot size and compared against total capital allocated."
        )

    if is_limitation_query or is_live_query:
        sections.append(
            "⚠️ **Advisory Limitations & Best Practices**\n\n"
            "1. **Laboratory Soil Testing**: Always conduct a Soil Health Card (SHC) test for NPK, micronutrients, and pH before sowing.\n"
            "2. **Local Mandi Fluctuations**: Local APMC mandi rates fluctuate with daily arrivals, quality grade, and moisture.\n"
            "3. **Micro-Climate Variability**: Sowing dates should be aligned with local IMD rainfall advisories and block-level extension alerts."
        )

    return "\n\n---\n\n".join(sections)


def _handle_follow_up_query(query: str, session: SessionContext, lang: str = "en") -> str:
    """
    Answer follow-up questions referencing previous recommendation context
    without asking the user to resubmit their farm profile.
    Supports English and Telugu responses.
    """
    req = session.last_request
    resp = session.last_response
    lower = query.lower()

    if not req or not resp:
        if lang == "te":
            return (
                "🌾 **మునుపటి వ్యవసాయ వివరాలు నమోదు కాలేదు**\n\n"
                "ఈ సెషన్‌లో మీ మునుపటి పంటల సిఫార్సుల వివరాలు ఇంకా లేవు.\n\n"
                "మీ పొలానికి సరిగ్గా సరిపోయే సిఫార్సుల కోసం, దయచేసి వివరాలను తెలియజేయండి:\n"
                "- **రాష్ట్రం / జిల్లా** (ఉదా: తెలంగాణ, ఆంధ్రప్రదేశ్, వరంగల్, గుంటూరు)\n"
                "- **భూమి విస్తీర్ణం** (ఎకరాల్లో)\n"
                "- **నేల రకం** (నల్ల రేగడి, ఎర్ర నేల, ఒండ్రు నేల, ఇసుక నేల, బంకమట్టి)\n"
                "- **నీటి లభ్యత** (పరిమిత నీరు/వర్షాధారం, బోరు బావి, కాలువ నీరు)\n"
                "- **సీజన్** (ఖరీఫ్/వానాకాలం, రబీ/యాసంగి, జైద్/వేసవి)\n"
                "- **పెట్టుబడి బడ్జెట్** (రూపాయల్లో)"
            )

        return (
            "🌾 **No Active Farm Profile Found**\n\n"
            "I don't have a record of your previous crop recommendations in this session yet.\n\n"
            "To generate personalized recommendations, please share your farm profile:\n"
            "- **State** (e.g. your state or region)\n"
            "- **Land Size** in acres\n"
            "- **Soil Type** (alluvial, black, red, sandy loam, clayey, laterite)\n"
            "- **Water Availability** (low/limited, moderate/tubewell, high/canal)\n"
            "- **Season** (kharif, rabi, zaid)\n"
            "- **Seasonal Budget** in INR"
        )

    # 1. Check if user mentioned a specific crop (English or Telugu)
    all_recs = resp.primary_recommendations + resp.alternative_recommendations
    matched_rec = None
    for r in all_recs:
        r_crop_lower = r.crop_name.lower()
        r_te_meta = TELUGU_CROPS.get(r.crop_name, {})
        r_te_name = r_te_meta.get("name_te", "").lower()

        if r_crop_lower in lower or any(word in lower for word in r_crop_lower.split() if len(word) > 2):
            matched_rec = r
            break
        if r_te_name and any(part in lower for part in r_te_name.split() if len(part) > 1):
            matched_rec = r
            break

    if matched_rec:
        crop_profile = next(
            (c for c in CROP_DATABASE if c.name.lower() in matched_rec.crop_name.lower() or matched_rec.crop_name.lower() in c.name.lower()),
            None
        )
        cost_total = matched_rec.estimated_cost_per_acre_inr * req.land_size_acres
        profit_total = matched_rec.estimated_net_profit_per_acre_inr * req.land_size_acres

        if lang == "te":
            crop_meta = TELUGU_CROPS.get(matched_rec.crop_name, {})
            name_te = crop_meta.get("name_te", matched_rec.crop_name)
            category_te = crop_meta.get("category_te", matched_rec.category)
            adv_te = crop_meta.get("advantage_te", matched_rec.key_strengths[0] if matched_rec.key_strengths else "ప్రాంతీయ అనుకూలత")
            risk_te = crop_meta.get("risk_te", matched_rec.risk_factors[0] if matched_rec.risk_factors else "సాధారణ యాజమాన్యం అవసరం")
            sowing_notes = crop_meta.get("sowing_notes", crop_profile.advisory_notes if crop_profile else "")
            soil_te = TELUGU_SOIL_MAP.get(req.soil_type, req.soil_type.value)
            season_te = TELUGU_SEASON_MAP.get(req.season, req.season.value)
            water_te = TELUGU_WATER_MAP.get(req.water_availability, req.water_availability.value)

            lines = [
                f"🌾 **పంట సమగ్ర వివరాలు: {name_te} ({matched_rec.crop_name})**",
                f"**అనుకూలత స్కోర్**: `{matched_rec.suitability_score}/100` | **వర్గం**: {category_te}",
                f"- **మీ పొలం వివరాలు**: {req.land_size_acres:.1f} ఎకరాలు, {req.state} ({season_te}, {soil_te}, {water_te})",
                f"- **పెట్టుబడి వ్యయం**: ఎకరానికి ₹{matched_rec.estimated_cost_per_acre_inr:,.0f} (మొత్తం {req.land_size_acres:.1f} ఎకరాలకు ₹{cost_total:,.0f})",
                f"- **ఆశించే దిగుబడి**: {matched_rec.expected_yield_range_quintals_per_acre[0]} - {matched_rec.expected_yield_range_quintals_per_acre[1]} క్వింటాళ్లు/ఎకరానికి",
                f"- **అంచనా నికర లాభం**: ఎకరానికి ₹{matched_rec.estimated_net_profit_per_acre_inr:,.0f} (మొత్తం పొలానికి సుమారు ₹{profit_total:,.0f} లాభం - అంచనా మాత్రమే)",
                f"- **నీరు & నేల అనుకూలత**: నీరు: `{matched_rec.water_compatibility}` | నేల: `{matched_rec.soil_compatibility}`",
                f"- **ప్రధాన ప్రయోజనం**: {adv_te}",
                f"- **గమనించవలసిన రిస్క్**: {risk_te}",
            ]
            if sowing_notes:
                lines.append(f"- **వ్యవసాయ సూచన & సలహా**: {sowing_notes}")
            return "\n".join(lines)

        lines = [
            f"🌾 **Crop Deep-Dive: {matched_rec.crop_name} ({matched_rec.hindi_name})**",
            f"**Suitability Score**: `{matched_rec.suitability_score}/100` | **Category**: {matched_rec.category}",
            f"- **Your Farm Context**: {req.land_size_acres:.1f} Acres in {req.state} ({req.season.value.upper()} Season, {req.soil_type.value.title()} Soil, {req.water_availability.value.title()} Water)",
            f"- **Cost Breakdown**: ₹{matched_rec.estimated_cost_per_acre_inr:,.0f}/acre (₹{cost_total:,.0f} total for {req.land_size_acres:.1f} acres)",
            f"- **Expected Yield**: {matched_rec.expected_yield_range_quintals_per_acre[0]} - {matched_rec.expected_yield_range_quintals_per_acre[1]} quintals/acre",
            f"- **Estimated Net Profit**: ₹{matched_rec.estimated_net_profit_per_acre_inr:,.0f}/acre (approx. ₹{profit_total:,.0f} total net profit)",
            f"- **Soil & Water Compatibility**: Soil: `{matched_rec.soil_compatibility}` | Water: `{matched_rec.water_compatibility}`",
            f"- **Budget Feasibility**: `{matched_rec.budget_feasibility}`",
        ]
        if matched_rec.key_strengths:
            lines.append(f"- **Key Strengths**: {', '.join(matched_rec.key_strengths)}")
        if matched_rec.risk_factors:
            lines.append(f"- **Key Risks**: {', '.join(matched_rec.risk_factors)}")
        if crop_profile and crop_profile.advisory_notes:
            lines.append(f"- **Agronomic Advisory**: {crop_profile.advisory_notes}")
        return "\n".join(lines)

    # 2. If asking for a summary or repeat of recommendations
    if any(k in lower for k in ["summarize", "summary", "repeat", "previous", "earlier", "what did you recommend", "what did you suggest", "సారాంశం", "మునుపటి", "గత సిఫార్సు"]):
        if lang == "te":
            soil_te = TELUGU_SOIL_MAP.get(req.soil_type, req.soil_type.value)
            season_te = TELUGU_SEASON_MAP.get(req.season, req.season.value)
            water_te = TELUGU_WATER_MAP.get(req.water_availability, req.water_availability.value)

            lines = [
                f"🌾 **మునుపటి పంటల సిఫార్సుల సారాంశం ({req.state})**",
                f"**పొలం**: {req.land_size_acres:.1f} ఎకరాలు | **సీజన్**: {season_te} | **నేల**: {soil_te} | **నీటి వసతి**: {water_te} | **బడ్జెట్**: ₹{req.budget_inr:,.0f}",
                "",
                "**సిఫార్సు చేయబడిన ప్రధాన పంటలు**:"
            ]
            for idx, crop in enumerate(resp.primary_recommendations, 1):
                c_meta = TELUGU_CROPS.get(crop.crop_name, {})
                name_te = c_meta.get("name_te", crop.crop_name)
                lines.append(
                    f"{idx}. **{name_te}** ({crop.crop_name}) — స్కోర్: `{crop.suitability_score}/100`, "
                    f"ఎకరానికి ఖర్చు: ₹{crop.estimated_cost_per_acre_inr:,.0f}, అంచనా నికర లాభం: ₹{crop.estimated_net_profit_per_acre_inr:,.0f}/ఎకరం"
                )
            if resp.alternative_recommendations:
                lines.append("\n**ప్రత్యామ్నాయ పంటల అవకాశాలు**:")
                for alt in resp.alternative_recommendations:
                    alt_meta = TELUGU_CROPS.get(alt.crop_name, {})
                    alt_name_te = alt_meta.get("name_te", alt.crop_name)
                    lines.append(
                        f"- **{alt_name_te}** ({alt.crop_name}) — స్కోర్: `{alt.suitability_score}/100`, ఎకరానికి ఖర్చు: ₹{alt.estimated_cost_per_acre_inr:,.0f}"
                    )
            return "\n".join(lines)

        lines = [
            f"🌾 **Summary of Previous Recommendations for {req.state}**",
            f"**Holding**: {req.land_size_acres:.1f} Acres | **Season**: {req.season.value.upper()} | **Soil**: {req.soil_type.value.title()} | **Water**: {req.water_availability.value.title()} | **Budget**: ₹{req.budget_inr:,.0f}",
            "",
            "**Primary Recommended Crops**:"
        ]
        for idx, crop in enumerate(resp.primary_recommendations, 1):
            lines.append(
                f"{idx}. **{crop.crop_name}** ({crop.hindi_name}) — Score: `{crop.suitability_score}/100`, "
                f"Cost/ac: ₹{crop.estimated_cost_per_acre_inr:,.0f}, Est. Net Profit: ₹{crop.estimated_net_profit_per_acre_inr:,.0f}/ac"
            )
        if resp.alternative_recommendations:
            lines.append("\n**Diversification Options**:")
            for alt in resp.alternative_recommendations:
                lines.append(
                    f"- **{alt.crop_name}** ({alt.hindi_name}) — Score: `{alt.suitability_score}/100`, Cost/ac: ₹{alt.estimated_cost_per_acre_inr:,.0f}"
                )
        return "\n".join(lines)

    # 3. General follow-up inquiry based on previous plot
    if lang == "te":
        soil_te = TELUGU_SOIL_MAP.get(req.soil_type, req.soil_type.value)
        season_te = TELUGU_SEASON_MAP.get(req.season, req.season.value)
        water_te = TELUGU_WATER_MAP.get(req.water_availability, req.water_availability.value)

        primary_names = []
        for c in resp.primary_recommendations:
            c_meta = TELUGU_CROPS.get(c.crop_name, {})
            primary_names.append(c_meta.get("name_te", c.crop_name))

        lines = [
            f"🌾 **మీ {req.state} పొలానికి తదుపరి సలహాలు**",
            f"మీ {req.land_size_acres:.1f} ఎకరాల పొలం ({season_te}, {soil_te}, {water_te}) ఆధారంగా:",
            f"- **ప్రధాన సిఫార్సులు**: {', '.join(primary_names) if primary_names else 'ఏవీ లేవు'}",
            f"- **కేటాయించిన బడ్జెట్**: ₹{req.budget_inr:,.0f} (ఎకరానికి ₹{req.budget_inr / req.land_size_acres:,.0f})",
            "",
            "**ముఖ్యమైన నిర్ణయ కారణాలు**:"
        ]
        for step in resp.step_by_step_reasoning[:2]:
            lines.append(f"- {step}")
        lines.append("\nమీరు నిర్దిష్ట పంటల సాగు, తెగుళ్ల నివారణ, వ్యయ వివరాల గురించి అడగవచ్చు లేదా కొత్త పొలం వివరాలను ఎప్పుడైనా పంపవచ్చు.")
        return "\n".join(lines)

    lines = [
        f"🌾 **Follow-Up Consultation for Your {req.state} Farm**",
        f"Based on your {req.land_size_acres:.1f}-acre farm in {req.state} for {req.season.value.upper()} season with {req.water_availability.value} water availability:",
        f"- **Primary recommendations**: {', '.join(c.crop_name for c in resp.primary_recommendations) if resp.primary_recommendations else 'None'}",
        f"- **Budget allocation**: ₹{req.budget_inr:,.0f} (₹{req.budget_inr / req.land_size_acres:,.0f}/acre)",
        "",
        "**Multi-Step Decision Insights**:"
    ]
    for step in resp.step_by_step_reasoning[:2]:
        lines.append(f"- {step}")
    lines.append("\nYou can ask about specific crop agronomy, risk factors, cost breakdowns, or submit a new farm profile anytime.")
    return "\n".join(lines)


def format_acp_recommendation_telugu(response: RecommendationResponse, req: FarmerProfileRequest) -> str:
    """Formats the decision response into simple, farmer-friendly Telugu for ACP."""
    budget_per_acre = req.budget_inr / req.land_size_acres
    soil_te = TELUGU_SOIL_MAP.get(req.soil_type, req.soil_type.value)
    season_te = TELUGU_SEASON_MAP.get(req.season, req.season.value)
    water_te = TELUGU_WATER_MAP.get(req.water_availability, req.water_availability.value)

    lines = [
        f"### 🌾 అగ్రిసారథి పంటల సిఫార్సు: {req.state}",
        f"**రైతు పొలం వివరాలు**: {req.land_size_acres:.1f} ఎకరాలు | **సీజన్**: {season_te} | **నేల**: {soil_te} | **నీటి లభ్యత**: {water_te}",
        f"**కేటాయించిన బడ్జెట్**: ₹{req.budget_inr:,.0f} (ఎకరానికి ₹{budget_per_acre:,.0f})",
        "",
        "---",
        "#### 🏆 అత్యంత అనుకూలమైన ప్రధాన పంటలు",
    ]

    if not response.primary_recommendations:
        lines.append("*మీరు పేర్కొన్న నేల మరియు నీటి పరిస్థితులకు సరిపోయే పంటలు ఏవీ రిస్క్ లేకుండా అందుబాటులో లేవు.*")
    else:
        for idx, crop in enumerate(response.primary_recommendations, 1):
            crop_meta = TELUGU_CROPS.get(crop.crop_name, {})
            name_te = crop_meta.get("name_te", crop.crop_name)
            category_te = crop_meta.get("category_te", crop.category)
            adv_te = crop_meta.get("advantage_te", crop.key_strengths[0] if crop.key_strengths else "ప్రాంతీయ అనుకూలత కలిగిన పంట")
            risk_te = crop_meta.get("risk_te", crop.risk_factors[0] if crop.risk_factors else "సాధారణ చీడపీడల యాజమాన్యం అవసరం")
            sowing_notes = crop_meta.get("sowing_notes", "")

            lines.extend([
                f"**{idx}. {name_te}** ({crop.crop_name}) — *అనుకూలత స్కోర్: {crop.suitability_score}/100*",
                f"- **పంట వర్గం**: {category_te} | **బడ్జెట్ సాధ్యత**: అనుకూలం",
                f"- **ఎకరానికి ఖర్చు (అంచనా)**: ₹{crop.estimated_cost_per_acre_inr:,.0f} *(మొత్తం {req.land_size_acres:.1f} ఎకరాలకు: ₹{crop.total_estimated_cost_inr:,.0f})*",
                f"- **ఆశించే దిగుబడి**: {crop.expected_yield_range_quintals_per_acre[0]} - {crop.expected_yield_range_quintals_per_acre[1]} క్వింటాళ్లు/ఎకరానికి",
                f"- **అంచనా నికర లాభం**: ₹{crop.estimated_net_profit_per_acre_inr:,.0f}/ఎకరానికి (అంచనా మాత్రమే)",
                f"- **నీటి అవసరం**: {water_te}తో సరిపోతుంది",
                f"- **ప్రధాన ప్రయోజనం**: {adv_te}",
                f"- **గమనించవలసిన రిస్క్**: {risk_te}",
            ])
            if sowing_notes:
                lines.append(f"- **సాగు & విత్తే సూచన**: {sowing_notes}")
            lines.append("")

    if response.alternative_recommendations:
        lines.append("#### 🔄 ప్రత్యామ్నాయ పంటల అవకాశాలు")
        for alt in response.alternative_recommendations:
            alt_meta = TELUGU_CROPS.get(alt.crop_name, {})
            alt_name_te = alt_meta.get("name_te", alt.crop_name)
            lines.append(
                f"- **{alt_name_te}** ({alt.crop_name}): స్కోర్ `{alt.suitability_score}/100`, "
                f"ఎకరానికి ఖర్చు: ₹{alt.estimated_cost_per_acre_inr:,.0f}, అంచనా నికర లాభం: ₹{alt.estimated_net_profit_per_acre_inr:,.0f}/ఎకరం"
            )
        lines.append("")

    lines.append("#### 🧠 నిర్ణయ విశ్లేషణ & కారణాలు")
    for step in response.step_by_step_reasoning:
        lines.append(f"- {step}")

    lines.append("")
    lines.append("#### ⚠️ రైతులకు ముఖ్య గమనిక & పరిమితులు")
    lines.append("- **మట్టి పరీక్ష**: విత్తే ముందు సాయిల్ హెల్త్ కార్డ్ (SHC) ద్వారా మట్టి పరీక్ష చేయించి పోషకాలు సరిచూసుకోండి.")
    lines.append("- **ధరల హెచ్చుతగ్గులు**: స్థానిక మార్కెట్ / మండి ధరలు నాణ్యత మరియు డిమాండ్‌ను బట్టి మారవచ్చు. ఇవి ప్రభుత్వ MSP ఆధారిత అంచనాలు మాత్రమే.")
    lines.append("- **వాతావరణం**: విత్తే తేదీలను స్థానిక IMD వర్ష సూచనలకు అనుగుణంగా నిర్ణయించుకోండి.")

    return "\n".join(lines)


def format_acp_recommendation(
    response: RecommendationResponse,
    req: FarmerProfileRequest,
    lang: str = "en",
) -> str:
    """Formats the decision response into structured Markdown for ACP (English or Telugu)."""
    if lang == "te":
        return format_acp_recommendation_telugu(response, req)

    budget_per_acre = req.budget_inr / req.land_size_acres
    lines = [
        f"### 🌾 AgriSaarthi Crop Advisory: {req.state}",
        f"**Plot Profile**: {req.land_size_acres:.1f} Acres | **Season**: {req.season.value.upper()} | **Soil**: {req.soil_type.value.title()} | **Water**: {req.water_availability.value.title()}",
        f"**Budget Allocated**: ₹{req.budget_inr:,.0f} (₹{budget_per_acre:,.0f}/acre) [{response.budget_summary.get('status', 'NORMAL')}]",
        "",
        "---",
        "#### 🏆 Top Primary Recommendations",
    ]

    if not response.primary_recommendations:
        lines.append("*No crops in the reference catalog meet all strict criteria without severe risk.*")
    else:
        for idx, crop in enumerate(response.primary_recommendations, 1):
            lines.extend([
                f"**{idx}. {crop.crop_name}** ({crop.hindi_name}) — *Suitability Score: {crop.suitability_score}/100*",
                f"- **Category**: {crop.category} | **Budget Status**: {crop.budget_feasibility}",
                f"- **Cost / Acre**: ₹{crop.estimated_cost_per_acre_inr:,.0f} *(Total for {req.land_size_acres:.1f} ac: ₹{crop.total_estimated_cost_inr:,.0f})*",
                f"- **Expected Yield**: {crop.expected_yield_range_quintals_per_acre[0]} - {crop.expected_yield_range_quintals_per_acre[1]} quintals/acre",
                f"- **Est. Net Profit**: ₹{crop.estimated_net_profit_per_acre_inr:,.0f}/acre",
                f"- **Water & Soil Compatibility**: Water: `{crop.water_compatibility}` | Soil: `{crop.soil_compatibility}`",
                f"- **Key Advantage**: {crop.key_strengths[0] if crop.key_strengths else 'High regional suitability'}",
                f"- **Key Risk**: {crop.risk_factors[0] if crop.risk_factors else 'Standard pest/climate monitoring needed'}",
                "",
            ])

    if response.alternative_recommendations:
        lines.append("#### 🔄 Diversification & Hedging Options")
        for alt in response.alternative_recommendations:
            lines.append(
                f"- **{alt.crop_name}** ({alt.hindi_name}): Score `{alt.suitability_score}/100`, "
                f"Cost: ₹{alt.estimated_cost_per_acre_inr:,.0f}/ac, Est. Net Profit: ₹{alt.estimated_net_profit_per_acre_inr:,.0f}/ac"
            )
        lines.append("")

    lines.append("#### 🧠 Multi-Step Decision Reasoning")
    for step in response.step_by_step_reasoning:
        lines.append(f"- {step}")

    lines.append("")
    lines.append("#### ⚠️ Agronomic Advisory & Practical Limitations")
    for lim in response.limitations_and_advisory[:3]:
        lines.append(f"- {lim}")

    return "\n".join(lines)


def _generate_help_message(error_detail: str) -> str:
    """Generate friendly guide when input cannot be parsed."""
    return (
        f"🌾 **AgriSaarthi AI — Decision Support Error**\n\n"
        f"**Issue**: {error_detail}\n\n"
        "To get accurate, climate-smart crop recommendations, please provide:\n"
        "- **state**: e.g., 'Punjab', 'Maharashtra', 'Rajasthan', 'Telangana'\n"
        "- **land_size_acres**: Farm holding size (e.g., 5.0)\n"
        "- **soil_type**: `alluvial`, `black`, `red`, `sandy_loam`, `clayey`, `laterite`\n"
        "- **water_availability**: `low` (limited/rainfed), `moderate` (tubewell/borewell), `high` (canal)\n"
        "- **season**: `kharif` (monsoon), `rabi` (winter), `zaid` (summer)\n"
        "- **budget_inr**: Total seasonal budget in INR (e.g., 80000)\n\n"
        "**Example JSON format**:\n"
        "```json\n"
        "{\n"
        '  "state": "Punjab",\n'
        '  "land_size_acres": 5.0,\n'
        '  "soil_type": "alluvial",\n'
        '  "water_availability": "moderate",\n'
        '  "season": "rabi",\n'
        '  "budget_inr": 110000\n'
        "}\n"
        "```"
    )


def _generate_welcome_message(lang: str = "en") -> str:
    """Generate friendly welcome guide for new sessions or greeting prompts."""
    if lang == "te":
        return (
            "🌾 **నమస్కారం! నేను అగ్రిసారథి AI (AgriSaarthi AI)**, మీ నమ్మకమైన వ్యవసాయ సలహాదారుని.\n\n"
            "భారతీయ రైతులకు వారి భూమి విస్తీర్ణం, నేల రకం, నీటి వసతి, నాట్లు వేసే కాలం (సీజన్) మరియు బడ్జెట్‌కు తగిన "
            "అత్యంత అనుకూలమైన, వాతావరణాన్ని తట్టుకునే లాభదాయకమైన పంటలను ఎంచుకోవడంలో నేను తోడ్పడతాను.\n\n"
            "**మీరు నాతో మూడు విధాలుగా మాట్లాడవచ్చు**:\n"
            "1. **పంటల సిఫార్సు**: మీ పొలం వివరాలు చెప్పండి (రాష్ట్రం/జిల్లా, ఎకరాలు, నేల, నీటి వసతి, సీజన్, బడ్జెట్).\n"
            "2. **సందేహాలు & వివరాలు**: పంటల దిగుబడి, పెట్టుబడి వ్యయం, లాభం లేదా రిస్కుల గురించి వివరంగా అడగండి.\n"
            "3. **డేటా మూలాలు**: మా CACP/ICAR ప్రామాణిక నివేదికలు, లెక్కింపు పద్ధతులు లేదా పరిమితుల గురించి తెలుసుకోండి.\n\n"
            "**ఉదాహరణ సందేశం**:\n"
            "*'తెలంగాణలో 4 ఎకరాల నల్ల నేల ఉంది, ఖరీఫ్ సీజన్, బోరు బావి నీరు, బడ్జెట్ 1 లక్ష'*"
        )

    return (
        "🌾 **Namaste! I am AgriSaarthi AI**, your autonomous agricultural decision assistant.\n\n"
        "I assist Indian farmers in choosing the most suitable, climate-resilient, and profitable crops "
        "tailored to your exact land holding, soil type, water availability, planting season, and budget.\n\n"
        "**You can interact with me in three ways**:\n"
        "1. **Crop Recommendations**: Provide your farm profile (State, Land size, Soil, Water, Season, Budget).\n"
        "2. **Follow-Up Inquiries**: Ask deep-dive questions about crops, risks, yield, or profitability.\n"
        "3. **Methodology & Data Questions**: Ask about our CACP/ICAR sources, calculations, or limitations.\n\n"
        "**Example prompt**:\n"
        "*'I have 5 acres of alluvial soil in Punjab with limited irrigation for Rabi season, budget 100000'*"
    )


def _generate_missing_fields_message(missing: List[str], original_text: str, lang: str = "en") -> str:
    """Generate diagnostic message when specific fields are missing for a new recommendation."""
    missing_te_map = {
        "state": "రాష్ట్రం లేదా జిల్లా (ఉదా: తెలంగాణ, ఆంధ్రప్రదేశ్, వరంగల్, గుంటూరు)",
        "season": "సీజన్ ('ఖరీఫ్' / వానాకాలం, 'రబీ' / యాసంగి, 'జైద్' / వేసవి)",
        "soil_type": "నేల రకం ('నల్ల రేగడి', 'ఎర్ర నేల', 'ఒండ్రు నేల', 'ఇసుక నేల', 'బంకమట్టి')",
        "water_availability": "నీటి వసతి ('మోస్తరు నీరు' / బోరు బావి, 'పరిమిత నీరు' / వర్షాధారం, 'కాలువ నీరు')",
        "land_size_acres": "భూమి విస్తీర్ణం ఎకరాల్లో (ఉదా: 2 ఎకరాలు)",
        "budget_inr": "పెట్టుబడి బడ్జెట్ (ఉదా: ₹40,000 లేదా 1 లక్ష)",
    }

    clean_keys = [m.split()[0] for m in missing]

    if lang == "te":
        if len(clean_keys) == 1:
            desc = missing_te_map.get(clean_keys[0], clean_keys[0])
            return (
                f"🌾 **అగ్రిసారథి AI — వ్యవసాయ వివరాలు**\n\n"
                f"మీరు అందించిన మిగతా పొలం వివరాలు నమోదయ్యాయి. దయచేసి కేవలం మీ **{desc}** వివరాలను తెలియజేయండి.\n\n"
                f"ఆ వివరాలు అందించిన వెంటనే మీ పొలానికి అత్యంత అనుకూలమైన పంటల సిఫార్సులను అందిస్తాను."
            )

        missing_items = [f"- **{missing_te_map.get(k, k)}**" for k in clean_keys]
        items_str = "\n".join(missing_items)
        return (
            f"🌾 **అగ్రిసారథి AI — అసంపూర్ణ వ్యవసాయ వివరాలు**\n\n"
            f"మీ పొలానికి సరిగ్గా సరిపోయే పంటల సిఫార్సు కోసం, దయచేసి కింది వివరాలను తెలియజేయండి:\n{items_str}\n\n"
            f"**మీ సందేశం**: *\"{original_text}\"*"
        )

    # English friendly mappings
    friendly_en_map = {
        "state": "State or District (e.g., Telangana, Punjab, Maharashtra)",
        "season": "Season ('kharif', 'rabi', or 'zaid')",
        "soil_type": "Soil type ('black', 'alluvial', 'red', 'sandy_loam', 'clayey')",
        "water_availability": "Water availability ('low' / rainfed, 'moderate' / borewell, 'high' / canal)",
        "land_size_acres": "Land holding size in acres (e.g., 2.0 acres)",
        "budget_inr": "Total seasonal budget in INR (e.g., ₹40,000)",
    }

    if len(clean_keys) == 1:
        desc = friendly_en_map.get(clean_keys[0], clean_keys[0])
        return (
            f"🌾 **AgriSaarthi AI — Farm Detail Required**\n\n"
            f"Your other farm parameters have been recorded. Please provide only your **{desc}** (`{clean_keys[0]}`) to generate the recommendation."
        )

    missing_items = "\n".join(f"- **{friendly_en_map.get(k, k)}** (`{k}`)" for k in clean_keys)
    return (
        f"🌾 **AgriSaarthi AI — Incomplete Farm Profile**\n\n"
        f"To generate an accurate crop recommendation, please provide the following missing details:\n{missing_items}\n\n"
        f"**Your Message**: *\"{original_text}\"*"
    )


# =============================================================================
# Master Message Processor (Dispatches Across Intents & Languages)
# =============================================================================

def process_chat_message(
    text: str,
    sender: str,
    engine_cls=AgriSaarthiEngine,
    ctx: Optional[Context] = None,
) -> str:
    """
    Main entry point for ACP messages.
    Determines intent, language, preserves session context, and generates the appropriate response.
    """
    clean_text = text.strip()
    # Strip leading @mentions from chat platforms (e.g. @agrisaarthi-ai)
    clean_text = re.sub(r"^@\S+\s*", "", clean_text)
    session = get_session(sender)

    if not clean_text:
        return _generate_welcome_message(lang=session.preferred_language)

    # 0. Check language detection and explicit language switches
    lang = detect_language(clean_text, session)
    session.set_language(lang)

    # Check for pure language switch command
    pure_switch = is_pure_language_switch(clean_text)
    if pure_switch:
        session.set_language(pure_switch)
        if pure_switch == "te":
            if session.last_response is not None and session.last_request is not None:
                return format_acp_recommendation_telugu(session.last_response, session.last_request)
            return (
                "🌾 ఇకపై సమాధానాలు **తెలుగులో** ఉంటాయి. మీ వ్యవసాయ సలహా కోసం మీ భూమి విస్తీర్ణం, "
                "రాష్ట్రం/జిల్లా, నేల రకం, సీజన్, నీటి వసతి మరియు బడ్జెట్ వివరాలను చెప్పండి."
            )
        else:
            if session.last_response is not None and session.last_request is not None:
                return format_acp_recommendation(session.last_response, session.last_request, lang="en")
            return (
                "🌾 Language preference set to **English**. How can I assist your farm today? "
                "Please provide your land size, state, soil type, season, water availability, and budget."
            )

    # 1. Greetings
    if is_greeting(clean_text):
        return _generate_welcome_message(lang=lang)

    # 2. Source, Data Origin, Live Weather, Mandi Prices, Methodology Questions
    if is_source_or_data_query(clean_text):
        logger.info(f"Routing '{clean_text[:40]}...' to SOURCE_OR_DATA_QUERY handler (lang={lang})")
        return _handle_source_or_data_query(clean_text, session, lang=lang)

    # 3. Queries explicitly asking about past recommendations
    if is_query_about_previous_recommendation(clean_text):
        return _handle_follow_up_query(clean_text, session, lang=lang)

    # 4. Follow-up inquiries on previous recommendation
    if session.last_response is not None and is_follow_up_query(clean_text, session):
        logger.info(f"Routing '{clean_text[:40]}...' to FOLLOW_UP handler (lang={lang})")
        return _handle_follow_up_query(clean_text, session, lang=lang)

    # 5. New recommendation attempt or completion of pending profile
    has_pending = bool(session.pending_profile)
    if is_new_recommendation_attempt(clean_text) or (has_pending and not is_greeting(clean_text) and not is_source_or_data_query(clean_text)):
        logger.info(f"Routing '{clean_text[:40]}...' to NEW_RECOMMENDATION parser (lang={lang}, pending={has_pending})")
        profile_req, err_msg = parse_chat_query(clean_text, session=session)

        if profile_req:
            try:
                response = engine_cls.execute(profile_req)
                session.update(profile_req, response)
                return format_acp_recommendation(response, profile_req, lang=lang)
            except Exception as e:
                logger.exception(f"Error executing recommendation engine: {e}")
                if lang == "te":
                    return f"🌾 **అగ్రిసారథి ప్రాసెసింగ్ లోపం**: పంట అనుకూలత లెక్కింపులో లోపం ఏర్పడింది: {str(e)}"
                return f"🌾 **AgriSaarthi Processing Error**: An unexpected error occurred while calculating crop suitability: {str(e)}"
        else:
            return err_msg

    # 6. Fallback: If session context exists, try follow-up query; otherwise provide guidance
    if session.last_response is not None:
        return _handle_follow_up_query(clean_text, session, lang=lang)

    # If message has agricultural words, request the missing fields
    extracted, missing = _extract_entities_from_text(clean_text)
    if missing and len(missing) < 6:
        if session:
            session.update_pending_profile(extracted)
        return _generate_missing_fields_message(missing, clean_text, lang=lang)

    return _generate_welcome_message(lang=lang)


# =============================================================================
# Protocol Factory
# =============================================================================

def create_chat_protocol(engine_cls=AgriSaarthiEngine) -> Protocol:
    """
    Factory creating a verified Agent Chat Protocol (ACP v0.3.0) Protocol instance.
    """
    chat_proto = Protocol(spec=chat_protocol_spec)

    @chat_proto.on_message(ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        ctx.logger.info(f"Received ChatMessage from {sender} (msg_id={msg.msg_id})")

        # 1. Standard ACP Acknowledgement
        try:
            ack = ChatAcknowledgement(acknowledged_msg_id=msg.msg_id)
            await ctx.send(sender, ack)
            ctx.logger.info(f"Sent ChatAcknowledgement for msg_id={msg.msg_id} to {sender}")
        except Exception as e:
            ctx.logger.warning(f"Could not send ChatAcknowledgement: {e}")

        # 2. Check for ACP Session Lifecycle content
        has_start_session = any(isinstance(c, StartSessionContent) for c in msg.content)
        has_end_session = any(isinstance(c, EndSessionContent) for c in msg.content)

        session = get_session(sender)

        if has_start_session:
            reply_text = _generate_welcome_message(lang=session.preferred_language)
        elif has_end_session:
            lang = session.preferred_language
            reset_session(sender)
            if lang == "te":
                reply_text = (
                    "🌾 **అగ్రిసారథి AI** ని సంప్రదించినందుకు ధన్యవాదాలు. "
                    "మీ పంటలు సమృద్ధిగా పండి మంచి దిగుబడులు సాధించాలని ఆశిస్తున్నాము!"
                )
            else:
                reply_text = (
                    "🌾 Thank you for consulting **AgriSaarthi AI**. "
                    "Wishing you a successful planting season and a prosperous harvest!"
                )
        else:
            # 3. Process message across intents with conversational context
            incoming_text = msg.text()
            ctx.logger.info(f"Processing chat content: '{incoming_text[:80]}...'")
            reply_text = process_chat_message(
                text=incoming_text,
                sender=sender,
                engine_cls=engine_cls,
                ctx=ctx,
            )

        # 4. Send formatted markdown response in ChatMessage wrapper
        reply_message = ChatMessage(content=[TextContent(text=reply_text)])
        await ctx.send(sender, reply_message)
        ctx.logger.info(f"Dispatched ChatMessage response to {sender}")

    @chat_proto.on_message(ChatAcknowledgement)
    async def handle_chat_acknowledgement(ctx: Context, sender: str, msg: ChatAcknowledgement):
        ctx.logger.info(f"Received ChatAcknowledgement from {sender} for message {msg.acknowledged_msg_id}")

    return chat_proto
