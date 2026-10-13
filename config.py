"""YAML config loader. Optional pydantic validation, falls back to dict."""
from __future__ import annotations
from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path = "config.yaml") -> dict:
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    try:
        from pydantic import BaseModel, Field

        class Config(BaseModel):
            limits: dict[str, Any] = Field(default_factory=dict)
            kill_switch: dict[str, Any] = Field(default_factory=dict)
            alerts: dict[str, Any] = Field(default_factory=dict)
            broker: dict[str, Any] = Field(default_factory=dict)
            storage: dict[str, Any] = Field(default_factory=dict)

        return Config(**raw).model_dump()
    except ImportError:
        return raw
