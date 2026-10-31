import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import __version__


FORMAT = "%(asctime)s %(levelname)-7s %(message)s"


def setup_logging() -> None:
    # Windows consoles default to cp1252; don't crash on accents/emoji.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(level=logging.INFO, format=FORMAT, datefmt="%H:%M:%S")


def add_file_logging(log_file: str) -> None:
    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter(FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
    logging.getLogger().addHandler(handler)


def list_windows(cfg) -> int:
    from . import roblox

    windows = roblox.find_game_windows(cfg.process_names)
    ghosts = roblox.windowless_pids(cfg.process_names)
    for w in windows:
        print(f"✔ fenêtre {w.hwnd}  pid {w.pid}  {w.title!r}")
    for pid in sorted(ghosts):
        print(f"✘ pid {pid} : Roblox tourne SANS fenêtre de jeu (lancement bloqué ?)")
    if not windows and not ghosts:
        print("Roblox n'est pas lancé.")
    return 0 if windows else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="rafk", description="Anti-AFK Roblox pour Windows")
    parser.add_argument("-c", "--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--place", type=int, help="ID du jeu à lancer (et à relancer si déconnecté)")
    parser.add_argument("--once", action="store_true", help="envoie une seule action puis quitte")
    parser.add_argument("--list", action="store_true", help="affiche les fenêtres Roblox détectées")
    parser.add_argument("--version", action="version", version=f"rafk {__version__}")
    args = parser.parse_args()

    if sys.platform != "win32":
        print("RAFK ne fonctionne que sous Windows", file=sys.stderr)
        return 1

    from . import roblox, winapi
    from .app import AntiAfk
    from .config import load_config
    from .hotkeys import HotkeyListener

    setup_logging()
    try:
        cfg = load_config(args.config)
    except (ValueError, OSError) as exc:
        print(f"Config invalide ({args.config}) : {exc}", file=sys.stderr)
        return 2
    if cfg.log_file:
        add_file_logging(cfg.log_file)
    if args.place:
        cfg.place_id = args.place

    if args.list:
        return list_windows(cfg)

    app = AntiAfk(cfg)
    if args.once:
        if not app.nudge_once():
            logging.warning("Aucune fenêtre Roblox trouvée (essaie --list)")
            return 1
        return 0

    hotkey = HotkeyListener(cfg.pause_hotkey, app.toggle_pause) if cfg.pause_hotkey else None
    try:
        if cfg.prevent_sleep:
            winapi.prevent_sleep(True)
        if hotkey:
            hotkey.start()
        if cfg.place_id and not roblox.find_game_windows(cfg.process_names):
            roblox.launch_place(cfg.place_id)
            logging.info("Attente de la fenêtre Roblox (max %ss)…", cfg.launch_wait_seconds)
            if not roblox.wait_for_window(cfg.process_names, cfg.launch_wait_seconds):
                logging.warning("Roblox ne s'est pas ouvert, le watchdog va réessayer")
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()
        if hotkey:
            hotkey.stop()
        if cfg.prevent_sleep:
            winapi.prevent_sleep(False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
