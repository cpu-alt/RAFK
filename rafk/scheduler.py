"""Pure decision logic: when to nudge a window. Kept free of Win32 for testing."""
from enum import Enum


class Decision(Enum):
    PLAYING = "playing"  # you're actively playing: Roblox's idle timer is reset
    WAIT = "wait"  # not due yet
    POSTPONE = "postpone"  # due, but you're using the PC: don't steal focus yet
    NUDGE = "nudge"
    FORCE = "force"  # postponed too long, nudge before Roblox kicks


# Below this many seconds of idle, input on a focused Roblox window is "playing".
PLAYING_IDLE_SECONDS = 5


def decide(
    elapsed: float,
    interval: float,
    user_idle: float,
    roblox_foreground: bool,
    required_idle: float,
    force_after: float,
) -> Decision:
    if roblox_foreground and user_idle < PLAYING_IDLE_SECONDS:
        return Decision.PLAYING
    if elapsed < interval:
        return Decision.WAIT
    if user_idle >= required_idle:
        return Decision.NUDGE
    if elapsed >= force_after:
        return Decision.FORCE
    return Decision.POSTPONE


def backoff(attempt: int, base: float = 60, cap: float = 600) -> float:
    """Delay before relaunch attempt `attempt` (0-based): 60, 120, 240… capped."""
    return min(cap, base * (2**attempt))
