#!/usr/bin/env python3
"""AriaOS Intelligent Firewall & Live Connection Monitor — Cyber Obsidian Edition."""

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
        from PyQt6.QtCore import QTimer
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
        print("PyQt6 is required to launch ariaos-firewall.", file=sys.stderr)
        return 1

    class AriaFirewallWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Intelligent Firewall & Socket Monitor")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(960, 660)
            self.lockdown_active = False

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
                QPushButton.danger {
                    background-color: #2a0f18;
                    border: 1px solid #ff2a85;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #ff2a85;
                    font-weight: bold;
                }
                QPushButton.danger:hover {
                    background-color: #ff2a85;
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
            lbl_t = QLabel("🛡️ AriaOS Intelligent Firewall & Live Socket Monitor")
            lbl_t.setObjectName("title")
            self.lbl_sub = QLabel("Inspección TCP/UDP en vivo (/proc/net/tcp & ss), bloqueo de puertos y aislamiento de emergencia")
            self.lbl_sub.setObjectName("subtitle")
            col.addWidget(lbl_t)
            col.addWidget(self.lbl_sub)
            header.addLayout(col)
            header.addStretch()

            self.btn_lockdown = QPushButton("🚨 Activar Aislamiento Total de Red")
            self.btn_lockdown.setProperty("class", "danger")
            self.btn_lockdown.clicked.connect(self._toggle_lockdown)
            header.addWidget(self.btn_lockdown)
            root.addLayout(header)

            # Section 1: Port Rules Management
            rules_card = QFrame()
            rules_card.setProperty("class", "card")
            r_lay = QVBoxLayout(rules_card)
            lbl_r = QLabel("🔒 Reglas Activas de Puertos (nftables / ufw / Kernel Filter)")
            lbl_r.setProperty("class", "section_title")
            r_lay.addWidget(lbl_r)

            form = QHBoxLayout()
            self.in_port = QLineEdit()
            self.in_port.setPlaceholderText("Puerto (1-65535, ej. 8080, 22, 4444)")
            self.combo_proto = QComboBox()
            self.combo_proto.addItems(["tcp", "udp", "both"])
            self.in_comment = QLineEdit()
            self.in_comment.setPlaceholderText("Motivo / Etiqueta (ej. Bloquear puerto dev)")

            btn_block = QPushButton("🚫 Bloquear Puerto")
            btn_block.setProperty("class", "danger")
            btn_block.clicked.connect(lambda: self._add_rule("block"))

            btn_allow = QPushButton("✅ Permitir Puerto")
            btn_allow.setProperty("class", "primary")
            btn_allow.clicked.connect(lambda: self._add_rule("allow"))

            btn_del = QPushButton("🗑️ Eliminar Seleccionada")
            btn_del.setProperty("class", "primary")
            btn_del.clicked.connect(self._delete_selected_rule)

            form.addWidget(self.in_port, 1)
            form.addWidget(self.combo_proto)
            form.addWidget(self.in_comment, 2)
            form.addWidget(btn_block)
            form.addWidget(btn_allow)
            form.addWidget(btn_del)
            r_lay.addLayout(form)

            self.rules_table = QTableWidget(0, 4)
            self.rules_table.setHorizontalHeaderLabels(["Puerto", "Protocolo", "Acción", "Descripción"])
            self.rules_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            self.rules_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.rules_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            r_lay.addWidget(self.rules_table)
            root.addWidget(rules_card, 1)

            # Section 2: Live Connections & Listening Sockets
            conn_card = QFrame()
            conn_card.setProperty("class", "card")
            c_lay = QVBoxLayout(conn_card)
            lbl_c = QLabel("🌐 Conexiones TCP/UDP y Puertos en Escucha en Tiempo Real")
            lbl_c.setProperty("class", "section_title")
            c_lay.addWidget(lbl_c)

            self.conn_table = QTableWidget(0, 5)
            self.conn_table.setHorizontalHeaderLabels(
                ["Protocolo", "Estado", "Dirección Local", "Dirección Remota", "Proceso / Socket"]
            )
            self.conn_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            self.conn_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.conn_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            c_lay.addWidget(self.conn_table)
            root.addWidget(conn_card, 1)

            self.status_lbl = QLabel("Cortafuegos inteligente activo • Refresco cada 3 s")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self._refresh_all)
            self.timer.start(3000)
            self._refresh_all()

        def _refresh_all(self) -> None:
            try:
                f_resp = client.call_tool("security-firewall", "firewall_status", {}, approved=True)
                if f_resp.get("ok"):
                    res = f_resp.get("result", {})
                    self.lockdown_active = bool(res.get("lockdown_mode"))
                    if self.lockdown_active:
                        self.btn_lockdown.setText("🟢 Restaurar Conectividad de Red")
                    else:
                        self.btn_lockdown.setText("🚨 Activar Aislamiento Total de Red")

                    rules: list[dict[str, Any]] = res.get("rules", [])
                    self.rules_table.setRowCount(len(rules))
                    for idx, r in enumerate(rules):
                        self.rules_table.setItem(idx, 0, QTableWidgetItem(str(r.get("port", ""))))
                        self.rules_table.setItem(idx, 1, QTableWidgetItem(str(r.get("protocol", "tcp"))))
                        act = "🚫 BLOQUEADO" if r.get("action") == "block" else "✅ PERMITIDO"
                        self.rules_table.setItem(idx, 2, QTableWidgetItem(act))
                        self.rules_table.setItem(idx, 3, QTableWidgetItem(str(r.get("comment", ""))))

                c_resp = client.call_tool("security-firewall", "active_connections", {"limit": 50}, approved=True)
                if c_resp.get("ok"):
                    conns: list[dict[str, Any]] = c_resp.get("result", {}).get("connections", [])
                    self.conn_table.setRowCount(len(conns))
                    for idx, c in enumerate(conns):
                        self.conn_table.setItem(idx, 0, QTableWidgetItem(str(c.get("proto", ""))))
                        self.conn_table.setItem(idx, 1, QTableWidgetItem(str(c.get("state", ""))))
                        self.conn_table.setItem(idx, 2, QTableWidgetItem(str(c.get("local", ""))))
                        self.conn_table.setItem(idx, 3, QTableWidgetItem(str(c.get("remote", ""))))
                        self.conn_table.setItem(idx, 4, QTableWidgetItem(str(c.get("process", ""))))
            except Exception as exc:
                self.status_lbl.setText(f"Esperando a aria-daemon: {exc}")

        def _add_rule(self, action: str) -> None:
            port_txt = self.in_port.text().strip()
            if not port_txt.isdigit():
                return
            port = int(port_txt)
            proto = self.combo_proto.currentText()
            comment = self.in_comment.text().strip() or f"Regla manual puerto {port}"
            try:
                client.call_tool(
                    "security-firewall",
                    "manage_port_rule",
                    {"action": action, "port": port, "protocol": proto, "comment": comment},
                    approved=True,
                )
                self.in_port.clear()
                self.in_comment.clear()
                self.status_lbl.setText(f"🛡️ Regla aplicada: {action.upper()} puerto {port}/{proto}")
                self._refresh_all()
            except Exception as exc:
                self.status_lbl.setText(f"Error aplicando regla: {exc}")

        def _delete_selected_rule(self) -> None:
            row = self.rules_table.currentRow()
            if row < 0:
                return
            p_item = self.rules_table.item(row, 0)
            pr_item = self.rules_table.item(row, 1)
            if not p_item or not pr_item:
                return
            try:
                client.call_tool(
                    "security-firewall",
                    "manage_port_rule",
                    {"action": "delete", "port": int(p_item.text()), "protocol": pr_item.text()},
                    approved=True,
                )
                self._refresh_all()
            except Exception as exc:
                self.status_lbl.setText(f"Error eliminando regla: {exc}")

        def _toggle_lockdown(self) -> None:
            target = not self.lockdown_active
            try:
                resp = client.call_tool("security-firewall", "network_lockdown", {"enabled": target}, approved=True)
                if resp.get("ok"):
                    st = resp.get("result", {}).get("status", "")
                    self.status_lbl.setText(f"🚨 {st}")
                self._refresh_all()
            except Exception as exc:
                self.status_lbl.setText(f"Error cambiando estado de red: {exc}")

    app = QApplication(sys.argv)
    win = AriaFirewallWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Intelligent Firewall & Socket Monitor")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-firewall"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())
