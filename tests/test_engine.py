"""
Tests for AgriSaarthi multi-step crop recommendation engine.
"""

from agrisaarthi.models import (
    FarmerProfileRequest,
    Season,
    SoilType,
    WaterAvailability,
    RiskTolerance,
)
from agrisaarthi.engine import AgriSaarthiEngine


def test_punjab_rabi_wheat_recommendation():
    """Punjab farmer in Rabi season with Alluvial soil, moderate water, and adequate budget."""
    request = FarmerProfileRequest(
        farmer_id="punjab_farmer_1",
        state="Punjab",
        district="Ludhiana",
        land_size_acres=5.0,
        soil_type=SoilType.ALLUVIAL,
        water_availability=WaterAvailability.MODERATE,
        season=Season.RABI,
        budget_inr=110000.0,  # ~22,000/acre
        risk_tolerance=RiskTolerance.LOW,
    )

    response = AgriSaarthiEngine.execute(request)

    assert response.workflow_status == "SUCCESS"
    assert len(response.primary_recommendations) >= 1

    primary_crop_names = [c.crop_name for c in response.primary_recommendations]
    # Wheat or Mustard should be the top recommendation
    assert "Wheat" in primary_crop_names or "Mustard / Rapeseed" in primary_crop_names

    top_crop = response.primary_recommendations[0]
    assert top_crop.suitability_score > 70.0
    assert top_crop.budget_feasibility == "Within Budget"
    assert len(top_crop.key_strengths) > 0
    assert len(top_crop.risk_factors) > 0

    # Verify multi-step reasoning is populated
    assert len(response.step_by_step_reasoning) >= 4
    assert any("Step 1 Validated" in r for r in response.step_by_step_reasoning)
    assert any("Step 2 Evaluated" in r for r in response.step_by_step_reasoning)
    assert any("Step 3 Economic Analysis" in r for r in response.step_by_step_reasoning)
    assert any("Step 4 Synthesized" in r for r in response.step_by_step_reasoning)

    # Verify limitations and advisory are included
    assert len(response.limitations_and_advisory) >= 3


def test_rajasthan_arid_low_water_recommendation():
    """Rajasthan farmer with sandy loam soil, low water availability in Kharif."""
    request = FarmerProfileRequest(
        farmer_id="rajasthan_farmer_2",
        state="Rajasthan",
        district="Barmer",
        land_size_acres=6.0,
        soil_type=SoilType.SANDY_LOAM,
        water_availability=WaterAvailability.LOW,
        season=Season.KHARIF,
        budget_inr=65000.0,
        risk_tolerance=RiskTolerance.LOW,
    )

    response = AgriSaarthiEngine.execute(request)

    assert response.workflow_status == "SUCCESS"
    primary_crops = [c.crop_name for c in response.primary_recommendations]

    # Bajra (Pearl Millet) is tailor-made for Rajasthan low water sandy loam
    assert "Pearl Millet (Bajra)" in primary_crops

    # Sugarcane or Rice should NOT be in primary recommendations due to severe water deficit
    assert "Sugarcane" not in primary_crops
    assert "Paddy / Rice" not in primary_crops


def test_maharashtra_black_soil_cotton_soybean():
    """Maharashtra farmer with black soil and Kharif season."""
    request = FarmerProfileRequest(
        farmer_id="vidarbha_farmer_3",
        state="Maharashtra",
        district="Nagpur",
        land_size_acres=4.0,
        soil_type=SoilType.BLACK,
        water_availability=WaterAvailability.MODERATE,
        season=Season.KHARIF,
        budget_inr=105000.0,
        risk_tolerance=RiskTolerance.MODERATE,
    )

    response = AgriSaarthiEngine.execute(request)

    assert response.workflow_status == "SUCCESS"
    rec_names = [c.crop_name for c in response.primary_recommendations + response.alternative_recommendations]
    assert any("Soybean" in name or "Cotton" in name for name in rec_names)


def test_budget_constraint_warning():
    """Farmer with very tight budget gets low-budget warning."""
    request = FarmerProfileRequest(
        farmer_id="tight_budget_farmer",
        state="Uttar Pradesh",
        district="Varanasi",
        land_size_acres=10.0,
        soil_type=SoilType.ALLUVIAL,
        water_availability=WaterAvailability.LOW,
        season=Season.RABI,
        budget_inr=25000.0,  # Only 2,500/acre!
    )

    response = AgriSaarthiEngine.execute(request)

    assert response.workflow_status == "SUCCESS"
    assert any("Extremely low budget" in w for w in response.warnings)
    assert response.budget_summary["status"] == "CONSTRAINED"


def test_zaid_season_short_duration_crops():
    """Zaid / Summer season should recommend short pulses like Moong or Groundnut."""
    request = FarmerProfileRequest(
        farmer_id="zaid_grower",
        state="Madhya Pradesh",
        district="Indore",
        land_size_acres=3.0,
        soil_type=SoilType.SANDY_LOAM,
        water_availability=WaterAvailability.LOW,
        season=Season.ZAID,
        budget_inr=35000.0,
    )

    response = AgriSaarthiEngine.execute(request)

    assert response.workflow_status == "SUCCESS"
    all_recs = [c.crop_name for c in response.primary_recommendations + response.alternative_recommendations]
    assert "Green Gram / Moong" in all_recs
