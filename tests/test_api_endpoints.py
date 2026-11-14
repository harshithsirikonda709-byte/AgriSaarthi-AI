"""
Comprehensive API Contract Tests for Task 3:
1. POST /api/auth/register
2. POST /api/auth/login
3. GET  /api/farmer/profile
4. PUT  /api/farmer/profile
5. GET  /api/farmer/dashboard
"""

import json
import unittest
import tempfile
import shutil
import os
from io import BytesIO
from unittest.mock import MagicMock

from scripts.run_farmer_ui import AgriFarmerUIHandler, get_storage
from agrisaarthi.storage import FarmerStorage


class TestAPIEndpointContracts(unittest.TestCase):
    """Rigorous HTTP contract tests for the 5 core farmer backend endpoints."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_api_farmers.db")
        os.environ["AGRI_DB_PATH"] = self.db_path
        os.environ["DISABLE_LIVE_WEATHER"] = "true"
        # Force re-initialization of storage singleton
        import scripts.run_farmer_ui as ui_module
        ui_module._STORAGE_INSTANCE = FarmerStorage(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _invoke(self, method: str, path: str, body: dict = None, headers: dict = None):
        """Invoke AgriFarmerUIHandler in memory and capture status code, headers, and body."""
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
    # 1. POST /api/auth/register Contract
    # -------------------------------------------------------------------------
    def test_contract_post_register_success(self):
        status, res = self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "K. Somanna",
                "phone_number": "9848011223",
                "email": "somanna@example.com",
                "password": "FarmerPassword2026",
                "preferred_language": "te",
                "district": "Guntur",
                "mandal": "Mangalagiri",
                "village": "Atmakuru",
                "land_size_acres": 3.0,
                "soil_type": "black",
                "water_availability": "moderate",
            },
        )
        self.assertEqual(status, 201, "Successful registration must return HTTP 201 Created")
        self.assertIn("farmer", res)
        self.assertIn("token", res)
        farmer = res["farmer"]
        self.assertEqual(farmer["full_name"], "K. Somanna")
        self.assertEqual(farmer["phone_number"], "9848011223")
        self.assertEqual(farmer["email"], "somanna@example.com")
        self.assertEqual(farmer["mandal"], "Mangalagiri")
        self.assertEqual(farmer["soil_type"], "black")
        self.assertNotIn("password", farmer)
        self.assertNotIn("password_hash", farmer)

    def test_contract_post_register_duplicate_error(self):
        # First registration
        self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "First User",
                "phone_number": "9998887776",
                "password": "Password123",
            },
        )
        # Duplicate registration
        status, res = self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "Duplicate User",
                "phone_number": "9998887776",
                "password": "Password123",
            },
        )
        self.assertEqual(status, 400, "Duplicate registration must return HTTP 400 Bad Request")
        self.assertIn("error", res)

    def test_contract_post_register_short_password_error(self):
        status, res = self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "Test User",
                "phone_number": "9123456789",
                "password": "123",  # Under 6 chars
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("error", res)

    # -------------------------------------------------------------------------
    # 2. POST /api/auth/login Contract
    # -------------------------------------------------------------------------
    def test_contract_post_login_success_and_failure(self):
        # Register user first
        self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "Login Farmer",
                "phone_number": "9000011111",
                "email": "loginfarmer@ap.gov.in",
                "password": "SecretPassword123",
            },
        )

        # 1. Login with Phone Number
        status1, res1 = self._invoke(
            "POST",
            "/api/auth/login",
            body={"identifier": "9000011111", "password": "SecretPassword123"},
        )
        self.assertEqual(status1, 200, "Valid phone login must return HTTP 200 OK")
        self.assertTrue(bool(res1.get("token")))

        # 2. Login with Email directly
        status2, res2 = self._invoke(
            "POST",
            "/api/auth/login",
            body={"email": "loginfarmer@ap.gov.in", "password": "SecretPassword123"},
        )
        self.assertEqual(status2, 200, "Valid email login must return HTTP 200 OK")

        # 3. Wrong password returns 401
        status3, res3 = self._invoke(
            "POST",
            "/api/auth/login",
            body={"identifier": "9000011111", "password": "WrongPassword!"},
        )
        self.assertEqual(status3, 401, "Invalid password must return HTTP 401 Unauthorized")
        self.assertIn("error", res3)

    # -------------------------------------------------------------------------
    # 3. GET /api/farmer/profile Contract
    # -------------------------------------------------------------------------
    def test_contract_get_farmer_profile(self):
        # Unauthenticated request without Bearer token returns 401
        status_unauth, res_unauth = self._invoke("GET", "/api/farmer/profile")
        self.assertEqual(status_unauth, 401)
        self.assertIn("error", res_unauth)

        # Register and get token
        _, reg_res = self._invoke(
            "POST",
            "/api/auth/register",
            body={
                "full_name": "Profile Farmer",
                "phone_number": "9440055555",
                "password": "SecurePassword1",
                "district": "Krishna",
                "mandal": "Gudivada",
            },
        )
        token = reg_res["token"]
        auth_header = {"Authorization": f"Bearer {token}"}

        # Authenticated GET returns 200 and profile
        status_auth, res_auth = self._invoke("GET", "/api/farmer/profile", headers=auth_header)
        self.assertEqual(status_auth, 200, "Authenticated GET /api/farmer/profile must return HTTP 200 OK")
        self.assertEqual(res_auth["farmer"]["full_name"], "Profile Farmer")
        self.assertEqual(res_auth["farmer"]["district"], "Krishna")
        self.assertEqual(res_auth["farmer"]["mandal"], "Gudivada")

    # -------------------------------------------------------------------------
    # 4. PUT /api/farmer/profile Contract
    # -------------------------------------------------------------------------
    def test_contract_put_farmer_profile(self):
        # Register user
        _, reg_res = self._invoke(
            "POST",
            "/api/auth/register",
            body={"full_name": "Initial Name", "phone_number": "9330044444", "password": "SecurePassword1"},
        )
        token = reg_res["token"]
        auth_header = {"Authorization": f"Bearer {token}"}

        # PUT update
        status, res = self._invoke(
            "PUT",
            "/api/farmer/profile",
            body={
                "full_name": "Updated Farmer",
                "mandal": "Tadepalligudem",
                "district": "West Godavari",
                "village": "Penumantra",
                "land_size_acres": 5.5,
                "soil_type": "alluvial",
                "water_availability": "high",
            },
            headers=auth_header,
        )
        self.assertEqual(status, 200, "Valid PUT /api/farmer/profile must return HTTP 200 OK")
        farmer = res["farmer"]
        self.assertEqual(farmer["full_name"], "Updated Farmer")
        self.assertEqual(farmer["mandal"], "Tadepalligudem")
        self.assertEqual(farmer["district"], "West Godavari")
        self.assertEqual(farmer["land_size_acres"], 5.5)
        self.assertEqual(farmer["soil_type"], "alluvial")
        self.assertTrue(farmer["profile_completed"])

    # -------------------------------------------------------------------------
    # 5. GET /api/farmer/dashboard Contract
    # -------------------------------------------------------------------------
    def test_contract_get_farmer_dashboard(self):
        # Unauthenticated request returns 401
        status_unauth, _ = self._invoke("GET", "/api/farmer/dashboard")
        self.assertEqual(status_unauth, 401)

        # Register farmer
        _, reg_res = self._invoke(
            "POST",
            "/api/auth/register",
            body={"full_name": "Dashboard Farmer", "phone_number": "9220033333", "password": "SecurePassword1"},
        )
        token = reg_res["token"]
        auth_header = {"Authorization": f"Bearer {token}"}

        status, res = self._invoke("GET", "/api/farmer/dashboard", headers=auth_header)
        self.assertEqual(status, 200, "Authenticated GET /api/farmer/dashboard must return HTTP 200 OK")
        self.assertIn("farmer", res)
        self.assertIn("history", res)
        self.assertIn("weather", res)
        self.assertEqual(res["farmer"]["full_name"], "Dashboard Farmer")
        self.assertIsInstance(res["history"], list)
        self.assertIsInstance(res["weather"], dict)


if __name__ == "__main__":
    unittest.main()

