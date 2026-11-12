"""AriaOS `os-system` connector: system telemetry, top processes, and systemd control."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

UNIT_RE = re.compile(r"^[a-zA-Z0-9_.@-]+$")
server = ConnectorServer(connector_id="os-system", version="0.1.0")


def _run(cmd: List[str], timeout: int = 10) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise ConnectorError(f"Required binary not found: {cmd[0]}") from exc


def _read_linux_meminfo() -> Dict[str, Any]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return {"supported": False}

    values_kb: Dict[str, int] = {}
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            values_kb[parts[0].rstrip(":")] = int(parts[1])

    total_kb = values_kb.get("MemTotal", 0)
    avail_kb = values_kb.get("MemAvailable", values_kb.get("MemFree", 0))
    used_kb = max(0, total_kb - avail_kb)
    return {
        "supported": True,
        "total_mb": round(total_kb / 1024, 1),
        "used_mb": round(used_kb / 1024, 1),
        "available_mb": round(avail_kb / 1024, 1),
    }


def _read_uptime_seconds() -> float | None:
    uptime = Path("/proc/uptime")
    if not uptime.exists():
        return None
    first = uptime.read_text(encoding="utf-8").split()[0]
    return round(float(first), 1)


def _validate_unit(raw_unit: Any) -> str:
    if not isinstance(raw_unit, str) or not raw_unit.strip() or not UNIT_RE.match(raw_unit):
        raise ConnectorError("Invalid systemd unit name", code=-32602)
    return raw_unit.strip()


@server.tool("system_health_summary")
def system_health_summary(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Collect CPU, memory, disk usage, uptime, and failed systemd units."""
    root_path = Path("/") if os.name != "nt" else Path(Path.cwd().anchor)
    disk = shutil.disk_usage(root_path)
    loadavg = os.getloadavg() if hasattr(os, "getloadavg") else None

    failed_units: List[str] = []
    if shutil.which("systemctl"):
        res = _run(["systemctl", "--failed", "--no-legend", "--plain"])
        failed_units = [ln.split()[0] for ln in res.stdout.splitlines() if ln.strip()]

    return {
        "platform": sys.platform,
        "cpu_count": os.cpu_count(),
        "load_average_1m_5m_15m": [round(x, 2) for x in loadavg] if loadavg else None,
        "uptime_seconds": _read_uptime_seconds(),
        "memory": _read_linux_meminfo(),
        "disk": {
            "mount": str(root_path),
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
        },
        "failed_systemd_units": failed_units,
    }


@server.tool("list_top_processes")
def list_top_processes(args: Dict[str, Any]) -> Dict[str, Any]:
    """List top processes by memory or CPU on Linux."""
    sort_by = args.get("sort_by", "memory")
    if sort_by not in ("memory", "cpu"):
        raise ConnectorError("sort_by must be 'memory' or 'cpu'", code=-32602)

    limit = max(1, min(int(args.get("limit", 10)), 50))
    if not shutil.which("ps"):
        raise ConnectorError("'ps' command is only available on Unix/Linux systems")

    sort_flag = "-%mem" if sort_by == "memory" else "-%cpu"
    res = _run(["ps", "-eo", "pid,comm,%cpu,%mem,rss", f"--sort={sort_flag}"])
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or "Failed to run ps")

    rows = []
    for line in res.stdout.splitlines()[1 : limit + 1]:
        parts = line.split(None, 4)
        if len(parts) == 5:
            rows.append(
                {
                    "pid": int(parts[0]),
                    "command": parts[1],
                    "cpu_percent": float(parts[2]),
                    "mem_percent": float(parts[3]),
                    "rss_mb": round(int(parts[4]) / 1024, 1),
                }
            )
    return {"sort_by": sort_by, "processes": rows}


@server.tool("service_status")
def service_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect a systemd unit status and recent journal entries."""
    unit = _validate_unit(args.get("unit"))
    lines = max(1, min(int(args.get("lines", 10)), 100))

    state = _run(["systemctl", "is-active", unit])
    substate = _run(["systemctl", "show", unit, "--property=SubState,MainPID,ActiveEnterTimestamp"])
    logs = _run(["journalctl", "-u", unit, "-n", str(lines), "--no-pager", "-o", "short-iso"])

    props = {}
    for line in substate.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k] = v

    return {
        "unit": unit,
        "active_state": state.stdout.strip() or state.stderr.strip(),
        "properties": props,
        "recent_logs": logs.stdout.splitlines(),
    }


@server.tool("restart_service")
def restart_service(args: Dict[str, Any]) -> Dict[str, Any]:
    """Restart a systemd unit (requires privileged confirmation in aria-daemon)."""
    unit = _validate_unit(args.get("unit"))
    cmd = ["systemctl", "restart", unit]
    if os.geteuid() != 0 and shutil.which("sudo"):
        cmd = ["sudo", "-n"] + cmd

    res = _run(cmd, timeout=30)
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or f"Failed to restart {unit}")
    return {"unit": unit, "restarted": True}


if __name__ == "__main__":
    server.run_stdio()

