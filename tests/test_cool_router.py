import os
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import networkx as nx
from engine.cool_router import (
    CoolRouter,
    haversine_distance_m,
    calculate_bearing_deg,
    classify_turn,
    get_heat_risk_category,
    RouteResult,
    RouteComparison,
)


class TestSpatialHelpers:
    """Test geometry, distance, and bearing calculations."""

    def test_haversine_distance(self):
        # Distance between two nearby coordinates in San Francisco (~111 meters)
        lat1, lon1 = 37.774900, -122.419400
        lat2, lon2 = 37.775800, -122.419400
        dist = haversine_distance_m(lat1, lon1, lat2, lon2)
        assert 90.0 < dist < 115.0

    def test_calculate_bearing(self):
        # Due North
        bearing_north = calculate_bearing_deg(37.0, -122.0, 38.0, -122.0)
        assert abs(bearing_north - 0.0) < 1.0 or abs(bearing_north - 360.0) < 1.0

        # Due East
        bearing_east = calculate_bearing_deg(37.0, -122.0, 37.0, -121.0)
        assert abs(bearing_east - 90.0) < 1.0

    def test_classify_turn(self):
        # Heading north (0 deg), continuing north (0 deg) -> straight
        t_type, verb = classify_turn(0.0, 5.0)
        assert t_type == "straight"

        # Heading north (0 deg), turning east (90 deg) -> right
        t_type, verb = classify_turn(0.0, 90.0)
        assert t_type == "right"
        assert "right" in verb.lower()

        # Heading north (0 deg), turning west (270 deg / -90 deg) -> left
        t_type, verb = classify_turn(0.0, 270.0)
        assert t_type == "left"
        assert "left" in verb.lower()

    def test_get_heat_risk_category(self):
        assert get_heat_risk_category(20.0) == "Low"
        assert get_heat_risk_category(45.0) == "Moderate"
        assert get_heat_risk_category(70.0) == "High"
        assert get_heat_risk_category(85.0) == "Extreme"


class TestGraphConstruction:
    """Test building intersections and street segments."""

    def test_add_intersection_and_segment(self):
        router = CoolRouter()
        router.add_intersection("A", lat=37.7749, lon=-122.4194, name="Point A", has_hydration_kiosk=True)
        router.add_intersection("B", lat=37.7759, lon=-122.4194, name="Point B")

        # Auto-compute distance
        router.add_street_segment(
            u="A",
            v="B",
            street_name="Oak Street",
            heat_risk=40.0,
            canopy_shade_ratio=0.7,
            hydration_points=1,
            bidirectional=True,
        )

        assert router.graph.has_node("A")
        assert router.graph.has_node("B")
        assert router.graph.has_edge("A", "B")
        assert router.graph.has_edge("B", "A")

        edge_data = router.graph["A"]["B"]
        assert edge_data["street_name"] == "Oak Street"
        assert edge_data["heat_risk"] == 40.0
        assert edge_data["canopy_shade_ratio"] == 0.7
        assert edge_data["hydration_points"] == 1
        assert edge_data["length_m"] > 50.0

    def test_invalid_node_edge_addition(self):
        router = CoolRouter()
        router.add_intersection("A", lat=37.7749, lon=-122.4194)
        with pytest.raises(ValueError):
            router.add_street_segment("A", "NON_EXISTENT", street_name="Ghost Road")


class TestCostFunction:
    """Test thermal exposure cost function behavior."""

    def test_cost_function_weights(self):
        router = CoolRouter(default_alpha=2.0, default_beta=1.5, hydration_kiosk_discount=0.3)
        router.add_intersection("N1", lat=37.0, lon=-122.0)
        router.add_intersection("N2", lat=37.01, lon=-122.0)
        router.add_intersection("N3", lat=37.02, lon=-122.0, has_hydration_kiosk=True)

        # Hot unshaded edge
        router.add_street_segment("N1", "N2", "Hot Road", length_m=100.0, heat_risk=90.0, canopy_shade_ratio=0.0)
        hot_cost = router.compute_edge_cool_cost("N1", "N2")

        # Cool shaded edge with water
        router.add_street_segment("N2", "N3", "Cool Road", length_m=100.0, heat_risk=30.0, canopy_shade_ratio=0.8)
        cool_cost = router.compute_edge_cool_cost("N2", "N3")

        # Hot road cost must be substantially higher than cool road cost for same distance
        assert hot_cost > cool_cost
        assert hot_cost > 100.0  # length * (1 + 2.0*0.9) = 280
        assert cool_cost < 100.0  # benefits from shade and hydration bonus

    def test_cost_function_positive_floor(self):
        router = CoolRouter(min_cost_factor=0.15)
        router.add_intersection("A", 37.0, -122.0)
        router.add_intersection("B", 37.01, -122.0, has_hydration_kiosk=True)
        # Even with extreme shade and zero heat risk, cost cannot be negative or zero
        router.add_street_segment("A", "B", "Ice Tunnel", length_m=100.0, heat_risk=0.0, canopy_shade_ratio=1.0, hydration_points=3)
        cost = router.compute_edge_cool_cost("A", "B")
        assert cost >= 100.0 * 0.15


class TestRoutingAndComparisons:
    """Test shortest vs cool-corridor routing differences."""

    @pytest.fixture
    def diamond_network(self):
        """
        Creates a diamond test network:
        Source: S (0, 0)
        Target: T (0, 2)
        Path 1 (Hot Direct): S -> M1 -> T.
          - Length: 200m
          - Heat Risk: 92.0 (Extreme)
          - Shade: 5% (0.05)
          - Hydration: 0
        Path 2 (Cool Corridor): S -> M2 -> T.
          - Length: 260m (+60m detour)
          - Heat Risk: 30.0 (Low/Moderate)
          - Shade: 85% (0.85)
          - Hydration: 2
        """
        router = CoolRouter(default_alpha=2.5, default_beta=1.5, hydration_kiosk_discount=0.3)
        router.add_intersection("S", lat=37.7740, lon=-122.4200, name="Start Point")
        router.add_intersection("M1", lat=37.7740, lon=-122.4180, name="Asphalt Junction")
        router.add_intersection("M2", lat=37.7760, lon=-122.4180, name="Park Waypoint", has_hydration_kiosk=True)
        router.add_intersection("T", lat=37.7740, lon=-122.4160, name="Destination Plaza")

        # Hot Path
        router.add_street_segment("S", "M1", "Solar Highway 1", length_m=100.0, heat_risk=92.0, canopy_shade_ratio=0.05, hydration_points=0)
        router.add_street_segment("M1", "T", "Solar Highway 2", length_m=100.0, heat_risk=92.0, canopy_shade_ratio=0.05, hydration_points=0)

        # Cool Path
        router.add_street_segment("S", "M2", "Green Canopy Ave 1", length_m=130.0, heat_risk=30.0, canopy_shade_ratio=0.85, hydration_points=1)
        router.add_street_segment("M2", "T", "Green Canopy Ave 2", length_m=130.0, heat_risk=30.0, canopy_shade_ratio=0.85, hydration_points=1)

        return router

    def test_shortest_vs_cool_routing(self, diamond_network):
        router = diamond_network

        # 1. Shortest path minimizes distance
        shortest = router.find_shortest_path("S", "T")
        assert shortest.path_nodes == ["S", "M1", "T"]
        assert shortest.total_distance_m == 200.0
        assert shortest.avg_heat_risk == 92.0
        assert shortest.shade_percentage == 5.0
        assert shortest.hydration_kiosks_count == 0

        # 2. Cool path minimizes thermal exposure cost
        cool = router.find_cool_path("S", "T")
        assert cool.path_nodes == ["S", "M2", "T"]
        assert cool.total_distance_m == 260.0
        assert cool.avg_heat_risk == 30.0
        assert cool.shade_percentage == 85.0
        assert cool.hydration_kiosks_count >= 1

    def test_route_comparison_metrics(self, diamond_network):
        router = diamond_network
        comp = router.route_and_compare("S", "T")

        # Distance diff
        assert comp.distance_diff_m == 60.0
        assert round(comp.distance_diff_pct, 1) == 30.0
        assert comp.walk_time_diff_min > 0.5

        # Heat risk reduction
        assert comp.heat_risk_diff < 0  # 30.0 - 92.0 = -62.0
        assert comp.heat_risk_reduction_pct > 65.0  # ~67.4% reduction

        # Shade diff
        assert comp.shade_coverage_diff_pct == 80.0  # 85% - 5%

        # Hydration kiosks
        assert comp.hydration_kiosks_diff >= 1

        # Thermal strain reduction
        assert comp.thermal_strain_reduction_pct > 60.0

        # Markdown output checks
        md = comp.summary_markdown()
        assert "Cool-Corridor Walking Path Comparison" in md
        assert "Distance" in md
        assert "Average Heat Risk" in md
        assert "Canopy Shade Cover" in md
        assert "Hydration Kiosks" in md

    def test_turn_by_turn_directions(self, diamond_network):
        router = diamond_network
        cool = router.find_cool_path("S", "T")
        steps = cool.turn_by_turn_directions

        assert len(steps) >= 3  # Start step, turn/continue step, arrive step
        first_step = steps[0]
        assert first_step.step_number == 1
        assert "Green Canopy Ave" in first_step.street_name
        assert first_step.shade_percentage == 85.0

        # Destination step
        last_step = steps[-1]
        assert last_step.turn_type == "arrive"
        assert "Destination Plaza" in last_step.instruction

    def test_single_node_route(self, diamond_network):
        router = diamond_network
        res = router.find_shortest_path("S", "S")
        assert res.total_distance_m == 0.0
        assert len(res.turn_by_turn_directions) == 1
        assert res.turn_by_turn_directions[0].turn_type == "arrive"

    def test_no_path_exception(self, diamond_network):
        router = diamond_network
        router.add_intersection("ISOLATED", lat=38.0, lon=-123.0)
        with pytest.raises(nx.NetworkXNoPath):
            router.find_shortest_path("S", "ISOLATED")


class TestBalancedRouting:
    """Test constrained detour balanced path routing."""

    def test_balanced_path_respects_detour(self):
        router = CoolRouter()
        # Create 3 parallel paths:
        # P1 (Direct Sun): 100m, Heat=90, Shade=0
        # P2 (Moderate Shade): 120m (+20%), Heat=45, Shade=60%
        # P3 (Super Cool): 180m (+80%), Heat=20, Shade=95%
        router.add_intersection("O", 37.0, -122.0)
        router.add_intersection("D", 37.0, -121.99)
        router.add_intersection("M_hot", 37.001, -121.995)
        router.add_intersection("M_mod", 37.002, -121.995)
        router.add_intersection("M_cool", 37.005, -121.995)

        # P1
        router.add_street_segment("O", "M_hot", "Hot 1", 50.0, heat_risk=90.0, canopy_shade_ratio=0.0)
        router.add_street_segment("M_hot", "D", "Hot 2", 50.0, heat_risk=90.0, canopy_shade_ratio=0.0)

        # P2
        router.add_street_segment("O", "M_mod", "Mod 1", 60.0, heat_risk=45.0, canopy_shade_ratio=0.6)
        router.add_street_segment("M_mod", "D", "Mod 2", 60.0, heat_risk=45.0, canopy_shade_ratio=0.6)

        # P3
        router.add_street_segment("O", "M_cool", "Cool 1", 90.0, heat_risk=20.0, canopy_shade_ratio=0.95)
        router.add_street_segment("M_cool", "D", "Cool 2", 90.0, heat_risk=20.0, canopy_shade_ratio=0.95)

        # Shortest is P1 (100m)
        shortest = router.find_shortest_path("O", "D")
        assert shortest.total_distance_m == 100.0

        # Unconstrained cool path will pick P3 (180m)
        cool = router.find_cool_path("O", "D")
        assert cool.total_distance_m == 180.0

        # Constrained balanced path with max_detour_ratio=1.3 (max allowed = 130m)
        # Must pick P2 (120m) because P3 (180m) violates max detour
        balanced = router.find_balanced_path("O", "D", max_detour_ratio=1.3)
        assert balanced.total_distance_m <= 130.0
        assert balanced.total_distance_m == 120.0


class TestSyntheticGridAndGeoJSON:
    """Test synthetic grid generation, GeoJSON export and import."""

    def test_synthetic_urban_grid(self):
        router = CoolRouter.create_synthetic_urban_grid(rows=4, cols=4, block_size_m=100.0)
        assert len(router.graph.nodes) == 16
        # Bidirectional grid edges
        assert len(router.graph.edges) > 30

        # Test routing in grid
        comp = router.route_and_compare("I_0_0", "I_3_3")
        assert comp.shortest_path.total_distance_m > 0
        assert comp.cool_path.total_distance_m > 0
        assert comp.cool_path.avg_heat_risk <= comp.shortest_path.avg_heat_risk

    def test_geojson_export_and_import(self):
        router = CoolRouter.create_synthetic_urban_grid(rows=3, cols=3, block_size_m=100.0)
        geojson_net = router.export_graph_geojson()

        assert geojson_net["type"] == "FeatureCollection"
        assert len(geojson_net["features"]) > 0

        # Load back via from_geojson
        imported_router = CoolRouter.from_geojson(geojson_net)
        assert len(imported_router.graph.nodes) >= 9
        assert len(imported_router.graph.edges) > 0

        # Route on imported graph
        nodes = list(imported_router.graph.nodes)
        res = imported_router.find_cool_path(nodes[0], nodes[-1])
        assert res.total_distance_m > 0
        route_geojson = res.to_geojson()
        assert route_geojson["type"] == "FeatureCollection"
        assert len(route_geojson["features"]) >= 1
