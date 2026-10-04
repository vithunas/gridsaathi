"""
GridSaathi Synthetic Load Generator Module.
Generates 15-minute load profiles for ~100 consumers on an Indian peri-urban LV distribution feeder.
Incorporates archetype mix, per-appliance ownership, temperature dependence, weekday/weekend/festival effects,
staggered consumer activation, coincidental diversity, and consumer-level random variation.

Labels all output data clearly as synthetic=True.
Checks evening peak transformer loading against sanity limits defined in config.
"""
import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def generate_consumer_appliances(
    consumer_id: str,
    archetype: str,
    config: Dict[str, Any],
    rng: np.random.Generator
) -> Tuple[list, dict]:
    """
    Determine appliance ownership and flexibility flags for a consumer based on archetype ownership probabilities.

    Args:
        consumer_id (str): Consumer ID (e.g. 'C001')
        archetype (str): Archetype ('household', 'shop', 'critical')
        config (Dict[str, Any]): Configuration dictionary
        rng (np.random.Generator): Random generator instance

    Returns:
        Tuple[list, dict]: (List of owned appliance names, Dict of flexibility flags)
    """
    ownership = config["feeder"]["appliance_ownership"][archetype]
    flex_cfg = config["flexibility"].get(archetype, {})
    
    owned_appliances = []
    flexibility_flags = {}
    
    for app_name, prob in ownership.items():
        if prob > 0.0 and rng.random() < prob:
            owned_appliances.append(app_name)
            if app_name in flex_cfg:
                flexibility_flags[app_name] = True
            else:
                flexibility_flags[app_name] = False
                
    # Ensure every consumer has essential lights & fans
    if "lights" not in owned_appliances:
        owned_appliances.append("lights")
        flexibility_flags["lights"] = False
    if "fans" not in owned_appliances:
        owned_appliances.append("fans")
        flexibility_flags["fans"] = False
        
    return owned_appliances, flexibility_flags


def build_appliance_load_shape(
    times: pd.DatetimeIndex,
    app_name: str,
    app_meta: dict,
    archetype: str,
    temp_c: pd.Series,
    rng: np.random.Generator
) -> pd.Series:
    """
    Build a 15-minute load profile (kW) for a single appliance owned by a consumer,
    incorporating coincidental diversity factors and consumer-specific schedule jitter.

    Args:
        times (pd.DatetimeIndex): Timestamps index
        app_name (str): Appliance name
        app_meta (dict): Appliance metadata from config.appliances
        archetype (str): Consumer archetype
        temp_c (pd.Series): Ambient temperature series (°C)
        rng (np.random.Generator): Random generator

    Returns:
        pd.Series: 15-minute power demand in kW
    """
    rated_power = app_meta["rated_power_kw_by_archetype"][archetype]
    if rated_power <= 0:
        return pd.Series(0.0, index=times)
        
    daily_hours = app_meta["daily_hours"]
    start_hour, end_hour = app_meta["evening_window"]
    
    # Add random consumer schedule jitter (shift start/end by up to +/- 1.5 hours)
    jitter_h = rng.uniform(-1.0, 1.0)
    c_start_h = max(0.0, start_hour + jitter_h)
    c_end_h = min(24.0, end_hour + jitter_h)
    
    hours = times.hour + times.minute / 60.0
    dayofweek = times.dayofweek # 0=Mon, 6=Sun
    
    base_weight = np.zeros(len(times))
    in_evening = (hours >= c_start_h) & (hours < c_end_h)
    base_weight[in_evening] = 1.0
    
    # Secondary activity hours outside primary window
    if app_name in ["lights", "tv", "general_plug_loads", "phone_charging"]:
        base_weight[(hours >= 6) & (hours < c_start_h)] = 0.20
    elif app_name in ["fans", "fridge", "freezer", "cold_storage", "medical"]:
        base_weight[~in_evening] = 0.40
    elif app_name == "water_pump":
        base_weight[(hours >= 6) & (hours < 9)] = 0.70 # Morning water fill
    elif app_name == "geyser":
        base_weight[(hours >= 5) & (hours < 8)] = 0.80 # Winter morning bath
    elif app_name == "ac":
        base_weight[(hours >= 13) & (hours < 17)] = 0.50 # Afternoon heat peak
        base_weight[(hours >= 22) | (hours < 6)] = 0.60  # Overnight sleeping
        
    # Coincidental diversity / duty-cycle factor (not all appliances run 100% simultaneously)
    coincidence_factor = 0.28
    if app_name in ["lights", "fans", "medical", "cold_storage", "clinic"]:
        coincidence_factor = 0.70
    elif app_name in ["fridge", "freezer"]:
        coincidence_factor = 0.40
    elif app_name in ["ac", "cooking_induction", "geyser", "ev_charging"]:
        coincidence_factor = 0.24
    elif app_name in ["washing_machine", "iron", "water_pump"]:
        coincidence_factor = 0.15
        
    # Temperature dependence for cooling/heating
    temp_mult = np.ones(len(times))
    if app_name in ["fans", "ac"]:
        temp_mult = np.clip(1.0 + 0.04 * (temp_c.values - 25.0), 0.5, 1.8)
    elif app_name in ["fridge", "freezer", "cold_storage"]:
        temp_mult = np.clip(1.0 + 0.02 * (temp_c.values - 28.0), 0.7, 1.4)
        
    # Day-of-week multiplier
    day_mult = np.ones(len(times))
    if archetype == "household":
        day_mult[dayofweek >= 5] = 1.10
    elif archetype == "shop":
        day_mult[dayofweek == 6] = 0.60
        
    # Timestep noise
    noise = rng.normal(1.0, 0.12, size=len(times))
    noise = np.clip(noise, 0.6, 1.4)
    
    raw_demand = base_weight * coincidence_factor * temp_mult * day_mult * noise
    
    # Scale profile so average daily energy matches rated_power * daily_hours * coincidence_factor
    target_daily_energy_kwh = rated_power * daily_hours * coincidence_factor
    n_days = (times[-1] - times[0]).total_seconds() / 86400.0 + (15 / 1440.0)
    total_target_kwh = target_daily_energy_kwh * n_days
    
    sum_raw = np.sum(raw_demand) * 0.25
    if sum_raw > 0:
        scale_factor = total_target_kwh / sum_raw
        power_kw = raw_demand * scale_factor
    else:
        power_kw = raw_demand
        
    power_kw = np.clip(power_kw, 0.0, rated_power * coincidence_factor * 1.5)
    return pd.Series(power_kw, index=times)


def generate_feeder_loads(
    config: Dict[str, Any],
    weather_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate synthetic 15-minute feeder loads for all consumers and return load & metadata DataFrames.

    Args:
        config (Dict[str, Any]): Configuration dictionary
        weather_df (pd.DataFrame): 15-minute weather DataFrame

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (load_df with consumer columns & aggregate_kw, metadata_df)
    """
    seed = config.get("seed", 42)
    rng = np.random.default_rng(seed)
    
    n_consumers = config["feeder"]["n_consumers"]
    archetype_mix = config["feeder"]["archetype_mix"]
    
    # Compute consumer counts per archetype
    n_household = int(round(n_consumers * (archetype_mix["household"] / 100.0)))
    n_shop = int(round(n_consumers * (archetype_mix["shop"] / 100.0)))
    n_critical = n_consumers - n_household - n_shop
    
    consumer_archetypes = (
        ["household"] * n_household +
        ["shop"] * n_shop +
        ["critical"] * n_critical
    )
    
    times = weather_df.index
    temp_c = weather_df["temp_c"]
    appliances_cfg = config["appliances"]
    
    load_dict = {}
    metadata_records = []
    
    for idx, arch in enumerate(consumer_archetypes, start=1):
        cid = f"C{idx:03d}"
        owned_apps, flex_flags = generate_consumer_appliances(cid, arch, config, rng)
        
        consumer_load = np.zeros(len(times))
        for app_name in owned_apps:
            if app_name in appliances_cfg:
                app_meta = appliances_cfg[app_name]
                app_load = build_appliance_load_shape(times, app_name, app_meta, arch, temp_c, rng)
                consumer_load += app_load.values
                
        load_dict[cid] = np.round(consumer_load, 3)
        
        metadata_records.append({
            "consumer_id": cid,
            "archetype": arch,
            "appliances": ",".join(owned_apps),
            "flexibility_flags": str(flex_flags),
            "synthetic": True
        })
        
    load_df = pd.DataFrame(load_dict, index=times)
    load_df["aggregate_kw"] = load_df.sum(axis=1)
    load_df["synthetic"] = True
    
    metadata_df = pd.DataFrame(metadata_records)
    
    # Sanity Check: Transformer Evening Peak Loading
    transformer_kva = config["feeder"]["transformer_kva"]
    pf = config["feeder"]["power_factor"]
    transformer_cap_kw = transformer_kva * pf
    
    start_h = config["outage_baseline"]["evening_start_hour"]
    end_h = config["outage_baseline"]["evening_end_hour"]
    
    evening_mask = (times.hour >= start_h) & (times.hour < end_h)
    evening_peak_kw = load_df.loc[evening_mask, "aggregate_kw"].max()
    evening_peak_pct = (evening_peak_kw / transformer_cap_kw) * 100.0
    
    target_bounds = config["sanity"]["evening_peak_target_pct_of_transformer"]
    logger.info(f"Generated synthetic feeder load. Evening Peak: {evening_peak_kw:.2f} kW ({evening_peak_pct:.1f}% of transformer rating {transformer_cap_kw:.1f} kW)")
    
    print(f"Generated synthetic feeder load. Evening Peak: {evening_peak_kw:.2f} kW ({evening_peak_pct:.1f}% of transformer rating {transformer_cap_kw:.1f} kW)")
    
    if not (target_bounds[0] <= evening_peak_pct <= target_bounds[1]):
        logger.warning(
            f"SANITY WARNING: Evening peak loading ({evening_peak_pct:.1f}%) is outside target bounds {target_bounds}% of transformer rating!"
        )
    else:
        logger.info(f"SANITY CHECK PASSED: Evening peak loading ({evening_peak_pct:.1f}%) is within target bounds {target_bounds}%.")
        
    return load_df, metadata_df
