"""
Unit tests for Phase 1 Data Layer (Weather, PV Model, Load Generator, DataLoader).
"""
import pytest
import pandas as pd
import numpy as np
from src.config import load_config
from src.data.weather import get_weather_data, generate_synthetic_weather
from src.data.pv import calculate_pv_ac_power
from src.data.load_generator import generate_feeder_loads
from src.data.loader import SyntheticLoader


def test_synthetic_weather_generation():
    """Verify synthetic weather generation outputs valid 15-minute weather data."""
    config = load_config()
    weather_df = get_weather_data(config)
    
    assert isinstance(weather_df, pd.DataFrame)
    assert not weather_df.empty
    
    required_cols = ["temp_c", "cloud_cover_pct", "ghi", "dni", "dhi", "synthetic"]
    for col in required_cols:
        assert col in weather_df.columns, f"Missing weather column: {col}"
        
    assert (weather_df["ghi"] >= 0.0).all()
    assert (weather_df["dni"] >= 0.0).all()
    assert (weather_df["dhi"] >= 0.0).all()
    assert weather_df["synthetic"].dtype == bool or isinstance(weather_df["synthetic"].iloc[0], (bool, np.bool_))


def test_pv_ac_power_calculation():
    """Verify pvlib AC power calculation produces reasonable generation profiles."""
    config = load_config()
    weather_df = get_weather_data(config)
    pv_df = calculate_pv_ac_power(weather_df, config)
    
    assert isinstance(pv_df, pd.DataFrame)
    assert "solar_ac_kw" in pv_df.columns
    assert "synthetic" in pv_df.columns
    
    kwp = config["solar"]["kwp"]
    assert (pv_df["solar_ac_kw"] >= 0.0).all()
    assert (pv_df["solar_ac_kw"] <= kwp).all(), f"PV AC power exceeds installed capacity {kwp} kWp"
    
    # Peak solar should occur during daytime hours (9 AM - 4 PM)
    daytime_mask = (pv_df.index.hour >= 9) & (pv_df.index.hour <= 16)
    nighttime_mask = (pv_df.index.hour >= 20) | (pv_df.index.hour <= 4)
    
    assert pv_df.loc[daytime_mask, "solar_ac_kw"].max() > 0.0
    assert pv_df.loc[nighttime_mask, "solar_ac_kw"].max() == 0.0


def test_synthetic_load_generator_and_sanity():
    """Verify synthetic load generator produces 100 consumer profiles and metadata."""
    config = load_config()
    weather_df = get_weather_data(config)
    load_df, meta_df = generate_feeder_loads(config, weather_df)
    
    assert isinstance(load_df, pd.DataFrame)
    assert isinstance(meta_df, pd.DataFrame)
    
    # Verify 100 consumer columns C001..C100
    assert len(meta_df) == 100
    consumer_cols = [f"C{i:03d}" for i in range(1, 101)]
    for col in consumer_cols:
        assert col in load_df.columns, f"Missing consumer column: {col}"
        
    assert "aggregate_kw" in load_df.columns
    assert "synthetic" in load_df.columns
    assert (load_df["aggregate_kw"] > 0.0).all()
    
    # Check archetype mix breakdown (80 household, 15 shop, 5 critical)
    archetype_counts = meta_df["archetype"].value_counts()
    assert archetype_counts["household"] == 80
    assert archetype_counts["shop"] == 15
    assert archetype_counts["critical"] == 5
    
    # Check metadata fields
    assert "consumer_id" in meta_df.columns
    assert "appliances" in meta_df.columns
    assert "flexibility_flags" in meta_df.columns
    assert (meta_df["synthetic"] == True).all()


def test_synthetic_loader_interface():
    """Verify swappable SyntheticLoader interface loads all data cleanly."""
    config = load_config()
    loader = SyntheticLoader(config)
    data = loader.load_all()
    
    assert "weather" in data
    assert "pv" in data
    assert "load" in data
    assert "metadata" in data
    assert "net_load_kw" in data
    
    assert len(data["load"]) == len(data["pv"])
    assert len(data["load"]) == len(data["weather"])
