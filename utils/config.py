"""Application configuration persistence."""

import json
import os
from typing import List

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(data: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def load_recent_directories() -> List[str]:
    cfg = load_config()
    return cfg.get("recent_directories", [])


def save_recent_directories(dirs: List[str]) -> None:
    cfg = load_config()
    cfg["recent_directories"] = dirs
    save_config(cfg)


def load_history() -> List[dict]:
    cfg = load_config()
    return cfg.get("history", [])


def save_history_entry(entry: dict) -> None:
    cfg = load_config()
    history = cfg.get("history", [])
    history.insert(0, entry)
    cfg["history"] = history[:20]  # keep last 20
    save_config(cfg)


def load_trusted_directories() -> List[str]:
    cfg = load_config()
    return cfg.get("trusted_directories", [])


def save_trusted_directories(dirs: List[str]) -> None:
    cfg = load_config()
    cfg["trusted_directories"] = dirs
    save_config(cfg)


def load_window_geometry() -> dict:
    cfg = load_config()
    return cfg.get("window", {})


def save_window_geometry(geo: dict) -> None:
    cfg = load_config()
    cfg["window"] = geo
    save_config(cfg)
