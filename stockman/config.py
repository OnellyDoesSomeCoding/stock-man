"""Load config.yaml (settings) and .env (secrets)."""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

ENV_KEYS = ("MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "MT5_PATH")


def load_config(path: Path | None = None) -> dict:
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict) or "config_version" not in cfg:
        raise ValueError("config.yaml must contain a config_version")
    return cfg


def load_env() -> dict[str, str]:
    load_dotenv(ROOT / ".env")
    return {k: os.getenv(k, "").strip() for k in ENV_KEYS}
