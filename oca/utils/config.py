import yaml
from pathlib import Path
from typing import Optional, Any

def find_config_file() -> Optional[Path]:
    """Find the .oca/config.yaml file by searching upwards from the current directory."""
    current_dir = Path.cwd()
    while current_dir != current_dir.parent:
        config_path = current_dir / ".oca" / "config.yaml"
        if config_path.exists():
            return config_path
        current_dir = current_dir.parent
    return None

def load_config() -> dict[str, Any]:
    """Load the OCA configuration from the .oca/config.yaml file."""
    config_file = find_config_file()
    if not config_file:
        return {}

    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, IOError):
        return {}

def get_config_value(key: str, default: Optional[any] = None) -> Any:
    """Get a specific value from the configuration."""
    config = load_config()
    keys = key.split('.')
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    return value if value is not None else default
