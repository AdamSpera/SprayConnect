from __future__ import annotations

import argparse
import sys

from .connection_manager import ConnectionManager, load_config
from .logger import logger
import os


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connect to host")
    parser.add_argument("hostname", help="Hostname to connect to")
    parser.add_argument(
        "--config",
        help=(
            "Path to an extra hosts YAML file overriding the packaged "
            "hosts.yaml (or CONEX_HOSTS_FILE)"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.error("Configuration file not found")
        return 1

    manager = ConnectionManager(config)
    try:
        method, info = manager.connect(args.hostname)
        logger.info(f"Successfully connected using {method}")

        # Launch interactive session using the successful method
        m = method.lower().replace(" ", "_")
        if m in {"ssh", "console_ssh"}:
            cmd = ["ssh"]
            if info.get("username"):
                cmd.extend(["-l", info["username"]])
            cmd.extend(["-p", str(info["port"]), info["ip"]])
            logger.info("Opening SSH session...")
            os.execvp("ssh", cmd)
        elif m in {"telnet", "console_telnet"}:
            cmd = ["telnet", info["ip"], str(info["port"])]
            logger.info("Opening Telnet session...")
            os.execvp("telnet", cmd)

        return 0
    except Exception as exc:  # catch all connection errors
        logger.error(str(exc))
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
