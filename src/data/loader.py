"""
GridSaathi Data Loader Abstraction.
Defines swappable DataLoader interface (SyntheticLoader vs CSVLoader).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from pathlib import Path
import pandas as pd

from src.data.weather import get_weather_data
from src.data.pv import calculate_pv_ac_power
from src.data.load_generator import generate_feeder_loads

PROCESSED_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"


class DataLoader(ABC):
    """Abstract Base Class for swappable GridSaathi data loaders."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def load_weather(self) -> pd.DataFrame:
        """Load 15-minute weather data (temp, cloud cover, GHI, DNI, DHI)."""
        pass

    @abstractmethod
    def load_pv(self, weather_df: pd.DataFrame = None) -> pd.DataFrame:
        """Load 15-minute AC solar power generation profile (kW)."""
        pass

    @abstractmethod
    def load_consumer_loads(self, weather_df: pd.DataFrame = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load 15-minute consumer loads DataFrame and metadata DataFrame."""
        pass

    @abstractmethod
    def load_all(self) -> Dict[str, Any]:
        """Load all datasets together and return a dictionary of DataFrames."""
        pass


class SyntheticLoader(DataLoader):
    """DataLoader implementation generating synthetic profiles based on config parameters."""

    def load_weather(self) -> pd.DataFrame:
        """Fetch/generate 15-minute weather data."""
        return get_weather_data(self.config)

    def load_pv(self, weather_df: pd.DataFrame = None) -> pd.DataFrame:
        """Calculate 15-minute AC solar power generation."""
        if weather_df is None:
            weather_df = self.load_weather()
        return calculate_pv_ac_power(weather_df, self.config)

    def load_consumer_loads(self, weather_df: pd.DataFrame = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Generate 15-minute consumer loads and consumer metadata."""
        if weather_df is None:
            weather_df = self.load_weather()
        return generate_feeder_loads(self.config, weather_df)

    def load_all(self) -> Dict[str, Any]:
        """Generate and combine all dataset profiles."""
        weather_df = self.load_weather()
        pv_df = self.load_pv(weather_df)
        load_df, meta_df = self.load_consumer_loads(weather_df)
        
        # Calculate net load: aggregate demand - PV AC generation
        net_load_kw = load_df["aggregate_kw"] - pv_df["solar_ac_kw"]
        
        return {
            "weather": weather_df,
            "pv": pv_df,
            "load": load_df,
            "metadata": meta_df,
            "net_load_kw": net_load_kw
        }


class CSVLoader(DataLoader):
    """Stub DataLoader implementation for reading pre-saved CSV data files."""

    def __init__(self, config: Dict[str, Any], data_dir: Path = PROCESSED_DATA_DIR):
        super().__init__(config)
        self.data_dir = data_dir

    def load_weather(self) -> pd.DataFrame:
        weather_file = self.data_dir / "weather.csv"
        if not weather_file.exists():
            raise FileNotFoundError(f"Processed weather CSV not found at {weather_file}")
        return pd.read_csv(weather_file, parse_dates=["time"], index_col="time")

    def load_pv(self, weather_df: pd.DataFrame = None) -> pd.DataFrame:
        pv_file = self.data_dir / "pv.csv"
        if not pv_file.exists():
            raise FileNotFoundError(f"Processed PV CSV not found at {pv_file}")
        return pd.read_csv(pv_file, parse_dates=["time"], index_col="time")

    def load_consumer_loads(self, weather_df: pd.DataFrame = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        load_file = self.data_dir / "load.csv"
        meta_file = self.data_dir / "consumer_metadata.csv"
        if not load_file.exists() or not meta_file.exists():
            raise FileNotFoundError(f"Processed load or metadata CSV not found at {self.data_dir}")
        load_df = pd.read_csv(load_file, parse_dates=["time"], index_col="time")
        meta_df = pd.read_csv(meta_file)
        return load_df, meta_df

    def load_all(self) -> Dict[str, Any]:
        weather_df = self.load_weather()
        pv_df = self.load_pv(weather_df)
        load_df, meta_df = self.load_consumer_loads(weather_df)
        net_load_kw = load_df["aggregate_kw"] - pv_df["solar_ac_kw"]
        return {
            "weather": weather_df,
            "pv": pv_df,
            "load": load_df,
            "metadata": meta_df,
            "net_load_kw": net_load_kw
        }
