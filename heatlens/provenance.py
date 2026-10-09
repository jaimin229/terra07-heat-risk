"""Data provenance logger for HeatLens (Team TERRA07)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from heatlens.config import PROJECT_ROOT

PROVENANCE_FILE = PROJECT_ROOT / "data" / "processed" / "provenance.json"


def get_default_provenance(city: str = "Ahmedabad") -> Dict[str, Any]:
    """Returns official provenance metadata for the real data sources utilized in HeatLens."""
    return {
        "project": "HeatLens (TERRA07)",
        "study_area": city,
        "bounding_box": [72.54, 22.99, 72.62, 23.06],
        "grid_resolution_meters": 250,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "is_synthetic": False,
        "sources": [
            {
                "name": "Landsat 8/9 Collection 2 Level-2 Surface Temperature (LST)",
                "provider": "USGS / NASA via Microsoft Planetary Computer STAC",
                "collection_id": "landsat-c2-l2",
                "bands": ["lwir11 (TIRS Band 10)", "red (Band 4)", "nir08 (Band 5)", "swir16 (Band 6)", "qa_pixel"],
                "resolution": "30 m (resampled from 100 m thermal sensor)",
                "date_range": "April 1 - June 30 (2023, 2024, 2025)",
                "overpass_time_local": "~10:45 AM local solar time",
                "license": "Public Domain (USGS Open Data Policy)",
                "caveat": "Relative morning surface heating; does not represent 3 PM peak air temperature."
            },
            {
                "name": "Overture Maps & OpenStreetMap Building Footprints",
                "provider": "Overture Maps Foundation / OpenStreetMap Contributors",
                "type": "Building coverage polygon layer",
                "resolution": "Vector polygon geometry",
                "license": "ODbL / CDLA Permissive 2.0",
                "metric_derived": "building_coverage fraction per 250 m grid cell"
            },
            {
                "name": "WorldPop High-Resolution Age-Sex Population Structure",
                "provider": "WorldPop Project / University of Southampton",
                "product": "India Constrained 100m Age/Sex Pyramids (2020 projection)",
                "resolution": "100 m raster cell",
                "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
                "cohorts_used": ["pop_total", "pop_65plus (sum of 65, 70, 75, 80+)", "pop_u5 (sum of 0, 1-4)"],
                "caveat": "Modelled dasymetric statistical surface, not house-to-house census records."
            },
            {
                "name": "OpenStreetMap Amenities & Walking Network",
                "provider": "OpenStreetMap Contributors via OSMnx / Overpass API",
                "features": ["amenity=drinking_water", "amenity=community_centre", "amenity=hospital", "highway=bus_stop", "landuse=commercial/industrial"],
                "license": "Open Data Commons Open Database License (ODbL)",
                "metric_derived": "Walking distance to nearest water point and cooling center via Dijkstra network graph; outdoor activity proxy."
            },
            {
                "name": "Open-Meteo Weather Forecast & Reanalysis",
                "provider": "Open-Meteo.com (ECMWF IFS / DWD ICON integration)",
                "resolution": "Seamless global 1-11 km model grid",
                "license": "Non-commercial CC BY 4.0 / Open Data",
                "metric_derived": "Live 7-day max temperature, feels-like heat index, and IMD heatwave alert tiers."
            }
        ]
    }


def write_provenance(city: str = "Ahmedabad", output_path: Path = PROVENANCE_FILE) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prov = get_default_provenance(city)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(prov, f, indent=2)
    return prov
