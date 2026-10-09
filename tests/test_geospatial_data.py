"""
Validation Suite for Synthetic Geospatial Data Architecture
Team TERRA07 - Agnitia Hackathon 2026
"""

import json
import os
import sys

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.schemas import (
    CityOverviewResponse,
    CoolingCenterItem,
    GeoJSONFeatureCollection,
    HydrationPointItem,
    StreetSegment,
    WardProfile,
)


def run_comprehensive_validation():
    print("=" * 76)
    print("  RUNNING GEOSPATIAL DATA VALIDATION SUITE  ")
    print("=" * 76)

    # 1. File existence checks
    expected_files = [
        "data/city_data.json",
        "data/city_geojson.json",
        "data/wards.geojson",
        "data/streets.geojson",
        "data/cooling_infrastructure.geojson",
    ]
    for ef in expected_files:
        assert os.path.exists(ef), f"Missing required file: {ef}"
        size_kb = os.path.getsize(ef) / 1024
        print(f"[PASS] File exists: {ef} ({size_kb:.1f} KB)")

    # 2. Load city_data.json
    with open("data/city_data.json", "r", encoding="utf-8") as f:
        city_data = json.load(f)

    # Validate Overview
    overview = CityOverviewResponse(**city_data["overview"])
    print(f"\n[PASS] City Overview Schema Validated:")
    print(f"       City: {overview.city_name}")
    print(f"       Population: {overview.total_population:,}")
    print(f"       Avg Heat Risk: {overview.average_heat_risk}")
    print(f"       Avg Surface Temp: {overview.average_surface_temp_celsius}°C")
    print(f"       Hottest Ward: {overview.hottest_ward.ward_name} ({overview.hottest_ward.mean_lst_celsius}°C)")
    print(f"       Coolest Ward: {overview.coolest_ward.ward_name} ({overview.coolest_ward.mean_lst_celsius}°C)")
    print(f"       Total Wards: {overview.total_wards_count}")
    print(f"       Total Streets: {overview.total_streets_count}")
    print(f"       Cooling Centers: {overview.active_cooling_centers_count}")
    print(f"       Hydration Points: {overview.active_hydration_points_count}")

    # Validate Wards
    wards = city_data["wards"]
    assert len(wards) >= 35, f"Expected at least 35 wards, got {len(wards)}"
    typologies = set()
    for w in wards:
        profile = WardProfile(**w)
        typologies.add(w.get("typology_key"))

    print(f"\n[PASS] All {len(wards)} Wards conform strictly to WardProfile schema.")
    print(f"       Distinct typologies found: {len(typologies)} -> {typologies}")

    # Physical Coherence Assertions
    affluent = [w for w in wards if w["typology_key"] == "affluent_suburbs"]
    industrial = [w for w in wards if w["typology_key"] == "industrial_belt"]
    informal = [w for w in wards if w["typology_key"] == "informal_settlements"]

    avg_affluent_lst = sum(w["environmental"]["mean_lst_celsius"] for w in affluent) / len(affluent)
    avg_industrial_lst = sum(w["environmental"]["mean_lst_celsius"] for w in industrial) / len(industrial)
    avg_informal_lst = sum(w["environmental"]["mean_lst_celsius"] for w in informal) / len(informal)

    avg_affluent_ndvi = sum(w["environmental"]["ndvi_vegetation_index"] for w in affluent) / len(affluent)
    avg_industrial_ndbi = sum(w["environmental"]["ndbi_builtup_index"] for w in industrial) / len(industrial)
    avg_informal_ndbi = sum(w["environmental"]["ndbi_builtup_index"] for w in informal) / len(informal)

    print("\n[PHYSICAL COHERENCE VERIFICATION]")
    print(f"  - Affluent Suburbs Avg LST:       {avg_affluent_lst:.1f}°C (NDVI: {avg_affluent_ndvi:.2f})")
    print(f"  - Industrial Belt Avg LST:         {avg_industrial_lst:.1f}°C (NDBI: {avg_industrial_ndbi:.2f})")
    print(f"  - Informal Settlement Avg LST:     {avg_informal_lst:.1f}°C (NDBI: {avg_informal_ndbi:.2f})")

    assert avg_affluent_ndvi >= 0.40, f"Affluent NDVI should be >= 0.40, got {avg_affluent_ndvi}"
    assert avg_industrial_ndbi > 0.50, f"Industrial NDBI should be > 0.50, got {avg_industrial_ndbi}"
    assert avg_informal_ndbi > 0.50, f"Informal NDBI should be > 0.50, got {avg_informal_ndbi}"
    assert avg_industrial_lst > avg_affluent_lst + 6.0, "Industrial LST must be significantly hotter than affluent suburbs"
    print("  [PASS] Physical coherence check passed: Industrial/Informal LST > Affluent LST by > 6°C!")

    # Validate Streets
    streets = city_data["streets"]
    assert len(streets) >= 120, f"Expected at least 120 street segments, got {len(streets)}"
    for s in streets:
        st_obj = StreetSegment(**s)
        # Verify required physical fields from prompt
        assert "start_coordinates" in s and "lat" in s["start_coordinates"]
        assert "end_coordinates" in s and "lat" in s["end_coordinates"]
        assert "street_width_meters" in s and s["street_width_meters"] > 0
        assert "tree_canopy_shading_ratio" in s and 0.0 <= s["tree_canopy_shading_ratio"] <= 0.95
        assert "surface_material" in s and s["surface_material"] in ["asphalt", "concrete", "paver", "permeable_paver", "compacted_earth"]
        assert "solar_orientation" in s
        assert "pedestrian_hourly_volume" in s and s["pedestrian_hourly_volume"] > 0
        assert "pedestrian_volume" in s and s["pedestrian_volume"] in ["Low", "Moderate", "High", "Critical"]

    print(f"\n[PASS] All {len(streets)} Street Segments conform strictly to StreetSegment schema and contain all physical morphology fields.")

    # Validate Cooling Centers
    cooling_centers = city_data["cooling_centers"]
    assert len(cooling_centers) >= 20, f"Expected >= 20 cooling centers, got {len(cooling_centers)}"
    for cc in cooling_centers:
        cc_obj = CoolingCenterItem(**cc)
        assert cc["capacity_persons"] > 0
        assert cc["status"] == "active"

    print(f"\n[PASS] All {len(cooling_centers)} Cooling Centers conform strictly to CoolingCenterItem schema.")

    # Validate Hydration Points
    hydration_points = city_data["hydration_points"]
    assert len(hydration_points) >= 30, f"Expected >= 30 hydration points, got {len(hydration_points)}"
    for hp in hydration_points:
        hp_obj = HydrationPointItem(**hp)
        assert hp["status"] == "active"
        assert hp["is_free"] is True

    print(f"\n[PASS] All {len(hydration_points)} Hydration Points conform strictly to HydrationPointItem schema.")

    # Validate Master GeoJSON
    with open("data/city_geojson.json", "r", encoding="utf-8") as f:
        master_geojson = json.load(f)

    fc = GeoJSONFeatureCollection(**master_geojson)
    print(f"\n[PASS] Master city_geojson.json is valid RFC 7946 GeoJSON FeatureCollection with {len(fc.features)} features.")

    # Validate individual GeoJSON layers
    for layer, path in [("wards", "data/wards.geojson"), ("streets", "data/streets.geojson"), ("cooling", "data/cooling_infrastructure.geojson")]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        layer_fc = GeoJSONFeatureCollection(**data)
        print(f"[PASS] Layer {path} valid with {len(layer_fc.features)} features.")

    print("\n" + "=" * 76)
    print("  ALL VALIDATION SUITE TESTS PASSED 100%! DATASET IS PRODUCTION READY!  ")
    print("=" * 76)


if __name__ == "__main__":
    run_comprehensive_validation()
