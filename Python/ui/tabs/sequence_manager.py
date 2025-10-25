#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from typing import List, Tuple, Dict
from collections import defaultdict

# --- Automatic package installation (install with pip if not present) ---
import subprocess
import importlib


def _ensure_packages() -> None:
    required = [("PyQt5", "PyQt5"), ("pandas", "pandas"), ("openpyxl", "openpyxl")]
    to_install = []
    for mod, pipname in required:
        try:
            spec = importlib.util.find_spec(mod)
            if spec is None:
                to_install.append(pipname)
        except Exception:
            to_install.append(pipname)
    if to_install:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", *to_install])
            importlib.invalidate_caches()
        except Exception as e:
            print("[Warning] Automatic package installation failed:", e)


_ensure_packages()

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QSpinBox, QSlider,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QLineEdit,
    QAbstractSpinBox, QToolButton, QCheckBox, QTextEdit
)

import pandas as pd

# ------------------- Constants -------------------
NOZZLE_COUNT_X = 128
NOZZLE_PITCH_UM = 137.1  # µm
CHANNELS = ["A", "T", "G", "C", "ACT"]
# --- The well dot size used for rendering and calculation is fixed at 1px ---
WELL_DOT_SIZE_RENDER = 1


# ------------------- Utilities -------------------
def clamp(v: int, vmin: int, vmax: int) -> int:
    return max(vmin, min(v, vmax))


# ------------------- Widgets -------------------
class PitchControl(QWidget):
    changed = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, m_init: int = 4) -> None:
        super().__init__(parent)
        self.m = max(1, int(m_init))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.btn_minus = QToolButton(self);
        self.btn_minus.setText("-");
        self.btn_minus.clicked.connect(self.dec)
        layout.addWidget(self.btn_minus)
        self.label = QLabel(self);
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label, 1)
        self.btn_plus = QToolButton(self);
        self.btn_plus.setText("+");
        self.btn_plus.clicked.connect(self.inc)
        layout.addWidget(self.btn_plus)
        self.update_label()

    def inc(self):
        self.m += 1;
        self.update_label();
        self.changed.emit(self.m)

    def dec(self):
        if self.m > 1: self.m -= 1; self.update_label(); self.changed.emit(self.m)

    def set_value(self, m: int):
        m = max(1, int(m))
        if m != self.m: self.m = m; self.update_label(); self.changed.emit(self.m)

    def value(self) -> int:
        return self.m

    def update_label(self):
        pitch_um = self.m * NOZZLE_PITCH_UM
        self.label.setText(f"Pitch: {pitch_um:.1f} µm  (m = {self.m})")


# ------------------- Main Window -------------------
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Printhead Text Data Generator (PyQt5)")
        self.resize(1350, 860)
        self.multipler_m = 4
        self.cols = 25
        self.rows = 40
        self.oligo_len = 0
        self.injection_amount = 3
        self.start_position = 0
        self.sequences: List[str] = []
        self.base_output_dir = os.path.abspath(".")
        self.project_name = "output"
        self.channel_offsets: Dict[str, int] = {ch: 0 for ch in CHANNELS}
        self.channel_y_offsets: Dict[str, int] = {ch: 0 for ch in CHANNELS}
        self.y_step_interval = 50  # Set default value
        self._build_ui()
        try:
            self.load_settings()
        except Exception as e:
            print("[Warning loading settings]", e)
        self._refresh_constraints()

    def _build_ui(self) -> None:
        cw = QWidget(self)
        self.setCentralWidget(cw)
        root = QHBoxLayout(cw)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        left = QVBoxLayout()
        left.setSpacing(8)

        geo_group = QGroupBox("Geometry/Grid Settings")
        geo = QGridLayout(geo_group)
        geo.setHorizontalSpacing(8)
        geo.setVerticalSpacing(6)
        geo.addWidget(QLabel("Number of Nozzles (X pixels):"), 0, 0)
        geo.addWidget(QLabel(str(NOZZLE_COUNT_X)), 0, 1)
        geo.addWidget(QLabel("Well Spacing (Nozzle Pitch Multiple):"), 1, 0)
        self.pitch_ctrl = PitchControl(m_init=self.multipler_m)
        self.pitch_ctrl.changed.connect(self.on_pitch_changed)
        geo.addWidget(self.pitch_ctrl, 1, 1, 1, 2)
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 128)
        self.spin_cols.setValue(self.cols)
        self.spin_cols.setAccelerated(True)
        self.spin_cols.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        self.spin_cols.valueChanged.connect(self.on_cols_changed)
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 10000)
        self.spin_rows.setValue(self.rows)
        self.spin_rows.setAccelerated(True)
        self.spin_rows.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        self.spin_rows.valueChanged.connect(self.on_rows_changed)
        geo.addWidget(QLabel("Number of Well Columns (Width, X):"), 2, 0)
        geo.addWidget(self.spin_cols, 2, 1)
        geo.addWidget(QLabel("Number of Well Rows (Height, Y):"), 3, 0)
        geo.addWidget(self.spin_rows, 3, 1)

        geo.addWidget(QLabel("Vertical Well Spacing (steps, 20 per 1mm):"), 4, 0)
        self.spin_y_step_interval = QSpinBox()
        self.spin_y_step_interval.setRange(1, 200000)
        self.spin_y_step_interval.setValue(self.y_step_interval)
        self.spin_y_step_interval.setAccelerated(True)
        self.spin_y_step_interval.valueChanged.connect(self.on_y_step_interval_changed)
        geo.addWidget(self.spin_y_step_interval, 4, 1)

        geo.addWidget(QLabel("Injection Amount:"), 5, 0)
        self.spin_injection_amount = QSpinBox()
        self.spin_injection_amount.setRange(1, 1000)
        self.spin_injection_amount.setValue(self.injection_amount)
        self.spin_injection_amount.setAccelerated(True)
        self.spin_injection_amount.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        self.spin_injection_amount.valueChanged.connect(self.on_injection_amount_changed)
        geo.addWidget(self.spin_injection_amount, 5, 1)

        geo.addWidget(QLabel("Start Position (steps):"), 6, 0)
        self.spin_start_position = QSpinBox()
        self.spin_start_position.setRange(0, 2000000)
        self.spin_start_position.setValue(self.start_position)
        self.spin_start_position.setAccelerated(True)
        self.spin_start_position.valueChanged.connect(self.on_start_position_changed)
        geo.addWidget(self.spin_start_position, 6, 1)

        geo.addWidget(QLabel("Oligo Length (auto):"), 7, 0)
        self.lbl_len_auto = QLabel("0 bp")
        geo.addWidget(self.lbl_len_auto, 7, 1)
        self.lbl_constraints = QLabel("")
        self.lbl_constraints.setStyleSheet("color:#c77; font-weight:600;")
        geo.addWidget(self.lbl_constraints, 8, 0, 1, 3)
        left.addWidget(geo_group)

        offset_container = QWidget()
        offset_layout = QHBoxLayout(offset_container)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        off_group_x = QGroupBox("Channel X Offset (px)")
        off_x = QGridLayout(off_group_x)
        self.offset_spins = {}
        for i, ch in enumerate(CHANNELS):
            off_x.addWidget(QLabel(ch + ":"), i, 0)
            sp = QSpinBox()
            sp.setRange(-128, 128)
            sp.setValue(self.channel_offsets.get(ch, 0))
            sp.setAccelerated(True)
            sp.valueChanged.connect(lambda v, ch=ch: self.on_offset_changed(ch, v))
            off_x.addWidget(sp, i, 1)
            self.offset_spins[ch] = sp
        offset_layout.addWidget(off_group_x)

        off_group_y = QGroupBox("Channel Y Offset (px)")
        off_y = QGridLayout(off_group_y)
        self.offset_y_spins = {}
        for i, ch in enumerate(CHANNELS):
            off_y.addWidget(QLabel(ch + ":"), i, 0)
            sp = QSpinBox()
            sp.setRange(-10000, 10000)
            sp.setValue(self.channel_y_offsets.get(ch, 0))
            sp.setAccelerated(True)
            sp.valueChanged.connect(lambda v, ch=ch: self.on_y_offset_changed(ch, v))
            off_y.addWidget(sp, i, 1)
            self.offset_y_spins[ch] = sp
        offset_layout.addWidget(off_group_y)
        left.addWidget(offset_container)

        seq_group = QGroupBox("Sequence Input")
        seq = QGridLayout(seq_group)
        seq.setHorizontalSpacing(8)
        seq.setVerticalSpacing(6)
        self.btn_load = QPushButton("Load Sequences (multiple files)")
        self.btn_load.clicked.connect(self.on_load_sequences)
        seq.addWidget(self.btn_load, 0, 0, 1, 2)
        self.lbl_seq_hint = QLabel("Loaded sequences are 5'→3'. Images are generated in the 3'→5' direction.")
        self.lbl_seq_hint.setStyleSheet("color:#888;")
        seq.addWidget(self.lbl_seq_hint, 1, 0, 1, 2)
        self.list_files = QListWidget()
        self.list_files.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        seq.addWidget(self.list_files, 2, 0, 3, 2)
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.on_clear_sequences)
        seq.addWidget(self.btn_clear, 5, 0)
        self.lbl_seq_summary = QLabel("Loaded sequences: 0")
        seq.addWidget(self.lbl_seq_summary, 5, 1)
        left.addWidget(seq_group, 1)

        out_group = QGroupBox("Output and Execution")
        out = QGridLayout(out_group)
        out.setHorizontalSpacing(8)
        out.setVerticalSpacing(6)
        out.addWidget(QLabel("Output Filename:"), 0, 0)
        self.edit_project_name = QLineEdit(self.project_name)
        out.addWidget(self.edit_project_name, 0, 1, 1, 2)
        out.addWidget(QLabel("Save Location:"), 1, 0)
        self.edit_outdir = QLineEdit(self.base_output_dir)
        self.edit_outdir.setReadOnly(True)
        out.addWidget(self.edit_outdir, 1, 1)
        self.btn_browse = QPushButton("Change...")
        self.btn_browse.clicked.connect(self.on_browse_outdir)
        out.addWidget(self.btn_browse, 1, 2)
        self.btn_generate = QPushButton("Generate Text Data")
        self.btn_generate.setStyleSheet("font-weight:700; padding:8px 12px;")
        self.btn_generate.clicked.connect(self.on_generate)
        out.addWidget(self.btn_generate, 2, 0, 1, 3)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        out.addWidget(self.progress, 3, 0, 1, 3)
        self.btn_save_settings = QPushButton("Save Settings")
        self.btn_save_settings.clicked.connect(self.on_save_settings)
        out.addWidget(self.btn_save_settings, 4, 0, 1, 3)
        left.addWidget(out_group)

        right = QVBoxLayout()
        prev_group = QGroupBox("Preview (Array)")
        prev_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        prev = QGridLayout(prev_group)
        prev.addWidget(QLabel("Cycle:"), 0, 0)
        self.slider_cycle = QSlider(Qt.Horizontal)
        self.slider_cycle.setRange(1, 1)
        self.slider_cycle.setValue(1)
        self.slider_cycle.valueChanged.connect(self.update_preview)
        prev.addWidget(self.slider_cycle, 0, 1)
        self.lbl_cycle_val = QLabel("1")
        prev.addWidget(self.lbl_cycle_val, 0, 2)
        self.lbl_legend = QLabel("■ = Active Nozzle, □ = Inactive Nozzle")
        prev.addWidget(self.lbl_legend, 1, 0, 1, 3)
        chk_layout = QHBoxLayout()
        chk_layout.addWidget(QLabel("View Channels:"))
        self.preview_checkboxes = {}
        for ch in CHANNELS:
            chk = QCheckBox(ch)
            chk.setChecked(True)
            chk.stateChanged.connect(self.update_preview)
            chk_layout.addWidget(chk)
            self.preview_checkboxes[ch] = chk
        chk_layout.addStretch(1)
        prev.addLayout(chk_layout, 2, 0, 1, 3)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        font = QtGui.QFont("Courier New")
        if not font.exactMatch():
            font = QtGui.QFont("Courier")
        font.setPointSize(8)

        self.preview.setFont(font)
        self.preview.setLineWrapMode(QTextEdit.NoWrap)
        self.preview.setStyleSheet("QTextEdit { background-color: #f0f0f0; color: #000; }")
        prev.addWidget(self.preview, 3, 0, 1, 3)
        right.addWidget(prev_group, 1)

        root.addLayout(left, 0)
        root.addLayout(right, 1)
        self._sync_to_state()

    def _sync_to_state(self):
        self.pitch_ctrl.set_value(self.multipler_m)
        self.spin_cols.setValue(self.cols)
        self.spin_rows.setValue(self.rows)
        self.spin_y_step_interval.blockSignals(True)
        self.spin_y_step_interval.setValue(self.y_step_interval)
        self.spin_y_step_interval.blockSignals(False)
        if hasattr(self, 'spin_start_position'):
            self.spin_start_position.blockSignals(True)
            self.spin_start_position.setValue(self.start_position)
            self.spin_start_position.blockSignals(False)
        self.lbl_len_auto.setText(f"{self.oligo_len} bp")
        self.slider_cycle.setRange(1, max(1, self.oligo_len))
        n = len(self.sequences)
        max_len = max((len(s) for s in self.sequences), default=0)
        self.lbl_seq_summary.setText(f"Loaded sequences: {n} (longest {max_len} bp)")
        self._refresh_constraints()
        self.update_preview()

    def _refresh_constraints(self):
        max_cols = NOZZLE_COUNT_X // self.multipler_m
        if self.cols > max_cols:
            self.cols = max_cols
            self.spin_cols.blockSignals(True)
            self.spin_cols.setValue(self.cols)
            self.spin_cols.blockSignals(False)
        warn = []
        if max_cols <= 0:
            warn.append("Pitch multiple is too large. Reduce m to keep the column count above 0.")
        if self.cols * self.multipler_m > NOZZLE_COUNT_X:
            warn.append("Number of columns × pitch (px) exceeds 128.")
        if len(self.sequences) > (self.cols * self.rows):
            warn.append("Number of loaded sequences exceeds the number of wells. Excess will be ignored.")
        self.lbl_constraints.setText("\n".join(warn))

    def on_pitch_changed(self, m: int):
        self.multipler_m = max(1, int(m))
        self._sync_to_state()

    def on_cols_changed(self, v: int):
        self.cols = int(v)
        self._refresh_constraints()
        self.update_preview()

    def on_rows_changed(self, v: int):
        self.rows = int(v)
        self._sync_to_state()

    def on_y_step_interval_changed(self, v: int):
        self.y_step_interval = int(v)

    def on_injection_amount_changed(self, v: int):
        self.injection_amount = int(v)

    def on_start_position_changed(self, v: int):
        self.start_position = int(v)

    def on_offset_changed(self, ch: str, v: int):
        self.channel_offsets[ch] = int(v)

    def on_y_offset_changed(self, ch: str, v: int):
        self.channel_y_offsets[ch] = int(v)

    def on_browse_outdir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Save Location", self.base_output_dir)
        if d:
            self.base_output_dir = d
            self.edit_outdir.setText(self.base_output_dir)

    def on_clear_sequences(self):
        self.sequences.clear()
        self.list_files.clear()
        self.oligo_len = 0
        self._sync_to_state()

    def on_load_sequences(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Sequence Files (multiple)", "",
                                                "Supported formats (*.xlsx *.xls *.csv *.txt);;All files (*)")
        if not files:
            return
        errors = []
        for fp in files:
            try:
                seqs, info = self._read_sequences_from_file(fp)
                for s in seqs:
                    self.sequences.append("".join(str(s).strip().upper().replace(" ", "").replace("\t", "")))
                item = QListWidgetItem(f"{os.path.basename(fp)}  —  {info}")
                item.setToolTip(fp)
                self.list_files.addItem(item)
            except Exception as e:
                errors.append(f"{os.path.basename(fp)}: {e}")
        self.oligo_len = max((len(s) for s in self.sequences), default=0)
        self._sync_to_state()
        if errors:
            QMessageBox.warning(self, "Read Error", "\n".join(errors))

    def _read_sequences_from_file(self, fp: str) -> Tuple[List[str], str]:
        """
        Reads sequences from a file. Each row is treated as a single sequence for all file formats.
        """
        ext = os.path.splitext(fp)[1].lower()
        sequences: List[str] = []

        try:
            if ext in (".xlsx", ".xls"):
                df = pd.read_excel(fp, header=None, engine=("openpyxl" if ext == ".xlsx" else None))
                # Read all non-empty values from the first column as strings
                sequences = [str(v).strip() for v in df.iloc[:, 0].dropna().tolist() if str(v).strip()]
            elif ext == ".csv":
                df = pd.read_csv(fp, header=None)
                # Read all non-empty values from the first column as strings
                sequences = [str(v).strip() for v in df.iloc[:, 0].dropna().tolist() if str(v).strip()]
            else:  # .txt file or other text file
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    # Read each non-empty line as a single sequence
                    sequences = [line.strip() for line in f if line.strip()]

            if not sequences:
                return ([], "File is empty or contains no readable sequences.")

            # All sequences are treated as individual items
            return (sequences, f"{len(sequences)} sequences loaded")

        except Exception as e:
            # Handle all exceptions that may occur during file reading
            return ([], f"Error: {e}")


    def _well_positions(self) -> List[Tuple[int, int]]:
        pos, m = [], self.multipler_m
        for r in range(self.rows):
            for c in range(self.cols):
                x_pos = c * m
                y_pos = r * self.y_step_interval
                pos.append((x_pos, y_pos))
        return pos

    def _render_preview_array_text(self, cycle_idx_1based: int) -> str:
        if not self.sequences or self.rows <= 0 or self.cols <= 0:
            return "No sequences to preview."

        idx = clamp(cycle_idx_1based - 1, 0, max(0, self.oligo_len - 1))

        grid = [['□'] * NOZZLE_COUNT_X for _ in range(self.rows)]

        num_wells = self.rows * self.cols
        use_n = min(len(self.sequences), num_wells)
        is_visible = {ch: self.preview_checkboxes[ch].isChecked() for ch in self.preview_checkboxes}

        for i in range(use_n):
            s = self.sequences[i]
            if idx >= len(s):
                continue

            base = s[::-1][idx].upper()
            if base not in ("A", "C", "G", "T"):
                continue

            well_row = i // self.cols
            well_col = i % self.cols
            nozzle_idx = well_col * self.multipler_m

            active_channels = set()
            if is_visible.get("ACT", False):
                active_channels.add("ACT")
            if is_visible.get(base, False):
                active_channels.add(base)

            if active_channels:
                if 0 <= nozzle_idx < NOZZLE_COUNT_X:
                    grid[well_row][nozzle_idx] = '■'

        header1 = "      " + "".join([f"{i:<10}" for i in range(0, 128, 10)])
        header2 = "Row/Col " + "".join(["0123456789" for _ in range(13)])[:NOZZLE_COUNT_X]
        lines = [header1, header2]

        for r_idx, row_data in enumerate(grid):
            line = f"{r_idx:<5} " + "".join(row_data)
            lines.append(line)

        return "\n".join(lines)

    def update_preview(self):
        cycle = self.slider_cycle.value()
        self.lbl_cycle_val.setText(str(cycle))
        preview_text = self._render_preview_array_text(cycle)
        self.preview.setText(preview_text)

    def _bits_to_string(self, bits: List[int]) -> str:
        """Converts a list of 128 bits into a 128-character string of '0's and '1's."""
        return "".join(map(str, bits))

    def on_generate(self) -> None:
        try:
            self.save_settings()
        except Exception as e:
            print("[Warning saving settings]", e)
        if (not self.sequences) or (self.oligo_len <= 0):
            QMessageBox.warning(self, "Warning", "Please load sequences first.")
            return

        base_dir, project_name = self.base_output_dir, self.edit_project_name.text().strip()
        if not project_name:
            QMessageBox.warning(self, "Warning", "Please enter an output filename.")
            return

        if not project_name.lower().endswith(".txt"):
            project_name += ".txt"
        output_filepath = os.path.join(base_dir, project_name)
        if os.path.isfile(output_filepath):
            reply = QMessageBox.question(self, "Confirm File", f"The output file already exists:\n{output_filepath}\n\nDo you want to overwrite the existing file?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

        pos, use_n, total_steps = self._well_positions(), min(len(self.sequences), len(self._well_positions())), max(1,
                                                                                                                     self.oligo_len)
        self.progress.setValue(0)

        base_map_hex = {'ACT': '0x13', 'A': '0x14', 'T': '0x15', 'G': '0x16', 'C': '0x17'}

        final_output_content: List[str] = []
        injection_amount = self.injection_amount

        for cyc in range(self.oligo_len):
            final_output_content.append(f"cycle : {cyc + 1}")
            cycle_output_lines: List[str] = []

            well_map = defaultdict(lambda: defaultdict(set))
            for i in range(use_n):
                s = self.sequences[i]
                if cyc >= len(s):
                    continue
                base = s[::-1][cyc].upper()
                if base not in ("A", "C", "G", "T"):
                    continue
                x, y = pos[i]
                act_x, act_y = x + self.channel_offsets["ACT"], y + self.channel_y_offsets["ACT"]
                if 0 <= act_x < NOZZLE_COUNT_X:
                    well_map["ACT"][act_y].add(act_x)
                base_x, base_y = x + self.channel_offsets[base], y + self.channel_y_offsets[base]
                if 0 <= base_x < NOZZLE_COUNT_X:
                    well_map[base][base_y].add(base_x)

            for channel, y_coords in well_map.items():
                for y, x_coords in y_coords.items():
                    bits = [0] * NOZZLE_COUNT_X
                    for x in x_coords:
                        if 0 <= x < NOZZLE_COUNT_X:
                            bits[x] = 1

                    text_data_128chars = self._bits_to_string(bits)

                    slave_addr_str = base_map_hex.get(channel, "0x00")
                    final_y_position = self.start_position + y

                    line_data = f"head_{final_y_position}_{slave_addr_str}_{injection_amount}_{text_data_128chars}"
                    cycle_output_lines.append(line_data)

            cycle_output_lines.sort(key=lambda line: int(line.split('_')[1]), reverse=True)  # Change sorting criteria index
            final_output_content.extend(cycle_output_lines)

            self.progress.setValue(int((cyc + 1) * 100 / total_steps))
            QApplication.processEvents()

        try:
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write('\n'.join(final_output_content))
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"{output_filepath}: {e}")
            return

        QMessageBox.information(self, "Complete",
                                f"Text data generation complete!\nA total of {len(final_output_content)} lines (including headers) have been saved to the file:\n{output_filepath}")
        self.progress.setValue(100)

    def _settings_path(self) -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "sequence_manager_settings.json")

    def save_settings(self) -> None:
        self.project_name = self.edit_project_name.text().strip()
        data = {
            "y_step_interval": self.y_step_interval,
            "injection_amount": self.injection_amount,
            "start_position": self.start_position,
            "multipler_m": self.multipler_m,
            "offsets_x": self.channel_offsets,
            "offsets_y": self.channel_y_offsets,
            "base_output_dir": self.base_output_dir,
            "project_name": self.project_name
        }
        with open(self._settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_settings(self) -> None:
        fp = self._settings_path()
        if not os.path.isfile(fp):
            return

        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data.get("multipler_m"), int) and data["multipler_m"] >= 1:
            self.multipler_m = data["multipler_m"]
            self.pitch_ctrl.set_value(self.multipler_m)

        y_step = data.get("y_step_interval", data.get("y_scale_px", 50))
        if isinstance(y_step, int) and y_step >= 1:
            self.y_step_interval = y_step

        amount = data.get("injection_amount", data.get("well_size_px"))
        if isinstance(amount, int) and 1 <= amount <= 1000:
            self.injection_amount = amount
            self.spin_injection_amount.setValue(self.injection_amount)

        start_pos = data.get("start_position", 0)
        if isinstance(start_pos, int) and start_pos >= 0:
            self.start_position = start_pos

        if isinstance(data.get("base_output_dir"), str) and data["base_output_dir"]:
            self.base_output_dir = data["base_output_dir"]
            self.edit_outdir.setText(self.base_output_dir)

        if isinstance(data.get("project_name"), str) and data["project_name"]:
            self.project_name = data["project_name"]
            self.edit_project_name.setText(self.project_name)

        offs_x = data.get("offsets_x", data.get("offsets", {}))
        for ch in CHANNELS:
            self.channel_offsets[ch] = int(offs_x.get(ch, 0))
            if ch in self.offset_spins:
                self.offset_spins[ch].setValue(self.channel_offsets[ch])

        offs_y = data.get("offsets_y", {})
        for ch in CHANNELS:
            self.channel_y_offsets[ch] = int(offs_y.get(ch, 0))
            if ch in self.offset_y_spins:
                self.offset_y_spins[ch].setValue(self.channel_y_offsets[ch])

        self.spin_y_step_interval.setValue(self.y_step_interval)
        self._sync_to_state()

    def on_save_settings(self) -> None:
        try:
            self.save_settings()
            QMessageBox.information(self, "Settings", "Current settings have been saved.")
        except Exception as e:
            QMessageBox.warning(self, "Settings", "Failed to save settings: " + str(e))


# ---------- Entry Point ----------
def main() -> None:
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()