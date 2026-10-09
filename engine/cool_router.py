"""
Cool Corridor Router Engine for Human-Scale Safe Walking Navigation.
Team TERRA07 (Software Track: Heat-Risk Mapping at Human Scale).

Calculates human-scale safe walking paths for citizens and outdoor workers during heatwaves,
minimizing cumulative thermal strain while maximizing tree canopy shade coverage and access
to hydration infrastructure.
"""

from __future__ import annotations

import math
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import networkx as nx


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class IntersectionNode:
    """Represents a street intersection or pedestrian waypoint."""
    node_id: str
    lat: float
    lon: float
    name: Optional[str] = None
    has_hydration_kiosk: bool = False
    kiosk_description: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreetSegmentEdge:
    """Represents a walkable street segment between two intersections."""
    u: str
    v: str
    street_name: str
    length_m: float
    heat_risk: float  # 0.0 (safest) to 100.0 (extreme thermal hazard)
    canopy_shade_ratio: float  # 0.0 (no canopy/full sun) to 1.0 (fully covered)
    hydration_points: int = 0  # Number of water kiosks/misting stations along segment
    surface_temp_c: Optional[float] = None
    oneway: bool = False
    geometry: Optional[List[Tuple[float, float]]] = None  # [(lat, lon), ...]
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnDirectionStep:
    """Step-by-step turn navigation instruction with thermal safety alerts."""
    step_number: int
    instruction: str
    street_name: str
    distance_m: float
    walk_time_sec: float
    heat_risk: float
    heat_category: str  # 'Low', 'Moderate', 'High', 'Extreme'
    shade_percentage: float  # 0 - 100%
    has_hydration: bool
    hydration_note: Optional[str] = None
    thermal_alert: Optional[str] = None
    turn_type: str = "straight"  # 'depart', 'straight', 'slight_left', 'left', 'sharp_left', 'slight_right', 'right', 'sharp_right', 'arrive'
    bearing_deg: Optional[float] = None
    from_node: Optional[str] = None
    to_node: Optional[str] = None
    start_coord: Optional[Tuple[float, float]] = None
    end_coord: Optional[Tuple[float, float]] = None


@dataclass
class RouteResult:
    """Routing solution with metrics and navigation instructions."""
    route_type: str  # 'shortest', 'cool_corridor', or 'balanced'
    path_nodes: List[str]
    total_distance_m: float
    estimated_walk_time_min: float
    avg_heat_risk: float
    max_heat_risk: float
    heat_risk_category: str
    shade_percentage: float
    hydration_kiosks_count: int
    hydration_kiosk_locations: List[Dict[str, Any]]
    cumulative_heat_dose: float
    net_thermal_strain: float
    turn_by_turn_directions: List[TurnDirectionStep]
    segments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert route result to a serializable dictionary."""
        return {
            "route_type": self.route_type,
            "path_nodes": self.path_nodes,
            "total_distance_m": round(self.total_distance_m, 1),
            "estimated_walk_time_min": round(self.estimated_walk_time_min, 1),
            "avg_heat_risk": round(self.avg_heat_risk, 1),
            "max_heat_risk": round(self.max_heat_risk, 1),
            "heat_risk_category": self.heat_risk_category,
            "shade_percentage": round(self.shade_percentage, 1),
            "hydration_kiosks_count": self.hydration_kiosks_count,
            "hydration_kiosk_locations": self.hydration_kiosk_locations,
            "cumulative_heat_dose": round(self.cumulative_heat_dose, 1),
            "net_thermal_strain": round(self.net_thermal_strain, 1),
            "turn_by_turn_directions": [asdict(step) for step in self.turn_by_turn_directions],
            "segments": self.segments,
        }

    def to_geojson(self) -> Dict[str, Any]:
        """Convert route to a GeoJSON FeatureCollection."""
        coordinates = []
        for seg in self.segments:
            geom = seg.get("geometry")
            if geom:
                # GeoJSON uses [lon, lat]
                for pt in geom:
                    coordinates.append([pt[1], pt[0]])

        features = [
            {
                "type": "Feature",
                "properties": {
                    "route_type": self.route_type,
                    "total_distance_m": round(self.total_distance_m, 1),
                    "avg_heat_risk": round(self.avg_heat_risk, 1),
                    "shade_percentage": round(self.shade_percentage, 1),
                    "hydration_kiosks_count": self.hydration_kiosks_count,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
            }
        ]

        # Add waypoint features for hydration kiosks along path
        for kiosk in self.hydration_kiosk_locations:
            lat = kiosk.get("lat")
            lon = kiosk.get("lon")
            if lat is not None and lon is not None:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "type": "hydration_kiosk",
                        "name": kiosk.get("name", "Hydration Kiosk"),
                        "street": kiosk.get("street", ""),
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat],
                    },
                })

        return {
            "type": "FeatureCollection",
            "features": features,
        }


@dataclass
class RouteComparison:
    """Comparison metrics between Standard Shortest and Safe Cool-Corridor paths."""
    shortest_path: RouteResult
    cool_path: RouteResult
    distance_diff_m: float
    distance_diff_pct: float
    walk_time_diff_min: float
    heat_risk_diff: float
    heat_risk_reduction_pct: float
    shade_coverage_diff_pct: float
    hydration_kiosks_shortest: int
    hydration_kiosks_cool: int
    hydration_kiosks_diff: int
    thermal_dose_reduction_pct: float
    thermal_strain_reduction_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distance_diff_m": round(self.distance_diff_m, 1),
            "distance_diff_pct": round(self.distance_diff_pct, 1),
            "walk_time_diff_min": round(self.walk_time_diff_min, 1),
            "heat_risk_diff": round(self.heat_risk_diff, 1),
            "heat_risk_reduction_pct": round(self.heat_risk_reduction_pct, 1),
            "shade_coverage_diff_pct": round(self.shade_coverage_diff_pct, 1),
            "hydration_kiosks_shortest": self.hydration_kiosks_shortest,
            "hydration_kiosks_cool": self.hydration_kiosks_cool,
            "hydration_kiosks_diff": self.hydration_kiosks_diff,
            "thermal_dose_reduction_pct": round(self.thermal_dose_reduction_pct, 1),
            "thermal_strain_reduction_pct": round(self.thermal_strain_reduction_pct, 1),
            "shortest_summary": {
                "distance_m": round(self.shortest_path.total_distance_m, 1),
                "walk_time_min": round(self.shortest_path.estimated_walk_time_min, 1),
                "avg_heat_risk": round(self.shortest_path.avg_heat_risk, 1),
                "risk_category": self.shortest_path.heat_risk_category,
                "shade_pct": round(self.shortest_path.shade_percentage, 1),
                "kiosks": self.shortest_path.hydration_kiosks_count,
            },
            "cool_summary": {
                "distance_m": round(self.cool_path.total_distance_m, 1),
                "walk_time_min": round(self.cool_path.estimated_walk_time_min, 1),
                "avg_heat_risk": round(self.cool_path.avg_heat_risk, 1),
                "risk_category": self.cool_path.heat_risk_category,
                "shade_pct": round(self.cool_path.shade_percentage, 1),
                "kiosks": self.cool_path.hydration_kiosks_count,
            },
        }

    def summary_markdown(self) -> str:
        """Formatted human-readable comparison summary card."""
        sign = "+" if self.distance_diff_m >= 0 else ""
        time_sign = "+" if self.walk_time_diff_min >= 0 else ""
        shade_sign = "+" if self.shade_coverage_diff_pct >= 0 else ""
        kiosk_sign = "+" if self.hydration_kiosks_diff >= 0 else ""

        return (
            "### 🌿 Cool-Corridor Walking Path Comparison\n\n"
            f"- **Distance**: {self.shortest_path.total_distance_m:.0f}m (Shortest) ➔ "
            f"{self.cool_path.total_distance_m:.0f}m (Cool) "
            f"({sign}{self.distance_diff_m:.0f}m, {time_sign}{self.walk_time_diff_min:.1f} mins walk)\n"
            f"- **Average Heat Risk**: {self.shortest_path.avg_heat_risk:.1f} ({self.shortest_path.heat_risk_category}) ➔ "
            f"{self.cool_path.avg_heat_risk:.1f} ({self.cool_path.heat_risk_category}) "
            f"([{self.heat_risk_reduction_pct:.1f}% risk reduction]({self.heat_risk_reduction_pct:.1f}%))\n"
            f"- **Canopy Shade Cover**: {self.shortest_path.shade_percentage:.1f}% ➔ "
            f"{self.cool_path.shade_percentage:.1f}% "
            f"({shade_sign}{self.shade_coverage_diff_pct:.1f}% shade gain)\n"
            f"- **Hydration Kiosks Encountered**: {self.shortest_path.hydration_kiosks_count} ➔ "
            f"{self.cool_path.hydration_kiosks_count} "
            f"({kiosk_sign}{self.hydration_kiosks_diff} water access points)\n"
            f"- **Net Human Thermal Strain Reduction**: {self.thermal_strain_reduction_pct:.1f}%\n"
        )


# -----------------------------------------------------------------------------
# Spatial Utility Helpers
# -----------------------------------------------------------------------------

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in meters between two coordinates."""
    r = 6371000.0  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass bearing (0-360 degrees) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def classify_turn(prev_bearing: Optional[float], current_bearing: Optional[float]) -> Tuple[str, str]:
    """
    Classify turn type and direction based on angular heading change.
    Returns (turn_type, direction_text).
    """
    if prev_bearing is None or current_bearing is None:
        return "depart", "Head"

    diff = (current_bearing - prev_bearing + 180.0) % 360.0 - 180.0

    if abs(diff) <= 20.0:
        return "straight", "Continue straight"
    elif 20.0 < diff <= 65.0:
        return "slight_right", "Bear slight right"
    elif 65.0 < diff <= 135.0:
        return "right", "Turn right"
    elif diff > 135.0:
        return "sharp_right", "Make a sharp right"
    elif -65.0 <= diff < -20.0:
        return "slight_left", "Bear slight left"
    elif -135.0 <= diff < -65.0:
        return "left", "Turn left"
    else:
        return "sharp_left", "Make a sharp left"


def get_heat_risk_category(score: float) -> str:
    """Categorize heat risk index (0-100 scale)."""
    if score < 30.0:
        return "Low"
    elif score < 60.0:
        return "Moderate"
    elif score < 80.0:
        return "High"
    else:
        return "Extreme"


# -----------------------------------------------------------------------------
# Main Routing Engine
# -----------------------------------------------------------------------------

class CoolRouter:
    """
    Safe Cool-Corridor Navigation & Street Routing Engine.

    Builds an urban walking graph enriched with thermal risk, canopy shade,
    and hydration infrastructure. Computes both standard shortest paths and
    optimal cool-corridor routes minimizing human thermal exposure.
    """

    def __init__(
        self,
        walking_speed_mps: float = 1.3,  # Average walking pace ~ 4.7 km/h (1.3 m/s)
        default_alpha: float = 2.0,       # Heat risk sensitivity factor
        default_beta: float = 1.2,        # Shade mitigation bonus factor
        hydration_kiosk_discount: float = 0.25, # Thermal penalty discount per water station
        min_cost_factor: float = 0.15,    # Floor factor to ensure strictly positive edge weights
    ):
        self.walking_speed_mps = walking_speed_mps
        self.default_alpha = default_alpha
        self.default_beta = default_beta
        self.hydration_kiosk_discount = hydration_kiosk_discount
        self.min_cost_factor = min_cost_factor
        self.graph = nx.DiGraph()

    # -------------------------------------------------------------------------
    # Graph Construction & Ingestion
    # -------------------------------------------------------------------------

    def add_intersection(
        self,
        node_id: str,
        lat: float,
        lon: float,
        name: Optional[str] = None,
        has_hydration_kiosk: bool = False,
        kiosk_description: Optional[str] = None,
        **attrs,
    ) -> None:
        """Add an intersection node to the walking graph."""
        self.graph.add_node(
            str(node_id),
            lat=float(lat),
            lon=float(lon),
            name=name or f"Intersection {node_id}",
            has_hydration_kiosk=bool(has_hydration_kiosk),
            kiosk_description=kiosk_description,
            **attrs,
        )

    def add_street_segment(
        self,
        u: str,
        v: str,
        street_name: str,
        length_m: Optional[float] = None,
        heat_risk: float = 50.0,
        canopy_shade_ratio: float = 0.2,
        hydration_points: int = 0,
        bidirectional: bool = True,
        surface_temp_c: Optional[float] = None,
        geometry: Optional[List[Tuple[float, float]]] = None,
        **attrs,
    ) -> None:
        """
        Add a walkable street segment between intersections u and v.
        If length_m is not provided, it is automatically computed using Haversine
        distance between the coordinates of nodes u and v.
        """
        u_str, v_str = str(u), str(v)

        if not self.graph.has_node(u_str) or not self.graph.has_node(v_str):
            raise ValueError(f"Both nodes ({u_str}, {v_str}) must exist in graph before adding edge.")

        u_data = self.graph.nodes[u_str]
        v_data = self.graph.nodes[v_str]

        # Calculate length if omitted
        if length_m is None or length_m <= 0:
            length_m = haversine_distance_m(u_data["lat"], u_data["lon"], v_data["lat"], v_data["lon"])
            if length_m <= 0:
                length_m = 1.0  # minimal 1 meter guard

        # Default straight line geometry if not supplied
        if geometry is None:
            geometry = [(u_data["lat"], u_data["lon"]), (v_data["lat"], v_data["lon"])]

        # Clamp values
        clamped_heat_risk = max(0.0, min(100.0, float(heat_risk)))
        clamped_shade_ratio = max(0.0, min(1.0, float(canopy_shade_ratio)))
        kiosk_count = max(0, int(hydration_points))

        edge_attrs = {
            "street_name": street_name,
            "length_m": float(length_m),
            "heat_risk": clamped_heat_risk,
            "canopy_shade_ratio": clamped_shade_ratio,
            "hydration_points": kiosk_count,
            "surface_temp_c": surface_temp_c,
            "geometry": geometry,
            **attrs,
        }

        self.graph.add_edge(u_str, v_str, **edge_attrs)

        if bidirectional:
            rev_geom = list(reversed(geometry)) if geometry else None
            rev_attrs = dict(edge_attrs)
            rev_attrs["geometry"] = rev_geom
            self.graph.add_edge(v_str, u_str, **rev_attrs)

    def compute_edge_cool_cost(
        self,
        u: str,
        v: str,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        hydration_discount: Optional[float] = None,
    ) -> float:
        """
        Compute thermal exposure navigation cost for an edge:
        Cost = Distance * (1 + alpha * HeatRisk - beta * ShadeRatio)
               with bonus for passing hydration kiosks.

        HeatRisk is normalized to [0, 1] range for weighting.
        """
        alpha_val = self.default_alpha if alpha is None else alpha
        beta_val = self.default_beta if beta is None else beta
        h_disc = self.hydration_kiosk_discount if hydration_discount is None else hydration_discount

        edge = self.graph[u][v]
        dist = edge["length_m"]
        heat_norm = edge["heat_risk"] / 100.0
        shade = edge["canopy_shade_ratio"]
        kiosks = edge.get("hydration_points", 0)

        # Check if destination intersection node has a hydration kiosk
        v_data = self.graph.nodes[v]
        if v_data.get("has_hydration_kiosk"):
            kiosks += 1

        # Thermal multiplier calculation
        thermal_factor = 1.0 + (alpha_val * heat_norm) - (beta_val * shade)

        # Hydration points relief bonus
        if kiosks > 0:
            kiosk_bonus = min(kiosks * h_disc, 0.6)
            thermal_factor -= kiosk_bonus

        # Guarantee strictly positive edge weight for Dijkstra
        effective_cost_multiplier = max(self.min_cost_factor, thermal_factor)
        return dist * effective_cost_multiplier

    # -------------------------------------------------------------------------
    # Spatial Queries & Routing
    # -------------------------------------------------------------------------

    def find_nearest_node(self, lat: float, lon: float) -> str:
        """Find the nearest intersection node in the graph to given coordinates."""
        if not self.graph.nodes:
            raise ValueError("Graph has no nodes.")

        best_node = None
        min_dist = float("inf")

        for n, data in self.graph.nodes(data=True):
            dist = haversine_distance_m(lat, lon, data["lat"], data["lon"])
            if dist < min_dist:
                min_dist = dist
                best_node = n

        return best_node

    def find_shortest_path(self, origin: str, destination: str) -> RouteResult:
        """
        Standard Shortest Path routing minimizing pure physical distance (meters).
        """
        origin_str, dest_str = str(origin), str(destination)
        if not self.graph.has_node(origin_str) or not self.graph.has_node(dest_str):
            raise ValueError(f"Origin '{origin_str}' or Destination '{dest_str}' does not exist in graph.")

        try:
            path_nodes = nx.shortest_path(
                self.graph,
                source=origin_str,
                target=dest_str,
                weight="length_m",
            )
        except nx.NetworkXNoPath:
            raise nx.NetworkXNoPath(f"No walkable path exists between {origin_str} and {dest_str}.")

        return self._build_route_result(path_nodes, route_type="shortest")

    def find_cool_path(
        self,
        origin: str,
        destination: str,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        hydration_discount: Optional[float] = None,
    ) -> RouteResult:
        """
        Cool-Corridor Path routing minimizing thermal exposure cost:
        Cost = Distance * (1 + alpha * HeatRisk - beta * ShadeRatio) - HydrationBonus.
        """
        origin_str, dest_str = str(origin), str(destination)
        if not self.graph.has_node(origin_str) or not self.graph.has_node(dest_str):
            raise ValueError(f"Origin '{origin_str}' or Destination '{dest_str}' does not exist in graph.")

        # Create weight function
        def weight_fn(u, v, d):
            return self.compute_edge_cool_cost(
                u, v, alpha=alpha, beta=beta, hydration_discount=hydration_discount
            )

        try:
            path_nodes = nx.shortest_path(
                self.graph,
                source=origin_str,
                target=dest_str,
                weight=weight_fn,
            )
        except nx.NetworkXNoPath:
            raise nx.NetworkXNoPath(f"No walkable path exists between {origin_str} and {dest_str}.")

        return self._build_route_result(path_nodes, route_type="cool_corridor")

    def find_balanced_path(
        self,
        origin: str,
        destination: str,
        max_detour_ratio: float = 1.25,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        hydration_discount: Optional[float] = None,
    ) -> RouteResult:
        """
        Calculates a balanced safe path that maximizes cooling relief while strictly
        constraining walking distance:
        total_distance <= max_detour_ratio * shortest_path_distance.
        """
        shortest = self.find_shortest_path(origin, destination)
        max_allowed_distance = shortest.total_distance_m * max(1.0, max_detour_ratio)

        cool = self.find_cool_path(
            origin, destination, alpha=alpha, beta=beta, hydration_discount=hydration_discount
        )
        if cool.total_distance_m <= max_allowed_distance:
            cool.route_type = "balanced"
            return cool

        # Parametric search to find maximum cooling weight that respects max_detour_ratio
        best_nodes = shortest.path_nodes
        low, high = 0.0, 1.0

        for _ in range(8):
            mid = (low + high) / 2.0

            def blended_weight(u, v, d):
                dist = self.graph[u][v]["length_m"]
                c_cost = self.compute_edge_cool_cost(
                    u, v, alpha=alpha, beta=beta, hydration_discount=hydration_discount
                )
                return (1.0 - mid) * dist + mid * c_cost

            try:
                candidate_nodes = nx.shortest_path(
                    self.graph,
                    source=str(origin),
                    target=str(destination),
                    weight=blended_weight,
                )
                cand_len = sum(
                    self.graph[candidate_nodes[i]][candidate_nodes[i + 1]]["length_m"]
                    for i in range(len(candidate_nodes) - 1)
                )
                if cand_len <= max_allowed_distance:
                    best_nodes = candidate_nodes
                    low = mid
                else:
                    high = mid
            except nx.NetworkXNoPath:
                break

        return self._build_route_result(best_nodes, route_type="balanced")

    def export_graph_geojson(self) -> Dict[str, Any]:
        """Export full street network as GeoJSON FeatureCollection with heat & shade properties."""
        features = []
        for u, v, data in self.graph.edges(data=True):
            geom = data.get("geometry")
            if not geom:
                u_node = self.graph.nodes[u]
                v_node = self.graph.nodes[v]
                geom = [(u_node["lat"], u_node["lon"]), (v_node["lat"], v_node["lon"])]
            coords = [[pt[1], pt[0]] for pt in geom]
            features.append({
                "type": "Feature",
                "properties": {
                    "u": u,
                    "v": v,
                    "street_name": data.get("street_name"),
                    "length_m": data.get("length_m"),
                    "heat_risk": data.get("heat_risk"),
                    "canopy_shade_ratio": data.get("canopy_shade_ratio"),
                    "hydration_points": data.get("hydration_points", 0),
                    "surface_temp_c": data.get("surface_temp_c"),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            })

        for n, data in self.graph.nodes(data=True):
            if data.get("has_hydration_kiosk"):
                features.append({
                    "type": "Feature",
                    "properties": {
                        "node_id": n,
                        "type": "hydration_kiosk",
                        "name": data.get("name"),
                        "description": data.get("kiosk_description"),
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [data["lon"], data["lat"]],
                    },
                })

        return {"type": "FeatureCollection", "features": features}

    def route_and_compare(
        self,
        origin: str,
        destination: str,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        hydration_discount: Optional[float] = None,
    ) -> RouteComparison:
        """
        Calculate both Shortest Path and Cool-Corridor Path, and return comprehensive
        comparative metrics.
        """
        shortest_route = self.find_shortest_path(origin, destination)
        cool_route = self.find_cool_path(
            origin, destination, alpha=alpha, beta=beta, hydration_discount=hydration_discount
        )

        return self.compare_routes(shortest_route, cool_route)

    @staticmethod
    def compare_routes(shortest_route: RouteResult, cool_route: RouteResult) -> RouteComparison:
        """Compute comparison metrics between shortest and cool corridor paths."""
        dist_diff_m = cool_route.total_distance_m - shortest_route.total_distance_m
        dist_diff_pct = (
            (dist_diff_m / shortest_route.total_distance_m * 100.0)
            if shortest_route.total_distance_m > 0 else 0.0
        )
        time_diff_min = cool_route.estimated_walk_time_min - shortest_route.estimated_walk_time_min

        heat_diff = cool_route.avg_heat_risk - shortest_route.avg_heat_risk
        heat_reduction_pct = (
            ((shortest_route.avg_heat_risk - cool_route.avg_heat_risk) / shortest_route.avg_heat_risk * 100.0)
            if shortest_route.avg_heat_risk > 0 else 0.0
        )
        heat_reduction_pct = max(0.0, heat_reduction_pct)

        shade_diff_pct = cool_route.shade_percentage - shortest_route.shade_percentage

        kiosk_diff = cool_route.hydration_kiosks_count - shortest_route.hydration_kiosks_count

        dose_diff_pct = (
            ((shortest_route.cumulative_heat_dose - cool_route.cumulative_heat_dose) / shortest_route.cumulative_heat_dose * 100.0)
            if shortest_route.cumulative_heat_dose > 0 else 0.0
        )
        dose_diff_pct = max(0.0, dose_diff_pct)

        strain_diff_pct = (
            ((shortest_route.net_thermal_strain - cool_route.net_thermal_strain) / shortest_route.net_thermal_strain * 100.0)
            if shortest_route.net_thermal_strain > 0 else 0.0
        )
        strain_diff_pct = max(0.0, strain_diff_pct)

        return RouteComparison(
            shortest_path=shortest_route,
            cool_path=cool_route,
            distance_diff_m=dist_diff_m,
            distance_diff_pct=dist_diff_pct,
            walk_time_diff_min=time_diff_min,
            heat_risk_diff=heat_diff,
            heat_risk_reduction_pct=heat_reduction_pct,
            shade_coverage_diff_pct=shade_diff_pct,
            hydration_kiosks_shortest=shortest_route.hydration_kiosks_count,
            hydration_kiosks_cool=cool_route.hydration_kiosks_count,
            hydration_kiosks_diff=kiosk_diff,
            thermal_dose_reduction_pct=dose_diff_pct,
            thermal_strain_reduction_pct=strain_diff_pct,
        )

    # -------------------------------------------------------------------------
    # Route Analysis & Turn-by-Turn Instruction Generator
    # -------------------------------------------------------------------------

    def _build_route_result(self, path_nodes: List[str], route_type: str) -> RouteResult:
        """Construct full RouteResult with metrics and turn directions from node path."""
        if not path_nodes:
            raise ValueError("Path nodes cannot be empty.")

        # Single point route edge case
        if len(path_nodes) == 1:
            node = path_nodes[0]
            nd = self.graph.nodes[node]
            kiosk = 1 if nd.get("has_hydration_kiosk") else 0
            kiosk_locs = [{"node": node, "lat": nd["lat"], "lon": nd["lon"], "name": nd.get("name")}] if kiosk else []
            step = TurnDirectionStep(
                step_number=1,
                instruction=f"You are at {nd.get('name', 'destination')}.",
                street_name=nd.get("name", "Arrival"),
                distance_m=0.0,
                walk_time_sec=0.0,
                heat_risk=0.0,
                heat_category="Low",
                shade_percentage=100.0,
                has_hydration=bool(kiosk),
                turn_type="arrive",
                from_node=node,
                to_node=node,
                start_coord=(nd["lat"], nd["lon"]),
                end_coord=(nd["lat"], nd["lon"]),
            )
            return RouteResult(
                route_type=route_type,
                path_nodes=path_nodes,
                total_distance_m=0.0,
                estimated_walk_time_min=0.0,
                avg_heat_risk=0.0,
                max_heat_risk=0.0,
                heat_risk_category="Low",
                shade_percentage=100.0,
                hydration_kiosks_count=kiosk,
                hydration_kiosk_locations=kiosk_locs,
                cumulative_heat_dose=0.0,
                net_thermal_strain=0.0,
                turn_by_turn_directions=[step],
                segments=[],
            )

        total_distance = 0.0
        weighted_heat_sum = 0.0
        weighted_shade_sum = 0.0
        max_heat = 0.0
        cumulative_dose = 0.0
        cumulative_strain = 0.0
        kiosk_locations: List[Dict[str, Any]] = []
        segments: List[Dict[str, Any]] = []

        seen_kiosk_nodes = set()
        seen_edge_kiosks = set()

        # Check origin node kiosk
        orig_data = self.graph.nodes[path_nodes[0]]
        if orig_data.get("has_hydration_kiosk"):
            seen_kiosk_nodes.add(path_nodes[0])
            kiosk_locations.append({
                "type": "intersection_kiosk",
                "node": path_nodes[0],
                "lat": orig_data["lat"],
                "lon": orig_data["lon"],
                "name": orig_data.get("name", "Hydration Kiosk"),
                "description": orig_data.get("kiosk_description", "Drinking fountain & refill station"),
            })

        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edge = self.graph[u][v]
            v_data = self.graph.nodes[v]

            length = edge["length_m"]
            heat = edge["heat_risk"]
            shade = edge["canopy_shade_ratio"]

            total_distance += length
            weighted_heat_sum += heat * length
            weighted_shade_sum += (shade * 100.0) * length
            cumulative_dose += heat * length
            # Effective human thermal strain: direct sun delivers full radiant heat;
            # tree canopy shields up to 70% of direct thermal radiation
            cumulative_strain += heat * (1.0 - 0.70 * shade) * length
            max_heat = max(max_heat, heat)

            # Mid-block hydration points on edge
            edge_kiosks = edge.get("hydration_points", 0)
            edge_key = tuple(sorted([u, v]))
            if edge_kiosks > 0 and edge_key not in seen_edge_kiosks:
                seen_edge_kiosks.add(edge_key)
                mid_geom = edge.get("geometry")
                kiosk_lat = mid_geom[len(mid_geom) // 2][0] if mid_geom else v_data["lat"]
                kiosk_lon = mid_geom[len(mid_geom) // 2][1] if mid_geom else v_data["lon"]
                kiosk_locations.append({
                    "type": "corridor_kiosk",
                    "street": edge.get("street_name"),
                    "lat": kiosk_lat,
                    "lon": kiosk_lon,
                    "name": f"Water Station on {edge.get('street_name')}",
                    "description": "Public drinking fountain / chilled water station",
                })

            if v_data.get("has_hydration_kiosk") and v not in seen_kiosk_nodes:
                seen_kiosk_nodes.add(v)
                kiosk_locations.append({
                    "type": "intersection_kiosk",
                    "node": v,
                    "lat": v_data["lat"],
                    "lon": v_data["lon"],
                    "name": v_data.get("name", "Hydration Kiosk"),
                    "description": v_data.get("kiosk_description", "Drinking fountain & misting kiosk"),
                })

            segments.append({
                "from_node": u,
                "to_node": v,
                "street_name": edge.get("street_name"),
                "length_m": length,
                "heat_risk": heat,
                "canopy_shade_ratio": shade,
                "hydration_points": edge_kiosks,
                "geometry": edge.get("geometry"),
            })

        avg_heat = (weighted_heat_sum / total_distance) if total_distance > 0 else 0.0
        avg_shade = (weighted_shade_sum / total_distance) if total_distance > 0 else 0.0
        walk_time_min = (total_distance / self.walking_speed_mps) / 60.0
        total_kiosks_encountered = len(seen_kiosk_nodes) + len(seen_edge_kiosks)

        turn_directions = self._generate_turn_by_turn(path_nodes)

        return RouteResult(
            route_type=route_type,
            path_nodes=path_nodes,
            total_distance_m=total_distance,
            estimated_walk_time_min=walk_time_min,
            avg_heat_risk=avg_heat,
            max_heat_risk=max_heat,
            heat_risk_category=get_heat_risk_category(avg_heat),
            shade_percentage=avg_shade,
            hydration_kiosks_count=total_kiosks_encountered,
            hydration_kiosk_locations=kiosk_locations,
            cumulative_heat_dose=cumulative_dose,
            net_thermal_strain=cumulative_strain,
            turn_by_turn_directions=turn_directions,
            segments=segments,
        )

    def _generate_turn_by_turn(self, path_nodes: List[str]) -> List[TurnDirectionStep]:
        """
        Generate human-friendly, step-by-step turn directions with thermal safety alerts.
        Groups contiguous segments on the same street when continuing straight.
        """
        steps: List[TurnDirectionStep] = []
        if len(path_nodes) < 2:
            return steps

        prev_bearing: Optional[float] = None
        step_number = 1

        # We consolidate consecutive steps along the same street name if the heading doesn't change significantly
        i = 0
        while i < len(path_nodes) - 1:
            u, v = path_nodes[i], path_nodes[i + 1]
            edge = self.graph[u][v]
            u_node = self.graph.nodes[u]
            v_node = self.graph.nodes[v]

            current_bearing = calculate_bearing_deg(
                u_node["lat"], u_node["lon"], v_node["lat"], v_node["lon"]
            )

            street_name = edge.get("street_name", "Street")
            accum_dist = edge["length_m"]
            weighted_heat = edge["heat_risk"] * edge["length_m"]
            weighted_shade = (edge["canopy_shade_ratio"] * 100.0) * edge["length_m"]
            max_step_heat = edge["heat_risk"]
            has_hydration = bool(
                edge.get("hydration_points", 0) > 0
                or u_node.get("has_hydration_kiosk")
                or v_node.get("has_hydration_kiosk")
            )
            kiosk_dist_m = int(edge["length_m"] * 0.6) if has_hydration else None

            start_node = u
            start_coord = (u_node["lat"], u_node["lon"])
            end_node = v
            end_coord = (v_node["lat"], v_node["lon"])

            # Determine turn classification
            if i == 0:
                turn_type = "depart"
                action_verb = f"Head on {street_name}"
            else:
                turn_type, action_verb = classify_turn(prev_bearing, current_bearing)
                if action_verb == "Continue straight":
                    action_verb = f"Continue on {street_name}"
                else:
                    action_verb = f"{action_verb} onto {street_name}"

            # Consolidate following segments if on the same street and continuing straight
            next_idx = i + 1
            while next_idx < len(path_nodes) - 1:
                next_u, next_v = path_nodes[next_idx], path_nodes[next_idx + 1]
                next_edge = self.graph[next_u][next_v]
                if next_edge.get("street_name") != street_name:
                    break

                next_u_node = self.graph.nodes[next_u]
                next_v_node = self.graph.nodes[next_v]
                next_bearing = calculate_bearing_deg(
                    next_u_node["lat"], next_u_node["lon"], next_v_node["lat"], next_v_node["lon"]
                )

                # Check turn angle
                diff = (next_bearing - current_bearing + 180.0) % 360.0 - 180.0
                if abs(diff) > 25.0:
                    break  # Significant turn, keep separate step

                # Accumulate
                next_len = next_edge["length_m"]
                accum_dist += next_len
                weighted_heat += next_edge["heat_risk"] * next_len
                weighted_shade += (next_edge["canopy_shade_ratio"] * 100.0) * next_len
                max_step_heat = max(max_step_heat, next_edge["heat_risk"])
                if next_edge.get("hydration_points", 0) > 0 or next_v_node.get("has_hydration_kiosk"):
                    has_hydration = True
                    kiosk_dist_m = int(accum_dist * 0.7)

                end_node = next_v
                end_coord = (next_v_node["lat"], next_v_node["lon"])
                current_bearing = next_bearing
                next_idx += 1

            # Compute step metrics
            step_avg_heat = weighted_heat / accum_dist if accum_dist > 0 else 0.0
            step_shade_pct = weighted_shade / accum_dist if accum_dist > 0 else 0.0
            step_heat_cat = get_heat_risk_category(step_avg_heat)
            step_walk_sec = accum_dist / self.walking_speed_mps

            # Compose thermal alert and instruction narrative
            thermal_alert = None
            hydration_note = None

            if has_hydration:
                if kiosk_dist_m and kiosk_dist_m > 0:
                    hydration_note = f"Water Kiosk at ~{kiosk_dist_m}m"
                else:
                    hydration_note = "Water Kiosk available"

            if step_shade_pct >= 70.0:
                shade_desc = f"🌿 {int(step_shade_pct)}% canopy shade"
                thermal_alert = "Cool Shaded Corridor"
            elif step_shade_pct >= 40.0:
                shade_desc = f"{int(step_shade_pct)}% partially shaded"
            else:
                shade_desc = f"☀️ {int(step_shade_pct)}% shade (direct sun exposure)"

            if step_avg_heat >= 80.0:
                thermal_alert = "⚠️ DANGER: Extreme Heat Exposure! Seek shade immediately."
            elif step_avg_heat >= 60.0:
                thermal_alert = "⚠️ CAUTION: High thermal strain. Stay hydrated."
            elif step_avg_heat < 35.0 and step_shade_pct >= 60.0:
                thermal_alert = "✅ Safe Cool-Zone: Optimal pedestrian thermal refuge."

            # Construct clear human-scale direction string
            # e.g. "Turn left on Green Tree Blvd - 85% shaded, Water Kiosk at 200m (450m walk)"
            instruction_parts = [f"{action_verb} ({int(accum_dist)}m)"]
            qualifiers = [shade_desc]
            if hydration_note:
                qualifiers.append(hydration_note)
            if step_avg_heat >= 75.0:
                qualifiers.append(f"Heat Risk {step_avg_heat:.0f}/100")

            instruction_str = f"{instruction_parts[0]} - {', '.join(qualifiers)}"

            steps.append(
                TurnDirectionStep(
                    step_number=step_number,
                    instruction=instruction_str,
                    street_name=street_name,
                    distance_m=round(accum_dist, 1),
                    walk_time_sec=round(step_walk_sec, 1),
                    heat_risk=round(step_avg_heat, 1),
                    heat_category=step_heat_cat,
                    shade_percentage=round(step_shade_pct, 1),
                    has_hydration=has_hydration,
                    hydration_note=hydration_note,
                    thermal_alert=thermal_alert,
                    turn_type=turn_type,
                    bearing_deg=round(current_bearing, 1),
                    from_node=start_node,
                    to_node=end_node,
                    start_coord=start_coord,
                    end_coord=end_coord,
                )
            )

            step_number += 1
            prev_bearing = current_bearing
            i = next_idx

        # Arrival destination step
        dest_node = path_nodes[-1]
        dest_data = self.graph.nodes[dest_node]
        dest_name = dest_data.get("name", "Destination")
        steps.append(
            TurnDirectionStep(
                step_number=step_number,
                instruction=f"Arrive at {dest_name}.",
                street_name=dest_name,
                distance_m=0.0,
                walk_time_sec=0.0,
                heat_risk=0.0,
                heat_category="Low",
                shade_percentage=100.0,
                has_hydration=dest_data.get("has_hydration_kiosk", False),
                hydration_note="Destination water station" if dest_data.get("has_hydration_kiosk") else None,
                thermal_alert="🏁 Safe arrival at destination.",
                turn_type="arrive",
                bearing_deg=prev_bearing,
                from_node=dest_node,
                to_node=dest_node,
                start_coord=(dest_data["lat"], dest_data["lon"]),
                end_coord=(dest_data["lat"], dest_data["lon"]),
            )
        )

        return steps

    # -------------------------------------------------------------------------
    # Data Import / Export & Synthetic Urban Generator
    # -------------------------------------------------------------------------

    @classmethod
    def from_geojson(cls, geojson_data: Any, **router_kwargs) -> CoolRouter:
        """
        Build a CoolRouter graph from a GeoJSON FeatureCollection of LineStrings
        and Points, or a filepath string.
        """
        if isinstance(geojson_data, str):
            import json, os
            if os.path.exists(geojson_data):
                with open(geojson_data, "r", encoding="utf-8") as f:
                    geojson_data = json.load(f)
            else:
                geojson_data = json.loads(geojson_data)

        router = cls(**router_kwargs)
        node_coords_to_id: Dict[Tuple[float, float], str] = {}
        node_counter = 1

        def get_or_create_node(lat: float, lon: float, name: Optional[str] = None) -> str:
            nonlocal node_counter
            # Round coordinates to ~0.5m precision to snap intersection vertices
            key = (round(lat, 6), round(lon, 6))
            if key not in node_coords_to_id:
                nid = f"N_{node_counter}"
                node_counter += 1
                node_coords_to_id[key] = nid
                router.add_intersection(nid, lat, lon, name=name)
            return node_coords_to_id[key]

        features = geojson_data.get("features", [])

        # First pass: register point hydration kiosks if present
        for f in features:
            geom = f.get("geometry", {})
            props = f.get("properties", {})
            g_type = geom.get("type")
            if g_type == "Point" and props.get("has_hydration_kiosk", True):
                lon, lat = geom.get("coordinates", [0, 0])
                nid = get_or_create_node(lat, lon, name=props.get("name", "Hydration Kiosk"))
                router.graph.nodes[nid]["has_hydration_kiosk"] = True
                router.graph.nodes[nid]["kiosk_description"] = props.get("description", "Water Refill Station")

        # Second pass: street segments (LineStrings)
        for f in features:
            geom = f.get("geometry", {})
            props = f.get("properties", {})
            g_type = geom.get("type")
            if g_type == "LineString":
                coords = geom.get("coordinates", [])
                if len(coords) < 2:
                    continue
                # LineString coordinates are [lon, lat]
                start_lon, start_lat = coords[0][0], coords[0][1]
                end_lon, end_lat = coords[-1][0], coords[-1][1]

                u = get_or_create_node(start_lat, start_lon)
                v = get_or_create_node(end_lat, end_lon)

                lat_lon_geom = [(pt[1], pt[0]) for pt in coords]

                router.add_street_segment(
                    u=u,
                    v=v,
                    street_name=props.get("street_name", props.get("name", "Street")),
                    length_m=props.get("length_m"),
                    heat_risk=props.get("heat_risk", 50.0),
                    canopy_shade_ratio=props.get("canopy_shade_ratio", 0.2),
                    hydration_points=props.get("hydration_points", 0),
                    bidirectional=props.get("bidirectional", True),
                    surface_temp_c=props.get("surface_temp_c"),
                    geometry=lat_lon_geom,
                )

        return router

    @classmethod
    def create_synthetic_urban_grid(
        cls,
        rows: int = 5,
        cols: int = 5,
        block_size_m: float = 120.0,
        base_lat: float = 37.7749,
        base_lon: float = -122.4194,
        seed: int = 42,
    ) -> CoolRouter:
        """
        Create a realistic synthetic urban street network representing a heat-vulnerable
        downtown district with:
        1. High-heat asphalt arterial avenues with direct sunlight (heat risk 80-90, shade 0.05-0.15)
        2. Shaded cool green corridors with mature tree canopies (heat risk 25-45, shade 0.70-0.90)
        3. Strategic hydration kiosks and misting stations along key intersections.
        """
        import random
        rng = random.Random(seed)

        router = cls()

        # Meters to degrees conversion at base_lat
        lat_deg_per_meter = 1.0 / 111320.0
        lon_deg_per_meter = 1.0 / (111320.0 * math.cos(math.radians(base_lat)))

        node_map: Dict[Tuple[int, int], str] = {}

        # 1. Add intersection nodes
        for r in range(rows):
            for c in range(cols):
                node_id = f"I_{r}_{c}"
                lat = base_lat + r * block_size_m * lat_deg_per_meter
                lon = base_lon + c * block_size_m * lon_deg_per_meter

                # Place hydration kiosks at designated green plazas / corridors
                # e.g., diagonal green corridor and park corners
                is_kiosk = False
                kiosk_desc = None
                if (r == c) or (r == 1 and c == 3) or (r == 3 and c == 1):
                    is_kiosk = True
                    kiosk_desc = f"Smart Misting Station & Chilled Water Fountain (Kiosk #{r}{c})"

                name = f"Ave {r+1} & St {c+1}"
                router.add_intersection(
                    node_id=node_id,
                    lat=lat,
                    lon=lon,
                    name=name,
                    has_hydration_kiosk=is_kiosk,
                    kiosk_description=kiosk_desc,
                )
                node_map[(r, c)] = node_id

        # 2. Add street segments
        # Horizontal streets:
        # - Row 0 & Row rows-1: High-sun highway / commercial asphalt (heat risk 85, shade 10%)
        # - Row 2 (Middle): "Green Canopy Promenade" (heat risk 32, shade 85%, hydration points)
        for r in range(rows):
            for c in range(cols - 1):
                u = node_map[(r, c)]
                v = node_map[(r, c + 1)]

                if r == 2:  # Designated Green Promenade
                    street_name = "Emerald Tree Boulevard"
                    heat_risk = rng.uniform(28.0, 38.0)
                    shade = rng.uniform(0.78, 0.90)
                    hydration = 1
                    surf_temp = 29.5
                elif r % 2 == 1:
                    street_name = f"Maple Avenue {r+1}"
                    heat_risk = rng.uniform(45.0, 58.0)
                    shade = rng.uniform(0.40, 0.60)
                    hydration = 0
                    surf_temp = 36.0
                else:  # High thermal exposure asphalt
                    street_name = f"Solar Expressway {r+1}"
                    heat_risk = rng.uniform(80.0, 92.0)
                    shade = rng.uniform(0.05, 0.15)
                    hydration = 0
                    surf_temp = 48.0

                router.add_street_segment(
                    u=u,
                    v=v,
                    street_name=street_name,
                    length_m=block_size_m,
                    heat_risk=heat_risk,
                    canopy_shade_ratio=shade,
                    hydration_points=hydration,
                    surface_temp_c=surf_temp,
                    bidirectional=True,
                )

        # Vertical streets:
        # - Col 0 & Col cols-1: Wide unshaded concrete streets (heat risk 82, shade 12%)
        # - Col 2 (Middle): "Parkside Way" (heat risk 35, shade 80%)
        for r in range(rows - 1):
            for c in range(cols):
                u = node_map[(r, c)]
                v = node_map[(r + 1, c)]

                if c == 2:  # Parkside North-South link
                    street_name = "Parkside Way"
                    heat_risk = rng.uniform(30.0, 42.0)
                    shade = rng.uniform(0.75, 0.88)
                    hydration = 1
                    surf_temp = 30.0
                elif c % 2 == 1:
                    street_name = f"Pine Street {c+1}"
                    heat_risk = rng.uniform(48.0, 62.0)
                    shade = rng.uniform(0.35, 0.55)
                    hydration = 0
                    surf_temp = 38.0
                else:  # High heat corridor
                    street_name = f"Concrete Canyon St {c+1}"
                    heat_risk = rng.uniform(82.0, 94.0)
                    shade = rng.uniform(0.05, 0.12)
                    hydration = 0
                    surf_temp = 51.0

                router.add_street_segment(
                    u=u,
                    v=v,
                    street_name=street_name,
                    length_m=block_size_m,
                    heat_risk=heat_risk,
                    canopy_shade_ratio=shade,
                    hydration_points=hydration,
                    surface_temp_c=surf_temp,
                    bidirectional=True,
                )

        return router


# -----------------------------------------------------------------------------
# Demo CLI Execution
# -----------------------------------------------------------------------------

def run_demo():
    """Demonstrate the Cool Corridor Navigation Engine on a synthetic urban network."""
    print("=" * 72)
    print("  TERRA07 SAFE COOL-CORRIDOR ROUTING ENGINE - HEATWAVE NAVIGATION  ")
    print("=" * 72)

    router = CoolRouter.create_synthetic_urban_grid(rows=5, cols=5, block_size_m=150.0)
    origin = "I_0_0"
    destination = "I_4_4"

    print(f"\nComputing paths from {origin} to {destination}...\n")
    comparison = router.route_and_compare(origin, destination)

    print(comparison.summary_markdown())

    print("\n--- STEP-BY-STEP COOL PATH TURN DIRECTIONS ---")
    for step in comparison.cool_path.turn_by_turn_directions:
        alert_tag = f" [{step.thermal_alert}]" if step.thermal_alert else ""
        print(f"Step {step.step_number}: {step.instruction}{alert_tag}")

    print("\n--- STEP-BY-STEP SHORTEST PATH TURN DIRECTIONS (HOT BASELINE) ---")
    for step in comparison.shortest_path.turn_by_turn_directions:
        alert_tag = f" [{step.thermal_alert}]" if step.thermal_alert else ""
        print(f"Step {step.step_number}: {step.instruction}{alert_tag}")

    print("\nDone. Engine ready for backend API and frontend Mapbox/Leaflet integration.")


if __name__ == "__main__":
    run_demo()
