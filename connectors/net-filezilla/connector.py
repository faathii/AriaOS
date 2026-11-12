#!/usr/bin/env python3
"""FileZilla & SFTP connector for AriaOS."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("net-filezilla", "0.1.0")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@server.tool("list_sites")
def list_sites(params: dict[str, Any]) -> dict[str, Any]:
    raw_xml = params.get("xml_path")
    if raw_xml is not None:
        if not isinstance(raw_xml, str) or not raw_xml.strip():
            raise ConnectorError("'xml_path' must be a non-empty string.", -32602)
        xml_path = Path(raw_xml).expanduser().resolve()
    else:
        xml_path = Path.home() / ".config" / "filezilla" / "sitemanager.xml"

    if not xml_path.is_file():
        raise ConnectorError(f"FileZilla sitemanager.xml not found: {xml_path}", -32000)

    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as exc:
        raise ConnectorError(f"Invalid sitemanager.xml: {exc}", -32602) from exc

    sites: list[dict[str, str]] = []
    for elem in tree.getroot().iter("Server"):
        sites.append(
            {
                "name": elem.findtext("Name", default="").strip(),
                "host": elem.findtext("Host", default="").strip(),
                "port": elem.findtext("Port", default="").strip(),
                "protocol": elem.findtext("Protocol", default="").strip(),
                "user": elem.findtext("User", default="").strip(),
                "remote_dir": elem.findtext("RemoteDir", default="").strip(),
            }
        )
    return {"xml_path": str(xml_path), "count": len(sites), "sites": sites}


@server.tool("list_remote_dir")
def list_remote_dir(params: dict[str, Any]) -> dict[str, Any]:
    host = params.get("host")
    user = params.get("user")
    port = params.get("port", 22)
    remote_path = params.get("remote_path", ".")

    if not isinstance(host, str) or not SAFE_TOKEN_RE.match(host.strip()):
        raise ConnectorError("'host' contains invalid characters.", -32602)
    if not isinstance(user, str) or not SAFE_TOKEN_RE.match(user.strip()):
        raise ConnectorError("'user' contains invalid characters.", -32602)
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ConnectorError("'port' must be between 1 and 65535.", -32602)
    if not isinstance(remote_path, str) or "\n" in remote_path or "\r" in remote_path:
        raise ConnectorError("'remote_path' must be a single-line string.", -32602)

    sftp = shutil.which("sftp")
    if not sftp:
        raise ConnectorError("'sftp' client is not installed on this system.", -32000)

    target = f"{user.strip()}@{host.strip()}"
    cmd = [sftp, "-P", str(port), "-o", "BatchMode=yes", "-b", "-", target]
    proc = subprocess.run(
        cmd,
        input=f"ls -la {remote_path.strip() or '.'}\n",
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or "sftp listing failed", -32000)

    return {"target": target, "port": port, "remote_path": remote_path, "output": proc.stdout.strip()}


if __name__ == "__main__":
    server.run_stdio()
