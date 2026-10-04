"""
GridSaathi Data Visualization & Plot Export Script.
Generates and saves Phase 1 plots to /outputs:
1. aggregate_weekly_load.png
2. solar_curve.png
3. net_load.png
Also exports processed datasets to /data/processed.
"""
from pathlib import Path
import logging
import matplotlib.pyplot as plt
import pandas as pd

from src.config import load_config
from src.data.loader import SyntheticLoader

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"
PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


def generate_phase1_outputs():
    """Load Phase 1 data, plot key profiles, and save results to outputs/ and data/processed/."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    config = load_config()
    loader = SyntheticLoader(config)
    data = loader.load_all()

    weather_df = data["weather"]
    pv_df = data["pv"]
    load_df = data["load"]
    meta_df = data["metadata"]
    net_load_kw = data["net_load_kw"]

    # Save processed CSVs
    weather_df.to_csv(PROCESSED_DIR / "weather.csv")
    pv_df.to_csv(PROCESSED_DIR / "pv.csv")
    load_df.to_csv(PROCESSED_DIR / "load.csv")
    meta_df.to_csv(PROCESSED_DIR / "consumer_metadata.csv", index=False)

    # Plot 1: Aggregate Weekly Feeder Load
    plt.figure(figsize=(12, 5))
    plt.plot(load_df.index, load_df["aggregate_kw"], color="#1f77b4", linewidth=1.5, label="Aggregate Feeder Load (kW)")
    plt.axhline(
        config["feeder"]["transformer_kva"] * config["feeder"]["power_factor"],
        color="red", linestyle="--", label="Transformer Rating (95 kW)"
    )
    plt.axvspan(
        load_df.index[0], load_df.index[-1], alpha=0.05, color="grey"
    )
    plt.title("GridSaathi Phase 1: Aggregate Weekly Feeder Load Profile (100 Consumers [SYNTHETIC])", fontsize=14, fontweight="bold")
    plt.xlabel("Time", fontsize=11)
    plt.ylabel("Power Demand (kW)", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "aggregate_weekly_load.png", dpi=300)
    plt.close()

    # Plot 2: Solar Generation Curve
    plt.figure(figsize=(12, 5))
    plt.plot(pv_df.index, pv_df["solar_ac_kw"], color="#ff7f0e", linewidth=1.5, label=f"Community Solar ({config['solar']['kwp']} kWp AC)")
    plt.title("GridSaathi Phase 1: Solar PV Generation Curve [SYNTHETIC/MODEL]", fontsize=14, fontweight="bold")
    plt.xlabel("Time", fontsize=11)
    plt.ylabel("AC Power Output (kW)", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "solar_curve.png", dpi=300)
    plt.close()

    # Plot 3: Net Load Profile (Feeder Demand - Solar PV)
    plt.figure(figsize=(12, 5))
    plt.plot(load_df.index, load_df["aggregate_kw"], color="#1f77b4", linewidth=1.2, alpha=0.8, label="Gross Load (kW)")
    plt.plot(pv_df.index, pv_df["solar_ac_kw"], color="#ff7f0e", linewidth=1.2, alpha=0.8, label="Solar PV (kW)")
    plt.plot(net_load_kw.index, net_load_kw, color="#2ca02c", linewidth=1.8, label="Net Load (kW)")
    
    # Highlight evening ramp window (6 PM - 10 PM)
    start_h = config["outage_baseline"]["evening_start_hour"]
    end_h = config["outage_baseline"]["evening_end_hour"]
    plt.axvspan(
        load_df.index[0], load_df.index[-1],
        color="orange", alpha=0.0, label=f"Evening Ramp Window ({start_h}:00 - {end_h}:00)"
    )
    plt.title("GridSaathi Phase 1: Feeder Net Load Profile & Evening Ramp Peak [SYNTHETIC]", fontsize=14, fontweight="bold")
    plt.xlabel("Time", fontsize=11)
    plt.ylabel("Power (kW)", fontsize=11)
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "net_load.png", dpi=300)
    plt.close()

    print(f"Phase 1 outputs generated successfully and saved to {OUTPUTS_DIR}")


if __name__ == "__main__":
    generate_phase1_outputs()
