import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    # Roblox kicks idle players after 20 minutes; stay well under that.
    interval_seconds: int = 600
    jitter_seconds: int = 60
    keys: list[str] = field(default_factory=lambda: ["space"])
    process_name: str = "RobloxPlayerBeta.exe"
    restore_focus: bool = True
    launch_place_id: int | None = None
    launch_wait_seconds: int = 30


def load_config(path: Path | None) -> Config:
    if path is None or not path.exists():
        return Config()
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    known = Config.__dataclass_fields__.keys()
    unknown = set(data) - set(known)
    if unknown:
        raise ValueError(f"Unknown config keys: {', '.join(sorted(unknown))}")
    return Config(**data)
