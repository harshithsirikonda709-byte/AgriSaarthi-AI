"""
Comprehensive Unit & Integration Tests for Day 2 Farmer Profile Backend:
1. Implement farmer profile creation and updating.
2. Store farmer details in the database.
3. Implement profile retrieval.
4. Store and retrieve sowing date and crop growth stage.
5. Ensure profile data persists after logout and login.
6. Test all profile APIs and database operations.
"""

import os
import json
import sqlite3
import tempfile
import shutil
import unittest
from io import BytesIO
from unittest.mock import MagicMock

from agrisaarthi.models import (
    FarmerProfile,
    FarmerRegistrationRequest,
    FarmerProfileUpdateRequest,
    CropGrowthStage,
    SoilType,
    WaterAvailability,
    Season,
)
from agrisaarthi.storage import (
    FarmerStorage,
    AuthValidationError,
    InvalidCredentialsError,
)
from scripts.run_farmer_ui import AgriFarmerUIHandler


class TestDay2FarmerProfileBackend(unittest.TestCase):
    """Rigorous tests covering all 6 Day 2 Farmer Profile Backend requirements."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_day2_farmers.db")
        os.environ["AGRI_DB_PATH"] = self.db_path
        os.environ["DISABLE_LIVE_WEATHER"] = "true"
        self.storage = FarmerStorage(db_path=self.db_path)
        import scripts.run_farmer_ui as ui_module
        ui_module._STORAGE_INSTANCE = self.storage

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _invoke(self, method: str, path: str, body: dict = None, headers: dict = None):
        """Invoke AgriFarmerUIHandler in memory and return (status_code, response_json)."""
        handler = AgriFarmerUIHandler.__new__(AgriFarmerUIHandler)
        handler.path = path
        req_headers = dict(headers or {})
        if body is not None:
            raw_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req_headers["Content-Length"] = str(len(raw_bytes))
            handler.rfile = BytesIO(raw_bytes)
        else:
            handler.rfile = BytesIO(b"")
        handler.headers = req_headers
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.send_error = MagicMock()
        handler.wfile = BytesIO()

        if method == "GET":
            handler.do_GET()
        elif method == "POST":
            handler.do_POST()
        elif method == "PUT":
            handler.do_PUT()

        status_code = handler.send_response.call_args[0][0] if handler.send_response.called else None
        response_bytes = handler.wfile.getvalue()
        response_json = json.loads(response_bytes.decode("utf-8")) if response_bytes else {}
        return status_code, response_json

    # -------------------------------------------------------------------------
    # 1 & 2. Profile Creation, Storage, and Updating
    # -------------------------------------------------------------------------
    def test_1_and_2_profile_creation_storage_and_updating(self):
        """1. Implement farmer profile creation and updating. 2. Store farmer details in DB."""
        # Create profile via storage
        farmer, token = self.storage.register_farmer(
            full_name="K. Satyanarayana",
            phone_number="9848099887",
            email="satya@kisan.ap.gov.in",
            password="FarmerPassword2026",
            preferred_language="te",
            district="Guntur",
            mandal="Tenali",
            village="Angalakuduru",
            land_size_acres=5.0,
            soil_type="black",
            water_availability="moderate",
        )
        self.assertIsNotNone(farmer["id"])
        self.assertEqual(farmer["full_name"], "K. Satyanarayana")
        self.assertEqual(farmer["district"], "Guntur")
        self.assertEqual(farmer["mandal"], "Tenali")

        # Verify storage in SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM farmers WHERE id = ?", (farmer["id"],)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["full_name"], "K. Satyanarayana")
            self.assertEqual(row["village"], "Angalakuduru")
            self.assertEqual(row["land_size_acres"], 5.0)

        # Update profile
        updated = self.storage.update_farmer_profile(
            farmer_id=farmer["id"],
            updates={
                "full_name": "K. Satyanarayana Varma",
                "land_size_acres": 6.5,
                "soil_type": "alluvial",
                "water_availability": "high",
            },
        )
        self.assertEqual(updated["full_name"], "K. Satyanarayana Varma")
        self.assertEqual(updated["land_size_acres"], 6.5)
        self.assertEqual(updated["soil_type"], "alluvial")
        self.assertEqual(updated["water_availability"], "high")

    # -------------------------------------------------------------------------
    # 3. Profile Retrieval
    # -------------------------------------------------------------------------
    def test_3_profile_retrieval(self):
        """3. Implement profile retrieval."""
        farmer, token = self.storage.register_farmer(
            full_name="B. Venkateswarlu",
            phone_number="9440123456",
            password="SecurePassword2026",
            district="Prakasam",
            mandal="Ongole",
            village="Santhanuthalapadu",
        )

        # Retrieve profile using storage method
        retrieved = self.storage.get_farmer_by_token(token)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], farmer["id"])
        self.assertEqual(retrieved["district"], "Prakasam")
        self.assertEqual(retrieved["mandal"], "Ongole")

        # Retrieve profile via REST API: GET /api/farmer/profile
        status, res = self._invoke("GET", "/api/farmer/profile", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(status, 200)
        self.assertEqual(res["farmer"]["full_name"], "B. Venkateswarlu")
        self.assertEqual(res["farmer"]["mandal"], "Ongole")

    # -------------------------------------------------------------------------
    # 4. Sowing Date and Crop Growth Stage
    # -------------------------------------------------------------------------
    def test_4_store_and_retrieve_sowing_date_and_crop_growth_stage(self):
        """4. Store and retrieve sowing date and crop growth stage."""
        # 1. Register with sowing date and crop growth stage
        farmer, token = self.storage.register_farmer(
            full_name="P. Ramesh",
            phone_number="9988112233",
            password="SecurePassword2026",
            district="Warangal",
            mandal="Narsampet",
            village="Chennaraopet",
            sowing_date="2026-06-20",
            crop_growth_stage="germination",
        )
        self.assertEqual(farmer["sowing_date"], "2026-06-20")
        self.assertEqual(farmer["crop_growth_stage"], "germination")

        # 2. Retrieve via token and verify
        retrieved = self.storage.get_farmer_by_token(token)
        self.assertEqual(retrieved["sowing_date"], "2026-06-20")
        self.assertEqual(retrieved["crop_growth_stage"], "germination")

        # 3. Update crop growth stage as crop advances (vegetative -> flowering)
        updated = self.storage.update_farmer_profile(
            farmer_id=farmer["id"],
            updates={
                "crop_growth_stage": "flowering",
                "sowing_date": "2026-06-25",
            },
        )
        self.assertEqual(updated["crop_growth_stage"], "flowering")
        self.assertEqual(updated["sowing_date"], "2026-06-25")

        # 4. Verify in relational view farm_details
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            farm = conn.execute("SELECT * FROM farm_details WHERE user_id = ?", (farmer["id"],)).fetchone()
            self.assertEqual(farm["sowing_date"], "2026-06-25")
            self.assertEqual(farm["crop_growth_stage"], "flowering")

        # 5. Validation failure on invalid sowing date format
        with self.assertRaises(AuthValidationError):
            self.storage.update_farmer_profile(
                farmer_id=farmer["id"],
                updates={"sowing_date": "25-06-2026"},  # Not YYYY-MM-DD
            )

        # 6. Validation failure on unsupported crop growth stage
        with self.assertRaises(AuthValidationError):
            self.storage.update_farmer_profile(
                farmer_id=farmer["id"],
                updates={"crop_growth_stage": "invalid_stage_xyz"},
            )

    # -------------------------------------------------------------------------
    # 5. Persistence Across Logout and Login
    # -------------------------------------------------------------------------
    def test_5_profile_data_persists_after_logout_and_login(self):
        """5. Ensure profile data persists after logout and login."""
        # 1. Register farmer via API with complete details including sowing date and growth stage
        status_reg, reg_res = self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "T. Subba Rao",
                "phone_number": "9123000111",
                "email": "subbarao@kisan.in",
                "password": "FarmerPassword2026",
                "preferred_language": "te",
                "district": "Krishna",
                "mandal": "Machilipatnam",
                "village": "Chilakalapudi",
                "land_size_acres": 4.25,
                "soil_type": "alluvial",
                "water_availability": "high",
                "sowing_date": "2026-07-10",
                "crop_growth_stage": "vegetative",
            },
        )
        self.assertEqual(status_reg, 201)
        initial_token = reg_res["token"]
        farmer_id = reg_res["farmer"]["id"]

        # 2. Farmer logs out: POST /api/auth/logout
        status_logout, logout_res = self._invoke(
            "POST", "/api/auth/logout", headers={"Authorization": f"Bearer {initial_token}"}
        )
        self.assertEqual(status_logout, 200)
        self.assertTrue(logout_res.get("logged_out"))

        # 3. Old session token must be revoked (401 Unauthorized)
        status_after_logout, _ = self._invoke(
            "GET", "/api/farmer/profile", headers={"Authorization": f"Bearer {initial_token}"}
        )
        self.assertEqual(status_after_logout, 401)

        # 4. Farmer logs in again: POST /api/auth/login
        status_login, login_res = self._invoke(
            "POST",
            "/api/auth/login",
            body={"identifier": "9123000111", "password": "FarmerPassword2026"},
        )
        self.assertEqual(status_login, 200)
        new_token = login_res["token"]
        self.assertNotEqual(initial_token, new_token, "Fresh session token must be generated on new login")

        # 5. Retrieve profile with the new session token
        status_get, get_res = self._invoke(
            "GET", "/api/farmer/profile", headers={"Authorization": f"Bearer {new_token}"}
        )
        self.assertEqual(status_get, 200)
        farmer = get_res["farmer"]

        # Verify all profile fields, sowing date, and crop growth stage persisted perfectly!
        self.assertEqual(farmer["id"], farmer_id)
        self.assertEqual(farmer["full_name"], "T. Subba Rao")
        self.assertEqual(farmer["phone_number"], "9123000111")
        self.assertEqual(farmer["email"], "subbarao@kisan.in")
        self.assertEqual(farmer["district"], "Krishna")
        self.assertEqual(farmer["mandal"], "Machilipatnam")
        self.assertEqual(farmer["village"], "Chilakalapudi")
        self.assertEqual(farmer["land_size_acres"], 4.25)
        self.assertEqual(farmer["soil_type"], "alluvial")
        self.assertEqual(farmer["water_availability"], "high")
        self.assertEqual(farmer["sowing_date"], "2026-07-10")
        self.assertEqual(farmer["crop_growth_stage"], "vegetative")
        self.assertEqual(farmer["preferred_language"], "te")

    # -------------------------------------------------------------------------
    # 6. Test All Profile APIs and Database Operations
    # -------------------------------------------------------------------------
    def test_6_profile_apis_and_database_operations(self):
        """6. Test all profile APIs and database operations."""
        # 1. Register
        status, reg = self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "API Test Farmer",
                "phone_number": "9000112233",
                "password": "Password123",
            },
        )
        self.assertEqual(status, 201)
        token = reg["token"]
        auth_header = {"Authorization": f"Bearer {token}"}

        # 2. PUT /api/farmer/profile with sowing date & growth stage
        status_put, put_res = self._invoke(
            "PUT",
            "/api/farmer/profile",
            body={
                "district": "Guntur",
                "mandal": "Mangalagiri",
                "village": "Atmakuru",
                "land_size_acres": 3.0,
                "soil_type": "black",
                "water_availability": "moderate",
                "sowing_date": "2026-10-01",
                "crop_growth_stage": "grain_filling",
            },
            headers=auth_header,
        )
        self.assertEqual(status_put, 200)
        self.assertEqual(put_res["farmer"]["sowing_date"], "2026-10-01")
        self.assertEqual(put_res["farmer"]["crop_growth_stage"], "grain_filling")

        # 3. GET /api/farmer/dashboard includes updated farm details
        status_dash, dash_res = self._invoke("GET", "/api/farmer/dashboard", headers=auth_header)
        self.assertEqual(status_dash, 200)
        self.assertEqual(dash_res["farmer"]["sowing_date"], "2026-10-01")
        self.assertEqual(dash_res["farmer"]["crop_growth_stage"], "grain_filling")


if __name__ == "__main__":
    unittest.main()
