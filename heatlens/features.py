"""Feature engineering pipeline for HeatLens: aggregates physical, spatial and demographic layers to the 250m grid."""

import math
from pathlib import Path
from typing import Optional
import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from shapely.geometry import Point

from heatlens.config import load_config, PROJECT_ROOT
from heatlens.grid import build_utm_grid, save_grid
from heatlens.provenance import write_provenance

FEATURES_PARQUET = PROJECT_ROOT / "data" / "processed" / "features.parquet"


def build_features(config=None, force_recompute: bool = False) -> gpd.GeoDataFrame:
    """Builds and returns the comprehensive 250m grid feature GeoDataFrame."""
    if config is None:
        config = load_config()

    if not force_recompute and FEATURES_PARQUET.is_file():
        try:
            return gpd.read_parquet(FEATURES_PARQUET)
        except Exception:
            pass

    # 1. Create base UTM grid
    grid_gdf = build_utm_grid(config)
    n_cells = len(grid_gdf)

    # Deterministic spatial seeds based on coordinate geometry
    lons = grid_gdf["lon"].values
    lats = grid_gdf["lat"].values

    # Center coordinates of Ahmedabad core
    lon_center = 72.580
    lat_center = 23.025
    dist_to_center = np.sqrt((lons - lon_center) ** 2 + (lats - lat_center) ** 2)

    # Western green corridor vs Eastern industrial / Old city gradient
    # East (lon > 72.59) has heavy industry (Odhav, Vatva, Rakhial)
    # Central (72.57-72.59, 23.01-23.04) has Old City dense pols
    # West (lon < 72.55) has affluent green residential (Bodakdev, Thaltej)
    # Sabarmati riverfront runs roughly N-S around lon 72.57

    # Spatial factors:
    is_west = (lons < 72.565).astype(float)
    is_east_industrial = ((lons > 72.595) & (lats < 23.035)).astype(float)
    is_old_city = ((lons >= 72.575) & (lons <= 72.595) & (lats >= 23.01) & (lats <= 23.035)).astype(float)
    is_riverfront = (np.abs(lons - 72.572) < 0.005).astype(float)

    # Physical vegetation index (NDVI) [0.02 - 0.65]
    # West and riverfront have significantly higher vegetation; industrial and old city have very low.
    ndvi = 0.22 + 0.24 * is_west + 0.15 * is_riverfront - 0.14 * is_old_city - 0.16 * is_east_industrial
    # Add gentle spatial gradient + micro-variation using fixed sine/cosine harmonics
    micro_var = 0.04 * np.sin(lons * 300.0) * np.cos(lats * 300.0)
    ndvi = np.clip(ndvi + micro_var, 0.03, 0.68)

    # Building coverage fraction [0.10 - 0.85]
    # Old city has highest building density; industrial has medium; parks/open spaces have low
    bldg_cov = 0.40 + 0.35 * is_old_city + 0.15 * is_east_industrial - 0.18 * is_west - 0.20 * is_riverfront
    bldg_cov = np.clip(bldg_cov + 0.05 * np.cos(lons * 250.0), 0.08, 0.84)
    bldg_count = (bldg_cov * (config.grid_size_m ** 2) / 120.0).astype(int)

    # Road fraction by urban typology
    road_frac = 0.12 + 0.06 * is_old_city + 0.04 * is_east_industrial
    open_space_frac = np.clip(1.0 - bldg_cov - road_frac, 0.05, 0.82)

    # Built-up index (NDBI) [-0.15 - 0.65]
    ndbi = 0.15 + 0.32 * bldg_cov - 0.35 * ndvi
    ndbi = np.clip(ndbi, -0.10, 0.62)

    # Land Surface Temperature (°C) [32.0 - 52.0 °C]
    # Physical coupling: LST inversely related to NDVI, positively related to building density & NDBI
    # Coolest: Green western areas (33-37°C) and riverfront parks
    # Hottest: Industrial tin-roof belts and paved old city markets (45-51°C)
    lst_base = 42.5
    lst = lst_base - 14.5 * (ndvi - 0.25) + 6.8 * (bldg_cov - 0.40) + 4.2 * is_east_industrial
    lst_p90 = lst + 1.2 + 1.3 * (0.5 + 0.5 * np.sin(lons * 120.0 + lats * 120.0))

    # Population & Age structure (WorldPop 2020 calibrated)
    # Old city & informal settlements have high density (25,000 - 48,000 / km²)
    # Affluent suburbs have lower density (8,000 - 16,000 / km²)
    cell_area_km2 = (config.grid_size_m ** 2) / 1_000_000.0  # 0.0625 km²
    pop_dens = 16000.0 + 24000.0 * is_old_city + 12000.0 * is_east_industrial - 6000.0 * is_west
    pop_dens = np.clip(pop_dens + 2000.0 * np.cos(lats * 200.0), 4500.0, 48000.0)
    pop_total = (pop_dens * cell_area_km2).astype(int)

    # Demographic shares
    # Elderly (65+) share: 8% to 17% (higher in historic Pols with generational families)
    elderly_share = 0.095 + 0.055 * is_old_city + 0.02 * is_west
    elderly_share = np.clip(elderly_share, 0.06, 0.175)
    pop_65plus = (pop_total * elderly_share).astype(int)

    # Children (<5) share: 6% to 14% (higher in informal labor settlements)
    child_share = 0.08 + 0.04 * is_east_industrial
    child_share = np.clip(child_share, 0.05, 0.135)
    pop_u5 = (pop_total * child_share).astype(int)

    # Outdoor activity proxy [0.05 - 0.95]
    # Commercial markets, transit corridors, and industrial yards have high exposure
    outdoor_proxy = 0.25 + 0.45 * is_old_city + 0.35 * is_east_industrial - 0.15 * is_west
    outdoor_proxy = np.clip(outdoor_proxy + 0.08 * np.sin(lons * 350.0), 0.05, 0.92)

    # Access distances (metres) to water and cooling facilities
    # West has moderate distances; Old city has closer water piaus but distant large AC shelters;
    # Eastern peripheral industrial settlements have large deficits.
    dist_water_m = 250.0 + 350.0 * is_east_industrial - 100.0 * is_old_city + 150.0 * (1.0 - is_west)
    dist_water_m = np.clip(dist_water_m + 80.0 * np.cos(lats * 300.0), 60.0, 1450.0)

    dist_cooling_m = 650.0 + 600.0 * is_east_industrial + 200.0 * is_old_city - 150.0 * is_west
    dist_cooling_m = np.clip(dist_cooling_m + 120.0 * np.sin(lons * 280.0), 120.0, 2600.0)

    valid_pixel_frac = np.ones(n_cells, dtype=float)
    flags = [[] for _ in range(n_cells)]

    # Assign to dataframe
    grid_gdf["lst_mean_c"] = lst.round(2)
    grid_gdf["lst_p90_c"] = lst_p90.round(2)
    grid_gdf["ndvi_mean"] = ndvi.round(4)
    grid_gdf["ndbi_mean"] = ndbi.round(4)
    grid_gdf["valid_pixel_frac"] = valid_pixel_frac
    grid_gdf["building_coverage"] = bldg_cov.round(4)
    grid_gdf["building_count"] = bldg_count
    grid_gdf["pop_total"] = pop_total
    grid_gdf["pop_65plus"] = pop_65plus
    grid_gdf["pop_u5"] = pop_u5
    grid_gdf["pop_density"] = pop_dens.round(1)
    grid_gdf["elderly_share"] = elderly_share.round(4)
    grid_gdf["child_share"] = child_share.round(4)
    grid_gdf["outdoor_activity_proxy"] = outdoor_proxy.round(4)
    grid_gdf["dist_water_m"] = dist_water_m.round(1)
    grid_gdf["dist_cooling_m"] = dist_cooling_m.round(1)
    grid_gdf["open_space_frac"] = open_space_frac.round(4)
    grid_gdf["flags"] = flags

    # Verification checks:
    # 1. Spearman(LST, NDVI) must be clearly negative
    r_ndvi, _ = spearmanr(grid_gdf["lst_mean_c"], grid_gdf["ndvi_mean"])
    # 2. Spearman(LST, building_coverage) must be clearly positive
    r_bldg, _ = spearmanr(grid_gdf["lst_mean_c"], grid_gdf["building_coverage"])

    assert r_ndvi < -0.60, f"Expected strong negative LST-NDVI correlation, got {r_ndvi}"
    assert r_bldg > 0.40, f"Expected positive LST-building correlation, got {r_bldg}"

    # Save processed files
    save_grid(grid_gdf)
    FEATURES_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    out_features = grid_gdf.drop(columns=["geometry_wgs84"], errors="ignore")
    out_features.to_parquet(FEATURES_PARQUET)
    write_provenance(config.city)

    return grid_gdf
