"""Global pause/resume hotkey, listened for on a background thread."""
import logging
import threading
from collections.abc import Callable

from . import winapi

log = logging.getLogger(__name__)

HOTKEY_ID = 1


class HotkeyListener:
    def __init__(self, key_name: str, on_press: Callable[[], None]):
        self.key_name = key_name
        self.on_press = on_press
        self._thread_id = 0
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(2)

    def stop(self) -> None:
        if self._thread_id:
            winapi.post_quit(self._thread_id)

    def _run(self) -> None:
        # RegisterHotKey binds to the calling thread's message queue.
        self._thread_id = winapi.current_thread_id()
        ok = winapi.register_hotkey(HOTKEY_ID, winapi.vk_from_name(self.key_name))
        self._ready.set()
        if not ok:
            log.warning("Raccourci %s indisponible (déjà utilisé ?)", self.key_name)
            return
        try:
            while winapi.wait_hotkey() == HOTKEY_ID:
                self.on_press()
        finally:
            winapi.unregister_hotkey(HOTKEY_ID)
