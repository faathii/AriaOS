"""AriaOS `os-desktop` connector: KDE Plasma / FreeDesktop session control."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

DESKTOP_ID_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
server = ConnectorServer(connector_id="os-desktop", version="0.1.0")


def _has_graphical_session() -> bool:
    return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


@server.tool("desktop_environment_info")
def desktop_environment_info(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Report current desktop session and available IPC/CLI bridges."""
    return {
        "has_graphical_session": _has_graphical_session(),
        "xdg_current_desktop": os.environ.get("XDG_CURRENT_DESKTOP"),
        "xdg_session_type": os.environ.get("XDG_SESSION_TYPE"),
        "wayland_display": os.environ.get("WAYLAND_DISPLAY"),
        "display": os.environ.get("DISPLAY"),
        "available_tools": {
            "notify_send": bool(shutil.which("notify-send")),
            "gtk_launch": bool(shutil.which("gtk-launch")),
            "qdbus6": bool(shutil.which("qdbus6")),
            "wl_copy": bool(shutil.which("wl-copy")),
        },
    }


@server.tool("send_notification")
def send_notification(args: Dict[str, Any]) -> Dict[str, Any]:
    """Send a notification using notify-send when a graphical session is active."""
    title = str(args.get("title", "")).strip()
    body = str(args.get("body", "")).strip()
    if not title or not body:
        raise ConnectorError("Both 'title' and 'body' are required", code=-32602)
    if not _has_graphical_session():
        raise ConnectorError("No active graphical desktop session (DISPLAY/WAYLAND_DISPLAY unset)")
    if not shutil.which("notify-send"):
        raise ConnectorError("'notify-send' not installed (install libnotify)")

    res = subprocess.run(["notify-send", title, body], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise ConnectorError(res.stderr.strip() or "Failed to send notification")
    return {"sent": True, "title": title}


@server.tool("launch_application")
def launch_application(args: Dict[str, Any]) -> Dict[str, Any]:
    """Launch a desktop entry asynchronously via gtk-launch."""
    desktop_id = args.get("desktop_id")
    if not isinstance(desktop_id, str) or not DESKTOP_ID_RE.match(desktop_id):
        raise ConnectorError("Invalid desktop_id", code=-32602)
    if not _has_graphical_session():
        raise ConnectorError("No active graphical desktop session (DISPLAY/WAYLAND_DISPLAY unset)")
    if not shutil.which("gtk-launch"):
        raise ConnectorError("'gtk-launch' not installed")

    subprocess.Popen(
        ["gtk-launch", desktop_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return {"launched": True, "desktop_id": desktop_id}


if __name__ == "__main__":
    server.run_stdio()

