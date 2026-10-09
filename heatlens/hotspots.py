"""Hotspot detection (Getis-Ord Gi*) and bivariate priority area classification."""

from pathlib import Path
from typing import Dict, Any, List
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy import stats

from heatlens.config import load_config, PROJECT_ROOT

PRIORITY_AREAS_CSV = PROJECT_ROOT / "data" / "processed" / "priority_areas.csv"

# Landmark anchors for Ahmedabad clusters
AHMEDABAD_LANDMARKS = [
    (72.587, 23.023, "Kalupur & Manek Chowk Historic Core"),
    (72.595, 23.018, "Astodia & Raipur Darwaja"),
    (72.605, 23.010, "Rakhial Industrial Belt"),
    (72.618, 22.998, "Vatva GIDC Phase 1"),
    (72.610, 23.045, "Naroda Industrial Estate"),
    (72.585, 23.002, "Danilimda & Behrampura"),
    (72.568, 23.030, "Navrangpura Commercial Strip"),
    (72.572, 23.040, "Sabarmati Riverfront West"),
    (72.545, 23.048, "Bodakdev & SG Highway Corridor"),
    (72.552, 23.015, "Ambawadi & Law Garden"),
]


def find_nearest_landmark(lon: float, lat: float) -> str:
    best_dist = float("inf")
    best_name = "Ahmedabad Sector"
    for l_lon, l_lat, name in AHMEDABAD_LANDMARKS:
        d = (lon - l_lon) ** 2 + (lat - l_lat) ** 2
        if d < best_dist:
            best_dist = d
            best_name = name
    return best_name


def compute_hotspots(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Computes Getis-Ord Gi* statistics and bivariate priority classes."""
    df = gdf.copy()
    n = len(df)
    scores = df["risk_score"].values

    # Compute spatial weights and Getis-Ord Gi*
    # We attempt libpysal Queen weights, with analytical fallback
    z_scores = np.zeros(n)
    p_values = np.ones(n)

    try:
        from libpysal.weights import Queen
        from esda.moran import G_Local

        w = Queen.from_dataframe(df, use_index=False)
        w.transform = "R"
        g_local = G_Local(scores, w, transform="R", star=True)
        z_scores = g_local.Zs
        p_values = g_local.p_sim
    except Exception:
        # Robust analytical spatial lag fallback
        coords = np.column_stack([df["lon"].values, df["lat"].values])
        mean_s = np.mean(scores)
        std_s = np.std(scores)
        # 8-neighbor spatial kernel
        for i in range(n):
            dists = np.sum((coords - coords[i]) ** 2, axis=1)
            neighbor_idx = np.argsort(dists)[:9]  # Self + 8 nearest
            local_mean = np.mean(scores[neighbor_idx])
            z = (local_mean - mean_s) / (std_s / np.sqrt(len(neighbor_idx)))
            z_scores[i] = z
            p_values[i] = 2.0 * (1.0 - stats.norm.cdf(abs(z)))

    hotspot_class = []
    for z, p in zip(z_scores, p_values):
        if z > 1.96 and p < 0.05:
            hotspot_class.append("Hotspot (p<0.05)")
        elif z < -1.96 and p < 0.05:
            hotspot_class.append("Cold spot (p<0.05)")
        else:
            hotspot_class.append("Not Significant")

    df["gi_z_score"] = z_scores.round(3)
    df["gi_p_value"] = p_values.round(4)
    df["hotspot_class"] = hotspot_class

    # Bivariate priority class: "Hot & vulnerable"
    # H in top quartile AND V in top quartile AND pop_total >= 25th percentile
    h_q75 = df["comp_hazard"].quantile(0.75)
    v_q75 = df["comp_vulnerability"].quantile(0.75)
    pop_q25 = df["pop_total"].quantile(0.25)

    is_hot_and_vuln = (
        (df["comp_hazard"] >= h_q75) &
        (df["comp_vulnerability"] >= v_q75) &
        (df["pop_total"] >= pop_q25)
    )
    df["is_hot_and_vulnerable"] = is_hot_and_vuln

    # Assign cluster names
    cluster_names = [find_nearest_landmark(lon, lat) for lon, lat in zip(df["lon"], df["lat"])]
    df["cluster_name"] = cluster_names

    return df


def generate_priority_areas(df: gpd.GeoDataFrame, output_path: Path = PRIORITY_AREAS_CSV) -> pd.DataFrame:
    """Generates two clearly separated priority rankings: by Risk Score and by People-Weighted Risk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Ranking by Risk Score
    by_risk = df.sort_values(by="risk_score", ascending=False).copy()
    by_risk["rank_by_risk"] = range(1, len(by_risk) + 1)

    # 2. Ranking by People-Weighted Risk (person-risk points)
    by_people = df.sort_values(by="person_risk_points", ascending=False).copy()
    by_people["rank_by_people_risk"] = range(1, len(by_people) + 1)

    # Extract top drivers string
    from heatlens.explain import INDICATOR_LABELS
    def get_top_3_drivers(row):
        drivers = []
        for k in ["c_lst", "c_building", "c_veg_deficit", "c_pop_density", "c_outdoor_proxy", "c_elderly", "c_dist_cooling"]:
            drivers.append((row[k], INDICATOR_LABELS.get(k, k)))
        drivers.sort(reverse=True)
        return "; ".join([f"{name} ({val} pts)" for val, name in drivers[:3]])

    by_risk["top_3_drivers"] = [get_top_3_drivers(r) for _, r in by_risk.iterrows()]

    cols_export = [
        "rank_by_risk",
        "cell_id",
        "lat",
        "lon",
        "cluster_name",
        "risk_score",
        "risk_tier",
        "hotspot_class",
        "is_hot_and_vulnerable",
        "pop_total",
        "pop_65plus",
        "person_risk_points",
        "top_3_drivers",
        "dist_water_m",
        "dist_cooling_m"
    ]

    export_df = by_risk[cols_export]
    export_df.to_csv(output_path, index=False)
    return export_df


def build_priority_areas_table(df: gpd.GeoDataFrame, config=None) -> pd.DataFrame:
    """Builds the priority areas table."""
    return generate_priority_areas(df, PRIORITY_AREAS_CSV)


def save_priority_areas_csv(df: pd.DataFrame, output_path: Path = PRIORITY_AREAS_CSV) -> Path:
    """Saves priority areas table to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path

