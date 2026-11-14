"""
Data schemas and message models for AgriSaarthi AI.
Built on uagents.Model (pydantic.v1 compatible) to support Fetch.ai agent communication.
"""

from enum import Enum
import re
from typing import List, Optional, Tuple, Dict, Any
from pydantic.v1 import Field, validator
from uagents import Model


class Season(str, Enum):
    KHARIF = "kharif"      # Monsoon / Summer (June - October)
    RABI = "rabi"          # Winter (October - March/April)
    ZAID = "zaid"          # Summer short crop (March - June)
    YEAR_ROUND = "year_round"


class SoilType(str, Enum):
    ALLUVIAL = "alluvial"       # Indo-Gangetic plains, delta regions
    BLACK = "black"             # Regur, Deccan plateau (Cotton, Soybean)
    RED = "red"                 # Iron-rich, Peninsular India (Pulses, Millets, Groundnut)
    LATERITE = "laterite"       # Leached, Coastal/Hilly (Cash crops, Plantation)
    SANDY_LOAM = "sandy_loam"   # Well-drained, semi-arid (Millets, Mustard, Pulses)
    CLAYEY = "clayey"           # Moisture retentive (Rice, Wheat)


class WaterAvailability(str, Enum):
    LOW = "low"                 # Rainfed / Drought prone (<500mm / no borewell)
    MODERATE = "moderate"       # Seasonal canal / Tube-well / Semi-irrigated (500-1000mm)
    HIGH = "high"               # Perennial canal / Assured heavy irrigation (>1000mm)


class RiskTolerance(str, Enum):
    LOW = "low"                 # MSP-backed, food security, resilient crops
    MODERATE = "moderate"       # Balanced portfolio
    HIGH = "high"               # High-investment, high-return cash crops


class CropGrowthStage(str, Enum):
    GERMINATION = "germination"          # Seedling / Germination (మొలక / నాటు దశ)
    VEGETATIVE = "vegetative"            # Vegetative growth (శాకీయ ఎదుగుదల దశ)
    FLOWERING = "flowering"              # Blooming / Flowering (పూత దశ)
    GRAIN_FILLING = "grain_filling"      # Grain filling / Pod formation (గింజ / కాయ దశ)
    MATURITY = "maturity"                # Physiological maturity / Harvest (కోత దశ)


class FarmerProfile(Model):
    """
    Standard Farmer Profile Data Structure (Task 2 & Day 2).
    Represents the complete identity, administrative location, and agronomic profile of a farmer.
    Sensitive credentials (passwords, salts, hashes) are NEVER stored or returned in this model.
    """
    farmer_id: Optional[int] = Field(default=None, description="Unique account ID")
    full_name: str = Field(..., min_length=2, max_length=120, description="Farmer's full name")
    email: Optional[str] = Field(default="", description="Email address if provided")
    phone_number: Optional[str] = Field(default="", description="10-digit Indian mobile number if provided")
    district: str = Field(default="", description="District name (e.g. Guntur, Warangal, Ludhiana)")
    mandal: Optional[str] = Field(default="", description="Mandal or sub-district tehsil")
    village: str = Field(default="", description="Village or Gram Panchayat")
    land_size_acres: Optional[float] = Field(default=None, ge=0.0, le=5000.0, description="Cultivable holding in acres")
    soil_type: Optional[SoilType] = Field(default=None, description="Dominant soil classification of the plot")
    water_availability: Optional[WaterAvailability] = Field(default=None, description="Farm water availability tier")
    preferred_language: str = Field(default="te", description="Preferred language code ('te' for Telugu, 'en' for English)")
    state: Optional[str] = Field(default="", description="State name (e.g. Andhra Pradesh, Telangana)")
    season: Optional[Season] = Field(default=None, description="Target planting season")
    sowing_date: Optional[str] = Field(default="", description="Date of sowing or transplanting (YYYY-MM-DD)")
    crop_growth_stage: Optional[CropGrowthStage] = Field(default=None, description="Current growth stage of primary crop")
    budget_inr: Optional[float] = Field(default=None, ge=0.0, description="Total planned investment budget in INR")
    risk_tolerance: Optional[RiskTolerance] = Field(default=RiskTolerance.MODERATE, description="Farmer risk preference")
    primary_crops_grown: Optional[str] = Field(default="", description="Comma-separated crops currently cultivated")
    profile_completed: bool = Field(default=False, description="Flag indicating if farm profile is filled")
    created_at: Optional[str] = Field(default=None, description="Timestamp when account was created")
    updated_at: Optional[str] = Field(default=None, description="Timestamp of last profile update")

    @validator("preferred_language")
    def validate_lang(cls, v: str) -> str:
        code = (v or "te").strip().lower()
        return code if code in ("te", "en") else "te"

    @validator("sowing_date")
    def validate_sowing_date(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        cleaned = v.strip()
        if cleaned and not re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
            raise ValueError("Sowing date must be in YYYY-MM-DD format (e.g. 2026-10-15).")
        return cleaned

    @validator("phone_number")
    def validate_phone(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        digits = re.sub(r"[^\d]", "", v)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if digits and len(digits) != 10:
            raise ValueError("Phone number must be a valid 10-digit mobile number if provided.")
        return digits

    @validator("email")
    def validate_email(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        cleaned = v.strip().lower()
        if cleaned and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
            raise ValueError("Invalid email address format.")
        return cleaned


class FarmerRegistrationRequest(Model):
    """
    Registration request payload for new farmers.
    Incoming plaintext password is immediately hashed via PBKDF2-HMAC-SHA256 with a unique salt
    before any persistent database write.
    """
    full_name: str = Field(..., min_length=2, max_length=120, description="Farmer full name")
    password: str = Field(..., min_length=6, description="Raw password to be hashed securely on receipt")
    phone_number: Optional[str] = Field(default="", description="10-digit mobile number")
    email: Optional[str] = Field(default="", description="Optional email address")
    identifier: Optional[str] = Field(default="", description="Mobile number, email, or unique username")
    district: Optional[str] = Field(default="", description="District name")
    mandal: Optional[str] = Field(default="", description="Mandal name")
    village: Optional[str] = Field(default="", description="Village name")
    land_size_acres: Optional[float] = Field(default=None, ge=0.0, le=5000.0, description="Land size in acres")
    soil_type: Optional[SoilType] = Field(default=None, description="Dominant soil classification")
    water_availability: Optional[WaterAvailability] = Field(default=None, description="Water source availability tier")
    preferred_language: str = Field(default="te", description="Preferred language code ('te' or 'en')")
    sowing_date: Optional[str] = Field(default="", description="Date of sowing or transplanting (YYYY-MM-DD)")
    crop_growth_stage: Optional[CropGrowthStage] = Field(default=None, description="Current growth stage of primary crop")

    @validator("password")
    def validate_pw(cls, v: str) -> str:
        if not v or len(v.strip()) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v

    @validator("sowing_date")
    def validate_reg_sowing_date(cls, v: Optional[str]) -> str:
        if not v:
            return ""
        cleaned = v.strip()
        if cleaned and not re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
            raise ValueError("Sowing date must be in YYYY-MM-DD format (e.g. 2026-10-15).")
        return cleaned


class FarmerLoginRequest(Model):
    """Login credentials payload."""
    identifier: str = Field(..., min_length=3, description="Mobile number, username, or email")
    password: str = Field(..., min_length=1, description="Password to verify against PBKDF2 hash")


class FarmerProfileUpdateRequest(Model):
    """Profile update payload for PUT /api/farmer/profile."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[str] = None
    phone_number: Optional[str] = None
    district: Optional[str] = None
    mandal: Optional[str] = None
    village: Optional[str] = None
    land_size_acres: Optional[float] = Field(default=None, ge=0.0, le=5000.0)
    soil_type: Optional[SoilType] = None
    water_availability: Optional[WaterAvailability] = None
    preferred_language: Optional[str] = None
    state: Optional[str] = None
    season: Optional[Season] = None
    sowing_date: Optional[str] = None
    crop_growth_stage: Optional[CropGrowthStage] = None
    budget_inr: Optional[float] = Field(default=None, ge=0.0)
    risk_tolerance: Optional[RiskTolerance] = None
    primary_crops_grown: Optional[str] = None

    @validator("sowing_date")
    def validate_upd_sowing_date(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return v
        cleaned = v.strip()
        if cleaned and not re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
            raise ValueError("Sowing date must be in YYYY-MM-DD format (e.g. 2026-10-15).")
        return cleaned


class FarmerProfileRequest(Model):
    """Input query model sent by a farmer or user-facing agent to AgriSaarthi."""
    farmer_id: Optional[str] = "farmer_default"
    state: str = Field(..., description="Indian State (e.g., Punjab, Maharashtra, Rajasthan, Karnataka)")
    district: Optional[str] = Field(default="", description="District or region name")
    land_size_acres: float = Field(..., gt=0.0, le=5000.0, description="Farm holding size in acres")
    soil_type: SoilType = Field(..., description="Dominant soil classification of the plot")
    water_availability: WaterAvailability = Field(..., description="Farm water availability tier")
    season: Season = Field(..., description="Target planting season")
    budget_inr: float = Field(..., ge=0.0, description="Total planned investment budget in INR for the season")
    risk_tolerance: RiskTolerance = Field(default=RiskTolerance.MODERATE, description="Farmer risk preference")

    @validator("state")
    def validate_state(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("State cannot be empty.")
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("State name is too short.")
        return cleaned.title()

    @validator("district")
    def validate_district(cls, v: Optional[str]) -> str:
        if v is None:
            return ""
        return v.strip().title()


class CropRecommendationItem(Model):
    """Detailed evaluation score and agronomic insights for a recommended crop."""
    crop_name: str
    hindi_name: str
    category: str  # Cereal, Pulse, Oilseed, Commercial, Millet
    suitability_score: float = Field(..., ge=0.0, le=100.0, description="Overall suitability out of 100")
    season_match: bool
    soil_compatibility: str  # Optimal, Compatible, Suboptimal
    water_compatibility: str # Optimal, Stressed, Over-irrigated
    estimated_cost_per_acre_inr: float
    total_estimated_cost_inr: float
    budget_feasibility: str  # Within Budget, Buffer Required, Infeasible
    expected_yield_range_quintals_per_acre: Tuple[float, float]
    estimated_net_profit_per_acre_inr: float
    key_strengths: List[str]
    risk_factors: List[str]


class RecommendationResponse(Model):
    """Structured response returned by AgriSaarthi decision agent."""
    farmer_id: str
    workflow_status: str  # SUCCESS, REJECTED_INPUT, NO_VIABLE_CROPS
    warnings: List[str]
    budget_summary: Dict[str, Any]
    primary_recommendations: List[CropRecommendationItem]
    alternative_recommendations: List[CropRecommendationItem]
    step_by_step_reasoning: List[str]
    limitations_and_advisory: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize response to python dictionary."""
        return self.dict()
