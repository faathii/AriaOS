#!/usr/bin/env python3
"""AriaOS Kernel, GPU & Process Monitor — Cyber Obsidian Real-Time System & Work Mode Manager."""

from __future__ import annotations

import argparse
import json
import os
import signal
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
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QIcon
        from PyQt6.QtWidgets import (
            QApplication,
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMessageBox,
            QProgressBar,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required to launch ariaos-monitor.", file=sys.stderr)
        return 1

    class AriaMonitorWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS Kernel, GPU & Process Monitor")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(980, 680)
            self.processes_cache: list[dict[str, Any]] = []

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
                QLabel.metric_title {
                    color: #94a3b8;
                    font-size: 11px;
                    font-weight: bold;
                }
                QLabel.metric_val {
                    color: #00f0ff;
                    font-family: "Hack", monospace;
                    font-size: 15px;
                    font-weight: bold;
                }
                QProgressBar {
                    background-color: #090d18;
                    border: 1px solid #1e3a5f;
                    border-radius: 6px;
                    height: 14px;
                    text-align: center;
                    font-size: 10px;
                    color: #ffffff;
                }
                QProgressBar::chunk {
                    background-color: #00f0ff;
                    border-radius: 5px;
                }
                QPushButton.mode_btn {
                    background-color: #0d1526;
                    border: 1px solid #1e3a5f;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #cbd5e1;
                    font-weight: bold;
                }
                QPushButton.mode_btn:hover {
                    background-color: #00f0ff;
                    color: #070a12;
                    border-color: #00f0ff;
                }
                QPushButton.action_btn {
                    background-color: #102038;
                    border: 1px solid #00f0ff;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #00f0ff;
                    font-weight: bold;
                }
                QPushButton.action_btn:hover {
                    background-color: #00f0ff;
                    color: #070a12;
                }
                QPushButton.danger_btn {
                    background-color: #2a0f18;
                    border: 1px solid #ff2a85;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #ff2a85;
                    font-weight: bold;
                }
                QPushButton.danger_btn:hover {
                    background-color: #ff2a85;
                    color: #070a12;
                }
                QLineEdit {
                    background-color: #0d1424;
                    border: 1px solid #1e3a5f;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                }
                QTableWidget {
                    background-color: #090d18;
                    border: 1px solid #162238;
                    border-radius: 10px;
                    gridline-color: #162238;
                    selection-background-color: #00f0ff;
                    selection-color: #070a12;
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
            header_row = QHBoxLayout()
            title_col = QVBoxLayout()
            lbl_title = QLabel("⚡ AriaOS Kernel, GPU & Process Monitor")
            lbl_title.setObjectName("title")
            lbl_sub = QLabel(
                "Telemetría x86_64 en tiempo real, Modos de Trabajo del Kernel y Gestor Nativo de Procesos (/proc)"
            )
            lbl_sub.setObjectName("subtitle")
            title_col.addWidget(lbl_title)
            title_col.addWidget(lbl_sub)
            header_row.addLayout(title_col)
            header_row.addStretch()

            self.btn_purge = QPushButton("⚡ Compactar & Liberar RAM")
            self.btn_purge.setProperty("class", "action_btn")
            self.btn_purge.clicked.connect(self._optimize_ram)
            header_row.addWidget(self.btn_purge)
            root.addLayout(header_row)

            # Telemetry Cards Row
            cards_row = QHBoxLayout()
            cards_row.setSpacing(10)

            self.card_cpu = QFrame()
            self.card_cpu.setProperty("class", "card")
            cpu_lay = QVBoxLayout(self.card_cpu)
            self.lbl_cpu_title = QLabel("PROCESADOR & SILICIO x86_64")
            self.lbl_cpu_title.setProperty("class", "metric_title")
            self.lbl_cpu_val = QLabel("Cargando...")
            self.lbl_cpu_val.setProperty("class", "metric_val")
            self.bar_cpu = QProgressBar()
            self.bar_cpu.setRange(0, 100)
            cpu_lay.addWidget(self.lbl_cpu_title)
            cpu_lay.addWidget(self.lbl_cpu_val)
            cpu_lay.addWidget(self.bar_cpu)
            cards_row.addWidget(self.card_cpu, 1)

            self.card_ram = QFrame()
            self.card_ram.setProperty("class", "card")
            ram_lay = QVBoxLayout(self.card_ram)
            self.lbl_ram_title = QLabel("MEMORIA FÍSICA & ZRAM (zstd)")
            self.lbl_ram_title.setProperty("class", "metric_title")
            self.lbl_ram_val = QLabel("Cargando...")
            self.lbl_ram_val.setProperty("class", "metric_val")
            self.bar_ram = QProgressBar()
            self.bar_ram.setRange(0, 100)
            ram_lay.addWidget(self.lbl_ram_title)
            ram_lay.addWidget(self.lbl_ram_val)
            ram_lay.addWidget(self.bar_ram)
            cards_row.addWidget(self.card_ram, 1)

            self.card_gpu = QFrame()
            self.card_gpu.setProperty("class", "card")
            gpu_lay = QVBoxLayout(self.card_gpu)
            self.lbl_gpu_title = QLabel("GPU / DRM & PRESIÓN PSI")
            self.lbl_gpu_title.setProperty("class", "metric_title")
            self.lbl_gpu_val = QLabel("Detectando GPU...")
            self.lbl_gpu_val.setProperty("class", "metric_val")
            self.lbl_psi_val = QLabel("PSI CPU: 0.0% | RAM: 0.0% | IO: 0.0%")
            self.lbl_psi_val.setObjectName("subtitle")
            gpu_lay.addWidget(self.lbl_gpu_title)
            gpu_lay.addWidget(self.lbl_gpu_val)
            gpu_lay.addWidget(self.lbl_psi_val)
            cards_row.addWidget(self.card_gpu, 1)

            root.addLayout(cards_row)

            # Work Modes Strip
            modes_frame = QFrame()
            modes_frame.setProperty("class", "card")
            modes_lay = QHBoxLayout(modes_frame)
            modes_lay.setSpacing(8)
            lbl_m = QLabel("🎛️ Modos del Kernel:")
            lbl_m.setProperty("class", "metric_title")
            modes_lay.addWidget(lbl_m)

            work_modes = [
                ("🎮 Gaming", "gaming"),
                ("💻 Desarrollo", "development"),
                ("🎨 Creativo", "creative"),
                ("🔋 Ahorro Extremo", "powersave"),
                ("🛡️ Seguridad", "security"),
                ("⚡ Equilibrado", "balanced"),
            ]
            for label, mode_id in work_modes:
                btn = QPushButton(label)
                btn.setProperty("class", "mode_btn")
                btn.clicked.connect(lambda _c=False, m=mode_id: self._activate_mode(m))
                modes_lay.addWidget(btn)
            root.addWidget(modes_frame)

            # Filter & Process Controls
            filter_row = QHBoxLayout()
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText("🔍 Filtrar procesos por nombre o PID...")
            self.search_input.textChanged.connect(self._render_process_table)
            filter_row.addWidget(self.search_input, 1)

            self.btn_term = QPushButton("🛑 Terminar (SIGTERM)")
            self.btn_term.setProperty("class", "danger_btn")
            self.btn_term.clicked.connect(lambda: self._kill_selected(signal.SIGTERM))
            filter_row.addWidget(self.btn_term)

            self.btn_kill = QPushButton("💀 Forzar Cierre (SIGKILL)")
            self.btn_kill.setProperty("class", "danger_btn")
            self.btn_kill.clicked.connect(lambda: self._kill_selected(signal.SIGKILL))
            filter_row.addWidget(self.btn_kill)
            root.addLayout(filter_row)

            # Process Table
            self.table = QTableWidget(0, 4)
            self.table.setHorizontalHeaderLabels(["PID", "Proceso / Comando", "RAM (MB)", "Uso RAM (%)"])
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            root.addWidget(self.table, 1)

            self.status_bar = QLabel("Enlazado con aria-daemon • Refresco automático cada 2.5 s")
            self.status_bar.setObjectName("subtitle")
            root.addWidget(self.status_bar)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self._refresh_all)
            self.timer.start(2500)
            self._refresh_all()
            self._refresh_gpu()

        def _refresh_gpu(self) -> None:
            try:
                resp = client.call_tool("os-power-modes", "gpu_telemetry", {}, approved=True)
                res = resp.get("result", {})
                adapters = res.get("adapters", [])
                pci = res.get("pci_display_controllers", [])
                if adapters:
                    a = adapters[0]
                    drv = a.get("driver", "drm")
                    busy = a.get("busy_pct", 0)
                    vram = a.get("vram_used_mb")
                    vram_str = f" • VRAM: {vram} MB" if vram is not None else ""
                    self.lbl_gpu_val.setText(f"{a.get('card', 'GPU0')} [{drv}] • {busy}%{vram_str}")
                elif pci:
                    short_name = pci[0].split(":")[-1].strip()[:36]
                    self.lbl_gpu_val.setText(short_name)
                else:
                    self.lbl_gpu_val.setText("Adaptador Gráfico KMS/DRM Activo")
            except Exception:
                self.lbl_gpu_val.setText("Adaptador Gráfico KMS/DRM Activo")

        def _refresh_all(self) -> None:
            try:
                k_resp = client.kernel_telemetry()
                if k_resp.get("ok") and "telemetry" in k_resp:
                    t = k_resp["telemetry"]
                    cpu = t.get("cpu", {})
                    mem = t.get("memory", {})
                    psi = t.get("psi", {})
                    load = t.get("load_avg", [0.0])[0]
                    cores = max(1, int(cpu.get("cores", 1)))
                    cpu_pct = min(100, int((load / cores) * 100))
                    avx = "AVX2" if t.get("silicon", {}).get("avx2") else "SSE4.2"

                    self.lbl_cpu_val.setText(f"{cores} Hilos [{avx}] • Carga: {load:.2f}")
                    self.bar_cpu.setValue(cpu_pct)

                    used = mem.get("used_mb", 0)
                    total = mem.get("total_mb", 1)
                    pct = int(mem.get("usage_pct", 0))
                    self.lbl_ram_val.setText(f"{used} / {total} MB ({pct}%)")
                    self.bar_ram.setValue(pct)

                    self.lbl_psi_val.setText(
                        f"PSI CPU: {psi.get('cpu_avg10', 0.0):.1f}% | "
                        f"RAM: {psi.get('memory_avg10', 0.0):.1f}% | "
                        f"IO: {psi.get('io_avg10', 0.0):.1f}%"
                    )

                p_resp = client.call_tool("os-system", "list_top_processes", {"limit": 35}, approved=True)
                if p_resp.get("ok"):
                    self.processes_cache = p_resp.get("result", {}).get("processes", [])
                    self._render_process_table()
            except Exception as exc:
                self.status_bar.setText(f"⚠️ Esperando a aria-daemon: {exc}")

        def _render_process_table(self) -> None:
            query = self.search_input.text().strip().lower()
            filtered = [
                p
                for p in self.processes_cache
                if not query
                or query in str(p.get("pid", "")).lower()
                or query in str(p.get("command", "")).lower()
            ]
            self.table.setRowCount(len(filtered))
            for row_idx, proc in enumerate(filtered):
                pid = str(proc.get("pid", ""))
                cmd = str(proc.get("command", ""))
                rss = str(proc.get("rss_mb", 0))
                pct = f"{float(proc.get('mem_percent', 0.0)):.1f}%"
                self.table.setItem(row_idx, 0, QTableWidgetItem(pid))
                self.table.setItem(row_idx, 1, QTableWidgetItem(cmd))
                self.table.setItem(row_idx, 2, QTableWidgetItem(rss))
                self.table.setItem(row_idx, 3, QTableWidgetItem(pct))

        def _optimize_ram(self) -> None:
            try:
                res = client.optimize_kernel()
                freed = res.get("freed_mb", 0)
                avail = res.get("after_available_mb", 0)
                self.status_bar.setText(
                    f"⚡ RAM compactada en el Kernel: +{freed} MB liberados ({avail} MB disponibles)"
                )
                self._refresh_all()
            except Exception as exc:
                self.status_bar.setText(f"Error al optimizar RAM: {exc}")

        def _activate_mode(self, mode_id: str) -> None:
            try:
                resp = client.call_tool(
                    "os-power-modes",
                    "apply_work_mode",
                    {"mode": mode_id, "launch_apps": False},
                    approved=True,
                )
                client.optimize_kernel()
                if resp.get("ok"):
                    r = resp.get("result", {})
                    self.status_bar.setText(
                        f"{r.get('icon', '⚡')} Activado: {r.get('name', mode_id)} — {r.get('description', '')}"
                    )
                self._refresh_all()
            except Exception as exc:
                self.status_bar.setText(f"Error activando modo {mode_id}: {exc}")

        def _kill_selected(self, sig: int) -> None:
            row = self.table.currentRow()
            if row < 0:
                return
            pid_item = self.table.item(row, 0)
            cmd_item = self.table.item(row, 1)
            if not pid_item:
                return
            pid = int(pid_item.text())
            name = cmd_item.text() if cmd_item else str(pid)
            ans = QMessageBox.question(
                self,
                "Confirmar terminación de proceso",
                f"¿Enviar señal {sig} al proceso '{name}' (PID {pid})?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if ans == QMessageBox.StandardButton.Yes:
                try:
                    os.kill(pid, sig)
                    self.status_bar.setText(f"✅ Señal enviada a {name} (PID {pid})")
                    self._refresh_all()
                except OSError as exc:
                    QMessageBox.warning(self, "Error", f"No se pudo terminar PID {pid}: {exc}")

    app = QApplication(sys.argv)
    win = AriaMonitorWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Kernel, GPU & Process Monitor")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-monitor"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())
