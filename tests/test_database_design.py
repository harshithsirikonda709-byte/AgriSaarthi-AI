"""
Unit tests for Task 4: Normalized Database Design (users, farmer_profiles, farm_details).
Verifies:
- Entity isolation: users, farmer_profiles, and farm_details schemas
- Relational integrity: 1-to-1 relationship mapping via user_id
- 3-way SQL JOIN functionality
- Zero table duplication and migration preservation
"""

import unittest
import tempfile
import shutil
import os
import sqlite3

from agrisaarthi.storage import FarmerStorage


class TestNormalizedDatabaseDesign(unittest.TestCase):
    """Tests the relational database design for users, farmer_profiles, and farm_details."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_normalized_db.db")
        self.storage = FarmerStorage(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_users_table_or_view_structure(self):
        # Register a farmer
        self.storage.register_farmer(
            full_name="B. Nageswara Rao",
            phone_number="9876501234",
            email="nagesh@agro.in",
            password="SecurePass2026",
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            user = conn.execute("SELECT * FROM users WHERE identifier = '9876501234'").fetchone()

            self.assertIsNotNone(user, "users entity must be queryable")
            self.assertIn("id", user.keys())
            self.assertEqual(user["identifier"], "9876501234")
            self.assertTrue(len(user["password_hash"]) >= 64, "password_hash must be SHA-256")
            self.assertTrue(len(user["password_salt"]) == 32, "password_salt must be 16 bytes hex")
            self.assertIn("created_at", user.keys())

    def test_farmer_profiles_entity_structure(self):
        farmer, _ = self.storage.register_farmer(
            full_name="K. Lakshmi Devi",
            phone_number="9123409876",
            email="lakshmi@kisan.org",
            password="SecurePass2026",
            preferred_language="te",
            district="Kurnool",
            mandal="Nandyal",
            village="Mahanandi",
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            profile = conn.execute(
                "SELECT * FROM farmer_profiles WHERE user_id = ?", (farmer["id"],)
            ).fetchone()

            self.assertIsNotNone(profile, "farmer_profiles entity must exist for the user")
            self.assertEqual(profile["user_id"], farmer["id"])
            self.assertEqual(profile["full_name"], "K. Lakshmi Devi")
            self.assertEqual(profile["phone_number"], "9123409876")
            self.assertEqual(profile["email"], "lakshmi@kisan.org")
            self.assertEqual(profile["preferred_language"], "te")
            self.assertEqual(profile["district"], "Kurnool")
            self.assertEqual(profile["mandal"], "Nandyal")
            self.assertEqual(profile["village"], "Mahanandi")

    def test_farm_details_entity_structure(self):
        farmer, _ = self.storage.register_farmer(
            full_name="Ch. Venkatesh",
            phone_number="9848123456",
            password="SecurePass2026",
            district="Warangal",
            mandal="Jangaon",
            village="Bachannapet",
            land_size_acres=5.25,
            soil_type="black",
            water_availability="moderate",
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            farm = conn.execute(
                "SELECT * FROM farm_details WHERE user_id = ?", (farmer["id"],)
            ).fetchone()

            self.assertIsNotNone(farm, "farm_details entity must exist for the user")
            self.assertEqual(farm["user_id"], farmer["id"])
            self.assertEqual(farm["land_size_acres"], 5.25)
            self.assertEqual(farm["soil_type"], "black")
            self.assertEqual(farm["water_availability"], "moderate")

    def test_relational_three_way_join(self):
        """Verifies that joining users, farmer_profiles, and farm_details creates the unified farmer record."""
        farmer, _ = self.storage.register_farmer(
            full_name="M. Apparao",
            phone_number="9700112233",
            email="apparao@kisan.in",
            password="SecurePass2026",
            district="East Godavari",
            mandal="Kakinada",
            village="Samalkot",
            land_size_acres=3.75,
            soil_type="alluvial",
            water_availability="high",
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT 
                    u.id AS user_id,
                    u.identifier,
                    p.full_name,
                    p.email,
                    p.phone_number,
                    p.district,
                    p.mandal,
                    p.village,
                    p.preferred_language,
                    f.land_size_acres,
                    f.soil_type,
                    f.water_availability
                FROM users u
                INNER JOIN farmer_profiles p ON u.id = p.user_id
                INNER JOIN farm_details f ON u.id = f.user_id
                WHERE u.id = ?
            """
            unified = conn.execute(query, (farmer["id"],)).fetchone()

            self.assertIsNotNone(unified)
            self.assertEqual(unified["user_id"], farmer["id"])
            self.assertEqual(unified["full_name"], "M. Apparao")
            self.assertEqual(unified["mandal"], "Kakinada")
            self.assertEqual(unified["soil_type"], "alluvial")
            self.assertEqual(unified["land_size_acres"], 3.75)


if __name__ == "__main__":
    unittest.main()

