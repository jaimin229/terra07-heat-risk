"""
Comprehensive Unit & Integration Test Suite for TERRA07 Backend API
Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test GET / returns Agnitia Hackathon TERRA07 branding and healthy status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == "TERRA07 Heat-Risk Intelligence Engine"
    assert "Agnitia Hackathon 2026" in data["project"]
    assert data["team"] == "Team TERRA07"
    assert data["status"] == "healthy"
    assert "endpoints" in data
    assert "city_overview" in data["endpoints"]


def test_api_overview():
    """Test GET /api/overview returns complete city summary."""
    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["city_name"] == "Ahmedabad Metropolitan Region"
    assert data["total_population"] > 0
    assert 0.0 <= data["average_heat_risk"] <= 100.0
    assert "hottest_ward" in data
    assert "coolest_ward" in data
    assert "most_vulnerable_population" in data
    assert data["active_cooling_centers_count"] > 0
    assert data["active_hydration_points_count"] > 0
    assert "Alert" in data["city_alert_level"]


def test_get_wards_json():
    """Test GET /api/wards returns list of wards."""
    response = client.get("/api/wards")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    assert len(data["wards"]) == data["total_count"]
    first_ward = data["wards"][0]
    assert "ward_id" in first_ward
    assert "environmental" in first_ward
    assert "demographics" in first_ward
    assert "adaptive_capacity" in first_ward
    assert "geometry" in first_ward


def test_get_wards_filtered():
    """Test GET /api/wards with zone and min_risk filters."""
    response = client.get("/api/wards?zone=Central&min_risk=40.0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] > 0
    for w in data["wards"]:
        assert "Central" in w["zone"]
        assert w["heat_risk_score"] >= 40.0


def test_get_wards_geojson_format():
    """Test GET /api/wards?format=geojson returns GeoJSON FeatureCollection."""
    response = client.get("/api/wards?format=geojson")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) > 0
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "Polygon"


def test_get_single_ward_valid():
    """Test GET /api/wards/{ward_id} with valid ID."""
    wards_res = client.get("/api/wards")
    first_ward = wards_res.json()["wards"][0]
    response = client.get(f"/api/wards/{first_ward['ward_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["ward_id"] == first_ward["ward_id"]
    assert data["heat_risk_score"] > 0.0


def test_get_single_ward_by_name():
    """Test GET /api/wards/{ward_id} by ward name."""
    wards_res = client.get("/api/wards")
    first_ward = wards_res.json()["wards"][0]
    response = client.get(f"/api/wards/{first_ward['ward_name']}")
    assert response.status_code == 200
    data = response.json()
    assert data["ward_name"] == first_ward["ward_name"]


def test_get_single_ward_invalid():
    """Test GET /api/wards/{ward_id} with non-existent ID returns 404."""
    response = client.get("/api/wards/NON_EXISTENT_WARD_999")
    assert response.status_code == 404
    assert "not found" in response.json()["message"].lower()


def test_get_streets():
    """Test GET /api/streets returns human-scale microclimate segments."""
    response = client.get("/api/streets?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] <= 10
    first = data["streets"][0]
    assert "shade_ratio" in first
    assert "mean_radiant_temp_celsius" in first
    assert "sky_view_factor" in first
    assert "aspect_ratio_h_w" in first
    assert first["geometry"]["type"] == "LineString"


def test_xai_explain_ward():
    """Test GET /api/explain/ward/{id} returns SHAP attribution and diagnosis."""
    wards_res = client.get("/api/wards")
    first_ward = wards_res.json()["wards"][0]
    response = client.get(f"/api/explain/ward/{first_ward['ward_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "ward"
    assert data["entity_id"] == first_ward["ward_id"]
    assert len(data["factor_attributions"]) > 0
    assert data["primary_driver"] != ""
    assert "natural_language_diagnosis" in data
    assert "actionable_policy_insight" in data

    # Factor contributions sum ~ 100%
    pct_sum = sum(f["percentage_contribution"] for f in data["factor_attributions"])
    assert 98.0 <= pct_sum <= 102.0


def test_xai_explain_street():
    """Test GET /api/explain/street/{id}."""
    streets_res = client.get("/api/streets?limit=1")
    first_st = streets_res.json()["streets"][0]
    response = client.get(f"/api/explain/street/{first_st['street_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "street"
    assert len(data["factor_attributions"]) > 0


def test_xai_explain_invalid():
    """Test invalid entity type returns 404."""
    response = client.get("/api/explain/invalid_type/W01")
    assert response.status_code == 404


def test_interventions_recommend():
    """Test POST /api/interventions/recommend returns ranked mitigations and what-if."""
    payload = {
        "budget_inr_lakhs": 350.0,
        "priority_focus": "balanced",
        "max_interventions": 6
    }
    response = client.post("/api/interventions/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_budget_allocated_lakhs"] <= 350.0
    assert len(data["recommendations"]) <= 6
    assert data["total_population_protected"] > 0
    assert "what_if_before_after" in data
    assert data["what_if_before_after"]["post_intervention_city_risk_score"] < data["what_if_before_after"]["baseline_city_risk_score"]


def test_cool_path_routing():
    """Test POST /api/routing/cool-path compares shortest vs cool route."""
    payload = {
        "origin": {"lat": 23.0125, "lon": 72.5830},       # Jamalpur (Central)
        "destination": {"lat": 23.0370, "lon": 72.5560},  # Navrangpura (West)
        "departure_hour": 14,
        "max_detour_factor": 1.5,
        "vulnerability_profile": "elderly"
    }
    response = client.post("/api/routing/cool-path", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "shortest_path" in data
    assert "cool_path" in data
    assert data["heat_stress_reduction_pct"] >= 0.0
    assert data["cool_path"]["average_shade_ratio"] >= data["shortest_path"]["average_shade_ratio"]
    assert len(data["cool_path"]["steps"]) > 0


def test_simulate_scenario():
    """Test POST /api/simulate/scenario runs dynamic stress test."""
    payload = {
        "scenario_type": "extreme_heatwave_4c",
        "temperature_delta_c": 4.0
    }
    response = client.post("/api/simulate/scenario", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "+4.0°C" in data["scenario_name"]
    assert data["simulated_city_average_risk"] > data["baseline_city_average_risk"]
    assert len(data["most_impacted_wards"]) > 0
    assert len(data["operational_emergency_directives"]) > 0


def test_public_advice():
    """Test GET /api/public/advice returns personalized advice & nearest havens."""
    response = client.get("/api/public/advice?lat=23.0125&lon=72.5830&age_group=elderly&activity=outdoor_laborer")
    assert response.status_code == 200
    data = response.json()
    assert data["matched_ward_id"] == "W01"
    assert len(data["nearest_cooling_centers"]) > 0
    assert len(data["nearest_hydration_points"]) > 0
    assert len(data["personalized_clinical_advice"]) > 0
    assert "108" in data["emergency_helpline_numbers"].values()


def test_cooling_centers_list():
    """Test GET /api/cooling-centers."""
    response = client.get("/api/cooling-centers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "address" in data[0]


def test_hydration_points_list():
    """Test GET /api/hydration-points."""
    response = client.get("/api/hydration-points")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["is_free"] is True


def test_static_file_serving():
    """Test static file serving at /static/index.html and /static/planner.js."""
    resp_html = client.get("/static/index.html")
    assert resp_html.status_code == 200
    assert "TERRA07" in resp_html.text

    resp_js = client.get("/static/planner.js")
    assert resp_js.status_code == 200
    assert "TERRA07" in resp_js.text


def test_ui_route():
    """Test /ui and /app routes serving frontend dashboard."""
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "<!DOCTYPE html>" in resp.text


def test_cors_headers():
    """Test CORS headers on preflight requests."""
    response = client.options(
        "/api/overview",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in ["*", "http://localhost:3000"]
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_validation_error_handling():
    """Test 422 error format when sending malformed payload."""
    response = client.post("/api/routing/cool-path", json={"invalid_field": 123})
    assert response.status_code == 422
    data = response.json()
    assert data["status_code"] == 422
    assert data["error"] == "Request Validation Error"
    assert "details" in data

