#!/usr/bin/env python3
"""AriaOS Cyber Software & Package Center — Visual Suite Installer, Pacman Browser & System Updater."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
COMMAND_BAR_DIR = HERE.parent / "command-bar"
if str(COMMAND_BAR_DIR) not in sys.path:
    sys.path.insert(0, str(COMMAND_BAR_DIR))
SYSTEM_CB_DIR = Path("/usr/lib/ariaos/command-bar")
if SYSTEM_CB_DIR.exists() and str(SYSTEM_CB_DIR) not in sys.path:
    sys.path.insert(0, str(SYSTEM_CB_DIR))

from aria_ipc import AriaDaemonClient  # noqa: E402

CURATED_SUITES: list[dict[str, str]] = [
    {
        "id": "creative",
        "name": "🎨 Suite Creativa 3D, Foto & Vídeo",
        "apps": "GIMP, Krita, Blender 3D, Inkscape, Darktable, RawTherapee, Kdenlive, HandBrake, Audacity",
        "desc": "Estudio completo de diseño gráfico, modelado 3D, edición de vídeo no lineal y masterización de audio.",
    },
    {
        "id": "dev",
        "name": "💻 Suite Desarrollo, Contenedores & VMs",
        "apps": "VSCodium, Docker, Podman, QEMU/KVM, Virt-Manager, VirtualBox, DBeaver, Insomnia, SQLite",
        "desc": "Entorno profesional de ingeniería de software, bases de datos y virtualización acelerada por hardware.",
    },
    {
        "id": "gaming",
        "name": "🎮 Suite Gaming & Emulación Retro",
        "apps": "Steam, Lutris, Wine, GameMode, MangoHud, RetroArch, PCSX2, RPCS3, DuckStation",
        "desc": "Plataformas de juego nativas, capa Proton/Wine optimizada y emuladores de consolas.",
    },
    {
        "id": "security",
        "name": "🛡️ Suite Seguridad, Cifrado & Backups",
        "apps": "Aria Shield ClamAV, KeePassXC, VeraCrypt, Timeshift, UFW Firewall, Flameshot, Ventoy",
        "desc": "Protección criptográfica de discos, bóveda de contraseñas, snapshots del sistema y cortafuegos.",
    },
    {
        "id": "pentest",
        "name": "🕵️ Suite Auditoría de Red & Reversing",
        "apps": "Nmap, Wireshark, Tcpdump, Gobuster, Nikto, Sqlmap, Hydra, John, Hashcat, Radare2, Cutter, Ghidra",
        "desc": "Laboratorio completo de ciberseguridad defensiva/ofensiva, análisis de paquetes e ingeniería inversa.",
    },
    {
        "id": "multimedia",
        "name": "🎬 Suite Multimedia & Streaming",
        "apps": "OBS Studio, VLC, MPV, Elisa, FreeTube, Stremio",
        "desc": "Transmisión en vivo acelerada por GPU y reproducción universal de medios.",
    },
    {
        "id": "knowledge",
        "name": "📚 Suite Oficina & Segundo Cerebro",
        "apps": "LibreOffice Fresh, Okular PDF, Obsidian, Calibre E-Books",
        "desc": "Documentación técnica, gestión de conocimiento en grafos Markdown y biblioteca digital.",
    },
    {
        "id": "comms",
        "name": "💬 Suite Comunicaciones & Navegadores",
        "apps": "Firefox, Brave, Thunderbird, Telegram, Signal, Element Matrix, Discord",
        "desc": "Mensajería cifrada, clientes de correo y navegadores con bloqueo nativo de rastreadores.",
    },
    {
        "id": "net",
        "name": "🌐 Suite Transferencia & Sincronización P2P",
        "apps": "FileZilla, qBittorrent, Syncthing, Rsync, OpenSSH",
        "desc": "Sincronización continua de carpetas entre dispositivos y transferencia segura FTP/SFTP.",
    },
]


def launch_gui(client: AriaDaemonClient) -> int:
    try:
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import (
            QApplication,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QPushButton,
            QTabWidget,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-store.", file=sys.stderr)
        return 1

    class AriaStoreWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Cyber Software & Package Center")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(960, 660)

            self.setStyleSheet(
                """
                QWidget {
                    background-color: #0d1117;
                    color: #e2e8f0;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QFrame.card {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 12px;
                    padding: 12px;
                }
                QLabel#title {
                    color: #3b82f6;
                    font-size: 20px;
                    font-weight: bold;
                }
                QLabel#subtitle {
                    color: #94a3b8;
                    font-size: 12px;
                }
                QLabel.suite_title {
                    color: #3b82f6;
                    font-size: 14px;
                    font-weight: bold;
                }
                QLabel.suite_apps {
                    color: #38bdf8;
                    font-size: 11px;
                }
                QPushButton.primary {
                    background-color: #0d1b33;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                    padding: 7px 14px;
                    color: #3b82f6;
                    font-weight: bold;
                }
                QPushButton.primary:hover {
                    background-color: #3b82f6;
                    color: #0d1117;
                }
                QLineEdit {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 9px 12px;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #30363d;
                    border-radius: 10px;
                    background-color: #161b22;
                }
                QTabBar::tab {
                    background-color: #161b22;
                    color: #94a3b8;
                    padding: 9px 18px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    margin-right: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #102038;
                    color: #3b82f6;
                    font-weight: bold;
                    border-bottom: 2px solid #3b82f6;
                }
                QTableWidget {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    gridline-color: #30363d;
                }
                QHeaderView::section {
                    background-color: #161b22;
                    color: #3b82f6;
                    padding: 6px;
                    border: none;
                    font-weight: bold;
                }
                """
            )

            root = QVBoxLayout(self)
            root.setContentsMargins(18, 18, 18, 18)
            root.setSpacing(12)

            # Header
            header = QHBoxLayout()
            col = QVBoxLayout()
            t_lbl = QLabel("📦 AriaOS Cyber Software & Package Center")
            t_lbl.setObjectName("title")
            s_lbl = QLabel(
                "Instalador visual de Suites Modulares (55+ Apps), Buscador de Paquetes Arch Linux y Actualizaciones"
            )
            s_lbl.setObjectName("subtitle")
            col.addWidget(t_lbl)
            col.addWidget(s_lbl)
            header.addLayout(col)
            header.addStretch()

            btn_check_upd = QPushButton("🔄 Comprobar Actualizaciones")
            btn_check_upd.setProperty("class", "primary")
            btn_check_upd.clicked.connect(self._check_updates)
            header.addWidget(btn_check_upd)

            btn_install_all = QPushButton("🚀 Instalar Ecosistema Completo (Todas las Suites)")
            btn_install_all.setProperty("class", "primary")
            btn_install_all.clicked.connect(lambda: self._install_suite("all"))
            header.addWidget(btn_install_all)
            root.addLayout(header)

            # Tabs
            self.tabs = QTabWidget()
            self.tabs.addTab(self._build_suites_tab(), "✨ Suites Modulares AriaOS")
            self.tabs.addTab(self._build_pacman_tab(), "🔍 Buscador de Paquetes (pacman)")
            root.addWidget(self.tabs, 1)

            self.status_lbl = QLabel("Conectado al conector nativo os-packages • Listo")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

        def _build_suites_tab(self) -> QWidget:
            page = QWidget()
            grid = QGridLayout(page)
            grid.setContentsMargins(14, 14, 14, 14)
            grid.setSpacing(10)

            for idx, suite in enumerate(CURATED_SUITES):
                card = QFrame()
                card.setProperty("class", "card")
                lay = QVBoxLayout(card)
                lbl_name = QLabel(suite["name"])
                lbl_name.setProperty("class", "suite_title")
                lbl_apps = QLabel(suite["apps"])
                lbl_apps.setProperty("class", "suite_apps")
                lbl_apps.setWordWrap(True)
                lbl_desc = QLabel(suite["desc"])
                lbl_desc.setObjectName("subtitle")
                lbl_desc.setWordWrap(True)

                btn = QPushButton(f"⬇️ Instalar {suite['id'].upper()}")
                btn.setProperty("class", "primary")
                sid = suite["id"]
                btn.clicked.connect(lambda _c=False, s=sid: self._install_suite(s))

                lay.addWidget(lbl_name)
                lay.addWidget(lbl_apps)
                lay.addWidget(lbl_desc)
                lay.addStretch()
                lay.addWidget(btn)
                grid.addWidget(card, idx // 3, idx % 3)

            return page

        def _build_pacman_tab(self) -> QWidget:
            page = QWidget()
            lay = QVBoxLayout(page)
            lay.setContentsMargins(14, 14, 14, 14)
            lay.setSpacing(10)

            search_row = QHBoxLayout()
            self.pkg_input = QLineEdit()
            self.pkg_input.setPlaceholderText(
                "Escribe el nombre de un paquete (ej. neovim, htop, blender, obs-studio, steam)..."
            )
            self.pkg_input.returnPressed.connect(self._search_packages)
            search_row.addWidget(self.pkg_input, 1)

            btn_search = QPushButton("🔍 Buscar en Repositorios")
            btn_search.setProperty("class", "primary")
            btn_search.clicked.connect(self._search_packages)
            search_row.addWidget(btn_search)

            btn_install_pkg = QPushButton("⬇️ Instalar Seleccionado")
            btn_install_pkg.setProperty("class", "primary")
            btn_install_pkg.clicked.connect(self._install_selected_pkg)
            search_row.addWidget(btn_install_pkg)
            lay.addLayout(search_row)

            self.pkg_table = QTableWidget(0, 4)
            self.pkg_table.setHorizontalHeaderLabels(["Repositorio", "Paquete", "Versión", "Descripción"])
            self.pkg_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            self.pkg_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.pkg_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            lay.addWidget(self.pkg_table, 1)

            return page

        def _install_suite(self, suite_id: str) -> None:
            installer = "/usr/bin/ariaos-install-apps"
            if shutil.which("konsole"):
                subprocess.Popen(["konsole", "-e", "bash", "-c", f"{installer} --{suite_id}; read -p 'Pulsa Enter...'"])
                self.status_lbl.setText(f"🚀 Instalando suite '{suite_id}' en terminal Konsole...")
            else:
                self.status_lbl.setText(f"Comando listo: sudo ariaos-install-apps --{suite_id}")

        def _check_updates(self) -> None:
            try:
                resp = client.call_tool("os-packages", "check_system_updates", {}, approved=True)
                if resp.get("ok"):
                    res = resp.get("result", {})
                    cnt = res.get("pending_count", 0)
                    self.status_lbl.setText(f"📦 Actualizaciones pendientes detectadas por pacman: {cnt} paquete(s)")
                else:
                    self.status_lbl.setText(f"Estado de actualizaciones: {resp.get('error', 'sin cambios')}")
            except Exception as exc:
                self.status_lbl.setText(f"Error consultando pacman: {exc}")

        def _search_packages(self) -> None:
            q = self.pkg_input.text().strip()
            if len(q) < 2:
                return
            try:
                resp = client.call_tool("os-packages", "search_packages", {"query": q, "limit": 30}, approved=True)
                if resp.get("ok"):
                    pkgs: list[dict[str, Any]] = resp.get("result", {}).get("results", [])
                    self.pkg_table.setRowCount(len(pkgs))
                    for idx, p in enumerate(pkgs):
                        self.pkg_table.setItem(idx, 0, QTableWidgetItem(str(p.get("repo", ""))))
                        self.pkg_table.setItem(idx, 1, QTableWidgetItem(str(p.get("name", ""))))
                        self.pkg_table.setItem(idx, 2, QTableWidgetItem(str(p.get("version", ""))))
                        self.pkg_table.setItem(idx, 3, QTableWidgetItem(str(p.get("description", ""))))
                    self.status_lbl.setText(f"🔍 {len(pkgs)} paquete(s) encontrados para '{q}'.")
            except Exception as exc:
                self.status_lbl.setText(f"Error buscando paquetes: {exc}")

        def _install_selected_pkg(self) -> None:
            row = self.pkg_table.currentRow()
            if row < 0:
                pkg_name = self.pkg_input.text().strip()
            else:
                item = self.pkg_table.item(row, 1)
                pkg_name = item.text().strip() if item else ""
            if not pkg_name:
                return
            if shutil.which("konsole"):
                subprocess.Popen(
                    [
                        "konsole",
                        "-e",
                        "bash",
                        "-c",
                        f"sudo pacman -S --needed {pkg_name}; read -p 'Pulsa Enter para cerrar...'",
                    ]
                )
                self.status_lbl.setText(f"⬇️ Instalando paquete '{pkg_name}' con pacman...")
            else:
                self.status_lbl.setText(f"Ejecuta: sudo pacman -S {pkg_name}")

    app = QApplication(sys.argv)
    win = AriaStoreWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Cyber Software & Package Center")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-store"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

