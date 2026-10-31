import unittest

from rafk.scheduler import Decision, backoff, decide

BASE = dict(interval=600, required_idle=30, force_after=1080)


class DecideTests(unittest.TestCase):
    def test_playing_resets_when_roblox_focused_and_user_active(self):
        self.assertIs(decide(elapsed=900, user_idle=1, roblox_foreground=True, **BASE), Decision.PLAYING)

    def test_waits_before_interval(self):
        self.assertIs(decide(elapsed=100, user_idle=999, roblox_foreground=False, **BASE), Decision.WAIT)

    def test_nudges_when_due_and_user_idle(self):
        self.assertIs(decide(elapsed=600, user_idle=60, roblox_foreground=False, **BASE), Decision.NUDGE)

    def test_postpones_when_user_busy_elsewhere(self):
        self.assertIs(decide(elapsed=700, user_idle=2, roblox_foreground=False, **BASE), Decision.POSTPONE)

    def test_forces_before_kick(self):
        self.assertIs(decide(elapsed=1080, user_idle=2, roblox_foreground=False, **BASE), Decision.FORCE)

    def test_idle_user_on_focused_roblox_still_nudged(self):
        self.assertIs(decide(elapsed=650, user_idle=120, roblox_foreground=True, **BASE), Decision.NUDGE)


class BackoffTests(unittest.TestCase):
    def test_doubles_then_caps(self):
        self.assertEqual([backoff(i) for i in range(5)], [60, 120, 240, 480, 600])


if __name__ == "__main__":
    unittest.main()
