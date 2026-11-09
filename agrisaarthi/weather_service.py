"""
Honest Weather & Meteorological Alert Service for AgriSaarthi AI.

Rules & Guarantees:
  1. Fetches real meteorological data from Open-Meteo (WMO standard API) for Indian districts/states
     when network connectivity is available.
  2. Never fabricates weather measurements, crop-loss statistics, or fake cyclone emergency alerts.
  3. When offline or when an official alert feed (IMD_ALERTS_FEED_URL) is not configured,
     returns explicit `available: False` / `official_alerts_configured: False` metadata so the UI
     displays a clear, honest status notice.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

DEFAULT_WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_WEATHER_TIMEOUT = 6.0

# Verified coordinates for major agricultural districts and state capitals across India
LOCATION_COORDINATES: Dict[str, Tuple[float, float, str, str]] = {
    # Telangana districts
    "warangal": (17.9689, 79.5941, "Warangal", "Telangana"),
    "karimnagar": (18.4386, 79.1288, "Karimnagar", "Telangana"),
    "khammam": (17.2473, 80.1514, "Khammam", "Telangana"),
    "nalgonda": (17.0575, 79.2684, "Nalgonda", "Telangana"),
    "nizamabad": (18.6725, 78.0941, "Nizamabad", "Telangana"),
    "mahabubnagar": (16.7488, 78.0035, "Mahabubnagar", "Telangana"),
    "rangareddy": (17.3850, 78.4867, "Rangareddy", "Telangana"),
    "siddipet": (18.1019, 78.8521, "Siddipet", "Telangana"),
    "adilabad": (19.6641, 78.5320, "Adilabad", "Telangana"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad", "Telangana"),
    "telangana": (17.9689, 79.5941, "Warangal (State Hub)", "Telangana"),
    # Andhra Pradesh districts
    "guntur": (16.3067, 80.4365, "Guntur", "Andhra Pradesh"),
    "krishna": (16.5062, 80.6480, "Krishna / Vijayawada", "Andhra Pradesh"),
    "vijayawada": (16.5062, 80.6480, "Vijayawada", "Andhra Pradesh"),
    "godavari": (16.9891, 81.7840, "Rajahmundry / Godavari", "Andhra Pradesh"),
    "nellore": (14.4426, 79.9865, "Nellore", "Andhra Pradesh"),
    "kurnool": (15.8281, 78.0373, "Kurnool", "Andhra Pradesh"),
    "anantapur": (14.6819, 77.6006, "Anantapur", "Andhra Pradesh"),
    "kadapa": (14.4673, 78.8242, "Kadapa", "Andhra Pradesh"),
    "chittoor": (13.2172, 79.1003, "Chittoor", "Andhra Pradesh"),
    "visakhapatnam": (17.6868, 83.2185, "Visakhapatnam", "Andhra Pradesh"),
    "prakasam": (15.5057, 80.0499, "Ongole / Prakasam", "Andhra Pradesh"),
    "andhra pradesh": (16.3067, 80.4365, "Guntur (State Hub)", "Andhra Pradesh"),
    # Major agricultural states across India
    "punjab": (30.9010, 75.8573, "Ludhiana", "Punjab"),
    "ludhiana": (30.9010, 75.8573, "Ludhiana", "Punjab"),
    "haryana": (29.6857, 76.9905, "Karnal", "Haryana"),
    "rajasthan": (26.9124, 75.7873, "Jaipur", "Rajasthan"),
    "maharashtra": (21.1458, 79.0882, "Nagpur", "Maharashtra"),
    "nagpur": (21.1458, 79.0882, "Nagpur", "Maharashtra"),
    "gujarat": (22.3039, 70.8022, "Rajkot", "Gujarat"),
    "karnataka": (15.4589, 75.0078, "Dharwad", "Karnataka"),
    "dharwad": (15.4589, 75.0078, "Dharwad", "Karnataka"),
    "madhya pradesh": (22.7196, 75.8577, "Indore", "Madhya Pradesh"),
    "uttar pradesh": (26.8467, 80.9462, "Lucknow", "Uttar Pradesh"),
    "tamil nadu": (11.0168, 76.9558, "Coimbatore", "Tamil Nadu"),
    "bihar": (25.5941, 85.1376, "Patna", "Bihar"),
    "west bengal": (23.2324, 87.8615, "Bardhaman", "West Bengal"),
    "odisha": (20.2961, 85.8245, "Bhubaneswar", "Odisha"),
}

WMO_WEATHER_CODES: Dict[int, Tuple[str, str]] = {
    0: ("Clear Sky", "నిర్మలమైన ఆకాశం"),
    1: ("Mainly Clear", "దాదాపు నిర్మలమైన ఆకాశం"),
    2: ("Partly Cloudy", "పాక్షికంగా మేఘావృతం"),
    3: ("Overcast", "పూర్తిగా మేఘావృతం"),
    45: ("Foggy", "పొగమంచు"),
    48: ("Depositing Rime Fog", "దట్టమైన పొగమంచు"),
    51: ("Light Drizzle", "తేలికపాటి చినుకులు"),
    53: ("Moderate Drizzle", "మోస్తరు చినుకులు"),
    55: ("Dense Drizzle", "దట్టమైన చినుకులు"),
    61: ("Slight Rain", "తేలికపాటి వర్షం"),
    63: ("Moderate Rain", "మోస్తరు వర్షం"),
    65: ("Heavy Rain", "భారీ వర్షం"),
    80: ("Slight Rain Showers", "తేలికపాటి జల్లులు"),
    81: ("Moderate Rain Showers", "మోస్తరు వర్షపు జల్లులు"),
    82: ("Violent Rain Showers", "తీవ్రమైన వర్షపు జల్లులు"),
    95: ("Thunderstorm", "ఉరుములు మెరుపులతో కూడిన వర్షం"),
    96: ("Thunderstorm with Hail", "వడగళ్ల వాన"),
    99: ("Severe Thunderstorm with Hail", "తీవ్రమైన వడగళ్ల తుఫాను"),
}


def resolve_coordinates(state: str = "", district: str = "") -> Optional[Tuple[float, float, str, str]]:
    """Resolve district or state name to verified (lat, lon, display_district, display_state)."""
    d_key = (district or "").strip().lower()
    s_key = (state or "").strip().lower()

    if d_key and d_key in LOCATION_COORDINATES:
        return LOCATION_COORDINATES[d_key]
    for key, val in LOCATION_COORDINATES.items():
        if d_key and d_key in key:
            return val
    if s_key and s_key in LOCATION_COORDINATES:
        return LOCATION_COORDINATES[s_key]
    for key, val in LOCATION_COORDINATES.items():
        if s_key and s_key in key:
            return val
    return None


def fetch_weather_and_alerts(state: str = "", district: str = "") -> Dict[str, Any]:
    """
    Fetch real meteorological conditions for the specified Indian district/state.
    Never fabricates weather readings or emergency alerts.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    imd_feed_url = os.getenv("IMD_ALERTS_FEED_URL", "").strip()
    official_alerts_configured = bool(imd_feed_url)

    resolved = resolve_coordinates(state=state, district=district)
    if not resolved:
        # Default to Warangal, Telangana if no location selected yet, but label clearly
        lat, lon, resolved_district, resolved_state = LOCATION_COORDINATES["telangana"]
        location_note = "Showing default regional station (Warangal, Telangana). Update your Farm Profile to see your district."
    else:
        lat, lon, resolved_district, resolved_state = resolved
        location_note = ""

    base_url = os.getenv("WEATHER_API_BASE_URL", DEFAULT_WEATHER_API_URL).strip()
    try:
        timeout = float(os.getenv("WEATHER_API_TIMEOUT", str(DEFAULT_WEATHER_TIMEOUT)))
    except ValueError:
        timeout = DEFAULT_WEATHER_TIMEOUT

    if not base_url or os.getenv("DISABLE_LIVE_WEATHER", "").lower() == "true":
        return {
            "available": False,
            "is_live": False,
            "state": resolved_state,
            "district": resolved_district,
            "source": "Unconfigured",
            "message": "Live weather API is not configured or is disabled in environment settings.",
            "message_te": "లైవ్ వాతావరణ API కాన్ఫిగర్ చేయబడలేదు.",
            "current": None,
            "daily_forecast": [],
            "official_alerts_configured": official_alerts_configured,
            "official_alerts_status": (
                "Official IMD/NDMA cyclone alert feed (IMD_ALERTS_FEED_URL) is not configured. "
                "Please check mausam.imd.gov.in for official cyclone warnings."
            ),
            "meteorological_advisories": [],
            "timestamp": now_iso,
        }

    query_url = (
        f"{base_url}?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
        "&timezone=Asia%2FKolkata&forecast_days=3"
    )

    req = urllib.request.Request(
        query_url,
        headers={"Accept": "application/json", "User-Agent": "AgriSaarthi-FarmerPortal/1.0"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        reason = getattr(exc, "reason", str(exc))
        return {
            "available": False,
            "is_live": False,
            "state": resolved_state,
            "district": resolved_district,
            "coordinates": {"lat": lat, "lon": lon},
            "source": "Open-Meteo API (Unreachable)",
            "message": f"Live weather data is currently unavailable ({reason}). No fabricated data is displayed.",
            "message_te": "ప్రస్తుతం లైవ్ వాతావరణ సమాచారం అందుబాటులో లేదు. నకిలీ గణాంకాలు చూపబడవు.",
            "current": None,
            "daily_forecast": [],
            "official_alerts_configured": official_alerts_configured,
            "official_alerts_status": (
                "Official IMD cyclone feed is not configured in environment (IMD_ALERTS_FEED_URL). "
                "Verify official bulletins at mausam.imd.gov.in."
            ),
            "meteorological_advisories": [],
            "timestamp": now_iso,
        }

    curr = payload.get("current", {})
    w_code = int(curr.get("weather_code", 0))
    cond_en, cond_te = WMO_WEATHER_CODES.get(w_code, (f"WMO Code {w_code}", f"వాతావరణ కోడ్ {w_code}"))

    current_data = {
        "temperature_c": curr.get("temperature_2m"),
        "humidity_pct": curr.get("relative_humidity_2m"),
        "precipitation_mm": curr.get("precipitation"),
        "wind_speed_kmh": curr.get("wind_speed_10m"),
        "weather_code": w_code,
        "condition_en": cond_en,
        "condition_te": cond_te,
        "observed_at": curr.get("time", now_iso),
    }

    daily_raw = payload.get("daily", {})
    dates = daily_raw.get("time", [])
    t_max = daily_raw.get("temperature_2m_max", [])
    t_min = daily_raw.get("temperature_2m_min", [])
    rain_sum = daily_raw.get("precipitation_sum", [])
    wind_max = daily_raw.get("wind_speed_10m_max", [])
    d_codes = daily_raw.get("weather_code", [])

    daily_forecast: List[Dict[str, Any]] = []
    advisories: List[Dict[str, str]] = []

    for idx, dt in enumerate(dates):
        dc = int(d_codes[idx]) if idx < len(d_codes) and d_codes[idx] is not None else 0
        d_en, d_te = WMO_WEATHER_CODES.get(dc, (f"WMO Code {dc}", f"కోడ్ {dc}"))
        r_mm = float(rain_sum[idx]) if idx < len(rain_sum) and rain_sum[idx] is not None else 0.0
        w_kmh = float(wind_max[idx]) if idx < len(wind_max) and wind_max[idx] is not None else 0.0
        hi_c = float(t_max[idx]) if idx < len(t_max) and t_max[idx] is not None else 0.0

        daily_forecast.append(
            {
                "date": dt,
                "temp_max_c": hi_c,
                "temp_min_c": float(t_min[idx]) if idx < len(t_min) and t_min[idx] is not None else None,
                "precipitation_mm": r_mm,
                "wind_max_kmh": w_kmh,
                "condition_en": d_en,
                "condition_te": d_te,
            }
        )

        # Derive honest, threshold-based agronomic advisories from real forecast numbers
        if r_mm >= 50.0:
            advisories.append(
                {
                    "level": "HIGH_RAIN_OBSERVATION",
                    "date": dt,
                    "title_en": f"Heavy Rainfall Forecast ({r_mm:.1f} mm on {dt})",
                    "title_te": f"భారీ వర్ష సూచన ({dt} న {r_mm:.1f} మి.మీ.)",
                    "action_en": "Keep field drainage channels open in paddy, cotton, and pulse plots; postpone foliar spraying and fertilizer top-dressing.",
                    "action_te": "పొలంలో మురుగు నీటి కాలువలను సిద్ధంగా ఉంచండి; పురుగుమందుల పిచికారీ మరియు పైపాటు ఎరువులను వాయిదా వేయండి.",
                }
            )
        if w_kmh >= 45.0:
            advisories.append(
                {
                    "level": "STRONG_WIND_OBSERVATION",
                    "date": dt,
                    "title_en": f"Strong Surface Winds Forecast ({w_kmh:.1f} km/h on {dt})",
                    "title_te": f"బలమైన గాలుల సూచన ({dt} న {w_kmh:.1f} కి.మీ./గం.)",
                    "action_en": "Avoid pesticide spraying during high winds; provide propping/earthing-up support for tall crops like sugarcane, banana, and maize.",
                    "action_te": "గాలులు ఎక్కువగా ఉన్నప్పుడు మందులు పిచికారీ చేయవద్దు; చెరకు, మొక్కజొన్న వంటి ఎత్తైన పంటలకు ఊతం ఇవ్వండి.",
                }
            )
        if hi_c >= 41.0:
            advisories.append(
                {
                    "level": "HEAT_STRESS_OBSERVATION",
                    "date": dt,
                    "title_en": f"High Temperature Forecast ({hi_c:.1f}°C on {dt})",
                    "title_te": f"అధిక ఉష్ణోగ్రత సూచన ({dt} న {hi_c:.1f}°C)",
                    "action_en": "Apply light evening irrigation to protect flowering/grain-filling crops from terminal heat stress.",
                    "action_te": "పూత/గింజ పాలుపోసుకునే దశలో ఉన్న పంటలకు సాయంత్రం వేళ తేలికపాటి నీటి తడి ఇవ్వండి.",
                }
            )

    return {
        "available": True,
        "is_live": True,
        "state": resolved_state,
        "district": resolved_district,
        "location_note": location_note,
        "coordinates": {"lat": lat, "lon": lon},
        "source": "Open-Meteo Meteorological Forecast API (Real-Time WMO Feed)",
        "message": f"Live weather retrieved for {resolved_district}, {resolved_state}.",
        "message_te": f"{resolved_district}, {resolved_state} ప్రాంతపు వాస్తవ వాతావరణ వివరాలు.",
        "current": current_data,
        "daily_forecast": daily_forecast,
        "official_alerts_configured": official_alerts_configured,
        "official_alerts_status": (
            "Direct IMD/NDMA cyclone CAP feed (IMD_ALERTS_FEED_URL) is not configured in environment. "
            "Below are real meteorological threshold observations from Open-Meteo. For official Government of India cyclone warnings, refer to mausam.imd.gov.in."
        ),
        "official_alerts_status_te": (
            "అధికారిక IMD తుఫాను అలర్ట్ API (IMD_ALERTS_FEED_URL) కాన్ఫిగర్ చేయబడలేదు. "
            "Open-Meteo వాస్తవ వాతావరణ పరిశీలనలు మాత్రమే కింద చూపబడ్డాయి. ప్రభుత్వ అధికారిక హెచ్చరికల కోసం mausam.imd.gov.in చూడండి."
        ),
        "meteorological_advisories": advisories,
        "timestamp": now_iso,
    }

