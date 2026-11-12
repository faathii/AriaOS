"""AriaOS `os-kernel` connector: Linux kernel telemetry, dmesg, hardware, sysctl, and kmods."""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

SYSCTL_KEY_RE = re.compile(r"^[a-zA-Z0-9._-]{1,128}$")
SYSCTL_VAL_RE = re.compile(r"^[a-zA-Z0-9 ._:/,-]{1,128}$")
KMOD_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
DMESG_LEVEL_RE = re.compile(r"^[a-z,]{1,40}$")

server = ConnectorServer(connector_id="os-kernel", version="0.1.0")


def _read_text(path: Path, max_chars: int = 4000) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip()[:max_chars]
    except OSError:
        return None


def _thermal_zones() -> List[Dict[str, Any]]:
    thermal_root = Path("/sys/class/thermal")
    zones: List[Dict[str, Any]] = []
    if not thermal_root.exists():
        return zones
    for zone in sorted(thermal_root.glob("thermal_zone*")):
        ztype = _read_text(zone / "type") or zone.name
        temp_raw = _read_text(zone / "temp")
        temp_c = round(int(temp_raw) / 1000.0, 1) if temp_raw and temp_raw.lstrip("-").isdigit() else None
        zones.append({"zone": zone.name, "type": ztype, "temp_c": temp_c})
    return zones


@server.tool("kernel_telemetry")
def kernel_telemetry(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Read Linux kernel release, cmdline, PSI metrics, thermal zones, and loaded modules."""
    uname = platform.uname()
    cmdline = _read_text(Path("/proc/cmdline"))
    loadavg = _read_text(Path("/proc/loadavg"))
    modules_raw = _read_text(Path("/proc/modules"), max_chars=32768)
    loaded_modules = [line.split()[0] for line in modules_raw.splitlines() if line.strip()] if modules_raw else []
    psi = {
        res: _read_text(Path(f"/proc/pressure/{res}"))
        for res in ("cpu", "memory", "io")
        if Path(f"/proc/pressure/{res}").exists()
    }
    return {
        "system": uname.system,
        "node": uname.node,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "cmdline": cmdline,
        "loadavg": loadavg,
        "psi": psi,
        "thermal_zones": _thermal_zones(),
        "loaded_module_count": len(loaded_modules),
        "sample_modules": loaded_modules[:25],
    }


@server.tool("dmesg_inspect")
def dmesg_inspect(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read recent Linux kernel ring buffer messages."""
    lines = max(1, min(int(args.get("lines") or 50), 300))
    level = args.get("level")
    if not shutil.which("dmesg"):
        return {"available": False, "reason": "dmesg binary not found", "lines": []}

    cmd = ["dmesg", "-T", "--notime"]
    # Keep human timestamps when supported
    cmd = ["dmesg", "-T"]
    if isinstance(level, str) and level.strip():
        lvl = level.strip()
        if not DMESG_LEVEL_RE.match(lvl):
            raise ConnectorError(f"Invalid dmesg level filter: {lvl}", code=-32602)
        cmd.append(f"--level={lvl}")

    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=10)
    if proc.returncode != 0:
        raise ConnectorError(f"dmesg failed: {(proc.stderr or proc.stdout).strip()}", code=-32000)

    out_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "total_matching_lines": len(out_lines),
        "lines": out_lines[-lines:],
    }


@server.tool("hardware_pci_usb")
def hardware_pci_usb(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Inspect PCI devices, USB devices, and kernel network interfaces."""
    pci_lines: List[str] = []
    usb_lines: List[str] = []
    interfaces: Any = []

    if shutil.which("lspci"):
        proc = subprocess.run(["lspci"], text=True, capture_output=True, timeout=8)
        if proc.returncode == 0:
            pci_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    if shutil.which("lsusb"):
        proc = subprocess.run(["lsusb"], text=True, capture_output=True, timeout=8)
        if proc.returncode == 0:
            usb_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    if shutil.which("ip"):
        proc = subprocess.run(["ip", "-j", "addr"], text=True, capture_output=True, timeout=8)
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                interfaces = json.loads(proc.stdout)
            except json.JSONDecodeError:
                interfaces = proc.stdout.strip()

    return {
        "pci_devices": pci_lines[:60],
        "usb_devices": usb_lines[:60],
        "network_interfaces": interfaces,
    }


@server.tool("sysctl_read")
def sysctl_read(args: Dict[str, Any]) -> Dict[str, Any]:
    """Read a live Linux kernel sysctl parameter."""
    key = args.get("key")
    if not isinstance(key, str) or not SYSCTL_KEY_RE.match(key.strip()):
        raise ConnectorError("Invalid sysctl key.", code=-32602)
    clean_key = key.strip()

    proc_path = Path("/proc/sys") / clean_key.replace(".", "/")
    if proc_path.exists() and proc_path.is_file():
        return {"key": clean_key, "value": _read_text(proc_path), "source": "/proc/sys"}

    if not shutil.which("sysctl"):
        raise ConnectorError("sysctl unavailable and key not found in /proc/sys", code=-32000)
    proc = subprocess.run(["sysctl", "-n", clean_key], text=True, capture_output=True, timeout=5)
    if proc.returncode != 0:
        raise ConnectorError(f"sysctl read failed: {(proc.stderr or proc.stdout).strip()}", code=-32000)
    return {"key": clean_key, "value": proc.stdout.strip(), "source": "sysctl"}


@server.tool("sysctl_write")
def sysctl_write(args: Dict[str, Any]) -> Dict[str, Any]:
    """Write a live Linux kernel sysctl parameter cleanly."""
    key = args.get("key")
    value = args.get("value")
    if not isinstance(key, str) or not SYSCTL_KEY_RE.match(key.strip()):
        raise ConnectorError("Invalid sysctl key.", code=-32602)
    if not isinstance(value, str) or not SYSCTL_VAL_RE.match(value.strip()):
        raise ConnectorError("Invalid sysctl value.", code=-32602)
    if not shutil.which("sysctl"):
        raise ConnectorError("sysctl binary not found.", code=-32000)

    clean_key = key.strip()
    clean_val = value.strip()
    proc = subprocess.run(["sysctl", "-w", f"{clean_key}={clean_val}"], text=True, capture_output=True, timeout=5)
    if proc.returncode != 0:
        raise ConnectorError(f"sysctl -w failed: {(proc.stderr or proc.stdout).strip()}", code=-32000)
    return {"key": clean_key, "value": clean_val, "applied": True, "output": proc.stdout.strip()}


@server.tool("kernel_module_manage")
def kernel_module_manage(args: Dict[str, Any]) -> Dict[str, Any]:
    """Load or unload a Linux kernel module with modprobe."""
    module = args.get("module")
    action = args.get("action")
    if not isinstance(module, str) or not KMOD_NAME_RE.match(module.strip()):
        raise ConnectorError("Invalid kernel module name.", code=-32602)
    if action not in {"load", "unload"}:
        raise ConnectorError("Action must be 'load' or 'unload'.", code=-32602)
    if not shutil.which("modprobe"):
        raise ConnectorError("modprobe binary not found.", code=-32000)

    clean_mod = module.strip()
    cmd = ["modprobe", clean_mod] if action == "load" else ["modprobe", "-r", clean_mod]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=15)
    if proc.returncode != 0:
        raise ConnectorError(f"modprobe failed: {(proc.stderr or proc.stdout).strip()}", code=-32000)
    return {"module": clean_mod, "action": action, "success": True}


if __name__ == "__main__":
    server.run_stdio()

