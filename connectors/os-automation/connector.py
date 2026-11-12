"""AriaOS `os-automation` connector: Neural Memory management & scheduled OS automations."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "core" / "sdk" / "python"))

from aria_sdk import ConnectorError, ConnectorServer  # noqa: E402

server = ConnectorServer(connector_id="os-automation", version="0.1.0")

DEFAULT_SCHEDULES: Dict[str, Dict[str, Any]] = {
    "auto_ram_purge": {
        "id": "auto_ram_purge",
        "name": "Compactación Autonómica de RAM & ZRAM",
        "icon": "⚡",
        "enabled": True,
        "interval": "15m",
        "command": "aria-daemon optimize",
        "description": "Libera pagecache y compacta bloques de memoria si la presión PSI supera el umbral.",
    },
    "auto_av_scan": {
        "id": "auto_av_scan",
        "name": "Auditoría Rápida de Descargas (Aria Shield)",
        "icon": "🛡️",
        "enabled": True,
        "interval": "6h",
        "command": "ariaos-av-scan ~/Downloads",
        "description": "Inspecciona silenciosamente la carpeta de Descargas con heurística YARA + SHA-256.",
    },
    "auto_pkg_sync": {
        "id": "auto_pkg_sync",
        "name": "Verificación de Actualizaciones del Sistema",
        "icon": "📦",
        "enabled": False,
        "interval": "24h",
        "command": "pacman -Qu",
        "description": "Comprueba en segundo plano si existen parches de seguridad o paquetes actualizables.",
    },
    "auto_trim_ssd": {
        "id": "auto_trim_ssd",
        "name": "Optimización NVMe / SSD (fstrim)",
        "icon": "💾",
        "enabled": True,
        "interval": "24h",
        "command": "fstrim -av",
        "description": "Mantiene el rendimiento máximo de lectura/escritura en unidades SSD y NVMe.",
    },
}

DEFAULT_PRETRAINED_RULES: List[Dict[str, Any]] = [
    {
        "trigger": "modo gaming",
        "target_prompt": "activar perfil gaming",
        "hits": 1,
    },
    {
        "trigger": "modo desarrollo",
        "target_prompt": "activar perfil desarrollo",
        "hits": 1,
    },
    {
        "trigger": "modo creativo",
        "target_prompt": "activar perfil creativo",
        "hits": 1,
    },
    {
        "trigger": "modo ahorro extremo",
        "target_prompt": "activar perfil ahorro",
        "hits": 1,
    },
    {
        "trigger": "modo seguridad",
        "target_prompt": "activar perfil seguridad",
        "hits": 1,
    },
    {
        "trigger": "limpieza profunda",
        "target_prompt": "optimizar ram",
        "hits": 1,
    },
]


def _data_dir() -> Path:
    home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/tmp"
    d = Path(home) / ".local" / "share" / "ariaos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _memory_path() -> Path:
    custom = os.environ.get("ARIAOS_MEMORY_PATH")
    if custom:
        return Path(custom)
    return _data_dir() / "neural_memory.json"


def _schedule_path() -> Path:
    return _data_dir() / "scheduled_tasks.json"


def _load_memory() -> Dict[str, Any]:
    path = _memory_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if "learned_rules" in data and "rules" not in data:
                    data["rules"] = data.pop("learned_rules")
                data.setdefault("rules", list(DEFAULT_PRETRAINED_RULES))
                data.setdefault("command_habits", {})
                data.setdefault("total_interactions", 0)
                return data
        except Exception:
            pass
    default_mem = {
        "rules": list(DEFAULT_PRETRAINED_RULES),
        "command_habits": {"kernel_telemetry": 5, "optimize_kernel_memory": 3},
        "total_interactions": 8,
    }
    try:
        path.write_text(json.dumps(default_mem, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return default_mem


def _save_memory(mem: Dict[str, Any]) -> None:
    try:
        _memory_path().write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise ConnectorError(f"Failed to write neural_memory.json: {exc}", code=-32000)


def _load_schedules() -> Dict[str, Dict[str, Any]]:
    path = _schedule_path()
    schedules = {k: dict(v) for k, v in DEFAULT_SCHEDULES.items()}
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                for k, v in saved.items():
                    if k in schedules and isinstance(v, dict):
                        schedules[k].update(v)
        except Exception:
            pass
    return schedules


def _save_schedules(schedules: Dict[str, Dict[str, Any]]) -> None:
    try:
        _schedule_path().write_text(
            json.dumps(schedules, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        raise ConnectorError(f"Failed to write scheduled_tasks.json: {exc}", code=-32000)


@server.tool("list_automations")
def list_automations(_args: Dict[str, Any]) -> Dict[str, Any]:
    mem = _load_memory()
    schedules = _load_schedules()
    return {
        "neural_memory": mem,
        "scheduled_tasks": list(schedules.values()),
    }


@server.tool("teach_rule")
def teach_rule(args: Dict[str, Any]) -> Dict[str, Any]:
    trigger = str(args.get("trigger", "")).strip().lower()
    action = str(args.get("action", "")).strip()
    if len(trigger) < 2 or len(action) < 2:
        raise ConnectorError("Both 'trigger' and 'action' must be at least 2 characters.", code=-32602)

    mem = _load_memory()
    rules: List[Dict[str, Any]] = mem.get("rules", [])
    updated = False
    for r in rules:
        if r.get("trigger") == trigger:
            r["target_prompt"] = action
            r["hits"] = int(r.get("hits", 0)) + 1
            updated = True
            break
    if not updated:
        rules.append(
            {
                "trigger": trigger,
                "target_prompt": action,
                "hits": 1,
            }
        )
    mem["rules"] = rules
    _save_memory(mem)
    return {
        "saved": True,
        "trigger": trigger,
        "action": action,
        "total_rules": len(rules),
    }


@server.tool("delete_rule")
def delete_rule(args: Dict[str, Any]) -> Dict[str, Any]:
    trigger = str(args.get("trigger", "")).strip().lower()
    if not trigger:
        raise ConnectorError("Missing 'trigger'.", code=-32602)

    mem = _load_memory()
    rules: List[Dict[str, Any]] = mem.get("rules", [])
    new_rules = [r for r in rules if r.get("trigger") != trigger]
    removed = len(rules) - len(new_rules)
    mem["rules"] = new_rules
    _save_memory(mem)
    return {
        "deleted": removed > 0,
        "trigger": trigger,
        "remaining_rules": len(new_rules),
    }


@server.tool("configure_schedule")
def configure_schedule(args: Dict[str, Any]) -> Dict[str, Any]:
    task_id = str(args.get("task_id", "")).strip()
    schedules = _load_schedules()
    if task_id not in schedules:
        raise ConnectorError(f"Unknown task_id: {task_id}", code=-32602)

    enabled = bool(args.get("enabled", True))
    interval = str(args.get("interval") or schedules[task_id].get("interval", "1h")).strip()
    if interval not in {"15m", "1h", "6h", "24h"}:
        raise ConnectorError(f"Unsupported interval: {interval}", code=-32602)

    schedules[task_id]["enabled"] = enabled
    schedules[task_id]["interval"] = interval
    _save_schedules(schedules)
    return {
        "updated": True,
        "task": schedules[task_id],
    }


if __name__ == "__main__":
    server.run_stdio()
