"""Anti-AFK actions. Each one leaves the character roughly where it was."""
import time
from collections.abc import Callable

from . import winapi

Action = Callable[[], None]


def _press(key: str, hold: float = 0.1) -> Action:
    return lambda: winapi.press_key(key, hold)


def _sequence(*steps: tuple[str, float]) -> Action:
    def run() -> None:
        for key, hold in steps:
            winapi.press_key(key, hold)
            time.sleep(0.15)

    return run


ACTIONS: dict[str, Action] = {
    "jump": _press("space"),
    "walk": _sequence(("w", 0.25), ("s", 0.25)),
    "strafe": _sequence(("a", 0.25), ("d", 0.25)),
    "camera": _sequence(("left", 0.3), ("right", 0.3)),
    "zoom": _sequence(("i", 0.2), ("o", 0.2)),
}


def resolve(spec: str) -> Action:
    """`spec` is a named action ("jump") or a raw key ("key:space")."""
    if spec.startswith("key:"):
        key = spec[4:]
        if key not in winapi.SCANCODES:
            raise ValueError(f"Unknown key {key!r} (known: {', '.join(winapi.SCANCODES)})")
        return _press(key)
    if spec not in ACTIONS:
        raise ValueError(f"Unknown action {spec!r} (known: {', '.join(ACTIONS)}, key:<name>)")
    return ACTIONS[spec]
