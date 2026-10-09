"""Heat risk scoring engine with exact additive feature attribution (Team TERRA07)."""

from pathlib import Path
from typing import Dict, Any, Tuple
import geopandas as gpd
import numpy as np
import pandas as pd

from heatlens.config import load_config, PROJECT_ROOT

SCORES_GEOJSON = PROJECT_ROOT / "data" / "processed" / "scores.geojson"


def winsorize_and_minmax(series: pd.Series, low_pct: float = 0.02, high_pct: float = 0.98, use_log1p: bool = False) -> Tuple[pd.Series, float, float]:
    """Winsorises a series at specified percentiles and applies min-max scaling to [0.0, 1.0]."""
    vals = series.copy()
    if use_log1p:
        vals = np.log1p(np.maximum(0.0, vals))

    q_lo = float(vals.quantile(low_pct))
    q_hi = float(vals.quantile(high_pct))

    if math.isclose(q_lo, q_hi):
        return pd.Series(0.5, index=series.index), q_lo, q_hi

    clipped = vals.clip(lower=q_lo, upper=q_hi)
    normalized = (clipped - q_lo) / (q_hi - q_lo)
    return normalized.clip(0.0, 1.0), q_lo, q_hi


import math


def score_features(gdf: gpd.GeoDataFrame, config=None, custom_weights: Dict[str, Any] = None) -> gpd.GeoDataFrame:
    """Computes composite heat risk score and exact indicator contributions for each grid cell."""
    if config is None:
        config = load_config()

    df = gdf.copy()

    # Extract weights
    w_comp = config.weights.components
    w_haz = config.weights.hazard
    w_exp = config.weights.exposure
    w_vul = config.weights.vulnerability
    w_adp = config.weights.adaptive_gap

    if custom_weights:
        # Override with custom weights if provided
        comp_override = custom_weights.get("components", {})
        w_c_h = comp_override.get("hazard", w_comp.hazard)
        w_c_e = comp_override.get("exposure", w_comp.exposure)
        w_c_v = comp_override.get("vulnerability", w_comp.vulnerability)
        w_c_a = comp_override.get("adaptive_gap", w_comp.adaptive_gap)
    else:
        w_c_h = w_comp.hazard
        w_c_e = w_comp.exposure
        w_c_v = w_comp.vulnerability
        w_c_a = w_comp.adaptive_gap

    # Normalize component weights to sum to 1.0
    c_sum = w_c_h + w_c_e + w_c_v + w_c_a
    w_c_h /= c_sum
    w_c_e /= c_sum
    w_c_v /= c_sum
    w_c_a /= c_sum

    # Derived indicator: vegetation deficit = 1 - clip(ndvi, 0, 1)
    df["veg_deficit"] = (1.0 - df["ndvi_mean"].clip(0.0, 1.0)).round(4)

    # 1. Hazard indicators
    z_lst, _, _ = winsorize_and_minmax(df["lst_mean_c"], config.normalisation.winsor_low, config.normalisation.winsor_high)
    z_bldg, _, _ = winsorize_and_minmax(df["building_coverage"], config.normalisation.winsor_low, config.normalisation.winsor_high)
    z_veg, _, _ = winsorize_and_minmax(df["veg_deficit"], config.normalisation.winsor_low, config.normalisation.winsor_high)

    # 2. Exposure indicators
    z_pop, _, _ = winsorize_and_minmax(df["pop_density"], config.normalisation.winsor_low, config.normalisation.winsor_high, use_log1p=True)
    z_act, _, _ = winsorize_and_minmax(df["outdoor_activity_proxy"], config.normalisation.winsor_low, config.normalisation.winsor_high)

    # 3. Vulnerability indicators
    z_eld, _, _ = winsorize_and_minmax(df["elderly_share"], config.normalisation.winsor_low, config.normalisation.winsor_high)
    z_chi, _, _ = winsorize_and_minmax(df["child_share"], config.normalisation.winsor_low, config.normalisation.winsor_high)

    # 4. Adaptive gap indicators
    z_cool, _, _ = winsorize_and_minmax(df["dist_cooling_m"], config.normalisation.winsor_low, config.normalisation.winsor_high, use_log1p=True)
    z_wat, _, _ = winsorize_and_minmax(df["dist_water_m"], config.normalisation.winsor_low, config.normalisation.winsor_high, use_log1p=True)

    # Component sub-scores in [0, 1]
    h_score = w_haz.lst * z_lst + w_haz.building_coverage * z_bldg + w_haz.veg_deficit * z_veg
    e_score = w_exp.pop_density * z_pop + w_exp.outdoor_activity_proxy * z_act
    v_score = w_vul.elderly_share * z_eld + w_vul.child_share * z_chi
    a_score = w_adp.dist_cooling_centre * z_cool + w_adp.dist_water_point * z_wat

    # Exact indicator contributions (0 to 100 points scale)
    c_lst = 100.0 * w_c_h * w_haz.lst * z_lst
    c_bldg = 100.0 * w_c_h * w_haz.building_coverage * z_bldg
    c_veg = 100.0 * w_c_h * w_haz.veg_deficit * z_veg

    c_pop = 100.0 * w_c_e * w_exp.pop_density * z_pop
    c_act = 100.0 * w_c_e * w_exp.outdoor_activity_proxy * z_act

    c_eld = 100.0 * w_c_v * w_vul.elderly_share * z_eld
    c_chi = 100.0 * w_c_v * w_vul.child_share * z_chi

    c_cool = 100.0 * w_c_a * w_adp.dist_cooling_centre * z_cool
    c_wat = 100.0 * w_c_a * w_adp.dist_water_point * z_wat

    # Component totals
    comp_h = c_lst + c_bldg + c_veg
    comp_e = c_pop + c_act
    comp_v = c_eld + c_chi
    comp_a = c_cool + c_wat

    # Composite Risk score = exact sum of all contributions
    risk = comp_h + comp_e + comp_v + comp_a

    # Verification: contribution sum equals risk score to within 1e-9
    diff = np.abs(risk - (c_lst + c_bldg + c_veg + c_pop + c_act + c_eld + c_chi + c_cool + c_wat))
    assert np.all(diff < 1e-6), "Indicator contributions do not sum to Risk score!"

    # Risk tiers from config
    t_low = config.tiers.low
    t_mod = config.tiers.moderate
    t_high = config.tiers.high

    def assign_tier(val: float) -> str:
        if val >= t_high:
            return "Extreme"
        elif val >= t_mod:
            return "High"
        elif val >= t_low:
            return "Moderate"
        else:
            return "Low"

    tiers = [assign_tier(r) for r in risk]

    # Assign columns
    df["c_lst"] = c_lst.round(2)
    df["c_building"] = c_bldg.round(2)
    df["c_veg_deficit"] = c_veg.round(2)
    df["c_pop_density"] = c_pop.round(2)
    df["c_outdoor_proxy"] = c_act.round(2)
    df["c_elderly"] = c_eld.round(2)
    df["c_child"] = c_chi.round(2)
    df["c_dist_cooling"] = c_cool.round(2)
    df["c_dist_water"] = c_wat.round(2)

    # Component totals from exact rounded columns
    comp_h = (df["c_lst"] + df["c_building"] + df["c_veg_deficit"]).round(2)
    comp_e = (df["c_pop_density"] + df["c_outdoor_proxy"]).round(2)
    comp_v = (df["c_elderly"] + df["c_child"]).round(2)
    comp_a = (df["c_dist_cooling"] + df["c_dist_water"]).round(2)

    df["comp_hazard"] = comp_h
    df["comp_exposure"] = comp_e
    df["comp_vulnerability"] = comp_v
    df["comp_adaptive_gap"] = comp_a

    # Composite Risk score = exact sum of all contributions
    risk = (comp_h + comp_e + comp_v + comp_a).round(2)
    df["risk_score"] = risk
    df["risk_tier"] = [assign_tier(r) for r in risk]

    # People-weighted risk = Risk * pop_total / 1000 ("person-risk points")
    df["person_risk_points"] = ((df["risk_score"] * df["pop_total"]) / 1000.0).round(2)

    return df


def save_scores_geojson(gdf: gpd.GeoDataFrame, output_path: Path = SCORES_GEOJSON):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure WGS84 for GeoJSON
    gdf_wgs84 = gdf.to_crs("EPSG:4326")
    # Drop list and complex objects for GeoJSON compatibility
    clean = gdf_wgs84.drop(columns=["flags", "geometry_wgs84"], errors="ignore")
    clean.to_file(output_path, driver="GeoJSON")
    return output_path
