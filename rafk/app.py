"""Main anti-AFK loop: nudges, idle detection, watchdog and auto-rejoin."""
import logging
import random
import threading
import time
from dataclasses import dataclass, field

from . import actions, roblox, winapi
from .logwatch import LogWatcher
from .config import Config
from .notify import Notifier
from .scheduler import Decision, backoff, decide

log = logging.getLogger(__name__)

TICK_SECONDS = 1.0
# Windows stamps injected input slightly after SendInput returns.
OWN_INPUT_GRACE_MS = 1000


@dataclass
class WindowState:
    last_activity: float
    interval: float
    hung_since: float | None = None
    hung_reported: bool = False
    postponed_logged: bool = False


@dataclass
class Stats:
    started: float = field(default_factory=time.monotonic)
    nudges: int = 0
    relaunches: int = 0

    def summary(self) -> str:
        minutes = int((time.monotonic() - self.started) // 60)
        return f"{minutes // 60}h{minutes % 60:02d} actif, {self.nudges} actions, {self.relaunches} relances"


class AntiAfk:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.notifier = Notifier(cfg.discord_webhook)
        self.stats = Stats()
        self.paused = threading.Event()
        self.stopping = threading.Event()
        self.windows: dict[int, WindowState] = {}
        # Tick of the last input we believe came from the user, not from us.
        self._user_input_tick = winapi.last_input_tick()
        self._own_input_until = self._user_input_tick
        self.logwatch = LogWatcher(cfg.disconnect_patterns) if cfg.detect_disconnect else None
        self._no_window_since: float | None = None
        self._next_launch_at = 0.0
        self._launch_attempts = 0

    # --- public -------------------------------------------------------------

    def toggle_pause(self) -> None:
        if self.paused.is_set():
            self.paused.clear()
            log.info("▶ Reprise")
        else:
            self.paused.set()
            log.info("⏸ Pause (appuie encore sur %s pour reprendre)", self.cfg.pause_hotkey)

    def run(self) -> None:
        log.info(
            "Anti-AFK actif : action toutes les ~%ss (%s). Ctrl+C pour arrêter%s.",
            self.cfg.interval_seconds,
            ", ".join(self.cfg.actions),
            f", {self.cfg.pause_hotkey} pour pause" if self.cfg.pause_hotkey else "",
        )
        self.notifier.send("🟢 RAFK démarré")
        while not self.stopping.wait(TICK_SECONDS):
            if not self.paused.is_set():
                self.tick()

    def stop(self) -> None:
        self.stopping.set()
        log.info("Arrêt — %s", self.stats.summary())
        self.notifier.send(f"🔴 RAFK arrêté — {self.stats.summary()}")

    def nudge_once(self) -> int:
        windows = roblox.find_game_windows(self.cfg.process_names)
        self._nudge([w.hwnd for w in windows])
        return len(windows)

    # --- loop ---------------------------------------------------------------

    def tick(self) -> None:
        now = time.monotonic()
        found = roblox.find_game_windows(self.cfg.process_names)
        self._sync_windows(found, now)
        self._check_disconnect(found)
        self._watchdog(found, now)

        user_idle = self._user_idle_seconds()
        foreground = winapi.foreground_window()
        due: list[int] = []
        for hwnd, state in self.windows.items():
            decision = decide(
                elapsed=now - state.last_activity,
                interval=state.interval,
                user_idle=user_idle,
                roblox_foreground=hwnd == foreground,
                required_idle=self.cfg.user_idle_seconds,
                force_after=self.cfg.force_after_seconds,
            )
            if decision is Decision.PLAYING:
                state.last_activity = now
            elif decision is Decision.POSTPONE and not state.postponed_logged:
                log.info("Tu utilises le PC, action reportée (forcée avant le kick)")
                state.postponed_logged = True
            elif decision is Decision.FORCE:
                log.info("Action forcée pour éviter le kick")
                due.append(hwnd)
            elif decision is Decision.NUDGE:
                due.append(hwnd)
        if due:
            self._nudge(due)

    def _sync_windows(self, found: list[roblox.GameWindow], now: float) -> None:
        current = {w.hwnd for w in found}
        for hwnd in list(self.windows):
            if hwnd not in current:
                log.warning("Fenêtre Roblox %s fermée", hwnd)
                del self.windows[hwnd]
        for w in found:
            if w.hwnd not in self.windows:
                log.info("Fenêtre Roblox détectée : %r (pid %s)", w.title, w.pid)
                self.windows[w.hwnd] = WindowState(last_activity=now, interval=self._interval())
                self._launch_attempts = 0

    def _interval(self) -> float:
        j = self.cfg.jitter_seconds
        return self.cfg.interval_seconds + random.uniform(-j, j)

    def _user_idle_seconds(self) -> float:
        last = winapi.last_input_tick()
        # Input stamped at or just after the end of our nudge is ours: ignore it.
        since_own = winapi.tick_diff(last, self._own_input_until)
        if OWN_INPUT_GRACE_MS < since_own < 2**31:
            self._user_input_tick = last
        return winapi.tick_diff(winapi.tick_ms(), self._user_input_tick) / 1000

    # --- nudging ------------------------------------------------------------

    def _nudge(self, hwnds: list[int]) -> None:
        previous = winapi.foreground_window()
        now = time.monotonic()
        try:
            for hwnd in hwnds:
                was_minimized = winapi.is_minimized(hwnd)
                if not winapi.focus_window(hwnd):
                    log.warning("Impossible de mettre Roblox au premier plan (%s)", hwnd)
                    continue
                time.sleep(0.3)
                spec = random.choice(self.cfg.actions)
                actions.resolve(spec)()
                self.stats.nudges += 1
                log.info("Action « %s » envoyée (fenêtre %s)", spec, hwnd)
                if was_minimized and self.cfg.restore_minimized:
                    winapi.minimize_window(hwnd)
                if hwnd in self.windows:
                    state = self.windows[hwnd]
                    state.last_activity = now
                    state.interval = self._interval()
                    state.postponed_logged = False
            if self.cfg.restore_focus and previous and previous not in hwnds and winapi.is_window(previous):
                winapi.focus_window(previous)
        finally:
            self._own_input_until = winapi.tick_ms()

    # --- watchdog & rejoin --------------------------------------------------

    def _watchdog(self, found: list[roblox.GameWindow], now: float) -> None:
        hung_pids: set[int] = set()
        for w in found:
            state = self.windows[w.hwnd]
            if winapi.is_hung(w.hwnd):
                state.hung_since = state.hung_since or now
                if now - state.hung_since >= self.cfg.hang_timeout_seconds:
                    hung_pids.add(w.pid)
                    if not state.hung_reported:
                        log.error("Roblox ne répond plus depuis %ss", self.cfg.hang_timeout_seconds)
                        self.notifier.send("⚠️ Roblox ne répond plus")
                        state.hung_reported = True
            else:
                state.hung_since = None
                state.hung_reported = False

        if hung_pids:
            if self.cfg.place_id and self.cfg.auto_rejoin:
                roblox.kill(hung_pids)
            return

        if found:
            self._no_window_since = None
            return
        if self._no_window_since is None:
            self._no_window_since = now
            log.warning("Aucune fenêtre Roblox trouvée")
            if self.cfg.place_id and self.cfg.auto_rejoin:
                self.notifier.send("⚠️ Roblox fermé / déconnecté, relance prévue")
        if not (self.cfg.place_id and self.cfg.auto_rejoin):
            return
        if now - self._no_window_since >= self.cfg.rejoin_after_seconds and now >= self._next_launch_at:
            self._relaunch(now)

    def _check_disconnect(self, found: list[roblox.GameWindow]) -> None:
        if not self.logwatch:
            return
        line = self.logwatch.poll()
        if not line or not found:
            return
        log.error("Déconnexion détectée dans les logs Roblox : %s", line[:200])
        self.notifier.send("⚠️ Déconnecté du jeu")
        if self.cfg.place_id and self.cfg.auto_rejoin:
            roblox.kill({w.pid for w in found})

    def _relaunch(self, now: float) -> None:
        ghosts = roblox.windowless_pids(self.cfg.process_names)
        if ghosts:
            log.info("Nettoyage de %d processus Roblox sans fenêtre", len(ghosts))
            roblox.kill(ghosts)
        roblox.launch_place(self.cfg.place_id)
        self.stats.relaunches += 1
        self.notifier.send(f"🔁 Relance du jeu {self.cfg.place_id}")
        self._next_launch_at = now + backoff(self._launch_attempts)
        self._launch_attempts += 1
