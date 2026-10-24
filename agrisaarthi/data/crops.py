"""
Indian Agricultural Crop Reference Dataset.
Data synthesized from Indian Council of Agricultural Research (ICAR),
Commission for Agricultural Costs and Prices (CACP MSP reports),
and state agricultural university agronomic recommendations.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
from agrisaarthi.models import Season, SoilType, WaterAvailability, RiskTolerance


@dataclass(frozen=True)
class CropProfile:
    id: str
    name: str
    hindi_name: str
    category: str  # Cereal, Pulse, Oilseed, Commercial, Millet
    seasons: Tuple[Season, ...]
    optimal_soils: Tuple[SoilType, ...]
    tolerated_soils: Tuple[SoilType, ...]
    water_requirement: WaterAvailability  # Low, Moderate, High
    water_mm_range: Tuple[int, int]
    cost_per_acre_inr: float               # CACP/ICAR standard average cultivation cost
    yield_quintals_per_acre: Tuple[float, float]
    expected_price_per_quintal_inr: float # Based on 2024-2025 MSP / avg farmgate
    risk_level: RiskTolerance              # Inherent volatility/vulnerability
    prominent_states: Tuple[str, ...]
    advantages: Tuple[str, ...]
    vulnerabilities: Tuple[str, ...]
    advisory_notes: str


CROP_DATABASE: List[CropProfile] = [
    CropProfile(
        id="paddy",
        name="Paddy / Rice",
        hindi_name="धान (Paddy)",
        category="Cereal",
        seasons=(Season.KHARIF,),
        optimal_soils=(SoilType.CLAYEY, SoilType.ALLUVIAL),
        tolerated_soils=(SoilType.BLACK,),
        water_requirement=WaterAvailability.HIGH,
        water_mm_range=(1000, 1600),
        cost_per_acre_inr=22000.0,
        yield_quintals_per_acre=(18.0, 26.0),
        expected_price_per_quintal_inr=2300.0,
        risk_level=RiskTolerance.LOW,
        prominent_states=("Punjab", "Haryana", "West Bengal", "Uttar Pradesh", "Andhra Pradesh", "Telangana", "Bihar", "Odisha", "Tamil Nadu"),
        advantages=("Guaranteed Government MSP procurement mandis", "High yield potential in irrigated basins", "Liquid grain market"),
        vulnerabilities=("High water table depletion", "Susceptible to sheath blight and stem borer", "Labor-intensive nursery transplanting"),
        advisory_notes="Requires standing water. If borewell water is saline or depleting, consider switching to Direct Seeded Rice (DSR) or pulses."
    ),
    CropProfile(
        id="wheat",
        name="Wheat",
        hindi_name="गेहूँ (Wheat)",
        category="Cereal",
        seasons=(Season.RABI,),
        optimal_soils=(SoilType.ALLUVIAL, SoilType.CLAYEY, SoilType.SANDY_LOAM),
        tolerated_soils=(SoilType.BLACK,),
        water_requirement=WaterAvailability.MODERATE,
        water_mm_range=(350, 500),
        cost_per_acre_inr=18000.0,
        yield_quintals_per_acre=(16.0, 22.0),
        expected_price_per_quintal_inr=2425.0,
        risk_level=RiskTolerance.LOW,
        prominent_states=("Punjab", "Haryana", "Uttar Pradesh", "Madhya Pradesh", "Rajasthan", "Bihar"),
        advantages=("Staple food security with strong MSP procurement", "Low marketing risk", "High straw/fodder commercial value"),
        vulnerabilities=("Sensitive to terminal heat stress in March", "Vulnerable to yellow rust in north-western plains"),
        advisory_notes="Sow between Nov 1 and Nov 20. Ensure timely irrigation at crown root initiation (CRI) stage (~21 days after sowing)."
    ),
    CropProfile(
        id="cotton",
        name="Cotton (Bt Cotton)",
        hindi_name="कपास (Cotton)",
        category="Commercial",
        seasons=(Season.KHARIF,),
        optimal_soils=(SoilType.BLACK, SoilType.ALLUVIAL),
        tolerated_soils=(SoilType.RED, SoilType.SANDY_LOAM),
        water_requirement=WaterAvailability.MODERATE,
        water_mm_range=(600, 850),
        cost_per_acre_inr=26000.0,
        yield_quintals_per_acre=(7.0, 12.0),
        expected_price_per_quintal_inr=7121.0,
        risk_level=RiskTolerance.HIGH,
        prominent_states=("Maharashtra", "Gujarat", "Telangana", "Andhra Pradesh", "Punjab", "Haryana", "Rajasthan", "Karnataka"),
        advantages=("High commercial net return", "Wide textile industry market demand", "Suited for deep black cotton soils"),
        vulnerabilities=("Heavy susceptibility to Pink Bollworm", "Sensitive to waterlogging", "High chemical pesticide input costs"),
        advisory_notes="Install pheromone traps early. Avoid prolonged mono-cropping to mitigate bollworm resistance."
    ),
    CropProfile(
        id="mustard",
        name="Mustard / Rapeseed",
        hindi_name="सरसों (Mustard)",
        category="Oilseed",
        seasons=(Season.RABI,),
        optimal_soils=(SoilType.SANDY_LOAM, SoilType.ALLUVIAL),
        tolerated_soils=(SoilType.RED, SoilType.BLACK),
        water_requirement=WaterAvailability.LOW,
        water_mm_range=(250, 400),
        cost_per_acre_inr=13000.0,
        yield_quintals_per_acre=(6.5, 9.5),
        expected_price_per_quintal_inr=5950.0,
        risk_level=RiskTolerance.LOW,
        prominent_states=("Rajasthan", "Haryana", "Madhya Pradesh", "Uttar Pradesh", "Gujarat", "Punjab"),
        advantages=("Low water consumption (2-3 light irrigations)", "High oil content demand in North India", "Fast maturation"),
        vulnerabilities=("Vulnerable to aphid attacks in humid spells", "Sensitive to late-winter frost (Pala)"),
        advisory_notes="Excellent low-irrigation alternative to wheat in semi-arid zones like Rajasthan and Haryana."
    ),
    CropProfile(
        id="chickpea",
        name="Chickpea / Bengal Gram (Chana)",
        hindi_name="चना (Chickpea)",
        category="Pulse",
        seasons=(Season.RABI,),
        optimal_soils=(SoilType.SANDY_LOAM, SoilType.BLACK, SoilType.ALLUVIAL),
        tolerated_soils=(SoilType.RED,),
        water_requirement=WaterAvailability.LOW,
        water_mm_range=(200, 350),
        cost_per_acre_inr=12500.0,
        yield_quintals_per_acre=(6.0, 9.0),
        expected_price_per_quintal_inr=5650.0,
        risk_level=RiskTolerance.LOW,
        prominent_states=("Madhya Pradesh", "Maharashtra", "Rajasthan", "Karnataka", "Uttar Pradesh", "Andhra Pradesh"),
        advantages=("Fixes atmospheric nitrogen into the soil", "High drought resilience", "Strong domestic dal consumption"),
        vulnerabilities=("Susceptible to Pod Borer (Helicoverpa)", "Intolerant of poorly drained waterlogged soils"),
        advisory_notes="Treat seeds with Rhizobium culture before sowing to maximize biological nitrogen fixation."
    ),
    CropProfile(
        id="bajra",
        name="Pearl Millet (Bajra)",
        hindi_name="बाजरा (Bajra)",
        category="Millet",
        seasons=(Season.KHARIF,),
        optimal_soils=(SoilType.SANDY_LOAM, SoilType.RED),
        tolerated_soils=(SoilType.ALLUVIAL,),
        water_requirement=WaterAvailability.LOW,
        water_mm_range=(250, 400),
        cost_per_acre_inr=9500.0,
        yield_quintals_per_acre=(9.0, 15.0),
        expected_price_per_quintal_inr=2625.0,
        risk_level=RiskTolerance.LOW,
        prominent_states=("Rajasthan", "Maharashtra", "Gujarat", "Haryana", "Uttar Pradesh"),
        advantages=("Outstanding drought & heat tolerance", "Very low input investment threshold", "High nutritional value and growing millet demand"),
        vulnerabilities=("Lower commercial margin compared to cotton", "Ergot and downy mildew during overcast wet spells"),
        advisory_notes="Best climate-resilient choice for water-scarce arid zones and marginal soils."
    ),
    CropProfile(
        id="soybean",
        name="Soybean",
        hindi_name="सोयाबीन (Soybean)",
        category="Oilseed",
        seasons=(Season.KHARIF,),
        optimal_soils=(SoilType.BLACK, SoilType.ALLUVIAL),
        tolerated_soils=(SoilType.CLAYEY,),
        water_requirement=WaterAvailability.MODERATE,
        water_mm_range=(500, 700),
        cost_per_acre_inr=15000.0,
        yield_quintals_per_acre=(7.5, 11.0),
        expected_price_per_quintal_inr=4892.0,
        risk_level=RiskTolerance.MODERATE,
        prominent_states=("Madhya Pradesh", "Maharashtra", "Rajasthan", "Karnataka", "Telangana"),
        advantages=("Short crop cycle (90-100 days)", "Improves soil health for subsequent Rabi crop", "Robust animal feed and edible oil processing demand"),
        vulnerabilities=("Yield drops sharply if dry spell occurs during pod-filling", "Yellow Mosaic Virus transmission via whiteflies"),
        advisory_notes="Ensure broad bed furrow (BBF) planting to manage heavy monsoon drainage."
    ),
    CropProfile(
        id="groundnut",
        name="Groundnut / Peanut",
        hindi_name="मूंगफली (Groundnut)",
        category="Oilseed",
        seasons=(Season.KHARIF, Season.ZAID),
        optimal_soils=(SoilType.SANDY_LOAM, SoilType.RED),
        tolerated_soils=(SoilType.ALLUVIAL,),
        water_requirement=WaterAvailability.MODERATE,
        water_mm_range=(450, 650),
        cost_per_acre_inr=17500.0,
        yield_quintals_per_acre=(8.5, 13.5),
        expected_price_per_quintal_inr=6783.0,
        risk_level=RiskTolerance.MODERATE,
        prominent_states=("Gujarat", "Andhra Pradesh", "Tamil Nadu", "Karnataka", "Rajasthan"),
        advantages=("High remuneration per quintal", "Nutritious green fodder", "Improves soil structure"),
        vulnerabilities=("High initial seed cost", "White grub infestation in root zones", "Clay soil prevents peg penetration"),
        advisory_notes="Avoid heavy clay soils which impede pod formation (pegging) and harvesting."
    ),
    CropProfile(
        id="maize",
        name="Maize / Corn",
        hindi_name="मक्का (Maize)",
        category="Cereal",
        seasons=(Season.KHARIF, Season.RABI),
        optimal_soils=(SoilType.ALLUVIAL, SoilType.RED, SoilType.BLACK),
        tolerated_soils=(SoilType.SANDY_LOAM,),
        water_requirement=WaterAvailability.MODERATE,
        water_mm_range=(500, 750),
        cost_per_acre_inr=16000.0,
        yield_quintals_per_acre=(18.0, 26.0),
        expected_price_per_quintal_inr=2225.0,
        risk_level=RiskTolerance.MODERATE,
        prominent_states=("Karnataka", "Madhya Pradesh", "Bihar", "Maharashtra", "Telangana", "Rajasthan", "Uttar Pradesh"),
        advantages=("High biomass yield", "Constant demand from poultry feed and starch processing industries", "Flexible sowing window"),
        vulnerabilities=("Fall Armyworm (FAW) can destroy standing crops if untreated", "Sensitive to standing water during germination"),
        advisory_notes="Monitor early vegetative whorls for Fall Armyworm egg masses and apply biocontrol measures."
    ),
    CropProfile(
        id="moong",
        name="Green Gram / Moong",
        hindi_name="मूंग (Moong)",
        category="Pulse",
        seasons=(Season.ZAID, Season.KHARIF),
        optimal_soils=(SoilType.SANDY_LOAM, SoilType.ALLUVIAL, SoilType.BLACK),
        tolerated_soils=(SoilType.RED,),
        water_requirement=WaterAvailability.LOW,
        water_mm_range=(250, 350),
        cost_per_acre_inr=9000.0,
        yield_quintals_per_acre=(4.5, 6.5),
        expected_price_per_quintal_inr=8682.0,
        risk_level=RiskTolerance.LOW,
        prominent_states=("Rajasthan", "Madhya Pradesh", "Maharashtra", "Gujarat", "Uttar Pradesh", "Bihar", "Punjab"),
        advantages=("Ultra-short duration (60-70 days)", "Exceptional pulse market value", "Ideal summer catch crop utilizing residual soil moisture"),
        vulnerabilities=("Pod shattering if harvesting delayed", "Susceptible to yellow mosaic virus"),
        advisory_notes="Excellent catch-crop to earn income and add green manure between Rabi wheat harvest and Kharif planting."
    ),
    CropProfile(
        id="sugarcane",
        name="Sugarcane",
        hindi_name="गन्ना (Sugarcane)",
        category="Commercial",
        seasons=(Season.YEAR_ROUND,),
        optimal_soils=(SoilType.ALLUVIAL, SoilType.BLACK, SoilType.CLAYEY),
        tolerated_soils=(SoilType.RED,),
        water_requirement=WaterAvailability.HIGH,
        water_mm_range=(1500, 2500),
        cost_per_acre_inr=36000.0,
        yield_quintals_per_acre=(300.0, 420.0),
        expected_price_per_quintal_inr=340.0,
        risk_level=RiskTolerance.MODERATE,
        prominent_states=("Uttar Pradesh", "Maharashtra", "Karnataka", "Tamil Nadu", "Bihar", "Gujarat"),
        advantages=("Statutory Fair & Remunerative Price (FRP) support", "High gross revenue potential", "Perennial ratoon harvest benefits"),
        vulnerabilities=("Exceedingly high water consumption", "10-14 month cycle blocks agricultural land", "Delayed mill payment risks"),
        advisory_notes="Strictly requires perennial irrigation. Consider drip irrigation systems to save up to 40% water."
    )
]
