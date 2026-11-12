"""AriaOS `security-firewall` connector: Live TCP/UDP connection monitor & intelligent firewall."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="security-firewall", version="0.1.0")


def _state_path() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp"
    p = Path(home) / ".local" / "share" / "ariaos" / "firewall_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("enabled", True)
                data.setdefault("lockdown", False)
                data.setdefault("default_incoming", "deny")
                data.setdefault("default_outgoing", "allow")
                data.setdefault("rules", [])
                return data
        except Exception:
            pass
    default_state = {
        "enabled": True,
        "lockdown": False,
        "default_incoming": "deny",
        "default_outgoing": "allow",
        "rules": [
            {"port": 22, "protocol": "tcp", "action": "block", "comment": "Bloquear SSH entrante no solicitado"},
            {"port": 4444, "protocol": "both", "action": "block", "comment": "Bloquear puerto Metasploit/Reverse Shell"},
        ],
    }
    try:
        path.write_text(json.dumps(default_state, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return default_state


def _save_state(state: Dict[str, Any]) -> None:
    try:
        _state_path().write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise ConnectorError(f"Failed to save firewall state: {exc}", code=-32000)


def _parse_proc_net_tcp(limit: int = 50) -> List[Dict[str, Any]]:
    conns: List[Dict[str, Any]] = []
    tcp_path = Path("/proc/net/tcp")
    if not tcp_path.exists():
        return conns
    state_map = {
        "01": "ESTABLISHED",
        "02": "SYN_SENT",
        "06": "TIME_WAIT",
        "0A": "LISTEN",
    }
    try:
        lines = tcp_path.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]
        for line in lines[:limit]:
            parts = line.split()
            if len(parts) < 4:
                continue
            local_hex, rem_hex, st_hex = parts[1], parts[2], parts[3]
            l_ip_h, l_port_h = local_hex.split(":")
            r_ip_h, r_port_h = rem_hex.split(":")
            l_port = int(l_port_h, 16)
            r_port = int(r_port_h, 16)

            def hex_to_ipv4(h: str) -> str:
                if len(h) != 8:
                    return h
                b = [str(int(h[i : i + 2], 16)) for i in range(0, 8, 2)]
                return ".".join(reversed(b))

            conns.append(
                {
                    "proto": "tcp",
                    "state": state_map.get(st_hex.upper(), st_hex),
                    "local": f"{hex_to_ipv4(l_ip_h)}:{l_port}",
                    "remote": f"{hex_to_ipv4(r_ip_h)}:{r_port}",
                    "process": "kernel/socket",
                }
            )
    except Exception:
        pass
    return conns


@server.tool("firewall_status")
def firewall_status(_args: Dict[str, Any]) -> Dict[str, Any]:
    state = _load_state()
    backend = "nftables" if shutil.which("nft") else ("ufw" if shutil.which("ufw") else "aria-kernel-filter")
    return {
        "backend": backend,
        "enabled": state["enabled"],
        "lockdown_mode": state["lockdown"],
        "default_incoming": state["default_incoming"],
        "default_outgoing": state["default_outgoing"],
        "rules_count": len(state["rules"]),
        "rules": state["rules"],
    }


@server.tool("active_connections")
def active_connections(args: Dict[str, Any]) -> Dict[str, Any]:
    limit = max(1, min(int(args.get("limit") or 50), 200))
    connections: List[Dict[str, Any]] = []

    if shutil.which("ss"):
        try:
            proc = subprocess.run(["ss", "-tunapH"], text=True, capture_output=True, timeout=5)
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.splitlines()[:limit]:
                    cols = line.split(None, 6)
                    if len(cols) >= 5:
                        connections.append(
                            {
                                "proto": cols[0],
                                "state": cols[1],
                                "local": cols[4],
                                "remote": cols[5] if len(cols) > 5 else "*:*",
                                "process": cols[6].strip() if len(cols) > 6 else "system",
                            }
                        )
        except Exception:
            pass

    if not connections:
        connections = _parse_proc_net_tcp(limit)

    return {
        "count": len(connections),
        "connections": connections,
    }


@server.tool("manage_port_rule")
def manage_port_rule(args: Dict[str, Any]) -> Dict[str, Any]:
    action = str(args.get("action", "")).strip().lower()
    if action not in {"block", "allow", "delete"}:
        raise ConnectorError("Action must be 'block', 'allow', or 'delete'.", code=-32602)
    port = int(args.get("port") or 0)
    if port < 1 or port > 65535:
        raise ConnectorError("Port must be between 1 and 65535.", code=-32602)
    protocol = str(args.get("protocol") or "tcp").strip().lower()
    if protocol not in {"tcp", "udp", "both"}:
        raise ConnectorError("Protocol must be 'tcp', 'udp', or 'both'.", code=-32602)
    comment = str(args.get("comment") or f"Regla puerto {port}/{protocol}").strip()

    state = _load_state()
    rules: List[Dict[str, Any]] = [
        r for r in state.get("rules", []) if not (int(r.get("port", 0)) == port and r.get("protocol") == protocol)
    ]

    if action in {"block", "allow"}:
        rules.append(
            {
                "port": port,
                "protocol": protocol,
                "action": action,
                "comment": comment,
                "updated_at": int(time.time()),
            }
        )
        # Apply to ufw if installed and permitted
        if shutil.which("ufw") and os.geteuid() == 0 if hasattr(os, "geteuid") else False:
            ufw_act = "deny" if action == "block" else "allow"
            proto_suffix = "" if protocol == "both" else f"/{protocol}"
            subprocess.run(["ufw", ufw_act, f"{port}{proto_suffix}"], capture_output=True, timeout=4)

    state["rules"] = rules
    _save_state(state)
    return {
        "applied": True,
        "action": action,
        "port": port,
        "protocol": protocol,
        "rules_count": len(rules),
    }


@server.tool("network_lockdown")
def network_lockdown(args: Dict[str, Any]) -> Dict[str, Any]:
    enabled = bool(args.get("enabled", False))
    state = _load_state()
    state["lockdown"] = enabled
    _save_state(state)

    if shutil.which("nmcli") and hasattr(os, "geteuid"):
        try:
            subprocess.run(
                ["nmcli", "networking", "off" if enabled else "on"],
                capture_output=True,
                timeout=4,
            )
        except Exception:
            pass

    return {
        "applied": True,
        "lockdown_mode": enabled,
        "status": "RED AISLADA (Modo Fortaleza)" if enabled else "CONECTIVIDAD RESTAURADA",
    }


if __name__ == "__main__":
    server.run_stdio()

