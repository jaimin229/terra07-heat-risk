"""
TERRA07 Heat-Risk Intelligence Engine - City Data Store & Geospatial Generator
Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale

Target Urban Region: Ahmedabad Metropolitan Region (Historic & Benchmark Heat Action Plan City)
Coordinates: 23.0225° N, 72.5714° E
"""

import json
import math
import os
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CITY_DATA_FILE = os.path.join(DATA_DIR, "city_data.json")
WARDS_GEOJSON_FILE = os.path.join(DATA_DIR, "wards.geojson")
STREETS_GEOJSON_FILE = os.path.join(DATA_DIR, "streets.geojson")

# Realistic wards list with real geographic zones for Ahmedabad
AHMEDABAD_WARDS_SPEC = [
    # Central Zone (Historic high-density, low green cover, high built-up thermal inertia)
    {"id": "W01", "name": "Jamalpur", "zone": "Central", "lat": 23.0125, "lon": 72.5830, "area_km2": 2.8, "pop": 142000, "lst": 44.8, "ndvi": 0.06, "ndbi": 0.58, "albedo": 0.11, "slum_pct": 38.5, "elderly_pct": 11.2, "child_pct": 9.8, "labor_pct": 32.0, "ac_pct": 14.0},
    {"id": "W02", "name": "Khadia", "zone": "Central", "lat": 23.0240, "lon": 72.5910, "area_km2": 2.1, "pop": 115000, "lst": 44.2, "ndvi": 0.05, "ndbi": 0.62, "albedo": 0.12, "slum_pct": 24.0, "elderly_pct": 13.5, "child_pct": 8.2, "labor_pct": 26.5, "ac_pct": 22.0},
    {"id": "W03", "name": "Dariapur", "zone": "Central", "lat": 23.0330, "lon": 72.5930, "area_km2": 2.4, "pop": 138000, "lst": 44.5, "ndvi": 0.05, "ndbi": 0.60, "albedo": 0.11, "slum_pct": 31.0, "elderly_pct": 12.0, "child_pct": 9.5, "labor_pct": 29.0, "ac_pct": 18.0},
    {"id": "W04", "name": "Shahpur", "zone": "Central", "lat": 23.0380, "lon": 72.5810, "area_km2": 2.6, "pop": 128000, "lst": 43.9, "ndvi": 0.07, "ndbi": 0.55, "albedo": 0.12, "slum_pct": 29.0, "elderly_pct": 10.8, "child_pct": 9.1, "labor_pct": 28.0, "ac_pct": 20.0},
    {"id": "W05", "name": "Danilimda", "zone": "Central", "lat": 22.9980, "lon": 72.5850, "area_km2": 4.5, "pop": 195000, "lst": 45.4, "ndvi": 0.04, "ndbi": 0.65, "albedo": 0.10, "slum_pct": 46.0, "elderly_pct": 9.5, "child_pct": 11.2, "labor_pct": 38.0, "ac_pct": 9.5},
    {"id": "W06", "name": "Behrampura", "zone": "Central", "lat": 23.0030, "lon": 72.5740, "area_km2": 3.6, "pop": 162000, "lst": 45.1, "ndvi": 0.05, "ndbi": 0.63, "albedo": 0.10, "slum_pct": 42.0, "elderly_pct": 10.1, "child_pct": 10.5, "labor_pct": 36.0, "ac_pct": 11.0},
    {"id": "W07", "name": "Asarwa", "zone": "Central", "lat": 23.0510, "lon": 72.6050, "area_km2": 3.8, "pop": 149000, "lst": 43.4, "ndvi": 0.09, "ndbi": 0.52, "albedo": 0.13, "slum_pct": 26.0, "elderly_pct": 11.5, "child_pct": 8.8, "labor_pct": 25.0, "ac_pct": 24.0},

    # North Zone (Industrial & residential mixed, elevated heat storage)
    {"id": "W08", "name": "Sardarnagar", "zone": "North", "lat": 23.0780, "lon": 72.6320, "area_km2": 4.9, "pop": 172000, "lst": 43.1, "ndvi": 0.11, "ndbi": 0.50, "albedo": 0.14, "slum_pct": 22.0, "elderly_pct": 9.8, "child_pct": 8.9, "labor_pct": 24.0, "ac_pct": 31.0},
    {"id": "W09", "name": "Naroda", "zone": "North", "lat": 23.0760, "lon": 72.6580, "area_km2": 7.2, "pop": 235000, "lst": 45.6, "ndvi": 0.05, "ndbi": 0.66, "albedo": 0.10, "slum_pct": 35.0, "elderly_pct": 8.7, "child_pct": 10.4, "labor_pct": 39.5, "ac_pct": 16.0},
    {"id": "W10", "name": "Kubernagar", "zone": "North", "lat": 23.0680, "lon": 72.6410, "area_km2": 3.9, "pop": 158000, "lst": 43.8, "ndvi": 0.08, "ndbi": 0.54, "albedo": 0.12, "slum_pct": 28.0, "elderly_pct": 9.9, "child_pct": 9.2, "labor_pct": 27.0, "ac_pct": 25.0},
    {"id": "W11", "name": "Saijpur", "zone": "North", "lat": 23.0590, "lon": 72.6340, "area_km2": 3.7, "pop": 147000, "lst": 43.9, "ndvi": 0.07, "ndbi": 0.56, "albedo": 0.12, "slum_pct": 30.0, "elderly_pct": 9.5, "child_pct": 9.6, "labor_pct": 31.0, "ac_pct": 20.0},
    {"id": "W12", "name": "India Colony", "zone": "North", "lat": 23.0490, "lon": 72.6480, "area_km2": 3.5, "pop": 152000, "lst": 43.6, "ndvi": 0.09, "ndbi": 0.51, "albedo": 0.13, "slum_pct": 21.0, "elderly_pct": 10.2, "child_pct": 8.6, "labor_pct": 23.0, "ac_pct": 34.0},
    {"id": "W13", "name": "Saraspur", "zone": "North", "lat": 23.0360, "lon": 72.6170, "area_km2": 3.1, "pop": 139000, "lst": 44.6, "ndvi": 0.06, "ndbi": 0.59, "albedo": 0.11, "slum_pct": 33.0, "elderly_pct": 10.6, "child_pct": 9.4, "labor_pct": 33.0, "ac_pct": 17.0},

    # East Zone (Dense industrial manufacturing corridor, highest heat load)
    {"id": "W14", "name": "Bapunagar", "zone": "East", "lat": 23.0420, "lon": 72.6350, "area_km2": 3.4, "pop": 182000, "lst": 45.2, "ndvi": 0.05, "ndbi": 0.63, "albedo": 0.11, "slum_pct": 34.0, "elderly_pct": 9.2, "child_pct": 10.1, "labor_pct": 37.0, "ac_pct": 19.0},
    {"id": "W15", "name": "Gomtipur", "zone": "East", "lat": 23.0180, "lon": 72.6190, "area_km2": 3.6, "pop": 164000, "lst": 45.8, "ndvi": 0.04, "ndbi": 0.67, "albedo": 0.10, "slum_pct": 44.0, "elderly_pct": 9.4, "child_pct": 10.8, "labor_pct": 41.0, "ac_pct": 11.5},
    {"id": "W16", "name": "Amraiwadi", "zone": "East", "lat": 23.0070, "lon": 72.6350, "area_km2": 4.1, "pop": 189000, "lst": 45.5, "ndvi": 0.05, "ndbi": 0.65, "albedo": 0.10, "slum_pct": 41.0, "elderly_pct": 8.9, "child_pct": 10.5, "labor_pct": 39.0, "ac_pct": 13.0},
    {"id": "W17", "name": "Odhav", "zone": "East", "lat": 23.0240, "lon": 72.6680, "area_km2": 7.8, "pop": 242000, "lst": 46.2, "ndvi": 0.03, "ndbi": 0.70, "albedo": 0.09, "slum_pct": 39.0, "elderly_pct": 8.1, "child_pct": 11.0, "labor_pct": 44.0, "ac_pct": 12.0},
    {"id": "W18", "name": "Viratnagar", "zone": "East", "lat": 23.0360, "lon": 72.6510, "area_km2": 4.2, "pop": 178000, "lst": 44.9, "ndvi": 0.06, "ndbi": 0.61, "albedo": 0.11, "slum_pct": 31.0, "elderly_pct": 9.1, "child_pct": 9.6, "labor_pct": 35.0, "ac_pct": 21.0},
    {"id": "W19", "name": "Nikol", "zone": "East", "lat": 23.0530, "lon": 72.6680, "area_km2": 6.4, "pop": 210000, "lst": 43.7, "ndvi": 0.10, "ndbi": 0.52, "albedo": 0.13, "slum_pct": 18.0, "elderly_pct": 8.8, "child_pct": 9.0, "labor_pct": 22.0, "ac_pct": 42.0},
    {"id": "W20", "name": "Ramol-Hathijan", "zone": "East", "lat": 22.9850, "lon": 72.6520, "area_km2": 8.5, "pop": 184000, "lst": 44.2, "ndvi": 0.12, "ndbi": 0.49, "albedo": 0.12, "slum_pct": 28.0, "elderly_pct": 8.5, "child_pct": 9.7, "labor_pct": 30.0, "ac_pct": 26.0},

    # South Zone
    {"id": "W21", "name": "Maninagar", "zone": "South", "lat": 22.9990, "lon": 72.6070, "area_km2": 3.9, "pop": 165000, "lst": 42.8, "ndvi": 0.14, "ndbi": 0.46, "albedo": 0.14, "slum_pct": 16.0, "elderly_pct": 13.0, "child_pct": 7.8, "labor_pct": 18.0, "ac_pct": 49.0},
    {"id": "W22", "name": "Kankaria", "zone": "South", "lat": 23.0070, "lon": 72.5980, "area_km2": 3.2, "pop": 136000, "lst": 41.9, "ndvi": 0.22, "ndbi": 0.41, "albedo": 0.15, "slum_pct": 20.0, "elderly_pct": 12.2, "child_pct": 8.1, "labor_pct": 21.0, "ac_pct": 44.0},
    {"id": "W23", "name": "Isanpur", "zone": "South", "lat": 22.9810, "lon": 72.6020, "area_km2": 5.2, "pop": 192000, "lst": 44.1, "ndvi": 0.08, "ndbi": 0.55, "albedo": 0.12, "slum_pct": 32.0, "elderly_pct": 9.8, "child_pct": 9.9, "labor_pct": 33.0, "ac_pct": 25.0},
    {"id": "W24", "name": "Ghodasar", "zone": "South", "lat": 22.9860, "lon": 72.6180, "area_km2": 4.6, "pop": 173000, "lst": 43.5, "ndvi": 0.10, "ndbi": 0.51, "albedo": 0.13, "slum_pct": 24.0, "elderly_pct": 10.5, "child_pct": 8.9, "labor_pct": 26.0, "ac_pct": 36.0},
    {"id": "W25", "name": "Vatva", "zone": "South", "lat": 22.9640, "lon": 72.6320, "area_km2": 9.2, "pop": 256000, "lst": 46.4, "ndvi": 0.04, "ndbi": 0.69, "albedo": 0.09, "slum_pct": 43.0, "elderly_pct": 8.2, "child_pct": 11.4, "labor_pct": 46.0, "ac_pct": 10.5},
    {"id": "W26", "name": "Lambha", "zone": "South", "lat": 22.9480, "lon": 72.5980, "area_km2": 8.8, "pop": 168000, "lst": 44.7, "ndvi": 0.09, "ndbi": 0.58, "albedo": 0.11, "slum_pct": 37.0, "elderly_pct": 8.9, "child_pct": 10.2, "labor_pct": 38.0, "ac_pct": 15.0},

    # West Zone (High vegetation along Sabarmati riverfront & mature neighborhoods)
    {"id": "W27", "name": "Navrangpura", "zone": "West", "lat": 23.0370, "lon": 72.5560, "area_km2": 4.2, "pop": 132000, "lst": 40.5, "ndvi": 0.24, "ndbi": 0.38, "albedo": 0.17, "slum_pct": 8.5, "elderly_pct": 15.2, "child_pct": 6.5, "labor_pct": 12.0, "ac_pct": 74.0},
    {"id": "W28", "name": "Stadium", "zone": "West", "lat": 23.0480, "lon": 72.5640, "area_km2": 3.8, "pop": 129000, "lst": 40.8, "ndvi": 0.22, "ndbi": 0.40, "albedo": 0.16, "slum_pct": 9.0, "elderly_pct": 14.8, "child_pct": 6.8, "labor_pct": 13.0, "ac_pct": 71.0},
    {"id": "W29", "name": "Paldi", "zone": "West", "lat": 23.0120, "lon": 72.5610, "area_km2": 3.9, "pop": 138000, "lst": 41.1, "ndvi": 0.20, "ndbi": 0.42, "albedo": 0.16, "slum_pct": 11.0, "elderly_pct": 14.5, "child_pct": 7.0, "labor_pct": 14.5, "ac_pct": 68.0},
    {"id": "W30", "name": "Vasna", "zone": "West", "lat": 22.9980, "lon": 72.5480, "area_km2": 4.6, "pop": 154000, "lst": 42.2, "ndvi": 0.16, "ndbi": 0.47, "albedo": 0.14, "slum_pct": 22.0, "elderly_pct": 12.0, "child_pct": 8.4, "labor_pct": 22.0, "ac_pct": 48.0},
    {"id": "W31", "name": "Naranpura", "zone": "West", "lat": 23.0570, "lon": 72.5480, "area_km2": 4.1, "pop": 146000, "lst": 41.3, "ndvi": 0.19, "ndbi": 0.44, "albedo": 0.15, "slum_pct": 12.0, "elderly_pct": 14.0, "child_pct": 7.2, "labor_pct": 15.0, "ac_pct": 65.0},
    {"id": "W32", "name": "Nava Vadaj", "zone": "West", "lat": 23.0670, "lon": 72.5690, "area_km2": 3.6, "pop": 143000, "lst": 42.6, "ndvi": 0.14, "ndbi": 0.49, "albedo": 0.13, "slum_pct": 25.0, "elderly_pct": 11.2, "child_pct": 8.7, "labor_pct": 24.0, "ac_pct": 41.0},
    {"id": "W33", "name": "Sabarmati", "zone": "West", "lat": 23.0820, "lon": 72.5850, "area_km2": 5.4, "pop": 162000, "lst": 41.8, "ndvi": 0.21, "ndbi": 0.43, "albedo": 0.15, "slum_pct": 19.0, "elderly_pct": 12.4, "child_pct": 8.1, "labor_pct": 20.0, "ac_pct": 52.0},
    {"id": "W34", "name": "Ranip", "zone": "West", "lat": 23.0760, "lon": 72.5640, "area_km2": 4.8, "pop": 160000, "lst": 42.4, "ndvi": 0.15, "ndbi": 0.48, "albedo": 0.14, "slum_pct": 21.0, "elderly_pct": 11.8, "child_pct": 8.3, "labor_pct": 21.5, "ac_pct": 46.0},

    # North-West Zone
    {"id": "W35", "name": "Ghatlodia", "zone": "North-West", "lat": 23.0690, "lon": 72.5360, "area_km2": 4.5, "pop": 178000, "lst": 41.7, "ndvi": 0.17, "ndbi": 0.46, "albedo": 0.15, "slum_pct": 15.0, "elderly_pct": 12.6, "child_pct": 7.7, "labor_pct": 17.0, "ac_pct": 58.0},
    {"id": "W36", "name": "Memnagar", "zone": "North-West", "lat": 23.0520, "lon": 72.5320, "area_km2": 3.4, "pop": 135000, "lst": 40.9, "ndvi": 0.21, "ndbi": 0.41, "albedo": 0.16, "slum_pct": 9.5, "elderly_pct": 14.1, "child_pct": 6.9, "labor_pct": 13.5, "ac_pct": 72.0},
    {"id": "W37", "name": "Thaltej", "zone": "North-West", "lat": 23.0560, "lon": 72.5080, "area_km2": 6.7, "pop": 182000, "lst": 40.2, "ndvi": 0.26, "ndbi": 0.36, "albedo": 0.18, "slum_pct": 7.0, "elderly_pct": 13.8, "child_pct": 7.1, "labor_pct": 11.0, "ac_pct": 81.0},
    {"id": "W38", "name": "Bodakdev", "zone": "North-West", "lat": 23.0390, "lon": 72.5120, "area_km2": 5.9, "pop": 169000, "lst": 39.8, "ndvi": 0.28, "ndbi": 0.34, "albedo": 0.19, "slum_pct": 6.2, "elderly_pct": 14.5, "child_pct": 6.8, "labor_pct": 10.0, "ac_pct": 86.0},
    {"id": "W39", "name": "Gota", "zone": "North-West", "lat": 23.1020, "lon": 72.5350, "area_km2": 7.4, "pop": 194000, "lst": 42.1, "ndvi": 0.16, "ndbi": 0.49, "albedo": 0.15, "slum_pct": 14.0, "elderly_pct": 10.2, "child_pct": 8.5, "labor_pct": 19.0, "ac_pct": 62.0},
    {"id": "W40", "name": "Chandlodia", "zone": "North-West", "lat": 23.0840, "lon": 72.5440, "area_km2": 4.7, "pop": 158000, "lst": 42.5, "ndvi": 0.14, "ndbi": 0.50, "albedo": 0.14, "slum_pct": 20.0, "elderly_pct": 11.0, "child_pct": 8.6, "labor_pct": 23.0, "ac_pct": 49.0},
    {"id": "W41", "name": "Sola", "zone": "North-West", "lat": 23.0810, "lon": 72.5160, "area_km2": 6.1, "pop": 166000, "lst": 41.2, "ndvi": 0.20, "ndbi": 0.43, "albedo": 0.16, "slum_pct": 11.0, "elderly_pct": 11.8, "child_pct": 7.9, "labor_pct": 16.0, "ac_pct": 70.0},

    # South-West Zone
    {"id": "W42", "name": "Vastrapur", "zone": "South-West", "lat": 23.0330, "lon": 72.5280, "area_km2": 4.1, "pop": 141000, "lst": 40.1, "ndvi": 0.27, "ndbi": 0.35, "albedo": 0.18, "slum_pct": 6.8, "elderly_pct": 14.6, "child_pct": 6.7, "labor_pct": 11.5, "ac_pct": 83.0},
    {"id": "W43", "name": "Jodhpur", "zone": "South-West", "lat": 23.0180, "lon": 72.5240, "area_km2": 5.8, "pop": 179000, "lst": 40.6, "ndvi": 0.23, "ndbi": 0.39, "albedo": 0.17, "slum_pct": 8.0, "elderly_pct": 13.9, "child_pct": 7.0, "labor_pct": 13.0, "ac_pct": 78.0},
    {"id": "W44", "name": "Vejalpur", "zone": "South-West", "lat": 23.0040, "lon": 72.5280, "area_km2": 5.2, "pop": 188000, "lst": 42.3, "ndvi": 0.15, "ndbi": 0.49, "albedo": 0.14, "slum_pct": 23.0, "elderly_pct": 11.5, "child_pct": 8.6, "labor_pct": 25.0, "ac_pct": 47.0},
    {"id": "W45", "name": "Sarkhej", "zone": "South-West", "lat": 22.9860, "lon": 72.5020, "area_km2": 8.2, "pop": 196000, "lst": 43.8, "ndvi": 0.11, "ndbi": 0.55, "albedo": 0.12, "slum_pct": 33.0, "elderly_pct": 9.6, "child_pct": 9.8, "labor_pct": 34.0, "ac_pct": 28.0},
    {"id": "W46", "name": "Maktampur", "zone": "South-West", "lat": 22.9910, "lon": 72.5210, "area_km2": 4.4, "pop": 152000, "lst": 43.2, "ndvi": 0.13, "ndbi": 0.52, "albedo": 0.13, "slum_pct": 29.0, "elderly_pct": 10.4, "child_pct": 9.2, "labor_pct": 29.0, "ac_pct": 33.0},
    {"id": "W47", "name": "Makarba", "zone": "South-West", "lat": 22.9970, "lon": 72.5040, "area_km2": 5.6, "pop": 164000, "lst": 41.5, "ndvi": 0.19, "ndbi": 0.44, "albedo": 0.16, "slum_pct": 14.0, "elderly_pct": 11.5, "child_pct": 7.8, "labor_pct": 18.0, "ac_pct": 64.0},
    {"id": "W48", "name": "Chandkheda", "zone": "North", "lat": 23.1110, "lon": 72.5850, "area_km2": 6.8, "pop": 175000, "lst": 41.4, "ndvi": 0.18, "ndbi": 0.45, "albedo": 0.15, "slum_pct": 15.0, "elderly_pct": 11.0, "child_pct": 8.2, "labor_pct": 17.5, "ac_pct": 61.0},
]


def _generate_ward_polygon(lat: float, lon: float, radius_km: float = 0.8) -> Dict[str, Any]:
    """Generate a realistic hexagonal/octagonal polygon boundary around center."""
    points = []
    num_pts = 8
    # 1 deg lat ~ 111 km, 1 deg lon ~ 102 km at lat 23 deg
    for i in range(num_pts):
        angle = 2 * math.pi * i / num_pts
        # add mild organic perturbation based on index
        perturbation = 0.85 + 0.3 * math.sin(i * 1.7)
        r = (radius_km / 111.0) * perturbation
        d_lat = r * math.sin(angle)
        d_lon = (r / math.cos(math.radians(lat))) * math.cos(angle)
        points.append([round(lon + d_lon, 5), round(lat + d_lat, 5)])
    # close ring
    points.append(points[0])
    return {
        "type": "Polygon",
        "coordinates": [points]
    }


def _calculate_hvi(spec: Dict[str, Any]) -> float:
    """
    IPCC WGII Aligned Composite Heat Vulnerability Index (0-100).
    HVI = 0.35 * Hazard + 0.25 * Exposure + 0.25 * Vulnerability + 0.15 * (1 - AdaptiveCapacity)
    """
    # 1. Hazard (LST 38C -> 0, 48C -> 1.0)
    hazard = max(0.0, min(1.0, (spec["lst"] - 38.0) / 10.0))

    # 2. Exposure (Pop density & NDBI vs NDVI)
    pop_density = spec["pop"] / spec["area_km2"]
    norm_density = max(0.0, min(1.0, (pop_density - 15000) / 45000))
    norm_ndbi = max(0.0, min(1.0, spec["ndbi"]))
    norm_lack_green = max(0.0, min(1.0, (0.35 - spec["ndvi"]) / 0.35))
    exposure = 0.4 * norm_density + 0.3 * norm_ndbi + 0.3 * norm_lack_green

    # 3. Socio-Demographic Vulnerability (Elderly + Child + Labor + Slum)
    vuln = (
        0.25 * min(1.0, spec["slum_pct"] / 50.0) +
        0.25 * min(1.0, spec["labor_pct"] / 50.0) +
        0.25 * min(1.0, spec["elderly_pct"] / 16.0) +
        0.25 * min(1.0, spec["child_pct"] / 12.0)
    )

    # 4. Adaptive Capacity (AC access, infrastructure, albedo)
    adaptive = (
        0.60 * (spec["ac_pct"] / 100.0) +
        0.20 * min(1.0, spec["albedo"] / 0.25) +
        0.20 * (spec["ndvi"] / 0.30)
    )
    adaptive = max(0.05, min(1.0, adaptive))

    # Composite formula
    score = (0.35 * hazard + 0.25 * exposure + 0.25 * vuln + 0.15 * (1.0 - adaptive)) * 100.0
    return round(max(5.0, min(99.0, score)), 1)


def _get_risk_tier(score: float) -> str:
    if score >= 75.0:
        return "Extreme"
    elif score >= 55.0:
        return "High"
    elif score >= 35.0:
        return "Moderate"
    return "Low"


class CityDataStore:
    """In-memory and file-backed cache of urban heat risk infrastructure."""

    def __init__(self):
        self.wards: Dict[str, Dict[str, Any]] = {}
        self.ward_lookup: Dict[str, Dict[str, Any]] = {}
        self.streets: List[Dict[str, Any]] = []
        self.street_lookup: Dict[str, Dict[str, Any]] = {}
        self.intersection_nodes: List[Dict[str, Any]] = []
        self.cooling_centers: List[Dict[str, Any]] = []
        self.hydration_points: List[Dict[str, Any]] = []
        self.hospitals: List[Dict[str, Any]] = []
        self._initialized = False

    def initialize(self):
        """Build or load complete geospatial city model."""
        if self._initialized:
            return

        os.makedirs(DATA_DIR, exist_ok=True)

        if os.path.exists(CITY_DATA_FILE):
            try:
                with open(CITY_DATA_FILE, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    raw_wards = cached_data.get("wards", [])
                    if len(raw_wards) == 48:
                        raw_streets = cached_data.get("streets", [])
                        self.intersection_nodes = cached_data.get("intersection_nodes", [])
                        self.cooling_centers = cached_data.get("cooling_centers", [])
                        self.hydration_points = cached_data.get("hydration_points", [])
                        self.hospitals = cached_data.get("hospitals", [])

                        self._normalize_and_index_wards(raw_wards)
                        self._normalize_and_index_streets(raw_streets)
                        self._initialized = True
                        return
            except Exception as e:
                print(f"[CityDataStore] Failed reading cache, regenerating: {e}")

        self._build_synthetic_dataset()
        self._save_to_disk()
        self._initialized = True

    def _normalize_and_index_wards(self, raw_wards: List[Dict[str, Any]]):
        self.wards.clear()
        self.ward_lookup.clear()
        for w in raw_wards:
            w_id = w["ward_id"]
            self.wards[w_id] = w

            # Ensure centroid lat/lon
            if "lat" not in w or "lon" not in w:
                coords = w.get("geometry", {}).get("coordinates", [[]])[0]
                if coords:
                    w["lon"] = round(sum(p[0] for p in coords) / len(coords), 5)
                    w["lat"] = round(sum(p[1] for p in coords) / len(coords), 5)
                else:
                    w["lat"] = 23.0225
                    w["lon"] = 72.5714

            # Map alias lookups
            aliases = [
                w_id,
                w_id.lower(),
                w_id.upper(),
                w_id.replace("_", ""),
                w_id.replace("WARD_", "W"),
                w_id.replace("WARD_", "W0"),
                w_id.replace("WARD_", ""),
                w["ward_name"].lower(),
                w["ward_name"].upper()
            ]
            # If name is "Jamalpur Old City", also add "jamalpur"
            name_parts = w["ward_name"].lower().split()
            if name_parts:
                aliases.append(name_parts[0])
            for a in aliases:
                self.ward_lookup[a] = w
                self.ward_lookup[a.lower()] = w
                self.ward_lookup[a.upper()] = w

    def _normalize_and_index_streets(self, raw_streets: List[Dict[str, Any]]):
        self.streets = raw_streets
        self.street_lookup.clear()
        for s in self.streets:
            s_id = s["street_id"]
            # Ensure shade_ratio
            shade = s.get("shade_ratio")
            if shade is None:
                shade = s.get("tree_canopy_shading_ratio", 0.35)
            s["shade_ratio"] = round(float(shade), 2)
            s["tree_canopy_shading_ratio"] = s["shade_ratio"]

            # Ensure numeric fields
            s["pedestrian_heat_risk"] = round(float(s.get("pedestrian_heat_risk", 50.0)), 1)
            s["mean_radiant_temp_celsius"] = round(float(s.get("mean_radiant_temp_celsius", 46.0)), 1)
            s["surface_temp_celsius"] = round(float(s.get("surface_temp_celsius", 43.0)), 1)
            s["sky_view_factor"] = round(float(s.get("sky_view_factor", 0.5)), 3)
            s["aspect_ratio_h_w"] = round(float(s.get("aspect_ratio_h_w", 1.2)), 2)
            s["risk_level"] = s.get("risk_level") or _get_risk_tier(s["pedestrian_heat_risk"])
            s["pedestrian_volume"] = s.get("pedestrian_volume", "Moderate")
            s["length_meters"] = round(float(s.get("length_meters", 500.0)), 1)

            # Map aliases
            aliases = [
                s_id,
                s_id.lower(),
                s_id.upper(),
                s_id.replace("_", ""),
                s_id.replace("ST_", "ST"),
                s_id.replace("ST_", ""),
                s["street_name"].lower()
            ]
            for a in aliases:
                self.street_lookup[a] = s
                self.street_lookup[a.lower()] = s
                self.street_lookup[a.upper()] = s

    def get_ward(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Flexible lookup by ID (W01, WARD_01), name, or partial token."""
        if not identifier:
            return None
        # Direct key lookup
        if identifier in self.wards:
            return self.wards[identifier]
        if identifier in self.ward_lookup:
            return self.ward_lookup[identifier]
        key = identifier.strip().lower()
        if key in self.ward_lookup:
            return self.ward_lookup[key]
        upper_key = identifier.strip().upper()
        if upper_key in self.ward_lookup:
            return self.ward_lookup[upper_key]
        # Partial name match
        for w in self.wards.values():
            if key in w["ward_name"].lower() or key in w["ward_id"].lower():
                return w
        return None

    def get_street(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Flexible lookup by street ID (ST001, ST_001) or name."""
        if not identifier:
            return None
        if identifier in self.street_lookup:
            return self.street_lookup[identifier]
        key = identifier.strip().lower()
        if key in self.street_lookup:
            return self.street_lookup[key]
        upper_key = identifier.strip().upper()
        if upper_key in self.street_lookup:
            return self.street_lookup[upper_key]
        for s in self.streets:
            if key in s["street_name"].lower() or key in s["street_id"].lower():
                return s
        return None

    def _build_synthetic_dataset(self):
        # 1. Build Wards
        temp_wards = []
        all_scores = []
        for spec in AHMEDABAD_WARDS_SPEC:
            score = _calculate_hvi(spec)
            all_scores.append(score)
            tier = _get_risk_tier(score)
            pop_density = round(spec["pop"] / spec["area_km2"], 1)
            poly = _generate_ward_polygon(spec["lat"], spec["lon"], radius_km=math.sqrt(spec["area_km2"]))

            # Infrastructure counts
            c_centers = max(1, int(spec["pop"] / 40000))
            h_points = max(2, int(spec["pop"] / 20000))
            clinics = max(1, int(spec["pop"] / 35000))

            # Drivers
            drivers = []
            if spec["lst"] >= 44.0:
                drivers.append("Extreme Land Surface Thermal Hotspot (>44°C)")
            if spec["ndvi"] < 0.08:
                drivers.append("Severe Lack of Vegetative Canopy Cover (<8%)")
            if spec["slum_pct"] >= 30.0:
                drivers.append("High Density Tin-Roof Informal Settlements")
            if spec["ac_pct"] < 25.0:
                drivers.append("Severe Energy Poverty & Low AC Penetration")
            if spec["labor_pct"] >= 30.0:
                drivers.append("High Concentration of Outdoor Informal Laborers")
            if not drivers:
                drivers.append("Urban Heat Island Thermal Retention")

            # Interventions
            interventions = []
            if spec["slum_pct"] >= 25.0:
                interventions.append("Mass High-Albedo Cool Roof Coating Initiative")
            if spec["ndvi"] < 0.12:
                interventions.append("Miyawaki Dense Urban Forestation & Pocket Parks")
            if spec["labor_pct"] >= 25.0:
                interventions.append("Shaded Tension-Sail Bus Shelters & Hydration Kiosks")
            interventions.append("Active AC Cooling Centers with Emergency Power Backup")

            ward_dict = {
                "ward_id": spec["id"],
                "ward_name": spec["name"],
                "zone": spec["zone"],
                "area_km2": spec["area_km2"],
                "heat_risk_score": score,
                "risk_level": tier,
                "risk_percentile": 0.0,  # Computed below
                "environmental": {
                    "mean_lst_celsius": spec["lst"],
                    "max_lst_celsius": round(spec["lst"] + 2.3, 1),
                    "min_lst_celsius": round(spec["lst"] - 2.8, 1),
                    "ndvi_vegetation_index": spec["ndvi"],
                    "ndbi_builtup_index": spec["ndbi"],
                    "surface_albedo": spec["albedo"],
                    "tree_canopy_pct": round(spec["ndvi"] * 100, 1),
                    "impervious_surface_pct": round(spec["ndbi"] * 100 + 15, 1)
                },
                "demographics": {
                    "total_population": spec["pop"],
                    "population_density_per_km2": pop_density,
                    "elderly_pct": spec["elderly_pct"],
                    "children_pct": spec["child_pct"],
                    "outdoor_workers_pct": spec["labor_pct"],
                    "slum_households_pct": spec["slum_pct"],
                    "poverty_ratio_pct": round(spec["slum_pct"] * 0.9, 1),
                    "baseline_heat_illness_rate": round((score / 100.0) * 14.5 + 2.0, 1)
                },
                "adaptive_capacity": {
                    "ac_penetration_pct": spec["ac_pct"],
                    "cooling_centers_count": c_centers,
                    "hydration_points_count": h_points,
                    "hospitals_and_clinics_count": clinics,
                    "distance_to_nearest_hospital_m": round(400 + (100 - spec["ac_pct"]) * 8, 1),
                    "tree_planting_potential_pct": round(max(5.0, (1.0 - spec["ndbi"]) * 45), 1)
                },
                "dominant_heat_drivers": drivers,
                "top_recommended_interventions": interventions,
                "geometry": poly,
                "lat": spec["lat"],
                "lon": spec["lon"]
            }
            temp_wards.append(ward_dict)

        # Compute percentile ranks
        sorted_scores = sorted(all_scores)
        for w in temp_wards:
            score = w["heat_risk_score"]
            rank_idx = sorted_scores.index(score)
            w["risk_percentile"] = round((rank_idx / (len(sorted_scores) - 1)) * 100.0, 1)
            self.wards[w["ward_id"]] = w

        # 2. Build Street Network Segments (High-Density human-scale microclimate)
        self.streets = self._generate_street_network()

        # 3. Build Cooling Centers & Hydration Points & Hospitals
        self.cooling_centers = self._generate_cooling_centers()
        self.hydration_points = self._generate_hydration_points()
        self.hospitals = self._generate_hospitals()

    def _generate_street_network(self) -> List[Dict[str, Any]]:
        """Generate interconnecting street segments between adjacent wards with realistic microclimate attributes."""
        streets = []
        street_counter = 1
        ward_list = list(self.wards.values())

        # Create pairs of nearby wards to build connecting streets
        for i, w1 in enumerate(ward_list):
            for j in range(i + 1, len(ward_list)):
                w2 = ward_list[j]
                # Distance in km
                d_lat = (w2["lat"] - w1["lat"]) * 111.0
                d_lon = (w2["lon"] - w1["lon"]) * 102.0
                dist_km = math.sqrt(d_lat**2 + d_lon**2)

                # Connect if close (< 2.2 km)
                if dist_km <= 2.2:
                    st_id = f"ST{street_counter:03d}"
                    street_name = f"{w1['ward_name']}-{w2['ward_name']} Corridor"

                    # Geometry: LineString from w1 to w2 with midpoint curvature
                    mid_lat = (w1["lat"] + w2["lat"]) / 2.0 + 0.001 * math.sin(street_counter)
                    mid_lon = (w1["lon"] + w2["lon"]) / 2.0 + 0.001 * math.cos(street_counter)

                    geom = {
                        "type": "LineString",
                        "coordinates": [
                            [round(w1["lon"], 5), round(w1["lat"], 5)],
                            [round(mid_lon, 5), round(mid_lat, 5)],
                            [round(w2["lon"], 5), round(w2["lat"], 5)]
                        ]
                    }

                    # Determine street microclimate
                    # High vegetation in ward => higher shade
                    avg_ndvi = (w1["environmental"]["ndvi_vegetation_index"] + w2["environmental"]["ndvi_vegetation_index"]) / 2.0
                    avg_lst = (w1["environmental"]["mean_lst_celsius"] + w2["environmental"]["mean_lst_celsius"]) / 2.0

                    shade_ratio = round(max(0.10, min(0.85, avg_ndvi * 2.2 + 0.08 * (1.0 if "West" in w1["zone"] else 0.4))), 2)
                    svf = round(max(0.25, min(0.92, 1.0 - (shade_ratio * 0.7))), 2)
                    aspect_ratio = round(max(0.4, min(2.8, 1.8 - (svf * 1.3))), 2)

                    # Pedestrian Mean Radiant Temperature Tmrt: Tmrt rises dramatically when exposed to unshaded sun
                    tmrt = round(avg_lst + (1.0 - shade_ratio) * 11.5 + svf * 4.2, 1)
                    ped_risk = round(max(10.0, min(99.0, (tmrt - 40.0) * 4.5 + (1.0 - shade_ratio) * 35.0)), 1)
                    tier = _get_risk_tier(ped_risk)

                    streets.append({
                        "street_id": st_id,
                        "street_name": street_name,
                        "ward_id": w1["ward_id"],
                        "ward_name": w1["ward_name"],
                        "destination_ward_id": w2["ward_id"],
                        "destination_ward_name": w2["ward_name"],
                        "length_meters": round(dist_km * 1000.0, 1),
                        "mean_radiant_temp_celsius": tmrt,
                        "surface_temp_celsius": avg_lst,
                        "shade_ratio": shade_ratio,
                        "sky_view_factor": svf,
                        "aspect_ratio_h_w": aspect_ratio,
                        "pedestrian_heat_risk": ped_risk,
                        "risk_level": tier,
                        "pedestrian_volume": "High" if ("Central" in w1["zone"] or "East" in w1["zone"]) else "Moderate",
                        "tree_count": int(shade_ratio * 80),
                        "has_water_misting": shade_ratio > 0.5,
                        "geometry": geom,
                        "start_coord": [w1["lat"], w1["lon"]],
                        "end_coord": [w2["lat"], w2["lon"]]
                    })
                    street_counter += 1

        # High-density internal street segments for each ward (Commercial Marg & Residential Walk)
        for w in ward_list:
            w_env = w["environmental"]
            w_ndvi = w_env["ndvi_vegetation_index"]
            w_lst = w_env["mean_lst_celsius"]

            # Internal Street 1: Commercial Avenue / Bazaar Marg
            st_id1 = f"ST{street_counter:03d}"
            s1_shade = round(max(0.08, min(0.75, w_ndvi * 1.8 + 0.05)), 2)
            s1_svf = round(max(0.30, min(0.95, 1.0 - (s1_shade * 0.65))), 2)
            s1_tmrt = round(w_lst + (1.0 - s1_shade) * 12.0 + s1_svf * 4.5, 1)
            s1_risk = round(max(10.0, min(99.0, (s1_tmrt - 40.0) * 4.6 + (1.0 - s1_shade) * 36.0)), 1)
            p1_lat = w["lat"] - 0.003
            p1_lon = w["lon"] - 0.002
            p2_lat = w["lat"] + 0.003
            p2_lon = w["lon"] + 0.002
            streets.append({
                "street_id": st_id1,
                "street_name": f"{w['ward_name']} Central Commercial Marg",
                "ward_id": w["ward_id"],
                "ward_name": w["ward_name"],
                "destination_ward_id": w["ward_id"],
                "destination_ward_name": w["ward_name"],
                "length_meters": 720.0,
                "mean_radiant_temp_celsius": s1_tmrt,
                "surface_temp_celsius": w_lst,
                "shade_ratio": s1_shade,
                "sky_view_factor": s1_svf,
                "aspect_ratio_h_w": 1.4,
                "pedestrian_heat_risk": s1_risk,
                "risk_level": _get_risk_tier(s1_risk),
                "pedestrian_volume": "High",
                "tree_count": int(s1_shade * 50),
                "has_water_misting": s1_shade > 0.45,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(p1_lon, 5), round(p1_lat, 5)],
                        [round(w["lon"], 5), round(w["lat"], 5)],
                        [round(p2_lon, 5), round(p2_lat, 5)]
                    ]
                },
                "start_coord": [round(p1_lat, 5), round(p1_lon, 5)],
                "end_coord": [round(p2_lat, 5), round(p2_lon, 5)]
            })
            street_counter += 1

            # Internal Street 2: Green Corridor / Shaded Community Way
            st_id2 = f"ST{street_counter:03d}"
            s2_shade = round(max(0.20, min(0.90, w_ndvi * 2.8 + 0.22)), 2)
            s2_svf = round(max(0.18, min(0.80, 1.0 - (s2_shade * 0.85))), 2)
            s2_tmrt = round(w_lst + (1.0 - s2_shade) * 9.5 + s2_svf * 3.5, 1)
            s2_risk = round(max(10.0, min(95.0, (s2_tmrt - 40.0) * 4.0 + (1.0 - s2_shade) * 28.0)), 1)
            q1_lat = w["lat"] + 0.0025
            q1_lon = w["lon"] - 0.003
            q2_lat = w["lat"] - 0.0025
            q2_lon = w["lon"] + 0.003
            streets.append({
                "street_id": st_id2,
                "street_name": f"{w['ward_name']} Shaded Community Way",
                "ward_id": w["ward_id"],
                "ward_name": w["ward_name"],
                "destination_ward_id": w["ward_id"],
                "destination_ward_name": w["ward_name"],
                "length_meters": 640.0,
                "mean_radiant_temp_celsius": s2_tmrt,
                "surface_temp_celsius": round(w_lst - 2.0, 1),
                "shade_ratio": s2_shade,
                "sky_view_factor": s2_svf,
                "aspect_ratio_h_w": 1.1,
                "pedestrian_heat_risk": s2_risk,
                "risk_level": _get_risk_tier(s2_risk),
                "pedestrian_volume": "Moderate",
                "tree_count": int(s2_shade * 90),
                "has_water_misting": True,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(q1_lon, 5), round(q1_lat, 5)],
                        [round(w["lon"], 5), round(w["lat"], 5)],
                        [round(q2_lon, 5), round(q2_lat, 5)]
                    ]
                },
                "start_coord": [round(q1_lat, 5), round(q1_lon, 5)],
                "end_coord": [round(q2_lat, 5), round(q2_lon, 5)]
            })
            street_counter += 1

        return streets

    def _generate_cooling_centers(self) -> List[Dict[str, Any]]:
        centers = []
        center_id = 1
        facility_types = [
            "AMC Community Hall (AC Active)",
            "Municipal Air-Conditioned Public Library",
            "Dedicated Heat Shelter & Night Home",
            "Metro Station Underground Concourse",
            "Civic Sports Complex Indoor Hall"
        ]
        for w in list(self.wards.values())[:30]:  # 30 primary cooling shelters
            c_type = facility_types[center_id % len(facility_types)]
            c_lat = round(w["lat"] + 0.002 * math.cos(center_id), 5)
            c_lon = round(w["lon"] + 0.002 * math.sin(center_id), 5)
            cap = 250 + (center_id % 4) * 100
            centers.append({
                "center_id": f"CC{center_id:03d}",
                "name": f"{w['ward_name']} {c_type}",
                "facility_type": c_type,
                "ward_id": w["ward_id"],
                "ward_name": w["ward_name"],
                "address": f"Near {w['ward_name']} Civic Centre, Ahmedabad",
                "capacity": cap,
                "capacity_persons": cap,
                "has_ac": True,
                "lat": c_lat,
                "lon": c_lon,
                "coordinates": {
                    "lat": c_lat,
                    "lon": c_lon
                },
                "operating_hours": "09:00 - 21:00 (Extended 24/7 during Red Alert)",
                "has_medical_staff": True if (center_id % 2 == 0) else False,
                "phone_contact": f"+91-79-255{center_id:04d}"
            })
            center_id += 1
        return centers

    def _generate_hydration_points(self) -> List[Dict[str, Any]]:
        points = []
        p_id = 1
        sources = [
            "AMC Chilled Water ATM Kiosk",
            "Public RO Drinking Fountain",
            "Temple Trust Piau (Cool Earthen Matkas)",
            "Bus Rapid Transit (BRTS) Free Water Post",
            "Red Cross Mobile Hydration Booth"
        ]
        for w in list(self.wards.values()):
            # 2 hydration spots per ward
            for k in range(2):
                src = sources[(p_id + k) % len(sources)]
                h_lat = round(w["lat"] + 0.003 * math.sin(p_id * 1.5), 5)
                h_lon = round(w["lon"] + 0.003 * math.cos(p_id * 1.5), 5)
                points.append({
                    "point_id": f"HY{p_id:03d}",
                    "name": f"{w['ward_name']} {src}",
                    "water_source_type": src,
                    "ward_id": w["ward_id"],
                    "ward_name": w["ward_name"],
                    "lat": h_lat,
                    "lon": h_lon,
                    "coordinates": {
                        "lat": h_lat,
                        "lon": h_lon
                    },
                    "status": "Operational & Inspected Daily",
                    "is_free": True
                })
                p_id += 1
        return points

    def _generate_hospitals(self) -> List[Dict[str, Any]]:
        hospitals = [
            {"name": "Civil Hospital Asarwa (Apex Trauma & Heatstroke Center)", "lat": 23.0520, "lon": 72.6060, "beds": 2000, "heat_icu": 50},
            {"name": "VS General Hospital Paldi", "lat": 23.0160, "lon": 72.5680, "beds": 750, "heat_icu": 30},
            {"name": "SVP Hospital Ellisbridge", "lat": 23.0230, "lon": 72.5710, "beds": 1500, "heat_icu": 40},
            {"name": "LG General Hospital Maninagar", "lat": 22.9960, "lon": 72.6080, "beds": 650, "heat_icu": 25},
            {"name": "Shardaben General Hospital Saraspur", "lat": 23.0370, "lon": 72.6190, "beds": 500, "heat_icu": 20},
            {"name": "Sola Civil Hospital", "lat": 23.0830, "lon": 72.5180, "beds": 700, "heat_icu": 25}
        ]
        return hospitals

    def _save_to_disk(self):
        try:
            full_data = {
                "system": "TERRA07 Heat-Risk Intelligence",
                "city": "Ahmedabad",
                "wards": list(self.wards.values()),
                "streets": self.streets,
                "cooling_centers": self.cooling_centers,
                "hydration_points": self.hydration_points,
                "hospitals": self.hospitals
            }
            with open(CITY_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(full_data, f, indent=2)

            # Also write GeoJSON for Wards
            features = []
            for w in self.wards.values():
                features.append({
                    "type": "Feature",
                    "id": w["ward_id"],
                    "geometry": w["geometry"],
                    "properties": {
                        "ward_id": w["ward_id"],
                        "ward_name": w["ward_name"],
                        "zone": w["zone"],
                        "heat_risk_score": w["heat_risk_score"],
                        "risk_level": w["risk_level"],
                        "mean_lst_celsius": w["environmental"]["mean_lst_celsius"],
                        "ndvi": w["environmental"]["ndvi_vegetation_index"],
                        "total_population": w["demographics"]["total_population"],
                        "slum_households_pct": w["demographics"]["slum_households_pct"],
                        "ac_penetration_pct": w["adaptive_capacity"]["ac_penetration_pct"]
                    }
                })
            geojson_data = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "city": "Ahmedabad",
                    "total_wards": len(features),
                    "crs": "EPSG:4326"
                }
            }
            with open(WARDS_GEOJSON_FILE, "w", encoding="utf-8") as f:
                json.dump(geojson_data, f, indent=2)

            # Also write GeoJSON for Streets
            street_features = []
            for s in self.streets:
                street_features.append({
                    "type": "Feature",
                    "id": s["street_id"],
                    "geometry": s["geometry"],
                    "properties": {
                        "street_id": s["street_id"],
                        "street_name": s["street_name"],
                        "ward_id": s["ward_id"],
                        "length_meters": s["length_meters"],
                        "shade_ratio": s["shade_ratio"],
                        "pedestrian_heat_risk": s["pedestrian_heat_risk"],
                        "mean_radiant_temp_celsius": s["mean_radiant_temp_celsius"],
                        "risk_level": s["risk_level"]
                    }
                })
            street_geojson = {
                "type": "FeatureCollection",
                "features": street_features,
                "metadata": {
                    "city": "Ahmedabad",
                    "total_streets": len(street_features),
                    "crs": "EPSG:4326"
                }
            }
            with open(STREETS_GEOJSON_FILE, "w", encoding="utf-8") as f:
                json.dump(street_geojson, f, indent=2)

            print(f"[CityDataStore] Saved city data to {CITY_DATA_FILE} ({len(self.wards)} wards, {len(self.streets)} streets)")
        except Exception as e:
            print(f"[CityDataStore] Warning: failed saving to disk: {e}")


# Singleton instance
store = CityDataStore()
