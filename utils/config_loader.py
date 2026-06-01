import yaml
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  # loads .env into environment

def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Missing environment variable: {key}")
    return value