"""Urban Planner Command Center (Team TERRA07 · HeatLens).

Comprehensive spatial risk exploration, Getis-Ord Gi* hotspots, exact XAI attribution, and counterfactual action knapsack optimizer.
"""

from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

from heatlens.config import load_config, PROJECT_ROOT
from heatlens.explain import generate_explanation_sentence, get_cell_contributions_vs_median
from heatlens.scoring import score_features
from heatlens.actions.rank import optimize_budget_allocation
from app.components.map import build_planner_map
from app.components.charts import (
    render_waterfall_chart,
    render_score_gauge,
    render_cumulative_benefit_curve,
    render_rank_ci_chart,
)

st.set_page_config(page_title="Planner Dashboard · HeatLens", page_icon="🗺️", layout="wide")

SCORES_GEOJSON = PROJECT_ROOT / "data" / "processed" / "scores.geojson"
PRIORITY_CSV = PROJECT_ROOT / "data" / "processed" / "priority_areas.csv"
ACTIONS_CSV = PROJECT_ROOT / "data" / "processed" / "actions.csv"


@st.cache_data
def load_planner_datasets():
    gdf = gpd.read_file(SCORES_GEOJSON) if SCORES_GEOJSON.is_file() else gpd.GeoDataFrame()
    priorities = pd.read_csv(PRIORITY_CSV) if PRIORITY_CSV.is_file() else pd.DataFrame()
    actions = pd.read_csv(ACTIONS_CSV) if ACTIONS_CSV.is_file() else pd.DataFrame()
    config = load_config()
    return gdf, priorities, actions, config


gdf, priorities_df, actions_df, config = load_planner_datasets()

if gdf.empty:
    st.error("Processed data missing. Run `python scripts/run_pipeline.py` first.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.title("🗺️ Control Panel")

# Layer selection
layer_options = {
    "risk_score": "Composite Heat Risk (0-100)",
    "lst_mean_c": "Land Surface Temp (°C)",
    "ndvi_mean": "Green Cover (NDVI)",
    "building_coverage": "Building Density",
    "pop_density": "Population Density (/km²)",
}
selected_layer = st.sidebar.selectbox("Active Map Layer", options=list(layer_options.keys()), format_func=lambda x: layer_options[x])

basemap = st.sidebar.selectbox("Base Tile Provider", ["CartoDB light", "OpenStreetMap", "CartoDB dark"])

# Filters
st.sidebar.subheader("Zone Filters")
tier_filter = st.sidebar.multiselect("Filter Risk Tier", ["Low", "Moderate", "High", "Extreme"], default=["Low", "Moderate", "High", "Extreme"])
robust_only = st.sidebar.checkbox("Robust Hotspots Only (≥80% Stability)", value=False)
show_actions_overlay = st.sidebar.checkbox("Overlay Recommended Actions", value=True)

# Weight sliders & Sensitivity Simulation
with st.sidebar.expander("⚖️ Component Weights & Assumptions", expanded=False):
    st.caption("Adjust component weights to simulate alternative policy priorities (<1s in-memory recalculation).")
    w_h = st.slider("Hazard Weight (LST, Built-up, Deficit)", 0.05, 0.70, float(config.weights.components.hazard), 0.05)
    w_e = st.slider("Exposure Weight (Density, Pedestrians)", 0.05, 0.70, float(config.weights.components.exposure), 0.05)
    w_v = st.slider("Vulnerability Weight (Seniors, Children)", 0.05, 0.70, float(config.weights.components.vulnerability), 0.05)
    w_a = st.slider("Adaptive Gap Weight (Water, Cooling)", 0.05, 0.70, float(config.weights.components.adaptive_gap), 0.05)

    if st.button("Reset to Default Weights"):
        st.session_state["w_h"] = config.weights.components.hazard
        st.session_state["w_e"] = config.weights.components.exposure
        st.session_state["w_v"] = config.weights.components.vulnerability
        st.session_state["w_a"] = config.weights.components.adaptive_gap
        st.rerun()

# Apply in-memory recalculation if weights differ from baseline
custom_weights = {"components": {"hazard": w_h, "exposure": w_e, "vulnerability": w_v, "adaptive_gap": w_a}}
active_gdf = score_features(gdf, config=config, custom_weights=custom_weights)

# Apply filters
filtered_gdf = active_gdf[active_gdf["risk_tier"].isin(tier_filter)].copy()
if robust_only and "is_robust_hotspot" in filtered_gdf.columns:
    filtered_gdf = filtered_gdf[filtered_gdf["is_robust_hotspot"]]

# ---------------------------------------------------------
# MAIN TABS
# ---------------------------------------------------------
tab_map, tab_why, tab_prio, tab_actions, tab_robust, tab_export = st.tabs([
    "🗺️ Interactive Map",
    "🔍 Why This Score? (XAI)",
    "📋 Priority Areas",
    "💡 Action Ranking & Budget",
    "📊 Robustness & Validation",
    "💾 Export & Briefing",
])

# ----------------- TAB 1: MAP -----------------
with tab_map:
    st.subheader(f"Ahmedabad Human-Scale Microclimate Map — {layer_options[selected_layer]}")
    c_m1, c_m2 = st.columns([3, 1])

    with c_m2:
        st.markdown("**Inspect Specific Cell**")
        cell_ids = filtered_gdf["cell_id"].tolist()
        inspect_cell_id = st.selectbox("Select Cell ID to Focus", options=cell_ids, index=0 if cell_ids else None)

        if inspect_cell_id:
            cell_row = filtered_gdf[filtered_gdf["cell_id"] == inspect_cell_id].iloc[0]
            st.metric("Risk Score", f"{cell_row['risk_score']:.1f}", cell_row["risk_tier"])
            st.write(f"**Cluster:** {cell_row.get('cluster_name', 'Ahmedabad Sector')}")
            st.write(f"**Surface Temp:** {cell_row['lst_mean_c']} °C")
            st.write(f"**Residents:** {int(cell_row['pop_total']):,} ({int(cell_row['pop_65plus'])} seniors)")
            st.write(f"**Nearest Cooling:** {int(cell_row['dist_cooling_m'])} m")
            st.write(f"**Nearest Water:** {int(cell_row['dist_water_m'])} m")

    with c_m1:
        overlay_df = actions_df if show_actions_overlay else None
        m = build_planner_map(
            gdf=filtered_gdf,
            selected_layer=selected_layer,
            basemap=basemap,
            actions_overlay=overlay_df,
            highlight_cell_id=inspect_cell_id,
        )
        st_folium(m, width=950, height=560)

# ----------------- TAB 2: WHY THIS SCORE (XAI) -----------------
with tab_why:
    st.subheader("Explainable AI Driver Attribution & Diagnosis")
    col_w1, col_w2 = st.columns([1, 2])

    target_id = inspect_cell_id if inspect_cell_id else filtered_gdf.iloc[0]["cell_id"]
    target_row = active_gdf[active_gdf["cell_id"] == target_id].iloc[0]

    with col_w1:
        fig_gauge = render_score_gauge(target_row["risk_score"], target_row["risk_tier"])
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown(f"**Cell ID:** `{target_id}` | **Cluster:** {target_row.get('cluster_name', 'Ahmedabad')}")
        if target_row.get("is_robust_hotspot", False):
            st.success("🎯 **Robust Hotspot Verified**: Remains in top risk decile across ≥80% of Dirichlet weight perturbations.")

        # Raw values summary
        raw_metrics = {
            "Surface Temperature": f"{target_row['lst_mean_c']} °C",
            "Green Cover (NDVI)": f"{target_row['ndvi_mean']}",
            "Building Footprint": f"{round(target_row['building_coverage']*100, 1)}%",
            "Population": f"{int(target_row['pop_total']):,}",
            "Seniors (65+)": f"{int(target_row['pop_65plus'])}",
            "Distance to Water": f"{int(target_row['dist_water_m'])} m",
            "Distance to Cooling": f"{int(target_row['dist_cooling_m'])} m",
        }
        st.table(pd.DataFrame(list(raw_metrics.items()), columns=["Indicator", "Value"]))

    with col_w2:
        # Plain language AI diagnosis
        explanation_text = generate_explanation_sentence(target_row, active_gdf)
        st.info(f"🗣️ **Executive Diagnostic Summary:**\n\n{explanation_text}")

        # Waterfall chart vs area median
        contributions = get_cell_contributions_vs_median(target_row, active_gdf)
        fig_waterfall = render_waterfall_chart(contributions, target_row["risk_score"])
        st.plotly_chart(fig_waterfall, use_container_width=True)

# ----------------- TAB 3: PRIORITY AREAS -----------------
with tab_prio:
    st.subheader("Ranked Priority Areas (Bivariate Classification)")
    prio_mode = st.radio("Ranking Formulation:", ["By Composite Heat Risk (Intensity)", "By People-Weighted Risk (Person-Risk Points)"], horizontal=True)

    if not priorities_df.empty:
        sort_col = "risk_score" if "Composite" in prio_mode else "person_risk_points"
        ranked_display = priorities_df.sort_values(sort_col, ascending=False).reset_index(drop=True)
        ranked_display["Rank"] = range(1, len(ranked_display) + 1)

        st.dataframe(
            ranked_display[["Rank", "cell_id", "cluster_name", "risk_score", "risk_tier", "pop_total", "person_risk_points", "top_3_drivers"]].head(50),
            use_container_width=True,
            height=450,
        )

        csv_data = ranked_display.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Download Priority Areas CSV", data=csv_data, file_name="heatlens_priority_areas.csv", mime="text/csv")

# ----------------- TAB 4: ACTIONS & BUDGET -----------------
with tab_actions:
    st.subheader("Ranked Interventions & Budget Knapsack Allocation")
    st.caption("Interventions evaluated by counterfactual re-scoring: Person-Risk Points Averted per ₹ Million.")

    b_col1, b_col2 = st.columns([1, 2])
    with b_col1:
        budget_slider = st.slider("Municipal Planning Budget (₹ Lakhs)", min_value=10, max_value=500, value=150, step=10)
        budget_inr = budget_slider * 100_000.0

        selected_plan, plan_kpis = optimize_budget_allocation(actions_df, budget_inr=budget_inr)
        st.metric("Allocated Interventions", f"{plan_kpis.get('actions_selected_count', 0)} of {len(actions_df)}")
        st.metric("Total Lives Protected", f"{plan_kpis.get('total_people_benefited', 0):,}")
        st.metric("Person-Risk Points Averted", f"{plan_kpis.get('total_impact_points', 0):.1f}")
        st.metric("Budget Utilised", f"₹{plan_kpis.get('budget_spent_inr', 0)/1e5:.1f} Lakhs", f"Remaining: ₹{plan_kpis.get('budget_remaining_inr', 0)/1e5:.1f}L")

    with b_col2:
        fig_curve = render_cumulative_benefit_curve(actions_df, budget_inr)
        st.plotly_chart(fig_curve, use_container_width=True)

    st.markdown("### Optimal Action Package within Selected Budget")
    if not selected_plan.empty:
        st.dataframe(
            selected_plan[["global_rank", "action_type", "cluster_name", "people_benefited", "impact", "cost_inr", "benefit_cost", "rationale"]],
            use_container_width=True,
            height=320,
        )

# ----------------- TAB 5: ROBUSTNESS -----------------
with tab_robust:
    st.subheader("Monte Carlo Robustness & Stability Analysis (1,000 Dirichlet Draws)")
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        if "median_rank" in gdf.columns:
            fig_ranks = render_rank_ci_chart(gdf)
            st.plotly_chart(fig_ranks, use_container_width=True)
    with r_col2:
        if "top_decile_stability" in gdf.columns:
            fig_hist = px.histogram(
                gdf,
                x="top_decile_stability",
                nbins=20,
                title="<b>Top-Decile Stability Distribution Across Perturbations</b>",
                labels={"top_decile_stability": "Stability Score (Fraction of 1,000 Draws in Top Decile)"},
                color_discrete_sequence=["#2563eb"],
                template="plotly_white",
            )
            fig_hist.update_layout(height=450, margin=dict(l=10, r=20, t=40, b=30))
            st.plotly_chart(fig_hist, use_container_width=True)

# ----------------- TAB 6: EXPORT -----------------
with tab_export:
    st.subheader("Data Export & Executive Briefing Generation")
    c_e1, c_e2 = st.columns(2)

    with c_e1:
        st.markdown("#### Download Analysis Datasets")
        if SCORES_GEOJSON.is_file():
            with open(SCORES_GEOJSON, "r", encoding="utf-8") as f:
                geojson_str = f.read()
            st.download_button("📥 Download Scored Metric Grid (GeoJSON)", data=geojson_str, file_name="heatlens_scores.geojson", mime="application/geo+json")

        if ACTIONS_CSV.is_file():
            with open(ACTIONS_CSV, "r", encoding="utf-8") as f:
                actions_str = f.read()
            st.download_button("📥 Download Action Catalog (CSV)", data=actions_str, file_name="heatlens_actions.csv", mime="text/csv")

    with c_e2:
        st.markdown("#### One-Page Municipal Briefing")
        brief_cluster = st.selectbox("Select Target Cluster for Briefing", options=gdf["cluster_name"].unique())
        cluster_cells = gdf[gdf["cluster_name"] == brief_cluster]

        brief_md = f"""# HeatLens Municipal Action Brief: {brief_cluster}
**Team TERRA07 · Agnitia Hackathon 2026**

- **Surveyed Footprint:** {len(cluster_cells)} cells (250m metric grid, {(len(cluster_cells)*0.0625):.2f} km²)
- **Total Residents at Risk:** {int(cluster_cells['pop_total'].sum()):,} ({int(cluster_cells['pop_65plus'].sum())} seniors 65+)
- **Average Surface Temperature:** {cluster_cells['lst_mean_c'].mean():.1f} °C (Max: {cluster_cells['lst_mean_c'].max():.1f} °C)
- **Mean Heat Risk Index:** {cluster_cells['risk_score'].mean():.1f} / 100
- **Identified Robust Hotspots:** {int(cluster_cells['is_robust_hotspot'].sum())}

### Key Drivers:
{generate_explanation_sentence(cluster_cells.sort_values('risk_score', ascending=False).iloc[0], gdf)}

### Recommended Priority Interventions:
1. **Canopy Shading & Albedo Enhancement:** Target unshaded transit streets.
2. **Potable Water Kiosks:** Deficit areas require walking distance reduction to ≤ 300m.
3. **Air-Conditioned Cooling Sanctuaries:** Designate public school auditoriums during 11 AM - 5 PM peak heat hours.
"""
        st.text_area("Generated Markdown Brief", brief_md, height=220)
        st.download_button("📥 Download Markdown Brief", data=brief_md, file_name=f"brief_{brief_cluster.lower().replace(' ', '_')}.md", mime="text/markdown")
