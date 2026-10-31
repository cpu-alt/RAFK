"""Finding, launching and killing the Roblox client."""
import logging
import os
import time
from dataclasses import dataclass

from . import winapi

log = logging.getLogger(__name__)

GAME_WINDOW_CLASS = "WINDOWSCLIENT"


@dataclass(frozen=True)
class GameWindow:
    hwnd: int
    pid: int
    title: str


def _matches(name: str, process_names: list[str]) -> bool:
    return name.lower() in {p.lower() for p in process_names}


def roblox_pids(process_names: list[str]) -> set[int]:
    return {pid for pid, exe in winapi.list_processes() if _matches(exe, process_names)}


def find_game_windows(process_names: list[str]) -> list[GameWindow]:
    """Visible game windows of the Roblox client (tray/IME windows excluded)."""
    pids = roblox_pids(process_names)
    if not pids:
        return []
    windows = []
    for hwnd in winapi.enum_windows():
        if not winapi.is_visible(hwnd):
            continue
        pid = winapi.window_pid(hwnd)
        if pid not in pids:
            continue
        title = winapi.window_title(hwnd)
        if winapi.window_class(hwnd) == GAME_WINDOW_CLASS or "roblox" in title.lower():
            windows.append(GameWindow(hwnd, pid, title))
    return windows


def windowless_pids(process_names: list[str]) -> set[int]:
    """Roblox processes running without a game window (stuck launch, ghost)."""
    with_window = {w.pid for w in find_game_windows(process_names)}
    return roblox_pids(process_names) - with_window


def launch_uri(place_id: int) -> str:
    return f"roblox://experiences/start?placeId={place_id}"


def launch_place(place_id: int) -> None:
    """Open a Roblox place through the registered roblox:// protocol handler."""
    log.info("Lancement du jeu %s", place_id)
    os.startfile(launch_uri(place_id))


def kill(pids: set[int]) -> None:
    for pid in pids:
        if winapi.terminate_process(pid):
            log.info("Processus Roblox %s arrêté", pid)
        else:
            log.warning("Impossible d'arrêter le processus %s", pid)


def wait_for_window(process_names: list[str], timeout: float) -> list[GameWindow]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        windows = find_game_windows(process_names)
        if windows:
            return windows
        time.sleep(1)
    return []
