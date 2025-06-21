from __future__ import annotations

import os
import yaml
from typing import Dict, Any, Optional, Iterable, Tuple

from .logger import logger

try:
    import paramiko
except ImportError:  # pragma: no cover - paramiko missing during tests
    paramiko = None

import telnetlib

PACKAGE_DIR = os.path.dirname(__file__)
DEFAULT_CONFIG_PATH = os.path.join(PACKAGE_DIR, "hosts.yaml")
ENV_CONFIG = "CONEX_HOSTS_FILE"


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration, optionally merging overrides from ``path``.

    The base configuration is read from ``hosts.yaml`` in the package
    directory. If a path is provided (either via ``--config`` or the
    ``CONEX_HOSTS_FILE`` environment variable), its contents override any
    matching hosts from the base file.
    """

    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    override = path or os.getenv(ENV_CONFIG)
    if override:
        with open(override, "r", encoding="utf-8") as f:
            new_cfg = yaml.safe_load(f) or {}
        config.update(new_cfg)

    return config


class ConnectionManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def connect(self, hostname: str) -> tuple[str, Dict[str, Any]]:
        host_cfg = self.config.get(hostname)
        if not host_cfg:
            raise ValueError(f"Host '{hostname}' not found in configuration")
        for name, method, info in self._iter_methods(host_cfg):
            ip = info["ip"]
            port = info["port"]
            logger.info(f"Trying {name} on {ip}:{port}")
            try:
                method(info)
                logger.info(f"Connected via {name}")
                return name, info
            except Exception as exc:
                logger.error(f"{name} failed: {exc}")

        raise RuntimeError("All connection methods failed")

    def _iter_methods(self, host_cfg: Any) -> Iterable[Tuple[str, callable, Dict[str, Any]]]:
        """Yield connection methods for a host in priority order.

        `host_cfg` may be a list directly under the hostname or a dictionary
        containing a `connections` list. Legacy keys like `ssh` and `telnet`
        are also accepted for backward compatibility. Each entry must include a
        `port` so all connection types share the same schema.
        """
        methods = []
        if isinstance(host_cfg, list):
            methods = host_cfg
        elif isinstance(host_cfg, dict):
            if isinstance(host_cfg.get("connections"), list):
                methods = host_cfg["connections"]
            else:
                def add(key, entry, conv=None):
                    if entry is None or str(entry).lower() == "none":
                        return
                    item = dict(entry)
                    if conv:
                        conv(item)
                    else:
                        item.setdefault("type", key)
                    methods.append(item)

                add("ssh", host_cfg.get("ssh"))
                add("telnet", host_cfg.get("telnet"))
                add("console_ssh", host_cfg.get("console_ssh"))
                add("console_telnet", host_cfg.get("console_telnet"))

                def conv_console(d):
                    typ = (d.get("type") or "ssh").lower()
                    d["type"] = f"console_{typ}"

                add("console", host_cfg.get("console"), conv_console)
        else:
            raise ValueError("Invalid host configuration format")

        priority = {
            "ssh": 0,
            "telnet": 1,
            "console_ssh": 2,
            "console_telnet": 3,
        }

        def sort_key(item):
            t = str(item.get("type", "")).lower().replace("-", "_")
            return priority.get(t, 99)

        for item in sorted(methods, key=sort_key):
            t = str(item.get("type", "")).lower().replace("-", "_")
            if "port" not in item:
                raise ValueError(f"{t} requires a port")
            if t == "telnet":
                yield "Telnet", self._connect_telnet, item
            elif t == "console_telnet":
                yield "Console Telnet", self._connect_telnet, item
            elif t == "console_ssh":
                yield "Console SSH", self._connect_ssh, item
            else:
                yield "SSH", self._connect_ssh, item

    def _connect_ssh(self, info: Dict[str, Any]):
        if paramiko is None:
            raise RuntimeError("paramiko not installed")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=info["ip"],
                port=info["port"],
                username=info.get("username"),
                password=info.get("password"),
                look_for_keys=False,
                allow_agent=False,
                timeout=5,
                banner_timeout=5,
                auth_timeout=5,
            )
        finally:
            client.close()

    def _connect_telnet(self, info: Dict[str, Any]):
        host = info["ip"]
        port = info["port"]
        tn = telnetlib.Telnet(host, port, timeout=5)
        username = info.get("username")
        password = info.get("password")
        if username:
            tn.read_until(b"login:")
            tn.write(username.encode("ascii") + b"\n")
        if password:
            tn.read_until(b"Password:")
            tn.write(password.encode("ascii") + b"\n")
        tn.close()

