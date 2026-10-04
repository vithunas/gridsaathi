"""
GridSaathi Weather Data Loader Module.
Fetches solar irradiance, temperature, and cloud cover from Open-Meteo API.
If offline or API fails, falls back to pvlib clear-sky synthetic weather generator.
Caches raw data in data/raw.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
import pvlib
from pvlib.location import Location
import requests

logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"

def fetch_open_meteo_weather(
    lat: float,
    lon: float,
    start_date: str,
    n_days: int,
    timezone: str = "Asia/Kolkata"
) -> Tuple[pd.DataFrame, bool]:
    """
    Fetch weather data from Open-Meteo Historical / Archive API.

    Args:
        lat (float): Latitude
        lon (float): Longitude
        start_date (str): Start date string "YYYY-MM-DD"
        n_days (int): Number of days
        timezone (str): Timezone string

    Returns:
        Tuple[pd.DataFrame, bool]: (DataFrame with hourly weather data, is_synthetic flag)
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = RAW_DATA_DIR / f"weather_openmeteo_{lat:.2f}_{lon:.2f}_{start_date}_{n_days}d.csv"

    if cache_file.exists():
        logger.info(f"WEATHER SOURCE USED: Open-Meteo API download (Cached at: {cache_file})")
        print(f"WEATHER SOURCE USED: Open-Meteo API download (Cached at: {cache_file})")
        df = pd.read_csv(cache_file, parse_dates=["time"])
        df.set_index("time", inplace=True)
        return df, False

    end_date = (pd.to_datetime(start_date) + pd.Timedelta(days=n_days - 1)).strftime("%Y-%m-%d")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,cloud_cover,shortwave_radiation,direct_normal_irradiance,diffuse_radiation",
        "timezone": timezone
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            hourly = data.get("hourly", {})
            df = pd.DataFrame({
                "time": pd.to_datetime(hourly["time"]),
                "temp_c": hourly["temperature_2m"],
                "cloud_cover_pct": hourly["cloud_cover"],
                "ghi": hourly["shortwave_radiation"],
                "dni": hourly["direct_normal_irradiance"],
                "dhi": hourly["diffuse_radiation"],
                "synthetic": False
            })
            df.set_index("time", inplace=True)
            df.to_csv(cache_file)
            logger.info(f"WEATHER SOURCE USED: Open-Meteo API download (Cached fresh data to: {cache_file})")
            print(f"WEATHER SOURCE USED: Open-Meteo API download (Cached fresh data to: {cache_file})")
            return df, False
        else:
            logger.warning(f"Open-Meteo API returned status code {response.status_code}. Falling back to synthetic weather.")
            print(f"Open-Meteo API status code {response.status_code}. Falling back to synthetic weather.")
    except Exception as e:
        logger.warning(f"Open-Meteo API fetch failed ({e}). Falling back to synthetic weather.")
        print(f"Open-Meteo API fetch failed ({e}). Falling back to synthetic weather.")

    return generate_synthetic_weather(lat, lon, start_date, n_days, timezone)


def generate_synthetic_weather(
    lat: float,
    lon: float,
    start_date: str,
    n_days: int,
    timezone: str = "Asia/Kolkata",
    seed: int = 42
) -> Tuple[pd.DataFrame, bool]:
    """
    Generate synthetic clear-sky weather with cloud noise using pvlib as a fallback.
    """
    logger.info("WEATHER SOURCE USED: Synthetic pvlib clear-sky fallback generator")
    print("WEATHER SOURCE USED: Synthetic pvlib clear-sky fallback generator")
    np.random.seed(seed)
    
    times = pd.date_range(
        start=start_date,
        periods=n_days * 24,
        freq="1h",
        tz=timezone
    )
    
    loc = Location(lat, lon, tz=timezone)
    cs = loc.get_clearsky(times, model="ineichen")
    
    # Generate realistic cloud cover noise with temporal autocorrelation
    raw_cloud = np.random.normal(0.2, 0.15, size=len(times))
    cloud_cover = np.clip(pd.Series(raw_cloud).rolling(window=3, min_periods=1).mean(), 0.0, 0.9)
    
    # Attenuate solar irradiance by cloud cover
    ghi = cs["ghi"] * (1.0 - 0.75 * (cloud_cover ** 2))
    dni = cs["dni"] * (1.0 - cloud_cover)
    dhi = cs["dhi"] * (1.0 - 0.2 * cloud_cover)
    
    # Temperature profile (diurnal cycle: peak ~14:00, min ~05:00)
    hour = times.hour
    temp_base = 32.0 + 6.0 * np.sin((hour - 9) * np.pi / 12) + np.random.normal(0, 1.0, len(times))
    
    df = pd.DataFrame({
        "temp_c": np.round(temp_base, 2),
        "cloud_cover_pct": np.round(cloud_cover * 100, 1),
        "ghi": np.maximum(0, np.round(ghi, 2)),
        "dni": np.maximum(0, np.round(dni, 2)),
        "dhi": np.maximum(0, np.round(dhi, 2)),
        "synthetic": True
    }, index=times)
    
    df.index.name = "time"
    return df, True


def get_weather_data(config: Dict[str, Any]) -> pd.DataFrame:
    """
    Main weather entry point: fetch or generate weather data and resample to 15-minute intervals.

    Args:
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        pd.DataFrame: 15-minute weather data with temp_c, cloud_cover_pct, ghi, dni, dhi, synthetic.
    """
    lat = config["location"]["lat"]
    lon = config["location"]["lon"]
    tz = config["location"]["timezone"]
    
    # Determine season & simulation duration from config rules
    season = config["simulation"].get("season", "summer")
    start_date = config["simulation"]["season_start_dates"].get(season, "2024-05-01")
    
    dev_mode = config["simulation"]["dev_mode"]["enabled"]
    n_days = config["simulation"]["dev_mode"]["dev_n_days"] if dev_mode else config["simulation"]["dev_mode"]["full_n_days"]
    
    df_hourly, is_synth = fetch_open_meteo_weather(lat, lon, start_date, n_days, tz)
    
    step_min = config["simulation"]["step_minutes"]
    numeric_cols = ["temp_c", "cloud_cover_pct", "ghi", "dni", "dhi"]
    df_numeric = df_hourly[numeric_cols].resample(f"{step_min}min").interpolate(method="linear")
    df_15m = df_numeric
    df_15m["synthetic"] = is_synth
    
    if df_15m.index.tz is None:
        df_15m.index = df_15m.index.tz_localize(tz)
        
    return df_15m
