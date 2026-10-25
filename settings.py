import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_camera_config():
    config_path = BASE_DIR / "config" / "camera.json"

    with config_path.open(encoding="utf-8") as file:
        return json.load(file)