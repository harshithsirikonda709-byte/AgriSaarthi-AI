"""
AgriSaarthi Multi-Step Agricultural Recommendation Engine.
Executes four disciplined steps:
  Step 1: Input Validation and Agronomic Sanity Checks
  Step 2: Crop Suitability Evaluation (Soil, Water, Season, Regional affinity)
  Step 3: Financial & Economic Candidate Comparison (Budget per acre, Yield, Net Profit)
  Step 4: Recommendation Synthesis with Explicit Reasoning and Advisories
"""

from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any
from agrisaarthi.models import (
    FarmerProfileRequest,
    RecommendationResponse,
    CropRecommendationItem,
    Season,
    SoilType,
    WaterAvailability,
    RiskTolerance,
)
from agrisaarthi.data.crops import CROP_DATABASE, CropProfile


class AgriSaarthiEngine:
    """Core recommendation pipeline."""

    @classmethod
    def execute(cls, request: FarmerProfileRequest) -> RecommendationResponse:
        """Run the complete 4-step decision workflow."""
        warnings: List[str] = []
        reasoning: List[str] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 1: Input Validation & Agronomic Sanity Checks
        validation_ok, warnings = cls._step1_validate_inputs(request)
        if not validation_ok:
            return RecommendationResponse(
                farmer_id=request.farmer_id or "unknown",
                workflow_status="REJECTED_INPUT",
                warnings=warnings,
                budget_summary={"status": "INVALID_INPUT"},
                primary_recommendations=[],
                alternative_recommendations=[],
                step_by_step_reasoning=[
                    "Step 1 Failed: Profile validation rejected due to agronomic or data inconsistency."
                ],
                limitations_and_advisory=["Please check input parameters and submit valid farm holding data."],
                timestamp=now_iso,
            )

        budget_per_acre = request.budget_inr / request.land_size_acres
        budget_summary = {
            "total_budget_inr": round(request.budget_inr, 2),
            "land_size_acres": round(request.land_size_acres, 2),
            "budget_per_acre_inr": round(budget_per_acre, 2),
            "status": "HEALTHY" if budget_per_acre >= 12000 else "CONSTRAINED",
        }

        reasoning.append(
            f"Step 1 Validated: Farm size {request.land_size_acres:.1f} acres in {request.state} "
            f"({request.district or 'district unspecified'}), season: {request.season.value.upper()}, "
            f"soil: {request.soil_type.value}, water: {request.water_availability.value}, "
            f"budget: ₹{request.budget_inr:,.0f} (₹{budget_per_acre:,.0f}/acre)."
        )

        # Step 2: Crop Suitability Evaluation
        scored_candidates = cls._step2_evaluate_suitability(request)
        reasoning.append(
            f"Step 2 Evaluated: Assessed {len(CROP_DATABASE)} reference crops against local agro-climate. "
            f"{len(scored_candidates)} candidates matched seasonal criteria."
        )

        if not scored_candidates:
            return RecommendationResponse(
                farmer_id=request.farmer_id or "farmer_default",
                workflow_status="NO_VIABLE_CROPS",
                warnings=warnings + ["No standard crops in the reference catalog match this exact combination."],
                budget_summary=budget_summary,
                primary_recommendations=[],
                alternative_recommendations=[],
                step_by_step_reasoning=reasoning,
                limitations_and_advisory=[
                    "Consult your local Krishi Vigyan Kendra (KVK) for specialized regional crops."
                ],
                timestamp=now_iso,
            )

        # Step 3: Candidate Comparison & Economic Feasibility
        ranked_items = cls._step3_compare_candidates(request, scored_candidates)
        reasoning.append(
            f"Step 3 Economic Analysis: Ranked candidates based on combined agronomic fit, "
            f"budget headroom, and projected net profitability."
        )

        # Step 4: Decision Synthesis, Primary vs Alternative Segregation & Advisories
        primary, alternatives, limitations = cls._step4_synthesize_decision(request, ranked_items)
        reasoning.append(
            f"Step 4 Synthesized: Selected {len(primary)} primary recommendation(s) "
            f"and {len(alternatives)} diversified/hedging alternative(s)."
        )

        return RecommendationResponse(
            farmer_id=request.farmer_id or "farmer_default",
            workflow_status="SUCCESS",
            warnings=warnings,
            budget_summary=budget_summary,
            primary_recommendations=primary,
            alternative_recommendations=alternatives,
            step_by_step_reasoning=reasoning,
            limitations_and_advisory=limitations,
            timestamp=now_iso,
        )

    # -------------------------------------------------------------------------
    # Step 1: Validation
    # -------------------------------------------------------------------------
    @classmethod
    def _step1_validate_inputs(cls, req: FarmerProfileRequest) -> Tuple[bool, List[str]]:
        warnings: List[str] = []

        if req.land_size_acres <= 0.0:
            return False, ["Land size must be strictly positive (> 0.0 acres)."]

        budget_per_acre = req.budget_inr / req.land_size_acres
        if budget_per_acre < 3000.0:
            warnings.append(
                f"Extremely low budget detected (₹{budget_per_acre:.0f}/acre). "
                "Minimum baseline cultivation in India generally requires at least ₹8,000-₹10,000/acre."
            )

        # Check for difficult agronomic combos
        if req.water_availability == WaterAvailability.LOW and req.soil_type == SoilType.CLAYEY:
            warnings.append(
                "Heavy clay soil under low/rainfed water conditions is prone to surface crusting and peg penetration issues."
            )

        return True, warnings

    # -------------------------------------------------------------------------
    # Step 2: Suitability Evaluation
    # -------------------------------------------------------------------------
    @classmethod
    def _step2_evaluate_suitability(
        cls, req: FarmerProfileRequest
    ) -> List[Tuple[CropProfile, float, str, str]]:
        """
        Filters by season and scores agronomic compatibility.
        Returns list of (CropProfile, agronomic_score, soil_status, water_status).
        """
        results = []

        for crop in CROP_DATABASE:
            # Season filter
            season_match = (req.season in crop.seasons) or (Season.YEAR_ROUND in crop.seasons)
            if not season_match:
                continue

            # Soil compatibility
            if req.soil_type in crop.optimal_soils:
                soil_score = 100.0
                soil_status = "Optimal"
            elif req.soil_type in crop.tolerated_soils:
                soil_score = 70.0
                soil_status = "Compatible"
            else:
                soil_score = 30.0
                soil_status = "Suboptimal"

            # Water compatibility
            water_score, water_status = cls._evaluate_water_compatibility(
                req.water_availability, crop.water_requirement
            )

            # Regional suitability bonus
            regional_bonus = 0.0
            if any(req.state.lower() in st.lower() for st in crop.prominent_states):
                regional_bonus = 10.0

            # Risk tolerance alignment
            risk_bonus = 0.0
            if req.risk_tolerance == crop.risk_level:
                risk_bonus = 5.0
            elif req.risk_tolerance == RiskTolerance.LOW and crop.risk_level == RiskTolerance.HIGH:
                risk_bonus = -15.0

            # Base agronomic suitability score (0 to 100)
            agronomic_score = (soil_score * 0.45) + (water_score * 0.45) + regional_bonus + risk_bonus
            agronomic_score = max(0.0, min(100.0, agronomic_score))

            results.append((crop, agronomic_score, soil_status, water_status))

        return results

    @classmethod
    def _evaluate_water_compatibility(
        cls, available: WaterAvailability, required: WaterAvailability
    ) -> Tuple[float, str]:
        if available == required:
            return 100.0, "Optimal"
        if available == WaterAvailability.HIGH:
            # High water can support moderate or low crops, but low-water crops (like bajra/mustard)
            # may suffer if waterlogged.
            if required == WaterAvailability.MODERATE:
                return 85.0, "Sufficient"
            if required == WaterAvailability.LOW:
                return 65.0, "High Water Risk for Dryland Crop"
        if available == WaterAvailability.MODERATE:
            if required == WaterAvailability.LOW:
                return 90.0, "Safe Buffer"
            if required == WaterAvailability.HIGH:
                return 50.0, "Irrigation Deficit Risk"
        if available == WaterAvailability.LOW:
            if required == WaterAvailability.MODERATE:
                return 40.0, "Stressed (Requires Rain Support)"
            if required == WaterAvailability.HIGH:
                return 10.0, "Severe Water Inadequacy"
        return 50.0, "Moderate"

    # -------------------------------------------------------------------------
    # Step 3: Candidate Comparison & Economic Feasibility
    # -------------------------------------------------------------------------
    @classmethod
    def _step3_compare_candidates(
        cls,
        req: FarmerProfileRequest,
        candidates: List[Tuple[CropProfile, float, str, str]],
    ) -> List[Tuple[CropProfile, float, CropRecommendationItem]]:
        """
        Computes economic metrics and builds CropRecommendationItem for each candidate.
        Returns sorted list of (crop, overall_score, item).
        """
        evaluated_candidates = []
        budget_per_acre = req.budget_inr / req.land_size_acres

        for crop, agro_score, soil_status, water_status in candidates:
            cost_per_acre = crop.cost_per_acre_inr
            total_cost = cost_per_acre * req.land_size_acres

            # Budget feasibility
            if total_cost <= req.budget_inr:
                budget_status = "Within Budget"
                budget_score = 100.0
            elif total_cost <= (req.budget_inr * 1.15):
                budget_status = "Buffer Required"
                budget_score = 70.0
            else:
                budget_status = "Exceeds Budget"
                # Penalize proportional to overrun
                overrun_ratio = total_cost / max(req.budget_inr, 1.0)
                budget_score = max(10.0, 100.0 - (overrun_ratio - 1.0) * 80.0)

            # Revenue & Profit Projections
            avg_yield = (crop.yield_quintals_per_acre[0] + crop.yield_quintals_per_acre[1]) / 2.0
            est_gross_revenue = avg_yield * crop.expected_price_per_quintal_inr
            est_net_profit = est_gross_revenue - cost_per_acre

            # Combined weighted score:
            # 60% agronomic suitability, 40% financial viability
            overall_score = (agro_score * 0.60) + (budget_score * 0.40)
            overall_score = round(max(0.0, min(100.0, overall_score)), 1)

            # Build strengths
            strengths = list(crop.advantages)
            if budget_status == "Within Budget":
                surplus = (budget_per_acre - cost_per_acre)
                if surplus > 0:
                    strengths.append(f"Provides a working capital safety margin of ₹{surplus:,.0f}/acre")

            # Build risks
            risks = list(crop.vulnerabilities)
            if budget_status != "Within Budget":
                risks.insert(0, f"Requires ₹{cost_per_acre - budget_per_acre:,.0f}/acre more than allocated budget")
            if water_status in ["Irrigation Deficit Risk", "Severe Water Inadequacy"]:
                risks.insert(0, f"High risk: Farm water availability is '{req.water_availability.value}', crop requires '{crop.water_requirement.value}'")

            item = CropRecommendationItem(
                crop_name=crop.name,
                hindi_name=crop.hindi_name,
                category=crop.category,
                suitability_score=overall_score,
                season_match=True,
                soil_compatibility=soil_status,
                water_compatibility=water_status,
                estimated_cost_per_acre_inr=cost_per_acre,
                total_estimated_cost_inr=round(total_cost, 2),
                budget_feasibility=budget_status,
                expected_yield_range_quintals_per_acre=crop.yield_quintals_per_acre,
                estimated_net_profit_per_acre_inr=round(est_net_profit, 2),
                key_strengths=strengths,
                risk_factors=risks,
            )

            evaluated_candidates.append((crop, overall_score, item))

        # Sort descending by overall score
        evaluated_candidates.sort(key=lambda x: x[1], reverse=True)
        return evaluated_candidates

    # -------------------------------------------------------------------------
    # Step 4: Decision Synthesis & Limitations
    # -------------------------------------------------------------------------
    @classmethod
    def _step4_synthesize_decision(
        cls,
        req: FarmerProfileRequest,
        ranked_items: List[Tuple[CropProfile, float, CropRecommendationItem]],
    ) -> Tuple[List[CropRecommendationItem], List[CropRecommendationItem], List[str]]:
        """
        Separates into top recommendations (primary) and viable alternatives / hedges.
        Appends transparent agricultural limitations.
        """
        # Primary recommendations: items with score >= 60 and within or near budget
        primary: List[CropRecommendationItem] = []
        alternatives: List[CropRecommendationItem] = []

        for crop, score, item in ranked_items:
            if len(primary) < 2 and item.budget_feasibility in ["Within Budget", "Buffer Required"] and score >= 55.0:
                primary.append(item)
            elif len(alternatives) < 2:
                alternatives.append(item)

        # Fallback if primary is empty (e.g. extremely constrained budget)
        if not primary and ranked_items:
            primary.append(ranked_items[0][2])
            if len(ranked_items) > 1:
                alternatives.append(ranked_items[1][2])

        limitations = [
            "Soil Health Verification: This recommendation assumes standard regional soil fertility. Always conduct a lab Soil Health Card (SHC) test via your local Krishi Vigyan Kendra (KVK) for exact N-P-K and micronutrient deficits.",
            "Water Source Reliability: If relying on tube-well or canal irrigation, verify groundwater table depth and electricity supply consistency before sowing high-water crops.",
            "Market & MSP Volatility: Profit calculations use current Government MSP / CACP baseline estimates. Actual mandi prices at harvest fluctuate based on national supply and moisture levels.",
            "Pest & Weather Contingency: Maintain at least a 10-15% cash contingency reserve for unexpected pest outbreaks or sudden unseasonal rains during crop maturity.",
            "Certified Seeds: Always procure certified seeds from authorized state agricultural corporations or registered seed dealers with lot numbers."
        ]

        return primary, alternatives, limitations
