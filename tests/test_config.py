import unittest

from rafk.config import from_dict


class ConfigTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        cfg = from_dict({})
        self.assertEqual(cfg.process_names, ["RobloxPlayerBeta.exe"])

    def test_migrates_v01_keys(self):
        with self.assertLogs("rafk.config", "WARNING"):
            cfg = from_dict({"keys": ["space"], "process_name": "X.exe", "launch_place_id": 42})
        self.assertEqual(cfg.actions, ["key:space"])
        self.assertEqual(cfg.process_names, ["X.exe"])
        self.assertEqual(cfg.place_id, 42)

    def test_rejects_unknown_key(self):
        with self.assertRaisesRegex(ValueError, "Unknown config keys"):
            from_dict({"nope": 1})

    def test_rejects_unknown_action(self):
        with self.assertRaisesRegex(ValueError, "Unknown action"):
            from_dict({"actions": ["dance"]})

    def test_rejects_unknown_raw_key(self):
        with self.assertRaisesRegex(ValueError, "Unknown key"):
            from_dict({"actions": ["key:f13"]})

    def test_rejects_interval_too_close_to_kick(self):
        with self.assertRaises(ValueError):
            from_dict({"interval_seconds": 1100, "jitter_seconds": 60})
        with self.assertRaises(ValueError):
            from_dict({"force_after_seconds": 1200})

    def test_rejects_bad_hotkey(self):
        with self.assertRaisesRegex(ValueError, "hotkey"):
            from_dict({"pause_hotkey": "ctrl+x"})

    def test_hotkey_can_be_disabled(self):
        self.assertEqual(from_dict({"pause_hotkey": ""}).pause_hotkey, "")


if __name__ == "__main__":
    unittest.main()
