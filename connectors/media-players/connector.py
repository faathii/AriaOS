#!/usr/bin/env python3
"""Media players connector for AriaOS (VLC / Elisa via MPRIS2 D-Bus + launcher)."""

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

server = ConnectorServer("media-players", "0.1.0")

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
MPRIS_PATH = "/org/mpris/MediaPlayer2"
MPRIS_PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"
ALLOWED_ACTIONS = {"Play", "Pause", "PlayPause", "Next", "Previous", "Stop"}
ALLOWED_PLAYERS = {"auto", "vlc", "elisa"}
SERVICE_RE = re.compile(r"^org\.mpris\.MediaPlayer2\.[A-Za-z0-9_.-]+$")


def _validate_service(service: Any) -> str:
    if not isinstance(service, str) or not SERVICE_RE.match(service.strip()):
        raise ConnectorError("'service' must match 'org.mpris.MediaPlayer2.<player>'.", -32602)
    return service.strip()


def _qdbus_bin() -> str | None:
    return shutil.which("qdbus6") or shutil.which("qdbus")


def _dbus_list_mpris() -> list[str]:
    qdbus = _qdbus_bin()
    if qdbus:
        proc = subprocess.run([qdbus], capture_output=True, text=True, timeout=5, check=False)
        if proc.returncode == 0:
            return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip().startswith(MPRIS_PREFIX))

    gdbus = shutil.which("gdbus")
    if gdbus:
        proc = subprocess.run(
            [
                gdbus,
                "call",
                "--session",
                "--dest",
                "org.freedesktop.DBus",
                "--object-path",
                "/org/freedesktop/DBus",
                "--method",
                "org.freedesktop.DBus.ListNames",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode == 0:
            return sorted(set(re.findall(r"org\.mpris\.MediaPlayer2\.[A-Za-z0-9_.-]+", proc.stdout)))

    raise ConnectorError("Neither qdbus6/qdbus nor gdbus is available to query session D-Bus.", -32000)


@server.tool("list_players")
def list_players(params: dict[str, Any]) -> dict[str, Any]:
    services = _dbus_list_mpris()
    return {"count": len(services), "players": services}


@server.tool("get_playback_status")
def get_playback_status(params: dict[str, Any]) -> dict[str, Any]:
    service = _validate_service(params.get("service"))
    qdbus = _qdbus_bin()
    gdbus = shutil.which("gdbus")

    if qdbus:
        status_proc = subprocess.run(
            [qdbus, service, MPRIS_PATH, f"{MPRIS_PLAYER_IFACE}.PlaybackStatus"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if status_proc.returncode != 0:
            raise ConnectorError(status_proc.stderr.strip() or f"Failed to query {service}", -32000)
        meta_proc = subprocess.run(
            [qdbus, service, MPRIS_PATH, f"{MPRIS_PLAYER_IFACE}.Metadata"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return {
            "service": service,
            "playback_status": status_proc.stdout.strip(),
            "metadata_raw": meta_proc.stdout.strip() if meta_proc.returncode == 0 else "",
        }

    if gdbus:
        proc = subprocess.run(
            [
                gdbus,
                "call",
                "--session",
                "--dest",
                service,
                "--object-path",
                MPRIS_PATH,
                "--method",
                "org.freedesktop.DBus.Properties.GetAll",
                MPRIS_PLAYER_IFACE,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if proc.returncode != 0:
            raise ConnectorError(proc.stderr.strip() or f"Failed to query {service}", -32000)
        return {"service": service, "properties_raw": proc.stdout.strip()}

    raise ConnectorError("Neither qdbus6/qdbus nor gdbus is available.", -32000)


@server.tool("control_playback")
def control_playback(params: dict[str, Any]) -> dict[str, Any]:
    service = _validate_service(params.get("service"))
    action = params.get("action")
    if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
        raise ConnectorError(f"'action' must be one of: {', '.join(sorted(ALLOWED_ACTIONS))}", -32602)

    qdbus = _qdbus_bin()
    if qdbus:
        cmd = [qdbus, service, MPRIS_PATH, f"{MPRIS_PLAYER_IFACE}.{action}"]
    elif shutil.which("gdbus"):
        cmd = [
            "gdbus",
            "call",
            "--session",
            "--dest",
            service,
            "--object-path",
            MPRIS_PATH,
            "--method",
            f"{MPRIS_PLAYER_IFACE}.{action}",
        ]
    else:
        raise ConnectorError("Neither qdbus6/qdbus nor gdbus is available.", -32000)

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or f"MPRIS2 call failed for {service}.{action}", -32000)
    return {"service": service, "action": action, "ok": True}


@server.tool("play_media")
def play_media(params: dict[str, Any]) -> dict[str, Any]:
    raw_path = params.get("path")
    player = params.get("player", "auto")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorError("'path' must be a non-empty string.", -32602)
    if not isinstance(player, str) or player not in ALLOWED_PLAYERS:
        raise ConnectorError(f"'player' must be one of: {', '.join(sorted(ALLOWED_PLAYERS))}", -32602)

    media_path = Path(raw_path).expanduser().resolve()
    if not media_path.is_file():
        raise ConnectorError(f"Media file does not exist: {media_path}", -32602)

    candidates = ["vlc", "elisa"] if player == "auto" else [player]
    binary = next((shutil.which(name) for name in candidates if shutil.which(name)), None)
    if not binary:
        raise ConnectorError(f"Media player not installed ({', '.join(candidates)}).", -32000)

    proc = subprocess.Popen([binary, str(media_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "player": Path(binary).name, "pid": proc.pid, "path": str(media_path)}


if __name__ == "__main__":
    server.run_stdio()
