"""
Secure Farmer Authentication, Profile Management, and Advisory History Storage
for AgriSaarthi AI.

Uses Python standard library only (sqlite3, hashlib, hmac, secrets) — zero external dependencies:
  - Passwords hashed with PBKDF2-HMAC-SHA256 (200,000 iterations) + 16-byte cryptographic salt.
  - Constant-time password verification via hmac.compare_digest.
  - Cryptographic bearer session tokens (secrets.token_urlsafe(32)) with server-side expiration.
  - Persistent farmer farm profiles and advisory history in SQLite.
"""

import os
import re
import json
import hmac
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

from agrisaarthi.models import Season, SoilType, WaterAvailability, RiskTolerance, CropGrowthStage

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "agrisaarthi_farmers.db")
PBKDF2_ITERATIONS = 200_000
SESSION_TTL_DAYS = 7

VALID_SOILS = {s.value for s in SoilType}
VALID_WATERS = {w.value for w in WaterAvailability}
VALID_SEASONS = {s.value for s in Season}
VALID_RISKS = {r.value for r in RiskTolerance}
VALID_GROWTH_STAGES = {g.value for g in CropGrowthStage}


class AuthValidationError(ValueError):
    """Raised when registration or profile input fails server-side validation."""
    pass


class InvalidCredentialsError(PermissionError):
    """Raised when login credentials or session tokens are invalid."""
    pass


def hash_password(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 and a 16-byte random salt."""
    if not salt_hex:
        salt_hex = secrets.token_hex(16)
    salt_bytes = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PBKDF2_ITERATIONS,
    )
    return derived.hex(), salt_hex


def verify_password(password: str, expected_hash_hex: str, salt_hex: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash in constant time."""
    if not password or not expected_hash_hex or not salt_hex:
        return False
    computed_hex, _ = hash_password(password, salt_hex=salt_hex)
    return hmac.compare_digest(computed_hex, expected_hash_hex)


class FarmerStorage:
    """SQLite-backed store for farmer accounts, sessions, farm profiles, and advisory history."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("AGRI_DB_PATH", DEFAULT_DB_PATH)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS farmers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    identifier TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    phone_number TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    preferred_language TEXT NOT NULL DEFAULT 'te',
                    state TEXT NOT NULL DEFAULT '',
                    district TEXT NOT NULL DEFAULT '',
                    mandal TEXT NOT NULL DEFAULT '',
                    village TEXT NOT NULL DEFAULT '',
                    land_size_acres REAL,
                    soil_type TEXT NOT NULL DEFAULT '',
                    water_availability TEXT NOT NULL DEFAULT '',
                    season TEXT NOT NULL DEFAULT '',
                    sowing_date TEXT NOT NULL DEFAULT '',
                    crop_growth_stage TEXT NOT NULL DEFAULT '',
                    budget_inr REAL,
                    risk_tolerance TEXT NOT NULL DEFAULT 'moderate',
                    primary_crops_grown TEXT NOT NULL DEFAULT '',
                    profile_completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    farmer_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS advisory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    farmer_id INTEGER NOT NULL,
                    advisory_type TEXT NOT NULL,
                    query_summary TEXT NOT NULL,
                    result_summary TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE CASCADE
                );
                """
            )

            # Safe automated schema migration: Add missing columns if upgrading an existing DB
            cursor = conn.execute("PRAGMA table_info(farmers);")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            if "email" not in existing_cols:
                conn.execute("ALTER TABLE farmers ADD COLUMN email TEXT NOT NULL DEFAULT '';")
            if "phone_number" not in existing_cols:
                conn.execute("ALTER TABLE farmers ADD COLUMN phone_number TEXT NOT NULL DEFAULT '';")
            if "mandal" not in existing_cols:
                conn.execute("ALTER TABLE farmers ADD COLUMN mandal TEXT NOT NULL DEFAULT '';")
            if "sowing_date" not in existing_cols:
                conn.execute("ALTER TABLE farmers ADD COLUMN sowing_date TEXT NOT NULL DEFAULT '';")
            if "crop_growth_stage" not in existing_cols:
                conn.execute("ALTER TABLE farmers ADD COLUMN crop_growth_stage TEXT NOT NULL DEFAULT '';")

            # Normalized Relational Views (Task 4 Database Design)
            # Exposes users, farmer_profiles, and farm_details without data duplication or migration overwrites
            conn.executescript(
                """
                CREATE VIEW IF NOT EXISTS users AS
                    SELECT 
                        id,
                        identifier,
                        password_hash,
                        password_salt,
                        created_at,
                        updated_at
                    FROM farmers;

                CREATE VIEW IF NOT EXISTS farmer_profiles AS
                    SELECT 
                        id,
                        id AS user_id,
                        full_name,
                        email,
                        phone_number,
                        preferred_language,
                        state,
                        district,
                        mandal,
                        village,
                        profile_completed,
                        created_at,
                        updated_at
                    FROM farmers;

                CREATE VIEW IF NOT EXISTS farm_details AS
                    SELECT 
                        id,
                        id AS user_id,
                        land_size_acres,
                        soil_type,
                        water_availability,
                        season,
                        sowing_date,
                        crop_growth_stage,
                        budget_inr,
                        risk_tolerance,
                        primary_crops_grown,
                        created_at,
                        updated_at
                    FROM farmers;
                """
            )

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        """Normalize mobile number or username consistently."""
        cleaned = (identifier or "").strip().lower()
        # Strip spaces and dashes if it looks like a phone number
        digits_only = cleaned.replace(" ", "").replace("-", "")
        if digits_only.startswith("+91") and len(digits_only) == 13 and digits_only[1:].isdigit():
            return digits_only[3:]
        if digits_only.isdigit():
            return digits_only
        return cleaned

    @staticmethod
    def _row_to_farmer_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database farmer row into a safe dictionary (never exposing password hashes)."""
        keys = set(row.keys())
        phone_val = row["phone_number"] if "phone_number" in keys and row["phone_number"] else ""
        if not phone_val and row["identifier"] and row["identifier"].isdigit():
            phone_val = row["identifier"]

        return {
            "id": row["id"],
            "farmer_id": row["id"],
            "full_name": row["full_name"],
            "identifier": row["identifier"],
            "email": row["email"] if "email" in keys else "",
            "phone_number": phone_val,
            "preferred_language": row["preferred_language"],
            "state": row["state"],
            "district": row["district"],
            "mandal": row["mandal"] if "mandal" in keys else "",
            "village": row["village"],
            "land_size_acres": row["land_size_acres"],
            "soil_type": row["soil_type"],
            "water_availability": row["water_availability"],
            "season": row["season"],
            "sowing_date": row["sowing_date"] if "sowing_date" in keys else "",
            "crop_growth_stage": row["crop_growth_stage"] if "crop_growth_stage" in keys else "",
            "budget_inr": row["budget_inr"],
            "risk_tolerance": row["risk_tolerance"],
            "primary_crops_grown": row["primary_crops_grown"],
            "profile_completed": bool(row["profile_completed"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def register_farmer(
        self,
        full_name: str,
        identifier: str = "",
        password: str = "",
        preferred_language: str = "te",
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        district: Optional[str] = None,
        mandal: Optional[str] = None,
        village: Optional[str] = None,
        land_size_acres: Optional[float] = None,
        soil_type: Optional[str] = None,
        water_availability: Optional[str] = None,
        state: Optional[str] = None,
        sowing_date: Optional[str] = None,
        crop_growth_stage: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """Register a new farmer account with server-side validation and return (farmer_dict, session_token)."""
        clean_name = (full_name or "").strip()
        if len(clean_name) < 2:
            raise AuthValidationError("Full name must be at least 2 characters long.")

        clean_phone = (phone_number or "").strip()
        if clean_phone:
            digits = re.sub(r"[^\d]", "", clean_phone)
            if digits.startswith("91") and len(digits) == 12:
                digits = digits[2:]
            if len(digits) != 10:
                raise AuthValidationError("Phone number must be a valid 10-digit mobile number.")
            clean_phone = digits

        clean_email = (email or "").strip().lower()
        if clean_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
            raise AuthValidationError("Invalid email address format.")

        raw_id = (identifier or "").strip()
        if not raw_id:
            raw_id = clean_phone or clean_email

        norm_id = self._normalize_identifier(raw_id)
        if len(norm_id) < 3:
            raise AuthValidationError("Mobile number or username must be at least 3 characters long.")
        if norm_id.isdigit() and len(norm_id) != 10:
            raise AuthValidationError("Please enter a valid 10-digit mobile number or an alphanumeric username.")

        if not clean_phone and norm_id.isdigit():
            clean_phone = norm_id

        if not password or len(password) < 6:
            raise AuthValidationError("Password must be at least 6 characters long.")

        clean_dist = (district or "").strip().title()
        clean_mandal = (mandal or "").strip().title()
        clean_village = (village or "").strip().title()
        clean_state = (state or "").strip().title()

        clean_sowing = str(sowing_date).strip() if sowing_date else ""
        if clean_sowing and not re.match(r"^\d{4}-\d{2}-\d{2}$", clean_sowing):
            raise AuthValidationError("Sowing date must be in YYYY-MM-DD format (e.g. 2026-10-15).")

        clean_stage = str(crop_growth_stage).strip().lower() if crop_growth_stage else ""
        if clean_stage and clean_stage not in VALID_GROWTH_STAGES:
            raise AuthValidationError(f"Unsupported crop growth stage '{clean_stage}'.")

        parsed_land: Optional[float] = None
        if land_size_acres not in (None, ""):
            try:
                parsed_land = round(float(land_size_acres), 2)
            except (ValueError, TypeError):
                raise AuthValidationError("Land size must be a valid number.")
            if parsed_land <= 0 or parsed_land > 5000:
                raise AuthValidationError("Land size must be between 0.1 and 5000 acres.")

        clean_soil = (soil_type or "").strip().lower().replace(" ", "_")
        if clean_soil and clean_soil not in VALID_SOILS:
            raise AuthValidationError(f"Unsupported soil type '{clean_soil}'.")

        clean_water = (water_availability or "").strip().lower()
        if clean_water and clean_water not in VALID_WATERS:
            raise AuthValidationError(f"Unsupported water availability '{clean_water}'.")

        profile_completed = 1 if (clean_dist and clean_village and parsed_land and clean_soil) else 0

        lang = preferred_language if preferred_language in ("te", "en") else "te"
        pw_hash, pw_salt = hash_password(password)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id FROM farmers
                WHERE identifier = ?
                   OR (phone_number != '' AND phone_number = ?)
                   OR (email != '' AND email = ?)
                """,
                (norm_id, clean_phone if clean_phone else norm_id, clean_email if clean_email else "__none__"),
            ).fetchone()
            if existing:
                raise AuthValidationError(
                    "An account with this mobile number, username, or email is already registered."
                )

            cursor = conn.execute(
                """
                INSERT INTO farmers (
                    full_name, identifier, email, phone_number, password_hash, password_salt,
                    preferred_language, state, district, mandal, village, land_size_acres,
                    soil_type, water_availability, sowing_date, crop_growth_stage,
                    profile_completed, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_name,
                    norm_id,
                    clean_email,
                    clean_phone,
                    pw_hash,
                    pw_salt,
                    lang,
                    clean_state,
                    clean_dist,
                    clean_mandal,
                    clean_village,
                    parsed_land,
                    clean_soil,
                    clean_water,
                    clean_sowing,
                    clean_stage,
                    profile_completed,
                    now_iso,
                    now_iso,
                ),
            )
            farmer_id = cursor.lastrowid
            token = self._create_session_in_tx(conn, farmer_id)
            row = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
            return self._row_to_farmer_dict(row), token

    def authenticate_farmer(self, identifier: str, password: str) -> Tuple[Dict[str, Any], str]:
        """Authenticate a farmer by mobile number/username/email and password."""
        norm_id = self._normalize_identifier(identifier)
        clean_raw = (identifier or "").strip().lower()
        if not norm_id or not password:
            raise InvalidCredentialsError("Please enter both your mobile number/username and password.")

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM farmers 
                WHERE identifier = ? 
                   OR phone_number = ?
                   OR (email != '' AND LOWER(email) = ?)
                LIMIT 1
                """,
                (norm_id, norm_id, clean_raw),
            ).fetchone()
            if not row or not verify_password(password, row["password_hash"], row["password_salt"]):
                raise InvalidCredentialsError("Invalid mobile number/username or password.")

            token = self._create_session_in_tx(conn, row["id"])
            return self._row_to_farmer_dict(row), token

    def _create_session_in_tx(self, conn: sqlite3.Connection, farmer_id: int) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=SESSION_TTL_DAYS)
        conn.execute(
            "INSERT INTO sessions (token, farmer_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, farmer_id, now.isoformat(), expires.isoformat()),
        )
        return token

    def get_farmer_by_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validate a bearer token and return the farmer profile if valid and unexpired."""
        if not token or not token.strip():
            return None
        clean_token = token.strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            sess = conn.execute(
                "SELECT farmer_id, expires_at FROM sessions WHERE token = ?",
                (clean_token,),
            ).fetchone()
            if not sess:
                return None
            if sess["expires_at"] < now_iso:
                conn.execute("DELETE FROM sessions WHERE token = ?", (clean_token,))
                return None

            row = conn.execute(
                "SELECT * FROM farmers WHERE id = ?", (sess["farmer_id"],)
            ).fetchone()
            if not row:
                return None
            return self._row_to_farmer_dict(row)

    def revoke_session(self, token: Optional[str]) -> bool:
        """Delete a session token on logout."""
        if not token or not token.strip():
            return False
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE token = ?", (token.strip(),))
            return cur.rowcount > 0

    def update_farmer_profile(
        self, farmer_id: int, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and update a farmer's personal and farm profile fields."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
            if not row:
                raise InvalidCredentialsError("Farmer account not found.")

            current = dict(row)
            if "email" not in current:
                current["email"] = ""
            if "phone_number" not in current:
                current["phone_number"] = ""
            if "mandal" not in current:
                current["mandal"] = ""

            if "full_name" in updates and updates["full_name"] is not None:
                name = str(updates["full_name"]).strip()
                if len(name) < 2:
                    raise AuthValidationError("Full name must be at least 2 characters.")
                current["full_name"] = name

            if "email" in updates and updates["email"] is not None:
                em = str(updates["email"]).strip().lower()
                if em and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", em):
                    raise AuthValidationError("Please enter a valid email address.")
                current["email"] = em

            if "phone_number" in updates and updates["phone_number"] is not None:
                ph = str(updates["phone_number"]).strip()
                digits = re.sub(r"[^\d]", "", ph)
                if digits.startswith("91") and len(digits) == 12:
                    digits = digits[2:]
                if digits and len(digits) != 10:
                    raise AuthValidationError("Phone number must be a valid 10-digit mobile number.")
                current["phone_number"] = digits

            if "preferred_language" in updates and updates["preferred_language"] in ("te", "en"):
                current["preferred_language"] = updates["preferred_language"]

            if "state" in updates and updates["state"] is not None:
                st = str(updates["state"]).strip()
                current["state"] = st.title() if st else ""

            if "district" in updates and updates["district"] is not None:
                dist = str(updates["district"]).strip()
                current["district"] = dist.title() if dist else ""

            if "mandal" in updates and updates["mandal"] is not None:
                man = str(updates["mandal"]).strip()
                current["mandal"] = man.title() if man else ""

            if "village" in updates and updates["village"] is not None:
                vil = str(updates["village"]).strip()
                current["village"] = vil.title() if vil else ""

            if "land_size_acres" in updates:
                val = updates["land_size_acres"]
                if val in (None, ""):
                    current["land_size_acres"] = None
                else:
                    try:
                        acres = float(val)
                    except (ValueError, TypeError):
                        raise AuthValidationError("Land size must be a valid number.")
                    if acres <= 0 or acres > 5000:
                        raise AuthValidationError("Land size must be between 0.1 and 5000 acres.")
                    current["land_size_acres"] = round(acres, 2)

            if "soil_type" in updates and updates["soil_type"] is not None:
                soil = str(updates["soil_type"]).strip().lower().replace(" ", "_")
                if soil and soil not in VALID_SOILS:
                    raise AuthValidationError(f"Unsupported soil type '{soil}'.")
                current["soil_type"] = soil

            if "water_availability" in updates and updates["water_availability"] is not None:
                water = str(updates["water_availability"]).strip().lower()
                if water and water not in VALID_WATERS:
                    raise AuthValidationError(f"Unsupported water availability '{water}'.")
                current["water_availability"] = water

            if "season" in updates and updates["season"] is not None:
                season = str(updates["season"]).strip().lower()
                if season and season not in VALID_SEASONS:
                    raise AuthValidationError(f"Unsupported season '{season}'.")
                current["season"] = season

            if "sowing_date" not in current:
                current["sowing_date"] = ""
            if "crop_growth_stage" not in current:
                current["crop_growth_stage"] = ""

            if "sowing_date" in updates:
                sd = updates["sowing_date"]
                if sd in (None, ""):
                    current["sowing_date"] = ""
                else:
                    sd_str = str(sd).strip()
                    if not re.match(r"^\d{4}-\d{2}-\d{2}$", sd_str):
                        raise AuthValidationError("Sowing date must be in YYYY-MM-DD format (e.g. 2026-10-15).")
                    current["sowing_date"] = sd_str

            if "crop_growth_stage" in updates:
                stg = updates["crop_growth_stage"]
                if stg in (None, ""):
                    current["crop_growth_stage"] = ""
                else:
                    stg_str = str(stg).strip().lower()
                    if stg_str and stg_str not in VALID_GROWTH_STAGES:
                        raise AuthValidationError(f"Unsupported crop growth stage '{stg_str}'.")
                    current["crop_growth_stage"] = stg_str

            if "budget_inr" in updates:
                val = updates["budget_inr"]
                if val in (None, ""):
                    current["budget_inr"] = None
                else:
                    try:
                        budget = float(val)
                    except (ValueError, TypeError):
                        raise AuthValidationError("Budget must be a valid number in INR.")
                    if budget < 0:
                        raise AuthValidationError("Budget cannot be negative.")
                    current["budget_inr"] = round(budget, 2)

            if "risk_tolerance" in updates and updates["risk_tolerance"]:
                risk = str(updates["risk_tolerance"]).strip().lower()
                if risk not in VALID_RISKS:
                    raise AuthValidationError(f"Unsupported risk tolerance '{risk}'.")
                current["risk_tolerance"] = risk

            if "primary_crops_grown" in updates and updates["primary_crops_grown"] is not None:
                current["primary_crops_grown"] = str(updates["primary_crops_grown"]).strip()

            # Mark profile_completed if explicitly passed or if core farm fields exist
            if "profile_completed" in updates:
                current["profile_completed"] = 1 if updates["profile_completed"] else 0
            elif current.get("district") and current.get("village") and current.get("land_size_acres") and current.get("soil_type"):
                current["profile_completed"] = 1

            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE farmers SET
                    full_name = ?,
                    email = ?,
                    phone_number = ?,
                    preferred_language = ?,
                    state = ?,
                    district = ?,
                    mandal = ?,
                    village = ?,
                    land_size_acres = ?,
                    soil_type = ?,
                    water_availability = ?,
                    season = ?,
                    sowing_date = ?,
                    crop_growth_stage = ?,
                    budget_inr = ?,
                    risk_tolerance = ?,
                    primary_crops_grown = ?,
                    profile_completed = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    current["full_name"],
                    current.get("email", ""),
                    current.get("phone_number", ""),
                    current["preferred_language"],
                    current["state"],
                    current["district"],
                    current.get("mandal", ""),
                    current["village"],
                    current["land_size_acres"],
                    current["soil_type"],
                    current["water_availability"],
                    current["season"],
                    current.get("sowing_date", ""),
                    current.get("crop_growth_stage", ""),
                    current["budget_inr"],
                    current["risk_tolerance"],
                    current["primary_crops_grown"],
                    current["profile_completed"],
                    now_iso,
                    farmer_id,
                ),
            )
            updated = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
            return self._row_to_farmer_dict(updated)

    def add_advisory_history(
        self,
        farmer_id: int,
        advisory_type: str,
        query_summary: str,
        result_summary: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Record a crop recommendation, crop health diagnosis, or voice consultation in history."""
        now_iso = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO advisory_history (
                    farmer_id, advisory_type, query_summary, result_summary, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (farmer_id, advisory_type, query_summary[:300], result_summary[:500], payload_str, now_iso),
            )
            row = conn.execute(
                "SELECT * FROM advisory_history WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            return {
                "id": row["id"],
                "farmer_id": row["farmer_id"],
                "advisory_type": row["advisory_type"],
                "query_summary": row["query_summary"],
                "result_summary": row["result_summary"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }

    def get_advisory_history(self, farmer_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent advisory history for a farmer."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM advisory_history
                WHERE farmer_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (farmer_id, limit),
            ).fetchall()
            items = []
            for r in rows:
                try:
                    parsed = json.loads(r["payload_json"])
                except Exception:
                    parsed = {}
                items.append(
                    {
                        "id": r["id"],
                        "advisory_type": r["advisory_type"],
                        "query_summary": r["query_summary"],
                        "result_summary": r["result_summary"],
                        "payload": parsed,
                        "created_at": r["created_at"],
                    }
                )
            return items

