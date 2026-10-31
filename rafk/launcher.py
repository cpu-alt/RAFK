import logging
import os
import time

from . import winapi

log = logging.getLogger(__name__)


def launch_place(place_id: int) -> None:
    """Open a Roblox place through the registered roblox:// protocol handler."""
    log.info("Launching Roblox place %s", place_id)
    os.startfile(f"roblox://placeId={place_id}")


def wait_for_window(process_name: str, timeout: float) -> list[int]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        windows = winapi.find_windows(process_name)
        if windows:
            return windows
        time.sleep(1)
    return []
