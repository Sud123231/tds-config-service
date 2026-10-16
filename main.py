
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_layer(values):
    normalized = {}

    for name, value in values.items():
        if value is None:
            continue

        if name == "NUM_WORKERS":
            normalized["workers"] = value
        elif name.startswith("APP_") and name != "APP_ENV":
            key = name[4:].lower()
            normalized[key] = value

    return normalized


def coerce_value(key, value):
    if key in ("port", "workers"):
        try:
            return int(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail=f"{key} must be an integer",
            )

    if key == "debug":
        return str(value).lower() in {
            "true", "1", "yes", "on"
        }

    return str(value)


@app.get("/effective-config")
def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    environment = os.environ.get("APP_ENV", "development")
    yaml_path = BASE_DIR / f"config.{environment}.yaml"

    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}

        config.update(yaml_config)

    env_config = normalize_layer(
        dotenv_values(BASE_DIR / ".env")
    )
    config.update(env_config)

    os_config = normalize_layer(os.environ)
    config.update(os_config)

    for override in set:
        key, separator, value = override.partition("=")

        if not separator or not key.strip():
            raise HTTPException(
                status_code=400,
                detail="Each set parameter must be key=value",
            )

        config[key.strip()] = value

    config = {
        key: coerce_value(key, value)
        for key, value in config.items()
    }

    config["api_key"] = "****"

    return config
