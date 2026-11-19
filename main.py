"""Entry point for BORDER LINES — A Bureaucratic Logic Puzzle of Visas & Borders."""

import argparse
import os
import sys
from typing import List, Optional

from game.app import Game
from game.core.loader import DataLoadError


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line options for developer shortcuts."""
    parser = argparse.ArgumentParser(
        prog="BORDER LINES",
        description="BORDER LINES: A 2D bureaucratic logic puzzle about visas and borders.",
    )
    parser.add_argument(
        "--unlock-all",
        action="store_true",
        help="Unlock all Traveler levels and the Consul campaign immediately.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset saved progress and star ratings back to default.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Parse arguments, initialize the Game controller, and start the main loop."""
    args = parse_args(argv)
    project_root = os.path.dirname(os.path.abspath(__file__))
    try:
        app = Game(
            project_root=project_root,
            unlock_all=args.unlock_all,
            reset_progress=args.reset,
        )
        app.run()
        return 0
    except DataLoadError as exc:
        sys.stderr.write(f"[DATA ERROR] Failed to load game configuration:\n  {exc}\n")
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
