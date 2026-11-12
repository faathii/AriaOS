#!/usr/bin/env python3
"""AriaOS Network Radar, LAN Scanner & Private DNS — Cyber Obsidian Edition."""

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
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-netradar.", file=sys.stderr)
        return 1

    class AriaNetRadarWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Network Radar — Escáner LAN y DNS Cifrado")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(940, 640)
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
                QComboBox {
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
            lbl_t = QLabel("🌐 AriaOS Network Radar, LAN Scanner & Private DNS")
            lbl_t.setObjectName("title")
            lbl_sub = QLabel(
                "Descubrimiento de nodos en tu red local (ARP/NDP), DNS anti-rastreo y radar de latencia"
            )
            lbl_sub.setObjectName("subtitle")
            col.addWidget(lbl_t)
            col.addWidget(lbl_sub)
            header.addLayout(col)
            header.addStretch()

            btn_scan = QPushButton("📡 Escanear Red y Latencia")
            btn_scan.setProperty("class", "primary")
            btn_scan.clicked.connect(self._refresh)
            header.addWidget(btn_scan)
            root.addLayout(header)

            # DNS Selector Card
            dns_card = QFrame()
            dns_card.setProperty("class", "card")
            d_lay = QHBoxLayout(dns_card)
            lbl_d = QLabel("🛡️ Proveedor DNS Privado y Anti-Tracking:")
            lbl_d.setProperty("class", "section_title")
            self.combo_dns = QComboBox()
            self.combo_dns.addItems(["cloudflare", "quad9", "mullvad", "google", "dhcp"])
            btn_dns = QPushButton("Aplicar DNS Seguro")
            btn_dns.setProperty("class", "primary")
            btn_dns.clicked.connect(self._apply_dns)
            d_lay.addWidget(lbl_d)
            d_lay.addWidget(self.combo_dns, 1)
            d_lay.addWidget(btn_dns)
            root.addWidget(dns_card)

            # LAN Devices Table
            lan_card = QFrame()
            lan_card.setProperty("class", "card")
            l_lay = QVBoxLayout(lan_card)
            lbl_l = QLabel("📶 Dispositivos Detectados en la Red Local (LAN / Wi-Fi)")
            lbl_l.setProperty("class", "section_title")
            l_lay.addWidget(lbl_l)

            self.lan_table = QTableWidget(0, 5)
            self.lan_table.setHorizontalHeaderLabels(["Dirección IP", "Dirección MAC", "Interfaz", "Estado", "Tipo"])
            self.lan_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            self.lan_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            l_lay.addWidget(self.lan_table)
            root.addWidget(lan_card, 1)

            # Latency Table
            lat_card = QFrame()
            lat_card.setProperty("class", "card")
            lat_lay = QVBoxLayout(lat_card)
            lbl_lat = QLabel("⚡ Radar de Latencia Global")
            lbl_lat.setProperty("class", "section_title")
            lat_lay.addWidget(lbl_lat)

            self.lat_table = QTableWidget(0, 4)
            self.lat_table.setHorizontalHeaderLabels(["Nodo Global", "IP", "Latencia (ms)", "Estado"])
            self.lat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self.lat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            lat_lay.addWidget(self.lat_table)
            root.addWidget(lat_card, 1)

            self.status_lbl = QLabel("Radar de red preparado")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self._refresh()

        def _refresh(self) -> None:
            try:
                l_resp = client.call_tool("network-radar", "scan_lan_devices", {}, approved=True)
                if l_resp.get("ok"):
                    devs: list[dict[str, Any]] = l_resp.get("result", {}).get("devices", [])
                    self.lan_table.setRowCount(len(devs))
                    for idx, d in enumerate(devs):
                        self.lan_table.setItem(idx, 0, QTableWidgetItem(str(d.get("ip", ""))))
                        self.lan_table.setItem(idx, 1, QTableWidgetItem(str(d.get("mac", ""))))
                        self.lan_table.setItem(idx, 2, QTableWidgetItem(str(d.get("interface", ""))))
                        self.lan_table.setItem(idx, 3, QTableWidgetItem(str(d.get("state", ""))))
                        self.lan_table.setItem(idx, 4, QTableWidgetItem(str(d.get("type", ""))))

                r_resp = client.call_tool("network-radar", "latency_radar", {}, approved=True)
                if r_resp.get("ok"):
                    nodes: list[dict[str, Any]] = r_resp.get("result", {}).get("nodes", [])
                    self.lat_table.setRowCount(len(nodes))
                    for idx, n in enumerate(nodes):
                        self.lat_table.setItem(idx, 0, QTableWidgetItem(str(n.get("node", ""))))
                        self.lat_table.setItem(idx, 1, QTableWidgetItem(str(n.get("ip", ""))))
                        self.lat_table.setItem(idx, 2, QTableWidgetItem(str(n.get("latency_ms", ""))))
                        self.lat_table.setItem(idx, 3, QTableWidgetItem(str(n.get("status", ""))))
            except Exception as exc:
                self.status_lbl.setText(f"Esperando a aria-daemon: {exc}")

        def _apply_dns(self) -> None:
            prov = self.combo_dns.currentText()
            try:
                resp = client.call_tool(
                    "network-radar",
                    "set_secure_dns",
                    {"provider": prov, "adblock_hosts": True},
                    approved=True,
                )
                if resp.get("ok"):
                    res = resp.get("result", {})
                    self.status_lbl.setText(
                        f"🛡️ DNS activo: {res.get('provider_label')} -> {res.get('servers')}"
                    )
            except Exception as exc:
                self.status_lbl.setText(f"Error aplicando DNS: {exc}")

    app = QApplication(sys.argv)
    win = AriaNetRadarWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Network Radar, LAN Scanner & Private DNS")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-netradar"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

