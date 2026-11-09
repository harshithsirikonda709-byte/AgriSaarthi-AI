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
import json
import hmac
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple

from agrisaarthi.models import Season, SoilType, WaterAvailability, RiskTolerance

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "agrisaarthi_farmers.db")
PBKDF2_ITERATIONS = 200_000
SESSION_TTL_DAYS = 7

VALID_SOILS = {s.value for s in SoilType}
VALID_WATERS = {w.value for w in WaterAvailability}
VALID_SEASONS = {s.value for s in Season}
VALID_RISKS = {r.value for r in RiskTolerance}


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
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    preferred_language TEXT NOT NULL DEFAULT 'te',
                    state TEXT NOT NULL DEFAULT '',
                    district TEXT NOT NULL DEFAULT '',
                    village TEXT NOT NULL DEFAULT '',
                    land_size_acres REAL,
                    soil_type TEXT NOT NULL DEFAULT '',
                    water_availability TEXT NOT NULL DEFAULT '',
                    season TEXT NOT NULL DEFAULT '',
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
        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "identifier": row["identifier"],
            "preferred_language": row["preferred_language"],
            "state": row["state"],
            "district": row["district"],
            "village": row["village"],
            "land_size_acres": row["land_size_acres"],
            "soil_type": row["soil_type"],
            "water_availability": row["water_availability"],
            "season": row["season"],
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
        identifier: str,
        password: str,
        preferred_language: str = "te",
    ) -> Tuple[Dict[str, Any], str]:
        """Register a new farmer account with server-side validation and return (farmer_dict, session_token)."""
        clean_name = (full_name or "").strip()
        if len(clean_name) < 2:
            raise AuthValidationError("Full name must be at least 2 characters long.")

        norm_id = self._normalize_identifier(identifier)
        if len(norm_id) < 3:
            raise AuthValidationError("Mobile number or username must be at least 3 characters long.")
        if norm_id.isdigit() and len(norm_id) != 10:
            raise AuthValidationError("Please enter a valid 10-digit mobile number or an alphanumeric username.")

        if not password or len(password) < 6:
            raise AuthValidationError("Password must be at least 6 characters long.")

        lang = preferred_language if preferred_language in ("te", "en") else "te"
        pw_hash, pw_salt = hash_password(password)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM farmers WHERE identifier = ?", (norm_id,)
            ).fetchone()
            if existing:
                raise AuthValidationError(
                    "An account with this mobile number or username is already registered."
                )

            cursor = conn.execute(
                """
                INSERT INTO farmers (
                    full_name, identifier, password_hash, password_salt,
                    preferred_language, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (clean_name, norm_id, pw_hash, pw_salt, lang, now_iso, now_iso),
            )
            farmer_id = cursor.lastrowid
            token = self._create_session_in_tx(conn, farmer_id)
            row = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer_id,)).fetchone()
            return self._row_to_farmer_dict(row), token

    def authenticate_farmer(self, identifier: str, password: str) -> Tuple[Dict[str, Any], str]:
        """Authenticate a farmer by mobile number/username and password."""
        norm_id = self._normalize_identifier(identifier)
        if not norm_id or not password:
            raise InvalidCredentialsError("Please enter both your mobile number/username and password.")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM farmers WHERE identifier = ?", (norm_id,)
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

            if "full_name" in updates and updates["full_name"] is not None:
                name = str(updates["full_name"]).strip()
                if len(name) < 2:
                    raise AuthValidationError("Full name must be at least 2 characters.")
                current["full_name"] = name

            if "preferred_language" in updates and updates["preferred_language"] in ("te", "en"):
                current["preferred_language"] = updates["preferred_language"]

            if "state" in updates and updates["state"] is not None:
                st = str(updates["state"]).strip()
                current["state"] = st.title() if st else ""

            if "district" in updates and updates["district"] is not None:
                dist = str(updates["district"]).strip()
                current["district"] = dist.title() if dist else ""

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
            elif current.get("state") and current.get("land_size_acres") and current.get("soil_type"):
                current["profile_completed"] = 1

            now_iso = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE farmers SET
                    full_name = ?,
                    preferred_language = ?,
                    state = ?,
                    district = ?,
                    village = ?,
                    land_size_acres = ?,
                    soil_type = ?,
                    water_availability = ?,
                    season = ?,
                    budget_inr = ?,
                    risk_tolerance = ?,
                    primary_crops_grown = ?,
                    profile_completed = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    current["full_name"],
                    current["preferred_language"],
                    current["state"],
                    current["district"],
                    current["village"],
                    current["land_size_acres"],
                    current["soil_type"],
                    current["water_availability"],
                    current["season"],
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

