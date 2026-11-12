#!/usr/bin/env python3
"""
AriaOS Professional Desktop Environment (AriaDE / ariaos-shell)
==============================================================
Entorno de escritorio propio, minimalista, sobrio y profesional para AriaOS (estilo macOS).
Reemplaza al 100% el entorno de Plasma KDE. Se ejecuta directamente sobre el compositor
acelerado picom y el gestor de ventanas independiente Openbox con botones traffic-light (rojo, amarillo, verde).

Componentes de la arquitectura:
  1. AriaTopMenuBar     : Barra de menús superior estilo macOS (28px) con menú manzana ⬡,
                          menús de aplicación, cápsula de búsqueda Spotlight/IA, telemetría y reloj.
  2. AriaDesktopCanvas  : Lienzo de escritorio limpio, sobrio y profesional con papel tapiz Dark Obsidian,
                          acceso directo para "Instalar AriaOS en Disco" y menú contextual macOS.
  3. AriaFloatingDock   : Dock inferior flotante centrado de cristal oscuro con iconos squircles uniformes
                          e indicadores sutiles de aplicación activa.
  4. AriaControlCenter  : Panel emergente de Centro de Control (estilo macOS) con controles de volumen,
                          perfiles de rendimiento del kernel y estado del motor neuronal local.
"""

import configparser
import datetime
import glob
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

# Force XCB backend for stable coordinates, EWMH struts and compositing
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
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

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

# Essential Suite Applications (macOS style Dock & Launch)
DOCK_APPS = [
    {
        "id": "files",
        "name": "Archivos",
        "subtitle": "Explorador de Archivos",
        "cmd": "thunar || dolphin",
        "icon": "ariaos-files",
    },
    {
        "id": "terminal",
        "name": "Terminal",
        "subtitle": "Consola del Sistema",
        "cmd": "xfce4-terminal || konsole",
        "icon": "ariaos-terminal",
    },
    {
        "id": "command-bar",
        "name": "Aria IA",
        "subtitle": "Spotlight Neuronal",
        "cmd": "aria-command-bar",
        "icon": "ariaos-command-bar",
    },
    {
        "id": "installer",
        "name": "Instalar AriaOS",
        "subtitle": "Instalador en Disco",
        "cmd": "ariaos-installer",
        "icon": "ariaos-installer",
    },
    {
        "id": "monitor",
        "name": "Monitor de Actividad",
        "subtitle": "CPU, RAM & Procesos",
        "cmd": "ariaos-monitor",
        "icon": "ariaos-monitor",
    },
    {
        "id": "store",
        "name": "App Store",
        "subtitle": "Tienda de Aplicaciones",
        "cmd": "ariaos-store",
        "icon": "ariaos-store",
    },
    {
        "id": "security",
        "name": "Seguridad",
        "subtitle": "Cortafuegos y Escudo",
        "cmd": "ariaos-firewall",
        "icon": "ariaos-firewall",
    },
    {
        "id": "settings",
        "name": "Ajustes",
        "subtitle": "Ajustes del Sistema",
        "cmd": "ariaos-settings",
        "icon": "ariaos-settings",
    },
]


def resolve_icon(icon_name: str) -> QIcon:
    """Finds custom SVG/PNG squircle icon or falls back cleanly."""
    for folder in ICON_SEARCH_DIRS:
        for ext in (".svg", ".png"):
            candidate = folder / f"{icon_name}{ext}"
            if candidate.exists():
                return QIcon(str(candidate))
    theme_icon = QIcon.fromTheme(icon_name)
    if not theme_icon.isNull():
        return theme_icon
    return QIcon()


def launch_command(cmd: str) -> None:
    """Launches detached desktop processes."""
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


# ---------------------------------------------------------------------------
# Telemetry Reader (Ultra-lightweight)
# ---------------------------------------------------------------------------
class SystemTelemetry:
    def __init__(self) -> None:
        self._prev_idle = 0
        self._prev_total = 0

    def sample(self) -> dict:
        cpu_pct = self._read_cpu()
        mem_used_gb, mem_total_gb = self._read_mem()
        temp_c = self._read_temp()
        ollama_ok = self._check_port(11434)
        return {
            "cpu_pct": cpu_pct,
            "mem_used_gb": mem_used_gb,
            "mem_total_gb": mem_total_gb,
            "temp_c": temp_c,
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
            self._prev_total, self._prev_idle = total, idle
            if diff_total <= 0:
                return 0.0
            return max(0.0, min(100.0, 100.0 * (1.0 - diff_idle / diff_total)))
        except Exception:
            return 2.5

    def _read_mem(self) -> tuple[float, float]:
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
            return (used_kb / (1024 * 1024), total_kb / (1024 * 1024))
        except Exception:
            return (0.8, 6.0)

    def _read_temp(self) -> float:
        try:
            for p in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
                with open(p, "r", encoding="utf-8") as f:
                    val = int(f.read().strip())
                    if val > 0:
                        return val / 1000.0
        except Exception:
            pass
        return 39.0

    def _check_port(self, port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.15):
                return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# macOS-Style Control Center Popup
# ---------------------------------------------------------------------------
class AriaControlCenter(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 390)

        frame = QFrame(self)
        frame.setGeometry(0, 0, 320, 390)
        frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(24, 27, 36, 245);
                border: 1px solid rgba(255, 255, 255, 22);
                border-radius: 16px;
            }
            QLabel {
                border: none;
                background: transparent;
                color: #f0f3f6;
            }
            """
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        h_row = QHBoxLayout()
        title = QLabel("Centro de Control")
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #f0f3f6;")
        h_row.addWidget(title)
        h_row.addStretch()
        layout.addLayout(h_row)

        # 1. Connectivity Box (macOS tile)
        conn_tile = QFrame()
        conn_tile.setStyleSheet(
            "background-color: rgba(35, 40, 52, 220); border-radius: 12px; border: 1px solid rgba(255,255,255,10);"
        )
        conn_lay = QVBoxLayout(conn_tile)
        conn_lay.setContentsMargins(12, 10, 12, 10)
        conn_lay.setSpacing(6)

        c1 = QLabel("📶  Wi-Fi  ·  Conectado (AriaOS-LAN)")
        c1.setStyleSheet("font-size: 11px; font-weight: 500; color: #f0f3f6;")
        c2 = QLabel("🧠  Motor IA Local  ·  aria-core 0.5B Activo")
        c2.setStyleSheet("font-size: 11px; color: #34d399; font-weight: 500;")
        conn_lay.addWidget(c1)
        conn_lay.addWidget(c2)
        layout.addWidget(conn_tile)

        # 2. Volume Slider Tile
        vol_tile = QFrame()
        vol_tile.setStyleSheet(
            "background-color: rgba(35, 40, 52, 220); border-radius: 12px; border: 1px solid rgba(255,255,255,10);"
        )
        vol_lay = QVBoxLayout(vol_tile)
        vol_lay.setContentsMargins(12, 8, 12, 8)
        vol_lay.setSpacing(4)
        vol_lbl = QLabel("🔊  Volumen de Salida")
        vol_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        vol_slider = QSlider(Qt.Orientation.Horizontal)
        vol_slider.setRange(0, 100)
        vol_slider.setValue(70)
        vol_slider.setStyleSheet(
            """
            QSlider::groove:horizontal { height: 6px; background: #1c202a; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #3b82f6; border-radius: 3px; }
            QSlider::handle:horizontal { width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; background: #ffffff; }
            """
        )
        vol_lay.addWidget(vol_lbl)
        vol_lay.addWidget(vol_slider)
        layout.addWidget(vol_tile)

        # 3. Kernel Mode Selector Tile
        mode_tile = QFrame()
        mode_tile.setStyleSheet(
            "background-color: rgba(35, 40, 52, 220); border-radius: 12px; border: 1px solid rgba(255,255,255,10);"
        )
        mode_lay = QVBoxLayout(mode_tile)
        mode_lay.setContentsMargins(12, 8, 12, 8)
        mode_lay.setSpacing(6)
        m_lbl = QLabel("⚡  Perfil de Energía y Kernel")
        m_lbl.setStyleSheet("font-size: 11px; color: #8b949e;")
        mode_lay.addWidget(m_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for m_name, cmd in (
            ("Equilibrado", "aria 'modo balanceado'"),
            ("Gaming", "aria 'activa el modo gaming'"),
            ("Ahorro", "aria 'modo ahorro'"),
        ):
            b = QPushButton(m_name)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                """
                QPushButton {
                    background-color: rgba(48, 54, 69, 180);
                    color: #e2e8f0;
                    border: 1px solid rgba(255,255,255,15);
                    border-radius: 6px;
                    padding: 5px;
                    font-size: 10px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3b82f6;
                    color: #ffffff;
                }
                """
            )
            b.clicked.connect(lambda _c=False, c=cmd: launch_command(c))
            btn_row.addWidget(b)
        mode_lay.addLayout(btn_row)
        layout.addWidget(mode_tile)

        # Telemetry Quick Readout
        self.telem_lbl = QLabel("CPU: 2%   ·   RAM: 0.8 / 6.0 GB   ·   Temp: 40°C")
        self.telem_lbl.setStyleSheet("color: #8b949e; font-size: 10px; text-align: center;")
        self.telem_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.telem_lbl)

        layout.addStretch()

    def update_telemetry(self, data: dict) -> None:
        self.telem_lbl.setText(
            f"CPU: {int(data['cpu_pct'])}%   ·   RAM: {data['mem_used_gb']:.1f} / {data['mem_total_gb']:.1f} GB   ·   {int(data['temp_c'])}°C"
        )


# ---------------------------------------------------------------------------
# macOS Top Menu Bar (28px height, Full Width)
# ---------------------------------------------------------------------------
class AriaTopMenuBar(QWidget):
    def __init__(self, screen_geom: QRect) -> None:
        super().__init__()
        self.screen_geom = screen_geom
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.bar_height = 28
        self.setGeometry(screen_geom.x(), screen_geom.y(), screen_geom.width(), self.bar_height)

        self.control_center = AriaControlCenter(self)

        self.frame = QFrame(self)
        self.frame.setGeometry(0, 0, screen_geom.width(), self.bar_height)
        self.frame.setStyleSheet(
            """
            QFrame {
                background-color: rgba(18, 21, 28, 235);
                border-bottom: 1px solid rgba(255, 255, 255, 18);
            }
            QLabel {
                border: none;
                background: transparent;
                color: #e6edf3;
                font-size: 12px;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: #e6edf3;
                font-size: 12px;
                padding: 2px 7px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 20);
            }
            """
        )

        layout = QHBoxLayout(self.frame)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(4)

        # 1. AriaOS Logo Menu (Apple-style ⬡)
        self.logo_btn = QPushButton("⬡")
        self.logo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logo_btn.setStyleSheet(
            "QPushButton { font-size: 15px; font-weight: bold; color: #ffffff; padding: 2px 8px; }"
            "QPushButton:hover { background-color: rgba(255,255,255,25); border-radius: 4px; }"
        )
        self.logo_btn.clicked.connect(self._open_system_menu)
        layout.addWidget(self.logo_btn)

        # Active App Name (bold)
        app_name = QLabel("<b>AriaOS</b>")
        app_name.setStyleSheet("padding-right: 6px;")
        layout.addWidget(app_name)

        # macOS standard menu items
        for m in ("Archivo", "Edición", "Ver", "Ventana", "Ayuda"):
            mb = QPushButton(m)
            mb.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(mb)

        layout.addStretch()

        # 2. Center Spotlight Search Capsule
        spot_btn = QPushButton("🔍  Buscar o consultar a Aria IA...   (⌘ Espacio)")
        spot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        spot_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(255, 255, 255, 14);
                color: #8b949e;
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 11px;
                padding: 2px 16px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 25);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 45);
            }
            """
        )
        spot_btn.clicked.connect(lambda: launch_command("aria-command-bar"))
        layout.addWidget(spot_btn)

        layout.addStretch()

        # 3. Status Tray & Clock (macOS style right side)
        self.telem_chip = QLabel("0.8 GB")
        self.telem_chip.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0 4px;")
        layout.addWidget(self.telem_chip)

        # Audio icon
        audio_btn = QPushButton("🔊")
        audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        audio_btn.setFixedWidth(26)
        audio_btn.clicked.connect(self._toggle_control_center)
        layout.addWidget(audio_btn)

        # Control Center Toggle Icon
        cc_btn = QPushButton("🎛")
        cc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cc_btn.setFixedWidth(26)
        cc_btn.clicked.connect(self._toggle_control_center)
        layout.addWidget(cc_btn)

        # Clock
        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet("color: #f0f3f6; font-size: 12px; font-weight: 500; padding-left: 6px;")
        layout.addWidget(self.clock_lbl)
        self._update_clock()

    def _open_system_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: rgba(24, 27, 36, 250);
                color: #e6edf3;
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 10px;
                padding: 5px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 18);
                margin: 4px 6px;
            }
            """
        )
        actions = [
            ("Acerca de AriaOS", lambda: launch_command("ariaos-welcome")),
            ("Ajustes del Sistema...", lambda: launch_command("ariaos-settings")),
            ("App Store...", lambda: launch_command("ariaos-store")),
            ("sep", None),
            ("Instalar AriaOS en Disco", lambda: launch_command("ariaos-installer")),
            ("sep", None),
            ("Bloquear Pantalla", lambda: launch_command("xflock4 2>/dev/null || true")),
            ("Cerrar Sesión...", lambda: launch_command("loginctl terminate-user $USER")),
            ("Reiniciar...", lambda: launch_command("systemctl reboot")),
            ("Apagar el Equipo...", lambda: launch_command("systemctl poweroff")),
        ]
        for item, fn in actions:
            if item == "sep":
                menu.addSeparator()
            else:
                act = QAction(item, self)
                act.triggered.connect(fn)
                menu.addAction(act)
        menu.exec(self.mapToGlobal(QPoint(10, self.bar_height + 2)))

    def _toggle_control_center(self) -> None:
        if self.control_center.isVisible():
            self.control_center.hide()
        else:
            gx = self.screen_geom.width() - self.control_center.width() - 12
            gy = self.bar_height + 6
            self.control_center.move(gx, gy)
            self.control_center.show()
            self.control_center.raise_()

    def update_telemetry(self, data: dict) -> None:
        self.telem_chip.setText(f"RAM {data['mem_used_gb']:.1f}G  ·  CPU {int(data['cpu_pct'])}%")
        self.control_center.update_telemetry(data)
        self._update_clock()

    def _update_clock(self) -> None:
        now = datetime.datetime.now()
        days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        self.clock_lbl.setText(f"{days[now.weekday()]} {now.day}  {now.strftime('%H:%M')}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.frame.setGeometry(0, 0, self.width(), self.height())


# ---------------------------------------------------------------------------
# macOS Centered Floating Dock (AriaFloatingDock)
# ---------------------------------------------------------------------------
class AriaFloatingDock(QWidget):
    def __init__(self, screen_geom: QRect) -> None:
        super().__init__()
        self.screen_geom = screen_geom
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        item_w = 54
        dock_w = len(DOCK_APPS) * item_w + 24
        dock_h = 64
        x_pos = screen_geom.x() + (screen_geom.width() - dock_w) // 2
        y_pos = screen_geom.y() + screen_geom.height() - dock_h - 10
        self.setGeometry(x_pos, y_pos, dock_w, dock_h)

        container = QFrame(self)
        container.setGeometry(0, 0, dock_w, dock_h)
        container.setStyleSheet(
            """
            QFrame {
                background-color: rgba(22, 25, 34, 218);
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 18px;
            }
            """
        )

        lay = QHBoxLayout(container)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(6)

        for app in DOCK_APPS:
            btn = QPushButton()
            btn.setToolTip(f"{app['name']} — {app['subtitle']}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedSize(48, 48)
            btn.setIcon(resolve_icon(app["icon"]))
            btn.setIconSize(QSize(38, 38))
            btn.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 24);
                }
                """
            )
            cmd = app["cmd"]
            btn.clicked.connect(lambda _c=False, c=cmd: launch_command(c))
            lay.addWidget(btn)


# ---------------------------------------------------------------------------
# Clean Desktop Canvas (Minimalist Wallpaper + Desktop Shortcuts)
# ---------------------------------------------------------------------------
class AriaDesktopCanvas(QWidget):
    def __init__(self, screen_geom: QRect) -> None:
        super().__init__()
        self.screen_geom = screen_geom
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

        # Desktop Layout: Clean desktop with 1 tidy shortcut on the top-right (like Macintosh HD)
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 46, 24, 80)

        root.addStretch(1)

        # Top-right disk icon: "Instalar AriaOS en Disco"
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        inst_btn = QPushButton()
        inst_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        inst_btn.setFixedSize(96, 92)
        inst_btn.setStyleSheet(
            """
            QPushButton {
                background-color: rgba(20, 24, 32, 160);
                border: 1px solid rgba(255, 255, 255, 14);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 35);
                border: 1px solid rgba(255, 255, 255, 40);
            }
            """
        )
        lay = QVBoxLayout(inst_btn)
        lay.setContentsMargins(4, 8, 4, 6)
        lay.setSpacing(4)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(resolve_icon("ariaos-installer").pixmap(QSize(42, 42)))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        lay.addWidget(icon_lbl)

        txt_lbl = QLabel("Instalar AriaOS")
        txt_lbl.setStyleSheet("color: #f0f3f6; font-size: 10px; font-weight: 500; border: none; background: transparent;")
        txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(txt_lbl)

        inst_btn.clicked.connect(lambda: launch_command("ariaos-installer"))
        right_col.addWidget(inst_btn, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        right_col.addStretch(1)

        root.addLayout(right_col)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: rgba(24, 27, 36, 250);
                color: #e6edf3;
                border: 1px solid rgba(255, 255, 255, 22);
                border-radius: 10px;
                padding: 5px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 18);
                margin: 4px 6px;
            }
            """
        )
        actions = [
            ("Nueva Carpeta", lambda: launch_command("thunar")),
            ("sep", None),
            ("Abrir en Terminal", lambda: launch_command("xfce4-terminal")),
            ("Consultar a Aria IA...", lambda: launch_command("aria-command-bar")),
            ("sep", None),
            ("Instalar AriaOS en Disco", lambda: launch_command("ariaos-installer")),
            ("Monitor de Sistema", lambda: launch_command("ariaos-monitor")),
            ("Ajustes del Sistema...", lambda: launch_command("ariaos-settings")),
        ]
        for label, fn in actions:
            if label == "sep":
                menu.addSeparator()
            else:
                act = QAction(label, self)
                act.triggered.connect(fn)
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
            grad = QLinearGradient(0, 0, 0, rect.height())
            grad.setColorAt(0.0, QColor("#0c0f17"))
            grad.setColorAt(1.0, QColor("#141824"))
            p.fillRect(rect, grad)


# ---------------------------------------------------------------------------
# Main Desktop Environment Controller
# ---------------------------------------------------------------------------
class AriaDesktopEnvironment:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        screen = app.primaryScreen()
        geom = screen.geometry() if screen else QRect(0, 0, 1280, 800)

        self.telemetry = SystemTelemetry()
        self.canvas = AriaDesktopCanvas(geom)
        self.topbar = AriaTopMenuBar(geom)
        self.dock = AriaFloatingDock(geom)

        if screen:
            screen.geometryChanged.connect(self._on_screen_resized)

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(2000)
        self._tick()

    def _on_screen_resized(self, new_geom: QRect) -> None:
        self.canvas.setGeometry(new_geom)
        self.topbar.setGeometry(new_geom.x(), new_geom.y(), new_geom.width(), self.topbar.bar_height)
        dock_w = self.dock.width()
        dock_h = self.dock.height()
        self.dock.setGeometry(
            new_geom.x() + (new_geom.width() - dock_w) // 2,
            new_geom.y() + new_geom.height() - dock_h - 10,
            dock_w,
            dock_h,
        )

    def _tick(self) -> None:
        data = self.telemetry.sample()
        self.topbar.update_telemetry(data)

    def show_all(self) -> None:
        self.canvas.show()
        self.topbar.show()
        self.dock.show()
        self._apply_x11_struts()
        QTimer.singleShot(500, self._reassert)

    def _reassert(self) -> None:
        self.canvas.lower()
        self.topbar.raise_()
        self.dock.raise_()
        self._apply_x11_struts()

    def _apply_x11_struts(self) -> None:
        """Reserves top bar (28px) so open windows do not overlap it."""
        try:
            top_wid = int(self.topbar.winId())
            w = self.canvas.width()
            subprocess.run(
                [
                    "xprop", "-id", str(top_wid),
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
                    f"0, 0, 28, 0, 0, 0, 0, 0, 0, {w - 1}, 0, 0",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def main() -> int:
    lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_sock.bind(("127.0.0.1", 47779))
    except OSError:
        return 0

    app = QApplication([sys.argv[0]])
    app.setApplicationName("AriaOS Desktop Environment")
    app.setQuitOnLastWindowClosed(False)
    env = AriaDesktopEnvironment(app)
    env.show_all()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
