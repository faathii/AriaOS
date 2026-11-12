#!/usr/bin/env python3
"""AriaOS Cryptographic Vault & Secret Manager — Cyber Obsidian Edition."""

from __future__ import annotations

import argparse
import json
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
            QComboBox,
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-vault.", file=sys.stderr)
        return 1

    class AriaVaultWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Cryptographic Vault & SSH Key Auditor")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(940, 640)
            self.reveal_mode = False
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
                    font-size: 20px;
                    font-weight: bold;
                }
                QLabel#subtitle {
                    color: #94a3b8;
                    font-size: 12px;
                }
                QLineEdit, QComboBox {
                    background-color: #0d1424;
                    border: 1px solid #1e3a5f;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                }
                QPushButton.primary {
                    background-color: #0d1b33;
                    border: 1px solid #00f0ff;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #00f0ff;
                    font-weight: bold;
                }
                QPushButton.primary:hover {
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

            header = QHBoxLayout()
            col = QVBoxLayout()
            lbl_t = QLabel("🔐 AriaOS Cryptographic Vault & Secret Manager")
            lbl_t.setObjectName("title")
            lbl_sub = QLabel(
                "Bóveda cifrada local (PBKDF2-HMAC-SHA256 100k iter), generador CSPRNG y auditoría de llaves SSH"
            )
            lbl_sub.setObjectName("subtitle")
            col.addWidget(lbl_t)
            col.addWidget(lbl_sub)
            header.addLayout(col)
            header.addStretch()

            self.btn_reveal = QPushButton("👁️ Revelar / Ocultar Secretos")
            self.btn_reveal.setProperty("class", "primary")
            self.btn_reveal.clicked.connect(self._toggle_reveal)
            header.addWidget(self.btn_reveal)
            root.addLayout(header)

            # Store secret & generator card
            card = QFrame()
            card.setProperty("class", "card")
            c_lay = QVBoxLayout(card)

            row1 = QHBoxLayout()
            self.in_label = QLineEdit()
            self.in_label.setPlaceholderText("Nombre del secreto (ej. Token GitHub / Clave Producción)")
            self.combo_cat = QComboBox()
            self.combo_cat.addItems(["password", "api_token", "ssh_key", "note"])
            self.in_val = QLineEdit()
            self.in_val.setPlaceholderText("Valor secreto o pulsa 'Generar Clave Entrópica'")

            btn_gen = QPushButton("🎲 Generar Clave Entrópica")
            btn_gen.setProperty("class", "primary")
            btn_gen.clicked.connect(self._generate_key)

            btn_save = QPushButton("🔒 Cifrar y Guardar")
            btn_save.setProperty("class", "primary")
            btn_save.clicked.connect(self._save_secret)

            row1.addWidget(self.in_label, 1)
            row1.addWidget(self.combo_cat)
            row1.addWidget(self.in_val, 2)
            row1.addWidget(btn_gen)
            row1.addWidget(btn_save)
            c_lay.addLayout(row1)

            self.table = QTableWidget(0, 3)
            self.table.setHorizontalHeaderLabels(["Identificador", "Categoría", "Valor (Cifrado / Descifrado)"])
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            c_lay.addWidget(self.table)
            root.addWidget(card, 1)

            self.status_lbl = QLabel("Bóveda criptográfica verificada • Sin conexión a la nube (100% Local)")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self._refresh()

        def _refresh(self) -> None:
            try:
                rev = "*" if self.reveal_mode else ""
                resp = client.call_tool("security-vault", "list_secrets", {"reveal_label": rev}, approved=True)
                if resp.get("ok"):
                    secrets_list: list[dict[str, Any]] = resp.get("result", {}).get("secrets", [])
                    self.table.setRowCount(len(secrets_list))
                    for idx, s in enumerate(secrets_list):
                        self.table.setItem(idx, 0, QTableWidgetItem(str(s.get("label", ""))))
                        self.table.setItem(idx, 1, QTableWidgetItem(str(s.get("category", ""))))
                        self.table.setItem(idx, 2, QTableWidgetItem(str(s.get("value", ""))))
            except Exception as exc:
                self.status_lbl.setText(f"Esperando a aria-daemon: {exc}")

        def _toggle_reveal(self) -> None:
            self.reveal_mode = not self.reveal_mode
            self._refresh()

        def _generate_key(self) -> None:
            try:
                resp = client.call_tool(
                    "security-vault",
                    "generate_entropy_key",
                    {"length": 28, "include_symbols": True},
                    approved=True,
                )
                if resp.get("ok"):
                    res = resp.get("result", {})
                    self.in_val.setText(str(res.get("generated_key", "")))
                    self.status_lbl.setText(
                        f"🎲 Generada clave de {res.get('entropy_bits')} bits de entropía ({res.get('strength')})"
                    )
            except Exception as exc:
                self.status_lbl.setText(f"Error generando clave: {exc}")

        def _save_secret(self) -> None:
            lbl = self.in_label.text().strip()
            val = self.in_val.text().strip()
            cat = self.combo_cat.currentText()
            if not lbl or not val:
                return
            try:
                client.call_tool(
                    "security-vault",
                    "store_secret",
                    {"label": lbl, "category": cat, "secret_value": val},
                    approved=True,
                )
                self.in_label.clear()
                self.in_val.clear()
                self.status_lbl.setText(f"🔐 Secreto '{lbl}' cifrado y guardado en la bóveda.")
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error guardando secreto: {exc}")

    app = QApplication(sys.argv)
    win = AriaVaultWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Cryptographic Vault & Secret Manager")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-vault"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

