# 🌡️ TERRA07 · Human-Scale Heat Risk Intelligence
**Team ID:** `TERRA07` | **Track:** Software Track | **Hackathon:** Agnitia Hackathon 2026  
**Status:** 100% Fully Built & Audited · 152 Automated Tests Passing · Production-Ready  
**Public Repository:** [https://github.com/jaimin229/terra07-heat-risk](https://github.com/jaimin229/terra07-heat-risk)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11](https://img.shields.io/badge/Python-3.11-brightgreen.svg)](https://python.org)
[![Tests: 152 Passed](https://img.shields.io/badge/Tests-152%20Passed-success.svg)](tests/)
[![Data: Landsat%208%2F9%20C2%20L2](https://img.shields.io/badge/Data-USGS%2FNASA%20Verified-blue.svg)](data/processed/provenance.json)
[![UI: Material%20Design%203](https://img.shields.io/badge/UI-Google%20Material%203-teal.svg)](frontend/)

---

## 📌 Executive Summary
City-wide weather forecasts hide that dense, paved neighbourhoods with little shade and many elderly people or outdoor workers suffer far more than greener areas during extreme heatwaves. **TERRA07** maps urban heat risk at a human scale (neighbourhood wards and street corridors) across Ahmedabad, Gujarat, India, combining Land Surface Temperature (LST), urban morphology, demographic vulnerability, and walking-network access gaps.

Beyond diagnostic mapping, TERRA07 calculates **grounded feature attributions** (*"Why is this area at high risk?"*) and solves **budget-constrained knapsack allocations** to deploy canopy shading, potable water/misting kiosks, and air-conditioned cooling sanctuaries ranked strictly by person-risk points averted per rupee (₹) invested.

```
+---------------------------------------------------------------------------------------------------------+
| TOTAL SURVEYED CELLS | POPULATION IN HIGH/EXTREME RISK | SENIORS 65+ AT RISK | STATISTICAL ROBUST HOTSPOTS |
|     1,088 Cells      |     538,679 (45.3% of total)    |   48,210 (52.1%)    |   27 Monte-Carlo Hotspots   |
+---------------------------------------------------------------------------------------------------------+
```

---

## 🏛️ Dual-Experience Product Delivery (Google Material Design 3)

TERRA07 provides two calm, trustworthy civic-tech interfaces:

### 1. Urban Planner Command Center (8 Dedicated Screens)
- **1. Heat Risk Overview:** City-wide alert banner, 5 key KPI cards (mean risk 54.9, 533k at risk, 4 critical zones), Leaflet overview map, and *"Where should we act first?"* priority panel.
- **2. Full Heat-Risk Map:** Full-width interactive GIS map with Carto Positron basemap, layer selector (Composite, LST, Canopy, SVI), and click-to-inspect drawer.
- **3. Priority Areas:** Filterable, sortable data table across all 48 wards and 147 streets with one-click CSV export.
- **4. Area Inspector:** Deep-dive into Danilimda Industrial South (and all wards) with demographic metrics and 4 physical driver breakdown bars.
- **5. Scenario Simulator:** Stress-test microclimate heatwaves (+0°C to +5°C), time of day, humidity, and power reliability with Before vs After metrics.
- **6. Intervention Planner:** Municipal budget sandbox in Indian Rupees (**₹4,50,000** default) with unit adjustment controls and Knapsack optimization review modal.
- **7. Reports & Export:** Downloadable 1-page Executive Briefing PDF, full CSV datasets, and architecture diagrams.
- **8. Data & Methodology:** IPCC AR6 formula documentation ($HRI = 0.40 H + 0.30 E + 0.30 V$), data sources, and confidence disclosure.

### 2. Citizen Heat Safety Portal (Mobile-First • EN / GU / HI)
- **Current Heat Alert:** Peak danger window (11:30 AM – 4:30 PM), feels-like temperatures, and emergency helpline **108**.
- **Check My Street:** Autocomplete search (Manek Chowk, Khadia, Odhav, Vatva) with thermal danger meters and shaded alternatives.
- **Personal Safety Advice:** Persona selector (Senior 65+, Outdoor Worker / Rider, Parent with Infant, General Public) with hydration protocols, symptom watchlists, medical disclaimer, and local browser privacy notice.
- **Find Shelter & Water:** Top 5 nearby cooling havens with *"View All Locations"* toggle, verified badges (`✓ Verified today`), and accurate geodesic distance calculations (no fake `0m away`).
- **Cool Walk Navigation:** Side-by-side route comparison (Shortest route vs Cooler route with ~18% less direct-sun exposure).

---

## 🏗️ System Architecture

```mermaid
flowchart LR
  subgraph Sources[Open Data Sources]
    L[Landsat 8/9 C2 L2<br/>Planetary Computer STAC]
    B[Overture / OSM Buildings]
    P[WorldPop 2020<br/>Age-Sex Rasters]
    O[OSM Walk Network + Amenities]
    W[Open-Meteo Weather API]
  end

  subgraph Pipeline[Python Batch Pipeline - make all]
    G[Grid 250m UTM EPSG:32643]
    I[Feature Ingestion & Physical Sanity]
    S[IPCC AR6 Tri-Factor Scoring]
    H[Getis-Ord Gi* Spatial Hotspots]
    R[Dirichlet Monte-Carlo Sensitivity]
    M[Empirical Cooling Regression]
    A[Action Knapsack Optimizer]
  end

  subgraph Store[data/processed/ - Committed Offline]
    D1[(scores.geojson)]
    D2[(priority_areas.csv)]
    D3[(actions.csv)]
    D4[(provenance.json)]
    D5[(validation.json)]
  end

  subgraph App[Dual Client Applications]
    PL[Streamlit Planner Dashboard<br/>XAI Waterfalls, Folium GIS]
    PU[Citizen Public View<br/>EN / HI / GU Navigation]
    FA[FastAPI REST Service<br/>run_app.py Interactive Portal]
  end

  L --> I
  B --> I
  P --> I
  O --> I
  G --> I --> S --> H --> M --> A
  S --> R
  H --> D1
  R --> D1
  S --> D2
  A --> D3
  I --> D4
  M --> D5
  D1 --> PL
  D2 --> PL
  D3 --> PL
  D4 --> PL
  D1 --> PU
  W --> PU
  D1 --> FA
```

![Architecture Diagram](reports/figures/architecture.png)

---

## 🔬 Scientific Methodology

HeatLens follows the **IPCC AR6 Tri-Factor Climate Risk Formulation**:

$$\text{Risk}_i = 100 \times \left( 0.35 H_i + 0.25 E_i + 0.25 V_i + 0.15 A_i \right)$$

1. **Hazard ($H_i$):** $0.60 \cdot z(\text{LST}) + 0.20 \cdot z(\text{BuildingCov}) + 0.20 \cdot z(\text{VegDeficit})$
2. **Exposure ($E_i$):** $0.60 \cdot z(\log(1 + \text{PopDensity})) + 0.40 \cdot z(\text{OutdoorProxy})$
3. **Vulnerability ($V_i$):** $0.60 \cdot z(\text{ElderlyShare}) + 0.40 \cdot z(\text{ChildShare})$
4. **Adaptive Gap ($A_i$):** $0.50 \cdot z(\log(1 + \text{DistCooling})) + 0.50 \cdot z(\log(1 + \text{DistWater}))$

### Exact Linear Additive Closure
Every single indicator contribution arithmetically sums to the final Risk Score:
$$\text{Risk}_i \equiv c_{\text{lst}} + c_{\text{bldg}} + c_{\text{veg}} + c_{\text{pop}} + c_{\text{outdoor}} + c_{\text{eld}} + c_{\text{child}} + c_{\text{cooling}} + c_{\text{water}}$$
$$\text{Max Difference across 1,088 cells: } |\Delta| < 10^{-6} \text{ pts (Zero black-box residual)}$$

### Counterfactual Action Prioritisation
- **City-Specific Cooling Model:** Fitted via cell-level OLS with HC3 robust SEs:
  $$\text{LST} = -24.33 \times \text{NDVI} + 5.12 \times \text{Bldg} - 1.84 \times \text{OpenSpace} + 46.12 \quad (R^2 = 0.961)$$
  *(Bootstrap 1,000 resamples 95% CI for $\beta_{\text{ndvi}}$: $[-25.19, -23.29]$ °C; conservative lower bound applied for ranking).*
- **Potable Water Kiosks ($k=15$):** Submodular greedy maximum coverage of demand nodes ($\ge 63\%$ of theoretical optimum).
- **Cooling Sanctuaries ($k=8$):** Greedy maximum coverage of vulnerable seniors and children within 1,000m walk.
- **Unified Common Impact Metric:** $\text{Impact} = \sum \text{Population}_i \times (\text{Risk}_{\text{before}} - \text{Risk}_{\text{after}}) / 1000$ (Person-Risk Points Averted).

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.11+
- Virtual environment recommended

### 2. Installation
```bash
git clone https://github.com/jaimin229/terra07-heat-risk.git
cd terra07-heat-risk
python -m pip install -r requirements.txt
```

### 3. Run Precomputed Pipeline & Verification
```bash
# Run complete end-to-end batch pipeline
python scripts/run_pipeline.py

# Run all 152 automated unit and integration tests
python -m pytest tests/
```

### 4. Launch Applications
```bash
# Option A: Launch Streamlit Multipage Scientific App
streamlit run app/streamlit_app.py

# Option B: Launch Unified Interactive Portal (FastAPI + Leaflet UI)
python run_app.py
```

---

## 📊 Verification & Validation Results

From `reports/validation.json`:
- **Physical Coupling:** $\rho(\text{LST}, \text{NDVI}) = -0.981$ (Strict negative correlation verified)
- **Morphology Coupling:** $\rho(\text{LST}, \text{BuildingCoverage}) = +0.857$ (Strict positive correlation verified)
- **Temporal Consistency:** Multi-scene split-halves composite Spearman rank correlation $\rho = 0.884$
- **Monte Carlo Stability (1,000 Draws):** Mean Spearman rank correlation under perturbation $\rho = 0.984$
- **Non-Linear Model Comparison:** Spearman rank correlation vs Geometric formulation $\rho = 0.938$

---

## ⚠️ Limitations & Governance Contract

1. **Morning Overpass Timing:** Landsat 8/9 overpasses Ahmedabad at ~10:45 AM local solar time, capturing relative solar surface heating rather than peak diurnal 3:30 PM air temperatures.
2. **Spatial Aggregation:** 250m grid cells resolve neighborhood and street-corridor scale; sub-parcel microclimates (isolated trees or individual shade awnings) are smoothed.
3. **Absence of Clinical Case Data:** Hospital heatstroke admission logs are not publicly released at street level; clinical morbidity calibration can be enhanced if municipal authorities provide 108 ambulance dispatch records.
4. **Planning Assumptions:** All intervention costs are transparent, editable municipal assumptions in `config.yaml`.

---

## 👥 Team TERRA07 · Agnitia Hackathon 2026
- **Lead Geospatial Scientist & Modeler:** Team TERRA07 Climate Lead
- **Full-Stack GIS & Systems Architect:** Team TERRA07 Engineering Lead
- **Repository Structure:** Conforms strictly to Agnitia Hackathon specifications (`00` through `09`).
- **Deliverables:** Architecture Diagram (`reports/figures/architecture.png`), Executive Report (`reports/report.pdf`, `reports/report.md`), Scored Dataset (`data/processed/scores.geojson`), Action Plan (`data/processed/actions.csv`).
