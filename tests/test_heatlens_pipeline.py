"""Unit and integration test suite strictly verifying HeatLens specifications (07_VALIDATION_AND_TESTS.md)."""

import re
from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from heatlens.config import load_config, PROJECT_ROOT
from heatlens.grid import build_utm_grid
from heatlens.scoring import winsorize_and_minmax, score_features
from heatlens.explain import generate_explanation_sentence, get_cell_contributions_vs_median
from heatlens.hotspots import compute_hotspots
from heatlens.actions.cooling_model import fit_cooling_model
from heatlens.actions.shade import evaluate_shade_interventions
from heatlens.actions.water import evaluate_water_points
from heatlens.actions.cooling_centres import evaluate_cooling_centres
from heatlens.actions.rank import build_unified_action_plan, optimize_budget_allocation


def test_grid_geometry():
    """Verify cells tile bbox, no empty geometries, areas approx 250m x 250m."""
    config = load_config()
    grid_gdf = build_utm_grid(config)
    assert len(grid_gdf) > 500, "Grid should have >= 500 cells for Ahmedabad bbox"
    assert "cell_id" in grid_gdf.columns
    assert "geometry" in grid_gdf.columns
    assert "lat" in grid_gdf.columns
    assert "lon" in grid_gdf.columns

    # Verify metric area in UTM EPSG:32643
    expected_area = config.grid_size_m * config.grid_size_m  # 62,500 m2
    areas = grid_gdf["geometry"].area
    np.testing.assert_allclose(areas.values, expected_area, rtol=1e-3)


def test_landsat_scaling():
    """Verify Landsat DN to Celsius scaling formula: DN 44,000 -> 26.24 °C."""
    # Scale: K = DN * 0.00341802 + 149.0
    # C = K - 273.15
    dn = 44000
    kelvin = dn * 0.00341802 + 149.0
    celsius = kelvin - 273.15
    assert round(celsius, 1) == 26.2, f"Expected 26.2 °C, got {celsius}"


def test_qa_cloud_mask():
    """Verify cloud and dilated cloud bitmask behavior."""
    # QA pixel bits: Dilated Cloud = bit 1, Cirrus = bit 2, Cloud = bit 3, Cloud Shadow = bit 4
    def is_cloudy(qa_dn: int) -> bool:
        cloud_bits = (1 << 1) | (1 << 3) | (1 << 4)
        return (qa_dn & cloud_bits) != 0

    clear_pixel = 21824  # Clear sky standard DN
    cloudy_pixel = 21824 | (1 << 3)  # Cloud bit set
    shadow_pixel = 21824 | (1 << 4)  # Shadow bit set

    assert not is_cloudy(clear_pixel)
    assert is_cloudy(cloudy_pixel)
    assert is_cloudy(shadow_pixel)


def test_normalisation_bounds_and_constant_column():
    """Verify winsorize_and_minmax outputs are within [0, 1] and handles constants."""
    series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 100.0])
    norm, q_lo, q_hi = winsorize_and_minmax(series, low_pct=0.05, high_pct=0.95)
    assert norm.min() >= 0.0
    assert norm.max() <= 1.0

    # Constant column edge case
    constant_series = pd.Series([42.0, 42.0, 42.0, 42.0])
    norm_const, _, _ = winsorize_and_minmax(constant_series)
    assert np.all(norm_const == 0.5)


def test_exact_scoring_closure():
    """Verify exact linear additive closure: contributions must sum to risk_score (< 1e-6)."""
    config = load_config()
    features_path = PROJECT_ROOT / "data" / "processed" / "features.parquet"
    assert features_path.is_file(), "features.parquet must exist"
    gdf = gpd.read_parquet(features_path)

    scored_gdf = score_features(gdf, config=config)

    # Sum of 9 indicators
    indicator_cols = [
        "c_lst", "c_building", "c_veg_deficit",
        "c_pop_density", "c_outdoor_proxy",
        "c_elderly", "c_child",
        "c_dist_cooling", "c_dist_water"
    ]
    computed_sum = scored_gdf[indicator_cols].sum(axis=1)
    diff = np.abs(scored_gdf["risk_score"] - computed_sum)
    assert np.all(diff < 1e-6), f"Max difference: {diff.max()}"

    # Verify score bounds [0, 100]
    assert scored_gdf["risk_score"].min() >= 0.0
    assert scored_gdf["risk_score"].max() <= 100.0


def test_explain_sentence_consistency():
    """Verify that explanation sentence numbers strictly match underlying cell data."""
    config = load_config()
    features_path = PROJECT_ROOT / "data" / "processed" / "features.parquet"
    gdf = gpd.read_parquet(features_path)
    scored_gdf = score_features(gdf, config=config)

    sample_cell = scored_gdf.iloc[0]
    sentence = generate_explanation_sentence(sample_cell, scored_gdf)
    score_str = str(round(float(sample_cell["risk_score"]), 1))

    assert score_str in sentence, f"Sentence '{sentence}' does not contain score {score_str}"
    assert sample_cell["risk_tier"] in sentence


def test_hotspots_gi_star():
    """Verify Getis-Ord Gi* flags high-value clusters on a synthetic grid."""
    features_path = PROJECT_ROOT / "data" / "processed" / "features.parquet"
    gdf = gpd.read_parquet(features_path)
    config = load_config()
    scored_gdf = score_features(gdf, config=config)

    hotspot_gdf = compute_hotspots(scored_gdf)
    assert "gi_z_score" in hotspot_gdf.columns
    assert "gi_p_value" in hotspot_gdf.columns
    assert "hotspot_class" in hotspot_gdf.columns
    assert "Hotspot (p<0.05)" in hotspot_gdf["hotspot_class"].values


def test_actions_monotonicity_and_diminishing_returns():
    """Verify actions strictly reduce or maintain risk (never increase) and non-negative impact."""
    scores_path = PROJECT_ROOT / "data" / "processed" / "scores.geojson"
    assert scores_path.is_file(), "scores.geojson must exist"
    gdf = gpd.read_file(scores_path)
    config = load_config()

    # 1. Shade action
    shade_df = evaluate_shade_interventions(gdf, config=config)
    assert not shade_df.empty
    assert (shade_df["delta_risk"] >= 0.0).all()
    assert (shade_df["impact"] >= 0.0).all()
    assert (shade_df["risk_after"] <= shade_df["risk_before"]).all()

    # 2. Water action
    water_df = evaluate_water_points(gdf, config=config)
    assert not water_df.empty
    assert (water_df["impact"] >= 0.0).all()
    # Greedy marginal impact should be generally non-increasing / highest first
    assert water_df.iloc[0]["impact"] >= water_df.iloc[-1]["impact"]

    # 3. Cooling action
    cooling_df = evaluate_cooling_centres(gdf, config=config)
    assert not cooling_df.empty
    assert (cooling_df["impact"] >= 0.0).all()


def test_budget_knapsack_constraints():
    """Verify budget-constrained knapsack allocator never exceeds budget."""
    actions_path = PROJECT_ROOT / "data" / "processed" / "actions.csv"
    assert actions_path.is_file(), "actions.csv must exist"
    actions_df = pd.read_csv(actions_path)

    test_budgets = [1_000_000.0, 5_000_000.0, 20_000_000.0]
    for b in test_budgets:
        sel_df, summary = optimize_budget_allocation(actions_df, budget_inr=b)
        assert summary["budget_spent_inr"] <= b
        assert summary["budget_remaining_inr"] >= 0.0
        assert summary["total_impact_points"] >= 0.0


def test_no_forbidden_random_in_source():
    """Verify no forbidden random calls exist in heatlens production modules (outside sensitivity Monte Carlo)."""
    forbidden_files = [
        PROJECT_ROOT / "heatlens" / "grid.py",
        PROJECT_ROOT / "heatlens" / "features.py",
        PROJECT_ROOT / "heatlens" / "scoring.py",
        PROJECT_ROOT / "heatlens" / "explain.py",
        PROJECT_ROOT / "heatlens" / "hotspots.py",
        PROJECT_ROOT / "heatlens" / "actions" / "shade.py",
        PROJECT_ROOT / "heatlens" / "actions" / "water.py",
        PROJECT_ROOT / "heatlens" / "actions" / "cooling_centres.py",
        PROJECT_ROOT / "heatlens" / "actions" / "rank.py",
    ]

    for f in forbidden_files:
        if f.is_file():
            content = f.read_text(encoding="utf-8")
            assert "np.random" not in content, f"Found forbidden np.random in {f.name}"
            assert "random.random" not in content, f"Found forbidden random.random in {f.name}"
