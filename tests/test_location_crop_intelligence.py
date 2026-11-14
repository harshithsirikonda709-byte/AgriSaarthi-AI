"""
Comprehensive Unit & Integration Tests for Day 3 Location-Aware Crop Intelligence:
1. Save farmer GPS latitude and longitude.
2. Implement nearby crop API with a 2.5 km radius.
3. Implement farmer crop observation submission API.
4. Include crop name, location, sowing date, growth stage and consent.
5. Connect nearby crop observations with the crop decision engine.
6. Exclude invalid, stale or non-consented records.
7. Handle missing GPS and unavailable nearby data safely.
8. Write and run backend tests.
"""

import os
import json
import sqlite3
import tempfile
import shutil
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO

from agrisaarthi.models import (
    FarmerProfile,
    FarmerRegistrationRequest,
    FarmerProfileUpdateRequest,
    FarmerProfileRequest,
    CropObservationSubmission,
    NearbyCropObservation,
    CropGrowthStage,
    SoilType,
    WaterAvailability,
    Season,
)
from agrisaarthi.storage import (
    FarmerStorage,
    AuthValidationError,
    InvalidCredentialsError,
    haversine_distance_km,
)
from agrisaarthi.engine import AgriSaarthiEngine
from scripts.run_farmer_ui import AgriFarmerUIHandler


class TestDay3LocationCropIntelligence(unittest.TestCase):
    """Rigorous tests covering all 8 Day 3 Location-Aware Crop Intelligence requirements."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_day3_farmers.db")
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
        captured = {"status": None, "headers": {}, "body": b""}

        def mock_send_response(code, message=None):
            captured["status"] = code

        def mock_send_header(k, v):
            captured["headers"][k] = v

        def mock_end_headers():
            pass

        handler.send_response = mock_send_response
        handler.send_header = mock_send_header
        handler.end_headers = mock_end_headers
        out_stream = BytesIO()
        handler.wfile = out_stream

        if method == "GET":
            handler.do_GET()
        elif method == "POST":
            handler.do_POST()
        elif method == "PUT":
            handler.do_PUT()
        else:
            raise ValueError(f"Unsupported method {method}")

        raw_out = out_stream.getvalue()
        try:
            parsed = json.loads(raw_out.decode("utf-8")) if raw_out else {}
        except Exception:
            parsed = {"raw": raw_out.decode("utf-8", errors="replace")}
        return captured["status"], parsed

    # =========================================================================
    # Task 1: Save Farmer GPS Latitude and Longitude
    # =========================================================================
    def test_task1_save_farmer_gps_coordinates(self):
        """Verify farmer GPS latitude and longitude are validated, stored, and retrieved."""
        # Registration with GPS
        farmer, token = self.storage.register_farmer(
            full_name="Kisan Venkatesh",
            identifier="9848012345",
            password="SecurePassword123!",
            district="Guntur",
            village="Tenali",
            land_size_acres=4.5,
            soil_type="black",
            water_availability="moderate",
            latitude=16.243000,
            longitude=80.640000,
        )
        self.assertAlmostEqual(farmer["latitude"], 16.243, places=3)
        self.assertAlmostEqual(farmer["longitude"], 80.640, places=3)

        # Profile retrieval by token
        retrieved = self.storage.get_farmer_by_token(token)
        self.assertIsNotNone(retrieved)
        self.assertAlmostEqual(retrieved["latitude"], 16.243, places=3)
        self.assertAlmostEqual(retrieved["longitude"], 80.640, places=3)

        # Update GPS coordinates via update_farmer_profile
        updated = self.storage.update_farmer_profile(
            farmer["id"],
            {"latitude": 16.3067, "longitude": 80.4365}
        )
        self.assertAlmostEqual(updated["latitude"], 16.3067, places=4)
        self.assertAlmostEqual(updated["longitude"], 80.4365, places=4)

        # Ensure validation rejects out-of-range coordinates
        with self.assertRaises(AuthValidationError):
            self.storage.update_farmer_profile(farmer["id"], {"latitude": 95.0})  # > 90

        with self.assertRaises(AuthValidationError):
            self.storage.update_farmer_profile(farmer["id"], {"longitude": -190.0})  # < -180

    # =========================================================================
    # Task 2: Haversine Distance & Nearby Crop Observations (2.5 km Radius)
    # =========================================================================
    def test_task2_haversine_and_2_5_km_radius(self):
        """Verify 2.5 km radius spatial filtering using Haversine formula."""
        center_lat = 16.3067
        center_lon = 80.4365

        # 1. Point at ~1.0 km (inside radius)
        self.storage.record_crop_observation(
            crop_name="Cotton",
            latitude=16.3140,
            longitude=80.4400,
            sowing_date="2026-06-15",
            crop_growth_stage="vegetative",
            consent_shared=True,
        )

        # 2. Point at ~2.1 km (inside 2.5 km radius)
        self.storage.record_crop_observation(
            crop_name="Chilli",
            latitude=16.3220,
            longitude=80.4450,
            sowing_date="2026-07-01",
            crop_growth_stage="flowering",
            consent_shared=True,
        )

        # 3. Point at ~4.8 km (outside 2.5 km radius)
        self.storage.record_crop_observation(
            crop_name="Rice",
            latitude=16.3450,
            longitude=80.4600,
            sowing_date="2026-06-20",
            crop_growth_stage="grain_filling",
            consent_shared=True,
        )

        # Query nearby within default 2.5 km
        nearby = self.storage.get_nearby_crop_observations(
            latitude=center_lat,
            longitude=center_lon,
            radius_km=2.5,
        )

        crops_returned = [o["crop_name"] for o in nearby]
        self.assertIn("Cotton", crops_returned)
        self.assertIn("Chilli", crops_returned)
        self.assertNotIn("Rice", crops_returned, "Rice is at ~4.8 km and must be excluded from 2.5 km radius.")

        # Ensure sorted by distance ascending
        distances = [o["distance_km"] for o in nearby]
        self.assertEqual(distances, sorted(distances))
        self.assertTrue(all(d <= 2.5 for d in distances))

    # =========================================================================
    # Task 3 & 4: Crop Observation Submission API & Required Fields
    # =========================================================================
    def test_task3_and_4_observation_submission_api(self):
        """Verify POST /api/crops/observations validates crop, location, sowing date, stage, and consent."""
        # Register a farmer to test authenticated submission
        farmer, token = self.storage.register_farmer(
            full_name="Lakshmi Devi",
            identifier="9848123456",
            password="SecurePassword123!",
            latitude=16.5000,
            longitude=80.6000,
        )

        # 1. Valid submission via HTTP API
        payload = {
            "crop_name": "Maize",
            "latitude": 16.5050,
            "longitude": 80.6080,
            "sowing_date": "2026-07-10",
            "crop_growth_stage": "flowering",
            "consent_shared": True,
            "field_notes": "Healthy crop with drip irrigation.",
        }
        status, resp = self._invoke(
            "POST",
            "/api/crops/observations",
            body=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(status, 201)
        self.assertTrue(resp.get("success"))
        obs = resp["observation"]
        self.assertEqual(obs["crop_name"], "Maize")
        self.assertEqual(obs["crop_growth_stage"], "flowering")
        self.assertEqual(obs["sowing_date"], "2026-07-10")
        self.assertTrue(obs["consent_shared"])
        self.assertEqual(obs["farmer_id"], farmer["id"])
        self.assertEqual(obs["farmer_name"], "Lakshmi Devi")

        # 2. Invalid sowing date format fails (Task 4)
        bad_payload = dict(payload, sowing_date="10-07-2026")
        status_bad_date, _ = self._invoke("POST", "/api/crops/observations", body=bad_payload)
        self.assertEqual(status_bad_date, 400)

        # 3. Invalid growth stage fails
        bad_stage_payload = dict(payload, crop_growth_stage="blooming_rapidly")
        status_bad_stage, _ = self._invoke("POST", "/api/crops/observations", body=bad_stage_payload)
        self.assertEqual(status_bad_stage, 400)

        # 4. Missing location fails
        bad_loc_payload = dict(payload, latitude=None, longitude=None)
        status_bad_loc, _ = self._invoke("POST", "/api/crops/observations", body=bad_loc_payload)
        self.assertEqual(status_bad_loc, 400)

    # =========================================================================
    # Task 6: Exclude Invalid, Stale, or Non-Consented Records
    # =========================================================================
    def test_task6_exclude_stale_and_non_consented_records(self):
        """Verify non-consented (consent=False) and stale (>180 days) observations are strictly excluded."""
        center_lat = 17.0000
        center_lon = 81.0000

        # Fresh consented observation (Within 1.0 km, 5 days ago)
        fresh_time = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        self.storage.record_crop_observation(
            crop_name="Groundnut",
            latitude=17.0050,
            longitude=81.0050,
            sowing_date="2026-06-01",
            crop_growth_stage="flowering",
            consent_shared=True,
            observed_at=fresh_time,
        )

        # Non-consented observation (consent_shared = False)
        self.storage.record_crop_observation(
            crop_name="Cotton",
            latitude=17.0040,
            longitude=81.0040,
            sowing_date="2026-06-01",
            crop_growth_stage="vegetative",
            consent_shared=False,  # Private observation
            observed_at=fresh_time,
        )

        # Stale observation (210 days old, > 180 max_age_days)
        stale_time = (datetime.now(timezone.utc) - timedelta(days=210)).isoformat()
        self.storage.record_crop_observation(
            crop_name="Sunflower",
            latitude=17.0030,
            longitude=81.0030,
            sowing_date="2025-11-01",
            crop_growth_stage="maturity",
            consent_shared=True,
            observed_at=stale_time,
        )

        # Query nearby observations via API
        status, resp = self._invoke(
            "GET",
            f"/api/crops/nearby?latitude={center_lat}&longitude={center_lon}&radius_km=2.5",
        )
        self.assertEqual(status, 200)
        observations = resp["observations"]
        returned_crops = [o["crop_name"] for o in observations]

        # Groundnut is fresh and consented -> MUST be present
        self.assertIn("Groundnut", returned_crops)

        # Cotton is non-consented -> MUST be excluded
        self.assertNotIn("Cotton", returned_crops, "Non-consented observation must be strictly excluded from peer queries.")

        # Sunflower is stale (210 days old) -> MUST be excluded
        self.assertNotIn("Sunflower", returned_crops, "Stale observation (>180 days) must be excluded from nearby queries.")

    # =========================================================================
    # Task 5: Connect Nearby Crop Observations with Crop Decision Engine
    # =========================================================================
    def test_task5_decision_engine_peer_boost_and_monoculture(self):
        """Verify peer crop observations boost suitability scores and monoculture triggers risk advisory."""
        req = FarmerProfileRequest(
            state="Andhra Pradesh",
            district="Guntur",
            land_size_acres=3.0,
            soil_type=SoilType.BLACK,
            water_availability=WaterAvailability.MODERATE,
            season=Season.KHARIF,
            budget_inr=90000,
            latitude=16.3067,
            longitude=80.4365,
        )

        # 1. Baseline without peer observations
        res_baseline = AgriSaarthiEngine.execute(req, nearby_observations=[])
        crops_baseline = {c.crop_name: c for c in res_baseline.primary_recommendations + res_baseline.alternative_recommendations}
        self.assertIn("Cotton (Bt Cotton)", crops_baseline)
        base_score = crops_baseline["Cotton (Bt Cotton)"].suitability_score

        # 2. Add peer observations within 2.5 km where 3 neighbors cultivate Cotton
        peer_obs = [
            {"crop_name": "Cotton", "crop_growth_stage": "vegetative", "consent_shared": True, "is_stale": False},
            {"crop_name": "Cotton", "crop_growth_stage": "vegetative", "consent_shared": True, "is_stale": False},
            {"crop_name": "Cotton", "crop_growth_stage": "flowering", "consent_shared": True, "is_stale": False},
        ]
        res_with_peers = AgriSaarthiEngine.execute(req, nearby_observations=peer_obs)
        crops_peers = {c.crop_name: c for c in res_with_peers.primary_recommendations + res_with_peers.alternative_recommendations}
        peer_cotton = crops_peers["Cotton (Bt Cotton)"]

        # Verification of Peer Strength note
        self.assertTrue(
            any("Peer Verified" in s for s in peer_cotton.key_strengths),
            "Decision engine must attach peer verification strength when neighbors cultivate the crop."
        )

        # Verification of Monoculture Alert (100% of nearby fields are Cotton)
        self.assertTrue(
            any("Monoculture" in r for r in peer_cotton.risk_factors),
            "Decision engine must warn against monoculture vulnerability when high density is observed."
        )
        self.assertTrue(
            any("Monoculture" in l for l in res_with_peers.limitations_and_advisory),
            "Monoculture warning must appear in general agricultural advisories."
        )

    # =========================================================================
    # Task 7: Handle Missing GPS and Unavailable Nearby Data Safely
    # =========================================================================
    def test_task7_handle_missing_gps_safely(self):
        """Verify engine and APIs degrade gracefully with zero errors when GPS is absent or unavailable."""
        # 1. API GET /api/crops/nearby without coordinates returns 200 OK with empty list
        status, resp = self._invoke("GET", "/api/crops/nearby")
        self.assertEqual(status, 200)
        self.assertEqual(resp["count"], 0)
        self.assertEqual(resp["observations"], [])
        self.assertIn("message", resp)

        # 2. Decision engine runs safely when lat/lon are None
        req_no_gps = FarmerProfileRequest(
            state="Telangana",
            district="Warangal",
            land_size_acres=2.0,
            soil_type=SoilType.RED,
            water_availability=WaterAvailability.LOW,
            season=Season.KHARIF,
            budget_inr=35000,
            latitude=None,
            longitude=None,
        )
        res_no_gps = AgriSaarthiEngine.execute(req_no_gps)
        self.assertEqual(res_no_gps.workflow_status, "SUCCESS")
        self.assertGreater(len(res_no_gps.primary_recommendations), 0)
        self.assertTrue(any("GPS coordinates not provided" in r for r in res_no_gps.step_by_step_reasoning))

        # 3. Decision engine runs safely when GPS is provided but no nearby observations exist
        req_with_gps = FarmerProfileRequest(
            state="Punjab",
            district="Ludhiana",
            land_size_acres=5.0,
            soil_type=SoilType.ALLUVIAL,
            water_availability=WaterAvailability.HIGH,
            season=Season.RABI,
            budget_inr=150000,
            latitude=30.9010,
            longitude=75.8573,
        )
        res_empty_nearby = AgriSaarthiEngine.execute(req_with_gps, nearby_observations=[])
        self.assertEqual(res_empty_nearby.workflow_status, "SUCCESS")
        self.assertGreater(len(res_empty_nearby.primary_recommendations), 0)

    # =========================================================================
    # Task 8: Farmer My-Observations Endpoint
    # =========================================================================
    def test_task8_farmer_my_observations_endpoint(self):
        """Verify GET /api/crops/observations/my returns only authenticated farmer's observations."""
        farmer1, token1 = self.storage.register_farmer(
            full_name="Farmer One",
            identifier="9111111111",
            password="Password1!",
            latitude=16.1,
            longitude=80.1,
        )
        farmer2, token2 = self.storage.register_farmer(
            full_name="Farmer Two",
            identifier="9222222222",
            password="Password2!",
            latitude=16.2,
            longitude=80.2,
        )

        # Log observation for Farmer 1
        self.storage.record_crop_observation(
            crop_name="Black Gram",
            latitude=16.102,
            longitude=80.103,
            sowing_date="2026-06-15",
            crop_growth_stage="germination",
            farmer_id=farmer1["id"],
            farmer_name=farmer1["full_name"],
        )

        # Log observation for Farmer 2
        self.storage.record_crop_observation(
            crop_name="Soybean",
            latitude=16.202,
            longitude=80.203,
            sowing_date="2026-06-18",
            crop_growth_stage="vegetative",
            farmer_id=farmer2["id"],
            farmer_name=farmer2["full_name"],
        )

        # Query as Farmer 1
        status1, resp1 = self._invoke(
            "GET",
            "/api/crops/observations/my",
            headers={"Authorization": f"Bearer {token1}"},
        )
        self.assertEqual(status1, 200)
        self.assertEqual(len(resp1["observations"]), 1)
        self.assertEqual(resp1["observations"][0]["crop_name"], "Black Gram")

        # Query as Farmer 2
        status2, resp2 = self._invoke(
            "GET",
            "/api/crops/observations/my",
            headers={"Authorization": f"Bearer {token2}"},
        )
        self.assertEqual(status2, 200)
        self.assertEqual(len(resp2["observations"]), 1)
        self.assertEqual(resp2["observations"][0]["crop_name"], "Soybean")


if __name__ == "__main__":
    unittest.main()
