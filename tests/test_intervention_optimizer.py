"""
Comprehensive Test Suite for Urban Intervention & Resource Allocation Optimizer
Team TERRA07 - Software Track: Heat-Risk Mapping at Human Scale
"""

import math
import pytest
from engine.intervention_optimizer import (
    INTERVENTION_CATALOG,
    InterventionType,
    InterventionSpec,
    UrbanZone,
    ZoneUrgencyRank,
    InterventionAllocation,
    OptimizationResult,
    WhatIfZoneResult,
    WhatIfPortfolioResult,
    InterventionOptimizer,
    create_sample_urban_zones,
)


class TestInterventionCatalog:
    """Validates catalog definitions against mission specifications."""

    def test_catalog_has_all_five_interventions(self):
        expected_keys = {
            InterventionType.SHADE_SAILS.value,
            InterventionType.MISTING_KIOSKS.value,
            InterventionType.COOLING_CENTER.value,
            InterventionType.URBAN_FORESTRY.value,
            InterventionType.COOL_ROOF.value,
        }
        assert set(INTERVENTION_CATALOG.keys()) == expected_keys

    def test_shade_sails_specifications(self):
        spec = INTERVENTION_CATALOG[InterventionType.SHADE_SAILS.value]
        assert spec.unit_cost == 8000.0
        assert spec.unit_name == "street"
        assert spec.temp_reduction_surface_c == 4.5
        assert "48h" in spec.setup_time_desc
        assert "vendor" in spec.best_for.lower() or "traffic" in spec.best_for.lower()

    def test_misting_kiosks_specifications(self):
        spec = INTERVENTION_CATALOG[InterventionType.MISTING_KIOSKS.value]
        assert spec.unit_cost == 4500.0
        assert spec.unit_name == "point"
        assert spec.dehydration_heatstroke_reduction_pct == 65.0
        assert "72h" in spec.setup_time_desc
        assert "transit" in spec.best_for.lower() or "labor" in spec.best_for.lower()

    def test_cooling_center_specifications(self):
        spec = INTERVENTION_CATALOG[InterventionType.COOLING_CENTER.value]
        assert spec.unit_cost == 25000.0
        assert spec.unit_name == "center"
        assert spec.capacity_people_per_unit == 300
        assert "immediate" in spec.setup_time_desc.lower()
        assert "elderly" in spec.best_for.lower() or "informal" in spec.best_for.lower()

    def test_urban_forestry_specifications(self):
        spec = INTERVENTION_CATALOG[InterventionType.URBAN_FORESTRY.value]
        assert spec.unit_cost == 12000.0
        assert spec.unit_name == "km"
        assert spec.temp_reduction_ambient_c == 3.8
        assert spec.temp_reduction_surface_c == 7.0
        assert "seasonal" in spec.setup_time_desc.lower()
        assert "avenue" in spec.best_for.lower()

    def test_cool_roof_specifications(self):
        spec = INTERVENTION_CATALOG[InterventionType.COOL_ROOF.value]
        assert spec.unit_cost == 1200.0
        assert spec.unit_name == "household"
        assert spec.temp_reduction_ambient_c == 3.5  # Indoor temp reduction
        assert "tin-roof" in spec.best_for.lower() or "informal" in spec.best_for.lower()

    def test_spec_dict_serialization(self):
        for spec in INTERVENTION_CATALOG.values():
            d = spec.to_dict()
            assert isinstance(d, dict)
            assert d["id"] == spec.id
            assert d["unit_cost"] == spec.unit_cost


class TestUrbanZoneModel:
    """Validates UrbanZone initialization, bounds, and auto-computed capacities."""

    def test_valid_zone_creation(self):
        zone = UrbanZone(
            zone_id="Z-01",
            name="Test Ward",
            zone_type="informal_settlement",
            current_risk_score=85.0,
            baseline_ambient_temp_c=42.0,
            baseline_surface_temp_c=50.0,
            total_population=10000,
            vulnerable_population=3000,
            area_sq_km=1.0,
            tin_roof_pct=60.0,
        )
        assert zone.zone_id == "Z-01"
        assert zone.current_risk_score == 85.0
        assert zone.max_cooling_centers >= 1
        assert zone.max_cool_roof_households > 0
        assert zone.get_max_units("cool_roof") > 0

    def test_clamped_bounds(self):
        zone = UrbanZone(
            zone_id="Z-BOUNDS",
            name="Bounds Ward",
            zone_type="vendor_market",
            current_risk_score=150.0,  # exceeds 100
            baseline_ambient_temp_c=40.0,
            baseline_surface_temp_c=48.0,
            total_population=-50,      # negative
            vulnerable_population=999999,  # exceeds total
            area_sq_km=0.0,            # zero area
        )
        assert zone.current_risk_score == 100.0
        assert zone.total_population >= 1
        assert zone.vulnerable_population <= zone.total_population
        assert zone.area_sq_km > 0.0


class TestPriorityRankingAlgorithm:
    """Validates the Priority Ranking by Urgency algorithm."""

    @pytest.fixture
    def optimizer(self):
        return InterventionOptimizer()

    @pytest.fixture
    def sample_zones(self):
        return create_sample_urban_zones()

    def test_ranking_sorts_by_urgency_descending(self, optimizer, sample_zones):
        ranked = optimizer.rank_zones_by_urgency(sample_zones)
        assert len(ranked) == len(sample_zones)

        # Check descending order
        for i in range(len(ranked) - 1):
            assert ranked[i].urgency_score >= ranked[i + 1].urgency_score
            assert ranked[i].rank == i + 1

    def test_informal_slum_ranked_highest_urgency(self, optimizer, sample_zones):
        ranked = optimizer.rank_zones_by_urgency(sample_zones)
        # Ward A (tin-roof informal settlement with highest risk and 9,200 vulnerable) should be #1
        assert ranked[0].zone_id == "WARD-A-SLUM"
        assert ranked[0].urgency_score > 75.0

    def test_low_risk_suburb_ranked_lowest(self, optimizer, sample_zones):
        ranked = optimizer.rank_zones_by_urgency(sample_zones)
        # Ward F (planned residential suburb, low heat risk) should be last
        assert ranked[-1].zone_id == "WARD-F-SUBURB"
        assert ranked[-1].urgency_score < ranked[0].urgency_score

    def test_tailored_intervention_recommendations(self, optimizer, sample_zones):
        ranked = optimizer.rank_zones_by_urgency(sample_zones)
        slum_rank = next(r for r in ranked if r.zone_id == "WARD-A-SLUM")
        market_rank = next(r for r in ranked if r.zone_id == "WARD-B-MARKET")
        transit_rank = next(r for r in ranked if r.zone_id == "WARD-C-TRANSIT")
        avenue_rank = next(r for r in ranked if r.zone_id == "WARD-E-AVENUE")

        # Slum should have cool roof as top recommendation
        top_slum_int = slum_rank.recommended_interventions[0].intervention_id
        assert top_slum_int in (InterventionType.COOL_ROOF.value, InterventionType.COOLING_CENTER.value)

        # Market should have shade sails or misting kiosks high up
        market_int_ids = [rec.intervention_id for rec in market_rank.recommended_interventions[:2]]
        assert InterventionType.SHADE_SAILS.value in market_int_ids or InterventionType.MISTING_KIOSKS.value in market_int_ids

        # Transit hub should favor misting kiosks
        transit_top = transit_rank.recommended_interventions[0].intervention_id
        assert transit_top == InterventionType.MISTING_KIOSKS.value

        # Wide avenue should favor urban forestry
        avenue_top = avenue_rank.recommended_interventions[0].intervention_id
        assert avenue_top == InterventionType.URBAN_FORESTRY.value

    def test_empty_zones_returns_empty_list(self, optimizer):
        assert optimizer.rank_zones_by_urgency([]) == []


class TestKnapsackOptimizer:
    """Validates budget-constrained optimization, capacity limits, and ROI metrics."""

    @pytest.fixture
    def optimizer(self):
        return InterventionOptimizer()

    @pytest.fixture
    def sample_zones(self):
        return create_sample_urban_zones()

    def test_budget_100k_strict_adherence(self, optimizer, sample_zones):
        budget = 100000.0
        result = optimizer.optimize_budget(sample_zones, total_budget=budget)

        assert result.total_cost_spent <= budget
        assert result.remaining_budget >= 0.0
        assert result.total_cost_spent + result.remaining_budget == pytest.approx(budget, rel=1e-3)
        assert result.total_lives_protected > 0
        assert result.total_effective_heat_reduction_deg_c > 0.0
        assert len(result.allocations) > 0

    def test_budget_500k_strict_adherence(self, optimizer, sample_zones):
        budget = 500000.0
        result = optimizer.optimize_budget(sample_zones, total_budget=budget)

        assert result.total_cost_spent <= budget
        assert result.remaining_budget >= 0.0
        assert result.total_lives_protected > 2000
        assert result.budget_utilization_pct >= 90.0

    def test_zero_or_negative_budget(self, optimizer, sample_zones):
        result_zero = optimizer.optimize_budget(sample_zones, total_budget=0.0)
        assert result_zero.total_cost_spent == 0.0
        assert result_zero.total_lives_protected == 0
        assert len(result_zero.allocations) == 0

        result_neg = optimizer.optimize_budget(sample_zones, total_budget=-10000.0)
        assert result_neg.total_cost_spent == 0.0

    def test_roi_metrics_accuracy(self, optimizer, sample_zones):
        budget = 150000.0
        result = optimizer.optimize_budget(sample_zones, total_budget=budget)

        # Expected formula: (lives / cost) * 10,000
        expected_lives_roi = (result.total_lives_protected / result.total_cost_spent) * 10000.0
        assert result.lives_protected_per_10k_spent == pytest.approx(expected_lives_roi, rel=1e-2)

        # Degrees celsius reduction per dollar: deg_c / cost
        expected_temp_roi = result.total_effective_heat_reduction_deg_c / result.total_cost_spent
        assert result.degrees_celsius_reduction_per_dollar == pytest.approx(expected_temp_roi, rel=1e-4)

    def test_physical_capacities_not_exceeded(self, optimizer, sample_zones):
        budget = 1000000.0  # Large $1M budget
        result = optimizer.optimize_budget(sample_zones, total_budget=budget)

        # Sum allocated units per zone and verify against zone capacities
        alloc_map = {}
        for alloc in result.allocations:
            alloc_map[(alloc.zone_id, alloc.intervention_id)] = alloc.unit_count

        zone_dict = {z.zone_id: z for z in sample_zones}
        for (z_id, int_id), count in alloc_map.items():
            zone = zone_dict[z_id]
            max_allowed = zone.get_max_units(int_id)
            assert count <= max_allowed, f"Allocated {count} > max {max_allowed} for {int_id} in {z_id}"

    def test_objectives_change_allocation_priorities(self, optimizer, sample_zones):
        budget = 120000.0
        res_lives = optimizer.optimize_budget(sample_zones, total_budget=budget, objective="max_lives")
        res_heat = optimizer.optimize_budget(sample_zones, total_budget=budget, objective="max_heat_reduction")

        assert res_lives.total_cost_spent <= budget
        assert res_heat.total_cost_spent <= budget
        # Under max_lives, lives protected should be at least as high or higher
        assert res_lives.total_lives_protected >= res_heat.total_lives_protected


class TestWhatIfSimulation:
    """Validates microclimate recalculation, risk reduction, and diminishing returns."""

    @pytest.fixture
    def optimizer(self):
        return InterventionOptimizer()

    @pytest.fixture
    def test_zone(self):
        return UrbanZone(
            zone_id="TEST-WARD",
            name="Test Slum Ward",
            zone_type="informal_settlement",
            current_risk_score=85.0,
            baseline_ambient_temp_c=43.0,
            baseline_surface_temp_c=52.0,
            total_population=20000,
            vulnerable_population=6000,
            area_sq_km=1.0,
            tin_roof_pct=75.0,
            max_cool_roof_households=500,
            max_cooling_centers=3,
        )

    def test_no_interventions_yields_baseline(self, optimizer, test_zone):
        sim = optimizer.simulate_what_if(test_zone, {})
        assert sim.projected_risk_score == test_zone.current_risk_score
        assert sim.risk_score_reduction == 0.0
        assert sim.projected_ambient_temp_c == test_zone.baseline_ambient_temp_c
        assert sim.projected_surface_temp_c == test_zone.baseline_surface_temp_c
        assert sim.lives_protected == 0

    def test_deployment_strictly_reduces_risk(self, optimizer, test_zone):
        deployments = {
            InterventionType.COOL_ROOF.value: 150,
            InterventionType.COOLING_CENTER.value: 2,
            InterventionType.MISTING_KIOSKS.value: 4,
        }
        sim = optimizer.simulate_what_if(test_zone, deployments)

        assert sim.projected_risk_score < test_zone.current_risk_score
        assert sim.risk_score_reduction > 0.0
        assert sim.projected_ambient_temp_c < test_zone.baseline_ambient_temp_c
        assert sim.projected_surface_temp_c < test_zone.baseline_surface_temp_c
        assert sim.lives_protected > 0
        assert sim.lives_protected <= test_zone.vulnerable_population

    def test_diminishing_returns(self, optimizer, test_zone):
        # Adding 50 roofs vs adding 200 roofs
        sim_50 = optimizer.simulate_what_if(test_zone, {InterventionType.COOL_ROOF.value: 50})
        sim_200 = optimizer.simulate_what_if(test_zone, {InterventionType.COOL_ROOF.value: 200})

        marginal_gain_first_50 = sim_50.surface_temp_reduction_c / 50.0
        marginal_gain_next_150 = (sim_200.surface_temp_reduction_c - sim_50.surface_temp_reduction_c) / 150.0

        # Marginal gain per unit of the first 50 must be greater than subsequent units
        assert marginal_gain_first_50 >= marginal_gain_next_150

    def test_portfolio_simulation(self, optimizer):
        zones = create_sample_urban_zones()
        portfolio_deployments = {
            "WARD-A-SLUM": {"cool_roof": 200, "cooling_center": 1},
            "WARD-B-MARKET": {"shade_sails": 5, "misting_kiosks": 4},
            "WARD-C-TRANSIT": {"misting_kiosks": 6},
        }

        portfolio_sim = optimizer.simulate_portfolio_what_if(zones, portfolio_deployments)

        assert portfolio_sim.total_cost > 0.0
        assert portfolio_sim.total_lives_protected > 0
        assert portfolio_sim.average_projected_risk < portfolio_sim.average_baseline_risk
        assert portfolio_sim.average_risk_reduction_points > 0.0
        assert len(portfolio_sim.zone_results) == len(zones)


class TestScenariosAndReporting:
    """Validates scenario comparisons and executive summary generation."""

    @pytest.fixture
    def optimizer(self):
        return InterventionOptimizer()

    @pytest.fixture
    def sample_zones(self):
        return create_sample_urban_zones()

    def test_budget_scenarios_frontier(self, optimizer, sample_zones):
        budgets = [50000.0, 100000.0, 250000.0, 500000.0]
        comp = optimizer.compare_budget_scenarios(sample_zones, budgets)

        assert comp["scenario_count"] == 4
        scenarios = comp["scenarios"]

        # Increasing budget must protect equal or more lives
        for i in range(len(scenarios) - 1):
            assert scenarios[i]["cost_spent"] <= scenarios[i + 1]["cost_spent"]
            assert scenarios[i]["lives_protected"] <= scenarios[i + 1]["lives_protected"]

    def test_executive_summary_contains_essential_information(self, optimizer, sample_zones):
        ranked = optimizer.rank_zones_by_urgency(sample_zones)
        res = optimizer.optimize_budget(sample_zones, total_budget=100000.0)
        summary = optimizer.generate_executive_summary(res, ranked)

        assert "TERRA07 Heat Mitigation Resource Allocation Briefing" in summary
        assert "$100,000" in summary or "100,000.00" in summary
        assert "Vulnerable Lives Protected" in summary
        assert "Capital Efficiency (ROI)" in summary
        assert "Shanti Nagar" in summary or "WARD-A-SLUM" in summary

    def test_full_json_exportability(self, optimizer, sample_zones):
        res = optimizer.optimize_budget(sample_zones, total_budget=200000.0)
        d = res.to_dict()
        assert isinstance(d, dict)
        assert "total_budget" in d
        assert "roi" in d
        assert "allocations" in d
        assert "zone_reports" in d
        assert len(d["allocations"]) > 0
