#!/usr/bin/env python3
"""Docker, Podman, Portainer, VirtualBox, and QEMU/KVM connector for AriaOS."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer("dev-containers-vm", "0.1.0")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _pick_runtime(runtime: Any) -> str:
    if runtime not in {"auto", "docker", "podman"}:
        raise ConnectorError("'runtime' must be 'auto', 'docker', or 'podman'.", -32602)
    candidates = ["docker", "podman"] if runtime == "auto" else [runtime]
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    raise ConnectorError(f"Container runtime not installed ({', '.join(candidates)}).", -32000)


@server.tool("container_list")
def container_list(params: dict[str, Any]) -> dict[str, Any]:
    rt = _pick_runtime(params.get("runtime", "auto"))
    proc = subprocess.run([rt, "ps", "-a", "--format", "{{json .}}"], capture_output=True, text=True, timeout=15, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or f"{Path(rt).name} ps failed", -32000)

    items = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return {"runtime": Path(rt).name, "count": len(items), "containers": items}


@server.tool("container_logs")
def container_logs(params: dict[str, Any]) -> dict[str, Any]:
    container = params.get("container")
    tail = params.get("tail", 50)
    if not isinstance(container, str) or not SAFE_NAME_RE.match(container.strip()):
        raise ConnectorError("'container' contains invalid characters.", -32602)
    if not isinstance(tail, int) or tail < 1 or tail > 300:
        raise ConnectorError("'tail' must be between 1 and 300.", -32602)

    rt = _pick_runtime(params.get("runtime", "auto"))
    proc = subprocess.run(
        [rt, "logs", "--tail", str(tail), container.strip()],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or f"Failed reading logs for {container}", -32000)
    return {"runtime": Path(rt).name, "container": container.strip(), "logs": (proc.stdout + proc.stderr).strip()}


@server.tool("vm_list")
def vm_list(params: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"virtualbox": [], "libvirt": []}

    vbox = shutil.which("VBoxManage")
    if vbox:
        proc = subprocess.run([vbox, "list", "vms"], capture_output=True, text=True, timeout=10, check=False)
        if proc.returncode == 0:
            result["virtualbox"] = [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    virsh = shutil.which("virsh")
    if virsh:
        proc = subprocess.run([virsh, "list", "--all", "--name"], capture_output=True, text=True, timeout=10, check=False)
        if proc.returncode == 0:
            result["libvirt"] = [line.strip() for line in proc.stdout.splitlines() if line.strip()]

    return result


@server.tool("vm_power")
def vm_power(params: dict[str, Any]) -> dict[str, Any]:
    hypervisor = params.get("hypervisor")
    name = params.get("name")
    action = params.get("action")
    if hypervisor not in {"virtualbox", "libvirt"}:
        raise ConnectorError("'hypervisor' must be 'virtualbox' or 'libvirt'.", -32602)
    if not isinstance(name, str) or not SAFE_NAME_RE.match(name.strip()):
        raise ConnectorError("'name' contains invalid characters.", -32602)
    if action not in {"start", "shutdown"}:
        raise ConnectorError("'action' must be 'start' or 'shutdown'.", -32602)

    if hypervisor == "virtualbox":
        vbox = shutil.which("VBoxManage")
        if not vbox:
            raise ConnectorError("VirtualBox ('VBoxManage') is not installed.", -32000)
        cmd = [vbox, "startvm", name.strip(), "--type", "headless"] if action == "start" else [vbox, "controlvm", name.strip(), "acpipowerbutton"]
    else:
        virsh = shutil.which("virsh")
        if not virsh:
            raise ConnectorError("libvirt ('virsh') is not installed.", -32000)
        cmd = [virsh, "start", name.strip()] if action == "start" else [virsh, "shutdown", name.strip()]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    if proc.returncode != 0:
        raise ConnectorError(proc.stderr.strip() or proc.stdout.strip() or "VM power operation failed", -32000)
    return {"hypervisor": hypervisor, "name": name.strip(), "action": action, "output": proc.stdout.strip()}


if __name__ == "__main__":
    server.run_stdio()
