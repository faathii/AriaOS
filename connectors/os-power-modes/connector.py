"""AriaOS `os-power-modes` connector: Kernel work profiles & real-time GPU telemetry."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="os-power-modes", version="0.1.0")

WORK_MODES: Dict[str, Dict[str, Any]] = {
    "gaming": {
        "id": "gaming",
        "name": "Modo Gaming Ultra-Low Latency",
        "icon": "🎮",
        "cpu_governor": "performance",
        "swappiness": 10,
        "vfs_cache_pressure": 50,
        "drop_caches": True,
        "brightness_pct": 100,
        "apps": ["steam", "lutris", "gamemode"],
        "description": "Gobernador CPU en performance, purga de cachés de RAM, swappiness=10, latencia mínima de E/S y lanzamiento de gaming suite.",
    },
    "development": {
        "id": "development",
        "name": "Modo Desarrollo & Compilación",
        "icon": "💻",
        "cpu_governor": "schedutil",
        "swappiness": 30,
        "vfs_cache_pressure": 60,
        "drop_caches": True,
        "brightness_pct": 85,
        "apps": ["codium", "xfce4-terminal"],
        "description": "Optimiza cachés de sistema de archivos para compilaciones rápidas (Rust/C++/Python), libera RAM inactiva y abre VSCodium + Terminal.",
    },
    "creative": {
        "id": "creative",
        "name": "Modo Estudio Creativo & Render",
        "icon": "🎨",
        "cpu_governor": "performance",
        "swappiness": 20,
        "vfs_cache_pressure": 50,
        "drop_caches": True,
        "brightness_pct": 95,
        "apps": ["kdenlive", "obs", "gimp", "blender"],
        "description": "Prioriza ancho de banda de memoria y CPU para renderizado 3D, vídeo y audio PipeWire sin cortes.",
    },
    "powersave": {
        "id": "powersave",
        "name": "Modo Ahorro Extremo & Silencio",
        "icon": "🔋",
        "cpu_governor": "powersave",
        "swappiness": 100,
        "vfs_cache_pressure": 100,
        "drop_caches": True,
        "brightness_pct": 40,
        "apps": [],
        "description": "Activa gobernador powersave, maximiza compresión en ZRAM (swappiness=100), compacta memoria y reduce el brillo al 40%.",
    },
    "security": {
        "id": "security",
        "name": "Modo Fortaleza & Auditoría",
        "icon": "🛡️",
        "cpu_governor": "schedutil",
        "swappiness": 40,
        "vfs_cache_pressure": 80,
        "drop_caches": False,
        "brightness_pct": 80,
        "apps": ["ariaos-antivirus"],
        "description": "Activa vigilancia con Aria Shield Antivirus y prioriza integridad del sistema y red.",
    },
    "balanced": {
        "id": "balanced",
        "name": "Modo Equilibrado Autonómico",
        "icon": "⚡",
        "cpu_governor": "schedutil",
        "swappiness": 60,
        "vfs_cache_pressure": 80,
        "drop_caches": False,
        "brightness_pct": 75,
        "apps": [],
        "description": "Ajuste dinámico gobernado por el motor autonómico del kernel según carga PSI.",
    },
}


def _state_file() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp"
    p = Path(home) / ".local" / "share" / "ariaos" / "active_work_mode.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return None


def _current_cpu_governor() -> str:
    gov_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    return _read_text(gov_path) or "schedutil (virtual/host)"


@server.tool("list_work_modes")
def list_work_modes(_args: Dict[str, Any]) -> Dict[str, Any]:
    state_path = _state_file()
    active = "balanced"
    updated_at = 0
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            active = data.get("active_mode", "balanced")
            updated_at = data.get("updated_at", 0)
        except Exception:
            pass
    return {
        "active_mode": active,
        "updated_at": updated_at,
        "current_cpu_governor": _current_cpu_governor(),
        "modes": WORK_MODES,
    }


@server.tool("apply_work_mode")
def apply_work_mode(args: Dict[str, Any]) -> Dict[str, Any]:
    mode_id = str(args.get("mode", "")).strip().lower()
    if mode_id not in WORK_MODES:
        raise ConnectorError(f"Unsupported work mode: {mode_id}", code=-32602)
    launch_apps = bool(args.get("launch_apps", True))
    profile = WORK_MODES[mode_id]
    actions_taken: List[str] = []

    # 1. Tune CPU scaling governor if accessible
    cpu_root = Path("/sys/devices/system/cpu")
    if cpu_root.exists():
        tuned_cpus = 0
        for gov_file in cpu_root.glob("cpu[0-9]*/cpufreq/scaling_governor"):
            try:
                gov_file.write_text(profile["cpu_governor"] + "\n", encoding="utf-8")
                tuned_cpus += 1
            except OSError:
                break
        if tuned_cpus > 0:
            actions_taken.append(f"cpu_governor={profile['cpu_governor']} ({tuned_cpus} cores)")

    # 2. Tune VM sysctl parameters if accessible
    for key, val in (
        ("swappiness", profile["swappiness"]),
        ("vfs_cache_pressure", profile["vfs_cache_pressure"]),
    ):
        sys_file = Path(f"/proc/sys/vm/{key}")
        try:
            if sys_file.exists():
                sys_file.write_text(f"{val}\n", encoding="utf-8")
                actions_taken.append(f"vm.{key}={val}")
        except OSError:
            pass

    if profile.get("drop_caches"):
        for sys_name, val in (("drop_caches", "3"), ("compact_memory", "1")):
            try:
                p = Path(f"/proc/sys/vm/{sys_name}")
                if p.exists():
                    p.write_text(f"{val}\n", encoding="utf-8")
                    actions_taken.append(f"vm.{sys_name}={val}")
            except OSError:
                pass

    # 3. Adjust brightness if brightnessctl is available and mode is powersave
    if mode_id == "powersave" and shutil.which("brightnessctl"):
        try:
            subprocess.run(
                ["brightnessctl", "set", f"{profile['brightness_pct']}%"],
                capture_output=True,
                timeout=3,
            )
            actions_taken.append(f"brightness={profile['brightness_pct']}%")
        except Exception:
            pass

    # 4. Launch primary workspace apps if requested and installed
    launched: List[str] = []
    if launch_apps:
        for app_bin in profile.get("apps", []):
            if shutil.which(app_bin):
                try:
                    subprocess.Popen(
                        [app_bin],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    launched.append(app_bin)
                    if len(launched) >= 2:
                        break
                except OSError:
                    pass

    # 5. Persist active state
    state_payload = {
        "active_mode": mode_id,
        "name": profile["name"],
        "icon": profile["icon"],
        "updated_at": int(time.time()),
        "actions_taken": actions_taken,
        "launched_apps": launched,
    }
    try:
        _state_file().write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
    except OSError:
        pass

    return {
        "applied": True,
        "mode": mode_id,
        "name": profile["name"],
        "icon": profile["icon"],
        "description": profile["description"],
        "kernel_actions": actions_taken,
        "launched_apps": launched,
    }


@server.tool("gpu_telemetry")
def gpu_telemetry(_args: Dict[str, Any]) -> Dict[str, Any]:
    gpus: List[Dict[str, Any]] = []

    # 1. Check /sys/class/drm/card*
    drm_root = Path("/sys/class/drm")
    if drm_root.exists():
        for card in sorted(drm_root.glob("card[0-9]")):
            dev = card / "device"
            vendor = _read_text(dev / "vendor") or "unknown"
            device_id = _read_text(dev / "device") or "unknown"
            busy_pct = _read_text(dev / "gpu_busy_percent")
            vram_used = _read_text(dev / "mem_info_vram_used")
            vram_total = _read_text(dev / "mem_info_vram_total")
            driver = ""
            driver_link = dev / "driver"
            if driver_link.is_symlink():
                try:
                    driver = driver_link.resolve().name
                except OSError:
                    driver = ""
            gpus.append(
                {
                    "card": card.name,
                    "vendor_id": vendor,
                    "device_id": device_id,
                    "driver": driver or "drm",
                    "busy_pct": int(busy_pct) if busy_pct and busy_pct.isdigit() else 0,
                    "vram_used_mb": int(vram_used) // (1024 * 1024)
                    if vram_used and vram_used.isdigit()
                    else None,
                    "vram_total_mb": int(vram_total) // (1024 * 1024)
                    if vram_total and vram_total.isdigit()
                    else None,
                }
            )

    # 2. Check nvidia-smi if available
    if shutil.which("nvidia-smi"):
        try:
            proc = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                capture_output=True,
                timeout=4,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        gpus.append(
                            {
                                "card": parts[0],
                                "driver": "nvidia",
                                "busy_pct": int(parts[1]) if parts[1].isdigit() else 0,
                                "vram_used_mb": int(parts[2]) if parts[2].isdigit() else 0,
                                "vram_total_mb": int(parts[3]) if parts[3].isdigit() else 0,
                                "temp_c": int(parts[4]) if parts[4].isdigit() else None,
                            }
                        )
        except Exception:
            pass

    # 3. Fallback description via lspci
    pci_gpus: List[str] = []
    if shutil.which("lspci"):
        try:
            proc = subprocess.run(["lspci"], text=True, capture_output=True, timeout=4)
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    low = line.lower()
                    if "vga" in low or "3d controller" in low or "display" in low:
                        pci_gpus.append(line.strip())
        except Exception:
            pass

    return {
        "gpu_count": len(gpus) or len(pci_gpus),
        "adapters": gpus,
        "pci_display_controllers": pci_gpus,
    }


if __name__ == "__main__":
    server.run_stdio()

