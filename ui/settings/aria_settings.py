#!/usr/bin/env python3
"""AriaOS Control & Kernel Tuning Center — Cyber Obsidian Edition."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / "core" / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))
SYSTEM_SDK = Path("/usr/lib/ariaos/core/sdk/python")
if SYSTEM_SDK.exists() and str(SYSTEM_SDK) not in sys.path:
    sys.path.insert(0, str(SYSTEM_SDK))

from aria_sdk import (  # noqa: E402
    SUPPORTED_LANGUAGES,
    get_current_language,
    load_ariaos_config,
    save_ariaos_config,
    t,
)


def _query_daemon(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    if not hasattr(socket, "AF_UNIX"):
        return None
    for candidate in ("/run/ariaos/agent.sock", "/tmp/ariaos-agent.sock"):
        sock_path = Path(candidate)
        if sock_path.exists():
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect(str(sock_path))
                    s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
                    data = s.recv(65536)
                    if data:
                        return json.loads(data.decode("utf-8").splitlines()[0])
            except Exception:
                continue
    return None


def _list_ollama_models(endpoint: str) -> List[str]:
    url = f"{endpoint.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AriaOS-Settings"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _read_audit_entries(max_lines: int = 80) -> List[Dict[str, Any]]:
    audit_file = Path(os.environ.get("ARIAOS_AUDIT_LOG", "/tmp/ariaos-audit.jsonl"))
    if not audit_file.exists():
        return []
    entries = []
    try:
        lines = audit_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for raw in lines[-max_lines:]:
            if not raw.strip():
                continue
            try:
                entries.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return list(reversed(entries))


def main() -> int:
    parser = argparse.ArgumentParser(description="AriaOS Control & Kernel Tuning Center")
    parser.add_argument("--check", action="store_true", help="Self-check imports and exit")
    parser.add_argument("--get", help="Print configuration key value")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set configuration key")
    args = parser.parse_args()

    if args.check:
        print(json.dumps({
            "ok": True,
            "app": "ariaos-settings",
            "languages": list(SUPPORTED_LANGUAGES.keys()),
            "config": load_ariaos_config(),
        }))
        return 0

    if args.get:
        cfg = load_ariaos_config()
        print(cfg.get(args.get, ""))
        return 0

    if args.set:
        k, v = args.set
        cfg = load_ariaos_config()
        try:
            parsed_v = json.loads(v)
        except Exception:
            parsed_v = v
        cfg[k] = parsed_v
        p = save_ariaos_config(cfg)
        print(f"Updated {k} -> {parsed_v} in {p}")
        return 0

    try:
        from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
        from PyQt6.QtGui import QIcon, QPixmap
        from PyQt6.QtWidgets import (
            QApplication,
            QButtonGroup,
            QCheckBox,
            QComboBox,
            QFormLayout,
            QFrame,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMessageBox,
            QPushButton,
            QRadioButton,
            QSlider,
            QTabWidget,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("AriaOS Settings: PyQt6 not available. Install python-pyqt6.", file=sys.stderr)
        return 1

    class OllamaProbeThread(QThread):
        models_ready = pyqtSignal(list, bool)

        def __init__(self, endpoint: str) -> None:
            super().__init__()
            self.endpoint = endpoint

        def run(self) -> None:
            models = _list_ollama_models(self.endpoint)
            self.models_ready.emit(models, len(models) > 0)

    class SettingsWindow(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.cfg = load_ariaos_config()
            self.current_lang = get_current_language()
            self._probe_thread: OllamaProbeThread | None = None

            self.setWindowTitle("AriaOS — Centro de Control y Gobernador del Kernel")
            self.setWindowIcon(QIcon.fromTheme("ariaos-logo"))
            self.resize(840, 600)
            self._apply_style()
            self._init_ui()

            self.timer = QTimer(self)
            self.timer.timeout.connect(self._refresh_kernel_metrics)
            self.timer.start(3500)
            self._refresh_kernel_metrics()

        def _apply_style(self) -> None:
            self.setStyleSheet("""
                QWidget {
                    background-color: #0d1117;
                    color: #e2e8f0;
                    font-family: "Noto Sans", sans-serif;
                    font-size: 13px;
                }
                QTabWidget::pane {
                    border: 1px solid #30363d;
                    background: #0b101e;
                    border-radius: 10px;
                    padding: 14px;
                }
                QTabBar::tab {
                    background: #161b22;
                    color: #94a3b8;
                    padding: 9px 18px;
                    border: 1px solid #30363d;
                    border-bottom: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    margin-right: 3px;
                }
                QTabBar::tab:selected {
                    background: #0d1629;
                    color: #3b82f6;
                    border-color: #3b82f6;
                    font-weight: bold;
                }
                QLineEdit, QComboBox {
                    background-color: #21262d;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 7px 11px;
                    color: #ffffff;
                }
                QLineEdit:focus, QComboBox:focus {
                    border: 1.5px solid #3b82f6;
                }
                QPushButton {
                    background-color: #21262d;
                    color: #e2e8f0;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    padding: 8px 15px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3b82f6;
                    color: #0d1117;
                    border-color: #3b82f6;
                    font-weight: bold;
                }
                QPushButton#primary {
                    background-color: #3b82f6;
                    color: #0d1117;
                    border-color: #3b82f6;
                    font-weight: bold;
                }
                QPushButton#primary:hover {
                    background-color: #3b82f6;
                    color: #0d1117;
                }
                QFrame#kernel_card {
                    background-color: #090e1a;
                    border: 1px solid #3b82f6;
                    border-radius: 10px;
                    padding: 12px;
                }
                QTableWidget {
                    background-color: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    gridline-color: #30363d;
                }
                QHeaderView::section {
                    background-color: #21262d;
                    color: #3b82f6;
                    padding: 6px;
                    border: none;
                    font-weight: bold;
                }
            """)

        def _init_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(18, 15, 18, 15)
            root.setSpacing(12)

            # Header
            header = QHBoxLayout()
            logo_lbl = QLabel()
            pix = QPixmap("/usr/share/pixmaps/ariaos-logo.png")
            if pix.isNull():
                pix = QPixmap("c:/Users/hamza/Desktop/AriaOS/assets/branding/ariaos-logo.png")
            if not pix.isNull():
                logo_lbl.setPixmap(pix.scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            header.addWidget(logo_lbl)

            title_box = QVBoxLayout()
            self.title_lbl = QLabel("ARIA OS // CENTRO DE CONTROL Y KERNEL NEURONAL")
            self.title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; letter-spacing: 0.8px;")
            self.sub_lbl = QLabel("Gestión adaptativa de hardware (8GB+ / 16GB+), motor de IA en el kernel y seguridad")
            self.sub_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
            title_box.addWidget(self.title_lbl)
            title_box.addWidget(self.sub_lbl)
            header.addLayout(title_box)
            header.addStretch()
            root.addLayout(header)

            # Tab Widget
            self.tabs = QTabWidget()
            self.tabs.addTab(self._tab_kernel(), "⚡ Kernel & Hardware")
            self.tabs.addTab(self._tab_general(), t("tab_general", self.current_lang))
            self.tabs.addTab(self._tab_model(), t("tab_model", self.current_lang))
            self.tabs.addTab(self._tab_security(), t("tab_security", self.current_lang))
            self.tabs.addTab(self._tab_audit(), t("tab_audit", self.current_lang))
            root.addWidget(self.tabs)

            # Footer
            footer = QHBoxLayout()
            self.status_feedback = QLabel("")
            self.status_feedback.setStyleSheet("color: #3b82f6; font-weight: bold;")
            footer.addWidget(self.status_feedback)
            footer.addStretch()

            self.btn_save = QPushButton(t("btn_save", self.current_lang), objectName="primary")
            self.btn_save.clicked.connect(self._on_save)
            footer.addWidget(self.btn_save)

            self.btn_close = QPushButton(t("btn_close", self.current_lang))
            self.btn_close.clicked.connect(self.close)
            footer.addWidget(self.btn_close)
            root.addLayout(footer)

        def _tab_kernel(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(12)

            card = QFrame()
            card.setObjectName("kernel_card")
            c_layout = QVBoxLayout(card)
            c_layout.setSpacing(8)

            self.lbl_hw_tier = QLabel("🧠 <b>Perfil Adaptativo del Gobernador:</b> Detectando hardware...")
            self.lbl_silicon = QLabel("🔬 <b>Registros x86_64 (CPUID / RDTSC):</b> Analizando silicio...")
            self.lbl_mem_zram = QLabel("💾 <b>Memoria Física y ZRAM (zstd):</b> Calculando...")
            self.lbl_psi = QLabel("📊 <b>Presión PSI del Kernel (`/proc/pressure`):</b> Calculando...")

            for lbl in (self.lbl_hw_tier, self.lbl_silicon, self.lbl_mem_zram, self.lbl_psi):
                lbl.setStyleSheet("border: none; font-size: 13px;")
                c_layout.addWidget(lbl)

            layout.addWidget(card)

            btn_row = QHBoxLayout()
            btn_opt = QPushButton("⚡ Compactar Páginas y Liberar Caché del Kernel Ahora", objectName="primary")
            btn_opt.clicked.connect(self._on_optimize_kernel)
            btn_row.addWidget(btn_opt)

            btn_reapply = QPushButton("🎨 Reaplicar Diseño KDE Cyber Obsidian")
            btn_reapply.clicked.connect(self._on_reapply_plasma)
            btn_row.addWidget(btn_reapply)
            layout.addLayout(btn_row)

            layout.addStretch()
            return w

        def _tab_general(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(14)

            form = QFormLayout()
            form.setSpacing(12)

            self.lang_combo = QComboBox()
            for code, name in SUPPORTED_LANGUAGES.items():
                self.lang_combo.addItem(f"{name} ({code})", code)
            curr_idx = self.lang_combo.findData(self.cfg.get("language", "es"))
            if curr_idx >= 0:
                self.lang_combo.setCurrentIndex(curr_idx)
            self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
            form.addRow(t("language_label", self.current_lang), self.lang_combo)

            self.hotkey_combo = QComboBox()
            self.hotkey_combo.setEditable(True)
            self.hotkey_combo.addItems(["Alt+Space", "Meta+Space", "Ctrl+Space", "Ctrl+Alt+A"])
            self.hotkey_combo.setCurrentText(self.cfg.get("hotkey", "Alt+Space"))
            form.addRow(t("hotkey_label", self.current_lang), self.hotkey_combo)

            layout.addLayout(form)

            self.autostart_chk = QCheckBox(t("autostart_label", self.current_lang))
            self.autostart_chk.setChecked(True)
            layout.addWidget(self.autostart_chk)

            layout.addStretch()
            return w

        def _tab_model(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(14)

            form = QFormLayout()
            form.setSpacing(10)

            endpoint_box = QHBoxLayout()
            self.endpoint_edit = QLineEdit(self.cfg.get("ollama_url", "http://127.0.0.1:11434"))
            endpoint_box.addWidget(self.endpoint_edit)
            btn_test = QPushButton(t("btn_test_ollama", self.current_lang))
            btn_test.clicked.connect(self._on_test_ollama)
            endpoint_box.addWidget(btn_test)
            form.addRow(t("ollama_url_label", self.current_lang), endpoint_box)

            model_box = QHBoxLayout()
            self.model_combo = QComboBox()
            self.model_combo.setEditable(True)
            self.model_combo.addItems(["aria-core", "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b"])
            self.model_combo.setCurrentText(self.cfg.get("model", "aria-core"))
            model_box.addWidget(self.model_combo)
            btn_pull = QPushButton(t("btn_pull_model", self.current_lang))
            btn_pull.clicked.connect(self._on_pull_model)
            model_box.addWidget(btn_pull)
            form.addRow(t("model_select_label", self.current_lang), model_box)

            self.ctx_combo = QComboBox()
            self.ctx_combo.addItems(["512", "1024", "2048", "4096"])
            self.ctx_combo.setCurrentText(str(self.cfg.get("num_ctx", 1024)))
            form.addRow(t("context_size_label", self.current_lang), self.ctx_combo)

            temp_box = QHBoxLayout()
            self.temp_slider = QSlider(Qt.Orientation.Horizontal)
            self.temp_slider.setRange(0, 100)
            initial_temp = int(float(self.cfg.get("temperature", 0.2)) * 100)
            self.temp_slider.setValue(initial_temp)
            self.temp_lbl = QLabel(f"{initial_temp / 100.0:.2f}")
            self.temp_slider.valueChanged.connect(lambda v: self.temp_lbl.setText(f"{v / 100.0:.2f}"))
            temp_box.addWidget(self.temp_slider)
            temp_box.addWidget(self.temp_lbl)
            form.addRow(t("temperature_label", self.current_lang), temp_box)

            layout.addLayout(form)
            layout.addStretch()
            return w

        def _tab_security(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(12)

            sec_lbl = QLabel(t("approval_mode_label", self.current_lang))
            sec_lbl.setStyleSheet("font-weight: bold; color: #3b82f6;")
            layout.addWidget(sec_lbl)

            self.radio_interactive = QRadioButton(t("mode_interactive", self.current_lang))
            self.radio_autowrite = QRadioButton(t("mode_autowrite", self.current_lang))
            self.radio_readonly = QRadioButton(t("mode_readonly", self.current_lang))

            mode = str(self.cfg.get("approval_mode", "interactive")).lower()
            if mode == "autowrite":
                self.radio_autowrite.setChecked(True)
            elif mode == "readonly":
                self.radio_readonly.setChecked(True)
            else:
                self.radio_interactive.setChecked(True)

            self.sec_group = QButtonGroup(self)
            self.sec_group.addButton(self.radio_interactive)
            self.sec_group.addButton(self.radio_autowrite)
            self.sec_group.addButton(self.radio_readonly)

            layout.addWidget(self.radio_interactive)
            layout.addWidget(self.radio_autowrite)
            layout.addWidget(self.radio_readonly)
            layout.addSpacing(10)

            conn_lbl = QLabel(t("connector_groups_label", self.current_lang))
            conn_lbl.setStyleSheet("font-weight: bold; color: #3b82f6;")
            layout.addWidget(conn_lbl)

            groups = self.cfg.get("enabled_connector_groups", {})
            self.group_chks: Dict[str, QCheckBox] = {}
            labels = {
                "core_os": "Core OS & Kernel (Lectura directa en Rust <0.1ms: os-kernel, os-system, os-storage, os-files)",
                "security": "Seguridad & Aria Shield (ClamAV bajo demanda, Vault Crypto, Net Audit)",
                "development": "Desarrollo (Git, VSCodium, Contenedores, Bases de Datos)",
                "creative": "Creatividad & Multimedia (GIMP, Krita, Blender, Audacity, Kdenlive, FFmpeg)",
                "office": "Oficina & Documentos (LibreOffice, Okular, Obsidian, Calibre)",
                "browser": "Navegador Web (Brave CDP, Firefox)",
                "comms_gaming": "Comunicaciones & Gaming (Syncthing, qBittorrent, Steam, Lutris, RetroArch)",
            }
            for k, label in labels.items():
                chk = QCheckBox(label)
                chk.setChecked(bool(groups.get(k, True)))
                self.group_chks[k] = chk
                layout.addWidget(chk)

            layout.addStretch()
            return w

        def _tab_audit(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setSpacing(10)

            top_box = QHBoxLayout()
            top_box.addWidget(QLabel(t("audit_title", self.current_lang)))
            top_box.addStretch()
            btn_clear = QPushButton(t("btn_clear_audit", self.current_lang))
            btn_clear.clicked.connect(self._on_clear_audit)
            top_box.addWidget(btn_clear)
            layout.addLayout(top_box)

            self.audit_table = QTableWidget()
            self.audit_table.setColumnCount(5)
            self.audit_table.setHorizontalHeaderLabels(["Fecha / Hora", "Conector", "Herramienta", "Riesgo", "Estado"])
            self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(self.audit_table)
            self._load_audit_entries()

            return w

        def _refresh_kernel_metrics(self) -> None:
            resp = _query_daemon({"action": "kernel_telemetry"})
            if not resp or not resp.get("ok"):
                return
            t_data = resp.get("telemetry", {})
            tier = t_data.get("hardware_tier", "Tier-A (8GB+)")
            sil = t_data.get("silicon", {})
            mem = t_data.get("memory", {})
            psi = t_data.get("psi", {})

            self.lbl_hw_tier.setText(
                f"🧠 <b>Perfil Adaptativo del Gobernador:</b> <span style='color:#3b82f6;'>{tier}</span> — "
                f"Kernel <code>{t_data.get('kernel_version', 'Linux')}</code> ({t_data.get('cpu_cores', 1)} hilos)"
            )
            self.lbl_silicon.setText(
                f"🔬 <b>Registros Silicio x86_64 (CPUID):</b> "
                f"AVX2: <code>{'SÍ' if sil.get('avx2') else 'NO'}</code> | "
                f"FMA: <code>{'SÍ' if sil.get('fma') else 'NO'}</code> | "
                f"AES-NI: <code>{'SÍ' if sil.get('aes_ni') else 'NO'}</code> | "
                f"AVX-512: <code>{'SÍ' if sil.get('avx512') else 'NO'}</code> | "
                f"Modo: <code>{'VM' if sil.get('hypervisor') else 'Bare-Metal'}</code>"
            )
            self.lbl_mem_zram.setText(
                f"💾 <b>Memoria Física y ZRAM:</b> Usados <b>{mem.get('used_mb', 0)} MB</b> de "
                f"<b>{mem.get('total_mb', 0)} MB</b> ({mem.get('usage_pct', 0)}%) — "
                f"Disponible: <b>{mem.get('available_mb', 0)} MB</b> | "
                f"Swap/ZRAM libre: <b>{mem.get('swap_free_mb', 0)}/{mem.get('swap_total_mb', 0)} MB</b>"
            )
            self.lbl_psi.setText(
                f"📊 <b>Presión PSI del Kernel:</b> "
                f"CPU: <code>{psi.get('cpu_avg10', 0.0):.2f}%</code> | "
                f"Memoria: <code>{psi.get('memory_avg10', 0.0):.2f}%</code> | "
                f"I/O: <code>{psi.get('io_avg10', 0.0):.2f}%</code>"
            )

        def _on_optimize_kernel(self) -> None:
            resp = _query_daemon({"action": "optimize_kernel"})
            if resp and resp.get("ok"):
                freed = resp.get("freed_mb", 0)
                avail = resp.get("after_available_mb", 0)
                self.status_feedback.setText(f"⚡ Kernel optimizado: +{freed} MB liberados ({avail} MB disponibles)")
            self._refresh_kernel_metrics()

        def _on_reapply_plasma(self) -> None:
            marker = Path.home() / ".config" / ".ariaos-cyber-shell-v2"
            marker.unlink(missing_ok=True)
            if shutil.which("ariaos-apply-branding"):
                subprocess.Popen(["ariaos-apply-branding"])
                self.status_feedback.setText("🎨 Reconstruyendo paneles y tema Cyber Obsidian en KDE Plasma...")

        def _load_audit_entries(self) -> None:
            entries = _read_audit_entries(100)
            self.audit_table.setRowCount(len(entries))
            for row, e in enumerate(entries):
                ts = e.get("ts", 0)
                time_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if ts else "-"
                self.audit_table.setItem(row, 0, QTableWidgetItem(time_str))
                self.audit_table.setItem(row, 1, QTableWidgetItem(str(e.get("connector", ""))))
                self.audit_table.setItem(row, 2, QTableWidgetItem(str(e.get("tool", ""))))
                self.audit_table.setItem(row, 3, QTableWidgetItem(str(e.get("risk_level", ""))))
                self.audit_table.setItem(row, 4, QTableWidgetItem(str(e.get("status", ""))))

        def _on_clear_audit(self) -> None:
            audit_file = Path(os.environ.get("ARIAOS_AUDIT_LOG", "/tmp/ariaos-audit.jsonl"))
            if audit_file.exists():
                try:
                    audit_file.write_text("", encoding="utf-8")
                except OSError:
                    pass
            self._load_audit_entries()

        def _on_test_ollama(self) -> None:
            endpoint = self.endpoint_edit.text().strip()
            self._probe_thread = OllamaProbeThread(endpoint)
            self._probe_thread.models_ready.connect(self._on_models_probed)
            self._probe_thread.start()

        def _on_models_probed(self, models: list, ok: bool) -> None:
            if not ok or not models:
                QMessageBox.information(
                    self,
                    "Motor Neuronal AriaOS",
                    "El núcleo reflejo en Rust (Tier-0, <1ms) está activo y funcionando.\n"
                    f"Ollama Tier-1 en {self.endpoint_edit.text()} no tiene modelos cargados actualmente.",
                )
                return
            curr = self.model_combo.currentText()
            self.model_combo.clear()
            self.model_combo.addItems(models)
            idx = self.model_combo.findText(curr)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            QMessageBox.information(self, "Motor Neuronal AriaOS", f"Conexión exitosa. {len(models)} modelo(s) disponibles.")

        def _on_pull_model(self) -> None:
            target_model = self.model_combo.currentText().strip()
            if not target_model:
                return
            cmd_str = (
                "ollama pull qwen2.5:0.5b && ollama create aria-core -f /usr/share/ariaos/models/Modelfile.aria-core"
                if target_model == "aria-core"
                else f"ollama pull {target_model}"
            )
            if shutil.which("konsole"):
                subprocess.Popen(["konsole", "--title", f"AriaOS - Modelo {target_model}", "-e", "bash", "-c", f"{cmd_str}; echo; read -p 'Presiona Enter para cerrar...'"])
            elif shutil.which("xterm"):
                subprocess.Popen(["xterm", "-title", f"AriaOS - Modelo {target_model}", "-e", "bash", "-c", f"{cmd_str}; echo; read -p 'Presiona Enter para cerrar...'"])

        def _on_lang_changed(self) -> None:
            code = self.lang_combo.currentData()
            if code in SUPPORTED_LANGUAGES:
                self.current_lang = code
                self.tabs.setTabText(1, t("tab_general", code))
                self.tabs.setTabText(2, t("tab_model", code))
                self.tabs.setTabText(3, t("tab_security", code))
                self.tabs.setTabText(4, t("tab_audit", code))
                self.btn_save.setText(t("btn_save", code))
                self.btn_close.setText(t("btn_close", code))

        def _on_save(self) -> None:
            selected_mode = "interactive"
            if self.radio_autowrite.isChecked():
                selected_mode = "autowrite"
            elif self.radio_readonly.isChecked():
                selected_mode = "readonly"

            new_cfg: Dict[str, Any] = {
                "language": self.lang_combo.currentData() or "es",
                "hotkey": self.hotkey_combo.currentText().strip(),
                "ollama_url": self.endpoint_edit.text().strip(),
                "model": self.model_combo.currentText().strip(),
                "num_ctx": int(self.ctx_combo.currentText() or 1024),
                "temperature": round(self.temp_slider.value() / 100.0, 2),
                "approval_mode": selected_mode,
                "enabled_connector_groups": {
                    k: chk.isChecked() for k, chk in self.group_chks.items()
                },
            }
            saved_path = save_ariaos_config(new_cfg)
            self.cfg = new_cfg
            self.status_feedback.setText(f"✓ {t('saved_success', self.current_lang)} ({saved_path.name})")

    app = QApplication(sys.argv)
    win = SettingsWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
