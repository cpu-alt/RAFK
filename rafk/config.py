import logging
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from . import actions, winapi

log = logging.getLogger(__name__)

# Roblox disconnects after 20 minutes without input.
ROBLOX_KICK_SECONDS = 1200

# Keys from the 0.1 config format, mapped to their replacement.
LEGACY_KEYS = {"keys": "actions", "process_name": "process_names", "launch_place_id": "place_id"}


@dataclass
class Config:
    interval_seconds: int = 600
    jitter_seconds: int = 60
    actions: list[str] = field(default_factory=lambda: ["jump", "camera"])
    user_idle_seconds: int = 30
    force_after_seconds: int = 1080
    process_names: list[str] = field(default_factory=lambda: ["RobloxPlayerBeta.exe"])
    restore_focus: bool = True
    restore_minimized: bool = True
    place_id: int | None = None
    auto_rejoin: bool = True
    rejoin_after_seconds: int = 30
    hang_timeout_seconds: int = 90
    detect_disconnect: bool = False
    # 277/279: connection lost, 267: kicked. 285 (you left) is deliberately absent.
    disconnect_patterns: list[str] = field(
        default_factory=lambda: [
            "Lost connection with reason",
            "Sending disconnect with reason: 277",
            "Sending disconnect with reason: 279",
            "Sending disconnect with reason: 267",
        ]
    )
    launch_wait_seconds: int = 90
    prevent_sleep: bool = True
    pause_hotkey: str = "F8"
    discord_webhook: str = ""
    log_file: str = ""

    def validate(self) -> None:
        for spec in self.actions:
            actions.resolve(spec)
        if not self.actions:
            raise ValueError("actions must not be empty")
        if self.jitter_seconds < 0 or self.interval_seconds <= self.jitter_seconds:
            raise ValueError("interval_seconds must be greater than jitter_seconds (>= 0)")
        if self.force_after_seconds >= ROBLOX_KICK_SECONDS:
            raise ValueError(f"force_after_seconds must be < {ROBLOX_KICK_SECONDS} (Roblox kick)")
        if self.interval_seconds + self.jitter_seconds > self.force_after_seconds:
            raise ValueError("interval_seconds + jitter_seconds must be <= force_after_seconds")
        if self.pause_hotkey:
            winapi.vk_from_name(self.pause_hotkey)


def _migrate(data: dict) -> dict:
    data = dict(data)
    for old, new in LEGACY_KEYS.items():
        if old not in data:
            continue
        value = data.pop(old)
        log.warning("Config : '%s' est obsolète, utilise '%s'", old, new)
        if new in data:
            continue
        if old == "keys":
            value = [f"key:{k}" for k in value]
        elif old == "process_name":
            value = [value]
        data[new] = value
    return data


def from_dict(data: dict) -> Config:
    data = _migrate(data)
    known = {f.name for f in fields(Config)}
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(sorted(unknown))}")
    cfg = Config(**data)
    cfg.validate()
    return cfg


def load_config(path: Path) -> Config:
    if not path.exists():
        log.info("Pas de %s, configuration par défaut", path)
        return from_dict({})
    return from_dict(tomllib.loads(path.read_text(encoding="utf-8")))
