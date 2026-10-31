import logging
import random
import time

from . import winapi
from .config import Config

log = logging.getLogger(__name__)


def nudge_all(cfg: Config) -> int:
    """Send one anti-AFK input to every Roblox window. Returns windows touched."""
    windows = winapi.find_windows(cfg.process_name)
    if not windows:
        log.warning("No %s window found", cfg.process_name)
        return 0

    previous = winapi.foreground_window()
    for hwnd in windows:
        if not winapi.focus_window(hwnd):
            log.warning("Could not focus window %s", hwnd)
            continue
        time.sleep(0.3)
        key = random.choice(cfg.keys)
        winapi.press_key(key)
        log.info("Pressed %s in window %s", key, hwnd)

    if cfg.restore_focus and previous and previous not in windows:
        winapi.focus_window(previous)
    return len(windows)


def run(cfg: Config) -> None:
    log.info("Anti-AFK running: every ~%ss (Ctrl+C to stop)", cfg.interval_seconds)
    while True:
        nudge_all(cfg)
        delay = cfg.interval_seconds + random.uniform(-cfg.jitter_seconds, cfg.jitter_seconds)
        time.sleep(max(30, delay))
