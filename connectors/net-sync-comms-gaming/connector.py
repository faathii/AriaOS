#!/usr/bin/env python3
"""Syncthing, qBittorrent, Comms, Streaming & Gaming connector for AriaOS."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("net-sync-comms-gaming", "0.1.0")

APP_BINARIES: dict[str, list[str]] = {
    "steam": ["steam"],
    "heroic": ["heroic", "heroic-games-launcher"],
    "lutris": ["lutris"],
    "retroarch": ["retroarch"],
    "pcsx2": ["pcsx2-qt", "pcsx2"],
    "rpcs3": ["rpcs3"],
    "duckstation": ["duckstation-qt", "duckstation"],
    "stremio": ["stremio"],
    "freetube": ["freetube"],
    "spotify": ["spotify"],
    "telegram-desktop": ["Telegram", "telegram-desktop"],
    "element-desktop": ["element-desktop"],
    "signal-desktop": ["signal-desktop"],
    "discord": ["discord"],
    "qbittorrent": ["qbittorrent"],
    "syncthing": ["syncthing"],
    "ventoy": ["ventoygui", "ventoy"],
    "stacer": ["stacer"],
    "gnome-tweaks": ["gnome-tweaks"],
}


@server.tool("ecosystem_apps_status")
def ecosystem_apps_status(params: dict[str, Any]) -> dict[str, Any]:
    installed = {
        app: any(shutil.which(cmd) for cmd in cmds)
        for app, cmds in APP_BINARIES.items()
    }
    return {"installed": installed}


@server.tool("syncthing_status")
def syncthing_status(params: dict[str, Any]) -> dict[str, Any]:
    port = params.get("port", 8384)
    api_key = params.get("api_key", "")
    if not isinstance(port, int) or port < 1024 or port > 65535:
        raise ConnectorError("'port' must be between 1024 and 65535.", -32602)

    headers = {"X-API-Key": api_key} if isinstance(api_key, str) and api_key.strip() else {}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/rest/system/status", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return {"status": json.loads(resp.read().decode("utf-8"))}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectorError(f"Syncthing REST API not reachable on port {port}: {exc}", -32000) from exc


@server.tool("qbittorrent_torrents")
def qbittorrent_torrents(params: dict[str, Any]) -> dict[str, Any]:
    port = params.get("port", 8080)
    if not isinstance(port, int) or port < 1024 or port > 65535:
        raise ConnectorError("'port' must be between 1024 and 65535.", -32602)

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v2/torrents/info", timeout=2.0) as resp:
            torrents = json.loads(resp.read().decode("utf-8"))
            summary = [
                {
                    "name": t.get("name"),
                    "state": t.get("state"),
                    "progress": t.get("progress"),
                    "size": t.get("size"),
                }
                for t in torrents[:50]
            ]
            return {"count": len(torrents), "torrents": summary}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ConnectorError(f"qBittorrent WebUI API not reachable on port {port}: {exc}", -32000) from exc


@server.tool("launch_ecosystem_app")
def launch_ecosystem_app(params: dict[str, Any]) -> dict[str, Any]:
    app = params.get("app")
    if not isinstance(app, str) or app not in APP_BINARIES:
        raise ConnectorError(f"'app' must be one of: {', '.join(sorted(APP_BINARIES))}", -32602)

    binary = next((shutil.which(cmd) for cmd in APP_BINARIES[app] if shutil.which(cmd)), None)
    if not binary:
        raise ConnectorError(f"'{app}' is not installed on this system.", -32000)

    proc = subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "app": app, "pid": proc.pid}


if __name__ == "__main__":
    server.run_stdio()
