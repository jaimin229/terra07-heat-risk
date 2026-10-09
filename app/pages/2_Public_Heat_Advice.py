"""Citizen Heat Advice & Cooling Sanctuary Finder (Team TERRA07 · HeatLens).

Mobile-accessible, multilingual public health thermal advisory in English, Hindi, and Gujarati.
"""

from pathlib import Path
import json
import yaml
import geopandas as gpd
import pandas as pd
import streamlit as st

from heatlens.config import PROJECT_ROOT
from heatlens.ingest.weather import get_weather_forecast

st.set_page_config(page_title="Citizen Heat Advice · HeatLens", page_icon="💧", layout="wide")

I18N_PATH = PROJECT_ROOT / "app" / "i18n.yaml"
SCORES_GEOJSON = PROJECT_ROOT / "data" / "processed" / "scores.geojson"
ACTIONS_CSV = PROJECT_ROOT / "data" / "processed" / "actions.csv"


@st.cache_data
def load_public_data():
    with open(I18N_PATH, "r", encoding="utf-8") as f:
        i18n = yaml.safe_load(f)
    gdf = gpd.read_file(SCORES_GEOJSON) if SCORES_GEOJSON.is_file() else gpd.GeoDataFrame()
    actions = pd.read_csv(ACTIONS_CSV) if ACTIONS_CSV.is_file() else pd.DataFrame()
    weather = get_weather_forecast(23.0225, 72.5714)
    return i18n, gdf, actions, weather


i18n_dict, gdf, actions_df, weather_data = load_public_data()

# Language Switcher
lang_col, _ = st.columns([2, 5])
with lang_col:
    lang = st.selectbox("🌐 Language / भाषा / ભાષા", options=["en", "hi", "gu"], format_func=lambda x: {"en": "English", "hi": "हिन्दी (Hindi)", "gu": "ગુજરાતી (Gujarati)"}[x])

t = i18n_dict.get(lang, i18n_dict["en"])

st.title(f"🌡️ {t['title']}")
st.caption(f"{t['subtitle']} · Team TERRA07")

# Area Selector
clusters = sorted(gdf["cluster_name"].unique()) if not gdf.empty else ["Ahmedabad Central"]
selected_cluster = st.selectbox(t["select_area"], options=clusters)

cluster_cells = gdf[gdf["cluster_name"] == selected_cluster] if not gdf.empty else gdf
cluster_risk = float(cluster_cells["risk_score"].mean()) if not cluster_cells.empty else 62.0
cluster_tier = cluster_cells.iloc[0]["risk_tier"] if not cluster_cells.empty else "High"
dist_water = int(cluster_cells["dist_water_m"].mean()) if not cluster_cells.empty else 280
dist_cool = int(cluster_cells["dist_cooling_m"].mean()) if not cluster_cells.empty else 750

# Weather Headline Card
today_f = weather_data.get("today", {})
t_max = today_f.get("max_temp_c", 42.4)
t_app = today_f.get("apparent_max_temp_c", 45.1)
heat_cat = today_f.get("heat_category", "Severe Heatwave")

st.markdown("---")
w1, w2, w3, w4 = st.columns(4)
with w1:
    st.metric(t["current_temp"], f"{t_max:.1f} °C", "Peak 2:30 PM")
with w2:
    st.metric(t["apparent_temp"], f"{t_app:.1f} °C", "Feels Like")
with w3:
    st.metric(t["heat_category"], heat_cat, "IMD Orange/Red Alert")
with w4:
    st.metric(t["local_risk"], f"{cluster_tier.upper()}", f"Score: {cluster_risk:.1f}/100")

# Emergency Heat Advice Box
st.markdown("---")
st.subheader(f"🛡️ {t['today_advice_title']} ({selected_cluster})")

advice_key = f"advice_{cluster_tier.lower()}"
advice_items = t.get(advice_key, t["advice_moderate"])

if cluster_tier == "Extreme":
    st.error("\n\n".join([f"• {item}" for item in advice_items]), icon="🚨")
elif cluster_tier == "High":
    st.warning("\n\n".join([f"• {item}" for item in advice_items]), icon="⚠️")
else:
    st.info("\n\n".join([f"• {item}" for item in advice_items]), icon="ℹ️")

# Sanctuaries & Navigation
st.markdown("---")
col_s1, col_s2 = st.columns(2)

with col_s1:
    st.subheader(f"❄️ {t['nearest_cooling_title']}")
    st.write(f"**{t['walking_distance']}:** `{dist_cool} metres`")
    st.write(f"**{t['est_walk_time']}:** `~{max(3, int(dist_cool / 75))} minutes walk`")
    lat_c = float(cluster_cells.iloc[0]["lat"]) if not cluster_cells.empty else 23.0225
    lon_c = float(cluster_cells.iloc[0]["lon"]) if not cluster_cells.empty else 72.5714
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat_c},{lon_c}&travelmode=walking"
    st.link_button(f"🗺️ {t['open_directions']}", gmaps_url)

with col_s2:
    st.subheader(f"🚰 {t['nearest_water_title']}")
    st.write(f"**{t['walking_distance']}:** `{dist_water} metres`")
    st.write(f"**{t['est_walk_time']}:** `~{max(2, int(dist_water / 75))} minutes walk`")
    st.link_button(f"🗺️ {t['open_directions']}", gmaps_url)

# 7-Day Forecast Strip
st.markdown("---")
st.subheader(f"📅 {t['forecast_7day']}")
daily_list = weather_data.get("daily", [])
if daily_list:
    cols = st.columns(min(7, len(daily_list)))
    for idx, day in enumerate(daily_list[:7]):
        with cols[idx]:
            st.markdown(f"**{day.get('date', f'Day {idx+1}')[-5:]}**")
            st.markdown(f"🌡️ **{day.get('max_temp_c', 40.0):.1f}°C**")
            st.caption(f"{day.get('heat_category', 'Normal')}")

st.markdown("---")
st.caption(f"ℹ️ {t['disclaimer']}")
st.error(f"📞 {t['emergency_call']}")
