import argparse
import logging
import sys
from pathlib import Path

from . import afk, launcher
from .config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(prog="rafk", description="Roblox anti-AFK")
    parser.add_argument("-c", "--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--place", type=int, help="Launch this Roblox place before starting")
    parser.add_argument("--once", action="store_true", help="Send a single nudge and exit")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if sys.platform != "win32":
        logging.error("RAFK only runs on Windows")
        return 1

    cfg = load_config(args.config)
    place = args.place or cfg.launch_place_id
    if place:
        launcher.launch_place(place)
        if not launcher.wait_for_window(cfg.process_name, cfg.launch_wait_seconds):
            logging.error("Roblox did not open within %ss", cfg.launch_wait_seconds)
            return 1

    if args.once:
        return 0 if afk.nudge_all(cfg) else 1

    try:
        afk.run(cfg)
    except KeyboardInterrupt:
        logging.info("Stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
