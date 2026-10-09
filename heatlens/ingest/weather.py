"""Open-Meteo live weather and heatwave categorization client."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from heatlens.config import load_config, PROJECT_ROOT

logger = logging.getLogger(__name__)
CACHE_DIR = PROJECT_ROOT / "data" / "cache"


def classify_imd_heat_tier(t_max_c: float) -> Dict[str, str]:
    """Classifies daytime max temperature using Indian Meteorological Department (IMD) plains criteria."""
    if t_max_c >= 45.0:
        return {
            "tier": "Severe Heatwave",
            "color": "#990000",
            "alert": "RED ALERT",
            "description": "Severe heatwave conditions. High probability of heat illness and heatstroke."
        }
    elif t_max_c >= 40.0:
        return {
            "tier": "Heatwave",
            "color": "#D32F2F",
            "alert": "ORANGE ALERT",
            "description": "Heatwave conditions. Moderate to high risk for vulnerable people."
        }
    elif t_max_c >= 37.0:
        return {
            "tier": "Very Hot",
            "color": "#F57C00",
            "alert": "YELLOW ALERT",
            "description": "Very hot weather. Stay hydrated and avoid unshaded midday sun."
        }
    else:
        return {
            "tier": "Normal / Moderate",
            "color": "#388E3C",
            "alert": "GREEN",
            "description": "Normal seasonal heat conditions."
        }


def fetch_open_meteo_weather(lat: float = 23.0225, lon: float = 72.5714, use_cache: bool = True) -> Dict[str, Any]:
    """Fetches 7-day forecast from Open-Meteo with local caching and offline fallback."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / "weather_cache.json"

    # Try live request
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,apparent_temperature_max,relative_humidity_2m_mean"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature"
        f"&timezone=auto&forecast_days=7"
    )

    try:
        resp = requests.get(url, timeout=4.0)
        if resp.status_code == 200:
            data = resp.json()
            data["_fetched_at"] = datetime.now(timezone.utc).isoformat()
            data["_is_live"] = True
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return _process_weather_data(data)
    except Exception as e:
        logger.warning(f"Live weather fetch failed: {e}. Falling back to cached data.")

    # Fallback to cache if available
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_is_live"] = False
            return _process_weather_data(data)
        except Exception:
            pass

    # Deterministic physical baseline for Ahmedabad pre-monsoon
    fallback_data = {
        "_is_live": False,
        "_fetched_at": datetime.now(timezone.utc).isoformat(),
        "current": {
            "temperature_2m": 42.4,
            "relative_humidity_2m": 31.0,
            "apparent_temperature": 46.1
        },
        "daily": {
            "time": ["2026-05-15", "2026-05-16", "2026-05-17", "2026-05-18", "2026-05-19", "2026-05-20", "2026-05-21"],
            "temperature_2m_max": [43.1, 44.2, 44.8, 45.2, 44.0, 43.5, 42.8],
            "apparent_temperature_max": [46.8, 48.1, 49.2, 49.8, 48.0, 47.3, 46.5],
            "relative_humidity_2m_mean": [28.0, 27.5, 29.0, 31.0, 30.5, 29.0, 32.0]
        }
    }
    return _process_weather_data(fallback_data)


def _process_weather_data(raw: Dict[str, Any]) -> Dict[str, Any]:
    daily = raw.get("daily", {})
    t_max_list = daily.get("temperature_2m_max", [42.0])
    app_max_list = daily.get("apparent_temperature_max", [45.0])
    rh_list = daily.get("relative_humidity_2m_mean", [30.0])
    times = daily.get("time", ["Today"])

    today_max = float(t_max_list[0])
    today_apparent = float(app_max_list[0])
    today_rh = float(rh_list[0])
    tier_info = classify_imd_heat_tier(today_max)

    forecast_days = []
    for i in range(len(times)):
        t_m = float(t_max_list[i])
        cat = classify_imd_heat_tier(t_m)
        forecast_days.append({
            "date": times[i],
            "temp_max_c": t_m,
            "apparent_max_c": float(app_max_list[i]),
            "rh_mean_pct": float(rh_list[i]),
            "tier": cat["tier"],
            "color": cat["color"]
        })

    return {
        "is_live": raw.get("_is_live", False),
        "fetched_at": raw.get("_fetched_at", ""),
        "today_max_c": today_max,
        "today_apparent_c": today_apparent,
        "today_rh_pct": today_rh,
        "heat_tier": tier_info["tier"],
        "heat_color": tier_info["color"],
        "alert_level": tier_info["alert"],
        "guidance_summary": tier_info["description"],
        "seven_day_forecast": forecast_days
    }
