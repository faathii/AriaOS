#!/usr/bin/env python3
"""AriaOS Neural Core & Local LLM Studio — Cyber Obsidian Edition."""

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
        print("PyQt6 is required to launch ariaos-ai-studio.", file=sys.stderr)
        return 1

    class AriaAIStudioWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("AriaOS AI Studio — Laboratorio de Modelos Locales y Memoria Neuronal")
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
                QLabel.section_title {
                    color: #3b82f6;
                    font-size: 14px;
                    font-weight: bold;
                }
                QLineEdit {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: #ffffff;
                }
                QPushButton.primary {
                    background-color: #0d1b33;
                    border: 1px solid #3b82f6;
                    border-radius: 8px;
                    padding: 8px 14px;
                    color: #3b82f6;
                    font-weight: bold;
                }
                QPushButton.primary:hover {
                    background-color: #3b82f6;
                    color: #0d1117;
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

            header = QHBoxLayout()
            col = QVBoxLayout()
            lbl_t = QLabel("🚀 AriaOS AI Studio & Neural Memory Manager")
            lbl_t.setObjectName("title")
            self.lbl_sub = QLabel(
                "Control del modelo local de IA, benchmark de inferencia CPU/GPU y edición de la memoria neuronal"
            )
            self.lbl_sub.setObjectName("subtitle")
            col.addWidget(lbl_t)
            col.addWidget(self.lbl_sub)
            header.addLayout(col)
            header.addStretch()

            btn_bench = QPushButton("⚡ Ejecutar Benchmark de Inferencia")
            btn_bench.setProperty("class", "primary")
            btn_bench.clicked.connect(self._run_benchmark)
            header.addWidget(btn_bench)
            root.addLayout(header)

            # Card 1: Models
            m_card = QFrame()
            m_card.setProperty("class", "card")
            m_lay = QVBoxLayout(m_card)
            lbl_m = QLabel("🧠 Modelos Locales de IA (Ollama & Aria-Core Kernel Weights)")
            lbl_m.setProperty("class", "section_title")
            m_lay.addWidget(lbl_m)

            self.models_table = QTableWidget(0, 5)
            self.models_table.setHorizontalHeaderLabels(
                ["Modelo", "Tamaño (MB)", "Cuantización", "Rol / Especialidad", "Estado"]
            )
            self.models_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
            self.models_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.models_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            m_lay.addWidget(self.models_table)

            btn_switch = QPushButton("🎯 Activar Modelo Seleccionado como Cerebro del OS")
            btn_switch.setProperty("class", "primary")
            btn_switch.clicked.connect(self._switch_selected_model)
            m_lay.addWidget(btn_switch)
            root.addWidget(m_card, 1)

            # Card 2: Neural Memory Aliases
            mem_card = QFrame()
            mem_card.setProperty("class", "card")
            mem_lay = QVBoxLayout(mem_card)
            lbl_mem = QLabel("🧬 Memoria Neuronal Persistente (Alias y Órdenes Aprendidas)")
            lbl_mem.setProperty("class", "section_title")
            mem_lay.addWidget(lbl_mem)

            a_row = QHBoxLayout()
            self.in_trig = QLineEdit()
            self.in_trig.setPlaceholderText("Frase corta / Disparador (ej. 'modo streamer')")
            self.in_targ = QLineEdit()
            self.in_targ.setPlaceholderText("Acción o comando objetivo (ej. 'modo creativo')")
            btn_add_alias = QPushButton("➕ Enseñar Nuevo Hábito a Aria")
            btn_add_alias.setProperty("class", "primary")
            btn_add_alias.clicked.connect(self._add_alias)
            a_row.addWidget(self.in_trig, 1)
            a_row.addWidget(self.in_targ, 2)
            a_row.addWidget(btn_add_alias)
            mem_lay.addLayout(a_row)

            self.mem_table = QTableWidget(0, 2)
            self.mem_table.setHorizontalHeaderLabels(["Disparador Aprendido", "Acción / Comando Asociado"])
            self.mem_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            self.mem_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            mem_lay.addWidget(self.mem_table)
            root.addWidget(mem_card, 1)

            self.status_lbl = QLabel("Motor Neuronal Reflex <1ms activo")
            self.status_lbl.setObjectName("subtitle")
            root.addWidget(self.status_lbl)

            self._refresh()

        def _refresh(self) -> None:
            try:
                resp = client.call_tool("ai-model-manager", "list_models", {}, approved=True)
                if resp.get("ok"):
                    res = resp.get("result", {})
                    active = res.get("active_model", "aria-core")
                    models: list[dict[str, Any]] = res.get("models", [])
                    self.models_table.setRowCount(len(models))
                    for idx, m in enumerate(models):
                        name = str(m.get("name", ""))
                        self.models_table.setItem(idx, 0, QTableWidgetItem(name))
                        self.models_table.setItem(idx, 1, QTableWidgetItem(str(m.get("size_mb", ""))))
                        self.models_table.setItem(idx, 2, QTableWidgetItem(str(m.get("quantization", ""))))
                        self.models_table.setItem(idx, 3, QTableWidgetItem(str(m.get("role", ""))))
                        st = "🟢 ACTIVO" if active in name else ("Instalado" if m.get("installed") else "Disponible")
                        self.models_table.setItem(idx, 4, QTableWidgetItem(st))

                m_resp = client.call_tool("ai-model-manager", "inspect_neural_memory", {}, approved=True)
                if m_resp.get("ok"):
                    aliases: dict[str, Any] = m_resp.get("result", {}).get("learned_aliases", {})
                    self.mem_table.setRowCount(len(aliases))
                    for idx, (k, v) in enumerate(aliases.items()):
                        self.mem_table.setItem(idx, 0, QTableWidgetItem(str(k)))
                        self.mem_table.setItem(idx, 1, QTableWidgetItem(str(v)))
            except Exception as exc:
                self.status_lbl.setText(f"Esperando a aria-daemon: {exc}")

        def _switch_selected_model(self) -> None:
            row = self.models_table.currentRow()
            if row < 0:
                return
            item = self.models_table.item(row, 0)
            if not item:
                return
            model_name = item.text()
            try:
                resp = client.call_tool(
                    "ai-model-manager",
                    "switch_active_model",
                    {"model_name": model_name},
                    approved=True,
                )
                if resp.get("ok"):
                    self.status_lbl.setText(f"🎯 Modelo activo cambiado a '{model_name}'.")
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error cambiando modelo: {exc}")

        def _run_benchmark(self) -> None:
            try:
                resp = client.call_tool("ai-model-manager", "benchmark_inference", {}, approved=True)
                if resp.get("ok"):
                    r = resp.get("result", {})
                    self.status_lbl.setText(
                        f"⚡ Benchmark: Reflex Kernel {r.get('kernel_reflex_latency_ms')} ms | "
                        f"Velocidad estimada LLM: {r.get('estimated_tokens_per_sec')} tokens/s "
                        f"({r.get('cpu_threads')} hilos CPU) • Recomendado: {r.get('recommended_model')}"
                    )
            except Exception as exc:
                self.status_lbl.setText(f"Error ejecutando benchmark: {exc}")

        def _add_alias(self) -> None:
            trig = self.in_trig.text().strip()
            targ = self.in_targ.text().strip()
            if not trig or not targ:
                return
            try:
                client.call_tool(
                    "ai-model-manager",
                    "inspect_neural_memory",
                    {"add_alias_trigger": trig, "add_alias_target": targ},
                    approved=True,
                )
                self.in_trig.clear()
                self.in_targ.clear()
                self.status_lbl.setText(f"🧬 Nuevo hábito neuronal guardado: '{trig}' -> '{targ}'")
                self._refresh()
            except Exception as exc:
                self.status_lbl.setText(f"Error guardando alias: {exc}")

    app = QApplication(sys.argv)
    win = AriaAIStudioWindow()
    win.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS AI Studio & Neural Memory Manager")
    parser.add_argument("--socket", help="Override aria-daemon socket path")
    parser.add_argument("--check", action="store_true", help="Validate imports and exit")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({"ok": True, "component": "ariaos-ai-studio"}))
        return 0

    client = AriaDaemonClient(args.socket)
    return launch_gui(client)


if __name__ == "__main__":
    raise SystemExit(main())

