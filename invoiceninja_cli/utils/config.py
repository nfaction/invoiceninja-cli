"""Configuration management for invoiceninja-cli."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "invoiceninja-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"

_ENV_URL = "INVOICENINJA_URL"
_ENV_TOKEN = "INVOICENINJA_TOKEN"


def load_config() -> dict:
    """Load configuration from disk. Returns empty dict if not found."""
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_config(config: dict) -> None:
    """Persist configuration to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w") as fh:
        json.dump(config, fh, indent=2)
    # Restrict permissions so the token is not world-readable
    CONFIG_FILE.chmod(0o600)


def get_config() -> dict:
    """Return effective configuration, merging file config with env vars.

    Environment variables take precedence over the config file.
    """
    config = load_config()

    env_url = os.environ.get(_ENV_URL)
    env_token = os.environ.get(_ENV_TOKEN)

    if env_url:
        config["url"] = env_url
    if env_token:
        config["token"] = env_token

    return config


def require_config() -> dict:
    """Return effective config or raise a helpful error if incomplete."""
    config = get_config()
    missing = []
    if not config.get("url"):
        missing.append("url (set INVOICENINJA_URL or run 'invoiceninja-cli configure')")
    if not config.get("token"):
        missing.append("token (set INVOICENINJA_TOKEN or run 'invoiceninja-cli configure')")
    if missing:
        raise RuntimeError(
            "Missing required configuration:\n  " + "\n  ".join(missing)
        )
    return config
