"""
Unit tests for Task 2: Farmer Data Structure & Secure Authentication.
Tests:
- FarmerProfile schema with all 11 required fields
- Phone number and email validation
- Password hashing (PBKDF2-HMAC-SHA256 + 16-byte cryptographic salt)
- Storage persistence of farmer profile (farmer_id, email, phone_number, mandal, district, village, etc.)
- Multi-identifier login (phone, email, username)
"""

import os
import unittest
import tempfile
import shutil

from agrisaarthi.models import (
    FarmerProfile,
    FarmerRegistrationRequest,
    FarmerLoginRequest,
    FarmerProfileUpdateRequest,
    SoilType,
    WaterAvailability,
)
from agrisaarthi.storage import (
    FarmerStorage,
    hash_password,
    verify_password,
    AuthValidationError,
    InvalidCredentialsError,
)


class TestFarmerDataStructure(unittest.TestCase):
    """Tests Pydantic validation for the 11 farmer profile fields."""

    def test_full_farmer_profile_structure(self):
        profile = FarmerProfile(
            farmer_id=101,
            full_name="M. Rama Rao",
            email="ramarao@example.com",
            phone_number="9876543210",
            district="Guntur",
            mandal="Tenali",
            village="Kolakaluru",
            land_size_acres=3.5,
            soil_type=SoilType.BLACK,
            water_availability=WaterAvailability.MODERATE,
            preferred_language="te",
        )
        self.assertEqual(profile.farmer_id, 101)
        self.assertEqual(profile.full_name, "M. Rama Rao")
        self.assertEqual(profile.email, "ramarao@example.com")
        self.assertEqual(profile.phone_number, "9876543210")
        self.assertEqual(profile.district, "Guntur")
        self.assertEqual(profile.mandal, "Tenali")
        self.assertEqual(profile.village, "Kolakaluru")
        self.assertEqual(profile.land_size_acres, 3.5)
        self.assertEqual(profile.soil_type, SoilType.BLACK)
        self.assertEqual(profile.water_availability, WaterAvailability.MODERATE)
        self.assertEqual(profile.preferred_language, "te")

    def test_phone_number_cleaning_and_validation(self):
        # Cleans +91 prefix and dashes
        profile = FarmerProfile(
            full_name="K. Venkatesh",
            phone_number="+91 91234-56789",
        )
        self.assertEqual(profile.phone_number, "9123456789")

        # Invalid phone length raises ValueError
        with self.assertRaises(ValueError):
            FarmerProfile(
                full_name="K. Venkatesh",
                phone_number="12345",  # Too short
            )

    def test_email_validation(self):
        # Valid email
        profile = FarmerProfile(
            full_name="K. Venkatesh",
            email="farmer@kisan.gov.in",
        )
        self.assertEqual(profile.email, "farmer@kisan.gov.in")

        # Invalid email raises ValueError
        with self.assertRaises(ValueError):
            FarmerProfile(
                full_name="K. Venkatesh",
                email="not-an-email",
            )

    def test_password_never_in_profile_model(self):
        # Confirm FarmerProfile has no password or password_hash fields
        profile = FarmerProfile(full_name="Sita Devi")
        data = profile.dict()
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)
        self.assertNotIn("password_salt", data)


class TestPasswordSecurity(unittest.TestCase):
    """Tests PBKDF2-HMAC-SHA256 password hashing security requirements."""

    def test_hash_creates_salt_and_digest(self):
        raw_pw = "KisanPass2026@"
        pw_hash, pw_salt = hash_password(raw_pw)

        self.assertTrue(len(pw_hash) >= 64, "Hash hex digest must be at least 64 chars (SHA-256)")
        self.assertEqual(len(pw_salt), 32, "Salt hex must be 32 chars (16 bytes)")
        self.assertNotEqual(raw_pw, pw_hash, "Raw password must NEVER match stored hash")

    def test_unique_salts_produce_different_hashes(self):
        pw = "SamePassword123"
        hash1, salt1 = hash_password(pw)
        hash2, salt2 = hash_password(pw)

        self.assertNotEqual(salt1, salt2, "Each hash invocation must generate a fresh random salt")
        self.assertNotEqual(hash1, hash2, "Identical passwords with different salts must yield different hashes")

    def test_verify_password(self):
        pw = "SecretFarmerKey!"
        pw_hash, pw_salt = hash_password(pw)

        self.assertTrue(verify_password(pw, pw_hash, pw_salt))
        self.assertFalse(verify_password("WrongPassword", pw_hash, pw_salt))
        self.assertFalse(verify_password("", pw_hash, pw_salt))


class TestStorageFarmerProfileIntegration(unittest.TestCase):
    """Tests SQLite database storage with the new Task 2 schema fields."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_farmers.db")
        self.storage = FarmerStorage(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_and_retrieve_all_11_fields(self):
        farmer, token = self.storage.register_farmer(
            full_name="Anji Reddy",
            phone_number="9848012345",
            email="anji.reddy@gmail.com",
            password="SecurePassword999",
            preferred_language="te",
            district="Khammam",
            mandal="Madhira",
            village="Siripuram",
            land_size_acres=4.5,
            soil_type="black",
            water_availability="high",
        )

        self.assertIn("id", farmer)
        self.assertEqual(farmer["farmer_id"], farmer["id"])
        self.assertEqual(farmer["full_name"], "Anji Reddy")
        self.assertEqual(farmer["phone_number"], "9848012345")
        self.assertEqual(farmer["email"], "anji.reddy@gmail.com")
        self.assertEqual(farmer["district"], "Khammam")
        self.assertEqual(farmer["mandal"], "Madhira")
        self.assertEqual(farmer["village"], "Siripuram")
        self.assertEqual(farmer["land_size_acres"], 4.5)
        self.assertEqual(farmer["soil_type"], "black")
        self.assertEqual(farmer["water_availability"], "high")
        self.assertEqual(farmer["preferred_language"], "te")

        # Plaintext password and hashes must NOT be in the returned dictionary
        self.assertNotIn("password", farmer)
        self.assertNotIn("password_hash", farmer)
        self.assertNotIn("password_salt", farmer)

        # Retrieve profile using the session token
        retrieved = self.storage.get_farmer_by_token(token)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["id"], farmer["id"])
        self.assertEqual(retrieved["mandal"], "Madhira")

    def test_multi_identifier_login(self):
        # Register a farmer with phone and email
        self.storage.register_farmer(
            full_name="Suresh Kumar",
            phone_number="9988776655",
            email="suresh@kisan.org",
            password="FarmerPassword123",
        )

        # 1. Login with Phone Number
        farmer_by_phone, token1 = self.storage.authenticate_farmer(
            identifier="9988776655", password="FarmerPassword123"
        )
        self.assertEqual(farmer_by_phone["full_name"], "Suresh Kumar")
        self.assertTrue(bool(token1))

        # 2. Login with Email
        farmer_by_email, token2 = self.storage.authenticate_farmer(
            identifier="suresh@kisan.org", password="FarmerPassword123"
        )
        self.assertEqual(farmer_by_email["id"], farmer_by_phone["id"])
        self.assertTrue(bool(token2))

        # 3. Invalid password fails
        with self.assertRaises(InvalidCredentialsError):
            self.storage.authenticate_farmer(
                identifier="9988776655", password="WrongPassword"
            )

    def test_update_profile_task2_fields(self):
        farmer, _ = self.storage.register_farmer(
            full_name="Initial Name",
            identifier="9123456780",
            password="Password123",
        )

        # Update mandal, email, district, soil, land size
        updated = self.storage.update_farmer_profile(
            farmer_id=farmer["id"],
            updates={
                "full_name": "Updated Farmer Name",
                "email": "updated.farmer@ap.gov.in",
                "mandal": "Mangalagiri",
                "district": "Guntur",
                "village": "Navuluru",
                "land_size_acres": 6.25,
                "soil_type": "alluvial",
                "water_availability": "moderate",
            },
        )

        self.assertEqual(updated["full_name"], "Updated Farmer Name")
        self.assertEqual(updated["email"], "updated.farmer@ap.gov.in")
        self.assertEqual(updated["mandal"], "Mangalagiri")
        self.assertEqual(updated["district"], "Guntur")
        self.assertEqual(updated["village"], "Navuluru")
        self.assertEqual(updated["land_size_acres"], 6.25)
        self.assertEqual(updated["soil_type"], "alluvial")
        self.assertEqual(updated["water_availability"], "moderate")


if __name__ == "__main__":
    unittest.main()

