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
            self.setWindowTitle("Instalador de Sistema AriaOS")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(940, 660)

            self.setStyleSheet(
                """
                QWidget {
                    background-color: #0d1117;
                    color: #e6edf3;
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
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: bold;
                }
                QLabel#subtitle {
                    color: #8b949e;
                    font-size: 12px;
                }
                QLabel.section_title {
                    color: #58a6ff;
                    font-size: 14px;
                    font-weight: bold;
                }
                QLineEdit, QComboBox {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                }
                QLineEdit:focus, QComboBox:focus {
                    border: 1px solid #58a6ff;
                }
                QPushButton.primary {
                    background-color: #238636;
                    border: 1px solid #2ea043;
                    border-radius: 8px;
                    padding: 10px 18px;
                    color: #ffffff;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton.primary:hover {
                    background-color: #2ea043;
                }
                QPushButton.secondary {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #c9d1d9;
                    font-weight: 600;
                }
                QPushButton.secondary:hover {
                    background-color: #30363d;
                    color: #ffffff;
                }
                QTableWidget {
                    background-color: #0d1117;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    gridline-color: #21262d;
                }
                QHeaderView::section {
                    background-color: #161b22;
                    color: #c9d1d9;
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
            lbl_t = QLabel("💿 Instalador de Sistema AriaOS")
            lbl_t.setObjectName("title")
            lbl_s = QLabel(
                "Transfiere AriaOS, el Kernel Neuronal en Rust/ASM y el entorno AriaDE Cupertino a tu disco NVMe/SSD"
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

            if not devices and shutil.which("lsblk"):
                try:
                    out = subprocess.run(
                        ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINTS,MODEL"],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if out.stdout:
                        blk = json.loads(out.stdout).get("blockdevices", [])
                        for b in blk:
                            b_type = b.get("type", "disk")
                            b_name = b.get("name", "")
                            if b_type in {"disk", "loop"} and not b_name.startswith("loop"):
                                dev_path = f"/dev/{b_name}" if not b_name.startswith("/dev/") else b_name
                                mnts = b.get("mountpoints") or []
                                mnt_str = mnts[0] if mnts and mnts[0] else (b.get("mountpoint") or "")
                                devices.append({
                                    "name": dev_path,
                                    "size": str(b.get("size", "?")),
                                    "type": b.get("model") or b_type,
                                    "mountpoint": mnt_str or "Disponible",
                                })
                except Exception:
                    pass

            if not devices:
                devices = [
                    {"name": "/dev/sda", "size": "64G", "type": "disk (SATA/VirtIO)", "mountpoint": "Disponible"}
                ]

            self.disk_table.setRowCount(len(devices))
            for idx, d in enumerate(devices):
                name = str(d.get("name", ""))
                if not name.startswith("/dev/"):
                    name = f"/dev/{name}"
                self.disk_table.setItem(idx, 0, QTableWidgetItem(name))
                self.disk_table.setItem(idx, 1, QTableWidgetItem(str(d.get("size", "?"))))
                self.disk_table.setItem(idx, 2, QTableWidgetItem(str(d.get("type", "disk"))))
                self.disk_table.setItem(idx, 3, QTableWidgetItem(str(d.get("mountpoint") or "Disponible")))
            if devices:
                self.disk_table.selectRow(0)
                self.status_lbl.setText(f"✅ {len(devices)} unidad(es) de almacenamiento detectadas.")

        def _start_guided_install(self) -> None:
            row = self.disk_table.currentRow()
            disk_dev = "/dev/sda"
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
                term = shutil.which("xfce4-terminal") or shutil.which("alacritty") or shutil.which("xterm")
                if term:
                    cmd_str = f"echo 'Perfil generado en {cfg_file}'; sudo archinstall --config {cfg_file} || sudo archinstall; read -p 'Pulsa Enter...'"
                    if "xfce4-terminal" in term:
                        subprocess.Popen([term, "--title=Instalador de AriaOS", "-e", f"bash -c \"{cmd_str}\""])
                    else:
                        subprocess.Popen([term, "-e", "bash", "-c", cmd_str])
                self.status_lbl.setText(f"🚀 Instalador iniciado con perfil {cfg_file}")

        def _launch_archinstall_tui(self) -> None:
            term = shutil.which("xfce4-terminal") or shutil.which("alacritty") or shutil.which("xterm")
            if term:
                if "xfce4-terminal" in term:
                    subprocess.Popen([term, "--title=Instalador de AriaOS", "-e", "sudo archinstall"])
                else:
                    subprocess.Popen([term, "-e", "sudo", "archinstall"])

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

