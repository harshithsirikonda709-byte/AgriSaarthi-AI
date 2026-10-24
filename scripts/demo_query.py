"""
AgriSaarthi AI - Interactive Demo / Verification Script.
Simulates farmer queries across Indian agro-climatic zones and prints
the multi-step decision pipeline outputs.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agrisaarthi.models import (
    FarmerProfileRequest,
    Season,
    SoilType,
    WaterAvailability,
    RiskTolerance,
)
from agrisaarthi.engine import AgriSaarthiEngine


def run_scenario(title: str, request: FarmerProfileRequest):
    print("=" * 70)
    print(f"🌾 SCENARIO: {title}")
    print("=" * 70)
    print(f"📍 Location : {request.state} ({request.district or 'General'})")
    print(f"📐 Land Size: {request.land_size_acres} Acres")
    print(f"🌱 Season   : {request.season.value.upper()} | Soil: {request.soil_type.value.title()}")
    print(f"💧 Water    : {request.water_availability.value.title()} | Risk: {request.risk_tolerance.value.title()}")
    print(f"💰 Budget   : ₹{request.budget_inr:,.0f} (₹{request.budget_inr/request.land_size_acres:,.0f}/acre)")
    print("-" * 70)

    response = AgriSaarthiEngine.execute(request)

    print(f"Status: {response.workflow_status}")
    if response.warnings:
        print("⚠️  Warnings:")
        for w in response.warnings:
            print(f"   • {w}")

    print("\n🏆 Top Primary Recommendations:")
    for idx, crop in enumerate(response.primary_recommendations, 1):
        print(f"  {idx}. {crop.crop_name} [{crop.hindi_name}] - Suitability: {crop.suitability_score}/100")
        print(f"     • Category      : {crop.category}")
        print(f"     • Est. Cost/Acre: ₹{crop.estimated_cost_per_acre_inr:,.0f} (Total: ₹{crop.total_estimated_cost_inr:,.0f})")
        print(f"     • Est. Net Profit: ₹{crop.estimated_net_profit_per_acre_inr:,.0f}/acre")
        print(f"     • Water Fit     : {crop.water_compatibility} | Soil Fit: {crop.soil_compatibility}")
        print(f"     • Budget Status : {crop.budget_feasibility}")
        print(f"     • Top Advantage : {crop.key_strengths[0] if crop.key_strengths else 'N/A'}")
        print(f"     • Key Risk      : {crop.risk_factors[0] if crop.risk_factors else 'N/A'}")

    if response.alternative_recommendations:
        print("\n🔄 Alternative Diversification Options:")
        for alt in response.alternative_recommendations:
            print(f"  • {alt.crop_name} (Score: {alt.suitability_score}/100, Est. Profit: ₹{alt.estimated_net_profit_per_acre_inr:,.0f}/ac)")

    print("\n🧠 Multi-Step Decision Reasoning:")
    for step in response.step_by_step_reasoning:
        print(f"  ✔ {step}")

    print("\n⚠️  Agronomic Advisories & Limitations:")
    for adv in response.limitations_and_advisory[:3]:
        print(f"  ℹ {adv}")
    print("\n")


if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("        AGRISAARTHI AI - AGRICULTURAL DECISION ENGINE DEMO")
    print("#" * 70 + "\n")

    # Scenario 1: Punjab Rabi Season
    s1 = FarmerProfileRequest(
        farmer_id="farmer_pb_01",
        state="Punjab",
        district="Sangrur",
        land_size_acres=5.0,
        soil_type=SoilType.ALLUVIAL,
        water_availability=WaterAvailability.MODERATE,
        season=Season.RABI,
        budget_inr=110000.0,
        risk_tolerance=RiskTolerance.LOW,
    )
    run_scenario("Punjab Rabi Sowing (Low Risk, Alluvial Soil)", s1)

    # Scenario 2: Rajasthan Arid Kharif Season
    s2 = FarmerProfileRequest(
        farmer_id="farmer_rj_02",
        state="Rajasthan",
        district="Jodhpur",
        land_size_acres=6.0,
        soil_type=SoilType.SANDY_LOAM,
        water_availability=WaterAvailability.LOW,
        season=Season.KHARIF,
        budget_inr=65000.0,
        risk_tolerance=RiskTolerance.LOW,
    )
    run_scenario("Rajasthan Arid Rainfed Kharif (Water-Scarce, Sandy Loam)", s2)

    # Scenario 3: Maharashtra Black Soil Commercial Kharif
    s3 = FarmerProfileRequest(
        farmer_id="farmer_mh_03",
        state="Maharashtra",
        district="Amravati",
        land_size_acres=4.0,
        soil_type=SoilType.BLACK,
        water_availability=WaterAvailability.MODERATE,
        season=Season.KHARIF,
        budget_inr=120000.0,
        risk_tolerance=RiskTolerance.HIGH,
    )
    run_scenario("Vidarbha Maharashtra Kharif (Commercial Cash Crop, Black Soil)", s3)
