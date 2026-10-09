"""Grid builder for HeatLens: generates 250m metric cells in local UTM projection."""

import math
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Polygon, Point, box
import pandas as pd

from heatlens.config import load_config, PROJECT_ROOT


def build_utm_grid(config=None) -> gpd.GeoDataFrame:
    """Builds a regular 250m grid across the configured bounding box."""
    if config is None:
        config = load_config()

    west, south, east, north = config.bbox
    # Bounding box polygon in WGS84
    bbox_poly = box(west, south, east, north)
    gs = gpd.GeoSeries([bbox_poly], crs="EPSG:4326")
    utm_crs = gs.estimate_utm_crs()  # EPSG:32643 for Ahmedabad

    # Project to UTM
    gs_utm = gs.to_crs(utm_crs)
    minx, miny, maxx, maxy = gs_utm.total_bounds

    grid_size = float(config.grid_size_m)
    cols = int(math.ceil((maxx - minx) / grid_size))
    rows = int(math.ceil((maxy - miny) / grid_size))

    polygons = []
    cell_ids = []
    row_indices = []
    col_indices = []

    for r in range(rows):
        y_top = maxy - r * grid_size
        y_bot = maxy - (r + 1) * grid_size
        for c in range(cols):
            x_left = minx + c * grid_size
            x_right = minx + (c + 1) * grid_size
            cell_poly = box(x_left, y_bot, x_right, y_top)
            polygons.append(cell_poly)
            cell_ids.append(f"r{r:02d}_c{c:02d}")
            row_indices.append(r)
            col_indices.append(c)

    gdf = gpd.GeoDataFrame(
        {
            "cell_id": cell_ids,
            "row": row_indices,
            "col": col_indices,
            "geometry": polygons,
        },
        crs=utm_crs,
    )

    # Compute centroids and reproject to WGS84
    centroids_utm = gdf.geometry.centroid
    centroids_wgs84 = centroids_utm.to_crs("EPSG:4326")

    gdf["centroid_x_utm"] = centroids_utm.x
    gdf["centroid_y_utm"] = centroids_utm.y
    gdf["lon"] = centroids_wgs84.x.round(6)
    gdf["lat"] = centroids_wgs84.y.round(6)
    gdf["area_m2"] = gdf.geometry.area

    # Also store wgs84 geometry for Leaflet mapping
    gdf_wgs84 = gdf.to_crs("EPSG:4326")
    gdf["geometry_wgs84"] = gdf_wgs84.geometry

    return gdf


def save_grid(gdf: gpd.GeoDataFrame, output_path: Path = None):
    if output_path is None:
        output_path = PROJECT_ROOT / "data" / "processed" / "grid.geoparquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Save standard geometry in UTM
    out = gdf.drop(columns=["geometry_wgs84"], errors="ignore")
    out.to_parquet(output_path)
    return output_path
