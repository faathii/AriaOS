#!/usr/bin/env python3
"""Postman, Insomnia, DBeaver, and MySQL Workbench connector for AriaOS."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("dev-api-databases", "0.1.0")
ALLOWED_DEV_APPS = {"dbeaver", "mysql-workbench", "postman", "insomnia"}


@server.tool("http_get_preview")
def http_get_preview(params: dict[str, Any]) -> dict[str, Any]:
    raw_url = params.get("url")
    max_chars = params.get("max_chars", 2000)
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise ConnectorError("'url' must be a non-empty string.", -32602)
    parsed = urllib.parse.urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ConnectorError("Only http:// or https:// URLs are allowed.", -32602)
    if not isinstance(max_chars, int) or max_chars < 100 or max_chars > 10000:
        raise ConnectorError("'max_chars' must be between 100 and 10000.", -32602)

    req = urllib.request.Request(raw_url.strip(), method="GET", headers={"User-Agent": "AriaOS/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            body = resp.read(max_chars + 1).decode("utf-8", errors="replace")
            return {
                "url": raw_url.strip(),
                "status": resp.status,
                "content_type": resp.headers.get("Content-Type", ""),
                "truncated": len(body) > max_chars,
                "body_preview": body[:max_chars],
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectorError(f"HTTP GET failed: {exc}", -32000) from exc


@server.tool("list_db_connections")
def list_db_connections(params: dict[str, Any]) -> dict[str, Any]:
    raw_cfg = params.get("config_path")
    connections: list[dict[str, str]] = []

    candidates: list[Path] = []
    if raw_cfg is not None:
        if not isinstance(raw_cfg, str) or not raw_cfg.strip():
            raise ConnectorError("'config_path' must be a non-empty string.", -32602)
        p = Path(raw_cfg).expanduser().resolve()
        if not p.is_file():
            raise ConnectorError(f"Config file not found: {p}", -32602)
        candidates.append(p)
    else:
        candidates.extend(Path.home().glob(".local/share/DBeaverData/workspace*/General/.dbeaver/data-sources.json"))
        wb = Path.home() / ".mysql" / "workbench" / "connections.xml"
        if wb.is_file():
            candidates.append(wb)

    for path in candidates:
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for cid, entry in data.get("connections", {}).items():
                    cfg = entry.get("configuration", {})
                    connections.append(
                        {
                            "source": "dbeaver",
                            "id": cid,
                            "name": str(entry.get("name", "")),
                            "provider": str(entry.get("provider", "")),
                            "host": str(cfg.get("host", "")),
                            "port": str(cfg.get("port", "")),
                            "database": str(cfg.get("database", "")),
                        }
                    )
            except (OSError, json.JSONDecodeError):
                continue
        elif path.suffix.lower() == ".xml":
            try:
                root = ET.parse(path).getroot()
                for val in root.findall(".//value[@struct-name='db.mgmt.Connection']"):
                    name = val.findtext("value[@key='name']", default="")
                    if name:
                        connections.append({"source": "mysql-workbench", "name": name})
            except ET.ParseError:
                continue

    return {"count": len(connections), "connections": connections}


@server.tool("launch_dev_client")
def launch_dev_client(params: dict[str, Any]) -> dict[str, Any]:
    app = params.get("app")
    if not isinstance(app, str) or app not in ALLOWED_DEV_APPS:
        raise ConnectorError(f"'app' must be one of: {', '.join(sorted(ALLOWED_DEV_APPS))}", -32602)

    binary = shutil.which(app)
    if not binary:
        raise ConnectorError(f"'{app}' is not installed on this system.", -32000)

    proc = subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "app": app, "pid": proc.pid}


if __name__ == "__main__":
    server.run_stdio()
