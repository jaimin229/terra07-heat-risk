"""
Unit test suite for engine/risk_engine.py
Team: TERRA07 (Heat-Risk Mapping at Human Scale)
"""

import math
import pytest
from engine.risk_engine import (
    UrbanHeatRiskEngine,
    HazardWeights,
    ExposureWeights,
    VulnerabilityWeights,
    NormalizationBounds,
    HazardInputs,
    ExposureInputs,
    VulnerabilityInputs,
    WardRiskInput,
    StreetSegmentRiskInput,
    RiskCategory,
    calculate_heat_index,
    calculate_wet_bulb_temperature,
    min_max_scale,
)


def test_heat_index_rothfusz_accuracy():
    """Verify NOAA / Rothfusz heat index calculation for known benchmark pairs."""
    # 35°C (95°F) at 60% RH -> severe heat index
    hi = calculate_heat_index(35.0, 60.0)
    assert 44.0 <= hi <= 49.0

    # 27°C (80.6°F) at 40% RH -> mild heat index
    hi_mild = calculate_heat_index(27.0, 40.0)
    assert 26.0 <= hi_mild <= 29.5

    # Cool condition: 20°C at 50% RH
    hi_cool = calculate_heat_index(20.0, 50.0)
    assert 18.0 <= hi_cool <= 22.0


def test_wet_bulb_stull_accuracy():
    """Verify Stull (2011) wet bulb temperature formula."""
    # At 35°C, 100% RH, wet bulb equals dry bulb (35°C)
    tw_saturated = calculate_wet_bulb_temperature(35.0, 100.0)
    assert math.isclose(tw_saturated, 35.0, abs_tol=0.7)

    # 35°C at 50% RH -> ~26°C - 28°C
    tw = calculate_wet_bulb_temperature(35.0, 50.0)
    assert 25.5 <= tw <= 28.5


def test_min_max_clamping():
    """Verify min_max_scale clamps outliers safely within [0.0, 1.0]."""
    assert min_max_scale(10.0, 20.0, 40.0) == 0.0
    assert min_max_scale(50.0, 20.0, 40.0) == 1.0
    assert min_max_scale(30.0, 20.0, 40.0) == 0.5


def test_invalid_weights_raise_exception():
    """Verify dataclasses enforce sum-to-1.0 invariant."""
    with pytest.raises(ValueError, match="HazardWeights must sum to 1.0"):
        HazardWeights(w_lst=0.5, w_heat_index=0.5, w_ndbi=0.2, w_solar_irradiance=0.1)

    with pytest.raises(ValueError, match="ExposureWeights must sum to 1.0"):
        ExposureWeights(w_population_density=0.5, w_pedestrian_traffic=0.5, w_outdoor_workers=0.5)

    with pytest.raises(ValueError, match="VulnerabilityWeights must sum to 1.0"):
        VulnerabilityWeights(
            w_elderly=0.1,
            w_children=0.1,
            w_ac_deficit=0.1,
            w_chronic_illness=0.1,
            w_housing_vulnerability=0.1,
        )


def test_risk_categorization_boundaries():
    """Verify exact categorization bands: Low, Moderate, High, Severe, Extreme."""
    engine = UrbanHeatRiskEngine()
    assert engine.categorize_hri(0.0) == RiskCategory.LOW
    assert engine.categorize_hri(25.0) == RiskCategory.LOW
    assert engine.categorize_hri(25.01) == RiskCategory.MODERATE
    assert engine.categorize_hri(50.0) == RiskCategory.MODERATE
    assert engine.categorize_hri(50.1) == RiskCategory.HIGH
    assert engine.categorize_hri(70.0) == RiskCategory.HIGH
    assert engine.categorize_hri(70.01) == RiskCategory.SEVERE
    assert engine.categorize_hri(85.0) == RiskCategory.SEVERE
    assert engine.categorize_hri(85.01) == RiskCategory.EXTREME
    assert engine.categorize_hri(100.0) == RiskCategory.EXTREME


def test_zero_exposure_and_zero_hazard_axioms():
    """Axiomatic requirement: if exposure is 0, geometric HRI must be 0."""
    engine = UrbanHeatRiskEngine(aggregation_mode="geometric")

    hazard = HazardInputs(lst_c=48.0, heat_index_c=48.0, ndbi=0.5, solar_irradiance_w_m2=1000.0)
    zero_exposure = ExposureInputs(
        population_density_per_km2=0.0,
        pedestrian_foot_traffic_hourly=0.0,
        outdoor_workers_pct=0.0,
    )
    vuln = VulnerabilityInputs(
        elderly_pct=25.0,
        children_pct=15.0,
        ac_deficit_pct=80.0,
        chronic_conditions_pct=30.0,
        housing_uninsulated_pct=70.0,
    )

    ward = WardRiskInput(
        ward_id="W_EMPTY",
        ward_name="Empty Zone",
        hazard=hazard,
        exposure=zero_exposure,
        vulnerability=vuln,
    )
    score = engine.score_ward(ward)
    assert score.hri == 0.0
    assert score.category == RiskCategory.LOW


def test_street_segment_canopy_mitigation():
    """Tree canopy cover must measurably attenuate effective hazard and HRI."""
    engine = UrbanHeatRiskEngine()

    base_hazard = HazardInputs(lst_c=42.0, heat_index_c=40.0, ndbi=0.3, solar_irradiance_w_m2=900.0)
    exposure = ExposureInputs(
        population_density_per_km2=12000.0,
        pedestrian_foot_traffic_hourly=400.0,
        outdoor_workers_pct=15.0,
    )
    vuln = VulnerabilityInputs(
        elderly_pct=15.0,
        children_pct=10.0,
        ac_deficit_pct=40.0,
        chronic_conditions_pct=18.0,
        housing_uninsulated_pct=30.0,
    )

    unshaded = StreetSegmentRiskInput(
        segment_id="ST_01",
        street_name="Barren Avenue",
        hazard=base_hazard,
        exposure=exposure,
        vulnerability=vuln,
        length_meters=500.0,
        tree_canopy_pct=0.0,
    )
    shaded = StreetSegmentRiskInput(
        segment_id="ST_02",
        street_name="Canopy Avenue",
        hazard=base_hazard,
        exposure=exposure,
        vulnerability=vuln,
        length_meters=500.0,
        tree_canopy_pct=50.0,
    )

    score_unshaded = engine.score_street_segment(unshaded)
    score_shaded = engine.score_street_segment(shaded)

    assert score_shaded.hri < score_unshaded.hri
    assert score_shaded.hazard_breakdown.norm_lst < score_unshaded.hazard_breakdown.norm_lst
    assert score_shaded.hazard_breakdown.norm_solar < score_unshaded.hazard_breakdown.norm_solar


def test_batch_scoring():
    """Verify batch ward and street evaluation."""
    engine = UrbanHeatRiskEngine()
    h = HazardInputs(lst_c=36.0, heat_index_c=37.0, ndbi=0.2, solar_irradiance_w_m2=750.0)
    e = ExposureInputs(
        population_density_per_km2=8000.0,
        pedestrian_foot_traffic_hourly=200.0,
        outdoor_workers_pct=10.0,
    )
    v = VulnerabilityInputs(
        elderly_pct=12.0,
        children_pct=8.0,
        ac_deficit_pct=25.0,
        chronic_conditions_pct=15.0,
        housing_uninsulated_pct=20.0,
    )

    wards = [
        WardRiskInput(ward_id=f"W_{i}", ward_name=f"Ward {i}", hazard=h, exposure=e, vulnerability=v)
        for i in range(5)
    ]
    results = engine.batch_score_wards(wards)
    assert len(results) == 5
    for res in results:
        assert isinstance(res.hri, float)
        assert res.category in list(RiskCategory)
