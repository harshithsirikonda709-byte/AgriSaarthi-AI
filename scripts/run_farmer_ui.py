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
import json
import logging
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any

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
)
from agrisaarthi.storage import (
    FarmerStorage,
    AuthValidationError,
    InvalidCredentialsError,
)
from agrisaarthi.weather_service import fetch_weather_and_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agrisaarthi.ui_server")

PORT = int(os.getenv("AGRI_UI_PORT", "8080"))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")

_STORAGE_INSTANCE: Optional[FarmerStorage] = None


def get_storage() -> FarmerStorage:
    """Return a singleton or test-configured FarmerStorage instance."""
    global _STORAGE_INSTANCE
    db_path = os.getenv("AGRI_DB_PATH")
    if _STORAGE_INSTANCE is None or (db_path and _STORAGE_INSTANCE.db_path != db_path):
        _STORAGE_INSTANCE = FarmerStorage(db_path=db_path)
    return _STORAGE_INSTANCE


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
        content_length = int(headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

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
            history = get_storage().get_advisory_history(farmer["id"], limit=10)
            weather = fetch_weather_and_alerts(
                state=farmer.get("state", ""),
                district=farmer.get("district", ""),
            )
            self._send_json(
                200,
                {
                    "farmer": farmer,
                    "history": history,
                    "weather": weather,
                },
            )

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/chat":
            headers = getattr(self, "headers", None) or {}
            content_length = int(headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                text = data.get("text", "")
                sender = data.get("sender", "farmer_voice_demo")

                logger.info(f"Received query from UI: '{text[:60]}...' (sender={sender})")
                reply = process_chat_message(text=text, sender=sender)
                model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")

                # If authenticated farmer is using voice/chat, store in their advisory history
                token = self._extract_bearer_token()
                if token and text.strip():
                    farmer = get_storage().get_farmer_by_token(token)
                    if farmer:
                        get_storage().add_advisory_history(
                            farmer_id=farmer["id"],
                            advisory_type="voice_chat",
                            query_summary=text.strip(),
                            result_summary=reply[:240],
                            payload={"sender": sender, "model": model_name},
                        )

                self._send_json(200, {"reply": reply, "model": model_name})
            except Exception as e:
                logger.exception(f"Error handling UI chat request: {e}")
                err_msg = str(e)
                friendly_reply = (
                    f"⚠️ **గమనిక (System Notice)**: క్షమించండి, విశ్లేషణ సమయంలో లోపం ఏర్పడింది: {err_msg}."
                    f"\n\nదయచేసి మీ ప్రశ్నను మళ్ళీ పంపండి లేదా Ollama రన్ అవుతుందో లేదో సరిచూసుకోండి."
                    f"\n\n*(Error processing query: {err_msg}. Please retry or check that Ollama is running.)*"
                )
                self._send_json(200, {"reply": friendly_reply, "error": err_msg})

        elif route == "/api/auth/register":
            try:
                data = self._read_json_body()
                farmer, token = get_storage().register_farmer(
                    full_name=data.get("full_name", ""),
                    identifier=data.get("identifier", "") or data.get("phone_number", ""),
                    password=data.get("password", ""),
                    preferred_language=data.get("preferred_language", "te"),
                    email=data.get("email"),
                    phone_number=data.get("phone_number"),
                    district=data.get("district"),
                    mandal=data.get("mandal"),
                    village=data.get("village"),
                    land_size_acres=data.get("land_size_acres"),
                    soil_type=data.get("soil_type"),
                    water_availability=data.get("water_availability"),
                    state=data.get("state"),
                    sowing_date=data.get("sowing_date"),
                    crop_growth_stage=data.get("crop_growth_stage"),
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
                    identifier=data.get("identifier", "") or data.get("phone_number", "") or data.get("email", ""),
                    password=data.get("password", ""),
                )
                self._send_json(200, {"farmer": farmer, "token": token})
            except InvalidCredentialsError as e:
                self._send_json(401, {"error": str(e)})
            except Exception as e:
                logger.exception(f"Login error: {e}")
                self._send_json(500, {"error": "Server error during login."})

        elif route == "/api/auth/logout":
            token = self._extract_bearer_token()
            get_storage().revoke_session(token)
            self._send_json(200, {"logged_out": True})

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

            # Attach Telugu localized metadata for each crop
            for group_key in ("primary_recommendations", "alternative_recommendations"):
                for item in rec_dict.get(group_key, []):
                    te_meta = TELUGU_CROPS.get(item["crop_name"], {})
                    item["name_te"] = te_meta.get("name_te", item["crop_name"])
                    item["category_te"] = te_meta.get("category_te", item["category"])
                    item["sowing_notes_te"] = te_meta.get("sowing_notes", "")
                    item["advantage_te"] = te_meta.get("advantage_te", "")
                    item["risk_te"] = te_meta.get("risk_te", "")

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
