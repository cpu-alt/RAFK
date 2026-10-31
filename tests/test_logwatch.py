import tempfile
import time
import unittest
from pathlib import Path

from rafk.logwatch import LogWatcher

PATTERNS = ["Lost connection with reason"]


class LogWatcherTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def write(self, name: str, text: str, mode: str = "a") -> Path:
        path = self.dir / name
        with path.open(mode, encoding="utf-8") as f:
            f.write(text)
        return path

    def test_ignores_lines_written_before_start(self):
        self.write("old.log", "Lost connection with reason: old\n")
        watcher = LogWatcher(PATTERNS, self.dir)
        self.assertIsNone(watcher.poll())

    def test_detects_new_matching_line(self):
        self.write("s.log", "boot\n")
        watcher = LogWatcher(PATTERNS, self.dir)
        self.write("s.log", "noise\n2026 [FLog::Network] Lost connection with reason : 277\n")
        self.assertIn("277", watcher.poll())
        self.assertIsNone(watcher.poll())

    def test_waits_for_complete_line(self):
        watcher = LogWatcher(PATTERNS, self.dir)
        self.write("s.log", "Lost connection with")
        self.assertIsNone(watcher.poll())
        self.write("s.log", " reason: 279\n")
        self.assertIn("279", watcher.poll())

    def test_follows_new_session_log(self):
        self.write("a.log", "x\n")
        watcher = LogWatcher(PATTERNS, self.dir)
        time.sleep(0.05)
        self.write("b.log", "Lost connection with reason: new session\n")
        self.assertIn("new session", watcher.poll())

    def test_missing_dir_is_harmless(self):
        self.assertIsNone(LogWatcher(PATTERNS, self.dir / "nope").poll())


if __name__ == "__main__":
    unittest.main()
