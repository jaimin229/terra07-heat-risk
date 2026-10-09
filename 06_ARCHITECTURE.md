# 06 — Architecture

The AI must render this diagram to `reports/figures/architecture.png` (use `mermaid-cli` via npx if network allows, otherwise `matplotlib`/`graphviz`) and embed it in README, the Method page and the report.

```mermaid
flowchart LR
  subgraph Sources[Open data sources]
    L[Landsat 8/9 C2 L2<br/>Planetary Computer STAC]
    B[Overture / OSM buildings]
    P[WorldPop 2020<br/>age-sex rasters]
    O[OSM amenities + walk network]
    W[Open-Meteo forecast]
  end

  subgraph Pipeline[Python batch pipeline - make all]
    G[Grid 250 m UTM]
    I[Ingest + QA masks<br/>cache + provenance]
    F[Feature aggregation<br/>features.parquet]
    S[Scoring H E V A<br/>exact contributions]
    H[Hotspots Gi* + priority classes]
    R[Sensitivity Monte Carlo]
    A[Action engine<br/>shade / water / cooling<br/>counterfactual re-scoring]
  end

  subgraph Store[data/processed - committed]
    D1[(scores.geojson)]
    D2[(priority_areas.csv)]
    D3[(actions.csv)]
    D4[(provenance.json)]
  end

  subgraph App[Streamlit app]
    PL[Planner dashboard<br/>Leaflet map, drivers, actions]
    PU[Public advice view<br/>EN / HI / GU]
    ME[Method + data page]
  end

  L --> I
  B --> I
  P --> I
  O --> I
  G --> I --> F --> S --> H --> A
  S --> R
  H --> D1
  R --> D1
  S --> D2
  A --> D3
  I --> D4
  D1 --> PL
  D2 --> PL
  D3 --> PL
  D4 --> ME
  D1 --> PU
  W --> PU
  O --> PU
```

## Design decisions (state them in the report)
- **Batch + static store, thin app:** heavy geospatial work runs once; the app is fast, reproducible and demo-safe offline.
- **Local UTM grid:** metric distances/areas are correct; cells are comparable.
- **Linear composite index:** exact attribution, auditable by non-technical planners.
- **Counterfactual action engine:** actions evaluated by re-running the same scoring, so impact numbers are consistent with the map.
- **Provenance everywhere:** every output carries its source and date.

## Sequence for one planner query (clicking a cell)
1. Streamlit reads the clicked cell id from `streamlit-folium` return value.
2. Looks up the row in cached GeoDataFrame → shows contributions (precomputed, or recomputed instantly with user weights).
3. Looks up actions touching that cell and sensitivity stats.
