"""
Unit tests for Phase 0 skeleton and config validation.
"""
import pytest
import yaml
from pathlib import Path
from src.config import load_config, UniqueKeyLoader

def test_config_loading():
    """Verify that config.yaml exists, loads cleanly, and contains all required sections."""
    config = load_config()
    
    required_keys = [
        "seed",
        "location",
        "feeder",
        "simulation",
        "sanity",
        "mpc",
        "battery",
        "solar",
        "outage_baseline",
        "tiers",
        "appliances",
        "flexibility",
        "response_rates",
        "tariffs",
        "economics",
        "fairness"
    ]
    
    for key in required_keys:
        assert key in config, f"Missing required config key: {key}"
    
    # Check location settings
    assert config["location"]["timezone"] == "Asia/Kolkata"
    assert abs(config["solar"]["tilt"] - config["location"]["lat"]) < 1.0
    assert config["sanity"]["evening_peak_target_pct_of_transformer"] == [60, 100]

def test_duplicate_key_rejection(tmp_path):
    """Verify that UniqueKeyLoader raises ValueError on duplicate keys in YAML."""
    duplicate_yaml = tmp_path / "duplicate.yaml"
    duplicate_yaml.write_text("""
section:
  key1: 10
  key1: 20
""")
    with pytest.raises(ValueError, match="Duplicate key 'key1'"):
        with open(duplicate_yaml, "r", encoding="utf-8") as f:
            yaml.load(f, Loader=UniqueKeyLoader)

def test_four_tiers_and_appliances_mapping():
    """
    Verify the four-tier appliance structure:
    - tier0_life_critical
    - tier1_essential
    - tier2_flexible
    - tier3_deferrable
    - essential_load_cap_kw_per_household
    Ensure every appliance listed in the appliances section belongs to EXACTLY ONE tier
    and that appliances[*].tier matches the tiers lists.
    """
    config = load_config()
    tiers_cfg = config["tiers"]
    appliances_cfg = config["appliances"]
    
    tier_keys = [
        "tier0_life_critical",
        "tier1_essential",
        "tier2_flexible",
        "tier3_deferrable"
    ]
    
    for tk in tier_keys:
        assert tk in tiers_cfg, f"Missing tier key: {tk}"
        assert isinstance(tiers_cfg[tk], list), f"{tk} must be a list of appliances"
    
    assert "essential_load_cap_kw_per_household" in tiers_cfg
    assert tiers_cfg["essential_load_cap_kw_per_household"] == 0.3
    
    # Build tier map: appliance -> tier
    appliance_to_tier = {}
    for tk in tier_keys:
        for app in tiers_cfg[tk]:
            assert app not in appliance_to_tier, f"Appliance '{app}' appears in multiple tiers!"
            appliance_to_tier[app] = tk
            
    # Verify every appliance in appliances section is present in exactly one tier
    for app_name, app_meta in appliances_cfg.items():
        assert app_name in appliance_to_tier, f"Appliance '{app_name}' not assigned to any tier in tiers"
        assert app_meta["tier"] == appliance_to_tier[app_name], (
            f"Tier mismatch for '{app_name}': appliances section specifies '{app_meta['tier']}' "
            f"but tiers section defines '{appliance_to_tier[app_name]}'"
        )

def test_appliance_ownership_all_appliances():
    """Verify appliance ownership fractions exist for ALL appliances per archetype."""
    config = load_config()
    ownership = config["feeder"]["appliance_ownership"]
    appliances_cfg = config["appliances"]
    
    archetypes = ["household", "shop", "critical"]
    for arch in archetypes:
        assert arch in ownership, f"Missing archetype '{arch}' in appliance_ownership"
        arch_ownership = ownership[arch]
        for app_name in appliances_cfg.keys():
            assert app_name in arch_ownership, (
                f"Missing ownership fraction for appliance '{app_name}' in archetype '{arch}'"
            )
            val = arch_ownership[app_name]
            assert 0.0 <= val <= 1.0, f"Invalid ownership fraction {val} for '{app_name}' in archetype '{arch}'"

def test_archetype_aware_appliance_power():
    """Verify appliances section provides rated_power_kw_by_archetype for all archetypes."""
    config = load_config()
    appliances_cfg = config["appliances"]
    
    archetypes = ["household", "shop", "critical"]
    for app_name, app_meta in appliances_cfg.items():
        assert "rated_power_kw_by_archetype" in app_meta, f"Missing rated_power_kw_by_archetype for '{app_name}'"
        power_map = app_meta["rated_power_kw_by_archetype"]
        for arch in archetypes:
            assert arch in power_map, f"Missing rated power for archetype '{arch}' in appliance '{app_name}'"
            assert power_map[arch] >= 0.0

def test_flexibility_feasibility():
    """
    Verify that for every flexibility entry across archetypes:
    capacity_kwh <= power_kw * (max_deferral_min / 60)
    """
    config = load_config()
    flex_cfg = config["flexibility"]
    
    # Ensure old flat keys are deleted
    assert "freezer" not in flex_cfg, "Old flat key 'freezer' must be deleted from flexibility"
    assert "water_pump" not in flex_cfg, "Old flat key 'water_pump' must be deleted from flexibility"
    assert "geyser" not in flex_cfg, "Old flat key 'geyser' must be deleted from flexibility"
    
    archetypes = ["household", "shop", "critical"]
    for arch in archetypes:
        assert arch in flex_cfg, f"Missing archetype '{arch}' in flexibility config"
        arch_flex = flex_cfg[arch]
        for app_name, params in arch_flex.items():
            cap = params["capacity_kwh"]
            power = params["power_kw"]
            max_def = params["max_deferral_min"]
            max_energy_possible = power * (max_def / 60.0)
            
            assert cap <= max_energy_possible + 1e-6, (
                f"Infeasible flexibility for {arch}.{app_name}: "
                f"capacity_kwh ({cap}) > max energy possible ({max_energy_possible:.2f} kWh)"
            )
