"""
Unit and Integration Test Suite for TERRA07 Explainable AI (XAI) Engine
Software Track: Heat-Risk Mapping at Human Scale
Agent 4: Explainable AI & Driver Breakdown Architect

Tests:
1. Exact Additive Feature Attribution (Points closure & 100% percentage closure)
2. Game-Theoretic Shapley Decomposition (Efficiency, Symmetry, Dummy Player axioms)
3. 7 Core Biophysical & Demographic Driver Coverage
4. Natural Language Diagnostic Generator (Format, accuracy, quantitative assertions)
5. Actionable Bottleneck Identification & Counterfactual What-If Calculations
6. Waterfall & Radar Chart Data Formatters (Frontend JSON schema readiness)
7. Diverse Data Ingestion (Wards, Streets, Raw Values, Dataclasses)
8. Edge Cases, Zero Risk, Extreme Danger, Boundary Clamping
"""

import math
import pytest
from typing import Dict

from engine.xai_attribution import (
    HeatRiskDriver,
    DriverWeights,
    NormalizationThresholds,
    RawDriverValues,
    FeatureAttribution,
    BottleneckLeveragePoint,
    WaterfallChartData,
    RadarChartData,
    XAIDiagnosticReport,
    RiskTier,
    AdditiveAttributionEngine,
    ShapleyAttributionEngine,
    DiagnosticNarrativeGenerator,
    BottleneckLeverageIdentifier,
    VisualizationDataFormatter,
    HeatRiskXAIExplainer,
    explain_heat_risk,
    normalize_driver_value,
    categorize_score,
    INTERVENTION_CATALOG,
)


# ============================================================================
# 1. FIXTURES & TEST DATA
# ============================================================================

@pytest.fixture
def sample_extreme_ward() -> Dict:
    """Represents an extreme heat-risk urban ward like Ahmedabad Old City / Market."""
    return {
        "ward_id": "W14",
        "ward_name": "Old Market Quarter",
        "zone": "Central",
        "area_km2": 2.4,
        "heat_risk_score": 89.2,
        "environmental": {
            "mean_lst_celsius": 44.2,
            "ndvi_vegetation_index": 0.08,
            "ndbi_builtup_index": 0.52,
            "surface_albedo": 0.12,
            "tree_canopy_pct": 5.0,
            "impervious_surface_pct": 88.0,
        },
        "demographics": {
            "total_population": 125000,
            "elderly_pct": 14.5,
            "children_pct": 9.2,
            "outdoor_workers_pct": 28.5,
            "slum_households_pct": 32.0,
        },
        "adaptive_capacity": {
            "ac_penetration_pct": 24.0,
            "cooling_centers_count": 1,
            "hydration_points_count": 3,
        },
    }


@pytest.fixture
def sample_cool_residential_ward() -> Dict:
    """Represents a cooler, green, affluent residential ward."""
    return {
        "ward_id": "W38",
        "ward_name": "Bodakdev Garden Suburb",
        "zone": "North-West",
        "area_km2": 5.9,
        "heat_risk_score": 28.5,
        "environmental": {
            "mean_lst_celsius": 32.5,
            "ndvi_vegetation_index": 0.35,
            "ndbi_builtup_index": 0.10,
            "surface_albedo": 0.22,
            "tree_canopy_pct": 45.0,
            "impervious_surface_pct": 40.0,
        },
        "demographics": {
            "total_population": 90000,
            "elderly_pct": 10.0,
            "children_pct": 5.0,
            "outdoor_workers_pct": 6.0,
            "slum_households_pct": 2.0,
        },
        "adaptive_capacity": {
            "ac_penetration_pct": 88.0,
            "cooling_centers_count": 5,
            "hydration_points_count": 12,
        },
    }


@pytest.fixture
def sample_street_corridor() -> Dict:
    """Represents a human-scale pedestrian thoroughfare."""
    return {
        "street_id": "ST102",
        "street_name": "Relief Road Commercial Corridor",
        "ward_id": "W14",
        "length_meters": 850.0,
        "mean_radiant_temp_celsius": 56.4,
        "surface_temp_celsius": 46.8,
        "shade_ratio": 0.08,
        "sky_view_factor": 0.72,
        "aspect_ratio_h_w": 0.85,
        "pedestrian_heat_risk": 82.5,
        "outdoor_workers_pct": 32.0,
        "elderly_pct": 12.0,
        "children_pct": 7.0,
        "ac_pct": 18.0,
        "ndvi": 0.04,
        "ndbi": 0.58,
    }


# ============================================================================
# 2. TESTS: EXACT ADDITIVE ATTRIBUTION ENGINE
# ============================================================================

class TestAdditiveAttribution:

    def test_weights_sum_to_one(self):
        """DriverWeights must sum strictly to 1.0."""
        weights = DriverWeights()
        total = (
            weights.surface_temp
            + weights.canopy_deficit
            + weights.impervious_surface
            + weights.demographic_vulnerability
            + weights.outdoor_workers
            + weights.cooling_deficit
            + weights.shade_deficit
        )
        assert math.isclose(total, 1.0, rel_tol=1e-5)

    def test_invalid_weights_raise_error(self):
        """DriverWeights must reject configs not summing to 1.0."""
        with pytest.raises(ValueError):
            DriverWeights(surface_temp=0.5, canopy_deficit=0.5, impervious_surface=0.5)

    def test_exact_closure_of_attribution_points(self):
        """The sum of individual driver points must exactly equal the composite score."""
        engine = AdditiveAttributionEngine()
        raw_vals = {
            HeatRiskDriver.SURFACE_TEMP: 44.2,
            HeatRiskDriver.CANOPY_DEFICIT: 0.08,
            HeatRiskDriver.IMPERVIOUS_SURFACE: 0.52,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: 23.7,
            HeatRiskDriver.OUTDOOR_WORKERS: 28.5,
            HeatRiskDriver.COOLING_DEFICIT: 76.0,
            HeatRiskDriver.SHADE_DEFICIT: 95.0,
        }
        norm_vals = {d: normalize_driver_value(d, raw_vals[d]) for d in HeatRiskDriver}

        score = engine.compute_score(norm_vals)
        attributions = engine.attribute(raw_vals, norm_vals)

        sum_points = sum(a.attribution_points for a in attributions)
        assert math.isclose(score, sum_points, abs_tol=0.1)

    def test_exact_percentage_sum_to_100(self):
        """The percentage contributions must sum strictly to 100.0%."""
        engine = AdditiveAttributionEngine()
        raw_vals = {
            HeatRiskDriver.SURFACE_TEMP: 42.0,
            HeatRiskDriver.CANOPY_DEFICIT: 0.12,
            HeatRiskDriver.IMPERVIOUS_SURFACE: 0.45,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: 20.0,
            HeatRiskDriver.OUTDOOR_WORKERS: 18.0,
            HeatRiskDriver.COOLING_DEFICIT: 50.0,
            HeatRiskDriver.SHADE_DEFICIT: 60.0,
        }
        norm_vals = {d: normalize_driver_value(d, raw_vals[d]) for d in HeatRiskDriver}

        attributions = engine.attribute(raw_vals, norm_vals)
        total_pct = sum(a.percentage_contribution for a in attributions)
        assert math.isclose(total_pct, 100.0, abs_tol=0.2)

    def test_all_seven_drivers_present(self):
        """All 7 required drivers must be present in the attribution output."""
        engine = AdditiveAttributionEngine()
        raw_vals = {d: 0.5 for d in HeatRiskDriver}
        norm_vals = {d: 0.5 for d in HeatRiskDriver}

        attributions = engine.attribute(raw_vals, norm_vals)
        assert len(attributions) == 7

        present_drivers = {a.driver for a in attributions}
        expected_drivers = set(HeatRiskDriver)
        assert present_drivers == expected_drivers


# ============================================================================
# 3. TESTS: SHAPLEY GAME-THEORETIC ATTRIBUTION ENGINE
# ============================================================================

class TestShapleyAttribution:

    def test_shapley_efficiency_axiom(self):
        """
        Efficiency Axiom: sum(phi_i) = f(x) - f(baseline).
        Game-theoretic Shapley values must sum to the difference between
        the sample score and the baseline score.
        """
        engine = ShapleyAttributionEngine()
        sample = {
            HeatRiskDriver.SURFACE_TEMP: 0.85,
            HeatRiskDriver.CANOPY_DEFICIT: 0.90,
            HeatRiskDriver.IMPERVIOUS_SURFACE: 0.75,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: 0.65,
            HeatRiskDriver.OUTDOOR_WORKERS: 0.80,
            HeatRiskDriver.COOLING_DEFICIT: 0.70,
            HeatRiskDriver.SHADE_DEFICIT: 0.90,
        }
        raw_mock = {d: 50.0 for d in HeatRiskDriver}

        score, base_score, attributions = engine.attribute(raw_mock, sample)
        sum_shapley = sum(a.attribution_points for a in attributions)
        score_diff = score - base_score

        assert math.isclose(sum_shapley, score_diff, abs_tol=0.2)

    def test_shapley_dummy_player_axiom(self):
        """
        Dummy Player Axiom: A player whose values match baseline and provides
        zero marginal contribution must receive a Shapley value near 0.0.
        """
        baseline = {d: 0.10 for d in HeatRiskDriver}
        engine = ShapleyAttributionEngine(baseline_values=baseline)

        # Feature outdoor_workers matches baseline exactly
        sample = {d: 0.80 for d in HeatRiskDriver}
        sample[HeatRiskDriver.OUTDOOR_WORKERS] = 0.10

        shapley_vals = engine.compute_shapley_values(sample)
        assert abs(shapley_vals[HeatRiskDriver.OUTDOOR_WORKERS]) < 1.0
        # Active features should have much higher attribution
        assert shapley_vals[HeatRiskDriver.SURFACE_TEMP] > 5.0

    def test_shapley_symmetry_axiom(self):
        """
        Symmetry Axiom: Two symmetric features with identical weights and identical
        values must receive identical Shapley values.
        """
        # Create a symmetric linear model where 2 features have identical weight 0.3
        def symmetric_model(cfg: Dict[HeatRiskDriver, float]) -> float:
            return 100.0 * (
                0.3 * cfg.get(HeatRiskDriver.OUTDOOR_WORKERS, 0.0)
                + 0.3 * cfg.get(HeatRiskDriver.SHADE_DEFICIT, 0.0)
                + 0.4 * cfg.get(HeatRiskDriver.SURFACE_TEMP, 0.0)
            )

        baseline = {d: 0.0 for d in HeatRiskDriver}
        engine = ShapleyAttributionEngine(model_func=symmetric_model, baseline_values=baseline)

        sample = {
            HeatRiskDriver.OUTDOOR_WORKERS: 0.75,
            HeatRiskDriver.SHADE_DEFICIT: 0.75,
            HeatRiskDriver.SURFACE_TEMP: 0.50,
        }
        shap_vals = engine.compute_shapley_values(sample)

        assert math.isclose(
            shap_vals[HeatRiskDriver.OUTDOOR_WORKERS],
            shap_vals[HeatRiskDriver.SHADE_DEFICIT],
            abs_tol=1e-3,
        )


# ============================================================================
# 4. TESTS: NATURAL LANGUAGE DIAGNOSTIC GENERATOR
# ============================================================================

class TestDiagnosticGenerator:

    def test_executive_summary_matches_reference_pattern(self, sample_extreme_ward):
        """
        Tests generation of executive summary against the prompt requirement:
        e.g., 'Ward 14 (Old Market Quarter) is rated EXTREME RISK (Score: 89.2).
        Primary driver: Extreme Surface Temperature (44.2°C, +34% contribution)
        combined with severe lack of tree canopy (NDVI 0.08, +26% contribution)
        and high density of outdoor market vendors (+22% contribution).'
        """
        explainer = HeatRiskXAIExplainer()
        report = explainer.explain(
            sample_extreme_ward,
            entity_id="W14",
            entity_name="Old Market Quarter",
            entity_type="ward",
            target_score=89.2,
        )

        summary = report.executive_summary
        assert "Old Market Quarter" in summary
        assert "EXTREME RISK" in summary
        assert "89.2" in summary
        assert "Primary driver:" in summary
        assert "contribution" in summary

    def test_dynamic_quantitative_values_in_narrative(self, sample_extreme_ward):
        """The narrative must include real calculated numbers and units, never hardcoded placeholders."""
        explainer = HeatRiskXAIExplainer()
        report = explainer.explain(sample_extreme_ward, target_score=89.2)

        # Must mention surface temp in Celsius
        assert "°C" in report.executive_summary
        # Primary driver must have a calculated percentage
        primary = report.primary_driver
        assert primary.percentage_contribution > 10.0
        assert f"{primary.percentage_contribution:.0f}%" in report.executive_summary

    def test_detailed_narrative_sections(self, sample_extreme_ward):
        """Detailed narrative must contain diagnostic overview, mechanisms, and action directives."""
        explainer = HeatRiskXAIExplainer()
        report = explainer.explain(sample_extreme_ward, target_score=89.2)

        narrative = report.detailed_narrative
        assert "Diagnostic Overview:" in narrative
        assert "Biophysical & Social Mechanism:" in narrative
        assert "Actionable Leverage Directive:" in narrative
        assert report.top_leverage_bottleneck.intervention_name in narrative


# ============================================================================
# 5. TESTS: ACTIONABLE BOTTLENECK IDENTIFICATION & WHAT-IF
# ============================================================================

class TestBottleneckIdentification:

    def test_identifies_top_actionable_bottleneck(self, sample_extreme_ward):
        """
        Evaluates that the #1 bottleneck combines high attribution with high feasibility.
        Even if surface temp is slightly higher in points, shade deficit or cooling deficit
        often has higher actionable leverage because it can be mitigated within days.
        """
        explainer = HeatRiskXAIExplainer()
        report = explainer.explain(sample_extreme_ward, target_score=89.2)

        top_b = report.top_leverage_bottleneck
        assert isinstance(top_b, BottleneckLeveragePoint)
        assert top_b.leverage_score > 0.0
        assert top_b.potential_score_reduction > 0.0
        assert top_b.projected_new_score < report.heat_risk_score
        assert top_b.intervention_name != ""
        assert top_b.feasibility_timeframe != ""

    def test_counterfactual_score_reduction(self):
        """Simulates counterfactual score reduction when top intervention is implemented."""
        raws = {
            HeatRiskDriver.SURFACE_TEMP: 45.0,
            HeatRiskDriver.CANOPY_DEFICIT: 0.05,
            HeatRiskDriver.IMPERVIOUS_SURFACE: 0.55,
            HeatRiskDriver.DEMOGRAPHIC_VULNERABILITY: 25.0,
            HeatRiskDriver.OUTDOOR_WORKERS: 30.0,
            HeatRiskDriver.COOLING_DEFICIT: 80.0,
            HeatRiskDriver.SHADE_DEFICIT: 90.0,
        }
        norms = {d: normalize_driver_value(d, raws[d]) for d in HeatRiskDriver}
        engine = AdditiveAttributionEngine()
        attrs = engine.attribute(raws, norms)
        current_score = engine.compute_score(norms)

        bottlenecks = BottleneckLeverageIdentifier.evaluate_all_leverage_points(current_score, attrs)
        assert len(bottlenecks) == 7

        # Highest leverage bottleneck
        top = bottlenecks[0]
        assert top.projected_new_score == pytest.approx(
            current_score - top.potential_score_reduction, abs=0.2
        )
        assert top.projected_new_score < current_score

    def test_intervention_catalog_completeness(self):
        """Every single heat risk driver must have a configured intervention catalog entry."""
        for driver in HeatRiskDriver:
            assert driver in INTERVENTION_CATALOG
            item = INTERVENTION_CATALOG[driver]
            assert 0.0 < item.feasibility_weight <= 1.0
            assert 0.0 < item.mitigation_efficiency <= 1.0
            assert len(item.action_template) > 20


# ============================================================================
# 6. TESTS: VISUALIZATION DATA FORMATTERS
# ============================================================================

class TestVisualizationFormatters:

    def test_waterfall_chart_structure(self, sample_extreme_ward):
        """Waterfall chart must have baseline, individual feature increments, and total step."""
        explainer = HeatRiskXAIExplainer()
        report = explainer.explain(sample_extreme_ward, target_score=89.2)

        waterfall = report.waterfall_chart
        assert isinstance(waterfall, WaterfallChartData)
        assert waterfall.final_score == 89.2

        # Step count: 7 drivers + final total = 8 (baseline is 0 in default additive)
        steps = waterfall.steps
        assert len(steps) >= 8

        total_step = steps[-1]
        assert total_step.step_type == "total"
        assert total_step.cumulative == 89.2
        assert total_step.color == RiskTier.EXTREME.color_hex

        # Check serialization
        wf_dict = waterfall.to_dict()
        assert "steps" in wf_dict
        assert len(wf_dict["steps"]) == len(steps)

    def test_radar_chart_structure(self, sample_extreme_ward):
        """Radar chart must include all 7 normalized axes with benchmarks."""
        explainer = HeatRiskXAIExplainer()
        report = explainer.explain(sample_extreme_ward, target_score=89.2)

        radar = report.radar_chart
        assert isinstance(radar, RadarChartData)
        assert len(radar.axes) == 7

        for axis in radar.axes:
            assert 0.0 <= axis.zone_score <= 100.0
            assert 0.0 <= axis.benchmark_average <= 100.0
            assert 0.0 <= axis.safe_threshold <= 100.0
            assert axis.raw_display != ""

        radar_dict = radar.to_dict()
        assert len(radar_dict["axes"]) == 7


# ============================================================================
# 7. TESTS: STREET CORRIDOR & VARIED DATA INGESTION
# ============================================================================

class TestVariedDataIngestion:

    def test_street_segment_explanation(self, sample_street_corridor):
        """Properly ingests and explains a pedestrian street segment."""
        report = explain_heat_risk(
            sample_street_corridor,
            entity_id="ST102",
            entity_name="Relief Road Commercial Corridor",
            entity_type="street",
        )

        assert report.entity_type == "street"
        assert report.entity_id == "ST102"
        assert "Street Segment" in report.executive_summary
        assert len(report.factor_attributions) == 7
        assert report.heat_risk_score > 60.0

    def test_cool_ward_explanation(self, sample_cool_residential_ward):
        """Properly analyzes a low/moderate risk cool ward."""
        report = explain_heat_risk(
            sample_cool_residential_ward,
            entity_id="W38",
            entity_name="Bodakdev Garden Suburb",
            entity_type="ward",
        )

        assert report.risk_tier in [RiskTier.LOW, RiskTier.MODERATE]
        assert report.heat_risk_score < 50.0

    def test_raw_driver_values_dataclass_input(self):
        """Accepts typed RawDriverValues dataclass."""
        raws = RawDriverValues(
            surface_temp_c=41.5,
            ndvi=0.18,
            ndbi=0.48,
            demographics_vulnerable_pct=18.0,
            outdoor_workers_pct=22.0,
            cooling_deficit_pct=60.0,
            shade_deficit_pct=70.0,
            area_name="Industrial Cluster East",
        )
        report = explain_heat_risk(raws)
        assert report.entity_name == "Industrial Cluster East"
        assert len(report.factor_attributions) == 7

    def test_batch_explanation(self, sample_extreme_ward, sample_cool_residential_ward):
        """Batch explains an ensemble of urban wards."""
        explainer = HeatRiskXAIExplainer()
        reports = explainer.batch_explain([sample_extreme_ward, sample_cool_residential_ward])
        assert len(reports) == 2
        assert reports[0].entity_id == "W14"
        assert reports[1].entity_id == "W38"


# ============================================================================
# 8. TESTS: EDGE CASES & ROBUSTNESS
# ============================================================================

class TestEdgeCasesAndRobustness:

    def test_zero_risk_boundary(self):
        """Handles lowest possible theoretical inputs gracefully."""
        minimal_input = {
            "surface_temp": 20.0,      # very cool
            "ndvi": 0.60,              # lush forest
            "ndbi": -0.40,             # lake/water
            "elderly_pct": 0.0,
            "child_pct": 0.0,
            "outdoor_workers_pct": 0.0,
            "ac_pct": 100.0,           # 100% cooling
            "shade_ratio": 1.0,        # 100% shaded
        }
        report = explain_heat_risk(minimal_input, entity_name="Ideal Oasis")
        assert report.heat_risk_score == 0.0
        assert report.risk_tier == RiskTier.LOW
        assert len(report.factor_attributions) == 7

    def test_extreme_saturation_boundary(self):
        """Handles extreme off-scale inputs without crashing or exceeding 100."""
        extreme_input = {
            "surface_temp": 65.0,      # off-scale furnace heat
            "ndvi": -0.20,             # bare asphalt
            "ndbi": 0.90,              # steel and concrete
            "elderly_pct": 40.0,
            "child_pct": 30.0,
            "outdoor_workers_pct": 60.0,
            "ac_pct": 0.0,             # 0% AC
            "shade_ratio": 0.0,        # 0% shade
        }
        report = explain_heat_risk(extreme_input, entity_name="Molten Corridor")
        assert report.heat_risk_score == 100.0
        assert report.risk_tier == RiskTier.EXTREME

    def test_json_serializability(self, sample_extreme_ward):
        """The entire XAIDiagnosticReport must serialize cleanly to a dictionary."""
        report = explain_heat_risk(sample_extreme_ward)
        data_dict = report.to_dict()

        assert isinstance(data_dict, dict)
        assert "factor_attributions" in data_dict
        assert "executive_summary" in data_dict
        assert "waterfall_chart" in data_dict
        assert "radar_chart" in data_dict
        assert "top_leverage_bottleneck" in data_dict
        # Verify no non-serializable objects inside
        import json
        json_str = json.dumps(data_dict)
        assert len(json_str) > 1000
