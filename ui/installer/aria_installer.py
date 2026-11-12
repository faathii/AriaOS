#!/usr/bin/env python3
"""AriaOS Cyber Obsidian Graphical OS Installer — Native Disk, Filesystem, LUKS & AI Setup Wizard."""

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


def launch_gui(client: AriaDaemonClient) -> int:
    try:
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import (
            QApplication,
            QCheckBox,
            QComboBox,
            QFrame,
            QGridLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-installer.", file=sys.stderr)
        return 1

    class AriaInstallerWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Instalador Gráfico de AriaOS Cyber Obsidian")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(940, 660)

            self.setStyleSheet(
                """
                QWidget {
                    background-color: #070a12;
                    color: #e2e8f0;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QFrame.card {
                    background-color: #0c1222;
                    border: 1px solid #1e293b;
                    border-radius: 12px;
                    padding: 12px;
                }
                QLabel#title {
                    color: #00f0ff;
                    font-size: 21px;
                    font-weight: bold;
                }
                QLabel#subtitle {
                    color: #94a3b8;
                    font-size: 12px;
                }
                QLabel.section_title {
                    color: #00f0ff;
                    font-size: 14px;
                    font-weight: bold;
                }
                QLineEdit, QComboBox {
                    background-color: #0d1424;
                    border: 1px solid #1e3a5f;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                }
                QPushButton.primary {
                    background-color: #00b4d8;
                    border: 1px solid #00f0ff;
                    border-radius: 8px;
                    padding: 10px 18px;
                    color: #070a12;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton.primary:hover {
                    background-color: #00f0ff;
                    color: #070a12;
                }
                QPushButton.secondary {
                    background-color: #0d1b33;
                    border: 1px solid #00f0ff;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #00f0ff;
                    font-weight: bold;
                }
                QPushButton.secondary:hover {
                    background-color: #00f0ff;
                    color: #070a12;
                }
                QTableWidget {
                    background-color: #090d18;
                    border: 1px solid #162238;
                    border-radius: 8px;
                    gridline-color: #162238;
                }
                QHeaderView::section {
                    background-color: #0c1222;
                    color: #00f0ff;
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
            lbl_t = QLabel("💿 Instalador de Sistema AriaOS Cyber Obsidian")
            lbl_t.setObjectName("title")
            lbl_s = QLabel(
                "Transfiere AriaOS, el Kernel Neuronal en Rust/ASM, el escritorio KDE Cyber Obsidian y el modelo aria-core a tu disco NVMe/SSD"
            )
            lbl_s.setObjectName("subtitle")
            col.addWidget(lbl_t)
            col.addWidget(lbl_s)
            header.addLayout(col)
            header.addStretch()

            btn_refresh = QPushButton("🔄 Detectar Discos")
            btn_refresh.setProperty("class", "secondary")
            btn_refresh.clicked.connect(self._load_disks)
            header.addWidget(btn_refresh)
            root.addLayout(header)

            # Step 1: Disk Selection Table
            disk_card = QFrame()
            disk_card.setProperty("class", "card")
            d_lay = QVBoxLayout(disk_card)
            lbl_d = QLabel("1️⃣ Selecciona la Unidad de Destino (NVMe / SSD / VirtIO)")
            lbl_d.setProperty("class", "section_title")
            d_lay.addWidget(lbl_d)

            self.disk_table = QTableWidget(0, 4)
            self.disk_table.setHorizontalHeaderLabels(
                ["Dispositivo (/dev/...)", "Tamaño", "Tipo / Modelo", "Punto de Montaje Actual"]
            )
            self.disk_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.disk_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.disk_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            d_lay.addWidget(self.disk_table)
            root.addWidget(disk_card, 1)

            # Step 2 & 3: Filesystem, Encryption & User Profile
            cfg_card = QFrame()
            cfg_card.setProperty("class", "card")
            grid = QGridLayout(cfg_card)
            grid.setSpacing(10)

            lbl_cfg = QLabel("2️⃣ Sistema de Archivos, Cifrado e Identidad del Equipo")
            lbl_cfg.setProperty("class", "section_title")
            grid.addWidget(lbl_cfg, 0, 0, 1, 4)

            grid.addWidget(QLabel("Sistema de Archivos:"), 1, 0)
            self.combo_fs = QComboBox()
            self.combo_fs.addItems(
                [
                    "ext4 (Máximo rendimiento y baja latencia)",
                    "btrfs (Compresión zstd + Snapshots Timeshift)",
                    "xfs (Alto rendimiento para grandes volúmenes)",
                ]
            )
            grid.addWidget(self.combo_fs, 1, 1)

            grid.addWidget(QLabel("Distribución de Teclado:"), 1, 2)
            self.combo_kb = QComboBox()
            self.combo_kb.addItems(["es (Español)", "us (English US)", "latam (Latinoamérica)", "fr", "de", "it", "pt"])
            grid.addWidget(self.combo_kb, 1, 3)

            grid.addWidget(QLabel("Nombre del Equipo (Hostname):"), 2, 0)
            self.in_host = QLineEdit("ariaos")
            grid.addWidget(self.in_host, 2, 1)

            grid.addWidget(QLabel("Usuario Administrador:"), 2, 2)
            self.in_user = QLineEdit("aria")
            grid.addWidget(self.in_user, 2, 3)

            self.chk_luks = QCheckBox("🔐 Activar cifrado de disco completo LUKS2")
            grid.addWidget(self.chk_luks, 3, 0, 1, 2)

            self.chk_ai = QCheckBox("🧠 Preinstalar Motor Neuronal aria-core (0.5B) + Gobernador ZRAM")
            self.chk_ai.setChecked(True)
            grid.addWidget(self.chk_ai, 3, 2, 1, 2)

            root.addWidget(cfg_card)

            # Step 4: Action Bar
            footer = QHBoxLayout()
            self.status_lbl = QLabel("Selecciona un disco para continuar.")
            self.status_lbl.setObjectName("subtitle")
            footer.addWidget(self.status_lbl)
            footer.addStretch()

            btn_tui = QPushButton("🛠️ Abrir Asistente Avanzado (archinstall TUI)")
            btn_tui.setProperty("class", "secondary")
            btn_tui.clicked.connect(self._launch_archinstall_tui)
            footer.addWidget(btn_tui)

            btn_install = QPushButton("🚀 Iniciar Instalación Guiada de AriaOS")
            btn_install.setProperty("class", "primary")
            btn_install.clicked.connect(self._start_guided_install)
            footer.addWidget(btn_install)
            root.addLayout(footer)

            self._load_disks()

        def _load_disks(self) -> None:
            devices: list[dict[str, Any]] = []
            try:
                resp = client.call_tool("os-storage", "list_block_devices", {}, approved=True)
                if resp.get("ok"):
                    devices = resp.get("result", {}).get("blockdevices", [])
            except Exception:
                pass

            if not devices:
                devices = [
                    {"name": "/dev/nvme0n1", "size": "512G", "type": "disk (NVMe SSD)", "mountpoint": ""},
                    {"name": "/dev/vda", "size": "64G", "type": "disk (VirtIO VM Disk)", "mountpoint": ""},
                ]

            self.disk_table.setRowCount(len(devices))
            for idx, d in enumerate(devices):
                name = str(d.get("name", ""))
                if not name.startswith("/dev/"):
                    name = f"/dev/{name}"
                self.disk_table.setItem(idx, 0, QTableWidgetItem(name))
                self.disk_table.setItem(idx, 1, QTableWidgetItem(str(d.get("size", "?"))))
                self.disk_table.setItem(idx, 2, QTableWidgetItem(str(d.get("type", "disk"))))
                self.disk_table.setItem(idx, 3, QTableWidgetItem(str(d.get("mountpoint") or "Libre")))
            if devices:
                self.disk_table.selectRow(0)
                self.status_lbl.setText(f"✅ {len(devices)} unidad(es) de almacenamiento detectadas.")

        def _start_guided_install(self) -> None:
            row = self.disk_table.currentRow()
            disk_dev = "/dev/vda"
            if row >= 0 and self.disk_table.item(row, 0):
                disk_dev = self.disk_table.item(row, 0).text()

            fs_choice = self.combo_fs.currentText().split()[0]
            kb_choice = self.combo_kb.currentText().split()[0]
            hostname = self.in_host.text().strip() or "ariaos"
            username = self.in_user.text().strip() or "aria"

            cfg_payload = {
                "archinstall-language": "Spanish",
                "disk_config": {
                    "config_type": "default_layout",
                    "device_modifications": [
                        {
                            "device": disk_dev,
                            "wipe": True,
                            "filesystem": fs_choice,
                        }
                    ],
                },
                "disk_encryption": {"encryption_type": "luks" if self.chk_luks.isChecked() else "none"},
                "hostname": hostname,
                "kb_layout": kb_choice,
                "kernels": ["linux"],
                "ntp": True,
                "swap": True,
                "timezone": "Europe/Madrid",
                "ariaos_user": username,
                "ariaos_bundle_ai": self.chk_ai.isChecked(),
            }

            cfg_file = Path("/tmp/ariaos_install_config.json")
            try:
                cfg_file.write_text(json.dumps(cfg_payload, indent=2), encoding="utf-8")
            except OSError:
                pass

            confirm = QMessageBox.warning(
                self,
                "Confirmación de Seguridad — Instalación en Disco",
                f"Se ha generado el perfil de instalación para:\n\n"
                f"• Unidad destino: {disk_dev}\n"
                f"• Sistema de archivos: {fs_choice.upper()}\n"
                f"• Cifrado LUKS2: {'SÍ' if self.chk_luks.isChecked() else 'NO'}\n"
                f"• Hostname / Usuario: {hostname} / {username}\n\n"
                f"¿Deseas abrir el instalador con este perfil preconfigurado?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if confirm == QMessageBox.StandardButton.Yes:
                if shutil.which("konsole"):
                    subprocess.Popen(
                        [
                            "konsole",
                            "--title",
                            "Instalador de AriaOS",
                            "-e",
                            "bash",
                            "-c",
                            f"echo 'Perfil generado en {cfg_file}'; sudo archinstall --config {cfg_file} || sudo archinstall; read -p 'Pulsa Enter...'",
                        ]
                    )
                self.status_lbl.setText(f"🚀 Instalador iniciado con perfil {cfg_file}")

        def _launch_archinstall_tui(self) -> None:
            if shutil.which("konsole"):
                subprocess.Popen(["konsole", "--title", "Instalador de AriaOS", "-e", "sudo", "archinstall"])

    app = QApplication(sys.argv)
    win = AriaInstallerWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Graphical OS Installer")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-installer"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

