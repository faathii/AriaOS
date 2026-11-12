"""OS-to-Desktop session bridge helpers for AriaOS connectors.

Allows system-level OS daemons (running as root) to seamlessly interact with the
active graphical user's KDE Plasma / Wayland / XDG environment without losing
OS/kernel privileges.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

try:
    import pwd
except ImportError:  # Windows
    pwd = None  # type: ignore[assignment]


@dataclass(frozen=True)
class DesktopContext:
    uid: Optional[int]
    gid: Optional[int]
    username: str
    home: Path
    xdg_data_home: Path
    xdg_runtime_dir: Optional[Path]
    env: Dict[str, str]


def _is_root_posix() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def _read_session_env_from_proc(uid: int) -> Dict[str, str]:
    """Read Wayland/Display/D-Bus variables from an active user Plasma/graphical process."""
    wanted = ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR", "XDG_CURRENT_DESKTOP")
    discovered: Dict[str, str] = {}
    proc_root = Path("/proc")
    if not proc_root.exists():
        return discovered

    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            comm = (entry / "comm").read_text(encoding="utf-8", errors="ignore").strip()
            if comm not in {"plasmashell", "kwin_wayland", "kwin_x11", "startplasma-wayland", "systemd"}:
                continue
            raw_env = (entry / "environ").read_bytes()
        except OSError:
            continue
        for chunk in raw_env.split(b"\x00"):
            if b"=" not in chunk:
                continue
            k_b, v_b = chunk.split(b"=", 1)
            key = k_b.decode("utf-8", errors="ignore")
            if key in wanted and key not in discovered:
                discovered[key] = v_b.decode("utf-8", errors="ignore")
        if "DBUS_SESSION_BUS_ADDRESS" in discovered and (
            "WAYLAND_DISPLAY" in discovered or "DISPLAY" in discovered
        ):
            break
    return discovered


def resolve_desktop_context(target_path: Optional[Path] = None) -> DesktopContext:
    """Resolve user XDG and Wayland/D-Bus desktop context for current user or OS root."""
    explicit_data_home = os.environ.get("XDG_DATA_HOME")

    if not _is_root_posix() or pwd is None:
        home = Path.home()
        xdg_data = Path(explicit_data_home).expanduser() if explicit_data_home else home / ".local" / "share"
        runtime = Path(os.environ["XDG_RUNTIME_DIR"]) if "XDG_RUNTIME_DIR" in os.environ else None
        uid = os.getuid() if hasattr(os, "getuid") else None
        gid = os.getgid() if hasattr(os, "getgid") else None
        return DesktopContext(
            uid=uid,
            gid=gid,
            username=os.environ.get("USER", "user"),
            home=home,
            xdg_data_home=xdg_data,
            xdg_runtime_dir=runtime,
            env=dict(os.environ),
        )

    # Running as OS root: pick owner of target_path (if non-root), or UID 1000 ('aria'), or active /run/user/<uid>.
    chosen_pw = None
    if target_path is not None and target_path.exists():
        try:
            owner_uid = target_path.stat().st_uid
            if owner_uid >= 1000:
                chosen_pw = pwd.getpwuid(owner_uid)
        except (OSError, KeyError):
            pass

    if chosen_pw is None:
        run_user = Path("/run/user")
        if run_user.exists():
            for subdir in sorted(run_user.iterdir()):
                if subdir.name.isdigit() and int(subdir.name) >= 1000:
                    try:
                        chosen_pw = pwd.getpwuid(int(subdir.name))
                        break
                    except KeyError:
                        continue

    if chosen_pw is None:
        try:
            chosen_pw = pwd.getpwnam("aria")
        except KeyError:
            chosen_pw = pwd.getpwuid(0)

    home = Path(chosen_pw.pw_dir)
    xdg_data = Path(explicit_data_home).expanduser() if explicit_data_home else home / ".local" / "share"
    runtime_dir = Path(f"/run/user/{chosen_pw.pw_uid}")
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USER"] = chosen_pw.pw_name
    env["LOGNAME"] = chosen_pw.pw_name
    env["XDG_DATA_HOME"] = str(xdg_data)

    if runtime_dir.exists():
        env.setdefault("XDG_RUNTIME_DIR", str(runtime_dir))
        bus = runtime_dir / "bus"
        if bus.exists():
            env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={bus}")
        wayland_sock = runtime_dir / "wayland-0"
        if wayland_sock.exists():
            env.setdefault("WAYLAND_DISPLAY", "wayland-0")

    proc_env = _read_session_env_from_proc(chosen_pw.pw_uid)
    env.update(proc_env)
    env.setdefault("DISPLAY", ":0")

    return DesktopContext(
        uid=chosen_pw.pw_uid,
        gid=chosen_pw.pw_gid,
        username=chosen_pw.pw_name,
        home=home,
        xdg_data_home=xdg_data,
        xdg_runtime_dir=runtime_dir if runtime_dir.exists() else None,
        env=env,
    )


def chown_for_context(path: Path, ctx: DesktopContext) -> None:
    """When running as OS root, align ownership of user-layer files with the desktop user."""
    if _is_root_posix() and ctx.uid is not None and ctx.gid is not None and ctx.uid != 0:
        try:
            os.chown(path, ctx.uid, ctx.gid)
        except OSError:
            pass


def launch_in_desktop_session(cmd: List[str], ctx: DesktopContext) -> subprocess.Popen[bytes]:
    """Launch a graphical desktop command inside the target user's Plasma/Wayland session."""
    kwargs: Dict[str, object] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": ctx.env,
        "start_new_session": True,
    }
    if _is_root_posix() and ctx.uid is not None and ctx.gid is not None and ctx.uid != 0:
        kwargs["user"] = ctx.uid
        kwargs["group"] = ctx.gid
    return subprocess.Popen(cmd, **kwargs)  # type: ignore[arg-type]

