#!/usr/bin/env python3
"""
AriaOS Cyber Obsidian Desktop Environment Shell (AriaDE / ariaos-shell)
=======================================================================
Entorno de escritorio propio construido desde cero para AriaOS.
Reemplaza por completo a stock KDE `plasmashell` y `plasma-welcome`, ejecutándose
sobre el compositor acelerado `kwin` con cuatro componentes nativos propios:
  1. AriaDesktopCanvas : Lienzo de escritorio interactivo + Widgets Holográficos en vivo
  2. AriaTopBar        : Barra superior táctica con telemetría, escritorios virtuales y núcleo IA
  3. AriaCyberDock     : Dock inferior flotante estilo cristal oscuro con iconos SVG propios
  4. AriaAppLauncher   : Menú de aplicaciones holográfico con buscador y control de energía
"""

import configparser
import datetime
import glob
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Force XCB (X11 / XWayland) backend so global screen coordinates (setGeometry/move),
# WindowStaysOnBottomHint, WindowStaysOnTopHint, and EWMH struts work deterministically
# on both kwin_wayland (via XWayland) and kwin_x11.
if os.environ.get("DISPLAY"):
    os.environ["QT_QPA_PLATFORM"] = "xcb"

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QCursor,
    QFont,
    QGuiApplication,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
ICON_SEARCH_DIRS = [
    Path("/usr/share/icons/hicolor/scalable/apps"),
    Path("/usr/share/pixmaps"),
    REPO_ROOT / "assets" / "icons",
    REPO_ROOT / "assets" / "branding",
]
WALLPAPER_PATHS = [
    Path("/usr/share/wallpapers/AriaOS/contents/images/2816x1536.jpg"),
    REPO_ROOT / "assets" / "branding" / "ariaos-wallpaper.jpg",
]
STATE_FILE = Path.home() / ".config" / "ariaos_shell_state.json"

SUITE_APPS = [
    {
        "id": "installer",
        "name": "Instalar AriaOS",
        "subtitle": "Instalador NVMe / Disco",
        "cmd": "ariaos-installer",
        "icon": "ariaos-installer",
        "category": "sistema",
        "accent": "#00ff9d",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "command-bar",
        "name": "Aria Neural IA",
        "subtitle": "Barra de Comandos IA",
        "cmd": "aria-command-bar",
        "icon": "ariaos-command-bar",
        "category": "ia",
        "accent": "#00f0ff",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "ai-studio",
        "name": "Aria AI Studio",
        "subtitle": "Modelos Ollama & Prompts",
        "cmd": "ariaos-ai-studio",
        "icon": "ariaos-ai-studio",
        "category": "ia",
        "accent": "#ff007f",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "monitor",
        "name": "Monitor Kernel & GPU",
        "subtitle": "Telemetría y Procesos",
        "cmd": "ariaos-monitor",
        "icon": "ariaos-monitor",
        "category": "sistema",
        "accent": "#00ff9d",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "store",
        "name": "Tienda Cyber",
        "subtitle": "Gestor Visual de Paquetes",
        "cmd": "ariaos-store",
        "icon": "ariaos-store",
        "category": "sistema",
        "accent": "#00f0ff",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "firewall",
        "name": "Cortafuegos Cyber",
        "subtitle": "Control de Red & Puertos",
        "cmd": "ariaos-firewall",
        "icon": "ariaos-firewall",
        "category": "seguridad",
        "accent": "#ff0055",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "antivirus",
        "name": "Guardián Antivirus",
        "subtitle": "Escudo ClamAV en Vivo",
        "cmd": "ariaos-antivirus",
        "icon": "ariaos-antivirus",
        "category": "seguridad",
        "accent": "#00ff88",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "netradar",
        "name": "NetRadar",
        "subtitle": "Escáner LAN y Conexiones",
        "cmd": "ariaos-netradar",
        "icon": "ariaos-netradar",
        "category": "seguridad",
        "accent": "#00f0ff",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "optimizer",
        "name": "Optimizador Kernel",
        "subtitle": "Limpieza RAM, ZRAM y Caché",
        "cmd": "ariaos-optimizer",
        "icon": "ariaos-optimizer",
        "category": "sistema",
        "accent": "#ffbe0b",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "vault",
        "name": "Bóveda Cifrada",
        "subtitle": "Cifrado AES-256 & Secretos",
        "cmd": "ariaos-vault",
        "icon": "ariaos-vault",
        "category": "seguridad",
        "accent": "#ffd166",
        "dock": True,
        "desktop": False,
    },
    {
        "id": "snapshots",
        "name": "Instantáneas OS",
        "subtitle": "Puntos de Restauración",
        "cmd": "ariaos-snapshots",
        "icon": "ariaos-snapshots",
        "category": "sistema",
        "accent": "#c77dff",
        "dock": True,
        "desktop": False,
    },
    {
        "id": "automations",
        "name": "Automatizaciones",
        "subtitle": "Modos y Tareas Cron",
        "cmd": "ariaos-automations",
        "icon": "ariaos-automations",
        "category": "ia",
        "accent": "#ffbe0b",
        "dock": True,
        "desktop": False,
    },
    {
        "id": "clipboard",
        "name": "Portapapeles IA",
        "subtitle": "Historial Inteligente",
        "cmd": "ariaos-clipboard",
        "icon": "ariaos-clipboard",
        "category": "ia",
        "accent": "#9d4edd",
        "dock": False,
        "desktop": False,
    },
    {
        "id": "files",
        "name": "Archivos",
        "subtitle": "Explorador del Sistema",
        "cmd": "dolphin",
        "icon": "ariaos-files",
        "category": "sistema",
        "accent": "#00f0ff",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "terminal",
        "name": "Terminal Cyber",
        "subtitle": "Consola Bash / Aria CLI",
        "cmd": "konsole",
        "icon": "ariaos-terminal",
        "category": "sistema",
        "accent": "#00ff9d",
        "dock": True,
        "desktop": True,
    },
    {
        "id": "settings",
        "name": "Centro de Control",
        "subtitle": "Ajustes Globales de AriaOS",
        "cmd": "ariaos-settings",
        "icon": "ariaos-settings",
        "category": "sistema",
        "accent": "#00f0ff",
        "dock": True,
        "desktop": True,
    },
]


def resolve_icon(icon_name: str) -> QIcon:
    """Finds custom SVG/PNG icon from AriaOS directories or falls back to theme."""
    for folder in ICON_SEARCH_DIRS:
        for ext in (".svg", ".png"):
            candidate = folder / f"{icon_name}{ext}"
            if candidate.exists():
                return QIcon(str(candidate))
    theme_icon = QIcon.fromTheme(icon_name)
    if not theme_icon.isNull():
        return theme_icon
    for folder in ICON_SEARCH_DIRS:
        logo = folder / "ariaos-logo.png"
        if logo.exists():
            return QIcon(str(logo))
    return QIcon()


def launch_command(cmd: str) -> None:
    """Launches a desktop command detached from the shell process."""
    try:
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def suppress_stock_plasma() -> None:
    """Terminates stock KDE plasma-welcome so AriaDE owns the desktop cleanly."""
    cmds = [
        "killall -9 plasma-welcome 2>/dev/null || true",
    ]
    for c in cmds:
        subprocess.run(c, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# System Telemetry Reader
# ---------------------------------------------------------------------------
class KernelTelemetry:
    def __init__(self) -> None:
        self._prev_idle = 0
        self._prev_total = 0
        self._prev_rx = 0
        self._prev_tx = 0
        self._prev_net_ts = time.time()

    def sample(self) -> dict:
        cpu_pct = self._read_cpu()
        mem_used_gb, mem_total_gb, mem_pct, swap_pct = self._read_mem()
        rx_kbs, tx_kbs = self._read_net()
        temp_c = self._read_temp()
        uptime_str = self._read_uptime()
        daemon_ok = self._check_port(7770)
        ollama_ok = self._check_port(11434)
        return {
            "cpu_pct": cpu_pct,
            "mem_used_gb": mem_used_gb,
            "mem_total_gb": mem_total_gb,
            "mem_pct": mem_pct,
            "swap_pct": swap_pct,
            "rx_kbs": rx_kbs,
            "tx_kbs": tx_kbs,
            "temp_c": temp_c,
            "uptime": uptime_str,
            "daemon_ok": daemon_ok,
            "ollama_ok": ollama_ok,
        }

    def _read_cpu(self) -> float:
        try:
            with open("/proc/stat", "r", encoding="utf-8") as f:
                fields = [int(x) for x in f.readline().split()[1:]]
            idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
            total = sum(fields)
            diff_total = total - self._prev_total
            diff_idle = idle - self._prev_idle
            self._prev_total = total
            self._prev_idle = idle
            if diff_total <= 0:
                return 0.0
            return max(0.0, min(100.0, 100.0 * (1.0 - diff_idle / diff_total)))
        except Exception:
            return 8.5

    def _read_mem(self) -> tuple[float, float, float, float]:
        try:
            info = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        info[parts[0].strip()] = int(parts[1].strip().split()[0])
            total_kb = info.get("MemTotal", 6144000)
            avail_kb = info.get("MemAvailable", total_kb // 2)
            used_kb = max(0, total_kb - avail_kb)
            swap_total = info.get("SwapTotal", 0)
            swap_free = info.get("SwapFree", 0)
            swap_pct = ((swap_total - swap_free) / swap_total * 100.0) if swap_total > 0 else 0.0
            return (
                used_kb / (1024 * 1024),
                total_kb / (1024 * 1024),
                (used_kb / total_kb) * 100.0 if total_kb else 0.0,
                swap_pct,
            )
        except Exception:
            return (1.4, 6.0, 23.0, 0.0)

    def _read_net(self) -> tuple[float, float]:
        try:
            rx, tx = 0, 0
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                for line in f.readlines()[2:]:
                    if ":" not in line:
                        continue
                    iface, data = line.split(":", 1)
                    if iface.strip() == "lo":
                        continue
                    cols = [int(x) for x in data.split()]
                    rx += cols[0]
                    tx += cols[8]
            now = time.time()
            dt = max(0.2, now - self._prev_net_ts)
            rx_kbs = max(0.0, (rx - self._prev_rx) / 1024.0 / dt) if self._prev_rx else 0.0
            tx_kbs = max(0.0, (tx - self._prev_tx) / 1024.0 / dt) if self._prev_tx else 0.0
            self._prev_rx, self._prev_tx, self._prev_net_ts = rx, tx, now
            return rx_kbs, tx_kbs
        except Exception:
            return 0.0, 0.0

    def _read_temp(self) -> float:
        try:
            for p in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
                with open(p, "r", encoding="utf-8") as f:
                    val = int(f.read().strip())
                    if val > 0:
                        return val / 1000.0
        except Exception:
            pass
        return 42.0

    def _read_uptime(self) -> str:
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as f:
                secs = int(float(f.read().split()[0]))
            h, rem = divmod(secs, 3600)
            m, s = divmod(rem, 60)
            return f"{h:02d}h {m:02d}m {s:02d}s"
        except Exception:
            return "00h 15m 00s"

    def _check_port(self, port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Circular Neon Gauge Widget
# ---------------------------------------------------------------------------
class CyberGauge(QWidget):
    def __init__(self, label: str, color_hex: str, parent=None) -> None:
        super().__init__(parent)
        self.label = label
        self.color = QColor(color_hex)
        self.value = 0.0
        self.subtext = "0%"
        self.setFixedSize(96, 106)

    def set_metric(self, value: float, subtext: str = "") -> None:
        self.value = max(0.0, min(100.0, value))
        self.subtext = subtext or f"{int(self.value)}%"
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(12, 8, 72, 72)
        # Background track
        pen_bg = QPen(QColor(255, 255, 255, 24), 6.5)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_bg)
        p.drawArc(rect, 225 * 16, -270 * 16)

        # Active neon arc
        span = int(-270 * 16 * (self.value / 100.0))
        pen_fg = QPen(self.color, 6.5)
        pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_fg)
        p.drawArc(rect, 225 * 16, span)

        # Value text inside circle
        p.setPen(QColor("#eef6ff"))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.subtext)

        # Label below
        p.setPen(self.color)
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(QRectF(0, 82, 96, 20), Qt.AlignmentFlag.AlignCenter, self.label)


# ---------------------------------------------------------------------------
# Power / Session Dialog
# ---------------------------------------------------------------------------
class CyberPowerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(500, 250)

        container = QFrame(self)
        container.setGeometry(0, 0, 500, 250)
        container.setStyleSheet(
            """
            QFrame {
                background-color: rgba(7, 11, 20, 245);
                border: 2px solid #00f0ff;
                border-radius: 18px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            QPushButton {
                background-color: rgba(16, 24, 42, 220);
                color: #e6f2ff;
                border: 1px solid rgba(0, 240, 255, 90);
                border-radius: 12px;
                padding: 14px 10px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 240, 255, 40);
                border: 1px solid #00f0ff;
                color: #ffffff;
            }
            """
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 22, 24, 22)

        title = QLabel("⏻  CONTROL DE SESIÓN Y ENERGÍA ARIA-OS")
        title.setStyleSheet("color: #00f0ff; font-size: 15px; font-weight: bold; letter-spacing: 1px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Selecciona una acción para el núcleo del sistema:")
        sub.setStyleSheet("color: #8ba3c7; font-size: 12px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        actions = [
            ("🔒 Bloquear", "loginctl lock-session"),
            ("🚪 Cerrar Sesión", "loginctl terminate-user $USER"),
            ("🔄 Reiniciar", "systemctl reboot"),
            ("⏻ Apagar", "systemctl poweroff"),
        ]
        for label, cmd in actions:
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _checked=False, c=cmd: (launch_command(c), self.accept()))
            btn_row.addWidget(b)

        layout.addLayout(btn_row)

        cancel_btn = QPushButton("Cancelar (Esc)")
        cancel_btn.setStyleSheet(
            "background-color: rgba(255, 0, 85, 35); border: 1px solid #ff0055; padding: 8px;"
        )
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)


# ---------------------------------------------------------------------------
# Holographic Full Application Launcher (Replaces KDE Kickoff)
# ---------------------------------------------------------------------------
class AriaAppLauncher(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(780, 540)
        self.current_category = "all"
        self.system_apps = self._scan_system_desktop_apps()

        root = QFrame(self)
        root.setGeometry(0, 0, 780, 540)
        root.setStyleSheet(
            """
            QFrame#LauncherRoot {
                background-color: rgba(6, 10, 19, 246);
                border: 2px solid #00f0ff;
                border-radius: 18px;
            }
            QLineEdit {
                background-color: rgba(14, 22, 38, 230);
                color: #ffffff;
                border: 1px solid #00f0ff;
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
            }
            """
        )
        root.setObjectName("LauncherRoot")

        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(20, 18, 20, 16)
        main_layout.setSpacing(12)

        # Header + Search
        header = QHBoxLayout()
        brand = QLabel("⬡ ARIA-OS // CYBER APPLICATION MATRIX")
        brand.setStyleSheet("color: #00f0ff; font-size: 14px; font-weight: bold; letter-spacing: 1.2px;")
        header.addWidget(brand)
        header.addStretch()

        ai_btn = QPushButton("✦ Abrir Aria Neural HUD (Alt+Espacio)")
        ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ai_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(157, 78, 221, 55);
                color: #f0e6ff;
                border: 1px solid #c77dff;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(157, 78, 221, 110);
            }
            """
        )
        ai_btn.clicked.connect(lambda: (self.hide(), launch_command("aria-command-bar")))
        header.addWidget(ai_btn)
        main_layout.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Buscar herramientas de AriaOS, comandos de IA o aplicaciones del sistema...")
        self.search_input.textChanged.connect(self._populate_grid)
        main_layout.addWidget(self.search_input)

        # Body: Left Category Rail + Right App Grid
        body = QHBoxLayout()
        body.setSpacing(14)

        cat_rail = QVBoxLayout()
        cat_rail.setSpacing(6)
        self.cat_buttons = {}
        categories = [
            ("all", "⚡ Suite AriaOS"),
            ("ia", "🧠 Inteligencia IA"),
            ("seguridad", "🛡️ Seguridad & Red"),
            ("sistema", "⚙️ Sistema & Kernel"),
            ("linux", "🌐 Todas las Apps"),
        ]
        for cat_id, label in categories:
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(38)
            b.clicked.connect(lambda _c=False, cid=cat_id: self._select_category(cid))
            self.cat_buttons[cat_id] = b
            cat_rail.addWidget(b)

        cat_rail.addStretch()

        # Quick System Installer CTA inside menu
        inst_btn = QPushButton("🚀 Instalar en Disco")
        inst_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        inst_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(0, 255, 157, 35);
                color: #00ff9d;
                border: 1px solid #00ff9d;
                border-radius: 9px;
                padding: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 255, 157, 80);
                color: #ffffff;
            }
            """
        )
        inst_btn.clicked.connect(lambda: (self.hide(), launch_command("ariaos-installer")))
        cat_rail.addWidget(inst_btn)

        pwr_btn = QPushButton("⏻ Energía / Sesión")
        pwr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pwr_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 0, 85, 35);
                color: #ff6b9d;
                border: 1px solid #ff0055;
                border-radius: 9px;
                padding: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 85, 85);
                color: #ffffff;
            }
            """
        )
        pwr_btn.clicked.connect(self._open_power)
        cat_rail.addWidget(pwr_btn)

        rail_widget = QWidget()
        rail_widget.setFixedWidth(175)
        rail_widget.setLayout(cat_rail)
        body.addWidget(rail_widget)

        # Scrollable grid area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 6px; background: #0a101d; }"
            "QScrollBar::handle:vertical { background: #00f0ff; border-radius: 3px; }"
        )
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll.setWidget(self.grid_container)
        body.addWidget(self.scroll, 1)

        main_layout.addLayout(body, 1)
        self._select_category("all")

    def _open_power(self) -> None:
        self.hide()
        dlg = CyberPowerDialog(self.parentWidget())
        dlg.exec()

    def _scan_system_desktop_apps(self) -> list[dict]:
        results = []
        seen = set()
        for d in ("/usr/share/applications",):
            if not os.path.isdir(d):
                continue
            for fn in sorted(os.listdir(d)):
                if not fn.endswith(".desktop") or fn.startswith("ariaos-"):
                    continue
                path = os.path.join(d, fn)
                cp = configparser.ConfigParser(interpolation=None)
                try:
                    cp.read(path, encoding="utf-8")
                    if "Desktop Entry" not in cp:
                        continue
                    sec = cp["Desktop Entry"]
                    if sec.get("NoDisplay", "false").lower() == "true":
                        continue
                    name = sec.get("Name[es]", sec.get("Name", "")).strip()
                    exec_cmd = sec.get("Exec", "").strip()
                    icon_name = sec.get("Icon", "application-x-executable").strip()
                    if not name or not exec_cmd or name in seen:
                        continue
                    # Strip %U, %F, etc.
                    clean_cmd = " ".join(
                        p for p in exec_cmd.split() if not p.startswith("%")
                    )
                    seen.add(name)
                    results.append(
                        {
                            "name": name,
                            "subtitle": sec.get("GenericName[es]", sec.get("GenericName", "Aplicación Linux")),
                            "cmd": clean_cmd,
                            "icon": icon_name,
                            "category": "linux",
                            "accent": "#3a86ff",
                        }
                    )
                except Exception:
                    continue
        return results

    def _select_category(self, cat_id: str) -> None:
        self.current_category = cat_id
        for cid, btn in self.cat_buttons.items():
            if cid == cat_id:
                btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: rgba(0, 240, 255, 45);
                        color: #ffffff;
                        border: 1px solid #00f0ff;
                        border-radius: 8px;
                        text-align: left;
                        padding-left: 12px;
                        font-weight: bold;
                    }
                    """
                )
            else:
                btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: rgba(15, 22, 38, 160);
                        color: #9ab0d0;
                        border: 1px solid rgba(255, 255, 255, 18);
                        border-radius: 8px;
                        text-align: left;
                        padding-left: 12px;
                    }
                    QPushButton:hover {
                        background-color: rgba(0, 240, 255, 20);
                        color: #ffffff;
                    }
                    """
                )
        self._populate_grid()

    def _populate_grid(self) -> None:
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self.search_input.text().strip().lower()
        pool = SUITE_APPS + (self.system_apps if (self.current_category == "linux" or query) else [])

        filtered = []
        for app in pool:
            if query:
                if query not in app["name"].lower() and query not in app.get("subtitle", "").lower():
                    continue
            else:
                if self.current_category != "all" and app.get("category") != self.current_category:
                    continue
            filtered.append(app)

        cols = 3
        for idx, app in enumerate(filtered):
            r, c = divmod(idx, cols)
            card = self._create_app_card(app)
            self.grid_layout.addWidget(card, r, c)

        self.grid_layout.setRowStretch((len(filtered) // cols) + 1, 1)

    def _create_app_card(self, app: dict) -> QPushButton:
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(72)
        accent = app.get("accent", "#00f0ff")
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(13, 20, 35, 215);
                border: 1px solid rgba(0, 240, 255, 55);
                border-left: 3px solid {accent};
                border-radius: 10px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 240, 255, 35);
                border: 1px solid {accent};
                border-left: 4px solid {accent};
            }}
            """
        )
        lay = QHBoxLayout(btn)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        ic = resolve_icon(app["icon"])
        icon_lbl.setPixmap(ic.pixmap(QSize(38, 38)))
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        lay.addWidget(icon_lbl)

        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        t1 = QLabel(app["name"])
        t1.setStyleSheet("color: #f0f7ff; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        t2 = QLabel(app.get("subtitle", ""))
        t2.setStyleSheet("color: #7e97b8; font-size: 10px; border: none; background: transparent;")
        txt_col.addWidget(t1)
        txt_col.addWidget(t2)
        lay.addLayout(txt_col, 1)

        cmd = app["cmd"]
        btn.clicked.connect(lambda _c=False, command=cmd: (self.hide(), launch_command(command)))
        return btn


# ---------------------------------------------------------------------------
# Custom Top Tactical Status Bar (AriaTopBar)
# ---------------------------------------------------------------------------
class AriaTopBar(QWidget):
    mode_changed = pyqtSignal(str)

    def __init__(self, launcher: AriaAppLauncher, screen_geom: QRect) -> None:
        super().__init__()
        self.launcher = launcher
        self.active_mode = "BALANCEADO"
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.bar_height = 38
        self.setGeometry(screen_geom.x(), screen_geom.y(), screen_geom.width(), self.bar_height)

        self.frame = QFrame(self)
        self.frame.setGeometry(0, 0, screen_geom.width(), self.bar_height)
        self.frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(6, 9, 17, 242);
                border-bottom: 1.5px solid #00f0ff;
            }
            """
        )

        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(12, 3, 12, 3)
        layout.setSpacing(10)

        # 1. AriaOS Main Menu Button
        self.menu_btn = QPushButton("⬡  ARIA OS")
        self.menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(0, 240, 255, 32);
                color: #00f0ff;
                border: 1px solid #00f0ff;
                border-radius: 7px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: rgba(0, 240, 255, 80);
                color: #ffffff;
            }
            """
        )
        self.menu_btn.clicked.connect(self._toggle_launcher)
        layout.addWidget(self.menu_btn)

        # 2. Virtual Desktop Switcher (I, II, III, IV)
        self.ws_buttons = []
        ws_frame = QFrame()
        ws_frame.setStyleSheet("border: none; background: transparent;")
        ws_lay = QHBoxLayout(ws_frame)
        ws_lay.setContentsMargins(0, 0, 0, 0)
        ws_lay.setSpacing(4)
        for i, roman in enumerate(("I", "II", "III", "IV")):
            wb = QPushButton(roman)
            wb.setCursor(Qt.CursorShape.PointingHandCursor)
            wb.setFixedSize(28, 24)
            wb.clicked.connect(lambda _c=False, idx=i: self._switch_workspace(idx))
            self.ws_buttons.append(wb)
            ws_lay.addWidget(wb)
        self._highlight_workspace(0)
        layout.addWidget(ws_frame)

        # Quick top action buttons
        for label, cmd, col in (
            ("🚀 Instalar OS", "ariaos-installer", "#00ff9d"),
            ("📊 Monitor", "ariaos-monitor", "#00f0ff"),
            (">_ Terminal", "konsole", "#9ab0d0"),
        ):
            qb = QPushButton(label)
            qb.setCursor(Qt.CursorShape.PointingHandCursor)
            qb.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(16, 24, 42, 180);
                    color: {col};
                    border: 1px solid rgba(255,255,255,25);
                    border-radius: 6px;
                    padding: 3px 9px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    border: 1px solid {col};
                    background-color: rgba(0, 240, 255, 25);
                }}
                """
            )
            qb.clicked.connect(lambda _c=False, c=cmd: launch_command(c))
            layout.addWidget(qb)

        layout.addStretch()

        # 3. Center Neural Core Pill
        self.ai_pill = QPushButton("✦  ARIA NEURAL CORE  ·  Alt+Espacio")
        self.ai_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_pill.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 240, 255, 45),
                    stop:0.5 rgba(157, 78, 221, 55),
                    stop:1 rgba(0, 240, 255, 45));
                color: #ffffff;
                border: 1px solid #00f0ff;
                border-radius: 13px;
                padding: 4px 18px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background-color: rgba(0, 240, 255, 95);
                border: 1px solid #ffffff;
            }
            """
        )
        self.ai_pill.clicked.connect(lambda: launch_command("aria-command-bar"))
        layout.addWidget(self.ai_pill)

        layout.addStretch()

        # 4. Right Telemetry & System Controls
        self.mode_badge = QLabel("⚡ MODO: BALANCEADO")
        self.mode_badge.setStyleSheet(
            "color: #00ff9d; background: rgba(0, 255, 157, 22); "
            "border: 1px solid rgba(0, 255, 157, 90); border-radius: 6px; "
            "padding: 3px 8px; font-size: 10px; font-weight: bold;"
        )
        layout.addWidget(self.mode_badge)

        self.cpu_chip = QLabel("CPU 0%")
        self.cpu_chip.setStyleSheet(
            "color: #00f0ff; background: rgba(0, 240, 255, 18); "
            "border: 1px solid rgba(0, 240, 255, 60); border-radius: 6px; "
            "padding: 3px 8px; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(self.cpu_chip)

        self.ram_chip = QLabel("RAM 0.0G")
        self.ram_chip.setStyleSheet(
            "color: #c77dff; background: rgba(199, 125, 255, 18); "
            "border: 1px solid rgba(199, 125, 255, 60); border-radius: 6px; "
            "padding: 3px 8px; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(self.ram_chip)

        # Volume control button
        vol_btn = QPushButton("🔊 Audio")
        vol_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        vol_btn.setStyleSheet(
            "QPushButton { color: #d8e8ff; background: rgba(255,255,255,12); "
            "border: 1px solid rgba(255,255,255,30); border-radius: 6px; padding: 3px 8px; font-size: 11px; }"
            "QPushButton:hover { border: 1px solid #00f0ff; }"
        )
        vol_btn.clicked.connect(lambda: launch_command("ariaos-settings"))
        layout.addWidget(vol_btn)

        # Clock
        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet(
            "color: #ffffff; font-size: 12px; font-weight: bold; border: none; padding: 0 6px;"
        )
        layout.addWidget(self.clock_lbl)

        # Power button
        pwr_btn = QPushButton("⏻")
        pwr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        pwr_btn.setFixedSize(28, 26)
        pwr_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 0, 85, 45);
                color: #ff4d88;
                border: 1px solid #ff0055;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff0055;
                color: #ffffff;
            }
            """
        )
        pwr_btn.clicked.connect(self._open_power_dialog)
        layout.addWidget(pwr_btn)

        self._update_clock()

    def _toggle_launcher(self) -> None:
        if self.launcher.isVisible():
            self.launcher.hide()
        else:
            self.launcher.move(self.x() + 10, self.y() + self.bar_height + 6)
            self.launcher.search_input.clear()
            self.launcher.show()
            self.launcher.raise_()
            self.launcher.activateWindow()
            self.launcher.search_input.setFocus()

    def _switch_workspace(self, idx: int) -> None:
        self._highlight_workspace(idx)
        launch_command(
            f"qdbus6 org.kde.KWin /KWin setCurrentDesktop {idx + 1} 2>/dev/null || wmctrl -s {idx} 2>/dev/null"
        )

    def _highlight_workspace(self, active_idx: int) -> None:
        for i, b in enumerate(self.ws_buttons):
            if i == active_idx:
                b.setStyleSheet(
                    "background-color: #00f0ff; color: #050811; border: none; "
                    "border-radius: 5px; font-size: 10px; font-weight: bold;"
                )
            else:
                b.setStyleSheet(
                    "background-color: rgba(255,255,255,14); color: #8ea4c8; "
                    "border: 1px solid rgba(255,255,255,25); border-radius: 5px; font-size: 10px;"
                )

    def _open_power_dialog(self) -> None:
        dlg = CyberPowerDialog(self)
        dlg.exec()

    def set_mode_label(self, mode_name: str) -> None:
        self.active_mode = mode_name.upper()
        self.mode_badge.setText(f"⚡ MODO: {self.active_mode}")

    def update_telemetry(self, data: dict) -> None:
        self.cpu_chip.setText(f"CPU {int(data['cpu_pct'])}%")
        self.ram_chip.setText(f"RAM {data['mem_used_gb']:.1f}/{data['mem_total_gb']:.0f}G")
        self._update_clock()

    def _update_clock(self) -> None:
        now = datetime.datetime.now()
        self.clock_lbl.setText(now.strftime("%H:%M:%S   ·   %d/%m/%Y"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "frame"):
            self.frame.setGeometry(0, 0, self.width(), self.height())


# ---------------------------------------------------------------------------
# Custom Bottom Floating Cyber Dock (AriaCyberDock)
# ---------------------------------------------------------------------------
class AriaCyberDock(QWidget):
    def __init__(self, launcher: AriaAppLauncher, screen_geom: QRect) -> None:
        super().__init__()
        self.launcher = launcher
        self.screen_geom = screen_geom
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        dock_apps = [a for a in SUITE_APPS if a.get("dock")]
        item_w = 56
        dock_w = (len(dock_apps) + 1) * item_w + 32
        dock_h = 66
        x_pos = screen_geom.x() + (screen_geom.width() - dock_w) // 2
        y_pos = screen_geom.y() + screen_geom.height() - dock_h - 8
        self.setGeometry(x_pos, y_pos, dock_w, dock_h)

        container = QFrame(self)
        container.setGeometry(0, 0, dock_w, dock_h)
        container.setStyleSheet(
            """
            QFrame {
                background-color: rgba(7, 11, 22, 238);
                border: 1.8px solid #00f0ff;
                border-radius: 18px;
            }
            """
        )

        lay = QHBoxLayout(container)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(6)

        # App Launcher Button in Dock
        menu_btn = self._make_dock_button(
            "Menú AriaOS",
            "ariaos-welcome",
            "#00f0ff",
            self._toggle_launcher_from_dock,
        )
        lay.addWidget(menu_btn)

        for app in dock_apps:
            btn = self._make_dock_button(
                f"{app['name']} — {app['subtitle']}",
                app["icon"],
                app.get("accent", "#00f0ff"),
                lambda _c=False, cmd=app["cmd"]: launch_command(cmd),
            )
            lay.addWidget(btn)

    def _make_dock_button(self, tooltip: str, icon_name: str, accent: str, callback) -> QPushButton:
        b = QPushButton()
        b.setToolTip(tooltip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedSize(50, 50)
        b.setIcon(resolve_icon(icon_name))
        b.setIconSize(QSize(36, 36))
        b.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(16, 25, 45, 195);
                border: 1px solid rgba(0, 240, 255, 55);
                border-bottom: 2.5px solid {accent};
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 240, 255, 55);
                border: 1.5px solid #ffffff;
                border-bottom: 3px solid {accent};
            }}
            """
        )
        b.clicked.connect(callback)
        return b

    def _toggle_launcher_from_dock(self) -> None:
        if self.launcher.isVisible():
            self.launcher.hide()
        else:
            lx = self.x() + (self.width() - self.launcher.width()) // 2
            ly = self.y() - self.launcher.height() - 10
            self.launcher.move(max(10, lx), max(46, ly))
            self.launcher.show()
            self.launcher.raise_()
            self.launcher.activateWindow()


# ---------------------------------------------------------------------------
# Interactive Desktop Background Canvas + Holographic Desktop Widgets
# ---------------------------------------------------------------------------
class AriaDesktopCanvas(QWidget):
    mode_selected = pyqtSignal(str)

    def __init__(self, launcher: AriaAppLauncher, screen_geom: QRect) -> None:
        super().__init__()
        self.launcher = launcher
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setGeometry(screen_geom)

        self.wallpaper = QPixmap()
        for wp in WALLPAPER_PATHS:
            if wp.exists():
                self.wallpaper = QPixmap(str(wp))
                break

        root = QHBoxLayout(self)
        root.setContentsMargins(28, 56, 28, 86)
        root.setSpacing(24)

        # LEFT COLUMN: Cyber Desktop Shortcut Cards (2 columns)
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_grid = QGridLayout(left_widget)
        left_grid.setContentsMargins(0, 0, 0, 0)
        left_grid.setHorizontalSpacing(14)
        left_grid.setVerticalSpacing(12)

        desktop_apps = [a for a in SUITE_APPS if a.get("desktop")]
        for idx, app in enumerate(desktop_apps):
            r, c = divmod(idx, 2)
            card = self._build_desktop_shortcut(app)
            left_grid.addWidget(card, r, c)

        left_grid.setRowStretch(len(desktop_apps) // 2 + 1, 1)
        root.addWidget(left_widget, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        root.addStretch(1)

        # RIGHT COLUMN: 3 Native Holographic Desktop Widgets
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        # --- WIDGET 1: Holographic Clock & System Identity ---
        clock_card = self._make_holo_card()
        clock_lay = QVBoxLayout(clock_card)
        clock_lay.setContentsMargins(18, 14, 18, 14)
        clock_lay.setSpacing(4)

        tag = QLabel("⬡ ARIA-OS // CYBER OBSIDIAN KERNEL SHELL")
        tag.setStyleSheet("color: #00f0ff; font-size: 10px; font-weight: bold; letter-spacing: 1.5px;")
        clock_lay.addWidget(tag)

        self.big_clock = QLabel("00:00:00")
        self.big_clock.setStyleSheet("color: #ffffff; font-size: 36px; font-weight: bold; letter-spacing: 2px;")
        clock_lay.addWidget(self.big_clock)

        self.big_date = QLabel("Jueves, 12 de Noviembre 2026")
        self.big_date.setStyleSheet("color: #98b4d8; font-size: 12px;")
        clock_lay.addWidget(self.big_date)

        self.sys_meta = QLabel(f"Kernel: {platform.release()}  •  Uptime: 00h 00m")
        self.sys_meta.setStyleSheet("color: #00ff9d; font-size: 11px; font-weight: bold;")
        clock_lay.addWidget(self.sys_meta)
        right_col.addWidget(clock_card)

        # --- WIDGET 2: Real-Time Kernel & GPU Telemetry Gauges ---
        telem_card = self._make_holo_card()
        telem_lay = QVBoxLayout(telem_card)
        telem_lay.setContentsMargins(16, 12, 16, 12)
        telem_lay.setSpacing(8)

        th = QLabel("📊 TELEMETRÍA DEL KERNEL EN TIEMPO REAL")
        th.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        telem_lay.addWidget(th)

        gauges_row = QHBoxLayout()
        self.g_cpu = CyberGauge("CPU CORE", "#00f0ff")
        self.g_ram = CyberGauge("MEMORIA RAM", "#c77dff")
        self.g_temp = CyberGauge("TEMP NÚCLEO", "#00ff9d")
        gauges_row.addWidget(self.g_cpu)
        gauges_row.addWidget(self.g_ram)
        gauges_row.addWidget(self.g_temp)
        telem_lay.addLayout(gauges_row)

        self.net_lbl = QLabel("📡 Tráfico de Red:  ▼ 0.0 KB/s   ▲ 0.0 KB/s   |   ZRAM Activo")
        self.net_lbl.setStyleSheet("color: #a9c2e2; font-size: 11px;")
        telem_lay.addWidget(self.net_lbl)
        right_col.addWidget(telem_card)

        # --- WIDGET 3: Aria Neural Core + Instant Performance Profiles ---
        neural_card = self._make_holo_card()
        neural_lay = QVBoxLayout(neural_card)
        neural_lay.setContentsMargins(16, 12, 16, 14)
        neural_lay.setSpacing(8)

        nh = QLabel("🧠 CENTRO NEURONAL ARIA & MODOS DEL KERNEL")
        nh.setStyleSheet("color: #ff007f; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        neural_lay.addWidget(nh)

        self.ai_status_lbl = QLabel("● Motor Local aria-core (qwen2.5:0.5b): ACTIVO")
        self.ai_status_lbl.setStyleSheet("color: #00ff9d; font-size: 11px; font-weight: bold;")
        neural_lay.addWidget(self.ai_status_lbl)

        # 4 Mode Buttons
        modes_grid = QGridLayout()
        modes_grid.setSpacing(6)
        self.mode_btns = {}
        modes = [
            ("BALANCEADO", "⚖️ Balanceado", "#00f0ff"),
            ("GAMING", "🎮 Modo Gaming", "#00ff9d"),
            ("DESARROLLO", "💻 Modo Dev", "#c77dff"),
            ("AHORRO", "🔋 Ahorro Extremo", "#ffbe0b"),
        ]
        for idx, (m_id, m_label, m_col) in enumerate(modes):
            mb = QPushButton(m_label)
            mb.setCursor(Qt.CursorShape.PointingHandCursor)
            mb.setFixedHeight(30)
            mb.clicked.connect(lambda _c=False, mid=m_id: self._activate_profile(mid))
            self.mode_btns[m_id] = (mb, m_col)
            modes_grid.addWidget(mb, idx // 2, idx % 2)
        neural_lay.addLayout(modes_grid)
        self._style_mode_buttons("BALANCEADO")

        # Direct AI Input on Desktop
        prompt_row = QHBoxLayout()
        self.desktop_prompt = QLineEdit()
        self.desktop_prompt.setPlaceholderText("Habla con Aria IA desde el escritorio...")
        self.desktop_prompt.setStyleSheet(
            """
            QLineEdit {
                background-color: rgba(14, 22, 38, 220);
                color: #ffffff;
                border: 1px solid #00f0ff;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }
            """
        )
        self.desktop_prompt.returnPressed.connect(self._send_desktop_prompt)
        prompt_row.addWidget(self.desktop_prompt, 1)

        send_btn = QPushButton("✦ Enviar")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #00f0ff;
                color: #050811;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffffff;
            }
            """
        )
        send_btn.clicked.connect(self._send_desktop_prompt)
        prompt_row.addWidget(send_btn)
        neural_lay.addLayout(prompt_row)

        right_col.addWidget(neural_card)
        right_col.addStretch(1)

        right_wrap = QWidget()
        right_wrap.setFixedWidth(360)
        right_wrap.setStyleSheet("background: transparent;")
        right_wrap.setLayout(right_col)
        root.addWidget(right_wrap, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

    def _make_holo_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background-color: rgba(7, 11, 22, 212);
                border: 1.5px solid rgba(0, 240, 255, 110);
                border-radius: 16px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
            """
        )
        return card

    def _build_desktop_shortcut(self, app: dict) -> QPushButton:
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(195, 62)
        accent = app.get("accent", "#00f0ff")
        is_installer = app["id"] == "installer"
        bg_alpha = "235" if is_installer else "195"
        border_w = "2px" if is_installer else "1px"
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(8, 14, 26, {bg_alpha});
                border: {border_w} solid {accent};
                border-left: 4px solid {accent};
                border-radius: 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 240, 255, 48);
                border: 2px solid #ffffff;
                border-left: 5px solid {accent};
            }}
            """
        )
        lay = QHBoxLayout(btn)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        ic_lbl = QLabel()
        ic_lbl.setPixmap(resolve_icon(app["icon"]).pixmap(QSize(36, 36)))
        ic_lbl.setFixedSize(38, 38)
        ic_lbl.setStyleSheet("border: none; background: transparent;")
        lay.addWidget(ic_lbl)

        tc = QVBoxLayout()
        tc.setSpacing(1)
        n_lbl = QLabel(app["name"])
        n_lbl.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        s_lbl = QLabel(app["subtitle"])
        s_lbl.setStyleSheet(f"color: {accent}; font-size: 10px; border: none; background: transparent;")
        tc.addWidget(n_lbl)
        tc.addWidget(s_lbl)
        lay.addLayout(tc, 1)

        cmd = app["cmd"]
        btn.clicked.connect(lambda _c=False, c=cmd: launch_command(c))
        return btn

    def _activate_profile(self, mode_id: str) -> None:
        self._style_mode_buttons(mode_id)
        self.mode_selected.emit(mode_id)
        # Apply real kernel/power profile via aria CLI or sysctl
        if mode_id == "GAMING":
            launch_command("aria 'activa el modo gaming'")
        elif mode_id == "DESARROLLO":
            launch_command("aria 'activa el modo desarrollo'")
        elif mode_id == "AHORRO":
            launch_command("aria 'activa el modo ahorro de bateria'")

    def _style_mode_buttons(self, active_id: str) -> None:
        for mid, (btn, col) in self.mode_btns.items():
            if mid == active_id:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {col};
                        color: #050811;
                        border: none;
                        border-radius: 7px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                    """
                )
            else:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: rgba(14, 22, 38, 190);
                        color: #c8daf2;
                        border: 1px solid {col};
                        border-radius: 7px;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(0, 240, 255, 35);
                    }}
                    """
                )

    def _send_desktop_prompt(self) -> None:
        text = self.desktop_prompt.text().strip()
        self.desktop_prompt.clear()
        if text:
            launch_command(f"aria-command-bar {json.dumps(text)}")
        else:
            launch_command("aria-command-bar")

    def update_widgets(self, data: dict) -> None:
        now = datetime.datetime.now()
        self.big_clock.setText(now.strftime("%H:%M:%S"))
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        months = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
        ]
        self.big_date.setText(f"{days[now.weekday()]}, {now.day} de {months[now.month - 1]} {now.year}")
        self.sys_meta.setText(f"Kernel: {platform.release()}   •   Activo: {data['uptime']}")

        self.g_cpu.set_metric(data["cpu_pct"], f"{int(data['cpu_pct'])}%")
        self.g_ram.set_metric(data["mem_pct"], f"{int(data['mem_pct'])}%")
        self.g_temp.set_metric(min(100.0, data["temp_c"]), f"{int(data['temp_c'])}°C")
        self.net_lbl.setText(
            f"📡 Red:  ▼ {data['rx_kbs']:.1f} KB/s   ▲ {data['tx_kbs']:.1f} KB/s   |   RAM: {data['mem_used_gb']:.1f}/{data['mem_total_gb']:.1f} GB"
        )

        if data["daemon_ok"] and data["ollama_ok"]:
            self.ai_status_lbl.setText("● Núcleo aria-daemon (Rust) + Ollama aria-core: ONLINE")
            self.ai_status_lbl.setStyleSheet("color: #00ff9d; font-size: 11px; font-weight: bold;")
        elif data["ollama_ok"]:
            self.ai_status_lbl.setText("● Motor Ollama aria-core: ONLINE (Modo Directo)")
            self.ai_status_lbl.setStyleSheet("color: #00f0ff; font-size: 11px; font-weight: bold;")
        else:
            self.ai_status_lbl.setText("● Motor Neuronal Local Aria: LISTO BAJO DEMANDA")
            self.ai_status_lbl.setStyleSheet("color: #ffbe0b; font-size: 11px; font-weight: bold;")

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: rgba(7, 11, 22, 245);
                color: #eaf4ff;
                border: 1.5px solid #00f0ff;
                border-radius: 10px;
                padding: 6px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 7px 20px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 240, 255, 50);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(0, 240, 255, 60);
                margin: 4px 8px;
            }
            """
        )
        entries = [
            ("✦  Invocar a Aria Neural IA (Alt+Espacio)", "aria-command-bar"),
            ("🚀  Instalar AriaOS en Disco", "ariaos-installer"),
            ("sep", ""),
            ("📊  Monitor de Kernel, GPU y Procesos", "ariaos-monitor"),
            ("📦  Tienda Cyber de Paquetes", "ariaos-store"),
            ("🛡️  Cortafuegos Inteligente", "ariaos-firewall"),
            ("🧠  Aria AI Studio (Modelos Ollama)", "ariaos-ai-studio"),
            ("⚡  Optimizador de Memoria y Kernel", "ariaos-optimizer"),
            ("sep", ""),
            ("🖥️  Abrir Terminal Cyber", "konsole"),
            ("📁  Abrir Gestor de Archivos", "dolphin"),
            ("⚙️  Centro de Control de AriaOS", "ariaos-settings"),
        ]
        for label, cmd in entries:
            if label == "sep":
                menu.addSeparator()
            else:
                act = QAction(label, self)
                act.triggered.connect(lambda _c=False, c=cmd: launch_command(c))
                menu.addAction(act)
        menu.exec(event.globalPos())

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()

        if not self.wallpaper.isNull():
            scaled = self.wallpaper.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = (scaled.width() - rect.width()) // 2
            sy = (scaled.height() - rect.height()) // 2
            p.drawPixmap(0, 0, scaled, sx, sy, rect.width(), rect.height())
        else:
            grad = QLinearGradient(0, 0, rect.width(), rect.height())
            grad.setColorAt(0.0, QColor("#050811"))
            grad.setColorAt(0.5, QColor("#0a1224"))
            grad.setColorAt(1.0, QColor("#04070e"))
            p.fillRect(rect, grad)

        # Subtle Cyber Grid Overlay
        p.setPen(QPen(QColor(0, 240, 255, 11), 1))
        step = 64
        for x in range(0, rect.width(), step):
            p.drawLine(x, 0, x, rect.height())
        for y in range(0, rect.height(), step):
            p.drawLine(0, y, rect.width(), y)


# ---------------------------------------------------------------------------
# Main Desktop Controller
# ---------------------------------------------------------------------------
class AriaDesktopEnvironment:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        suppress_stock_plasma()

        screen = app.primaryScreen()
        geom = screen.geometry() if screen else QRect(0, 0, 1280, 800)

        self.telemetry = KernelTelemetry()
        self.launcher = AriaAppLauncher()
        self.canvas = AriaDesktopCanvas(self.launcher, geom)
        self.topbar = AriaTopBar(self.launcher, geom)
        self.dock = AriaCyberDock(self.launcher, geom)

        self.canvas.mode_selected.connect(self.topbar.set_mode_label)

        # React to screen resolution changes in VirtualBox / real monitors
        if screen:
            screen.geometryChanged.connect(self._on_screen_resized)

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(1500)
        self._tick()

    def _on_screen_resized(self, new_geom: QRect) -> None:
        self.canvas.setGeometry(new_geom)
        self.topbar.setGeometry(new_geom.x(), new_geom.y(), new_geom.width(), self.topbar.bar_height)
        dock_w = self.dock.width()
        dock_h = self.dock.height()
        self.dock.setGeometry(
            new_geom.x() + (new_geom.width() - dock_w) // 2,
            new_geom.y() + new_geom.height() - dock_h - 8,
            dock_w,
            dock_h,
        )

    def _tick(self) -> None:
        data = self.telemetry.sample()
        self.topbar.update_telemetry(data)
        self.canvas.update_widgets(data)

    def show_all(self) -> None:
        geom = self.canvas.geometry()
        self.canvas.show()
        self.canvas.setGeometry(geom)
        self.canvas.move(geom.x(), geom.y())
        self.canvas.lower()

        self.topbar.show()
        self.topbar.setGeometry(geom.x(), geom.y(), geom.width(), self.topbar.bar_height)
        self.topbar.move(geom.x(), geom.y())
        self.topbar.raise_()

        dock_w = self.dock.width()
        dock_h = self.dock.height()
        dx = geom.x() + (geom.width() - dock_w) // 2
        dy = geom.y() + geom.height() - dock_h - 8
        self.dock.show()
        self.dock.setGeometry(dx, dy, dock_w, dock_h)
        self.dock.move(dx, dy)
        self.dock.raise_()

        self._apply_x11_struts()
        # Re-assert positions 400ms and 1500ms after KWin maps windows
        QTimer.singleShot(400, self._reassert_geometry)
        QTimer.singleShot(1500, self._reassert_geometry)

    def _reassert_geometry(self) -> None:
        screen = self.app.primaryScreen()
        geom = screen.geometry() if screen else self.canvas.geometry()
        self._on_screen_resized(geom)
        self.canvas.move(geom.x(), geom.y())
        self.canvas.lower()
        self.topbar.move(geom.x(), geom.y())
        self.topbar.raise_()
        dock_w = self.dock.width()
        dock_h = self.dock.height()
        self.dock.move(
            geom.x() + (geom.width() - dock_w) // 2,
            geom.y() + geom.height() - dock_h - 8,
        )
        self.dock.raise_()
        self._apply_x11_struts()

    def _apply_x11_struts(self) -> None:
        """Sets EWMH Desktop/Dock window types and reserves TopBar (38px) strut."""
        try:
            canvas_wid = int(self.canvas.winId())
            top_wid = int(self.topbar.winId())
            dock_wid = int(self.dock.winId())
            w = self.canvas.width()
            subprocess.run(
                [
                    "xprop", "-id", str(canvas_wid),
                    "-f", "_NET_WM_STATE", "32a",
                    "-set", "_NET_WM_STATE",
                    "_NET_WM_STATE_BELOW,_NET_WM_STATE_SKIP_TASKBAR,_NET_WM_STATE_SKIP_PAGER",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for wid in (top_wid, dock_wid):
                subprocess.run(
                    [
                        "xprop", "-id", str(wid),
                        "-f", "_NET_WM_WINDOW_TYPE", "32a",
                        "-set", "_NET_WM_WINDOW_TYPE",
                        "_NET_WM_WINDOW_TYPE_DOCK",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            subprocess.run(
                [
                    "xprop", "-id", str(top_wid),
                    "-f", "_NET_WM_STRUT_PARTIAL", "32c",
                    "-set", "_NET_WM_STRUT_PARTIAL",
                    f"0, 0, 38, 0, 0, 0, 0, 0, 0, {w - 1}, 0, 0",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def main() -> int:
    # Single-instance lock via local TCP port 47779 so duplicate invocations exit cleanly
    lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_sock.bind(("127.0.0.1", 47779))
    except OSError:
        return 0

    app = QApplication([sys.argv[0]])
    app.setApplicationName("AriaOS Cyber Desktop Shell")
    app.setQuitOnLastWindowClosed(False)
    env = AriaDesktopEnvironment(app)
    env.show_all()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
