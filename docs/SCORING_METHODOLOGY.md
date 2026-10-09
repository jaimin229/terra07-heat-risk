# Urban Heat Risk Scoring Methodology & Biophysical Foundations
**Team TERRA07 — Software Track: Heat-Risk Mapping at Human Scale**  
**Lead Author:** Climate Risk Science Lead (Agent 1)  
**Framework Version:** 1.0.0 (Production Release)  
**Standard Reference:** IPCC Sixth Assessment Report (AR6) WGII Risk Formulation

---

## 1. Executive Summary & Objective

Urban extreme heat is the single deadliest weather-related hazard worldwide, responsible for tens of thousands of excess mortalities annually. Traditional municipal heat monitoring relies almost exclusively on regional synoptic weather stations or coarse satellite Land Surface Temperature (LST) rasters. These approaches fail because:
1. **Satellite thermal data alone is not risk**: An uninhabited industrial runway reaching 55°C represents zero direct human mortality risk, while an unshaded informal settlement market at 38°C with high elderly density and metal roofs constitutes an acute humanitarian emergency.
2. **City-scale averages obscure micro-scale realities**: Within the same 1 km² urban ward, human heat exposure varies drastically between a tree-shaded residential boulevard and an asphalt pedestrian corridor flanked by multi-story masonry walls.

This document establishes the rigorous mathematical and biophysical foundation for **Team TERRA07's Urban Heat Risk Engine (`engine/risk_engine.py`)**. The formulation formalizes the **Intergovernmental Panel on Climate Change (IPCC) Sixth Assessment Report (AR6)** disaster risk paradigm:

$$\text{Risk} = f(\text{Hazard}, \text{Exposure}, \text{Vulnerability})$$

It translates multi-source satellite imagery, meteorological data, pedestrian foot-traffic dynamics, and socio-demographic census statistics into a human-scale **Composite Heat Risk Index (HRI)** calibrated from **0 to 100**, evaluated across both macro-scale **Wards/Grid Cells** and micro-scale **Street Segments**.

---

## 2. IPCC AR6 Conceptual Risk Architecture

According to **IPCC AR6 WGII (Chapter 6: Cities, Settlements and Key Infrastructure; Cross-Chapter Paper 2: Cities)**, climate-related risk emerges from the dynamic interplay of three core dimensions:

```
                  ┌──────────────────────────────┐
                  │          URBAN RISK          │
                  │   Composite Heat Risk Index  │
                  └──────────────┬───────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
  │    HAZARD    │        │   EXPOSURE   │        │VULNERABILITY │
  │   Thermal    │   ×    │    Human     │   ×    │Physiological │
  │   Stress     │        │   Presence   │        │& Adaptive    │
  │  Intensity   │        │   Density    │        │  Deficits    │
  └──────────────┘        └──────────────┘        └──────────────┘
```

1. **Hazard ($H$)**: The physical intensity, duration, and magnitude of thermal and radiative anomalies across the urban landscape. Includes Land Surface Temperature (LST), ambient air Heat Index (combining dry-bulb temperature and humidity), built-up sensible heat storage (NDBI), and unattenuated solar irradiance.
2. **Exposure ($E$)**: The spatial co-location of humans with the thermal hazard footprint. Includes resident population density, active outdoor pedestrian foot-traffic, and occupational cohorts compelled to work outdoors (construction laborers, delivery couriers, street vendors).
3. **Vulnerability ($V$)**: The intrinsic propensity or predisposition of the exposed population to suffer physiological strain, morbidity, or mortality. Encompasses physiological sensitivity (elderly $>65$, infants $<5$, pre-existing cardiovascular/respiratory conditions) and structural/socioeconomic adaptive capacity deficits (cooling poverty / AC deficit, tin/asbestos uninsulated housing).

---

## 3. Mathematical Formulation & Normalization Architecture

### 3.1 Multi-Criteria Feature Rescaling (Min-Max Clamping)

Because raw input indicators possess disparate dimensions and physical units ($^\circ\text{C}$, $\text{W/m}^2$, $\text{persons/km}^2$, dimensionless indices $[-1, 1]$, and percentages $[0, 100\%]$), each indicator $x_k$ is transformed into a dimensionless standardized sub-score $\tilde{x}_k \in [0.0, 1.0]$ via boundary-clamped linear feature scaling:

$$\tilde{x}_k = \min\left(1.0, \, \max\left(0.0, \, \frac{x_k - x_{k,\min}}{x_{k,\max} - x_{k,\min}}\right)\right)$$

#### Biophysical and Empirical Calibration Bounds

| Dimension | Indicator Symbol | Indicator Name | Unit | Minimum ($x_{\min}$) | Maximum ($x_{\max}$) | Physical Rationale |
|:---|:---:|:---|:---:|:---:|:---:|:---|
| **Hazard** | $T_{\text{LST}}$ | Land Surface Temperature | $^\circ\text{C}$ | 24.0 | 52.0 | Baseline comfort floor vs. critical asphalt/bare ground radiant maximum. |
| **Hazard** | $HI$ | Ambient Air Heat Index | $^\circ\text{C}$ | 25.0 | 52.0 | NOAA neutral baseline vs. NOAA "Extreme Danger" threshold. |
| **Hazard** | $NDBI$ | Built-up Index | index | -0.30 | +0.60 | Vegetated/water surfaces vs. high-density impervious concrete canyon. |
| **Hazard** | $R_{\text{solar}}$ | Solar Irradiance ($GHI$) | $\text{W/m}^2$ | 200.0 | 1050.0 | Overcast diffuse floor vs. peak summer unshaded zenith radiation. |
| **Exposure** | $\rho_{\text{pop}}$ | Population Density | $\text{pers/km}^2$ | 0.0 | 30,000.0 | Uninhabited zone vs. ultra-dense Global South / Asian urban cores. |
| **Exposure** | $F_{\text{ped}}$ | Pedestrian Foot-Traffic | $\text{ped/hr}$ | 0.0 | 1,200.0 | Deserted street vs. peak commercial transit pedestrian thoroughfare. |
| **Exposure** | $W_{\text{out}}$ | Outdoor Workforce Share | $\%$ | 0.0 | 35.0 | Zero outdoor workforce vs. major informal/construction cluster. |
| **Vulnerability** | $P_{\text{eld}}$ | Elderly Population ($>65$) | $\%$ | 0.0 | 30.0 | Young demographic baseline vs. aging community concentration. |
| **Vulnerability** | $P_{\text{chi}}$ | Young Children ($<5$) | $\%$ | 0.0 | 20.0 | Minimal pediatric presence vs. high young child proportion. |
| **Vulnerability** | $P_{\text{AC-def}}$ | Low-Income / AC Deficit | $\%$ | 0.0 | 100.0 | Universal mechanical cooling vs. complete cooling poverty. |
| **Vulnerability** | $P_{\text{chr}}$ | Chronic Cardiorespiratory | $\%$ | 0.0 | 40.0 | Healthy population vs. high disease burden hotspot. |
| **Vulnerability** | $P_{\text{tin}}$ | Tin/Uninsulated Roofing | $\%$ | 0.0 | 100.0 | Insulated concrete/clay tiles vs. 100% informal tin/asbestos sheets. |

---

### 3.2 Sub-Index Aggregation Equations

Within each primary dimension, standardized indicators are combined using multi-criteria weighted linear combinations where all weights strictly satisfy $\sum w = 1.0$:

#### 1. Hazard Sub-Index ($H \in [0.0, 1.0]$)
$$H = w_{\text{LST}} \cdot \tilde{T}_{\text{LST}} + w_{\text{HI}} \cdot \widetilde{HI} + w_{\text{NDBI}} \cdot \widetilde{NDBI} + w_{\text{solar}} \cdot \tilde{R}_{\text{solar}}$$
$$\text{Weights: } w_{\text{LST}} = 0.35, \quad w_{\text{HI}} = 0.35, \quad w_{\text{NDBI}} = 0.15, \quad w_{\text{solar}} = 0.15$$

#### 2. Exposure Sub-Index ($E \in [0.0, 1.0]$)
$$E = w_{\text{pop}} \cdot \tilde{\rho}_{\text{pop}} + w_{\text{ped}} \cdot \tilde{F}_{\text{ped}} + w_{\text{work}} \cdot \tilde{W}_{\text{out}}$$
$$\text{Weights: } w_{\text{pop}} = 0.40, \quad w_{\text{ped}} = 0.30, \quad w_{\text{work}} = 0.30$$

#### 3. Vulnerability Sub-Index ($V \in [0.0, 1.0]$)
$$V = w_{\text{eld}} \cdot \tilde{P}_{\text{eld}} + w_{\text{chi}} \cdot \tilde{P}_{\text{chi}} + w_{\text{AC}} \cdot \tilde{P}_{\text{AC-def}} + w_{\text{chr}} \cdot \tilde{P}_{\text{chr}} + w_{\text{tin}} \cdot \tilde{P}_{\text{tin}}$$
$$\text{Weights: } w_{\text{eld}} = 0.25, \quad w_{\text{chi}} = 0.15, \quad w_{\text{AC}} = 0.25, \quad w_{\text{chr}} = 0.20, \quad w_{\text{tin}} = 0.15$$

---

### 3.3 Composite Heat Risk Index (HRI) Formulation

To compute the final **Composite Heat Risk Index (HRI)** on a continuous scale from **0.0 to 100.0**, the engine utilizes the **Geometric Multiplicative Aggregation** derived directly from the IPCC AR6 disaster framework:

$$\text{HRI} = 100 \times \left( H \times E \times V \right)^{1/3}$$

#### Axiomatic Justification of the Geometric Mean:
1. **Preservation of the Zero-Exposure Axiom**:
   If Exposure $E = 0$ (e.g., an unpopulated desert, an airport runway, or a solar farm), then $\text{HRI} = 0$. Purely additive models ($\text{HRI} \propto w_H H + w_E E + w_V V$) produce artificial hazard scores of 30–40 in completely unpopulated regions, misallocating municipal emergency response resources.
2. **Preservation of the Zero-Hazard Axiom**:
   If thermal conditions are mild ($H = 0$), then regardless of how dense or vulnerable the population is, heat-related morbidity risk is zero.
3. **Equi-Elasticity Across Dimensions**:
   A 10% percentage improvement in reducing exposure (e.g. moving workers indoors) or reducing vulnerability (e.g. providing cooling sanctuaries) exerts equal proportionate leverage on lowering the total risk index.

*(Note: The engine also supports `multiplicative_scaled` $\text{HRI} = 100 \times H \times \sqrt{E \cdot V}$ and `arithmetic` options via the `aggregation_mode` configuration parameter).*

---

## 4. Biophysical Thresholds & Meteorological Foundations

### 4.1 Wet Bulb Temperature ($T_w$) and Physiological Survivability Limits

Humans maintain homeostatic internal core body temperatures ($37.0^\circ\text{C}$) primarily through the evaporation of sweat from the skin into the surrounding air. The thermodynamic driving force for evaporative cooling is governed by the wet-bulb temperature ($T_w$).

- **The $35^\circ\text{C}$ Thermodynamic Upper Limit (Sherwood & Huber, 2010)**:
  At a sustained wet-bulb temperature of $35^\circ\text{C}$ ($95^\circ\text{F}$), the skin temperature ($T_{\text{skin}} \approx 35^\circ\text{C}$) equilibrates with the ambient air at 100% relative humidity. Metabolic heat generation ($\approx 100\,\text{W}$ at rest, $300\text{--}500\,\text{W}$ during light physical labor) cannot be dissipated into the environment via conduction, convection, or radiation. Core body temperature rises continuously until hyperthermia and fatal heatstroke occur within 4 to 6 hours, regardless of water supply or acclimation.
- **The Empirical Non-Compensable Limit ($31^\circ\text{C}$, Vecellio et al., 2022)**:
  Recent experimental chamber studies at Penn State University demonstrated that for active young adults performing minimal tasks of daily life, the critical environmental limit where core temperature begins unconstrained elevation occurs much earlier, between **$30.5^\circ\text{C}$ and $31.5^\circ\text{C}$ wet bulb**.

#### Calculation via Stull's (2011) Formulation:
The risk engine implements Stull's empirical polynomial, accurate to within $\pm 0.3^\circ\text{C}$ across standard surface pressures:

$$T_w = T_{\text{air}} \cdot \arctan\left(0.151977 \cdot \sqrt{RH + 8.313659}\right) + \arctan(T_{\text{air}} + RH) - \arctan(RH - 1.676331) + 0.00391838 \cdot (RH)^{1.5} \cdot \arctan(0.023101 \cdot RH) - 4.686035$$

---

### 4.2 Land Surface Temperature ($T_{\text{LST}}$) & Surface Urban Heat Island (SUHI)

While ambient air temperature ($T_{\text{air}}$) measures free kinetic molecular heat at 2 meters above ground level, **Land Surface Temperature ($T_{\text{LST}}$)**—derived from thermal infrared satellite sensors (Landsat 8/9 TIRS Band 10, ECOSTRESS, MODIS)—quantifies the radiative skin temperature of urban surfaces (asphalt, concrete pavements, building facades, and rooftops).

- **Why $42^\circ\text{C}$ LST Represents Extreme Hazard**:
  When satellite radiometric LST exceeds **$42^\circ\text{C}$**, ground asphalt and roofing materials commonly reach **$55^\circ\text{C}\text{ to }68^\circ\text{C}$**. This produces extreme localized long-wave thermal re-radiation ($L_{\uparrow} = \epsilon \sigma T^4$), dramatically elevating the pedestrian **Mean Radiant Temperature ($T_{\text{mrt}}$)** to over $60^\circ\text{C}$. This radiative heat load overwhelms human thermoregulation even before air temperatures exceed $38^\circ\text{C}$.
- **Nocturnal Heat Trapping**: Dense impervious materials ($NDBI > 0.30$) absorb vast quantities of sensible heat during daylight hours, which is continuously re-radiated throughout the night, preventing nocturnal thermal recovery.

---

### 4.3 NOAA National Weather Service Heat Index ($HI$)

The engine resolves or calculates the Steadman Heat Index using the 9-parameter polynomial regression developed by Rothfusz (1990) for temperatures $T \ge 26.7^\circ\text{C}$ ($80^\circ\text{F}$):

$$\begin{aligned}
HI_{\text{F}} = &-42.379 + 2.04901523\,T_F + 10.14333127\,RH - 0.22475541\,T_F\,RH \\
&- 0.00683783\,T_F^2 - 0.05481717\,RH^2 + 0.00122874\,T_F^2\,RH \\
&+ 0.00085282\,T_F\,RH^2 - 0.00000199\,T_F^2\,RH^2
\end{aligned}$$

With NOAA low-humidity and high-humidity boundary adjustments applied as standard.

#### NOAA Operational Danger Thresholds:
- **Caution** ($27.0^\circ\text{C} - 32.2^\circ\text{C}$): Fatigue possible with prolonged exposure.
- **Extreme Caution** ($32.2^\circ\text{C} - 39.4^\circ\text{C}$): Heat stroke, heat cramps, and heat exhaustion possible with prolonged exposure.
- **Danger** ($39.4^\circ\text{C} - 51.1^\circ\text{C}$): Heat stroke, cramps, or exhaustion likely; heat stroke possible with continued activity.
- **Extreme Danger** ($\ge 51.1^\circ\text{C}$): Heat stroke or sunstroke highly imminent.

---

## 5. Human-Scale Downscaling: Street Segments vs. Wards

A core innovation of Team TERRA07's engine is dual-scale spatial evaluation:

```
┌───────────────────────────────────────┐
│     Macro-Scale: Ward / Grid Cell     │
│   (100m – 1000m resolution polygon)   │
│ - Average LST, NDBI, Regional HI      │
│ - Census population density           │
│ - Ward-level demographic vulnerability│
└──────────────────┬────────────────────┘
                   │ Downscaling
                   ▼
┌───────────────────────────────────────┐
│   Micro-Scale: Human Street Segment   │
│   (10m – 50m resolution line/corridor)│
│ - Microclimate tree canopy shade      │
│ - Street canyon aspect ratio (H/W)    │
│ - Real-time pedestrian foot-traffic   │
│ - Outdoor worker cluster concentration│
└───────────────────────────────────────┘
```

### 5.1 Biophysical Microclimate Downscaling Physics for Streets

Streets possess unique microclimates heavily modulated by urban geometry and vegetative canopy cover:

1. **Tree Canopy Solar Radiative Interception**:
   Dense tree foliage intercepts shortwave direct solar radiation via leaf area index (LAI) extinction. The effective solar irradiance $R_{\text{solar, eff}}$ incident upon pedestrians on a street segment is formulated as:
   $$R_{\text{solar, eff}} = R_{\text{solar}} \times \left(1.0 - 0.75 \times \frac{\text{Canopy}_{\%}}{100}\right)$$
   Where $0.75$ represents the empirical foliage extinction coefficient ($k$) for urban broadleaf deciduous/evergreen canopies.

2. **Canopy Surface Cooling & Evapotranspirative Offset**:
   Empirical field studies (Bowler et al., 2010; Santamouris et al., 2017) demonstrate that unshaded asphalt can be up to $15\text{--}20^\circ\text{C}$ hotter than shaded pavement. The localized effective LST along the street corridor is attenuated by:
   $$T_{\text{LST, eff}} = T_{\text{LST}} - \left(4.5^\circ\text{C} \times \frac{\text{Canopy}_{\%}}{100}\right)$$

3. **Urban Canyon Aspect Ratio ($H/W$) Sensible Heat Trap**:
   In deep urban street canyons where building height $H$ significantly exceeds street width $W$ ($H/W > 1.0$), reduced Sky View Factor (SVF) impedes nocturnal radiative dissipation. We model this microclimate retention penalty as:
   $$\Delta HI_{\text{canyon}} = \max\left(0.0, \, \frac{H}{W} - 1.0\right) \times 0.8^\circ\text{C}$$
   Simultaneously, vegetative transpiration cools ambient air by up to $-1.5^\circ\text{C}$ under complete canopy cover:
   $$HI_{\text{eff}} = HI + \Delta HI_{\text{canyon}} - \left(1.5^\circ\text{C} \times \frac{\text{Canopy}_{\%}}{100}\right)$$

---

## 6. Categorization & Public Health Action Protocols

The continuous Composite Heat Risk Index ($\text{HRI} \in [0, 100]$) is classified into five operational tiers strictly aligned with international early warning standards (WMO/WHO Heatwaves and Health Guidance):

| Category | HRI Score Range | Color Code | Map Hex | Physical & Health Impact | Operational Municipal Action Protocol |
|:---|:---:|:---:|:---:|:---|:---|
| **Low** | $0.0 - 25.0$ | Emerald Green | `#2ECC71` | Normal baseline thermal conditions; negligible excess mortality. | Routine monitoring; standard hydration advisories on public information portals. |
| **Moderate** | $25.01 - 50.0$ | Amber Yellow | `#F1C40F` | Noticeable thermal discomfort; early fatigue in sensitive individuals. | Advisory alert; recommend shaded pedestrian corridors; voluntary cooling breaks for manual workers. |
| **High** | $50.01 - 70.0$ | Orange | `#E67E22` | High risk of heat exhaustion and cramps; pediatric and elderly strain. | Amber alert; deploy mobile misting stations; extend air-conditioned public facility hours; issue mandatory hydration warnings to employers. |
| **Severe** | $70.01 - 85.0$ | Crimson Red | `#E74C3C` | High risk of life-threatening heat stroke; spike in emergency ambulance dispatches. | Red alert; activate designated municipal cooling shelters; enforce mandatory 15-minute rest/hour for outdoor labor; dispatch paramedical street patrols. |
| **Extreme** | $85.01 - 100.0$ | Deep Purple | `#8E44AD` | Critical humanitarian heat emergency; non-compensable hyperthermia risk across general population. | Emergency disaster declaration; halt all non-essential outdoor labor; open 24/7 climate sanctuaries; emergency dispatch of municipal water tankers. |

---

## 7. Data Pipeline & Input Schema Specifications

The engine consumes standardized data payloads derived from remote sensing, meteorological reanalysis, and demographic sources:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      DATA INGESTION STACK                              │
├────────────────────────────────┬───────────────────────────────────────┤
│ Spatial Indicator              │ Representative Data Sources           │
├────────────────────────────────┼───────────────────────────────────────┤
│ Land Surface Temp (LST)        │ Landsat 8/9 Band 10 (30m), ECOSTRESS  │
│ Air Temp & Relative Humidity   │ ERA5-Land Reanalysis, Weather Stations│
│ Built-up Index (NDBI)          │ Sentinel-2 / Landsat-8 (SWIR - NIR)   │
│ Solar Irradiance (GHI)         │ CAMS Radiation Service, NSRDB         │
│ Resident Population Density    │ GHSL (100m), WorldPop, Census Tracts  │
│ Pedestrian Foot-Traffic        │ Street Camera Analytics, Telemetry    │
│ Outdoor Workforce Share        │ National Sample Survey, Labor Stats   │
│ Demographic Vulnerability      │ National Census (Age >65, Age <5)     │
│ AC Deficit / Low Income        │ Energy Poverty Audits, Slum Surveys   │
│ Chronic Health Burden          │ Municipal Public Health Registries    │
│ Tin/Asbestos Roof Share        │ Aerial Orthophoto ML Classification  │
│ Street Tree Canopy Cover       │ LiDAR Point Clouds, NDVI Shadow Mask  │
│ Street Canyon Aspect Ratio     │ OpenStreetMap Building Heights & Width│
└────────────────────────────────┴───────────────────────────────────────┘
```

---

## 8. Verification & Test Suite Summary

The mathematical formulation is fully implemented in `engine/risk_engine.py` and validated by both an internal validation suite and an external `pytest` regression suite (`tests/test_risk_engine.py`):

1. **Biophysical Calculations Test**: Verifies Rothfusz Heat Index and Stull Wet Bulb formulations against benchmark meteorological psychrometric tables.
2. **Boundary and Clamping Test**: Confirms that non-physical input values (e.g. negative densities or outlier temperatures) are clamped without runtime exceptions.
3. **Weight Normalization Test**: Ensures that any weight specification deviating from $1.000$ strictly raises a `ValueError`.
4. **Zero-Exposure Axiom Test**: Proves that unpopulated environments evaluate to strictly $\text{HRI} = 0.0$.
5. **Microclimate Canopy Attenuation Test**: Verifies that adding street tree canopy cover proportionally reduces effective surface temperatures, effective solar radiation, and the resulting composite risk score.
6. **Serialization & Batch Processing**: Verifies seamless dictionary export (`to_dict`) ready for REST API serialization and GeoJSON spatial pipeline outputs.

---

## 9. References & Key Scientific Literature

1. **IPCC, 2022**: *Climate Change 2022: Impacts, Adaptation, and Vulnerability. Contribution of Working Group II to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change* (Chapter 6: Cities, Settlements and Key Infrastructure; Cross-Chapter Paper 2: Cities). Cambridge University Press.
2. **Sherwood, S. C., & Huber, M. (2010)**: An adaptability limit to climate change due to heat stress. *Proceedings of the National Academy of Sciences (PNAS)*, 107(21), 9552–9555.
3. **Vecellio, D. J., Wolf, S. T., Cottle, R. M., & Kenney, W. L. (2022)**: Evaluating the 35°C wet-bulb temperature adaptability threshold for young, healthy subjects (PSU HEAT project). *Journal of Applied Physiology*, 132(2), 340–345.
4. **Stull, R. (2011)**: Wet-bulb temperature from relative humidity and air temperature. *Journal of Applied Meteorology and Climatology*, 50(11), 2267–2269.
5. **Rothfusz, L. P. (1990)**: The heat index equation (or, more than you ever wanted to know about heat index). *National Oceanic and Atmospheric Administration, Technical Attachment SR/SSD 90-23*.
6. **Bowler, D. E., Buyung-Ali, L., Knight, T. M., & Pullin, A. S. (2010)**: Urban greening to cool towns and cities: A systematic review of the empirical evidence. *Landscape and Urban Planning*, 97(3), 147–155.
7. **Santamouris, M., et al. (2017)**: Passive and active cooling for the outdoor built environment—Analysis and state of the art. *Solar Energy*, 154, 14–33.
8. **World Health Organization & World Meteorological Organization (2015)**: *Heatwaves and Health: Guidance on Warning-System Development*. WMO-No. 1142.
