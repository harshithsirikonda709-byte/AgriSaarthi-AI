"""
Farmer Web Portal & Voice Demo Server for AgriSaarthi AI.
Provides:
  - Responsive multi-page Farmer Portal (Home, Login, Register, Dashboard,
    Crop Advisory, Crop Health, Weather & Alerts, Voice Assistant, Farmer Profile)
  - Secure SQLite + PBKDF2-HMAC-SHA256 authentication & session management
  - Structured REST APIs connected to AgriSaarthiEngine, CROP_DATABASE,
    CROP_DISORDER_DATABASE, Ollama (qwen2.5:0.5b), and Open-Meteo weather
  - Backward-compatible `/`, `/api/model-status`, and `/api/chat` endpoints
Uses Python standard library (http.server, sqlite3, urllib, hashlib) — zero extra dependencies.
"""

import os
import sys
import io
import re
import json
import logging
import mimetypes
import urllib.parse
import urllib.request
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

from agrisaarthi.models import FarmerProfileRequest
from agrisaarthi.engine import AgriSaarthiEngine
from agrisaarthi.data.crops import CROP_DATABASE
from agrisaarthi.data.crop_diagnostics import (
    CROP_DISORDER_DATABASE,
    find_matching_crop_disorder,
)
from agrisaarthi.chat_protocol import (
    process_chat_message,
    TELUGU_CROPS,
    TELUGU_SOIL_MAP,
    TELUGU_SEASON_MAP,
    TELUGU_WATER_MAP,
    HINDI_CROPS,
    HINDI_SOIL_MAP,
    HINDI_SEASON_MAP,
    HINDI_WATER_MAP,
)
from agrisaarthi.storage import (
    FarmerStorage,
    AuthValidationError,
    InvalidCredentialsError,
)
from agrisaarthi.weather_service import fetch_weather_and_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agrisaarthi.ui_server")

port_env = os.getenv("AGRI_UI_PORT") or os.getenv("AGRI_PORT")
PORT = int(port_env) if port_env else 8080
for _idx, _arg in enumerate(sys.argv):
    if _arg == "--port" and _idx + 1 < len(sys.argv):
        PORT = int(sys.argv[_idx + 1])
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

_STORAGE_INSTANCE: Optional[FarmerStorage] = None


def get_storage() -> FarmerStorage:
    """Return a singleton or test-configured FarmerStorage instance."""
    global _STORAGE_INSTANCE
    db_path = os.getenv("AGRI_DB_PATH")
    if _STORAGE_INSTANCE is None or (db_path and _STORAGE_INSTANCE.db_path != db_path):
        _STORAGE_INSTANCE = FarmerStorage(db_path=db_path)
    return _STORAGE_INSTANCE


def sanitize_ai_reply_for_farmer(reply: str) -> str:
    """
    Sanitize AI reply so farmers only see verified, professional recommendations.
    Strips internal Ollama notices, model availability debug banners, and LLM headers.
    """
    if not reply:
        return ""
    # Strip [Ollama Notice: ...] or ⚠️ *[Ollama Notice: ...]*
    cleaned = re.sub(r'⚠️\s*\*\[Ollama Notice:[^\]]*\]\*\s*\n*', '', reply, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[Ollama Notice:[^\]]*\]\s*\n*', '', cleaned, flags=re.IGNORECASE)
    # Strip 🤖 **[Ollama: ...]** headers
    cleaned = re.sub(r'🤖\s*\*\*\[Ollama:[^\]]*\]\*\*\s*\n*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\*\*\[Ollama:[^\]]*\]\*\*\s*\n*', '', cleaned, flags=re.IGNORECASE)
    # Strip model fallback notices or Ollama availability messages
    cleaned = re.sub(r'⚠️\s*\*\[[^\]]*unavailable[^\]]*\]\*\s*\n*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[Notice:[^\]]*\]\s*\n*', '', cleaned, flags=re.IGNORECASE)
    # Clean any leftover divider if it was separating LLM header from advisory
    cleaned = re.sub(r'^\s*---\s*\n+', '', cleaned)
    return cleaned.strip()


def generate_tts_audio(text: str, lang: str = "te") -> bytes:
    """
    Generate natural Text-to-Speech MP3 audio for agricultural queries.
    Uses gTTS with automatic chunking and fallback to direct Google TTS stream.
    Supports Telugu ('te'), Hindi ('hi'), and English ('en').
    """
    clean = sanitize_ai_reply_for_farmer(text)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"[*_#`~>]", "", clean)
    clean = re.sub(r"https?://\S+", "", clean)
    clean = re.sub(r"\{[^\}]*\}", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    if not clean:
        raise ValueError("Text cannot be empty for TTS synthesis.")

    lang_code = "te"
    if lang:
        l = str(lang).lower().split("-")[0]
        if l in ("te", "hi", "en"):
            lang_code = l

    # 1. Try gTTS first
    if gTTS is not None:
        try:
            fp = io.BytesIO()
            tts = gTTS(text=clean, lang=lang_code, slow=False)
            tts.write_to_fp(fp)
            data = fp.getvalue()
            if data:
                return data
        except Exception as e:
            logger.warning(f"gTTS error: {e}, falling back to direct stream")

    # 2. Fallback to direct chunked Google Translate TTS HTTP stream
    words = clean.split()
    chunks = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 <= 160:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = w
    if cur:
        chunks.append(cur)

    audio_bytes = bytearray()
    for chunk in chunks[:15]:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang_code}&client=tw-ob&q={urllib.parse.quote(chunk)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            audio_bytes.extend(resp.read())

    if not audio_bytes:
        raise RuntimeError(f"Unable to generate TTS audio for language {lang_code}.")

    return bytes(audio_bytes)


class AgriFarmerUIHandler(BaseHTTPRequestHandler):
    """Handles static web requests, authentication, farmer dashboard, and AI decision calls."""

    def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body_bytes)

    def _read_json_body(self) -> Dict[str, Any]:
        headers = getattr(self, "headers", None) or {}
        try:
            content_length = int(headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0
        if content_length <= 0:
            return {}
        try:
            raw = self.rfile.read(content_length).decode("utf-8")
        except UnicodeDecodeError:
            raise AuthValidationError("Request body must be valid UTF-8 text.")
        if not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            raise AuthValidationError(f"Invalid JSON in request body: {e}")
        if not isinstance(parsed, dict):
            raise AuthValidationError("Request payload must be a JSON object.")
        return parsed

    def _extract_bearer_token(self) -> Optional[str]:
        headers = getattr(self, "headers", None) or {}
        auth_header = headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return None

    def _require_authenticated_farmer(self) -> Optional[Dict[str, Any]]:
        token = self._extract_bearer_token()
        farmer = get_storage().get_farmer_by_token(token)
        if not farmer:
            self._send_json(
                401,
                {
                    "error": "Authentication required or session expired. Please log in.",
                    "error_te": "లాగిన్ గడువు ముగిసింది లేదా లాగిన్ అవసరం. దయచేసి మళ్ళీ లాగిన్ అవ్వండి.",
                },
            )
            return None
        return farmer

    def _serve_static_file(self, rel_path: str) -> None:
        web_real = os.path.realpath(WEB_DIR)
        target_real = os.path.realpath(os.path.join(WEB_DIR, rel_path.lstrip("/\\")))
        if not target_real.startswith(web_real + os.sep) and target_real != web_real:
            self.send_error(403, "Forbidden")
            return
        if not os.path.isfile(target_real):
            self.send_error(404, "File Not Found")
            return
        mime_type, _ = mimetypes.guess_type(target_real)
        content_type = mime_type or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        with open(target_real, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)

        spa_routes = {
            "/",
            "/index.html",
            "/home",
            "/login",
            "/register",
            "/dashboard",
            "/advisory",
            "/health",
            "/weather",
            "/voice",
            "/profile",
        }

        if route in spa_routes:
            index_path = os.path.join(WEB_DIR, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")

        elif route == "/favicon.ico":
            self.send_response(204)
            self.end_headers()

        elif route == "/config.js":
            cfg = {
                "API_BASE_URL": os.getenv("AGRI_API_BASE_URL", "").rstrip("/"),
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
                "DEFAULT_LANG": "te",
                "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
                "ACP_VERSION": "0.3.0",
                "WEATHER_CONFIGURED": bool(os.getenv("WEATHER_API_BASE_URL", "https://api.open-meteo.com/v1/forecast")),
                "IMD_ALERTS_CONFIGURED": bool(os.getenv("IMD_ALERTS_FEED_URL", "").strip()),
            }
            js_body = f"window.AGRISAARTHI_CONFIG = {json.dumps(cfg, ensure_ascii=False)};\n".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(js_body)))
            self.end_headers()
            self.wfile.write(js_body)

        elif route == "/api/config":
            self._send_json(
                200,
                {
                    "api_base_url": os.getenv("AGRI_API_BASE_URL", "").rstrip("/"),
                    "environment": os.getenv("ENVIRONMENT", "development"),
                    "ollama_model": os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
                    "acp_version": "0.3.0",
                    "weather_configured": bool(os.getenv("WEATHER_API_BASE_URL", "https://api.open-meteo.com/v1/forecast")),
                    "imd_alerts_configured": bool(os.getenv("IMD_ALERTS_FEED_URL", "").strip()),
                },
            )

        elif route.startswith("/css/") or route.startswith("/js/") or route.startswith("/assets/"):
            self._serve_static_file(route)

        elif route == "/api/model-status":
            try:
                from agrisaarthi.ollama_client import OllamaClient
                client = OllamaClient()
                available, message = client.check_availability()
                data = {
                    "available": available,
                    "model": client.model,
                    "base_url": client.base_url,
                    "message": message,
                }
                self._send_json(200, data)
            except Exception as e:
                self._send_json(200, {"available": False, "error": str(e)})

        elif route == "/api/crops":
            crops_list = []
            for c in CROP_DATABASE:
                te_info = TELUGU_CROPS.get(c.name, {})
                crops_list.append(
                    {
                        "id": c.id,
                        "name": c.name,
                        "name_te": te_info.get("name_te", c.name),
                        "hindi_name": c.hindi_name,
                        "category": c.category,
                        "category_te": te_info.get("category_te", c.category),
                        "seasons": [s.value for s in c.seasons],
                        "optimal_soils": [s.value for s in c.optimal_soils],
                        "water_requirement": c.water_requirement.value,
                        "cost_per_acre_inr": c.cost_per_acre_inr,
                        "yield_quintals_per_acre": list(c.yield_quintals_per_acre),
                        "expected_price_per_quintal_inr": c.expected_price_per_quintal_inr,
                        "prominent_states": list(c.prominent_states),
                        "advisory_notes": c.advisory_notes,
                        "sowing_notes_te": te_info.get("sowing_notes", ""),
                    }
                )
            self._send_json(200, {"crops": crops_list})

        elif route == "/api/crop-disorders":
            disorders = []
            for d in CROP_DISORDER_DATABASE:
                disorders.append(
                    {
                        "symptom_key": d.symptom_key,
                        "crop_name": d.crop_name,
                        "symptom_name_en": d.symptom_name_en,
                        "symptom_name_te": d.symptom_name_te,
                        "source_name": d.source_name,
                    }
                )
            self._send_json(200, {"disorders": disorders})

        elif route == "/api/weather":
            state = (query.get("state", [""])[0] or "").strip()
            district = (query.get("district", [""])[0] or "").strip()
            # If user is authenticated and didn't pass state/district, fall back to their profile
            if not state and not district:
                token = self._extract_bearer_token()
                farmer = get_storage().get_farmer_by_token(token) if token else None
                if farmer:
                    state = farmer.get("state", "")
                    district = farmer.get("district", "")
            weather_data = fetch_weather_and_alerts(state=state, district=district)
            self._send_json(200, weather_data)

        elif route == "/api/farmer/profile":
            farmer = self._require_authenticated_farmer()
            if not farmer:
                return
            self._send_json(200, {"farmer": farmer})

        elif route == "/api/farmer/history":
            farmer = self._require_authenticated_farmer()
            if not farmer:
                return
            history = get_storage().get_advisory_history(farmer["id"], limit=20)
            self._send_json(200, {"history": history})

        elif route == "/api/farmer/dashboard":
            farmer = self._require_authenticated_farmer()
            if not farmer:
                return
            try:
                history = get_storage().get_advisory_history(farmer["id"], limit=10)
            except Exception as e:
                logger.warning(f"Failed to fetch advisory history: {e}")
                history = []
            try:
                weather = fetch_weather_and_alerts(
                    state=farmer.get("state", ""),
                    district=farmer.get("district", ""),
                )
            except Exception as e:
                logger.warning(f"Failed to fetch weather: {e}")
                weather = {
                    "available": False,
                    "is_live": False,
                    "state": farmer.get("state", ""),
                    "district": farmer.get("district", ""),
                    "message": "Weather service temporarily unavailable.",
                    "current": None,
                    "daily_forecast": [],
                }
            self._send_json(
                200,
                {
                    "farmer": farmer,
                    "history": history,
                    "weather": weather,
                },
            )

        elif route == "/api/tts":
            try:
                query = parse_qs(parsed.query)
                text = (query.get("text", [""])[0] or "").strip()
                lang = (query.get("lang", ["te"])[0] or "te").strip()
                if not text:
                    self._send_json(400, {"error": "Text parameter is required for speech synthesis."})
                    return

                audio_data = generate_tts_audio(text=text, lang=lang)
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(audio_data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(audio_data)
            except Exception as e:
                logger.exception(f"TTS GET endpoint error: {e}")
                self._send_json(500, {"error": f"TTS synthesis failed: {e}"})

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/chat":
            headers = getattr(self, "headers", None) or {}
            content_length = int(headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            norm_lang = None
            try:
                data = json.loads(body)
                text = (data.get("text") or data.get("message") or "").strip()
                sender = data.get("sender", "farmer_voice_demo")
                req_lang = data.get("lang") or data.get("language") or data.get("response_language")

                if req_lang:
                    code = str(req_lang).lower().strip()
                    if code.startswith("te") or "telugu" in code:
                        norm_lang = "te"
                    elif code.startswith("hi") or "hindi" in code:
                        norm_lang = "hi"
                    elif code.startswith("en") or "english" in code:
                        norm_lang = "en"

                from agrisaarthi.chat_protocol import get_session
                session = get_session(sender)
                if norm_lang:
                    session.set_language(norm_lang)

                logger.info(f"Received query from UI: '{text[:60]}...' (sender={sender}, lang={norm_lang})")
                raw_reply = process_chat_message(text=text, sender=sender, language=norm_lang)
                effective_lang = norm_lang or getattr(session, "preferred_language", "en")
                model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
                clean_reply = sanitize_ai_reply_for_farmer(raw_reply)

                # If authenticated farmer is using voice/chat, store in their advisory history
                token = self._extract_bearer_token()
                if token and text:
                    farmer = get_storage().get_farmer_by_token(token)
                    if farmer:
                        get_storage().add_advisory_history(
                            farmer_id=farmer["id"],
                            advisory_type="voice_chat",
                            query_summary=text,
                            result_summary=clean_reply[:240],
                            payload={"sender": sender, "model": model_name, "language": effective_lang},
                        )

                self._send_json(200, {
                    "reply": clean_reply,
                    "model": model_name,
                    "language": effective_lang,
                    "debug_info": {
                        "model": model_name,
                        "raw_length": len(raw_reply),
                        "sender": sender,
                        "language": effective_lang
                    }
                })
            except Exception as e:
                logger.exception(f"Error handling UI chat request: {e}")
                err_lang = norm_lang or (str(req_lang).lower() if req_lang else "en")
                if "te" in err_lang:
                    friendly_reply = "మీ పంట సలహా సహాయకుడు ప్రస్తుతం అందుబాటులో లేదు. దయచేసి కాసేపటి తర్వాత మళ్ళీ ప్రయత్నించండి."
                elif "hi" in err_lang:
                    friendly_reply = "आपका फसल सलाह सहायक अस्थायी रूप से अनुपलब्ध है। कृपया कुछ समय बाद पुनः प्रयास करें।"
                else:
                    friendly_reply = "Your crop advisory assistant is temporarily unavailable. Please try again shortly."

                self._send_json(200, {
                    "reply": friendly_reply,
                    "debug_info": {
                        "error": str(e),
                        "language": err_lang
                    }
                })

        elif route == "/api/tts":
            try:
                data = self._read_json_body()
                text = (data.get("text") or "").strip()
                lang = (data.get("lang") or data.get("language") or "te").strip()
                if not text:
                    self._send_json(400, {"error": "Text is required for speech synthesis."})
                    return

                audio_data = generate_tts_audio(text=text, lang=lang)
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(len(audio_data)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(audio_data)
            except Exception as e:
                logger.exception(f"TTS POST endpoint error: {e}")
                self._send_json(500, {"error": f"TTS synthesis failed: {e}"})

        elif route == "/api/auth/register":
            try:
                data = self._read_json_body()
                farmer, token = get_storage().register_farmer(
                    full_name=data.get("full_name", ""),
                    identifier=data.get("identifier", ""),
                    password=data.get("password", ""),
                    preferred_language=data.get("preferred_language", "te"),
                    email=data.get("email"),
                    phone_number=data.get("phone_number") or data.get("phone"),
                    confirm_password=data.get("confirm_password"),
                )
                self._send_json(201, {"farmer": farmer, "token": token})
            except AuthValidationError as e:
                self._send_json(400, {"error": str(e)})
            except Exception as e:
                logger.exception(f"Registration error: {e}")
                self._send_json(500, {"error": "Server error during registration."})

        elif route == "/api/auth/login":
            try:
                data = self._read_json_body()
                farmer, token = get_storage().authenticate_farmer(
                    identifier=data.get("identifier", ""),
                    password=data.get("password", ""),
                )
                self._send_json(200, {"farmer": farmer, "token": token})
            except InvalidCredentialsError as e:
                self._send_json(401, {"error": str(e)})
            except AuthValidationError as e:
                self._send_json(400, {"error": str(e)})
            except Exception as e:
                logger.exception(f"Login error: {e}")
                self._send_json(500, {"error": "Server error during login."})

        elif route == "/api/auth/logout":
            token = self._extract_bearer_token()
            get_storage().revoke_session(token)
            self._send_json(200, {"logged_out": True})

        elif route == "/api/auth/send-otp":
            try:
                data = self._read_json_body()
                identifier = (data.get("identifier") or "").strip()
                if not identifier:
                    raise AuthValidationError("Please enter your mobile number, username, or email.")
                otp_code = get_storage().create_otp(identifier)
                self._send_json(200, {
                    "success": True,
                    "message": "OTP sent successfully.",
                    "otp": otp_code,
                    "identifier": identifier,
                })
            except AuthValidationError as e:
                self._send_json(400, {"error": str(e)})
            except Exception as e:
                logger.exception(f"Send OTP error: {e}")
                self._send_json(500, {"error": "Server error while sending OTP."})

        elif route == "/api/auth/verify-otp":
            try:
                data = self._read_json_body()
                identifier = (data.get("identifier") or "").strip()
                otp = (data.get("otp") or data.get("otp_code") or "").strip()
                if not identifier:
                    raise AuthValidationError("Please enter your mobile number, username, or email.")
                if not otp:
                    raise AuthValidationError("Please enter the 6-digit verification OTP.")
                farmer, token = get_storage().verify_otp_and_login(identifier, otp)
                self._send_json(200, {
                    "success": True,
                    "farmer": farmer,
                    "token": token,
                    "message": "OTP verified successfully.",
                })
            except AuthValidationError as e:
                self._send_json(400, {"error": str(e)})
            except InvalidCredentialsError as e:
                self._send_json(401, {"error": str(e)})
            except Exception as e:
                logger.exception(f"Verify OTP error: {e}")
                self._send_json(500, {"error": "Server error during OTP verification."})

        elif route in ("/api/auth/reset-password", "/api/auth/set-password", "/api/auth/change-password"):
            try:
                data = self._read_json_body()
                new_password = (data.get("new_password") or data.get("password") or "").strip()
                identifier = (data.get("identifier") or "").strip()
                token = self._extract_bearer_token()
                farmer = get_storage().get_farmer_by_token(token) if token else None

                if farmer:
                    get_storage().update_farmer_password(farmer["id"], new_password)
                elif identifier:
                    get_storage().reset_farmer_password(identifier, new_password)
                else:
                    raise AuthValidationError("Authentication or user identifier is required to reset password.")

                self._send_json(200, {
                    "success": True,
                    "message": "Password updated successfully."
                })
            except AuthValidationError as e:
                self._send_json(400, {"error": str(e)})
            except InvalidCredentialsError as e:
                self._send_json(401, {"error": str(e)})
            except Exception as e:
                logger.exception(f"Password update error: {e}")
                self._send_json(500, {"error": "Server error while updating password."})

        elif route == "/api/farmer/profile":
            self._handle_update_profile()

        elif route == "/api/recommend":
            self._handle_structured_recommendation()

        elif route == "/api/crop-health":
            self._handle_structured_crop_health()

        else:
            self.send_error(404, "Endpoint Not Found")

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/farmer/profile":
            self._handle_update_profile()
        else:
            self.send_error(404, "Endpoint Not Found")

    def _handle_update_profile(self) -> None:
        farmer = self._require_authenticated_farmer()
        if not farmer:
            return
        try:
            data = self._read_json_body()
            updated = get_storage().update_farmer_profile(farmer["id"], data)
            self._send_json(200, {"farmer": updated})
        except AuthValidationError as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:
            logger.exception(f"Profile update error: {e}")
            self._send_json(500, {"error": "Failed to update farmer profile."})

    def _handle_structured_recommendation(self) -> None:
        try:
            data = self._read_json_body()
            token = self._extract_bearer_token()
            farmer = get_storage().get_farmer_by_token(token) if token else None

            req_payload = {
                "farmer_id": str(farmer["id"]) if farmer else data.get("farmer_id", "portal_farmer"),
                "state": str(data.get("state", "")).strip(),
                "district": str(data.get("district", "")).strip(),
                "land_size_acres": float(data.get("land_size_acres", 0)),
                "soil_type": str(data.get("soil_type", "")).strip().lower().replace(" ", "_"),
                "water_availability": str(data.get("water_availability", "")).strip().lower(),
                "season": str(data.get("season", "")).strip().lower(),
                "budget_inr": float(data.get("budget_inr", 0)),
                "risk_tolerance": str(data.get("risk_tolerance", "moderate")).strip().lower(),
            }
            req_model = FarmerProfileRequest(**req_payload)
            rec_resp = AgriSaarthiEngine.execute(req_model)
            rec_dict = rec_resp.to_dict()

            # Attach English, Telugu, and Hindi localized metadata for each crop
            for group_key in ("primary_recommendations", "alternative_recommendations"):
                for item in rec_dict.get(group_key, []):
                    cname = item.get("crop_name", "")
                    te_meta = TELUGU_CROPS.get(cname, {})
                    hi_meta = HINDI_CROPS.get(cname, {})
                    item["name_en"] = cname
                    item["name_te"] = te_meta.get("name_te", cname)
                    item["name_hi"] = hi_meta.get("name_hi", item.get("hindi_name") or cname)
                    item["category_en"] = item.get("category", "")
                    item["category_te"] = te_meta.get("category_te", item.get("category", ""))
                    item["category_hi"] = hi_meta.get("category_hi", item.get("category", ""))
                    item["sowing_notes_en"] = item.get("sowing_notes", "") or "Follow recommended local sowing window and balanced NPK fertilizer schedule."
                    item["sowing_notes_te"] = te_meta.get("sowing_notes", "")
                    item["sowing_notes_hi"] = hi_meta.get("sowing_notes_hi", "")
                    item["advantage_en"] = (item.get("key_strengths") or ["High regional suitability and market demand."])[0]
                    item["advantage_te"] = te_meta.get("advantage_te", "")
                    item["advantage_hi"] = hi_meta.get("advantage_hi", "")
                    item["risk_en"] = (item.get("risk_factors") or ["Standard pest and weather monitoring recommended."])[0]
                    item["risk_te"] = te_meta.get("risk_te", "")
                    item["risk_hi"] = hi_meta.get("risk_hi", "")

            # Save to farmer history if authenticated
            if farmer:
                top_names = ", ".join(c.crop_name for c in rec_resp.primary_recommendations) or "No primary match"
                get_storage().add_advisory_history(
                    farmer_id=farmer["id"],
                    advisory_type="crop_advisory",
                    query_summary=(
                        f"{req_model.state} ({req_model.district or 'All'}) • "
                        f"{req_model.land_size_acres} ac • {req_model.soil_type.value} • "
                        f"{req_model.season.value} • ₹{req_model.budget_inr:,.0f}"
                    ),
                    result_summary=f"Top Recommended: {top_names}",
                    payload=rec_dict,
                )

            self._send_json(200, {"recommendation": rec_dict})
        except Exception as e:
            self._send_json(400, {"error": str(e)})

    def _handle_structured_crop_health(self) -> None:
        try:
            data = self._read_json_body()
            crop = str(data.get("crop", "")).strip()
            symptom = str(data.get("symptom", "")).strip()
            field_notes = str(data.get("field_notes", "")).strip()
            lang = str(data.get("lang", "te")).strip()

            combined_query = f"{crop} {symptom}".strip()
            if not combined_query:
                self._send_json(400, {"error": "Please select a crop or describe the symptom."})
                return

            disorder = find_matching_crop_disorder(combined_query)
            if not disorder:
                # Fall back to the conversational processor which handles general crop symptoms safely
                reply_md = process_chat_message(
                    text=f"{combined_query} {field_notes}".strip(),
                    sender="crop_health_portal",
                )
                self._send_json(
                    200,
                    {
                        "matched": False,
                        "fallback_markdown": reply_md,
                    },
                )
                return

            stage = "diagnosis" if field_notes else "questions"
            result_payload = {
                "matched": True,
                "stage": stage,
                "symptom_key": disorder.symptom_key,
                "crop_name": disorder.crop_name,
                "symptom_name_en": disorder.symptom_name_en,
                "symptom_name_te": disorder.symptom_name_te,
                "follow_up_questions_en": list(disorder.follow_up_questions_en),
                "follow_up_questions_te": list(disorder.follow_up_questions_te),
                "possible_causes": [c.to_dict() for c in disorder.possible_causes],
                "safe_actions_en": list(disorder.safe_actions_en),
                "safe_actions_te": list(disorder.safe_actions_te),
                "required_inspection_en": disorder.required_inspection_en,
                "required_inspection_te": disorder.required_inspection_te,
                "source_name": disorder.source_name,
                "source_reference": disorder.source_reference,
                "field_notes": field_notes,
            }

            token = self._extract_bearer_token()
            farmer = get_storage().get_farmer_by_token(token) if token else None
            if farmer and stage == "diagnosis":
                causes_summary = ", ".join(c.name_en for c in disorder.possible_causes[:2])
                get_storage().add_advisory_history(
                    farmer_id=farmer["id"],
                    advisory_type="crop_health",
                    query_summary=f"{disorder.crop_name}: {disorder.symptom_name_en}",
                    result_summary=f"Possible causes: {causes_summary}",
                    payload=result_payload,
                )

            self._send_json(200, result_payload)
        except Exception as e:
            logger.exception(f"Crop health error: {e}")
            self._send_json(400, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, format, *args):
        logger.debug("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


class ExclusiveThreadingHTTPServer(ThreadingHTTPServer):
    """Prevents multiple processes on Windows from silently binding to the same port."""
    if sys.platform == "win32":
        allow_reuse_address = False


def run_server(port=PORT):
    server_address = ("127.0.0.1", port)
    httpd = ExclusiveThreadingHTTPServer(server_address, AgriFarmerUIHandler)
    logger.info(f"🌾 AgriSaarthi Farmer Web Portal & Voice Interface running at: http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping UI server...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
