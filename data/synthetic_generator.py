"""
TERRA07 Heat-Risk Intelligence - Synthetic Geospatial Data Generator
Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale

Generates realistic, physically-coherent human-scale geospatial microclimate and urban morphology
data for a benchmark heatwave-prone city (Ahmedabad Metropolitan Area, Gujarat, India).

Features:
- 40 distinct wards/micro-neighborhoods across 7 diverse urban typologies:
  1. Dense Commercial Core (Ashram Rd, CG Rd, Navrangpura)
  2. Old City Historic Quarter / Pols (Manek Chowk, Kalupur, Khadia, Astodia)
  3. Industrial Belt (Vatva GIDC, Naroda, Odhav, Rakhial)
  4. Informal Settlements / Corrugated Tin Roof Clusters (Behrampura, Danilimda, Chandola)
  5. Affluent Green Residential Suburbs (Bodakdev, Satellite, Vastrapur, Thaltej)
  6. Transit Corridors & Arterial Spines (SG Highway, Ring Road, BRTS Mega-Terminals)
  7. Urban Parks & Riverfront Green/Blue Lungs (Sabarmati Riverfront, Parimal, Kankaria Lake)
- 150 realistic street segments with start/end node coordinates, street names, street width,
  tree canopy shading ratio (0.0 to 0.9), surface material, solar orientation, and pedestrian volume.
- 60 cooling infrastructure assets + 6 major apex heatstroke hospitals:
  - 26 Cooling Centers (libraries, community halls, AC transit hubs, hospitals, heritage dharamshalas)
  - 34 Hydration & Misting Kiosks (RO water ATMs, misting fans, chabutro drinking points)
  - 6 Apex Emergency Hospitals with dedicated Heat ICU capacity
- Deterministic and physically coupled microclimate equations (LST, Tmrt, SVF, Albedo, NDVI, NDBI).
- Exports full datasets to data/city_data.json and data/city_geojson.json, plus individual layer GeoJSONs.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# =============================================================================
# 1. GEODETIC & PHYSICAL FORMULAE HELPERS
# =============================================================================

EARTH_RADIUS_METERS = 6371000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth surface in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the forward azimuth / bearing in degrees from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def bearing_to_cardinal_aspect(bearing_deg: float) -> Tuple[str, str]:
    """Convert azimuth angle to solar aspect orientation and cardinal axis."""
    normalized = bearing_deg % 180.0  # Street orientation is bidirectional
    if 22.5 <= normalized < 67.5:
        return "NE-SW", "Diagonal (NE-SW)"
    elif 67.5 <= normalized < 112.5:
        return "E-W", "East-West (High Solar Gain)"
    elif 112.5 <= normalized < 157.5:
        return "NW-SE", "Diagonal (NW-SE)"
    else:
        return "N-S", "North-South (Midday Shadowing)"


def calculate_sky_view_factor(aspect_ratio_h_w: float) -> float:
    """
    Estimate Sky View Factor (SVF) from building canyon aspect ratio (H/W).
    SVF = cos(arctan(2 * H / W)).
    SVF approaches 1.0 in open areas, and 0.15-0.30 in deep urban canyons.
    """
    h_w = max(0.05, aspect_ratio_h_w)
    theta = math.atan(2.0 * h_w)
    svf = math.cos(theta)
    return round(max(0.15, min(0.98, svf)), 3)


def calculate_surface_temperature(
    ambient_c: float,
    albedo: float,
    shade_ratio: float,
    solar_irradiance_wm2: float = 950.0,
) -> float:
    """
    Physically modeled street surface temperature under peak solar irradiance:
    T_surf = T_ambient + Delta_T_radiation - Delta_T_shade
    """
    solar_gain_factor = (1.0 - albedo) * (solar_irradiance_wm2 / 950.0)
    unshaded_heating = solar_gain_factor * 18.5  # up to ~18.5C above ambient on dark asphalt
    shade_cooling = shade_ratio * (unshaded_heating + 3.5)
    t_surf = ambient_c + unshaded_heating - shade_cooling
    return round(float(t_surf), 1)


def calculate_mean_radiant_temperature(
    ambient_c: float,
    shade_ratio: float,
    svf: float,
    solar_irradiance_wm2: float = 950.0,
) -> float:
    """
    Physically modeled Mean Radiant Temperature (Tmrt) at 1.5m pedestrian height.
    Tmrt = T_ambient + (1.0 - 0.85 * shade) * sqrt(SVF) * 16.5 * (I / 950)
    """
    irradiance_ratio = solar_irradiance_wm2 / 950.0
    direct_solar_dose = (1.0 - 0.85 * shade_ratio) * math.sqrt(svf) * 16.5 * irradiance_ratio
    t_mrt = ambient_c + direct_solar_dose
    return round(float(t_mrt), 1)


def calculate_pedestrian_heat_risk(
    tmrt_c: float,
    tsurf_c: float,
    shade_ratio: float,
    svf: float,
) -> Tuple[float, str]:
    """
    Calculate Human-Scale Pedestrian Heat Risk Score (0-100) and assign RiskTier.
    """
    tmrt_score = max(0.0, min(100.0, (tmrt_c - 35.0) / (62.0 - 35.0) * 100.0))
    tsurf_score = max(0.0, min(100.0, (tsurf_c - 34.0) / (60.0 - 34.0) * 100.0))
    exposure_score = (1.0 - shade_ratio) * 100.0
    svf_score = svf * 100.0

    risk = 0.40 * tmrt_score + 0.30 * tsurf_score + 0.20 * exposure_score + 0.10 * svf_score
    risk = round(max(5.0, min(99.0, risk)), 1)

    if risk < 35.0:
        tier = "Low"
    elif risk < 60.0:
        tier = "Moderate"
    elif risk < 75.0:
        tier = "High"
    else:
        tier = "Extreme"

    return risk, tier


# =============================================================================
# 2. BENCHMARK CITY METEOROLOGY & URBAN TYPOLOGY TEMPLATES
# =============================================================================

BENCHMARK_CITY = {
    "city_name": "Ahmedabad Metropolitan Area",
    "country": "India",
    "state": "Gujarat",
    "climate_zone": "Hot Semi-Arid (Köppen BSh)",
    "scenario_name": "Ahmedabad May Red Alert Heatwave Baseline",
    "baseline_meteorology": {
        "ambient_air_temp_celsius": 44.5,
        "relative_humidity_pct": 28.0,
        "peak_solar_irradiance_wm2": 950.0,
        "wind_speed_mps": 2.2,
        "atmospheric_pressure_hpa": 1008.0,
        "heat_index_celsius": 52.8,
        "wbgt_celsius": 33.6,
        "alert_level": "Red Alert (Heatwave Emergency)",
    },
    "bounds": {
        "min_lat": 22.955,
        "max_lat": 23.095,
        "min_lon": 72.485,
        "max_lon": 72.665,
        "center_lat": 23.0225,
        "center_lon": 72.5714,
    },
}

TYPOLOGY_SPECS = {
    "dense_commercial": {
        "name": "Dense Commercial Core",
        "description": "High-density retail and corporate corridors with mid-rise concrete and glass facades, high traffic emissions, and AC heat rejection.",
        "ndvi_range": (0.16, 0.25),
        "ndbi_range": (0.46, 0.58),
        "albedo_range": (0.16, 0.22),
        "canopy_pct_range": (12.0, 20.0),
        "impervious_pct_range": (78.0, 88.0),
        "base_lst_range": (42.5, 44.5),
        "pop_density_range": (16000, 24000),
        "elderly_pct_range": (11.0, 15.0),
        "children_pct_range": (8.0, 11.0),
        "outdoor_workers_pct_range": (20.0, 32.0),
        "slum_households_pct_range": (6.0, 14.0),
        "poverty_ratio_pct_range": (12.0, 20.0),
        "ac_penetration_pct_range": (62.0, 78.0),
        "hospitals_count_range": (3, 6),
        "dominant_heat_drivers": [
            "Anthropogenic vehicular & HVAC waste heat emissions",
            "High impervious pavement fraction",
            "Solar radiation reflection from glass & masonry facades",
            "Restricted street-level wind dispersion",
        ],
        "top_recommended_interventions": [
            "High-albedo cool pavement retrofits along parking and sidewalks",
            "Green transit corridor shaded pergolas",
            "Rooftop solar canopy heat shielding",
            "Mandatory HVAC thermal plume dispersion baffles",
        ],
    },
    "old_city_pols": {
        "name": "Old City Historic Quarter (Pols)",
        "description": "UNESCO World Heritage historic precinct characterized by tightly packed 3-4 story havelis, micro-alleys, deep canyon shadows, and severe night heat trapping.",
        "ndvi_range": (0.08, 0.15),
        "ndbi_range": (0.58, 0.70),
        "albedo_range": (0.18, 0.26),
        "canopy_pct_range": (4.0, 10.0),
        "impervious_pct_range": (88.0, 96.0),
        "base_lst_range": (43.0, 45.8),
        "pop_density_range": (42000, 58000),
        "elderly_pct_range": (16.0, 23.0),
        "children_pct_range": (10.0, 13.0),
        "outdoor_workers_pct_range": (32.0, 46.0),
        "slum_households_pct_range": (20.0, 36.0),
        "poverty_ratio_pct_range": (30.0, 44.0),
        "ac_penetration_pct_range": (14.0, 26.0),
        "hospitals_count_range": (2, 4),
        "dominant_heat_drivers": [
            "Severe street canyon heat entrapment and low ventilation",
            "Aging demographic with high cardiovascular vulnerability",
            "High building thermal mass re-radiating heat into night hours",
            "Extremely limited open ground for mature tree root zones",
        ],
        "top_recommended_interventions": [
            "Micro-nozzle misting lines in pedestrian pol chowks",
            "Traditional lime-wash high-reflectance roof coatings",
            "Heritage dharamshala emergency cool-room activation",
            "Community water piau and hydration network densification",
        ],
    },
    "industrial_belt": {
        "name": "Industrial Belt & Low-Albedo Logistics",
        "description": "Expansive industrial estates with vast uninsulated corrugated metal sheds, heavy diesel logistics, low surface albedo, and minimal canopy.",
        "ndvi_range": (0.05, 0.12),
        "ndbi_range": (0.65, 0.80),
        "albedo_range": (0.10, 0.16),
        "canopy_pct_range": (2.0, 6.0),
        "impervious_pct_range": (90.0, 98.0),
        "base_lst_range": (46.8, 49.8),
        "pop_density_range": (8000, 15000),
        "elderly_pct_range": (5.0, 8.0),
        "children_pct_range": (7.0, 10.0),
        "outdoor_workers_pct_range": (58.0, 76.0),
        "slum_households_pct_range": (35.0, 50.0),
        "poverty_ratio_pct_range": (40.0, 55.0),
        "ac_penetration_pct_range": (6.0, 15.0),
        "hospitals_count_range": (1, 3),
        "dominant_heat_drivers": [
            "Extensive low-albedo asphalt yards and metal fabrication sheds",
            "Industrial kiln & boiler secondary heat discharges",
            "Predominance of outdoor shift laborers exposed during peak hours",
            "Severe vegetation deficit (NDVI < 0.10)",
        ],
        "top_recommended_interventions": [
            "Mandatory factory cool-roof elastomeric thermal barriers",
            "Miyawaki dense pocket forests along industrial perimeter buffers",
            "Occupational heat-stress rest sheds with active misting",
            "Shift-rescheduling and mandatory 12:00-15:00 outdoor work halts",
        ],
    },
    "informal_settlements": {
        "name": "Informal Settlements & Tin-Roof Clusters",
        "description": "High-density informal bastis with uninsulated corrugated galvanized iron/tin roofs, narrow unpaved alleys, extreme socioeconomic vulnerability, and lack of AC.",
        "ndvi_range": (0.04, 0.10),
        "ndbi_range": (0.55, 0.72),
        "albedo_range": (0.12, 0.18),
        "canopy_pct_range": (2.0, 6.0),
        "impervious_pct_range": (86.0, 95.0),
        "base_lst_range": (45.6, 49.2),
        "pop_density_range": (38000, 54000),
        "elderly_pct_range": (8.0, 12.0),
        "children_pct_range": (14.0, 19.0),
        "outdoor_workers_pct_range": (54.0, 72.0),
        "slum_households_pct_range": (74.0, 96.0),
        "poverty_ratio_pct_range": (58.0, 76.0),
        "ac_penetration_pct_range": (2.0, 6.0),
        "hospitals_count_range": (1, 2),
        "dominant_heat_drivers": [
            "Corrugated metal tin roofs radiating excessive indoor heat (50°C+)",
            "High concentration of children and informal daily-wage laborers",
            "Minimal household cooling capacity and unreliable power supply",
            "Overcrowded living quarters with deficient natural cross-ventilation",
        ],
        "top_recommended_interventions": [
            "Rapid municipal cool-roof paint program (ModRoof / solar reflective paint)",
            "Emergency community hall air-cooled day shelters",
            "Mobile water tankers and oral rehydration salt (ORS) distribution hubs",
            "Shaded communal breezeway retrofits with green netting",
        ],
    },
    "affluent_suburbs": {
        "name": "Affluent Green Residential Suburbs",
        "description": "Master-planned residential neighborhoods with wide tree-lined boulevards, lush private gardens, high AC adoption, low population density, and high NDVI.",
        "ndvi_range": (0.42, 0.68),
        "ndbi_range": (0.14, 0.26),
        "albedo_range": (0.22, 0.32),
        "canopy_pct_range": (36.0, 56.0),
        "impervious_pct_range": (42.0, 55.0),
        "base_lst_range": (35.5, 38.5),
        "pop_density_range": (9000, 16000),
        "elderly_pct_range": (14.0, 20.0),
        "children_pct_range": (7.0, 10.0),
        "outdoor_workers_pct_range": (6.0, 12.0),
        "slum_households_pct_range": (1.0, 5.0),
        "poverty_ratio_pct_range": (3.0, 8.0),
        "ac_penetration_pct_range": (76.0, 92.0),
        "hospitals_count_range": (4, 8),
        "dominant_heat_drivers": [
            "Residential air-conditioning compressor thermal exhaust plumes",
            "Wide suburban road carriage ways absorbing solar radiation",
            "Aging demographic in gated residential communities",
        ],
        "top_recommended_interventions": [
            "Permeable pavement retrofits for stormwater and evaporative cooling",
            "Canopy density preservation and mature neem/gulmohar care",
            "Solar canopy integration over open residential carports",
            "Neighborhood emergency hydration check-in stations",
        ],
    },
    "transit_corridors": {
        "name": "Transit Corridors & Arterial Hubs",
        "description": "Multi-modal transport arteries (BRTS Janmarg, Metro, Ring Roads) with heavy commuter foot-traffic, high asphalt surface area, and concrete medians.",
        "ndvi_range": (0.12, 0.22),
        "ndbi_range": (0.50, 0.64),
        "albedo_range": (0.11, 0.16),
        "canopy_pct_range": (8.0, 18.0),
        "impervious_pct_range": (84.0, 94.0),
        "base_lst_range": (44.0, 47.0),
        "pop_density_range": (12000, 20000),
        "elderly_pct_range": (9.0, 13.0),
        "children_pct_range": (8.0, 12.0),
        "outdoor_workers_pct_range": (30.0, 48.0),
        "slum_households_pct_range": (12.0, 25.0),
        "poverty_ratio_pct_range": (18.0, 32.0),
        "ac_penetration_pct_range": (35.0, 55.0),
        "hospitals_count_range": (2, 5),
        "dominant_heat_drivers": [
            "Extensive black asphalt multi-lane carriage ways",
            "Concentrated bus, auto-rickshaw, and vehicle exhaust heat",
            "Unshaded pedestrian road crossings and bus queue bottlenecks",
            "High solar exposure on concrete pedestrian islands",
        ],
        "top_recommended_interventions": [
            "Continuous solar-shaded pedestrian pergolas along transit stations",
            "Air-conditioned transit waiting lounges open to general public",
            "High-capacity chilled water ATMs at all BRTS and Metro stops",
            "Reflective asphalt seal coats along bus lanes",
        ],
    },
    "urban_parks": {
        "name": "Urban Parks & Riverfront Green/Blue Lungs",
        "description": "Major public botanical gardens, lake parks, and landscaped riverfront buffers providing strong urban cool island effects and recreational shade.",
        "ndvi_range": (0.60, 0.82),
        "ndbi_range": (-0.15, 0.10),
        "albedo_range": (0.24, 0.35),
        "canopy_pct_range": (65.0, 88.0),
        "impervious_pct_range": (10.0, 22.0),
        "base_lst_range": (32.0, 35.2),
        "pop_density_range": (1500, 4500),
        "elderly_pct_range": (12.0, 18.0),
        "children_pct_range": (9.0, 14.0),
        "outdoor_workers_pct_range": (10.0, 18.0),
        "slum_households_pct_range": (2.0, 8.0),
        "poverty_ratio_pct_range": (5.0, 12.0),
        "ac_penetration_pct_range": (40.0, 65.0),
        "hospitals_count_range": (1, 3),
        "dominant_heat_drivers": [
            "Solar radiation exposure along open hardscape promenades",
            "High daytime visitor influx during heatwave emergencies",
        ],
        "top_recommended_interventions": [
            "Expansion of deep canopy tree groves along riverfront edge",
            "Public misting arches along active recreational walking trails",
            "Free potable drinking water fountains at 200m intervals",
            "Nighttime urban cooling sanctuary extension hours",
        ],
    },
}


# =============================================================================
# 3. WARD SPECIFICATIONS (40 WARDS)
# =============================================================================

RAW_WARD_SPECS = [
    # 1. Dense Commercial Core (6 wards)
    {"id": "WARD_01", "name": "Navrangpura Commercial Core", "zone": "West Zone", "typology": "dense_commercial", "area_km2": 3.8, "center": (23.0360, 72.5580), "radius_deg": (0.009, 0.010)},
    {"id": "WARD_02", "name": "CG Road Retail Promenade", "zone": "West Zone", "typology": "dense_commercial", "area_km2": 2.9, "center": (23.0285, 72.5565), "radius_deg": (0.008, 0.008)},
    {"id": "WARD_03", "name": "Ashram Road Business District", "zone": "West Zone", "typology": "dense_commercial", "area_km2": 3.4, "center": (23.0330, 72.5710), "radius_deg": (0.009, 0.007)},
    {"id": "WARD_04", "name": "Usmanpura Corporate Sector", "zone": "West Zone", "typology": "dense_commercial", "area_km2": 2.7, "center": (23.0480, 72.5680), "radius_deg": (0.007, 0.008)},
    {"id": "WARD_05", "name": "Ellisbridge Financial Strip", "zone": "Central-West Zone", "typology": "dense_commercial", "area_km2": 3.1, "center": (23.0210, 72.5690), "radius_deg": (0.008, 0.008)},
    {"id": "WARD_06", "name": "Mithakhali Corporate Precinct", "zone": "West Zone", "typology": "dense_commercial", "area_km2": 2.5, "center": (23.0270, 72.5630), "radius_deg": (0.007, 0.007)},

    # 2. Old City Historic Quarter (Pols) (7 wards)
    {"id": "WARD_07", "name": "Manek Chowk & Mandvi Pol", "zone": "Central Zone", "typology": "old_city_pols", "area_km2": 1.6, "center": (23.0245, 72.5875), "radius_deg": (0.006, 0.006)},
    {"id": "WARD_08", "name": "Kalupur Swaminarayan Precinct", "zone": "Central Zone", "typology": "old_city_pols", "area_km2": 2.1, "center": (23.0305, 72.5970), "radius_deg": (0.007, 0.007)},
    {"id": "WARD_09", "name": "Khadia Heritage Living Pols", "zone": "Central Zone", "typology": "old_city_pols", "area_km2": 1.9, "center": (23.0215, 72.5930), "radius_deg": (0.006, 0.006)},
    {"id": "WARD_10", "name": "Astodia & Raipur Darwaja Sector", "zone": "Central Zone", "typology": "old_city_pols", "area_km2": 2.4, "center": (23.0160, 72.5940), "radius_deg": (0.007, 0.007)},
    {"id": "WARD_11", "name": "Dhalgarwad & Teen Darwaza Bazaar", "zone": "Central Zone", "typology": "old_city_pols", "area_km2": 1.5, "center": (23.0255, 72.5820), "radius_deg": (0.005, 0.006)},
    {"id": "WARD_12", "name": "Dariapur Historic Walled Sector", "zone": "Central Zone", "typology": "old_city_pols", "area_km2": 2.2, "center": (23.0370, 72.5920), "radius_deg": (0.007, 0.007)},
    {"id": "WARD_13", "name": "Shahpur Delhi Darwaja Sector", "zone": "Central Zone", "typology": "old_city_pols", "area_km2": 2.0, "center": (23.0385, 72.5815), "radius_deg": (0.006, 0.007)},

    # 3. Industrial Belt (Low Albedo & Metal Sheds) (6 wards)
    {"id": "WARD_14", "name": "Vatva GIDC Phase-I & II", "zone": "South Zone", "typology": "industrial_belt", "area_km2": 6.8, "center": (22.9650, 72.6320), "radius_deg": (0.012, 0.014)},
    {"id": "WARD_15", "name": "Vatva GIDC Phase-IV Chemical Complex", "zone": "South Zone", "typology": "industrial_belt", "area_km2": 5.9, "center": (22.9560, 72.6450), "radius_deg": (0.011, 0.013)},
    {"id": "WARD_16", "name": "Naroda Industrial Estate North", "zone": "East Zone", "typology": "industrial_belt", "area_km2": 7.2, "center": (23.0780, 72.6580), "radius_deg": (0.013, 0.015)},
    {"id": "WARD_17", "name": "Odhav GIDC Heavy Machinery Belt", "zone": "East Zone", "typology": "industrial_belt", "area_km2": 6.4, "center": (23.0290, 72.6520), "radius_deg": (0.012, 0.014)},
    {"id": "WARD_18", "name": "Rakhial Textile Mills & Foundries", "zone": "East Zone", "typology": "industrial_belt", "area_km2": 4.5, "center": (23.0180, 72.6240), "radius_deg": (0.010, 0.011)},
    {"id": "WARD_19", "name": "Amraiwadi Industrial Logistics Hub", "zone": "East Zone", "typology": "industrial_belt", "area_km2": 4.8, "center": (23.0030, 72.6310), "radius_deg": (0.010, 0.012)},

    # 4. Informal Settlements & Tin-Roof Clusters (6 wards)
    {"id": "WARD_20", "name": "Behrampura High-Density Tin Roof Basti", "zone": "South Zone", "typology": "informal_settlements", "area_km2": 3.6, "center": (22.9980, 72.5850), "radius_deg": (0.009, 0.009)},
    {"id": "WARD_21", "name": "Danilimda Chawl & Tannery Workers Colony", "zone": "South Zone", "typology": "informal_settlements", "area_km2": 4.2, "center": (22.9900, 72.5930), "radius_deg": (0.010, 0.010)},
    {"id": "WARD_22", "name": "Chandola Lake Periphery Settlement", "zone": "South Zone", "typology": "informal_settlements", "area_km2": 3.9, "center": (22.9810, 72.6020), "radius_deg": (0.009, 0.010)},
    {"id": "WARD_23", "name": "Ramol Informal Migrant Bastis", "zone": "East Zone", "typology": "informal_settlements", "area_km2": 4.7, "center": (22.9920, 72.6480), "radius_deg": (0.011, 0.011)},
    {"id": "WARD_24", "name": "Meghaninagar Railway Bastis", "zone": "North Zone", "typology": "informal_settlements", "area_km2": 3.5, "center": (23.0560, 72.6120), "radius_deg": (0.009, 0.009)},
    {"id": "WARD_25", "name": "Gomtipur Old Mill Workers Chawls", "zone": "East Zone", "typology": "informal_settlements", "area_km2": 3.2, "center": (23.0190, 72.6100), "radius_deg": (0.008, 0.008)},

    # 5. Affluent Green Residential Suburbs (7 wards)
    {"id": "WARD_26", "name": "Bodakdev Canopy Residential Enclave", "zone": "North West Zone", "typology": "affluent_suburbs", "area_km2": 5.4, "center": (23.0420, 72.5150), "radius_deg": (0.012, 0.013)},
    {"id": "WARD_27", "name": "Satellite Green Residential Avenues", "zone": "South West Zone", "typology": "affluent_suburbs", "area_km2": 4.8, "center": (23.0230, 72.5260), "radius_deg": (0.011, 0.012)},
    {"id": "WARD_28", "name": "Vastrapur Garden Suburb", "zone": "North West Zone", "typology": "affluent_suburbs", "area_km2": 4.1, "center": (23.0350, 72.5320), "radius_deg": (0.010, 0.011)},
    {"id": "WARD_29", "name": "Thaltej Mature Canopy Suburb", "zone": "North West Zone", "typology": "affluent_suburbs", "area_km2": 6.2, "center": (23.0580, 72.5080), "radius_deg": (0.013, 0.014)},
    {"id": "WARD_30", "name": "Ambawadi Gulmohar Colony", "zone": "West Zone", "typology": "affluent_suburbs", "area_km2": 3.5, "center": (23.0190, 72.5480), "radius_deg": (0.009, 0.010)},
    {"id": "WARD_31", "name": "Gulbai Tekra Residential District", "zone": "West Zone", "typology": "affluent_suburbs", "area_km2": 2.8, "center": (23.0270, 72.5470), "radius_deg": (0.008, 0.008)},
    {"id": "WARD_32", "name": "Paldi Riverside Residential Enclave", "zone": "West Zone", "typology": "affluent_suburbs", "area_km2": 3.7, "center": (23.0080, 72.5620), "radius_deg": (0.009, 0.009)},

    # 6. Transit Corridors & Arterial Hubs (4 wards)
    {"id": "WARD_33", "name": "SG Highway Commercial Transit Spine", "zone": "North West Zone", "typology": "transit_corridors", "area_km2": 6.5, "center": (23.0480, 72.4980), "radius_deg": (0.014, 0.010)},
    {"id": "WARD_34", "name": "132 Feet Ring Road Multi-Modal Corridor", "zone": "West Zone", "typology": "transit_corridors", "area_km2": 5.2, "center": (23.0390, 72.5380), "radius_deg": (0.013, 0.009)},
    {"id": "WARD_35", "name": "Kalupur Central Railway Station Concourse", "zone": "Central Zone", "typology": "transit_corridors", "area_km2": 2.3, "center": (23.0280, 72.6030), "radius_deg": (0.007, 0.007)},
    {"id": "WARD_36", "name": "Ranip BRTS & Regional Bus Mega-Terminal", "zone": "North Zone", "typology": "transit_corridors", "area_km2": 3.4, "center": (23.0750, 72.5780), "radius_deg": (0.009, 0.009)},

    # 7. Urban Parks & Riverfront Green/Blue Lungs (4 wards)
    {"id": "WARD_37", "name": "Sabarmati Riverfront Promenade West", "zone": "Central-West Zone", "typology": "urban_parks", "area_km2": 2.6, "center": (23.0290, 72.5730), "radius_deg": (0.014, 0.005)},
    {"id": "WARD_38", "name": "Sabarmati Riverfront East & Flower Park", "zone": "Central Zone", "typology": "urban_parks", "area_km2": 2.8, "center": (23.0260, 72.5780), "radius_deg": (0.014, 0.005)},
    {"id": "WARD_39", "name": "Kankaria Lake Ecological Park & Zoo", "zone": "South Zone", "typology": "urban_parks", "area_km2": 3.5, "center": (23.0060, 72.6010), "radius_deg": (0.009, 0.009)},
    {"id": "WARD_40", "name": "Parimal Garden & Law Garden Urban Forest", "zone": "West Zone", "typology": "urban_parks", "area_km2": 2.4, "center": (23.0180, 72.5560), "radius_deg": (0.007, 0.007)},
]


def generate_ward_polygon(center_lat: float, center_lon: float, r_lat: float, r_lon: float, num_pts: int = 14) -> List[List[float]]:
    """Generate a realistic, convex polygon boundary ring around center coordinates."""
    coords = []
    for i in range(num_pts):
        angle = 2.0 * math.pi * i / num_pts
        jitter = 1.0 + 0.12 * math.sin(3.0 * angle) - 0.08 * math.cos(2.0 * angle)
        lat = center_lat + r_lat * jitter * math.sin(angle)
        lon = center_lon + r_lon * jitter * math.cos(angle)
        coords.append([round(lon, 6), round(lat, 6)])

    coords.append(coords[0])  # Close ring
    return coords


# =============================================================================
# 4. DATA MODEL CLASS IMPLEMENTATION
# =============================================================================

@dataclass
class WardData:
    ward_id: str
    ward_name: str
    zone: str
    typology_key: str
    typology_name: str
    area_km2: float
    heat_risk_score: float
    risk_level: str
    risk_percentile: float
    environmental: Dict[str, Any]
    demographics: Dict[str, Any]
    adaptive_capacity: Dict[str, Any]
    dominant_heat_drivers: List[str]
    top_recommended_interventions: List[str]
    geometry: Dict[str, Any]
    lat: float
    lon: float


@dataclass
class IntersectionNode:
    node_id: str
    name: str
    lat: float
    lon: float
    ward_id: str
    has_hydration_kiosk: bool
    has_cooling_center: bool


@dataclass
class StreetData:
    street_id: str
    street_name: str
    ward_id: str
    ward_name: str
    length_meters: float
    mean_radiant_temp_celsius: float
    surface_temp_celsius: float
    shade_ratio: float
    sky_view_factor: float
    aspect_ratio_h_w: float
    pedestrian_heat_risk: float
    risk_level: str
    pedestrian_volume: str
    tree_count: int
    has_water_misting: bool
    geometry: Dict[str, Any]
    # Extra physical attributes
    start_node_id: str
    end_node_id: str
    start_coordinates: Dict[str, float]
    end_coordinates: Dict[str, float]
    street_width_meters: float
    surface_material: str
    surface_albedo: float
    tree_canopy_shading_ratio: float
    solar_orientation: str
    solar_aspect_label: str
    azimuth_degrees: float
    pedestrian_hourly_volume: int
    speed_limit_kmh: int


@dataclass
class CoolingCenterData:
    center_id: str
    name: str
    facility_type: str
    ward_id: str
    ward_name: str
    address: str
    coordinates: Dict[str, float]
    distance_meters: float
    walking_time_minutes: int
    operating_hours: str
    capacity_persons: int
    current_occupancy: int
    indoor_temp_celsius: float
    has_medical_staff: bool
    has_backup_generator: bool
    wheelchair_accessible: bool
    phone_contact: str
    amenities: List[str]
    status: str
    geometry: Dict[str, Any]


@dataclass
class HydrationPointData:
    point_id: str
    name: str
    water_source_type: str
    ward_id: str
    ward_name: str
    address: str
    coordinates: Dict[str, float]
    distance_meters: float
    flow_rate_liters_per_min: float
    daily_dispensed_liters: int
    status: str
    is_free: bool
    has_chilled_water: bool
    has_misting_fan: bool
    operating_hours: str
    geometry: Dict[str, Any]


# =============================================================================
# 5. CORE SYNTHETIC GENERATOR ENGINE
# =============================================================================

class SyntheticGeospatialGenerator:
    """
    Deterministic Generator for Citywide Human-Scale Microclimate and Heat Vulnerability Data.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        np.random.seed(seed)

        self.city_meta = BENCHMARK_CITY
        self.ambient_temp = self.city_meta["baseline_meteorology"]["ambient_air_temp_celsius"]

        self.wards: List[WardData] = []
        self.nodes: Dict[str, IntersectionNode] = {}
        self.streets: List[StreetData] = []
        self.cooling_centers: List[CoolingCenterData] = []
        self.hydration_points: List[HydrationPointData] = []
        self.hospitals: List[Dict[str, Any]] = []

    def generate_all(self) -> None:
        """Run complete generation pipeline."""
        self._generate_wards()
        self._generate_street_nodes()
        self._generate_streets()
        self._generate_cooling_infrastructure()
        self._generate_hospitals()
        self._link_adaptive_counts_to_wards()

    # -------------------------------------------------------------------------
    # 5.1 Ward Generation
    # -------------------------------------------------------------------------
    def _generate_wards(self) -> None:
        raw_ward_data_list = []

        for spec in RAW_WARD_SPECS:
            w_id = spec["id"]
            w_name = spec["name"]
            zone = spec["zone"]
            t_key = spec["typology"]
            t_spec = TYPOLOGY_SPECS[t_key]
            area = spec["area_km2"]
            c_lat, c_lon = spec["center"]
            r_lat, r_lon = spec["radius_deg"]

            ndvi = round(self.rng.uniform(*t_spec["ndvi_range"]), 3)
            ndbi = round(self.rng.uniform(*t_spec["ndbi_range"]), 3)
            albedo = round(self.rng.uniform(*t_spec["albedo_range"]), 2)
            canopy_pct = round(self.rng.uniform(*t_spec["canopy_pct_range"]), 1)
            impervious_pct = round(self.rng.uniform(*t_spec["impervious_pct_range"]), 1)

            # Physically Coupled Land Surface Temperature (LST)
            lst_mean = 34.0 + 16.5 * ndbi - 12.0 * ndvi - 8.0 * (canopy_pct / 100.0) + 5.0 * (1.0 - albedo)
            lst_mean = round(float(lst_mean) + self.rng.uniform(-0.4, 0.4), 1)
            lst_max = round(lst_mean + self.rng.uniform(2.8, 4.5), 1)
            lst_min = round(lst_mean - self.rng.uniform(2.5, 4.0), 1)

            pop_density = int(self.rng.uniform(*t_spec["pop_density_range"]))
            total_pop = int(pop_density * area)
            elderly_pct = round(self.rng.uniform(*t_spec["elderly_pct_range"]), 1)
            children_pct = round(self.rng.uniform(*t_spec["children_pct_range"]), 1)
            outdoor_workers_pct = round(self.rng.uniform(*t_spec["outdoor_workers_pct_range"]), 1)
            slum_pct = round(self.rng.uniform(*t_spec["slum_households_pct_range"]), 1)
            poverty_pct = round(self.rng.uniform(*t_spec["poverty_ratio_pct_range"]), 1)

            illness_base = (lst_mean - 34.0) * 2.2 + (slum_pct * 0.28) + (outdoor_workers_pct * 0.25)
            baseline_heat_illness_rate = round(max(3.5, illness_base + self.rng.uniform(-2.0, 2.0)), 1)

            ac_penetration_pct = round(self.rng.uniform(*t_spec["ac_penetration_pct_range"]), 1)
            hospitals_count = int(self.rng.randint(*t_spec["hospitals_count_range"]))
            dist_to_hospital = round(self.rng.uniform(350.0, 2800.0) / math.sqrt(max(1, hospitals_count)), 0)
            tree_planting_potential = round(max(5.0, 100.0 - impervious_pct - canopy_pct), 1)

            hazard_score = 0.50 * ((lst_mean - 32.0) / 18.0) + 0.30 * ndbi + 0.20 * (1.0 - albedo)
            exposure_score = (
                0.35 * (pop_density / 55000.0)
                + 0.35 * (outdoor_workers_pct / 75.0)
                + 0.15 * (elderly_pct / 22.0)
                + 0.15 * (children_pct / 18.0)
            )
            vulnerability_score = (
                0.45 * (slum_pct / 90.0)
                + 0.35 * (poverty_pct / 75.0)
                + 0.20 * (1.0 - ac_penetration_pct / 100.0)
            )
            adaptive_score = (
                0.40 * (canopy_pct / 60.0)
                + 0.30 * (ac_penetration_pct / 100.0)
                + 0.30 * (1.0 - min(1.0, dist_to_hospital / 3000.0))
            )

            raw_risk = 100.0 * (
                0.42 * hazard_score
                + 0.36 * (0.5 * exposure_score + 0.5 * vulnerability_score)
                - 0.22 * adaptive_score
            )
            heat_risk_score = round(max(8.0, min(97.5, raw_risk)), 1)

            if heat_risk_score < 35.0:
                risk_tier = "Low"
            elif heat_risk_score < 60.0:
                risk_tier = "Moderate"
            elif heat_risk_score < 75.0:
                risk_tier = "High"
            else:
                risk_tier = "Extreme"

            poly_coords = generate_ward_polygon(c_lat, c_lon, r_lat, r_lon, num_pts=14)
            geom = {
                "type": "Polygon",
                "coordinates": [poly_coords],
            }

            ward_dict = {
                "ward_id": w_id,
                "ward_name": w_name,
                "zone": zone,
                "typology_key": t_key,
                "typology_name": t_spec["name"],
                "area_km2": area,
                "heat_risk_score": heat_risk_score,
                "risk_level": risk_tier,
                "lat": round(c_lat, 6),
                "lon": round(c_lon, 6),
                "environmental": {
                    "mean_lst_celsius": lst_mean,
                    "max_lst_celsius": lst_max,
                    "min_lst_celsius": lst_min,
                    "ndvi_vegetation_index": ndvi,
                    "ndbi_builtup_index": ndbi,
                    "surface_albedo": albedo,
                    "tree_canopy_pct": canopy_pct,
                    "impervious_surface_pct": impervious_pct,
                },
                "demographics": {
                    "total_population": total_pop,
                    "population_density_per_km2": float(pop_density),
                    "elderly_pct": elderly_pct,
                    "children_pct": children_pct,
                    "outdoor_workers_pct": outdoor_workers_pct,
                    "slum_households_pct": slum_pct,
                    "poverty_ratio_pct": poverty_pct,
                    "baseline_heat_illness_rate": baseline_heat_illness_rate,
                },
                "adaptive_capacity": {
                    "ac_penetration_pct": ac_penetration_pct,
                    "cooling_centers_count": 0,
                    "hydration_points_count": 0,
                    "hospitals_and_clinics_count": hospitals_count,
                    "distance_to_nearest_hospital_m": dist_to_hospital,
                    "tree_planting_potential_pct": tree_planting_potential,
                },
                "dominant_heat_drivers": t_spec["dominant_heat_drivers"],
                "top_recommended_interventions": t_spec["top_recommended_interventions"],
                "geometry": geom,
            }
            raw_ward_data_list.append(ward_dict)

        risk_scores = [w["heat_risk_score"] for w in raw_ward_data_list]
        for w in raw_ward_data_list:
            percentile = round((sum(1 for s in risk_scores if s <= w["heat_risk_score"]) / len(risk_scores)) * 100.0, 1)
            w["risk_percentile"] = percentile
            self.wards.append(WardData(**w))

    # -------------------------------------------------------------------------
    # 5.2 Street Network Intersections & Nodes (72 Named Nodes)
    # -------------------------------------------------------------------------
    def _generate_street_nodes(self) -> None:
        node_catalog = [
            ("NODE_NAV_01", "Commerce Six Roads", 23.0380, 72.5550, "WARD_01", True, False),
            ("NODE_NAV_02", "Navrangpura Bus Stand Jn", 23.0360, 72.5610, "WARD_01", False, True),
            ("NODE_NAV_03", "St. Xavier's College Corner", 23.0335, 72.5535, "WARD_01", True, False),
            ("NODE_CG_01", "Swastik Cross Roads", 23.0310, 72.5570, "WARD_02", True, True),
            ("NODE_CG_02", "Panchvati Circle", 23.0250, 72.5560, "WARD_02", False, False),
            ("NODE_CG_03", "Girish Cold Drinks Jn", 23.0275, 72.5565, "WARD_02", True, False),
            ("NODE_ASH_01", "Income Tax Circle (Ashram Rd)", 23.0410, 72.5715, "WARD_03", True, True),
            ("NODE_ASH_02", "Usmanpura Underpass Entry", 23.0470, 72.5695, "WARD_04", False, False),
            ("NODE_ASH_03", "Gandhigram Station Road Jn", 23.0255, 72.5710, "WARD_03", True, False),
            ("NODE_ELL_01", "Ellisbridge Town Hall Circle", 23.0195, 72.5685, "WARD_05", True, True),
            ("NODE_ELL_02", "VS Hospital Gate 1", 23.0165, 72.5700, "WARD_05", False, True),
            ("NODE_MIT_01", "Mithakhali Underpass Jn", 23.0280, 72.5640, "WARD_06", False, False),
            ("NODE_MIT_02", "Law Garden North Gate", 23.0250, 72.5610, "WARD_06", True, False),
            ("NODE_MNK_01", "Manek Chowk Main Chawk", 23.0245, 72.5875, "WARD_07", True, False),
            ("NODE_MNK_02", "Rani no Hajiro Entry", 23.0250, 72.5890, "WARD_07", False, True),
            ("NODE_MNK_03", "Mandvi Pol Entrance Gate", 23.0235, 72.5860, "WARD_07", True, False),
            ("NODE_KAL_01", "Kalupur Swaminarayan Temple Chowk", 23.0310, 72.5975, "WARD_08", True, True),
            ("NODE_KAL_02", "Kalupur Kotni Rang Jn", 23.0295, 72.5950, "WARD_08", False, False),
            ("NODE_KHD_01", "Khadia Char Rasta", 23.0220, 72.5935, "WARD_09", True, True),
            ("NODE_KHD_02", "Bala Hanuman Temple Square", 23.0230, 72.5915, "WARD_09", True, False),
            ("NODE_AST_01", "Astodia Darwaja Circle", 23.0160, 72.5940, "WARD_10", True, False),
            ("NODE_AST_02", "Raipur Chakla Heritage Corner", 23.0185, 72.5960, "WARD_10", False, True),
            ("NODE_DHL_01", "Teen Darwaza Archway", 23.0255, 72.5825, "WARD_11", True, False),
            ("NODE_DHL_02", "Bhadra Plaza South Pavilion", 23.0260, 72.5795, "WARD_11", False, True),
            ("NODE_DAR_01", "Dariapur Darwaja Chowk", 23.0380, 72.5930, "WARD_12", True, False),
            ("NODE_DAR_02", "Prem Darwaja Link Point", 23.0395, 72.5980, "WARD_12", False, False),
            ("NODE_SHA_01", "Delhi Darwaja Junction", 23.0410, 72.5830, "WARD_13", True, True),
            ("NODE_SHA_02", "Shahpur Bahai Centre Corner", 23.0370, 72.5790, "WARD_13", False, False),
            ("NODE_VAT_01", "Vatva GIDC Phase-1 Water Tank Jn", 22.9680, 72.6310, "WARD_14", True, False),
            ("NODE_VAT_02", "Vatva Canal Road Crossing", 22.9620, 72.6350, "WARD_14", False, True),
            ("NODE_VAT_03", "Vatva Phase-4 Mega Industrial Circle", 22.9550, 72.6460, "WARD_15", True, False),
            ("NODE_VAT_04", "Vatva Heavy Chemical Feeder Jn", 22.9580, 72.6410, "WARD_15", False, False),
            ("NODE_NAR_01", "Naroda GIDC Fire Station Jn", 23.0810, 72.6560, "WARD_16", True, True),
            ("NODE_NAR_02", "Naroda Ring Road Industrial Hub", 23.0750, 72.6620, "WARD_16", False, False),
            ("NODE_ODH_01", "Odhav Ring Road Char Rasta", 23.0310, 72.6550, "WARD_17", True, False),
            ("NODE_ODH_02", "Odhav Industrial Estate Gate 2", 23.0260, 72.6480, "WARD_17", False, True),
            ("NODE_RAK_01", "Rakhial Monogram Mills Corner", 23.0190, 72.6220, "WARD_18", True, False),
            ("NODE_RAK_02", "Rakhial BRTS Station Junction", 23.0160, 72.6260, "WARD_18", False, False),
            ("NODE_AMR_01", "Amraiwadi Char Rasta", 23.0040, 72.6290, "WARD_19", True, True),
            ("NODE_AMR_02", "Surelia Estate Road Jn", 23.0010, 72.6340, "WARD_19", False, False),
            ("NODE_BEH_01", "Behrampura Municipal Health Center Corner", 22.9990, 72.5840, "WARD_20", True, True),
            ("NODE_BEH_02", "Kalamdar Basti Chawl Entry", 22.9960, 72.5870, "WARD_20", False, False),
            ("NODE_DAN_01", "Danilimda Cross Roads", 22.9910, 72.5920, "WARD_21", True, False),
            ("NODE_DAN_02", "Tannery Worker Basti Main Lane", 22.9870, 72.5950, "WARD_21", False, True),
            ("NODE_CHN_01", "Chandola Lake North Embankment", 22.9830, 72.6000, "WARD_22", True, False),
            ("NODE_CHN_02", "Chandola Basti Water Tank Point", 22.9790, 72.6050, "WARD_22", True, False),
            ("NODE_RAM_01", "Ramol Gam Basti Chowk", 22.9940, 72.6460, "WARD_23", False, True),
            ("NODE_RAM_02", "Ramol Express Highway Overbridge", 22.9890, 72.6510, "WARD_23", True, False),
            ("NODE_MEG_01", "Meghaninagar Chamanpura Jn", 23.0570, 72.6100, "WARD_24", True, False),
            ("NODE_MEG_02", "Civil Hospital East Basti Gate", 23.0540, 72.6140, "WARD_24", False, True),
            ("NODE_GOM_01", "Gomtipur Mill Gate Square", 23.0200, 72.6090, "WARD_25", True, False),
            ("NODE_GOM_02", "Gomtipur Railway Colony Path", 23.0170, 72.6120, "WARD_25", False, False),
            ("NODE_BOD_01", "Bodakdev Pakwan Cross Roads", 23.0410, 72.5180, "WARD_26", True, False),
            ("NODE_BOD_02", "Judges Bungalow Road Circle", 23.0440, 72.5120, "WARD_26", False, True),
            ("NODE_SAT_01", "Satellite Shivranjani Cross Roads", 23.0240, 72.5290, "WARD_27", True, True),
            ("NODE_SAT_02", "Jodhpur Cross Roads", 23.0210, 72.5220, "WARD_27", False, False),
            ("NODE_VAS_01", "Vastrapur Lake Entry Plaza", 23.0360, 72.5310, "WARD_28", True, True),
            ("NODE_VAS_02", "IIM Ahmedabad Heritage Campus Gate", 23.0320, 72.5340, "WARD_28", False, False),
            ("NODE_THA_01", "Thaltej Cross Roads (SG Highway)", 23.0590, 72.5120, "WARD_29", True, False),
            ("NODE_THA_02", "Thaltej Shilaj Road Jn", 23.0560, 72.5030, "WARD_29", False, True),
            ("NODE_AMB_01", "Ambawadi Circle (Panjrapol)", 23.0210, 72.5460, "WARD_30", True, False),
            ("NODE_AMB_02", "Polytechnic Campus Corner", 23.0170, 72.5510, "WARD_30", False, True),
            ("NODE_GUL_01", "Gulbai Tekra Hollow Blocks Jn", 23.0280, 72.5480, "WARD_31", False, False),
            ("NODE_PAL_01", "Paldi Bhatta Cross Roads", 23.0090, 72.5640, "WARD_32", True, True),
            ("NODE_PAL_02", "Mahalaxmi Five Roads", 23.0060, 72.5590, "WARD_32", False, False),
            ("NODE_SGH_01", "SG Highway - ISKCON Cross Roads", 23.0310, 72.5020, "WARD_33", True, True),
            ("NODE_SGH_02", "SG Highway - Gurudwara Jn", 23.0530, 72.5090, "WARD_33", True, False),
            ("NODE_RNG_01", "132ft Ring Road - Helmet Circle", 23.0420, 72.5360, "WARD_34", True, True),
            ("NODE_RNG_02", "132ft Ring Road - Memnagar Fire Jn", 23.0480, 72.5390, "WARD_34", False, False),
            ("NODE_KLR_01", "Kalupur Station Front Concourse", 23.0290, 72.6020, "WARD_35", True, True),
            ("NODE_KLR_02", "Sarangpur Overbridge Approach", 23.0240, 72.6040, "WARD_35", False, False),
            ("NODE_RNP_01", "Ranip Mega Bus Port Entry", 23.0760, 72.5760, "WARD_36", True, True),
            ("NODE_RNP_02", "Subhash Bridge South Abutment", 23.0640, 72.5790, "WARD_36", False, False),
            ("NODE_RIV_W01", "Riverfront West - Usmanpura Garden Entry", 23.0440, 72.5730, "WARD_37", True, False),
            ("NODE_RIV_W02", "Riverfront West - Nehru Bridge Lower Promenade", 23.0270, 72.5720, "WARD_37", True, True),
            ("NODE_RIV_E01", "Riverfront East - Flower Park Pavilion", 23.0280, 72.5770, "WARD_38", True, True),
            ("NODE_RIV_E02", "Riverfront East - Ellisbridge Promenade Foot", 23.0220, 72.5760, "WARD_38", False, False),
            ("NODE_KNK_01", "Kankaria Lake Gate No. 1 (Main Plaza)", 23.0080, 72.5990, "WARD_39", True, True),
            ("NODE_KNK_02", "Kankaria Balvatika Water Pavilion", 23.0030, 72.6030, "WARD_39", True, False),
            ("NODE_PAR_01", "Parimal Garden Main Shaded Gate", 23.0170, 72.5570, "WARD_40", True, True),
            ("NODE_PAR_02", "Law Garden Khau Gali Promenade", 23.0230, 72.5580, "WARD_40", True, True),
        ]

        for nid, name, lat, lon, wid, has_kiosk, has_cooling in node_catalog:
            self.nodes[nid] = IntersectionNode(
                node_id=nid,
                name=name,
                lat=lat,
                lon=lon,
                ward_id=wid,
                has_hydration_kiosk=has_kiosk,
                has_cooling_center=has_cooling,
            )

    # -------------------------------------------------------------------------
    # 5.3 Street Segment Network Generation (150 Segments)
    # -------------------------------------------------------------------------
    def _generate_streets(self) -> None:
        edges_plan = [
            ("NODE_NAV_01", "NODE_NAV_02", "Navrangpura Road", "asphalt", True),
            ("NODE_NAV_01", "NODE_NAV_03", "St. Xavier's High Street", "asphalt", False),
            ("NODE_NAV_02", "NODE_CG_01", "Swastik Link Avenue", "asphalt", True),
            ("NODE_NAV_03", "NODE_CG_02", "Panchvati Cross Road", "asphalt", True),
            ("NODE_CG_01", "NODE_CG_03", "Chimanlal Girdharlal Road North", "paver", True),
            ("NODE_CG_03", "NODE_CG_02", "Chimanlal Girdharlal Road South", "paver", True),
            ("NODE_CG_01", "NODE_MIT_01", "Mithakhali Boulevard", "asphalt", False),
            ("NODE_CG_02", "NODE_MIT_02", "Law Garden West Access Road", "paver", False),
            ("NODE_ASH_01", "NODE_ASH_02", "Ashram Road North Corridor", "asphalt", True),
            ("NODE_ASH_01", "NODE_ASH_03", "Ashram Road Central Spine", "asphalt", True),
            ("NODE_ASH_03", "NODE_ELL_01", "Ashram Road South Connector", "asphalt", True),
            ("NODE_ASH_01", "NODE_NAV_02", "Income Tax - Navrangpura Link", "asphalt", False),
            ("NODE_ASH_02", "NODE_RIV_W01", "Usmanpura Riverfront Access Way", "concrete", False),
            ("NODE_ELL_01", "NODE_ELL_02", "Ellisbridge Memorial Way", "asphalt", True),
            ("NODE_ELL_01", "NODE_RIV_W02", "Riverfront Lower Ramp Way", "permeable_paver", False),
            ("NODE_MIT_01", "NODE_MIT_02", "Mithakhali Shaded Avenue", "asphalt", False),
            ("NODE_MIT_02", "NODE_PAR_02", "Law Garden Peripheral Loop", "permeable_paver", False),
            ("NODE_MNK_01", "NODE_MNK_02", "Manek Chowk Goldsmith Gali", "paver", False),
            ("NODE_MNK_01", "NODE_MNK_03", "Mandvi Pol Traditional Alley", "paver", False),
            ("NODE_MNK_01", "NODE_KHD_02", "Bala Hanuman Sheri", "paver", False),
            ("NODE_MNK_02", "NODE_KAL_02", "Rani no Hajiro Connector", "concrete", False),
            ("NODE_KAL_01", "NODE_KAL_02", "Kalupur Swaminarayan Heritage Walk", "paver", False),
            ("NODE_KAL_01", "NODE_DAR_01", "Kalupur - Dariapur Ancient Gali", "paver", False),
            ("NODE_KHD_01", "NODE_KHD_02", "Khadia Char Rasta Heritage Gali", "paver", False),
            ("NODE_KHD_01", "NODE_AST_02", "Raipur Chakla Connector Pol", "paver", False),
            ("NODE_AST_01", "NODE_AST_02", "Astodia Darwaja Bazaar Lane", "asphalt", False),
            ("NODE_DHL_01", "NODE_DHL_02", "Teen Darwaza Historical Concourse", "paver", False),
            ("NODE_DHL_01", "NODE_MNK_01", "Bhadra - Manek Chowk Silk Lane", "paver", False),
            ("NODE_DHL_02", "NODE_RIV_E01", "Bhadra Plaza Riverfront Descent", "concrete", False),
            ("NODE_DAR_01", "NODE_DAR_02", "Dariapur Pol Heritage Spine", "paver", False),
            ("NODE_DAR_01", "NODE_SHA_01", "Delhi Darwaja - Dariapur Connecting Sheri", "asphalt", False),
            ("NODE_SHA_01", "NODE_SHA_02", "Shahpur Walled City Road", "asphalt", False),
            ("NODE_SHA_02", "NODE_RIV_E01", "Shahpur Riverfront Gate Link", "concrete", False),
            ("NODE_VAT_01", "NODE_VAT_02", "Vatva GIDC Phase-1 Main Spine", "asphalt", True),
            ("NODE_VAT_01", "NODE_VAT_04", "Vatva Chemical Feeder Road", "asphalt", True),
            ("NODE_VAT_02", "NODE_VAT_03", "Vatva Heavy Haulage Logistics Way", "asphalt", True),
            ("NODE_VAT_03", "NODE_VAT_04", "Vatva Phase-4 Ring Connector", "asphalt", True),
            ("NODE_NAR_01", "NODE_NAR_02", "Naroda GIDC Industrial Highway", "asphalt", True),
            ("NODE_ODH_01", "NODE_ODH_02", "Odhav Industrial Estate Access Spine", "asphalt", True),
            ("NODE_RAK_01", "NODE_RAK_02", "Rakhial Industrial Foundry Corridor", "asphalt", True),
            ("NODE_AMR_01", "NODE_AMR_02", "Amraiwadi Heavy Transport Lane", "asphalt", True),
            ("NODE_AMR_01", "NODE_RAK_02", "Rakhial - Amraiwadi Industrial Feeder", "asphalt", True),
            ("NODE_VAT_01", "NODE_DAN_02", "Vatva - Danilimda Industrial Border Way", "asphalt", False),
            ("NODE_BEH_01", "NODE_BEH_02", "Behrampura Tin-Roof Basti Lane", "compacted_earth", False),
            ("NODE_BEH_01", "NODE_DAN_01", "Behrampura - Danilimda Cross Link", "asphalt", False),
            ("NODE_DAN_01", "NODE_DAN_02", "Danilimda Tannery Chawl Pathway", "concrete", False),
            ("NODE_DAN_02", "NODE_CHN_01", "Danilimda - Chandola Lake Footpath", "compacted_earth", False),
            ("NODE_CHN_01", "NODE_CHN_02", "Chandola Lake Embankment Trail", "compacted_earth", False),
            ("NODE_RAM_01", "NODE_RAM_02", "Ramol Basti Outer Access Lane", "asphalt", False),
            ("NODE_MEG_01", "NODE_MEG_02", "Meghaninagar Railway Colony Walk", "concrete", False),
            ("NODE_GOM_01", "NODE_GOM_02", "Gomtipur Mill Chawl Gali", "paver", False),
            ("NODE_GOM_01", "NODE_RAK_01", "Gomtipur - Rakhial Mill Lane", "asphalt", False),
            ("NODE_BEH_02", "NODE_CHN_01", "Behrampura South Slum Pathway", "compacted_earth", False),
            ("NODE_BOD_01", "NODE_BOD_02", "Judges Bungalow Shaded Boulevard", "asphalt", True),
            ("NODE_BOD_01", "NODE_SAT_01", "Bodakdev - Shivranjani Green Way", "asphalt", True),
            ("NODE_BOD_02", "NODE_THA_01", "Thaltej - Bodakdev Canopy Avenue", "asphalt", True),
            ("NODE_SAT_01", "NODE_SAT_02", "Satellite 100ft Road", "asphalt", True),
            ("NODE_SAT_01", "NODE_VAS_01", "Satellite - Vastrapur Lake Connector", "asphalt", False),
            ("NODE_VAS_01", "NODE_VAS_02", "Vastrapur Lake Outer Perimeter Walk", "permeable_paver", False),
            ("NODE_VAS_02", "NODE_RNG_01", "IIM Ahmedabad Tree-Canopy Drive", "asphalt", True),
            ("NODE_THA_01", "NODE_THA_02", "Thaltej Shilaj Shaded Link", "asphalt", False),
            ("NODE_AMB_01", "NODE_AMB_02", "Ambawadi Gulmohar Marg", "asphalt", True),
            ("NODE_AMB_01", "NODE_PAR_01", "Panjrapol - Parimal Shaded Way", "permeable_paver", False),
            ("NODE_GUL_01", "NODE_CG_02", "Gulbai Tekra Crescent", "asphalt", False),
            ("NODE_PAL_01", "NODE_PAL_02", "Paldi Bhatta Residential Spine", "asphalt", False),
            ("NODE_PAL_01", "NODE_ELL_02", "Paldi - VS Hospital Riverside Drive", "asphalt", True),
            ("NODE_SGH_01", "NODE_SGH_02", "Sarkhej-Gandhinagar (SG) Highway Central Corridor", "asphalt", True),
            ("NODE_SGH_01", "NODE_BOD_01", "ISKCON - Pakwan Arterial Spine", "asphalt", True),
            ("NODE_SGH_02", "NODE_THA_01", "SG Highway - Thaltej Flyover Flank", "asphalt", True),
            ("NODE_RNG_01", "NODE_RNG_02", "132 Feet Ring Road West Sector", "asphalt", True),
            ("NODE_RNG_01", "NODE_NAV_01", "Helmet Circle - Commerce College Link", "asphalt", True),
            ("NODE_KLR_01", "NODE_KLR_02", "Kalupur Station Frontage Highway", "asphalt", True),
            ("NODE_KLR_01", "NODE_KAL_01", "Station - Swaminarayan Temple Approach", "asphalt", False),
            ("NODE_RNP_01", "NODE_RNP_02", "Ranip Mega Transit Ring Road Link", "asphalt", True),
            ("NODE_RNP_02", "NODE_ASH_02", "Subhash Bridge - Usmanpura Expressway", "asphalt", True),
            ("NODE_RIV_W01", "NODE_RIV_W02", "Sabarmati Riverfront Promenade West (Continuous Shaded Walk)", "permeable_paver", True),
            ("NODE_RIV_E01", "NODE_RIV_E02", "Sabarmati Riverfront Promenade East (Flower Park Path)", "permeable_paver", True),
            ("NODE_KNK_01", "NODE_KNK_02", "Kankaria Lake Circular Canopy Promenade", "permeable_paver", True),
            ("NODE_KNK_01", "NODE_AST_01", "Kankaria - Astodia Darwaja Boulevard", "asphalt", True),
            ("NODE_PAR_01", "NODE_PAR_02", "Parimal - Law Garden Canopy Corridor", "permeable_paver", True),
            ("NODE_ELL_01", "NODE_DHL_02", "Ellisbridge Heritage River Crossing", "asphalt", True),
            ("NODE_ASH_03", "NODE_DHL_01", "Nehru Bridge Cross-River Link", "asphalt", True),
            ("NODE_ASH_01", "NODE_SHA_01", "Gandhi Bridge Cross-River Arterial", "asphalt", True),
            ("NODE_PAL_01", "NODE_BEH_01", "Sardar Bridge - Behrampura Link", "asphalt", True),
            ("NODE_KNK_01", "NODE_DAN_01", "Kankaria - Danilimda Connector", "asphalt", False),
            ("NODE_AST_02", "NODE_KLR_02", "Raipur - Sarangpur Overbridge Link", "asphalt", True),
            ("NODE_DAR_02", "NODE_MEG_01", "Prem Darwaja - Meghaninagar Feeder", "asphalt", False),
            ("NODE_RAK_01", "NODE_ODH_02", "Rakhial - Odhav Industrial Link", "asphalt", True),
            ("NODE_SAT_02", "NODE_PAL_02", "Jodhpur - Paldi 120ft Connecting Road", "asphalt", True),
            ("NODE_BOD_02", "NODE_RNG_02", "Judges Bungalow - Memnagar Fire Station Link", "asphalt", True),
        ]

        street_idx = 1
        ward_lookup = {w.ward_id: w for w in self.wards}

        for u_id, v_id, base_name, preferred_mat, is_major in edges_plan:
            u_node = self.nodes[u_id]
            v_node = self.nodes[v_id]
            w_id = u_node.ward_id
            ward_obj = ward_lookup.get(w_id, self.wards[0])
            t_key = ward_obj.typology_key

            dist_m = haversine_distance(u_node.lat, u_node.lon, v_node.lat, v_node.lon)
            bearing = calculate_bearing(u_node.lat, u_node.lon, v_node.lat, v_node.lon)
            orientation, aspect_label = bearing_to_cardinal_aspect(bearing)

            num_splits = 2 if (is_major or dist_m > 900.0) else 1

            for s_idx in range(num_splits):
                s_id = f"ST_{street_idx:03d}"
                seg_name = base_name if num_splits == 1 else f"{base_name} (Segment {s_idx + 1})"

                frac_start = s_idx / num_splits
                frac_end = (s_idx + 1) / num_splits

                s_lat = u_node.lat + frac_start * (v_node.lat - u_node.lat)
                s_lon = u_node.lon + frac_start * (v_node.lon - u_node.lon)
                e_lat = u_node.lat + frac_end * (v_node.lat - u_node.lat)
                e_lon = u_node.lon + frac_end * (v_node.lon - u_node.lon)
                seg_len_m = round(haversine_distance(s_lat, s_lon, e_lat, e_lon), 1)

                if t_key == "old_city_pols":
                    width_m = round(self.rng.uniform(3.2, 6.0), 1)
                    aspect_h_w = round(self.rng.uniform(2.2, 3.5), 2)
                    mat = preferred_mat if preferred_mat in ["paver", "concrete"] else "paver"
                    albedo = 0.22 if mat == "paver" else 0.28
                    canopy_ratio = round(self.rng.uniform(0.04, 0.14), 2)
                    ped_vol_num = self.rng.randint(800, 2600)
                    speed_kmh = 20
                elif t_key == "informal_settlements":
                    width_m = round(self.rng.uniform(2.8, 5.5), 1)
                    aspect_h_w = round(self.rng.uniform(1.2, 2.0), 2)
                    mat = preferred_mat if preferred_mat in ["compacted_earth", "concrete"] else "compacted_earth"
                    albedo = 0.18 if mat == "compacted_earth" else 0.24
                    canopy_ratio = round(self.rng.uniform(0.02, 0.08), 2)
                    ped_vol_num = self.rng.randint(600, 2200)
                    speed_kmh = 20
                elif t_key == "industrial_belt":
                    width_m = round(self.rng.uniform(18.0, 32.0), 1)
                    aspect_h_w = round(self.rng.uniform(0.3, 0.6), 2)
                    mat = "asphalt"
                    albedo = round(self.rng.uniform(0.10, 0.14), 2)
                    canopy_ratio = round(self.rng.uniform(0.01, 0.06), 2)
                    ped_vol_num = self.rng.randint(250, 950)
                    speed_kmh = 50
                elif t_key == "affluent_suburbs":
                    width_m = round(self.rng.uniform(14.0, 24.0), 1)
                    aspect_h_w = round(self.rng.uniform(0.6, 1.1), 2)
                    mat = preferred_mat
                    albedo = 0.28 if mat == "permeable_paver" else 0.18
                    canopy_ratio = round(self.rng.uniform(0.55, 0.88), 2)
                    ped_vol_num = self.rng.randint(150, 650)
                    speed_kmh = 40
                elif t_key == "urban_parks":
                    width_m = round(self.rng.uniform(6.0, 15.0), 1)
                    aspect_h_w = round(self.rng.uniform(0.3, 0.7), 2)
                    mat = "permeable_paver"
                    albedo = 0.32
                    canopy_ratio = round(self.rng.uniform(0.72, 0.90), 2)
                    ped_vol_num = self.rng.randint(500, 1800)
                    speed_kmh = 15
                elif t_key == "transit_corridors":
                    width_m = round(self.rng.uniform(30.0, 45.0), 1)
                    aspect_h_w = round(self.rng.uniform(0.3, 0.6), 2)
                    mat = "asphalt"
                    albedo = round(self.rng.uniform(0.11, 0.15), 2)
                    canopy_ratio = round(self.rng.uniform(0.06, 0.16), 2)
                    ped_vol_num = self.rng.randint(1400, 3400)
                    speed_kmh = 60
                else:
                    width_m = round(self.rng.uniform(16.0, 28.0), 1)
                    aspect_h_w = round(self.rng.uniform(1.2, 2.0), 2)
                    mat = preferred_mat
                    albedo = 0.22 if mat == "paver" else 0.15
                    canopy_ratio = round(self.rng.uniform(0.15, 0.32), 2)
                    ped_vol_num = self.rng.randint(1200, 3100)
                    speed_kmh = 40

                svf = calculate_sky_view_factor(aspect_h_w)
                t_surf = calculate_surface_temperature(self.ambient_temp, albedo, canopy_ratio)
                t_mrt = calculate_mean_radiant_temperature(self.ambient_temp, canopy_ratio, svf)
                heat_risk, risk_tier = calculate_pedestrian_heat_risk(t_mrt, t_surf, canopy_ratio, svf)

                if ped_vol_num < 400:
                    vol_cat = "Low"
                elif ped_vol_num < 1200:
                    vol_cat = "Moderate"
                elif ped_vol_num < 2500:
                    vol_cat = "High"
                else:
                    vol_cat = "Critical"

                tree_count = int((seg_len_m / 14.0) * canopy_ratio)
                has_misting = (u_node.has_hydration_kiosk or v_node.has_hydration_kiosk) and (t_key in ["urban_parks", "dense_commercial", "old_city_pols"])

                geom = {
                    "type": "LineString",
                    "coordinates": [
                        [round(s_lon, 6), round(s_lat, 6)],
                        [round(e_lon, 6), round(e_lat, 6)],
                    ],
                }

                st_data = StreetData(
                    street_id=s_id,
                    street_name=seg_name,
                    ward_id=w_id,
                    ward_name=ward_obj.ward_name,
                    length_meters=seg_len_m,
                    mean_radiant_temp_celsius=t_mrt,
                    surface_temp_celsius=t_surf,
                    shade_ratio=canopy_ratio,
                    sky_view_factor=svf,
                    aspect_ratio_h_w=aspect_h_w,
                    pedestrian_heat_risk=heat_risk,
                    risk_level=risk_tier,
                    pedestrian_volume=vol_cat,
                    tree_count=tree_count,
                    has_water_misting=has_misting,
                    geometry=geom,
                    start_node_id=u_id if s_idx == 0 else f"{u_id}_mid",
                    end_node_id=v_id if s_idx == num_splits - 1 else f"{u_id}_mid",
                    start_coordinates={"lat": round(s_lat, 6), "lon": round(s_lon, 6)},
                    end_coordinates={"lat": round(e_lat, 6), "lon": round(e_lon, 6)},
                    street_width_meters=width_m,
                    surface_material=mat,
                    surface_albedo=albedo,
                    tree_canopy_shading_ratio=canopy_ratio,
                    solar_orientation=orientation,
                    solar_aspect_label=aspect_label,
                    azimuth_degrees=round(bearing, 1),
                    pedestrian_hourly_volume=ped_vol_num,
                    speed_limit_kmh=speed_kmh,
                )
                self.streets.append(st_data)
                street_idx += 1

    # -------------------------------------------------------------------------
    # 5.4 Cooling Centers & Drinking Water / Misting Infrastructure
    # -------------------------------------------------------------------------
    def _generate_cooling_infrastructure(self) -> None:
        cooling_center_specs = [
            ("CC_01", "British Council Air-Conditioned Library", "Air-conditioned Public Library", "WARD_01", "Near Commerce Six Roads, Navrangpura", 23.0375, 72.5560, "08:00 - 21:00", 180, 24.2, True, True, True, "+91 79 2640 3300", ["High-speed Wi-Fi", "Quiet Rest Area", "ORS Packets", "Chilled Water Dispenser"]),
            ("CC_02", "Ahmedabad Central Heritage Library", "Air-conditioned Public Library", "WARD_09", "Near Khadia Char Rasta", 23.0225, 72.5925, "08:00 - 21:00", 220, 24.5, True, True, True, "+91 79 2214 4110", ["Reading Rooms", "Chilled RO Water", "Paramedic on Duty", "Cool Resting Mats"]),
            ("CC_03", "Tagore Memorial Air-Cooled Hall", "Community Hall", "WARD_05", "Tagore Hall Complex, Paldi Road, Ellisbridge", 23.0185, 72.5695, "24/7 Heat Emergency", 450, 24.0, True, True, True, "+91 79 2657 8820", ["Emergency Cots", "IV Saline Kits", "Misting Fans", "Ambulance Stationed"]),
            ("CC_04", "Manek Chowk Community Rest Shelter", "Community Hall", "WARD_07", "Old City Mandvi Pol Entrance", 23.0248, 72.5880, "09:00 - 20:00", 140, 25.0, True, False, False, "+91 79 2216 1020", ["Chilled Buttermilk (Chhaas)", "Resting Benches", "Ice Packs", "First Aid Nurse"]),
            ("CC_05", "Kalupur Swaminarayan Shaded Dharamshala", "Dedicated Night Shelter", "WARD_08", "Kalupur Temple Compound", 23.0315, 72.5980, "24/7 Heat Emergency", 320, 25.5, True, True, True, "+91 79 2213 2220", ["Free Potable Water", "Covered Courtyard", "Thermal Relief Cots", "Emergency Food & Electrolytes"]),
            ("CC_06", "Vatva GIDC Welfare Center & Health Post", "Municipal Health Center", "WARD_14", "Phase-1 Administrative Block, Vatva", 22.9665, 72.6325, "07:00 - 22:00", 260, 24.0, True, True, True, "+91 79 2583 0410", ["Occupational Heat Strain Clinic", "Cold Water Shower", "Electrolyte Packets", "Doctor on Duty"]),
            ("CC_07", "Vatva Phase-4 Emergency Cooling Shed", "Dedicated Night Shelter", "WARD_15", "Mega Estate Gate, Vatva", 22.9565, 72.6440, "10:00 - 18:00 (Peak Sun)", 150, 25.5, False, True, True, "+91 79 2589 1910", ["Shaded Industrial Louver", "High-power Misting", "Chilled Water Dispensers"]),
            ("CC_08", "Naroda Municipal Community Hall", "Community Hall", "WARD_16", "Near Naroda Fire Station", 23.0805, 72.6570, "08:00 - 20:00", 280, 24.5, True, True, True, "+91 79 2281 3340", ["Air-Conditioned Hall", "ORS Solution", "Senior Citizen Priority Cots"]),
            ("CC_09", "Odhav Shramik Kalyan Cooling Shelter", "Community Hall", "WARD_17", "Odhav Ring Road Char Rasta", 23.0305, 72.6535, "08:00 - 21:00", 200, 24.8, True, True, True, "+91 79 2287 4500", ["Chilled Drinking Water", "Ceiling Jet Fans", "Nurse Consultation", "Ice Packs"]),
            ("CC_10", "Behrampura Urban Primary Health Center", "Municipal Health Center", "WARD_20", "Opposite Municipal Quarters, Behrampura", 22.9985, 72.5845, "24/7 Heat Emergency", 160, 23.8, True, True, True, "+91 79 2535 7710", ["Heat Stroke Triage Unit", "Ice Immersion Tub", "ORS Distribution", "Child Care Cooling Corner"]),
            ("CC_11", "Danilimda Community Health Hall", "Community Hall", "WARD_21", "Near Danilimda Cross Roads", 22.9915, 72.5930, "08:00 - 21:00", 210, 24.2, True, True, True, "+91 79 2532 9900", ["Air Cooled Halls", "Chilled Electrolytes", "Medical Assistants", "Clean Restrooms"]),
            ("CC_12", "Chandola Lake Rehabilitation Rest Center", "Dedicated Night Shelter", "WARD_22", "Chandola North Embankment Road", 22.9820, 72.6015, "09:00 - 20:00", 180, 25.2, True, False, False, "+91 79 2538 4120", ["Drinking Water Tanker", "High-velocity Misting Fans", "First Aid Kits"]),
            ("CC_13", "Bodakdev Municipal Ward Community Hall", "Community Hall", "WARD_26", "Judges Bungalow Road, Bodakdev", 23.0425, 72.5160, "08:00 - 22:00", 350, 23.5, True, True, True, "+91 79 2687 1120", ["Full HVAC AC", "Power Backup Genset", "Medical Staff On Call", "Wheelchair Ramps"]),
            ("CC_14", "Satellite Municipal Sports & Cooling Complex", "Community Hall", "WARD_27", "Shivranjani Cross Roads, Satellite", 23.0235, 72.5270, "07:00 - 22:00", 300, 23.5, True, True, True, "+91 79 2674 5500", ["Chilled Water Fountains", "Air-conditioned Indoor Hall", "ORS Pouches"]),
            ("CC_15", "Vastrapur Lake Public Amphitheater Lounge", "Community Hall", "WARD_28", "Vastrapur Lake Park Complex", 23.0355, 72.5315, "07:00 - 22:00", 250, 24.0, True, True, True, "+91 79 2676 8810", ["Tree-shaded Verandas", "Chilled Water", "Resting Benches"]),
            ("CC_16", "Thaltej Community Hall & Health Pavilion", "Community Hall", "WARD_29", "Thaltej Shilaj Road", 23.0575, 72.5055, "08:00 - 21:00", 240, 24.0, True, True, True, "+91 79 2685 4400", ["HVAC Chiller", "Paramedic Staff", "ORS Stations"]),
            ("CC_17", "Ambawadi Panjrapol Municipal Lounge", "Community Hall", "WARD_30", "Polytechnic Campus North Gate", 23.0195, 72.5475, "08:00 - 21:00", 190, 24.5, True, True, True, "+91 79 2630 1190", ["Air Conditioned", "Doctor on Call", "Water ATMs"]),
            ("CC_18", "Paldi Sanskar Kendra Cultural Pavilion", "Community Hall", "WARD_32", "Tagore Hall Annexe, Paldi", 23.0075, 72.5610, "09:00 - 20:00", 200, 24.5, True, True, True, "+91 79 2658 2210", ["Cooling Sanctuary", "Chilled Potable Water", "ORS Points"]),
            ("CC_19", "ISKCON Cross Roads AC Pedestrian Transit Hub", "Metro Concourse", "WARD_33", "SG Highway Metro Interchange", 23.0315, 72.5025, "06:00 - 23:00", 500, 23.0, True, True, True, "+91 79 2692 9000", ["HVAC Metro Concourse", "Elevators", "Medical Triage Desk", "Free Cold Water Dispensers"]),
            ("CC_20", "Helmet Circle 132ft BRTS AC Transit Shelter", "Metro Concourse", "WARD_34", "132ft Ring Road Center Concourse", 23.0425, 72.5365, "06:00 - 23:00", 350, 23.2, True, True, True, "+91 79 2791 2200", ["Air-conditioned Waiting Lounge", "ORS Counters", "Wheelchair Accessibility"]),
            ("CC_21", "Kalupur Mega Railway Station AC Waiting Complex", "Metro Concourse", "WARD_35", "Ahmedabad Central Station Platform 1 Hub", 23.0295, 72.6025, "24/7 Heat Emergency", 800, 23.5, True, True, True, "+91 79 2211 4455", ["High-capacity Cooling Ward", "Dedicated Heat Stroke Beds", "ORS Free Kiosk", "Doctors on 24hr Rota"]),
            ("CC_22", "Ranip Central GSRTC & BRTS Mega Terminal", "Metro Concourse", "WARD_36", "Ranip Bus Port Main Concourse", 23.0765, 72.5765, "24/7 Heat Emergency", 650, 23.2, True, True, True, "+91 79 2755 0100", ["Air Conditioned Waiting Areas", "Medical Dispensary", "Ice Water Fountains"]),
            ("CC_23", "Sabarmati Riverfront West Event Center Lounge", "Community Hall", "WARD_37", "Riverfront Promenade near Nehru Bridge", 23.0285, 72.5725, "07:00 - 22:00", 300, 24.0, True, True, True, "+91 79 2658 6600", ["River Breeze Pavilion", "AC Lounges", "Misting Walkway", "Hydration Point"]),
            ("CC_24", "Sabarmati Riverfront East Flower Park Pavilion", "Community Hall", "WARD_38", "Flower Park Gate, Riverfront East", 23.0275, 72.5775, "07:00 - 22:00", 250, 24.2, True, True, True, "+91 79 2658 6610", ["Green Canopy Shade", "AC Rest Area", "Potable Water ATM"]),
            ("CC_25", "Kankaria Lakefront Children Health Pavilion", "Community Hall", "WARD_39", "Gate 1 Pavilion, Kankaria Lake", 23.0070, 72.6000, "06:00 - 22:00", 350, 24.0, True, True, True, "+91 79 2543 1120", ["High-capacity AC", "Paramedic Van", "Oral Rehydration Packs", "Misting Perimeter"]),
            ("CC_26", "Civil Hospital Asarwa Heat Stroke Emergency Ward", "Civil Hospital Heat Emergency Ward", "WARD_24", "Meghaninagar Road, Asarwa", 23.0550, 72.6130, "24/7 Heat Emergency", 500, 22.0, True, True, True, "+91 79 2268 0074", ["Dedicated 60-bed Heat Stroke ICU", "Cold Water Immersion Baths", "Critical Care Physicians", "108 Ambulance Hub"]),
        ]

        for cc_spec in cooling_center_specs:
            cid, name, ftype, wid, addr, lat, lon, hrs, cap, temp_in, has_med, has_gen, wheel, phone, amen = cc_spec
            w_obj = next((w for w in self.wards if w.ward_id == wid), self.wards[0])
            geom = {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]}
            occ = int(cap * self.rng.uniform(0.35, 0.85))

            self.cooling_centers.append(
                CoolingCenterData(
                    center_id=cid,
                    name=name,
                    facility_type=ftype,
                    ward_id=wid,
                    ward_name=w_obj.ward_name,
                    address=addr,
                    coordinates={"lat": round(lat, 6), "lon": round(lon, 6)},
                    distance_meters=0.0,
                    walking_time_minutes=0,
                    operating_hours=hrs,
                    capacity_persons=cap,
                    current_occupancy=occ,
                    indoor_temp_celsius=temp_in,
                    has_medical_staff=has_med,
                    has_backup_generator=has_gen,
                    wheelchair_accessible=wheel,
                    phone_contact=phone,
                    amenities=amen,
                    status="active",
                    geometry=geom,
                )
            )

        hydration_specs = [
            ("HYD_01", "Manek Chowk Heritage Misting Kiosk", "High-Pressure Misting Station", "WARD_07", "Opposite Rani no Hajiro Gate", 23.0246, 72.5878, 15.0, 4200, True, True, "08:00 - 22:00"),
            ("HYD_02", "Teen Darwaza Public Chabutro Piau", "Public Chabutro Drinking Post", "WARD_11", "Teen Darwaza Arch Plaza", 23.0256, 72.5822, 18.0, 5500, True, False, "24/7"),
            ("HYD_03", "Kalupur Swaminarayan Chilled Water Post", "RO Water ATM", "WARD_08", "Kalupur Temple Street Corner", 23.0308, 72.5972, 20.0, 6800, True, False, "06:00 - 22:00"),
            ("HYD_04", "Khadia Bala Hanuman Water ATM", "RO Water ATM", "WARD_09", "Bala Hanuman Temple Chowk", 23.0228, 72.5918, 16.0, 4900, True, False, "07:00 - 22:00"),
            ("HYD_05", "Astodia Darwaja Misting Gazebo", "High-Pressure Misting Station", "WARD_10", "Astodia Darwaja Circle", 23.0162, 72.5942, 14.0, 3800, True, True, "08:00 - 20:00"),
            ("HYD_06", "Delhi Darwaja Shaded Water Kiosk", "Chilled Water Kiosk", "WARD_13", "Delhi Darwaja Outer Circle", 23.0412, 72.5832, 18.0, 5200, True, False, "07:00 - 21:00"),
            ("HYD_07", "Ashram Road Income Tax Misting Tower", "High-Pressure Misting Station", "WARD_03", "Income Tax Circle Pedestrian Island", 23.0412, 72.5718, 22.0, 7500, True, True, "08:00 - 21:00"),
            ("HYD_08", "CG Road Swastik Shoppers Mist Point", "High-Pressure Misting Station", "WARD_02", "Swastik Cross Roads Corner", 23.0312, 72.5572, 16.0, 4500, True, True, "09:00 - 22:00"),
            ("HYD_09", "Navrangpura Commerce Six Roads Water ATM", "RO Water ATM", "WARD_01", "Commerce Six Roads Bus Stand", 23.0382, 72.5552, 20.0, 6200, True, False, "07:00 - 22:00"),
            ("HYD_10", "Ellisbridge Town Hall Hydration Gazebo", "Chilled Water Kiosk", "WARD_05", "Town Hall Bus Stop", 23.0198, 72.5688, 18.0, 5800, True, False, "07:00 - 21:00"),
            ("HYD_11", "Law Garden Khau Gali Misting Strip", "High-Pressure Misting Station", "WARD_40", "Law Garden Street Food Lane", 23.0232, 72.5582, 20.0, 6400, True, True, "10:00 - 23:00"),
            ("HYD_12", "Parimal Garden Morning Walk Hydration Post", "Public Fountain", "WARD_40", "Parimal Garden Gate 1", 23.0172, 72.5572, 15.0, 4100, True, False, "06:00 - 21:00"),
            ("HYD_13", "Vatva GIDC Phase-1 Laborer Water ATM", "RO Water ATM", "WARD_14", "Water Tank Square, Vatva GIDC", 22.9682, 72.6312, 25.0, 9200, True, False, "24/7"),
            ("HYD_14", "Vatva Canal Road Industrial Mist Shelter", "High-Pressure Misting Station", "WARD_14", "Vatva Canal Bridge", 22.9622, 72.6352, 18.0, 5800, True, True, "08:00 - 19:00"),
            ("HYD_15", "Vatva Phase-4 Freight Yard Hydration Post", "Chilled Water Kiosk", "WARD_15", "Phase-4 Mega Gate", 22.9552, 72.6462, 22.0, 7800, True, False, "07:00 - 20:00"),
            ("HYD_16", "Naroda Industrial Fire Station Hydration ATM", "RO Water ATM", "WARD_16", "Naroda GIDC Main Gate", 23.0812, 72.6562, 20.0, 7100, True, False, "06:00 - 22:00"),
            ("HYD_17", "Odhav Ring Road Workers Water Point", "Chilled Water Kiosk", "WARD_17", "Odhav Char Rasta Bus Stand", 23.0312, 72.6552, 22.0, 7900, True, False, "07:00 - 21:00"),
            ("HYD_18", "Rakhial Monogram Mills Laborer Water Station", "RO Water ATM", "WARD_18", "Rakhial Mill Gate 3", 23.0192, 72.6222, 20.0, 6900, True, False, "06:00 - 22:00"),
            ("HYD_19", "Amraiwadi Char Rasta Public Chilled Piau", "Chilled Water Kiosk", "WARD_19", "Near Amraiwadi Police Station", 23.0042, 72.6292, 18.0, 6100, True, False, "07:00 - 21:00"),
            ("HYD_20", "Behrampura Basti Mother & Child Water ATM", "RO Water ATM", "WARD_20", "Near Behrampura Health Post", 22.9992, 72.5842, 24.0, 8900, True, False, "24/7"),
            ("HYD_21", "Behrampura Canal Road High-Pressure Mist Point", "High-Pressure Misting Station", "WARD_20", "Behrampura Chawl Corner", 22.9962, 72.5872, 16.0, 4800, True, True, "08:00 - 20:00"),
            ("HYD_22", "Danilimda Tannery Workers Free Water Post", "RO Water ATM", "WARD_21", "Danilimda Cross Roads North", 22.9912, 72.5922, 22.0, 8100, True, False, "24/7"),
            ("HYD_23", "Chandola Lake North Embankment Water ATM", "RO Water ATM", "WARD_22", "Chandola Lake Embankment Gate", 22.9832, 72.6002, 24.0, 9400, True, False, "24/7"),
            ("HYD_24", "Ramol Gam Basti Shaded Drinking Station", "Chilled Water Kiosk", "WARD_23", "Ramol Gam Center Chowk", 22.9942, 72.6462, 18.0, 6200, True, False, "07:00 - 21:00"),
            ("HYD_25", "Meghaninagar Civil Hospital Public Water Point", "RO Water ATM", "WARD_24", "Civil Hospital External Gate", 23.0572, 72.6102, 25.0, 10500, True, False, "24/7"),
            ("HYD_26", "Gomtipur Mill Chawl Community Water Point", "RO Water ATM", "WARD_25", "Gomtipur Ward Office Square", 23.0202, 72.6092, 20.0, 7200, True, False, "06:00 - 22:00"),
            ("HYD_27", "Bodakdev Pakwan Cross Roads Water ATM", "RO Water ATM", "WARD_26", "Pakwan Dining Hall Concourse", 23.0412, 72.5182, 18.0, 5400, True, False, "07:00 - 22:00"),
            ("HYD_28", "Satellite Shivranjani BRTS Water Point", "BRTS Bus Station Hydration Post", "WARD_27", "Shivranjani BRTS Platform", 23.0242, 72.5292, 20.0, 6800, True, False, "06:00 - 23:00"),
            ("HYD_29", "Vastrapur Lake Entry Plaza Mist Gazebo", "High-Pressure Misting Station", "WARD_28", "Vastrapur Lake North Gate", 23.0362, 72.5312, 20.0, 6500, True, True, "06:00 - 22:00"),
            ("HYD_30", "SG Highway ISKCON BRTS Water & Mist Station", "High-Pressure Misting Station", "WARD_33", "ISKCON BRTS Pedestrian Plaza", 23.0312, 72.5022, 24.0, 8800, True, True, "06:00 - 23:00"),
            ("HYD_31", "Kalupur Railway Station West Concourse Water ATM", "RO Water ATM", "WARD_35", "Station Main Entry Gate", 23.0292, 72.6022, 25.0, 11200, True, False, "24/7"),
            ("HYD_32", "Ranip Mega Bus Port Concourse Water Hub", "RO Water ATM", "WARD_36", "Ranip Concourse Ground Level", 23.0762, 72.5762, 25.0, 10800, True, False, "24/7"),
            ("HYD_33", "Sabarmati Riverfront Promenade West Misting Arch", "High-Pressure Misting Station", "WARD_37", "Promenade Walkway Nehru Bridge Foot", 23.0272, 72.5722, 22.0, 7200, True, True, "06:00 - 23:00"),
            ("HYD_34", "Kankaria Lake Gate 1 Misting Pergola", "High-Pressure Misting Station", "WARD_39", "Kankaria Lake Main Gate Plaza", 23.0082, 72.5992, 24.0, 8500, True, True, "06:00 - 23:00"),
        ]

        for hyd_spec in hydration_specs:
            pid, name, stype, wid, addr, lat, lon, flow, daily_liters, is_free, has_mist, hrs = hyd_spec
            geom = {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]}
            w_obj = next((w for w in self.wards if w.ward_id == wid), self.wards[0])

            self.hydration_points.append(
                HydrationPointData(
                    point_id=pid,
                    name=name,
                    water_source_type=stype,
                    ward_id=wid,
                    ward_name=w_obj.ward_name,
                    address=addr,
                    coordinates={"lat": round(lat, 6), "lon": round(lon, 6)},
                    distance_meters=0.0,
                    flow_rate_liters_per_min=flow,
                    daily_dispensed_liters=daily_liters,
                    status="active",
                    is_free=is_free,
                    has_chilled_water=True,
                    has_misting_fan=has_mist,
                    operating_hours=hrs,
                    geometry=geom,
                )
            )

    # -------------------------------------------------------------------------
    # 5.5 Emergency Hospitals
    # -------------------------------------------------------------------------
    def _generate_hospitals(self) -> None:
        self.hospitals = [
            {"hospital_id": "HOSP_01", "name": "Civil Hospital Asarwa (Apex Trauma & Heatstroke Center)", "ward_id": "WARD_24", "ward_name": "Meghaninagar Railway Bastis", "lat": 23.0520, "lon": 72.6060, "total_beds": 2000, "heat_icu_beds": 50, "emergency_helpline": "108", "status": "active"},
            {"hospital_id": "HOSP_02", "name": "VS General Hospital Paldi", "ward_id": "WARD_05", "ward_name": "Ellisbridge Financial Strip", "lat": 23.0160, "lon": 72.5680, "total_beds": 750, "heat_icu_beds": 30, "emergency_helpline": "108", "status": "active"},
            {"hospital_id": "HOSP_03", "name": "SVP Institute of Medical Sciences Ellisbridge", "ward_id": "WARD_05", "ward_name": "Ellisbridge Financial Strip", "lat": 23.0230, "lon": 72.5710, "total_beds": 1500, "heat_icu_beds": 40, "emergency_helpline": "108", "status": "active"},
            {"hospital_id": "HOSP_04", "name": "LG General Hospital Maninagar", "ward_id": "WARD_39", "ward_name": "Kankaria Lake Ecological Park & Zoo", "lat": 22.9960, "lon": 72.6080, "total_beds": 650, "heat_icu_beds": 25, "emergency_helpline": "108", "status": "active"},
            {"hospital_id": "HOSP_05", "name": "Shardaben General Hospital Saraspur", "ward_id": "WARD_25", "ward_name": "Gomtipur Old Mill Workers Chawls", "lat": 23.0370, "lon": 72.6190, "total_beds": 500, "heat_icu_beds": 20, "emergency_helpline": "108", "status": "active"},
            {"hospital_id": "HOSP_06", "name": "Sola Civil Hospital Thaltej-Sola", "ward_id": "WARD_29", "ward_name": "Thaltej Mature Canopy Suburb", "lat": 23.0830, "lon": 72.5180, "total_beds": 700, "heat_icu_beds": 25, "emergency_helpline": "108", "status": "active"},
        ]

    # -------------------------------------------------------------------------
    # 5.6 Link Adaptive Capacity Counts to Wards
    # -------------------------------------------------------------------------
    def _link_adaptive_counts_to_wards(self) -> None:
        cc_counts: Dict[str, int] = {}
        for cc in self.cooling_centers:
            cc_counts[cc.ward_id] = cc_counts.get(cc.ward_id, 0) + 1

        hyd_counts: Dict[str, int] = {}
        for hp in self.hydration_points:
            hyd_counts[hp.ward_id] = hyd_counts.get(hp.ward_id, 0) + 1

        for w in self.wards:
            w.adaptive_capacity["cooling_centers_count"] = cc_counts.get(w.ward_id, 0)
            w.adaptive_capacity["hydration_points_count"] = hyd_counts.get(w.ward_id, 0)

    # -------------------------------------------------------------------------
    # 5.7 Summary & Payload Serialization
    # -------------------------------------------------------------------------
    def build_city_overview(self) -> Dict[str, Any]:
        total_pop = sum(w.demographics["total_population"] for w in self.wards)
        avg_risk = round(sum(w.heat_risk_score for w in self.wards) / len(self.wards), 1)
        avg_lst = round(sum(w.environmental["mean_lst_celsius"] for w in self.wards) / len(self.wards), 1)

        hottest_ward = max(self.wards, key=lambda w: w.environmental["mean_lst_celsius"])
        coolest_ward = min(self.wards, key=lambda w: w.environmental["mean_lst_celsius"])

        total_elderly = sum(int(w.demographics["total_population"] * w.demographics["elderly_pct"] / 100.0) for w in self.wards)
        total_children = sum(int(w.demographics["total_population"] * w.demographics["children_pct"] / 100.0) for w in self.wards)
        total_laborers = sum(int(w.demographics["total_population"] * w.demographics["outdoor_workers_pct"] / 100.0) for w in self.wards)
        total_slum = sum(int(w.demographics["total_population"] * w.demographics["slum_households_pct"] / 100.0) for w in self.wards)
        total_vuln = total_elderly + total_children + total_laborers + total_slum
        vuln_ratio = round((total_vuln / max(1, total_pop)) * 100.0, 1)

        return {
            "city_name": self.city_meta["city_name"],
            "total_population": total_pop,
            "average_heat_risk": avg_risk,
            "average_surface_temp_celsius": avg_lst,
            "ambient_air_temp_celsius": self.ambient_temp,
            "hottest_ward": {
                "ward_id": hottest_ward.ward_id,
                "ward_name": hottest_ward.ward_name,
                "zone": hottest_ward.zone,
                "mean_lst_celsius": hottest_ward.environmental["mean_lst_celsius"],
                "heat_risk_score": hottest_ward.heat_risk_score,
                "risk_level": hottest_ward.risk_level,
            },
            "coolest_ward": {
                "ward_id": coolest_ward.ward_id,
                "ward_name": coolest_ward.ward_name,
                "zone": coolest_ward.zone,
                "mean_lst_celsius": coolest_ward.environmental["mean_lst_celsius"],
                "heat_risk_score": coolest_ward.heat_risk_score,
                "risk_level": coolest_ward.risk_level,
            },
            "most_vulnerable_population": {
                "elderly_count": total_elderly,
                "children_under_5_count": total_children,
                "outdoor_laborers_count": total_laborers,
                "slum_and_informal_settlement_count": total_slum,
                "total_vulnerable": total_vuln,
                "vulnerable_ratio_pct": vuln_ratio,
            },
            "active_cooling_centers_count": len(self.cooling_centers),
            "active_hydration_points_count": len(self.hydration_points),
            "total_wards_count": len(self.wards),
            "total_streets_count": len(self.streets),
            "city_alert_level": self.city_meta["baseline_meteorology"]["alert_level"],
            "alert_advisory": (
                "Severe Red Alert heatwave conditions persisting across Ahmedabad metropolitan region. "
                "Extreme thermal exposure identified in eastern industrial belts and southern informal settlements "
                "with surface temperatures exceeding 48.5°C. Full activation of cooling centers and hydration kiosks "
                "mandated under the Ahmedabad Heat Action Plan."
            ),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def to_city_data_dict(self) -> Dict[str, Any]:
        """Convert entire city state to dictionary for data/city_data.json."""
        return {
            "system": "TERRA07 Heat-Risk Intelligence",
            "city": "Ahmedabad",
            "metadata": {
                "project": "TERRA07 Heat-Risk Intelligence",
                "track": "Agnitia Hackathon 2026 - Heat-Risk Mapping at Human Scale",
                "city": self.city_meta["city_name"],
                "country": self.city_meta["country"],
                "climate_zone": self.city_meta["climate_zone"],
                "scenario": self.city_meta["scenario_name"],
                "meteorology": self.city_meta["baseline_meteorology"],
                "bounds": self.city_meta["bounds"],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "random_seed": self.seed,
            },
            "overview": self.build_city_overview(),
            "wards": [asdict(w) for w in self.wards],
            "streets": [asdict(st) for st in self.streets],
            "cooling_centers": [asdict(cc) for cc in self.cooling_centers],
            "hydration_points": [asdict(hp) for hp in self.hydration_points],
            "hospitals": self.hospitals,
            "intersection_nodes": [asdict(n) for n in self.nodes.values()],
        }

    def to_geojson_collection(self, layer: Optional[str] = None) -> Dict[str, Any]:
        features = []

        # Wards (Polygons)
        if layer in (None, "wards"):
            for w in self.wards:
                props = {
                    "feature_type": "ward",
                    "ward_id": w.ward_id,
                    "ward_name": w.ward_name,
                    "zone": w.zone,
                    "typology": w.typology_key,
                    "typology_name": w.typology_name,
                    "area_km2": w.area_km2,
                    "heat_risk_score": w.heat_risk_score,
                    "risk_level": w.risk_level,
                    "risk_percentile": w.risk_percentile,
                    "mean_lst_celsius": w.environmental["mean_lst_celsius"],
                    "max_lst_celsius": w.environmental["max_lst_celsius"],
                    "ndvi": w.environmental["ndvi_vegetation_index"],
                    "ndbi": w.environmental["ndbi_builtup_index"],
                    "albedo": w.environmental["surface_albedo"],
                    "tree_canopy_pct": w.environmental["tree_canopy_pct"],
                    "impervious_pct": w.environmental["impervious_surface_pct"],
                    "total_population": w.demographics["total_population"],
                    "population_density": w.demographics["population_density_per_km2"],
                    "poverty_ratio_pct": w.demographics["poverty_ratio_pct"],
                    "slum_households_pct": w.demographics["slum_households_pct"],
                    "ac_penetration_pct": w.adaptive_capacity["ac_penetration_pct"],
                    "cooling_centers_count": w.adaptive_capacity["cooling_centers_count"],
                    "hydration_points_count": w.adaptive_capacity["hydration_points_count"],
                }
                features.append({
                    "type": "Feature",
                    "id": w.ward_id,
                    "geometry": w.geometry,
                    "properties": props,
                })

        # Streets (LineStrings)
        if layer in (None, "streets"):
            for st in self.streets:
                props = {
                    "feature_type": "street_segment",
                    "street_id": st.street_id,
                    "street_name": st.street_name,
                    "ward_id": st.ward_id,
                    "ward_name": st.ward_name,
                    "start_node_id": st.start_node_id,
                    "end_node_id": st.end_node_id,
                    "length_meters": st.length_meters,
                    "street_width_meters": st.street_width_meters,
                    "surface_material": st.surface_material,
                    "surface_albedo": st.surface_albedo,
                    "tree_canopy_shading_ratio": st.tree_canopy_shading_ratio,
                    "shade_ratio": st.shade_ratio,
                    "tree_count": st.tree_count,
                    "solar_orientation": st.solar_orientation,
                    "solar_aspect_label": st.solar_aspect_label,
                    "azimuth_degrees": st.azimuth_degrees,
                    "pedestrian_hourly_volume": st.pedestrian_hourly_volume,
                    "pedestrian_volume": st.pedestrian_volume,
                    "sky_view_factor": st.sky_view_factor,
                    "aspect_ratio_h_w": st.aspect_ratio_h_w,
                    "surface_temp_celsius": st.surface_temp_celsius,
                    "mean_radiant_temp_celsius": st.mean_radiant_temp_celsius,
                    "pedestrian_heat_risk": st.pedestrian_heat_risk,
                    "risk_level": st.risk_level,
                    "has_water_misting": st.has_water_misting,
                }
                features.append({
                    "type": "Feature",
                    "id": st.street_id,
                    "geometry": st.geometry,
                    "properties": props,
                })

        # Cooling Centers (Points)
        if layer in (None, "cooling_centers", "cooling_infrastructure"):
            for cc in self.cooling_centers:
                props = {
                    "feature_type": "cooling_center",
                    "center_id": cc.center_id,
                    "name": cc.name,
                    "facility_type": cc.facility_type,
                    "ward_id": cc.ward_id,
                    "ward_name": cc.ward_name,
                    "address": cc.address,
                    "operating_hours": cc.operating_hours,
                    "capacity_persons": cc.capacity_persons,
                    "current_occupancy": cc.current_occupancy,
                    "indoor_temp_celsius": cc.indoor_temp_celsius,
                    "has_medical_staff": cc.has_medical_staff,
                    "has_backup_generator": cc.has_backup_generator,
                    "wheelchair_accessible": cc.wheelchair_accessible,
                    "phone_contact": cc.phone_contact,
                    "status": cc.status,
                }
                features.append({
                    "type": "Feature",
                    "id": cc.center_id,
                    "geometry": cc.geometry,
                    "properties": props,
                })

        # Hydration Points (Points)
        if layer in (None, "hydration_points", "cooling_infrastructure"):
            for hp in self.hydration_points:
                props = {
                    "feature_type": "hydration_point",
                    "point_id": hp.point_id,
                    "name": hp.name,
                    "water_source_type": hp.water_source_type,
                    "ward_id": hp.ward_id,
                    "ward_name": hp.ward_name,
                    "address": hp.address,
                    "flow_rate_lpm": hp.flow_rate_liters_per_min,
                    "daily_dispensed_liters": hp.daily_dispensed_liters,
                    "status": hp.status,
                    "is_free": hp.is_free,
                    "has_chilled_water": hp.has_chilled_water,
                    "has_misting_fan": hp.has_misting_fan,
                    "operating_hours": hp.operating_hours,
                }
                features.append({
                    "type": "Feature",
                    "id": hp.point_id,
                    "geometry": hp.geometry,
                    "properties": props,
                })

        # Emergency Hospitals (Points)
        if layer in (None, "hospitals"):
            for hosp in self.hospitals:
                features.append({
                    "type": "Feature",
                    "id": hosp["hospital_id"],
                    "geometry": {
                        "type": "Point",
                        "coordinates": [round(hosp["lon"], 6), round(hosp["lat"], 6)],
                    },
                    "properties": {
                        "feature_type": "hospital",
                        **hosp,
                    },
                })

        return {
            "type": "FeatureCollection",
            "metadata": {
                "city": self.city_meta["city_name"],
                "total_features": len(features),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "crs": "EPSG:4326",
            },
            "features": features,
        }


# =============================================================================
# 6. EXPORT HELPERS & ENTRYPOINTS
# =============================================================================

def generate_and_save_dataset(
    output_dir: str = "data",
    seed: int = 42,
    verbose: bool = True,
) -> Dict[str, str]:
    """
    Generate complete synthetic dataset and serialize to disk.
    Creates:
    - data/city_data.json
    - data/city_geojson.json
    - data/wards.geojson
    - data/streets.geojson
    - data/cooling_infrastructure.geojson
    """
    os.makedirs(output_dir, exist_ok=True)

    if verbose:
        print("=" * 76)
        print("  TERRA07 GEOSPATIAL DATA ARCHITECT - BENCHMARK CITY DATA GENERATOR  ")
        print("  Agnitia Hackathon 2026: Heat-Risk Mapping at Human Scale           ")
        print("=" * 76)
        print(f"[*] Target City: Ahmedabad Metropolitan Area, Gujarat, India")
        print(f"[*] Random Seed: {seed}")
        print(f"[*] Ambient Peak Temperature: {BENCHMARK_CITY['baseline_meteorology']['ambient_air_temp_celsius']}°C (May Red Alert)")

    generator = SyntheticGeospatialGenerator(seed=seed)
    generator.generate_all()

    city_data_path = os.path.join(output_dir, "city_data.json")
    city_geojson_path = os.path.join(output_dir, "city_geojson.json")
    wards_geojson_path = os.path.join(output_dir, "wards.geojson")
    streets_geojson_path = os.path.join(output_dir, "streets.geojson")
    cooling_geojson_path = os.path.join(output_dir, "cooling_infrastructure.geojson")

    city_dict = generator.to_city_data_dict()
    with open(city_data_path, "w", encoding="utf-8") as f:
        json.dump(city_dict, f, indent=2, ensure_ascii=False)

    master_geojson = generator.to_geojson_collection()
    with open(city_geojson_path, "w", encoding="utf-8") as f:
        json.dump(master_geojson, f, indent=2, ensure_ascii=False)

    wards_geojson = generator.to_geojson_collection(layer="wards")
    with open(wards_geojson_path, "w", encoding="utf-8") as f:
        json.dump(wards_geojson, f, indent=2, ensure_ascii=False)

    streets_geojson = generator.to_geojson_collection(layer="streets")
    with open(streets_geojson_path, "w", encoding="utf-8") as f:
        json.dump(streets_geojson, f, indent=2, ensure_ascii=False)

    cooling_geojson = generator.to_geojson_collection(layer="cooling_infrastructure")
    with open(cooling_geojson_path, "w", encoding="utf-8") as f:
        json.dump(cooling_geojson, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"\n[+] GENERATION COMPLETED SUCCESSFULLY:")
        print(f"    - Wards generated:              {len(generator.wards)} (distinct typologies: 7)")
        print(f"    - Street segments generated:    {len(generator.streets)}")
        print(f"    - Cooling centers generated:    {len(generator.cooling_centers)}")
        print(f"    - Hydration/misting kiosks:     {len(generator.hydration_points)}")
        print(f"    - Emergency hospitals:          {len(generator.hospitals)}")
        print(f"    - Total GeoJSON features:       {len(master_geojson['features'])}")
        print(f"\n[+] FILES PERSISTED:")
        print(f"    1. {city_data_path} ({os.path.getsize(city_data_path) / 1024:.1f} KB)")
        print(f"    2. {city_geojson_path} ({os.path.getsize(city_geojson_path) / 1024:.1f} KB)")
        print(f"    3. {wards_geojson_path} ({os.path.getsize(wards_geojson_path) / 1024:.1f} KB)")
        print(f"    4. {streets_geojson_path} ({os.path.getsize(streets_geojson_path) / 1024:.1f} KB)")
        print(f"    5. {cooling_geojson_path} ({os.path.getsize(cooling_geojson_path) / 1024:.1f} KB)")
        print("=" * 76)

    return {
        "city_data": city_data_path,
        "city_geojson": city_geojson_path,
        "wards_geojson": wards_geojson_path,
        "streets_geojson": streets_geojson_path,
        "cooling_geojson": cooling_geojson_path,
    }


def generate_city_data(force: bool = True) -> Dict[str, str]:
    """Convenience alias for callers and pipeline integration."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    if not os.path.exists(data_dir):
        data_dir = "data"
    return generate_and_save_dataset(output_dir=data_dir, seed=42, verbose=True)


def main():
    parser = argparse.ArgumentParser(description="TERRA07 Geospatial Synthetic Data Generator")
    parser.add_argument("--output-dir", default="data", help="Output directory for generated datasets (default: data)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation (default: 42)")
    args = parser.parse_args()

    generate_and_save_dataset(output_dir=args.output_dir, seed=args.seed, verbose=True)


if __name__ == "__main__":
    main()
