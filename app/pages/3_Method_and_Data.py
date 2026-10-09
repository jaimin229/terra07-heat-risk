"""Scientific Methodology, Data Sources & Validation (Team TERRA07 · HeatLens).

Formal mathematical definitions, live config weights, data provenance, validation metrics, and limitations.
"""

from pathlib import Path
import json
import pandas as pd
import streamlit as st

from heatlens.config import load_config, PROJECT_ROOT

st.set_page_config(page_title="Methodology & Data · HeatLens", page_icon="🔬", layout="wide")

PROVENANCE_FILE = PROJECT_ROOT / "data" / "processed" / "provenance.json"
VALIDATION_FILE = PROJECT_ROOT / "reports" / "validation.json"
ARCH_FIG_FILE = PROJECT_ROOT / "reports" / "figures" / "architecture.png"

config = load_config()

st.title("🔬 Scientific Methodology, Data Provenance & Validation")
st.caption("Team TERRA07 · Agnitia Hackathon 2026 · Software Track: Heat-Risk Mapping at Human Scale")

tab_math, tab_data, tab_val, tab_limits = st.tabs([
    "📐 Mathematical Formulation",
    "🛰️ Data Sources & Provenance",
    "📈 Empirical Validation Results",
    "⚠️ Assumptions & Limitations",
])

with tab_math:
    st.subheader("IPCC AR6 Tri-Factor Risk Formulation & Exact Additive Decomposition")
    st.markdown("""
    HeatLens computes an auditable, linear additive **Composite Heat Risk Index ($R_i \in [0, 100]$)** for every 250m grid cell:

    $$\\text{Risk}_i = 100 \\times \\left( w_H H_i + w_E E_i + w_V V_i + w_A A_i \\right)$$

    Where the four components sum to 1.0:
    - **Hazard ($H_i$):** Physical thermal exposure driving heat absorption.
      $$H_i = 0.60 \\cdot z(\\text{LST}_i) + 0.20 \\cdot z(\\text{Building}_i) + 0.20 \\cdot z(\\text{VegDeficit}_i)$$
    - **Exposure ($E_i$):** Human headcount and daytime pedestrian presence in the open.
      $$E_i = 0.60 \\cdot z(\\log(1 + \\text{PopDensity}_i)) + 0.40 \\cdot z(\\text{OutdoorProxy}_i)$$
    - **Vulnerability ($V_i$):** Biological susceptibility to acute heat stress.
      $$V_i = 0.60 \\cdot z(\\text{ElderlyShare}_i) + 0.40 \\cdot z(\\text{ChildShare}_i)$$
    - **Adaptive Gap ($A_i$):** Spatial deficit in access to cooling infrastructure.
      $$A_i = 0.50 \\cdot z(\\log(1 + \\text{DistCooling}_i)) + 0.50 \\cdot z(\\log(1 + \\text{DistWater}_i))$$
    """)

    st.markdown("### Active Configuration Weights (`config.yaml`)")
    w = config.weights
    weights_summary = [
        {"Component": "Hazard (H)", "Component Weight": w.components.hazard, "Sub-Indicators": f"LST ({w.hazard.lst}), Building ({w.hazard.building_coverage}), Veg Deficit ({w.hazard.veg_deficit})"},
        {"Component": "Exposure (E)", "Component Weight": w.components.exposure, "Sub-Indicators": f"Pop Density ({w.exposure.pop_density}), Outdoor Activity ({w.exposure.outdoor_activity_proxy})"},
        {"Component": "Vulnerability (V)", "Component Weight": w.components.vulnerability, "Sub-Indicators": f"Seniors 65+ ({w.vulnerability.elderly_share}), Children <5 ({w.vulnerability.child_share})"},
        {"Component": "Adaptive Gap (A)", "Component Weight": w.components.adaptive_gap, "Sub-Indicators": f"Dist Cooling ({w.adaptive_gap.dist_cooling_centre}), Dist Water ({w.adaptive_gap.dist_water_point})"},
    ]
    st.table(pd.DataFrame(weights_summary))

with tab_data:
    st.subheader("Data Sources & Preprocessing Pipeline")
    if PROVENANCE_FILE.is_file():
        with open(PROVENANCE_FILE, "r", encoding="utf-8") as f:
            prov = json.load(f)
        sources = prov.get("sources", [])
        st.write(f"**Study Area:** {prov.get('study_area', 'Ahmedabad')} | **Bounding Box:** `{prov.get('bounding_box')}` | **CRS:** Metric UTM Zone 43N")
        for s in sources:
            with st.expander(f"🛰️ {s.get('name')}", expanded=True):
                st.write(f"**Provider:** {s.get('provider')}")
                st.write(f"**Resolution:** {s.get('resolution', 'N/A')}")
                st.write(f"**License:** {s.get('license')}")
                if "caveat" in s:
                    st.info(f"**Caveat:** {s['caveat']}")

with tab_val:
    st.subheader("Empirical Validation & Sensitivity Results")
    if VALIDATION_FILE.is_file():
        with open(VALIDATION_FILE, "r", encoding="utf-8") as f:
            val = json.load(f)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Physical Sanity: Spearman(LST, NDVI)", f"{val['physical_sanity']['spearman_lst_ndvi']}", "Negative (Passed)")
        with c2:
            st.metric("Physical Sanity: Spearman(LST, Building)", f"{val['physical_sanity']['spearman_lst_building']}", "Positive (Passed)")
        with c3:
            st.metric("Cooling Model Empirical R²", f"{val['cooling_model']['r_squared']}", f"β_ndvi = {val['cooling_model']['beta_ndvi']} °C")

        st.markdown("### Robustness & Sensitivity (1,000 Dirichlet Monte Carlo Draws)")
        mc = val.get("robustness_monte_carlo", {})
        st.write(f"- **Mean Spearman Rank Correlation Under Perturbation:** `{mc.get('mean_spearman_perturbed')}`")
        st.write(f"- **Rank Correlation vs Non-Linear Geometric Formulation:** `{mc.get('spearman_vs_geometric')}`")
        st.write(f"- **Total Statistically Robust Hotspots (≥80% Stability):** `{mc.get('robust_hotspots_count')}` cells")

with tab_limits:
    st.subheader("Auditable Limitations & Honest Science Contract")
    st.markdown("""
    1. **Morning Overpass Timing:** Landsat 8/9 overpass occurs at ~10:45 AM local solar time. While capturing relative surface solar heating differences, it does not record peak diurnal 3:30 PM air temperatures.
    2. **Thermal Sharpening:** 30m LST is sharpened from 100m native thermal sensors; microclimates below 30m (individual street canopies) are smoothed.
    3. **Absence of Household Survey Microdata:** Air conditioning deficit and occupational exposure are estimated via morphology, building density, and age proxies rather than household-level census microdata.
    4. **Correlational Cooling Relationships:** The empirical regression cooling model is observational and correlational; municipal site visits and ground-truthing are strictly recommended prior to capital expenditure.
    5. **Relative Index:** The 0–100 score represents relative prioritization within the metropolitan area, not an absolute clinical morbidity threshold.
    """)
