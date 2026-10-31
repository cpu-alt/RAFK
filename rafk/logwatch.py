"""Detect in-game disconnects (error 277, kicks…) by tailing Roblox's own logs.

The game window stays open on the "Disconnected" dialog, so the watchdog can't
see it; the client log can.
"""
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


def default_log_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", "")) / "Roblox" / "logs"


class LogWatcher:
    def __init__(self, patterns: list[str], log_dir: Path | None = None):
        self.patterns = [p.lower() for p in patterns]
        self.log_dir = log_dir or default_log_dir()
        self._file: Path | None = None
        self._offset = 0
        # Start at the end of whatever log exists now: old sessions don't count.
        latest = self._latest()
        if latest:
            self._file, self._offset = latest, latest.stat().st_size

    def _latest(self) -> Path | None:
        try:
            logs = list(self.log_dir.glob("*.log"))
        except OSError:
            return None
        return max(logs, key=lambda p: p.stat().st_mtime, default=None)

    def poll(self) -> str | None:
        """Return the first new log line matching a pattern, if any."""
        latest = self._latest()
        if latest is None:
            return None
        if latest != self._file:
            self._file, self._offset = latest, 0
        try:
            with latest.open("rb") as f:
                f.seek(self._offset)
                chunk = f.read()
        except OSError:
            return None
        # Only consume complete lines; keep a partial last line for next poll.
        end = chunk.rfind(b"\n") + 1
        self._offset += end
        for line in chunk[:end].decode("utf-8", errors="ignore").splitlines():
            lower = line.lower()
            if any(p in lower for p in self.patterns):
                return line.strip()
        return None
