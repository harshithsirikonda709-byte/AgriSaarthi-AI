"""
Supabase Cloud Storage Adapter for AgriSaarthi AI.
Connects to Supabase PostgreSQL database via secure HTTPS REST API (PostgREST).
Provides identical interface as FarmerStorage for seamless cloud persistence:
  - PBKDF2-HMAC-SHA256 password hashing.
  - Constant-time verification.
  - Multi-tenant shared cloud storage for all users across the internet.
"""

import os
import re
import math
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
import requests

from agrisaarthi.models import Season, SoilType, WaterAvailability, RiskTolerance, CropGrowthStage
from agrisaarthi.storage import (
    AuthValidationError,
    InvalidCredentialsError,
    hash_password,
    verify_password,
    haversine_distance_km,
    VALID_SOILS,
    VALID_WATERS,
    VALID_SEASONS,
    VALID_RISKS,
    VALID_GROWTH_STAGES,
    SESSION_TTL_DAYS,
)


class SupabaseStorage:
    """Supabase-backed cloud store for farmer accounts, sessions, profiles, and crop observations."""

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        self.url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        self.key = (supabase_key or os.getenv("SUPABASE_KEY", "")).strip()

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured in environment variables.")

        self.session = requests.Session()
        self.session.headers.update({
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        })

    def _endpoint(self, table: str) -> str:
        return f"{self.url}/rest/v1/{table}"

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        cleaned = (identifier or "").strip().lower()
        digits_only = cleaned.replace(" ", "").replace("-", "")
        if digits_only.startswith("+91") and len(digits_only) == 13 and digits_only[1:].isdigit():
            return digits_only[3:]
        if digits_only.isdigit():
            return digits_only
        return cleaned

    @staticmethod
    def _row_to_farmer_dict(row: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a Supabase JSON record into safe farmer profile dictionary."""
        phone_val = row.get("phone_number", "")
        if not phone_val and row.get("identifier") and str(row["identifier"]).isdigit():
            phone_val = str(row["identifier"])

        return {
            "id": row["id"],
            "farmer_id": row["id"],
            "full_name": row.get("full_name", ""),
            "identifier": row.get("identifier", ""),
            "email": row.get("email", ""),
            "phone_number": phone_val,
            "preferred_language": row.get("preferred_language", "te"),
            "state": row.get("state", ""),
            "district": row.get("district", ""),
            "mandal": row.get("mandal", ""),
            "village": row.get("village", ""),
            "land_size_acres": row.get("land_size_acres"),
            "soil_type": row.get("soil_type", ""),
            "water_availability": row.get("water_availability", ""),
            "season": row.get("season", ""),
            "sowing_date": row.get("sowing_date", ""),
            "crop_growth_stage": row.get("crop_growth_stage", ""),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "budget_inr": row.get("budget_inr"),
            "risk_tolerance": row.get("risk_tolerance", "moderate"),
            "primary_crops_grown": row.get("primary_crops_grown", ""),
            "profile_completed": bool(row.get("profile_completed", False)),
            "created_at": str(row.get("created_at", "")),
            "updated_at": str(row.get("updated_at", "")),
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
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """Register a new farmer account in Supabase."""
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

        parsed_lat: Optional[float] = None
        if latitude not in (None, ""):
            try:
                parsed_lat = float(latitude)
            except (ValueError, TypeError):
                raise AuthValidationError("Latitude must be a valid decimal number.")
            if not (-90.0 <= parsed_lat <= 90.0):
                raise AuthValidationError("Latitude must be between -90.0 and 90.0 degrees.")
            parsed_lat = round(parsed_lat, 6)

        parsed_lon: Optional[float] = None
        if longitude not in (None, ""):
            try:
                parsed_lon = float(longitude)
            except (ValueError, TypeError):
                raise AuthValidationError("Longitude must be a valid decimal number.")
            if not (-180.0 <= parsed_lon <= 180.0):
                raise AuthValidationError("Longitude must be between -180.0 and 180.0 degrees.")
            parsed_lon = round(parsed_lon, 6)

        profile_completed = bool(clean_dist and clean_village and parsed_land and clean_soil)
        lang = preferred_language if preferred_language in ("te", "en") else "te"
        pw_hash, pw_salt = hash_password(password)

        # Check existing account
        params = {"or": f"(identifier.eq.{norm_id},phone_number.eq.{clean_phone or norm_id})"}
        check_res = self.session.get(self._endpoint("farmers"), params=params)
        if check_res.ok and check_res.json():
            raise AuthValidationError("An account with this mobile number or username is already registered.")

        insert_payload = {
            "full_name": clean_name,
            "identifier": norm_id,
            "email": clean_email,
            "phone_number": clean_phone,
            "password_hash": pw_hash,
            "password_salt": pw_salt,
            "preferred_language": lang,
            "state": clean_state,
            "district": clean_dist,
            "mandal": clean_mandal,
            "village": clean_village,
            "land_size_acres": parsed_land,
            "soil_type": clean_soil,
            "water_availability": clean_water,
            "sowing_date": clean_sowing,
            "crop_growth_stage": clean_stage,
            "latitude": parsed_lat,
            "longitude": parsed_lon,
            "profile_completed": profile_completed,
        }

        res = self.session.post(self._endpoint("farmers"), json=insert_payload)
        if not res.ok:
            raise AuthValidationError(f"Supabase error: {res.text}")

        created_farmer = res.json()[0]
        token = self._create_session(created_farmer["id"])
        return self._row_to_farmer_dict(created_farmer), token

    def authenticate_farmer(self, identifier: str, password: str) -> Tuple[Dict[str, Any], str]:
        """Authenticate a farmer against Supabase."""
        norm_id = self._normalize_identifier(identifier)
        clean_raw = (identifier or "").strip().lower()
        if not norm_id or not password:
            raise InvalidCredentialsError("Please enter both your mobile number/username and password.")

        params = {"or": f"(identifier.eq.{norm_id},phone_number.eq.{norm_id},email.eq.{clean_raw})"}
        res = self.session.get(self._endpoint("farmers"), params=params)
        if not res.ok or not res.json():
            raise InvalidCredentialsError("Invalid mobile number/username or password.")

        farmer_row = res.json()[0]
        if not verify_password(password, farmer_row["password_hash"], farmer_row["password_salt"]):
            raise InvalidCredentialsError("Invalid mobile number/username or password.")

        token = self._create_session(farmer_row["id"])
        return self._row_to_farmer_dict(farmer_row), token

    def _create_session(self, farmer_id: int) -> str:
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=SESSION_TTL_DAYS)
        payload = {
            "token": token,
            "farmer_id": farmer_id,
            "created_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }
        res = self.session.post(self._endpoint("sessions"), json=payload)
        if not res.ok:
            raise RuntimeError(f"Failed to create Supabase session: {res.text}")
        return token

    def get_farmer_by_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validate bearer token in Supabase and return farmer profile."""
        if not token or not token.strip():
            return None
        clean_token = token.strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        res = self.session.get(
            self._endpoint("sessions"),
            params={"token": f"eq.{clean_token}", "expires_at": f"gt.{now_iso}"}
        )
        if not res.ok or not res.json():
            return None

        sess = res.json()[0]
        farmer_res = self.session.get(
            self._endpoint("farmers"),
            params={"id": f"eq.{sess['farmer_id']}"}
        )
        if not farmer_res.ok or not farmer_res.json():
            return None

        return self._row_to_farmer_dict(farmer_res.json()[0])

    def revoke_session(self, token: Optional[str]) -> bool:
        """Revoke a session in Supabase on logout."""
        if not token or not token.strip():
            return False
        res = self.session.delete(
            self._endpoint("sessions"),
            params={"token": f"eq.{token.strip()}"}
        )
        return res.ok

    def update_farmer_profile(self, farmer_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update farmer profile fields in Supabase."""
        current_res = self.session.get(self._endpoint("farmers"), params={"id": f"eq.{farmer_id}"})
        if not current_res.ok or not current_res.json():
            raise InvalidCredentialsError("Farmer account not found.")

        current = current_res.json()[0]
        patch_payload: Dict[str, Any] = {}

        if "full_name" in updates and updates["full_name"] is not None:
            name = str(updates["full_name"]).strip()
            if len(name) < 2:
                raise AuthValidationError("Full name must be at least 2 characters.")
            patch_payload["full_name"] = name

        if "latitude" in updates:
            lat_val = updates["latitude"]
            if lat_val in (None, ""):
                patch_payload["latitude"] = None
            else:
                try:
                    plat = float(lat_val)
                    if not (-90.0 <= plat <= 90.0):
                        raise AuthValidationError("Latitude must be between -90.0 and 90.0.")
                    patch_payload["latitude"] = round(plat, 6)
                except ValueError:
                    raise AuthValidationError("Latitude must be a valid number.")

        if "longitude" in updates:
            lon_val = updates["longitude"]
            if lon_val in (None, ""):
                patch_payload["longitude"] = None
            else:
                try:
                    plon = float(lon_val)
                    if not (-180.0 <= plon <= 180.0):
                        raise AuthValidationError("Longitude must be between -180.0 and 180.0.")
                    patch_payload["longitude"] = round(plon, 6)
                except ValueError:
                    raise AuthValidationError("Longitude must be a valid number.")

        for field in ("state", "district", "mandal", "village", "soil_type", "water_availability", "season", "sowing_date", "crop_growth_stage"):
            if field in updates and updates[field] is not None:
                patch_payload[field] = str(updates[field]).strip()

        if "land_size_acres" in updates and updates["land_size_acres"] not in (None, ""):
            patch_payload["land_size_acres"] = float(updates["land_size_acres"])

        if "budget_inr" in updates and updates["budget_inr"] not in (None, ""):
            patch_payload["budget_inr"] = float(updates["budget_inr"])

        patch_payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        res = self.session.patch(
            self._endpoint("farmers"),
            params={"id": f"eq.{farmer_id}"},
            json=patch_payload
        )
        if not res.ok:
            raise AuthValidationError(f"Supabase update error: {res.text}")

        updated_row = res.json()[0]
        return self._row_to_farmer_dict(updated_row)

    def record_crop_observation(
        self,
        crop_name: str,
        latitude: float,
        longitude: float,
        sowing_date: str,
        crop_growth_stage: str,
        consent_shared: bool = True,
        farmer_id: Optional[int] = None,
        farmer_name: str = "",
        field_notes: str = "",
        observed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record crop observation in Supabase."""
        clean_crop = (crop_name or "").strip().title()
        if len(clean_crop) < 2:
            raise AuthValidationError("Crop name must be at least 2 characters long.")

        plat, plon = float(latitude), float(longitude)
        if not (-90.0 <= plat <= 90.0) or not (-180.0 <= plon <= 180.0):
            raise AuthValidationError("Invalid GPS coordinates.")

        clean_sowing = (sowing_date or "").strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", clean_sowing):
            raise AuthValidationError("Sowing date must be in YYYY-MM-DD format.")

        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "farmer_id": farmer_id,
            "farmer_name": farmer_name or "Anonymous Farmer",
            "crop_name": clean_crop,
            "latitude": round(plat, 6),
            "longitude": round(plon, 6),
            "sowing_date": clean_sowing,
            "crop_growth_stage": crop_growth_stage.lower(),
            "consent_shared": bool(consent_shared),
            "field_notes": (field_notes or "").strip(),
            "observed_at": (observed_at or "").strip() or now_iso,
        }

        res = self.session.post(self._endpoint("crop_observations"), json=payload)
        if not res.ok:
            raise AuthValidationError(f"Supabase error: {res.text}")
        return res.json()[0]

    def get_nearby_crop_observations(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        radius_km: float = 2.5,
        max_age_days: int = 180,
        require_consent: bool = True,
        include_stale: bool = False,
    ) -> List[Dict[str, Any]]:
        """Query nearby observations from Supabase with Haversine distance."""
        if latitude is None or longitude is None:
            return []
        try:
            target_lat = float(latitude)
            target_lon = float(longitude)
        except (ValueError, TypeError):
            return []

        # Bounding box
        lat_delta = (radius_km / 110.0) + 0.01
        cos_lat = max(0.01, math.cos(math.radians(target_lat)))
        lon_delta = (radius_km / (110.0 * cos_lat)) + 0.01

        params = {
            "latitude": f"gte.{target_lat - lat_delta}",
            "latitude": f"lte.{target_lat + lat_delta}",
            "longitude": f"gte.{target_lon - lon_delta}",
            "longitude": f"lte.{target_lon + lon_delta}",
        }
        if require_consent:
            params["consent_shared"] = "eq.true"

        res = self.session.get(self._endpoint("crop_observations"), params=params)
        if not res.ok:
            return []

        now_utc = datetime.now(timezone.utc)
        results = []
        for r in res.json():
            obs_lat = r.get("latitude")
            obs_lon = r.get("longitude")
            if obs_lat is None or obs_lon is None:
                continue

            dist = haversine_distance_km(target_lat, target_lon, obs_lat, obs_lon)
            if dist > radius_km:
                continue

            # Staleness check
            is_stale = False
            time_str = r.get("observed_at") or r.get("sowing_date")
            if time_str:
                try:
                    dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    if (now_utc - dt).total_seconds() / 86400.0 > max_age_days:
                        is_stale = True
                except Exception:
                    pass

            if is_stale and not include_stale:
                continue

            results.append({
                "id": r["id"],
                "farmer_id": r.get("farmer_id"),
                "farmer_name": r.get("farmer_name", "Anonymous Farmer"),
                "crop_name": r["crop_name"],
                "crop_growth_stage": r["crop_growth_stage"],
                "sowing_date": r["sowing_date"],
                "latitude": obs_lat,
                "longitude": obs_lon,
                "distance_km": dist,
                "consent_shared": bool(r.get("consent_shared", True)),
                "field_notes": r.get("field_notes", ""),
                "observed_at": r.get("observed_at", ""),
                "is_stale": is_stale,
            })

        results.sort(key=lambda x: x["distance_km"])
        return results

    def get_farmer_observations(self, farmer_id: int) -> List[Dict[str, Any]]:
        """Retrieve observations logged by a specific farmer from Supabase."""
        res = self.session.get(
            self._endpoint("crop_observations"),
            params={"farmer_id": f"eq.{farmer_id}", "order": "id.desc"}
        )
        return res.json() if res.ok else []

    def add_advisory_history(
        self,
        farmer_id: int,
        advisory_type: str,
        query_summary: str,
        result_summary: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Record advisory in Supabase."""
        record = {
            "farmer_id": farmer_id,
            "advisory_type": advisory_type,
            "query_summary": query_summary[:300],
            "result_summary": result_summary[:500],
            "payload_json": payload,
        }
        res = self.session.post(self._endpoint("advisory_history"), json=record)
        return res.json()[0] if res.ok else {}

    def get_advisory_history(self, farmer_id: int, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieve recent advisory history from Supabase."""
        res = self.session.get(
            self._endpoint("advisory_history"),
            params={"farmer_id": f"eq.{farmer_id}", "order": "id.desc", "limit": str(limit)}
        )
        return res.json() if res.ok else []
