"""Leaflet and Folium map rendering components for HeatLens."""

from typing import Dict, Any, List, Optional
import folium
from folium import plugins
import geopandas as gpd
import numpy as np


LAYER_CONFIGS = {
    "risk_score": {
        "name": "Heat Risk Index (0-100)",
        "column": "risk_score",
        "colors": ["#10b981", "#fbbf24", "#f97316", "#ef4444", "#7f1d1d"],
        "bins": [0, 25, 50, 70, 85, 100],
    },
    "lst_mean_c": {
        "name": "Land Surface Temp (°C)",
        "column": "lst_mean_c",
        "colors": ["#3b82f6", "#10b981", "#facc15", "#f97316", "#dc2626"],
        "bins": [30, 36, 40, 44, 48, 54],
    },
    "ndvi_mean": {
        "name": "Green Cover (NDVI)",
        "column": "ndvi_mean",
        "colors": ["#78350f", "#d97706", "#fef08a", "#84cc16", "#15803d"],
        "bins": [0.0, 0.10, 0.20, 0.35, 0.50, 0.80],
    },
    "building_coverage": {
        "name": "Building Coverage Fraction",
        "column": "building_coverage",
        "colors": ["#f8fafc", "#cbd5e1", "#94a3b8", "#64748b", "#0f172a"],
        "bins": [0.0, 0.20, 0.40, 0.60, 0.75, 1.0],
    },
    "pop_density": {
        "name": "Population Density (per km²)",
        "column": "pop_density",
        "colors": ["#fef3c7", "#fde047", "#f59e0b", "#d97706", "#7c2d12"],
        "bins": [0, 10000, 20000, 30000, 40000, 60000],
    },
}


def get_fill_color(val: float, layer_key: str) -> str:
    cfg = LAYER_CONFIGS.get(layer_key, LAYER_CONFIGS["risk_score"])
    bins = cfg["bins"]
    colors = cfg["colors"]
    for i in range(len(bins) - 1):
        if bins[i] <= val <= bins[i + 1]:
            return colors[i]
    return colors[-1] if val > bins[-1] else colors[0]


def build_planner_map(
    gdf: gpd.GeoDataFrame,
    selected_layer: str = "risk_score",
    basemap: str = "CartoDB positron",
    show_amenities: bool = True,
    actions_overlay: Optional[gpd.GeoDataFrame] = None,
    highlight_cell_id: Optional[str] = None,
) -> folium.Map:
    """Constructs a responsive Folium Leaflet map with styled choropleth polygons and interactive tooltips."""
    # Compute center of bbox
    bounds = gdf.total_bounds
    center_lat = float((bounds[1] + bounds[3]) / 2.0)
    center_lon = float((bounds[0] + bounds[2]) / 2.0)

    tiles_dict = {
        "CartoDB light": "CartoDB positron",
        "OpenStreetMap": "OpenStreetMap",
        "CartoDB dark": "CartoDB dark_matter",
    }
    tile_name = tiles_dict.get(basemap, "CartoDB positron")

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles=tile_name,
        control_scale=True,
    )

    # 1. GeoJSON Choropleth Layer
    col_name = LAYER_CONFIGS.get(selected_layer, {}).get("column", "risk_score")

    def style_fn(feature):
        props = feature["properties"]
        val = float(props.get(col_name, 0.0))
        cid = str(props.get("cell_id", ""))
        is_highlight = highlight_cell_id and cid == str(highlight_cell_id)

        color = get_fill_color(val, selected_layer)
        return {
            "fillColor": color,
            "color": "#b91c1c" if is_highlight else "#64748b",
            "weight": 3.0 if is_highlight else 0.8,
            "fillOpacity": 0.72 if not is_highlight else 0.90,
        }

    # Tooltip fields
    tooltip = folium.GeoJsonTooltip(
        fields=["cell_id", "cluster_name", "risk_score", "risk_tier", "lst_mean_c", "pop_total"],
        aliases=["Cell ID:", "Cluster:", "Risk Index:", "Tier:", "Surface Temp:", "Population:"],
        localize=True,
        sticky=True,
        labels=True,
        style="""
            background-color: #0f172a;
            color: #f8fafc;
            font-family: sans-serif;
            font-size: 12px;
            padding: 8px;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        """,
    )

    # Ensure EPSG:4326 for folium
    wgs_gdf = gdf.to_crs("EPSG:4326")
    folium.GeoJson(
        wgs_gdf,
        name="Heat Risk Metric Grid",
        style_function=style_fn,
        tooltip=tooltip,
    ).add_to(m)

    # 2. Recommended Action Markers
    if actions_overlay is not None and not actions_overlay.empty:
        action_cluster = plugins.MarkerCluster(name="Recommended Interventions").add_to(m)
        for _, act in actions_overlay.iterrows():
            atype = act["action_type"]
            icon_name = "tree" if atype == "shade" else ("tint" if atype == "water_point" else "plus-square")
            icon_color = "green" if atype == "shade" else ("blue" if atype == "water_point" else "purple")

            folium.Marker(
                location=[act["lat"], act["lon"]],
                popup=folium.Popup(f"<b>Rank #{act.get('global_rank', act.get('rank_within_type', 1))} {atype.upper()}</b><br>{act['rationale']}<br><b>Cost:</b> ₹{act['cost_inr']:,.0f}", max_width=300),
                icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa"),
            ).add_to(action_cluster)

    folium.LayerControl(collapsed=False).add_to(m)
    return m
