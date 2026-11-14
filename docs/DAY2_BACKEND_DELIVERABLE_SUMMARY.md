# 🌾 AgriSaarthi AI — Day 2 Backend Engineering Deliverable

**To**: Team Lead / Project Review Board  
**From**: Charan (Backend Lead)  
**Branch**: `feature/charan-backend`  
**Repository**: [AgriSaarthi-AI](https://github.com/harshithsirikonda709-byte/AgriSaarthi-AI)  
**Date**: Day 2 Backend Development Cycle  
**Status**: ✅ All 5 Tasks Complete & 100% Verified (96/96 Pytest Tests Passed, 19/19 Live HTTP Audits Passed)  

---

## 📌 Executive Summary

Today's main objective was to **prepare the backend foundation for the farmer website and AI engine**. 

All 5 assigned backend tasks have been developed, verified, and documented on branch `feature/charan-backend`. The backend now features a strongly-typed farmer profile schema, enterprise-grade PBKDF2 password hashing, formal REST API contracts, a normalized 3-entity database architecture, and a 100% automated test pass rate with zero breaking changes to existing features.

---

## 🚀 Detailed Breakdown of Completed Tasks

### Task 1 — Existing Backend Inspection
- **Audit Performed**: Fully inspected the existing dual-server architecture:
  - Entry point 1: `scripts/run_farmer_ui.py` (Port 8080 HTTP Server for farmer web portal).
  - Entry point 2: `agrisaarthi/agent.py` (Port 8000 Fetch.ai uAgent for autonomous agent comms).
  - Core engine: `agrisaarthi/engine.py` (ICAR rule engine and agronomic crop recommendations).
  - Storage layer: `agrisaarthi/storage.py` (SQLite persistent database).
- **Outcome**: Confirmed zero third-party dependencies are required for the web server; existing code uses Python standard library (`http.server`, `sqlite3`, `hashlib`, `hmac`, `secrets`).

---

### Task 2 — Farmer Data Structure & Secure Authentication
- **11-Field Farmer Profile**: Defined in `agrisaarthi/models.py` (`FarmerProfile`) with strict Pydantic validation:
  1. `farmer_id`: Unique account ID (`Optional[int]`).
  2. `full_name`: Farmer's legal name (min 2 chars, stripped).
  3. `email`: Optional contact email (validated via email regex).
  4. `phone_number`: 10-digit Indian mobile number (auto-cleans `+91`, spaces, dashes).
  5. `district`: Administrative district (e.g., *Guntur*, *Warangal*).
  6. `mandal`: Sub-district / Tehsil (crucial for AP & Telangana agricultural extension).
  7. `village`: Local village or Gram Panchayat.
  8. `land_size_acres`: Holding size in acres (range: $0.1$ to $5000$).
  9. `soil_type`: Validated against `SoilType` enum (`alluvial`, `black`, `red`, `laterite`, `sandy_loam`, `clayey`).
  10. `water_availability`: Validated against `WaterAvailability` enum (`low`, `moderate`, `high`).
  11. `preferred_language`: Advisory language (`'te'` for Telugu, `'en'` for English).
- **Password Security Mechanism**:
  - Passwords are **never stored in plaintext**.
  - Uses **PBKDF2-HMAC-SHA256** with **200,000 key-stretching iterations**.
  - Uses **16-byte cryptographically secure random salts** (`secrets.token_hex(16)`).
  - Verification uses **constant-time digest comparison** (`hmac.compare_digest`) to defeat timing attacks.
  - Plaintext passwords and hashes are permanently excluded from returned profile dictionaries.

---

### Task 3 — API Endpoints & Contract Definition
Prepared and standardized the formal API contracts for all 5 core endpoints in `scripts/run_farmer_ui.py`:

| HTTP Method | Endpoint URL | Auth Required | Success Status | Key Functionality |
| :--- | :--- | :---: | :---: | :--- |
| **POST** | `/api/auth/register` | No | `201 Created` | Registers farmer with all 11 fields, hashes password, creates active session token. |
| **POST** | `/api/auth/login` | No | `200 OK` | Flexible authentication via **either mobile number, email, or username**; returns Bearer session token. |
| **GET** | `/api/farmer/profile` | Yes (`Bearer`) | `200 OK` | Retrieves authenticated farmer's complete profile. Returns `401` if token is missing/expired. |
| **PUT** | `/api/farmer/profile` | Yes (`Bearer`) | `200 OK` | Updates personal, location, and farm holding fields with range and enum validation. |
| **GET** | `/api/farmer/dashboard` | Yes (`Bearer`) | `200 OK` | Aggregates farmer profile, last 10 advisory history items, and live weather/alerts. |

---

### Task 4 — Relational Database Design
Designed a normalized 3-entity relational database model:
- **`users` Table / View**: Primary Key `id`, `identifier` (unique phone/email), `password_hash`, `password_salt`, timestamps.
- **`farmer_profiles` Table / View**: Foreign Key `user_id REFERENCES users(id)`, `full_name`, `email`, `phone_number`, `preferred_language`, `state`, `district`, `mandal`, `village`.
- **`farm_details` Table / View**: Foreign Key `user_id REFERENCES users(id)`, `land_size_acres`, `soil_type`, `water_availability`, `season`, `budget_inr`, `risk_tolerance`, `primary_crops_grown`.
- **Zero-Duplication & Safe Migration**:
  - Implemented automatic column migration in `_init_db()` (`PRAGMA table_info(farmers)`) to add `email`, `phone_number`, `mandal` without breaking existing databases.
  - Implemented SQL Relational Views (`CREATE VIEW IF NOT EXISTS users/farmer_profiles/farm_details`) enabling 3-way SQL `INNER JOIN` queries with zero duplicate data storage.

---

### Task 5 — Testing & Backend Verification
- **Live HTTP Socket Audit (`scripts/test_live_backend.py`)**:
  - Booted the server on port `8089` and tested all 14 REST and static endpoints over live HTTP sockets.
  - Tested 19 distinct scenarios (happy paths, duplicate registrations, bad passwords, negative land sizes, session revocations).
  - **Result**: **19/19 Live Audits Passed (100%)**.
- **Pytest Automated Test Suite**:
  - Added new test modules: `tests/test_farmer_profile.py`, `tests/test_api_endpoints.py`, and `tests/test_database_design.py`.
  - Executed full test suite across all 10 test modules.
  - **Result**: **96/96 Tests Passed in 123s (100% Green)**.

---

## 📁 Files Modified & Created

| File | Status | Description |
| :--- | :---: | :--- |
| `agrisaarthi/models.py` | Modified | Added `FarmerProfile` (11 fields), `FarmerRegistrationRequest`, `FarmerLoginRequest`, `FarmerProfileUpdateRequest`. |
| `agrisaarthi/storage.py` | Modified | Added `email`, `phone_number`, `mandal` columns, automated migrations, multi-identifier login, relational views. |
| `scripts/run_farmer_ui.py` | Modified | Routed all 11 fields through `/api/auth/register`, updated `/api/auth/login` to accept phone/email/username. |
| `tests/test_farmer_profile.py` | Created | 10 unit tests for 11 fields, phone/email validation, salt uniqueness, and multi-identifier login. |
| `tests/test_api_endpoints.py` | Created | 7 contract tests verifying status codes (200, 201, 400, 401) for all 5 core endpoints. |
| `tests/test_database_design.py` | Created | 4 tests verifying `users`, `farmer_profiles`, `farm_details` schemas and 3-way SQL JOINs. |
| `scripts/test_live_backend.py` | Created | Live HTTP socket test auditing 19 endpoint scenarios on port 8089. |
| `docs/BACKEND_MODULE_REPORT.md` | Created | Full Day 2 backend architecture report, ER diagrams, and endpoint specifications. |
| `docs/DAY2_BACKEND_DELIVERABLE_SUMMARY.md` | Created | This executive deliverable document for team review. |

---

## 🧪 How to Verify & Run Locally

### 1. Run All 96 Automated Tests (Pytest)
```cmd
cd C:\Users\chara\Documents\myProjects\AgriSaarthi-AI
.venv\Scripts\pytest.exe
```

### 2. Run the 19 Live HTTP Endpoint Audits
```cmd
.venv\Scripts\python.exe scripts/test_live_backend.py
```

### 3. Start the Live Server
```cmd
.venv\Scripts\python.exe scripts/run_farmer_ui.py
```
Open **`http://127.0.0.1:8080`** in any browser to test live registration, login, and profile editing!

