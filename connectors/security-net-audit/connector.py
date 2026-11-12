#!/usr/bin/env python3
"""Security & Reverse Engineering connector for AriaOS."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("security-net-audit", "0.1.0")
TARGET_RE = re.compile(r"^[A-Za-z0-9._:/-]+$")

SECURITY_BINS = {
    "wireshark": "wireshark",
    "tshark": "tshark",
    "nmap": "nmap",
    "burpsuite": "burpsuite",
    "ghidra": "ghidra",
    "cutter": "cutter",
    "rizin": "rizin",
    "metasploit": "msfconsole",
    "hashcat": "hashcat",
    "john": "john",
}


@server.tool("security_suite_status")
def security_suite_status(params: dict[str, Any]) -> dict[str, Any]:
    tools = {label: bool(shutil.which(cmd)) for label, cmd in SECURITY_BINS.items()}
    return {"tools": tools}


@server.tool("inspect_binary")
def inspect_binary(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)

    target = Path(raw_path).expanduser().resolve()
    if not target.is_file():
        raise ConnectorError(f"Binary file does not exist: {target}", -32602)

    head = target.read_bytes()[:64]
    fmt = "unknown"
    arch = None
    if head.startswith(b"\x7fELF") and len(head) >= 20:
        fmt = "ELF"
        cls = head[4]
        arch = "64-bit" if cls == 2 else "32-bit" if cls == 1 else "unknown"
    elif head.startswith(b"MZ"):
        fmt = "PE/DOS"
    elif head[:4] in {b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe"}:
        fmt = "Mach-O"

    return {
        "path": str(target),
        "size_bytes": target.stat().st_size,
        "format": fmt,
        "bitness": arch,
    }


@server.tool("inspect_pcap")
def inspect_pcap(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    max_packets = params.get("max_packets", 40)
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)
    if not isinstance(max_packets, int) or max_packets < 1 or max_packets > 200:
        raise ConnectorError("'max_packets' must be between 1 and 200.", -32602)

    pcap = Path(raw_path).expanduser().resolve()
    if not pcap.is_file() or pcap.suffix.lower() not in {".pcap", ".pcapng", ".cap"}:
        raise ConnectorError(f"Expected an existing .pcap/.pcapng file: {pcap}", -32602)

    tshark = shutil.which("tshark")
    if not tshark:
        raise ConnectorError("'tshark' is not installed on this system.", -32000)

    proc = subprocess.run(
        [tshark, "-r", str(pcap), "-c", str(max_packets)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or "tshark failed", -32000)

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return {"path": str(pcap), "packet_count": len(lines), "packets": lines}


@server.tool("nmap_scan")
def nmap_scan(params: dict[str, Any]) -> dict[str, Any]:
    target = params.get("target")
    mode = params.get("mode", "top_ports")
    if not isinstance(target, str) or not TARGET_RE.match(target.strip()):
        raise ConnectorError("'target' contains invalid characters.", -32602)
    if mode not in {"ping", "top_ports"}:
        raise ConnectorError("'mode' must be 'ping' or 'top_ports'.", -32602)

    nmap = shutil.which("nmap")
    if not nmap:
        raise ConnectorError("'nmap' is not installed on this system.", -32000)

    flags = ["-sn"] if mode == "ping" else ["-sT", "--top-ports", "100", "-T4"]
    proc = subprocess.run([nmap, *flags, target.strip()], capture_output=True, text=True, timeout=60, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "nmap scan failed", -32000)

    return {"target": target.strip(), "mode": mode, "output": proc.stdout.strip()}


if __name__ == "__main__":
    server.run_stdio()
