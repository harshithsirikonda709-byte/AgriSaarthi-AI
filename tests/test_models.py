"""
Tests for AgriSaarthi input validation and Pydantic models.
"""

import pytest
from pydantic.v1.error_wrappers import ValidationError
from agrisaarthi.models import (
    FarmerProfileRequest,
    Season,
    SoilType,
    WaterAvailability,
    RiskTolerance,
)


def test_valid_farmer_profile_request():
    req = FarmerProfileRequest(
        farmer_id="farmer_123",
        state="punjab",
        district="ludhiana",
        land_size_acres=5.0,
        soil_type=SoilType.ALLUVIAL,
        water_availability=WaterAvailability.MODERATE,
        season=Season.RABI,
        budget_inr=100000.0,
        risk_tolerance=RiskTolerance.LOW,
    )
    assert req.state == "Punjab"  # Cleaned / title-cased
    assert req.district == "Ludhiana"
    assert req.land_size_acres == 5.0
    assert req.season == Season.RABI
    assert req.budget_inr == 100000.0


def test_invalid_negative_land_size():
    with pytest.raises(ValidationError):
        FarmerProfileRequest(
            state="Haryana",
            land_size_acres=-2.0,  # Negative land size must fail
            soil_type=SoilType.ALLUVIAL,
            water_availability=WaterAvailability.HIGH,
            season=Season.KHARIF,
            budget_inr=50000.0,
        )


def test_invalid_zero_land_size():
    with pytest.raises(ValidationError):
        FarmerProfileRequest(
            state="Haryana",
            land_size_acres=0.0,  # Zero land size must fail
            soil_type=SoilType.ALLUVIAL,
            water_availability=WaterAvailability.HIGH,
            season=Season.KHARIF,
            budget_inr=50000.0,
        )


def test_invalid_negative_budget():
    with pytest.raises(ValidationError):
        FarmerProfileRequest(
            state="Rajasthan",
            land_size_acres=4.0,
            soil_type=SoilType.SANDY_LOAM,
            water_availability=WaterAvailability.LOW,
            season=Season.RABI,
            budget_inr=-1000.0,  # Negative budget must fail
        )


def test_empty_state_validation():
    with pytest.raises(ValidationError):
        FarmerProfileRequest(
            state="   ",  # Blank state must fail
            land_size_acres=3.0,
            soil_type=SoilType.BLACK,
            water_availability=WaterAvailability.MODERATE,
            season=Season.KHARIF,
            budget_inr=40000.0,
        )


def test_invalid_enum_values():
    with pytest.raises(ValidationError):
        FarmerProfileRequest(
            state="Gujarat",
            land_size_acres=3.0,
            soil_type="volcanic_ash",  # Unsupported soil type
            water_availability=WaterAvailability.LOW,
            season=Season.KHARIF,
            budget_inr=30000.0,
        )
