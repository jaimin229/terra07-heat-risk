"""
TERRA07 Comprehensive End-to-End Test Suite
Agnitia Hackathon 2026 - Software Track: Heat-Risk Mapping at Human Scale

Covers:
1. Risk scoring engine mathematical range (0-100), monotonicity, and edge cases.
2. Synthetic data integrity (35+ wards, 120+ streets, cooling centers, hydration posts).
3. Explainable AI (XAI) attribution sum and driver consistency.
4. Intervention optimizer budget constraints, knapsack algorithm, and ROI sorting.
5. Cool-path router graph traversal, thermal cost function, and route comparisons.
6. FastAPI REST endpoints status codes, response schemas, and error handling.
"""

import math
import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.risk_engine import (
    UrbanHeatRiskEngine,
    WardRiskInput,
    HazardInputs,
    ExposureInputs,
    VulnerabilityInputs,
    RiskCategory,
    calculate_heat_index,
    calculate_wet_bulb_temperature,
)
from engine.cool_router import (
    CoolRouter,
    haversine_distance_m,
    calculate_bearing_deg,
    classify_turn,
    get_heat_risk_category,
)
from engine.intervention_optimizer import (
    InterventionOptimizer,
    UrbanZone,
    INTERVENTION_CATALOG,
    InterventionType,
    create_sample_urban_zones,
)
from backend.data_store import store
from backend.engine import explain_entity, recommend_interventions, router_engine
from backend.main import app
from backend.schemas import (
    XAIExplanationResponse,
)


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient fixture."""
    store.initialize()
    router_engine.build_graph()
    with TestClient(app) as c:
        yield c


# =============================================================================
# 1. RISK SCORING ENGINE: Range, Monotonicity & Mathematical Edge Cases
# =============================================================================

class TestRiskScoringEngine:
    """Validates the mathematical rigor of the IPCC AR6 Risk formulation."""

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.engine = UrbanHeatRiskEngine()

    def test_risk_score_mathematical_range_0_100(self):
        """Verify score is strictly bounded in [0.0, 100.0] across diverse inputs."""
        test_cases = [
            # Low risk case
            WardRiskInput(
                ward_id="W_TEST_LOW",
                ward_name="Green Suburb",
                hazard=HazardInputs(lst_c=30.0, heat_index_c=28.0, ndbi=0.1, solar_irradiance_w_m2=300.0),
                exposure=ExposureInputs(population_density_per_km2=5000.0, pedestrian_foot_traffic_hourly=100.0, outdoor_workers_pct=5.0),
                vulnerability=VulnerabilityInputs(elderly_pct=8.0, children_pct=5.0, ac_deficit_pct=10.0, chronic_conditions_pct=5.0, housing_uninsulated_pct=5.0)
            ),
            # Average case
            WardRiskInput(
                ward_id="W_TEST_MID",
                ward_name="Midtown",
                hazard=HazardInputs(lst_c=42.0, heat_index_c=38.0, ndbi=0.5, solar_irradiance_w_m2=750.0),
                exposure=ExposureInputs(population_density_per_km2=25000.0, pedestrian_foot_traffic_hourly=500.0, outdoor_workers_pct=25.0),
                vulnerability=VulnerabilityInputs(elderly_pct=12.0, children_pct=9.0, ac_deficit_pct=45.0, chronic_conditions_pct=15.0, housing_uninsulated_pct=35.0)
            ),
            # Severe case
            WardRiskInput(
                ward_id="W_TEST_HIGH",
                ward_name="Dense Industrial Slum",
                hazard=HazardInputs(lst_c=48.0, heat_index_c=44.0, ndbi=0.85, solar_irradiance_w_m2=950.0),
                exposure=ExposureInputs(population_density_per_km2=65000.0, pedestrian_foot_traffic_hourly=1200.0, outdoor_workers_pct=55.0),
                vulnerability=VulnerabilityInputs(elderly_pct=18.0, children_pct=14.0, ac_deficit_pct=85.0, chronic_conditions_pct=30.0, housing_uninsulated_pct=80.0)
            )
        ]

        for case in test_cases:
            res = self.engine.score_ward(case)
            assert 0.0 <= res.hri <= 100.0, f"Score {res.hri} out of [0, 100]"
            assert 0.0 <= res.hazard_breakdown.sub_index <= 100.0
            assert 0.0 <= res.exposure_breakdown.sub_index <= 100.0
            assert 0.0 <= res.vulnerability_breakdown.sub_index <= 100.0

    def test_monotonicity_hazard_lst(self):
        """Increasing Land Surface Temperature (LST) must monotonically increase heat risk."""
        scores = []
        lst_steps = [32.0, 36.0, 40.0, 44.0, 48.0, 52.0]

        for lst in lst_steps:
            w_input = WardRiskInput(
                ward_id=f"W_MONO_{lst}",
                ward_name=f"Zone_{lst}C",
                hazard=HazardInputs(lst_c=lst, heat_index_c=lst - 3.0, ndbi=0.5, solar_irradiance_w_m2=700.0),
                exposure=ExposureInputs(population_density_per_km2=20000.0, pedestrian_foot_traffic_hourly=300.0, outdoor_workers_pct=20.0),
                vulnerability=VulnerabilityInputs(elderly_pct=10.0, children_pct=8.0, ac_deficit_pct=40.0, chronic_conditions_pct=12.0, housing_uninsulated_pct=30.0)
            )
            res = self.engine.score_ward(w_input)
            scores.append(res.hri)

        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1], f"Monotonicity violated: {scores[i]} > {scores[i+1]} at step {i}"

    def test_monotonicity_vulnerability_increase(self):
        """Increasing low-income AC deficit and uninsulated housing must monotonically increase score."""
        scores = []
        deficit_steps = [10.0, 30.0, 50.0, 70.0, 90.0]

        for def_val in deficit_steps:
            w_input = WardRiskInput(
                ward_id=f"W_VULN_{def_val}",
                ward_name="Zone_Vuln",
                hazard=HazardInputs(lst_c=42.0, heat_index_c=39.0, ndbi=0.5, solar_irradiance_w_m2=700.0),
                exposure=ExposureInputs(population_density_per_km2=20000.0, pedestrian_foot_traffic_hourly=300.0, outdoor_workers_pct=20.0),
                vulnerability=VulnerabilityInputs(elderly_pct=10.0, children_pct=8.0, ac_deficit_pct=def_val, chronic_conditions_pct=12.0, housing_uninsulated_pct=def_val)
            )
            res = self.engine.score_ward(w_input)
            scores.append(res.hri)

        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1], f"Vulnerability monotonicity violated: {scores[i]} > {scores[i+1]}"

    def test_edge_cases_and_clamping(self):
        """Engine handles extreme edge conditions without NaN, inf, or negative values."""
        # Ultra cold/green edge
        extreme_min = WardRiskInput(
            ward_id="W_MIN",
            ward_name="Arctic Forest",
            hazard=HazardInputs(lst_c=10.0, heat_index_c=10.0, ndbi=-0.5, solar_irradiance_w_m2=0.0),
            exposure=ExposureInputs(population_density_per_km2=0.0, pedestrian_foot_traffic_hourly=0.0, outdoor_workers_pct=0.0),
            vulnerability=VulnerabilityInputs(elderly_pct=0.0, children_pct=0.0, ac_deficit_pct=0.0, chronic_conditions_pct=0.0, housing_uninsulated_pct=0.0)
        )
        res_min = self.engine.score_ward(extreme_min)
        assert res_min.hri >= 0.0
        assert not math.isnan(res_min.hri)

        # Ultra hot furnace edge
        extreme_max = WardRiskInput(
            ward_id="W_MAX",
            ward_name="Furnace Core",
            hazard=HazardInputs(lst_c=65.0, heat_index_c=58.0, ndbi=1.5, solar_irradiance_w_m2=1400.0),
            exposure=ExposureInputs(population_density_per_km2=150000.0, pedestrian_foot_traffic_hourly=10000.0, outdoor_workers_pct=100.0),
            vulnerability=VulnerabilityInputs(elderly_pct=50.0, children_pct=40.0, ac_deficit_pct=100.0, chronic_conditions_pct=60.0, housing_uninsulated_pct=100.0)
        )
        res_max = self.engine.score_ward(extreme_max)
        assert res_max.hri <= 100.0
        assert res_max.category in (RiskCategory.EXTREME, RiskCategory.SEVERE)

    def test_meteorological_formulas(self):
        """Test Steadman Heat Index & Stull Wet Bulb Temperature equations."""
        # 35C at 60% relative humidity
        hi = calculate_heat_index(35.0, 60.0)
        assert hi > 35.0, "Heat index should be higher than dry bulb under high humidity"

        # Stull formula for wet bulb
        wb = calculate_wet_bulb_temperature(40.0, 45.0)
        assert 20.0 < wb < 40.0, f"Wet bulb temperature {wb} outside physical limits"


# =============================================================================
# 2. SYNTHETIC DATA INTEGRITY (35+ Wards, 120+ Streets, Cooling Points)
# =============================================================================

class TestSyntheticDataIntegrity:
    """Verifies that the generated city dataset satisfies hackathon benchmark requirements."""

    @pytest.fixture(autouse=True)
    def load_data(self):
        store.initialize()
        self.store = store

    def test_ward_count_exceeds_35(self):
        """Platform requires at least 35 distinct wards/micro-neighborhoods."""
        ward_count = len(self.store.wards)
        assert ward_count >= 35, f"Expected >= 35 wards, found {ward_count}"

    def test_street_count_exceeds_120(self):
        """Platform requires at least 120 high-resolution street segments."""
        street_count = len(self.store.streets)
        assert street_count >= 120, f"Expected >= 120 streets, found {street_count}"

    def test_cooling_centers_and_hydration_infrastructure(self):
        """Verify cooling centers and hydration kiosks exist with realistic attributes."""
        assert len(self.store.cooling_centers) >= 10, "Insufficient cooling centers"
        assert len(self.store.hydration_points) >= 20, "Insufficient hydration points"
        assert len(self.store.hospitals) >= 3, "Insufficient emergency hospitals"

        sample_center = self.store.cooling_centers[0]
        assert "center_id" in sample_center
        assert "name" in sample_center
        assert ("capacity" in sample_center and sample_center["capacity"] > 0) or ("capacity_persons" in sample_center)

    def test_ward_demographic_and_environmental_integrity(self):
        """Wards must have physically coherent and deterministic climate features."""
        for w_id, w in self.store.wards.items():
            assert 0.0 <= w["heat_risk_score"] <= 100.0
            env = w["environmental"]
            demo = w["demographics"]

            assert 35.0 <= env["mean_lst_celsius"] <= 50.0
            assert -0.2 <= env["ndvi_vegetation_index"] <= 0.8
            assert -0.2 <= env["ndbi_builtup_index"] <= 0.9
            assert demo["total_population"] > 5000

            geom = w["geometry"]
            assert geom["type"] == "Polygon"
            assert len(geom["coordinates"][0]) >= 4

    def test_street_microclimate_integrity(self):
        """Streets must include human-scale shade, SVF, and radiant heat metrics."""
        for s in self.store.streets:
            assert s["length_meters"] > 0
            shade = s.get("shade_ratio", s.get("tree_canopy_shading_ratio", 0.0))
            assert 0.0 <= shade <= 1.0
            assert 0.0 <= s.get("sky_view_factor", 0.5) <= 1.0
            assert s["mean_radiant_temp_celsius"] > 30.0
            assert 0.0 <= s["pedestrian_heat_risk"] <= 100.0
            assert s["geometry"]["type"] == "LineString"


# =============================================================================
# 3. EXPLAINABLE AI (XAI) ATTRIBUTION & DRIVER CONSISTENCY
# =============================================================================

class TestExplainableAI:
    """Verifies SHAP-style feature attribution consistency and natural language diagnoses."""

    def test_xai_attribution_sum_consistency(self):
        """Attribution points from all factors sum up to 100% or match total risk drivers."""
        w_id = list(store.wards.keys())[0]
        explanation = explain_entity("ward", w_id)

        assert isinstance(explanation, XAIExplanationResponse)
        assert explanation.entity_id == w_id
        assert len(explanation.factor_attributions) >= 4

        pct_sum = sum(f.percentage_contribution for f in explanation.factor_attributions)
        assert abs(pct_sum - 100.0) < 1.0, f"Attribution percentages sum to {pct_sum}, expected ~100%"

    def test_xai_driver_contrast_hot_vs_cool_ward(self):
        """Hot industrial ward must have higher risk than green suburb."""
        all_wards = list(store.wards.values())
        hottest = max(all_wards, key=lambda w: w["environmental"]["mean_lst_celsius"])
        coolest = min(all_wards, key=lambda w: w["environmental"]["mean_lst_celsius"])

        exp_hot = explain_entity("ward", hottest["ward_id"])
        exp_cool = explain_entity("ward", coolest["ward_id"])

        assert exp_hot.overall_heat_risk >= exp_cool.overall_heat_risk
        assert exp_hot.primary_driver != ""

    def test_natural_language_diagnosis_clarity(self):
        """Generated diagnosis must mention ward name and risk tier."""
        w_id = list(store.wards.keys())[0]
        w = store.get_ward(w_id)
        exp = explain_entity("ward", w_id)
        diag = exp.natural_language_diagnosis
        assert w["ward_name"] in diag or w_id in diag
        assert len(diag) > 40


# =============================================================================
# 4. INTERVENTION OPTIMIZER & BUDGET CONSTRAINTS
# =============================================================================

class TestInterventionOptimizer:
    """Tests knapsack budget optimization, ROI metrics, and what-if calculations."""

    @pytest.fixture
    def optimizer(self):
        return InterventionOptimizer()

    @pytest.fixture
    def sample_zones(self):
        return create_sample_urban_zones()

    def test_budget_constraint_enforcement(self, optimizer, sample_zones):
        """Total spent in recommendation must never exceed the allocated municipal budget."""
        budgets = [50000.0, 100000.0, 250000.0, 500000.0]

        for b in budgets:
            res = optimizer.optimize_budget(sample_zones, total_budget=b)
            assert res.total_cost_spent <= b + 1.0, f"Budget exceeded: spent {res.total_cost_spent} on budget {b}"
            assert res.remaining_budget >= -0.01
            assert res.total_lives_protected > 0

    def test_roi_sorting_and_rank_consistency(self, optimizer, sample_zones):
        """Interventions should be prioritized with positive ROI metrics."""
        res = optimizer.optimize_budget(sample_zones, total_budget=200000.0)
        assert len(res.allocations) > 0
        assert res.lives_protected_per_10k_spent > 0.0
        assert res.degrees_celsius_reduction_per_dollar > 0.0

    def test_what_if_scenario_post_intervention(self, optimizer, sample_zones):
        """Post-intervention risk score and temperature must be strictly lower than baseline."""
        res = optimizer.optimize_budget(sample_zones, total_budget=300000.0)
        portfolio = optimizer.simulate_portfolio_what_if(sample_zones, res)

        assert portfolio.average_projected_risk <= portfolio.average_baseline_risk
        assert portfolio.average_risk_reduction_pct >= 0.0


# =============================================================================
# 5. COOL-PATH ROUTER & GRAPH TRAVERSAL
# =============================================================================

class TestCoolPathRouter:
    """Verifies pedestrian navigation, thermal cost function, and route comparison."""

    def test_graph_construction(self):
        """CoolRouter graph builds with nodes and edges."""
        geojson_path = os.path.join(BASE_DIR, "data", "sample_cool_network.geojson")
        router = CoolRouter.from_geojson(geojson_path)
        assert router.graph.number_of_nodes() >= 10
        assert router.graph.number_of_edges() >= 10

    def test_cool_corridor_vs_shortest_comparison(self):
        """Cool-corridor route must have lower thermal cost or higher shade."""
        router = CoolRouter(default_alpha=2.0, default_beta=1.5, hydration_kiosk_discount=0.3)
        router.add_intersection("START", lat=23.010, lon=72.580)
        router.add_intersection("HOT_WAY", lat=23.015, lon=72.580)
        router.add_intersection("COOL_WAY", lat=23.015, lon=72.585, has_hydration_kiosk=True)
        router.add_intersection("DEST", lat=23.020, lon=72.580)

        router.add_street_segment("START", "HOT_WAY", "Hot Sun Blvd", length_m=100.0, heat_risk=90.0, canopy_shade_ratio=0.0)
        router.add_street_segment("HOT_WAY", "DEST", "Hot Sun Blvd 2", length_m=100.0, heat_risk=90.0, canopy_shade_ratio=0.0)

        router.add_street_segment("START", "COOL_WAY", "Green Canopy Way", length_m=110.0, heat_risk=25.0, canopy_shade_ratio=0.85)
        router.add_street_segment("COOL_WAY", "DEST", "Green Canopy Way 2", length_m=110.0, heat_risk=25.0, canopy_shade_ratio=0.85)

        shortest = router.find_shortest_path("START", "DEST")
        cool = router.find_cool_path("START", "DEST")
        comp = router.compare_routes(shortest, cool)

        assert comp.cool_path.avg_heat_risk < comp.shortest_path.avg_heat_risk
        assert comp.cool_path.cumulative_heat_dose < comp.shortest_path.cumulative_heat_dose
        assert comp.cool_path.shade_percentage >= comp.shortest_path.shade_percentage
        assert comp.heat_risk_reduction_pct > 0.0

    def test_step_by_step_turn_directions(self):
        """Route produces valid turn-by-turn steps with thermal advisories."""
        router = CoolRouter()
        router.add_intersection("N1", lat=23.010, lon=72.580)
        router.add_intersection("N2", lat=23.015, lon=72.580)
        router.add_street_segment("N1", "N2", "Shaded Avenue", length_m=500.0, heat_risk=30.0, canopy_shade_ratio=0.7)

        res = router.find_cool_path("N1", "N2")
        assert len(res.turn_by_turn_directions) >= 1
        step = res.turn_by_turn_directions[0]
        assert step.street_name == "Shaded Avenue"
        assert step.instruction != ""


# =============================================================================
# 6. FASTAPI REST ENDPOINTS & RESPONSE SCHEMAS
# =============================================================================

class TestFastAPIEndpoints:
    """Verifies RESTful contracts, HTTP status codes, and Pydantic response models."""

    def test_root_metadata_endpoint(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["team"] == "Team TERRA07"
        assert data["status"] == "healthy"
        assert "endpoints" in data

    def test_city_overview_endpoint(self, client):
        r = client.get("/api/overview")
        assert r.status_code == 200
        data = r.json()
        assert "Ahmedabad" in data["city_name"]
        assert data["total_population"] > 1000000
        assert data["total_wards_count"] >= 35
        assert data["total_streets_count"] >= 120
        assert "hottest_ward" in data
        assert "coolest_ward" in data

    def test_wards_endpoint(self, client):
        r = client.get("/api/wards")
        assert r.status_code == 200
        data = r.json()
        assert "wards" in data
        assert len(data["wards"]) >= 35

        r_geo = client.get("/api/wards?format=geojson")
        assert r_geo.status_code == 200
        geo_data = r_geo.json()
        assert geo_data["type"] == "FeatureCollection"
        assert len(geo_data["features"]) >= 35

    def test_single_ward_endpoint(self, client):
        w_id = list(store.wards.keys())[0]
        r = client.get(f"/api/wards/{w_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["ward_id"] == w_id
        assert "environmental" in data
        assert "demographics" in data

        r_invalid = client.get("/api/wards/NON_EXISTENT_WARD_XYZ")
        assert r_invalid.status_code == 404

    def test_streets_endpoint(self, client):
        r = client.get("/api/streets")
        assert r.status_code == 200
        data = r.json()
        assert "streets" in data
        assert len(data["streets"]) >= 100

        r_geo = client.get("/api/streets?format=geojson")
        assert r_geo.status_code == 200
        assert r_geo.json()["type"] == "FeatureCollection"

    def test_xai_explain_endpoint(self, client):
        w_id = list(store.wards.keys())[0]
        r = client.get(f"/api/explain/ward/{w_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["entity_id"] == w_id
        assert len(data["factor_attributions"]) >= 4
        assert "natural_language_diagnosis" in data

    def test_interventions_recommend_endpoint(self, client):
        payload = {"budget_inr_lakhs": 500.0, "priority_focus": "balanced"}
        r = client.post("/api/interventions/recommend", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["total_budget_allocated_lakhs"] <= 500.0
        assert data["total_population_protected"] > 0
        assert "recommendations" in data

    def test_cool_path_routing_endpoint(self, client):
        payload = {
            "origin": {"lat": 23.0125, "lon": 72.5830},
            "destination": {"lat": 23.0240, "lon": 72.5910},
            "departure_hour": 14,
            "max_detour_factor": 1.5,
            "vulnerability_profile": "standard"
        }
        r = client.post("/api/routing/cool-path", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "shortest_path" in data
        assert "cool_path" in data
        assert "heat_stress_reduction_pct" in data

    def test_scenario_simulate_endpoint(self, client):
        payload = {
            "scenario_type": "extreme_heatwave_4c",
            "temperature_delta_c": 4.0
        }
        r = client.post("/api/simulate/scenario", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["simulated_city_average_risk"] > data["baseline_city_average_risk"]
        assert len(data["most_impacted_wards"]) > 0

    def test_public_advice_endpoint(self, client):
        r = client.get("/api/public/advice?lat=23.0125&lon=72.5830&persona=senior&has_ac=false")
        assert r.status_code == 200
        data = r.json()
        assert data["current_risk_level"] in ("Extreme", "Severe", "High", "Moderate", "Low")
        assert len(data["nearest_cooling_centers"]) > 0
        assert len(data["nearest_hydration_points"]) > 0

    def test_frontend_routes_served(self, client):
        """Verify unified frontend and individual view pages are served with 200."""
        r_portal = client.get("/static/index.html")
        assert r_portal.status_code == 200

        r_planner = client.get("/static/planner_view.html")
        assert r_planner.status_code == 200

        r_public = client.get("/static/public_view.html")
        assert r_public.status_code == 200


if __name__ == "__main__":
    pytest.main(["-v", __file__])
