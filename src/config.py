"""
GridSaathi Config Helper Module.
Loads project configuration from config/config.yaml with duplicate key detection.
"""
from pathlib import Path
import yaml
from yaml.loader import SafeLoader
from typing import Dict, Any

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "config.yaml"

class UniqueKeyLoader(SafeLoader):
    """YAML SafeLoader that raises ValueError on duplicate keys in mappings."""
    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in keys:
                raise ValueError(f"Duplicate key '{key}' found in YAML configuration at line {key_node.start_mark.line + 1}.")
            keys.add(key)
        return super().construct_mapping(node, deep=deep)

def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """
    Load YAML configuration file, enforcing unique keys.

    Args:
        config_path (Path): Path to the config file.

    Returns:
        Dict[str, Any]: Configuration dictionary.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If duplicate keys exist in the configuration.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=UniqueKeyLoader)
    
    return config
