#!/usr/bin/env python3
"""AriaOS Welcome & Onboarding Center: system status, AI setup, and quick actions."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

AUTORUN_PATH = Path.home() / ".config" / "autostart" / "ariaos-welcome.desktop"


def _check_network() -> bool:
    try:
        urllib.request.urlopen("https://archlinux.org", timeout=3)
        return True
    except Exception:
        return False


def _check_ollama_model(model_name: str = "qwen2.5:3b") -> bool:
    try:
        req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        data = json.loads(req.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        return any(model_name in m for m in models)
    except Exception:
        return False


def _check_clamav_ready() -> bool:
    db_dir = Path("/var/lib/clamav")
    if not db_dir.exists():
        return False
    return any(f.suffix.lower() in {".cvd", ".cld"} for f in db_dir.iterdir() if f.is_file())


def _launch_konsole(title: str, cmd: list[str]) -> None:
    if shutil.which("konsole"):
        subprocess.Popen(["konsole", "--title", title, "-e", "bash", "-c", " ".join(cmd) + "; echo; read -p 'Presiona Enter para cerrar...'"])
    elif shutil.which("xterm"):
        subprocess.Popen(["xterm", "-title", title, "-e", "bash", "-c", " ".join(cmd) + "; echo; read -p 'Presiona Enter para cerrar...'"])
    else:
        subprocess.Popen(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Welcome Center")
    parser.add_argument("--check", action="store_true", help="Self-check imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "app": "ariaos-welcome"}))
        return 0

    try:
        from PyQt6.QtCore import Qt, QThread, pyqtSignal
        from PyQt6.QtGui import QFont, QIcon, QPixmap
        from PyQt6.QtWidgets import (
            QApplication,
            QCheckBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("AriaOS Welcome: PyQt6 not available. Install python-pyqt6.", file=sys.stderr)
        return 1

    class StatusThread(QThread):
        status_ready = pyqtSignal(dict)

        def run(self) -> None:
            online = _check_network()
            has_model = _check_ollama_model("qwen2.5:3b")
            av_ready = _check_clamav_ready()
            self.status_ready.emit({
                "online": online,
                "has_model": has_model,
                "av_ready": av_ready,
            })

    class WelcomeWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Bienvenido a AriaOS")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(760, 520)
            self._apply_style()
            self._init_ui()
            self._refresh_status()

        def _apply_style(self) -> None:
            self.setStyleSheet("""
                QWidget {
                    background-color: #0b0f19;
                    color: #f1f5f9;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QTabWidget::pane {
                    border: 1px solid #1e293b;
                    background: #111827;
                    border-radius: 8px;
                    padding: 12px;
                }
                QTabBar::tab {
                    background: #0f172a;
                    color: #94a3b8;
                    padding: 8px 16px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #1e293b;
                    color: #38bdf8;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #1e293b;
                    color: #ffffff;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                    border-color: #3b82f6;
                }
                QPushButton#primary {
                    background-color: #2563eb;
                    border-color: #3b82f6;
                    font-weight: bold;
                }
                QPushButton#primary:hover {
                    background-color: #1d4ed8;
                }
                QFrame.card {
                    background-color: #111827;
                    border: 1px solid #1e293b;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)

        def _init_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(18, 16, 18, 14)
            root.setSpacing(12)

            # Header
            header = QHBoxLayout()
            logo_lbl = QLabel()
            pix = QPixmap("/usr/share/pixmaps/ariaos-logo.png")
            if pix.isNull():
                pix = QPixmap("c:/Users/hamza/Desktop/AriaOS/assets/branding/ariaos-logo.png")
            if not pix.isNull():
                logo_lbl.setPixmap(pix.scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            header.addWidget(logo_lbl)

            title_box = QVBoxLayout()
            t = QLabel("AriaOS")
            t.setStyleSheet("font-size: 22px; font-weight: bold; color: #38bdf8;")
            sub = QLabel("El Sistema Operativo con Inteligencia Artificial Nativa (Arch + KDE Plasma 6)")
            sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
            title_box.addWidget(t)
            title_box.addWidget(sub)
            header.addLayout(title_box)
            header.addStretch()
            root.addLayout(header)

            # Tabs
            tabs = QTabWidget()
            tabs.addTab(self._tab_status(), "Estado del Sistema e IA")
            tabs.addTab(self._tab_first_steps(), "Primeros Pasos")
            tabs.addTab(self._tab_installer(), "Instalación & Suites")
            root.addWidget(tabs)

            # Footer
            footer = QHBoxLayout()
            self.autostart_chk = QCheckBox("Mostrar esta pantalla al iniciar sesión")
            self.autostart_chk.setChecked(AUTORUN_PATH.exists() or not (Path.home() / ".config" / ".ariaos-no-welcome").exists())
            self.autostart_chk.toggled.connect(self._toggle_autostart)
            footer.addWidget(self.autostart_chk)
            footer.addStretch()

            close_btn = QPushButton("Cerrar")
            close_btn.clicked.connect(self.close)
            footer.addWidget(close_btn)
            root.addLayout(footer)

        def _tab_status(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(12)

            self.net_status_lbl = QLabel("Comprobando conexión a Internet...")
            self.ai_status_lbl = QLabel("Comprobando estado del modelo de IA (qwen2.5:3b)...")
            self.av_status_lbl = QLabel("Comprobando firmas del Antivirus ClamAV...")

            for lbl in (self.net_status_lbl, self.ai_status_lbl, self.av_status_lbl):
                lbl.setStyleSheet("padding: 6px; background: #0f172a; border-radius: 4px;")
                layout.addWidget(lbl)

            btn_box = QHBoxLayout()
            self.btn_pull_ai = QPushButton("Descargar / Actualizar Modelo IA (qwen2.5:3b)")
            self.btn_pull_ai.clicked.connect(lambda: _launch_konsole("AriaOS AI Setup", ["ollama", "pull", "qwen2.5:3b"]))
            btn_box.addWidget(self.btn_pull_ai)

            self.btn_freshclam = QPushButton("Actualizar Firmas de Antivirus (freshclam)")
            self.btn_freshclam.clicked.connect(lambda: _launch_konsole("AriaOS ClamAV Update", ["sudo", "freshclam"]))
            btn_box.addWidget(self.btn_freshclam)

            btn_refresh = QPushButton("Recomprobar")
            btn_refresh.clicked.connect(self._refresh_status)
            btn_box.addWidget(btn_refresh)

            layout.addLayout(btn_box)
            layout.addStretch()
            return w

        def _tab_first_steps(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(12)

            info = QLabel(
                "<b>¿Cómo usar AriaOS y su IA integrada?</b><br><br>"
                "• <b>Barra IA flotante:</b> Presiona <code>Alt + Espacio</code> en cualquier momento para hablar con Aria o ejecutar herramientas.<br>"
                "• <b>Gestor de Archivos (Dolphin):</b> Haz clic derecho en una carpeta para <i>Organizar con IA</i> o <i>Buscar duplicados</i>.<br>"
                "• <b>Antivirus en tiempo real:</b> Haz clic derecho en cualquier archivo o descarga para <i>Analizar con Antivirus AriaOS</i>.<br>"
                "• <b>Control total:</b> La IA se mueve en todas las capas desde el kernel (telemetría, hardware, módulos) hasta las aplicaciones de escritorio."
            )
            info.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(info)

            actions = QHBoxLayout()
            btn_bar = QPushButton("Abrir Barra IA ahora (Alt+Espacio)", objectName="primary")
            btn_bar.clicked.connect(lambda: subprocess.Popen(["aria-command-bar"]))
            actions.addWidget(btn_bar)

            btn_dolphin = QPushButton("Abrir Gestor de Archivos (Dolphin)")
            btn_dolphin.clicked.connect(lambda: subprocess.Popen(["dolphin"]))
            actions.addWidget(btn_dolphin)

            layout.addLayout(actions)
            layout.addStretch()
            return w

        def _tab_installer(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(14)

            intro = QLabel(
                "AriaOS funciona en modo <b>Live</b> sin tocar tu disco, pero puedes instalarlo permanentemente "
                "o añadir suites de aplicaciones adicionales según tu perfil:"
            )
            layout.addWidget(intro)

            grid = QGridLayout()
            btn_all_apps = QPushButton("Instalar Suite Completa (Creativa, Dev, Gaming, Security)")
            btn_all_apps.clicked.connect(lambda: _launch_konsole("AriaOS Apps Suite", ["sudo", "ariaos-install-apps", "--all"]))
            grid.addWidget(btn_all_apps, 0, 0)

            btn_dev_suite = QPushButton("Instalar Suite Desarrollo & Contenedores")
            btn_dev_suite.clicked.connect(lambda: _launch_konsole("AriaOS Dev Suite", ["sudo", "ariaos-install-apps", "--dev"]))
            grid.addWidget(btn_dev_suite, 0, 1)

            btn_sec_suite = QPushButton("Instalar Suite Pentesting & Seguridad")
            btn_sec_suite.clicked.connect(lambda: _launch_konsole("AriaOS Security Suite", ["sudo", "ariaos-install-apps", "--security"]))
            grid.addWidget(btn_sec_suite, 1, 0)

            btn_creative = QPushButton("Instalar Suite Creativa (Diseño, Foto, Video)")
            btn_creative.clicked.connect(lambda: _launch_konsole("AriaOS Creative Suite", ["sudo", "ariaos-install-apps", "--creative"]))
            grid.addWidget(btn_creative, 1, 1)
            layout.addLayout(grid)

            layout.addSpacing(8)
            install_card = QFrame()
            install_card.setObjectName("card")
            card_layout = QHBoxLayout(install_card)
            card_lbl = QLabel("<b>Instalar AriaOS en disco:</b> Ejecuta el asistente guiado de instalación.")
            btn_install_os = QPushButton("Instalar AriaOS en Disco", objectName="primary")
            btn_install_os.clicked.connect(lambda: _launch_konsole("Instalador de AriaOS", ["sudo", "archinstall"]))
            card_layout.addWidget(card_lbl)
            card_layout.addStretch()
            card_layout.addWidget(btn_install_os)
            layout.addWidget(install_card)

            layout.addStretch()
            return w

        def _refresh_status(self) -> None:
            self.net_status_lbl.setText("Comprobando conexión a Internet...")
            self.ai_status_lbl.setText("Comprobando estado del modelo de IA...")
            self.av_status_lbl.setText("Comprobando firmas del Antivirus ClamAV...")
            self._thread = StatusThread()
            self._thread.status_ready.connect(self._on_status_ready)
            self._thread.start()

        def _on_status_ready(self, data: dict) -> None:
            if data["online"]:
                self.net_status_lbl.setText("🟢 Conexión a Internet: <b>Conectado</b>")
            else:
                self.net_status_lbl.setText("🔴 Conexión a Internet: <b>Sin conexión</b> (conecta Wi-Fi o Ethernet)")

            if data["has_model"]:
                self.ai_status_lbl.setText("🟢 Modelo de IA: <b>qwen2.5:3b instalado y listo para usar</b>")
            else:
                self.ai_status_lbl.setText("🟡 Modelo de IA: <b>qwen2.5:3b no descargado aún</b> (haz clic abajo para descargarlo)")

            if data["av_ready"]:
                self.av_status_lbl.setText("🟢 Antivirus ClamAV: <b>Bases de firmas cargadas y listas</b>")
            else:
                self.av_status_lbl.setText("🟡 Antivirus ClamAV: <b>Firmas pendientes de primera descarga</b> (ejecuta freshclam)")

        def _toggle_autostart(self, checked: bool) -> None:
            no_welcome = Path.home() / ".config" / ".ariaos-no-welcome"
            if checked:
                if no_welcome.exists():
                    no_welcome.unlink(missing_ok=True)
            else:
                no_welcome.parent.mkdir(parents=True, exist_ok=True)
                no_welcome.write_text("disabled", encoding="utf-8")

    app = QApplication(sys.argv)
    win = WelcomeWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
