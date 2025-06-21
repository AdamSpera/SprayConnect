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

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.conex/hosts.yaml")
ENV_CONFIG = "CONEX_HOSTS_FILE"


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    path = path or os.getenv(ENV_CONFIG, DEFAULT_CONFIG_PATH)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ConnectionManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def connect(self, hostname: str) -> str:
        host_cfg = self.config.get(hostname)
        if not host_cfg:
            raise ValueError(f"Host '{hostname}' not found in configuration")
        for name, method, info in self._iter_methods(host_cfg):
            ip = info["ip"]
            port = info["port"]
            logger.info(f"Trying {name}:{port} on {ip}")
            try:
                method(info)
                logger.info(f"Connected via {name}")
                return name
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

