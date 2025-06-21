from __future__ import annotations

import argparse
import sys

from .connection_manager import ConnectionManager, load_config
from .logger import logger, console


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connect to host")
    parser.add_argument("hostname", help="Hostname to connect to")
    parser.add_argument(
        "--config",
        help="Path to hosts YAML file (default: ~/.sc/hosts.yaml or SC_HOSTS_FILE)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    console.print()  # spacing
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.error("Configuration file not found")
        return 1

    manager = ConnectionManager(config)
    try:
        method = manager.connect(args.hostname)
        logger.info(f"Successfully connected using {method}")
        console.print()
        return 0
    except Exception as exc:  # catch all connection errors
        logger.error(str(exc))
        console.print()
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
