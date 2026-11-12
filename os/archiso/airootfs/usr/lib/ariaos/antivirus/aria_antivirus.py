#!/usr/bin/env python3
"""AriaOS Antivirus - Modern PyQt6 graphical frontend for ClamAV malware protection."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from PyQt6.QtCore import QObject, QProcess, Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSplitter,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:
    print(f"Error: PyQt6 is required to run AriaOS Antivirus GUI ({exc}).", file=sys.stderr)
    sys.exit(1)

QUARANTINE_DIR = Path("/var/lib/ariaos/quarantine")
CLAMAV_DB_DIR = Path("/var/lib/clamav")


def get_clamav_version() -> str:
    try:
        out = subprocess.check_output(["clamscan", "--version"], text=True, stderr=subprocess.STDOUT)
        return out.strip().split("/")[0].strip()
    except Exception:
        return "ClamAV no detectado"


def get_db_info() -> str:
    daily = CLAMAV_DB_DIR / "daily.cld"
    if not daily.exists():
        daily = CLAMAV_DB_DIR / "daily.cvd"
    if daily.exists():
        mtime = datetime.fromtimestamp(daily.stat().st_mtime)
        return f"Actualizada: {mtime.strftime('%Y-%m-%d %H:%M')}"
    return "Base de firmas no inicializada"


class ScanWorker(QThread):
    output_received = pyqtSignal(str)
    scan_finished = pyqtSignal(int, int, list)  # exit_code, infected_count, infected_files

    def __init__(self, target_path: Path, quarantine: bool = False) -> None:
        super().__init__()
        self.target_path = target_path
        self.quarantine = quarantine
        self._process: subprocess.Popen | None = None
        self._is_cancelled = False

    def run(self) -> None:
        cmd = ["clamscan", "-r", "-i"]
        if self.quarantine:
            QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
            cmd.extend(["--move", str(QUARANTINE_DIR)])
        cmd.append(str(self.target_path))

        infected_files: list[str] = []
        infected_count = 0

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if self._process.stdout:
                for line in self._process.stdout:
                    if self._is_cancelled:
                        break
                    line_str = line.strip()
                    if line_str:
                        self.output_received.emit(line_str)
                        if "FOUND" in line_str:
                            infected_files.append(line_str)
                            infected_count += 1

            self._process.wait()
            ret = self._process.returncode if not self._is_cancelled else -1
            self.scan_finished.emit(ret, infected_count, infected_files)
        except Exception as exc:
            self.output_received.emit(f"Error ejecutando clamscan: {exc}")
            self.scan_finished.emit(2, 0, [])

    def cancel(self) -> None:
        self._is_cancelled = True
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass


class UpdateWorker(QThread):
    output_received = pyqtSignal(str)
    update_finished = pyqtSignal(bool, str)

    def run(self) -> None:
        try:
            proc = subprocess.Popen(
                ["sudo", "freshclam"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if proc.stdout:
                for line in proc.stdout:
                    self.output_received.emit(line.strip())
            proc.wait()
            success = (proc.returncode == 0)
            msg = "Firmas de virus actualizadas con éxito." if success else "La actualización de freshclam reportó advertencias o error."
            self.update_finished.emit(success, msg)
        except Exception as exc:
            self.output_received.emit(f"Error al actualizar firmas: {exc}")
            self.update_finished.emit(False, str(exc))


class AriaAntivirusWindow(QWidget):
    def __init__(self, initial_target: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Antivirus AriaOS (ClamAV Protection)")
        self.setWindowIcon(QIcon.fromTheme("security-high"))
        self.resize(860, 620)
        self.scan_worker: ScanWorker | None = None
        self.update_worker: UpdateWorker | None = None

        self._apply_theme()
        self._init_ui()

        if initial_target and os.path.exists(initial_target):
            self._start_scan(Path(initial_target))

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: "Noto Sans", sans-serif;
                font-size: 13px;
            }
            QFrame.card {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 14px;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
                border-color: #38bdf8;
            }
            QPushButton#primary {
                background-color: #0284c7;
                border-color: #38bdf8;
                font-weight: bold;
            }
            QPushButton#primary:hover {
                background-color: #0369a1;
            }
            QPushButton#danger {
                background-color: #dc2626;
                border-color: #ef4444;
                font-weight: bold;
            }
            QPushButton#danger:hover {
                background-color: #b91c1c;
            }
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 5px;
            }
            QTextEdit {
                background-color: #090d16;
                color: #94a3b8;
                border: 1px solid #1e293b;
                border-radius: 8px;
                font-family: "JetBrains Mono", "Courier New", monospace;
                font-size: 12px;
                padding: 8px;
            }
        """)

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        # Header
        header = QHBoxLayout()
        logo_lbl = QLabel()
        logo_icon = QIcon.fromTheme("security-high")
        logo_lbl.setPixmap(logo_icon.pixmap(52, 52))
        header.addWidget(logo_lbl)

        title_box = QVBoxLayout()
        t = QLabel("Antivirus AriaOS")
        t.setStyleSheet("font-size: 22px; font-weight: bold; color: #38bdf8;")
        sub = QLabel("Motor ClamAV de código abierto integrado con protección del sistema y cuarentena segura")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()
        root.addLayout(header)

        # Status banner card
        status_card = QFrame()
        status_card.setObjectName("card")
        sc_layout = QHBoxLayout(status_card)
        sc_layout.setSpacing(24)

        col1 = QVBoxLayout()
        col1.addWidget(QLabel("<b>🛡️ Motor de Detección:</b>"))
        self.lbl_clam_ver = QLabel(get_clamav_version())
        self.lbl_clam_ver.setStyleSheet("color: #22c55e; font-weight: bold;")
        col1.addWidget(self.lbl_clam_ver)
        sc_layout.addLayout(col1)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("<b>📅 Base de Firmas:</b>"))
        self.lbl_db_info = QLabel(get_db_info())
        self.lbl_db_info.setStyleSheet("color: #38bdf8;")
        col2.addWidget(self.lbl_db_info)
        sc_layout.addLayout(col2)

        col3 = QVBoxLayout()
        col3.addWidget(QLabel("<b>📦 Cuarentena Segura:</b>"))
        q_count = len(list(QUARANTINE_DIR.glob("*"))) if QUARANTINE_DIR.exists() else 0
        self.lbl_quarantine = QLabel(f"{q_count} archivo(s) aislado(s)")
        self.lbl_quarantine.setStyleSheet("color: #e2e8f0;")
        col3.addWidget(self.lbl_quarantine)
        sc_layout.addLayout(col3)

        sc_layout.addStretch()
        btn_update_db = QPushButton("🔄 Actualizar Firmas")
        btn_update_db.clicked.connect(self._start_update)
        sc_layout.addWidget(btn_update_db)

        root.addWidget(status_card)

        # Quick Actions Grid
        actions_card = QFrame()
        actions_card.setObjectName("card")
        ac_layout = QGridLayout(actions_card)
        ac_layout.setSpacing(10)

        btn_scan_home = QPushButton("🏠 Analizar Mi Carpeta Personal (/home/aria)", objectName="primary")
        btn_scan_home.clicked.connect(lambda: self._start_scan(Path.home()))
        ac_layout.addWidget(btn_scan_home, 0, 0)

        btn_scan_custom = QPushButton("📂 Seleccionar Archivo o Carpeta...")
        btn_scan_custom.clicked.connect(self._select_and_scan)
        ac_layout.addWidget(btn_scan_custom, 0, 1)

        btn_scan_sys = QPushButton("⚡ Análisis Rápido del Sistema (/etc, /tmp, /usr/bin)")
        btn_scan_sys.clicked.connect(lambda: self._start_scan(Path("/tmp")))
        ac_layout.addWidget(btn_scan_sys, 1, 0)

        btn_view_quarantine = QPushButton("📦 Administrar Cuarentena")
        btn_view_quarantine.clicked.connect(self._show_quarantine_dialog)
        ac_layout.addWidget(btn_view_quarantine, 1, 1)

        root.addWidget(actions_card)

        # Live Progress & Status
        self.lbl_scan_status = QLabel("Listo. Selecciona una acción para comenzar el análisis.")
        self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        root.addWidget(self.lbl_scan_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate pulse
        self.progress_bar.hide()
        root.addWidget(self.progress_bar)

        # Output Log Console
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Los resultados del análisis se mostrarán aquí...")
        root.addWidget(self.log_view, 1)

        # Bottom control bar
        bottom_bar = QHBoxLayout()
        self.btn_cancel = QPushButton("Detener Análisis", objectName="danger")
        self.btn_cancel.clicked.connect(self._cancel_scan)
        self.btn_cancel.hide()
        bottom_bar.addWidget(self.btn_cancel)

        bottom_bar.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        bottom_bar.addWidget(btn_close)
        root.addLayout(bottom_bar)

    def _select_and_scan(self) -> None:
        target = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para analizar", str(Path.home()))
        if not target:
            target, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo para analizar", str(Path.home()))
        if target:
            self._start_scan(Path(target))

    def _start_scan(self, target: Path) -> None:
        if self.scan_worker and self.scan_worker.isRunning():
            QMessageBox.warning(self, "Análisis en curso", "Ya hay un análisis ejecutándose actualmente.")
            return

        self.log_view.clear()
        self.lbl_scan_status.setText(f"🔍 Analizando: {target}...")
        self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        self.progress_bar.show()
        self.btn_cancel.show()

        self.scan_worker = ScanWorker(target)
        self.scan_worker.output_received.connect(self._append_log)
        self.scan_worker.scan_finished.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _cancel_scan(self) -> None:
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.lbl_scan_status.setText("⏹️ Análisis detenido por el usuario.")
            self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
            self.progress_bar.hide()
            self.btn_cancel.hide()

    def _append_log(self, text: str) -> None:
        self.log_view.append(text)
        self.log_view.ensureCursorVisible()

    def _on_scan_finished(self, code: int, infected: int, infected_files: list[str]) -> None:
        self.progress_bar.hide()
        self.btn_cancel.hide()
        if code == -1:
            self.lbl_scan_status.setText("⏹️ Análisis cancelado.")
            self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #f59e0b;")
        elif infected > 0 or code == 1:
            self.lbl_scan_status.setText(f"⚠️ ¡Atención! Se detectaron {infected} amenaza(s).")
            self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #ef4444;")
            QMessageBox.critical(
                self,
                "Amenaza Detectada",
                f"Se han encontrado {infected} archivo(s) infectado(s) o sospechoso(s).\n\n"
                "Revisa la consola inferior para ver los detalles.",
            )
        else:
            self.lbl_scan_status.setText("✅ Análisis completado con éxito. No se detectaron amenazas.")
            self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #22c55e;")

    def _start_update(self) -> None:
        if self.update_worker and self.update_worker.isRunning():
            return
        self.lbl_scan_status.setText("🔄 Actualizando base de datos de firmas ClamAV (freshclam)...")
        self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")
        self.progress_bar.show()

        self.update_worker = UpdateWorker()
        self.update_worker.output_received.connect(self._append_log)
        self.update_worker.update_finished.connect(self._on_update_finished)
        self.update_worker.start()

    def _on_update_finished(self, success: bool, msg: str) -> None:
        self.progress_bar.hide()
        self.lbl_db_info.setText(get_db_info())
        if success:
            self.lbl_scan_status.setText("✅ Firmas actualizadas correctamente.")
            self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #22c55e;")
        else:
            self.lbl_scan_status.setText(f"ℹ️ {msg}")
            self.lbl_scan_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")

    def _show_quarantine_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Archivos en Cuarentena")
        dialog.resize(600, 350)
        v = QVBoxLayout(dialog)

        lbl = QLabel(f"Directorio de Cuarentena: <code>{QUARANTINE_DIR}</code>")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        v.addWidget(lbl)

        files = list(QUARANTINE_DIR.glob("*")) if QUARANTINE_DIR.exists() else []
        table = QTableWidget(len(files), 2)
        table.setHorizontalHeaderLabels(["Archivo Aislado", "Tamaño"])
        for idx, f in enumerate(files):
            table.setItem(idx, 0, QTableWidgetItem(f.name))
            table.setItem(idx, 1, QTableWidgetItem(f"{f.stat().st_size} bytes"))
        v.addWidget(table)

        btn_box = QHBoxLayout()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dialog.accept)
        btn_box.addStretch()
        btn_box.addWidget(btn_close)
        v.addLayout(btn_box)
        dialog.exec()


def main() -> int:
    app = QApplication(sys.argv)
    target = sys.argv[1] if len(sys.argv) > 1 else None
    window = AriaAntivirusWindow(initial_target=target)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
