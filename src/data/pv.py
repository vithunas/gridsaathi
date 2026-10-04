"""
GridSaathi PV Solar Generation Model.
Calculates AC solar power generation (kW) using pvlib based on irradiance, solar geometry,
tilt, azimuth, system losses, and capacity specified in config.
"""
from typing import Dict, Any
import pandas as pd
import numpy as np
import pvlib
from pvlib.location import Location

def calculate_pv_ac_power(weather_df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    """
    Calculate 15-minute AC solar power generation in kW for specified solar capacity.

    Args:
        weather_df (pd.DataFrame): 15-minute weather DataFrame with ghi, dni, dhi.
        config (Dict[str, Any]): Configuration dictionary.

    Returns:
        pd.DataFrame: DataFrame with solar_ac_kw and synthetic columns.
    """
    lat = config["location"]["lat"]
    lon = config["location"]["lon"]
    tz = config["location"]["timezone"]
    
    solar_cfg = config["solar"]
    kwp = solar_cfg["kwp"]
    tilt = solar_cfg["tilt"]
    azimuth = solar_cfg["azimuth"]
    losses = solar_cfg["losses"]
    
    if weather_df.index.tz is None:
        weather_df.index = weather_df.index.tz_localize(tz)
    
    times = weather_df.index
    loc = Location(lat, lon, tz=tz)
    solpos = loc.get_solarposition(times)
    
    poa_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        solar_zenith=solpos["zenith"],
        solar_azimuth=solpos["azimuth"],
        ghi=weather_df["ghi"],
        dni=weather_df["dni"],
        dhi=weather_df["dhi"]
    )
    
    # Calculate DC/AC output in kW: POA global (W/m2) / 1000 * STC Rating (kWp) * (1 - losses)
    poa_global = poa_irradiance["poa_global"].fillna(0.0)
    ac_power_kw = (poa_global / 1000.0) * kwp * (1.0 - losses)
    ac_power_kw = np.clip(ac_power_kw, 0.0, None)
    
    res_df = pd.DataFrame({
        "solar_ac_kw": np.round(ac_power_kw, 3),
        "synthetic": weather_df.get("synthetic", True)
    }, index=weather_df.index)
    
    return res_df
