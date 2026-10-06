"""Local configuration and XDG paths; no network or project writes."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

from veri_ufku.domain.contracts import ComputeBudget


@dataclass(frozen=True)
class Settings:
    locale: str = "tr"
    budget: ComputeBudget = ComputeBudget()


@dataclass(frozen=True)
class AppPaths:
    config: Path
    state: Path
    cache: Path

    @classmethod
    def discover(cls):
        home = Path.home()
        return cls(
            Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "veri_ufku",
            Path(os.environ.get("XDG_STATE_HOME", home / ".local/state")) / "veri_ufku",
            Path(os.environ.get("XDG_CACHE_HOME", home / ".cache")) / "veri_ufku",
        )

    def prepare(self):
        for path in (self.config, self.state, self.cache):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)


def load_settings(paths):
    file = paths.config / "settings.json"
    if not file.exists():
        return Settings()
    if file.stat().st_size > 16_384:
        raise ValueError("Configuration too large")
    obj = json.loads(file.read_text())
    if not isinstance(obj, dict) or set(obj) - {"locale", "budget"}:
        raise ValueError("Unsupported configuration")
    locale = obj.get("locale", "tr")
    if locale not in {"tr", "en"}:
        raise ValueError("Unsupported locale")
    return Settings(locale, ComputeBudget(**obj.get("budget", {})))
