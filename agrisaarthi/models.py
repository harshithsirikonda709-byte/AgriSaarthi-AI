"""
Data schemas and message models for AgriSaarthi AI.
Built on uagents.Model (pydantic.v1 compatible) to support Fetch.ai agent communication.
"""

from enum import Enum
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
