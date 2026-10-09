"""Renders high-resolution architecture diagram to reports/figures/architecture.png."""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "reports" / "figures" / "architecture.png"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 8), dpi=200)
ax.set_xlim(0, 14)
ax.set_ylim(0, 8)
ax.axis("off")

# Colors
bg_blue = "#eff6ff"
border_blue = "#3b82f6"
bg_green = "#ecfdf5"
border_green = "#10b981"
bg_amber = "#fffbeb"
border_amber = "#f59e0b"
bg_purple = "#faf5ff"
border_purple = "#8b5cf6"

# Box style helper
def draw_box(x, y, w, h, bg, border, title, items):
    rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", linewidth=1.5, edgecolor=border, facecolor=bg)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h - 0.35, title, fontsize=11, fontweight="bold", ha="center", color="#0f172a")
    for idx, item in enumerate(items):
        ax.text(x + 0.2, y + h - 0.75 - (idx * 0.35), f"• {item}", fontsize=9, color="#334155")

# 1. Open Data Sources
draw_box(0.5, 4.2, 3.2, 3.4, bg_blue, border_blue, "Open Data Sources", [
    "Landsat 8/9 C2 L2 (STAC)",
    "Overture & OSM Buildings",
    "WorldPop 2020 100m Rasters",
    "OSM Walk & Amenity Graph",
    "Open-Meteo Weather API",
])

# 2. Batch Pipeline
draw_box(4.3, 4.2, 5.0, 3.4, bg_green, border_green, "Python Batch Pipeline (make all)", [
    "250m Metric UTM Grid (EPSG:32643)",
    "Feature Engineering & Physical Sanity",
    "IPCC AR6 Tri-Factor Risk Scoring",
    "Getis-Ord Gi* Hotspot Analysis",
    "Dirichlet Monte-Carlo Sensitivity (1k draws)",
    "Empirical Cooling Model (OLS + Bootstrapping)",
    "Action Engine (Shade, Water, Sanctuaries)",
])

# 3. Processed Datastore
draw_box(9.9, 4.2, 3.6, 3.4, bg_amber, border_amber, "data/processed/ (Committed)", [
    "scores.geojson (Scored Grid)",
    "priority_areas.csv",
    "actions.csv (Interventions)",
    "provenance.json",
    "validation.json",
])

# 4. User Applications
draw_box(2.5, 0.4, 4.2, 3.0, bg_purple, border_purple, "Urban Planner Command Center", [
    "Interactive Leaflet Choropleths",
    "Dynamic Layer Switcher",
    "XAI Driver Waterfall Charts",
    "Budget Knapsack Sandbox",
    "Monte Carlo Stability Plots",
])

draw_box(7.5, 0.4, 4.2, 3.0, bg_purple, border_purple, "Citizen Heat Advisory View", [
    "Multilingual: EN / HI / GU",
    "Live Weather & Alert Badges",
    "Neighbourhood Risk Tier",
    "Sanctuary Navigation & Walk Times",
    "7-Day Thermal Forecast",
])

# Arrows
arrow_kw = dict(arrowstyle="->", lw=2, color="#475569")
ax.annotate("", xy=(4.3, 5.9), xytext=(3.7, 5.9), arrowprops=arrow_kw)
ax.annotate("", xy=(9.9, 5.9), xytext=(9.3, 5.9), arrowprops=arrow_kw)

# Datastore down to Apps
ax.annotate("", xy=(4.6, 3.4), xytext=(11.0, 4.2), arrowprops=dict(arrowstyle="->", lw=2, color="#475569", connectionstyle="arc3,rad=-0.2"))
ax.annotate("", xy=(9.6, 3.4), xytext=(11.7, 4.2), arrowprops=dict(arrowstyle="->", lw=2, color="#475569", connectionstyle="arc3,rad=-0.15"))

plt.title("HeatLens System Architecture · Team TERRA07 · Agnitia Hackathon 2026", fontsize=14, fontweight="bold", pad=20, color="#0f172a")
plt.tight_layout()
plt.savefig(OUT_PATH, bbox_inches="tight", dpi=200)
plt.close()
print(f"Rendered architecture diagram to {OUT_PATH}")
