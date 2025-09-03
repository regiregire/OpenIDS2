#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt5 앱: 128노즐 프린트헤드(노즐 피치 137.1 µm)용 Activator/염기(A/T/G/C) 분사용 마스크 생성기

업데이트 사항
- 세로 스케일, 웰 도트 크기, 피치 배수, 채널별 X 오프셋, 출력 폴더를 설정 파일(~/.printhead_mask_settings.json)에 저장/자동불러오기
- 초기값: 세로 스케일=471, 웰 도트=3, 피치 배수=4
- Y 픽셀 직접 조절 제거(H0=(rows-1)*m+1 자동), 세로 스케일 px로 NEAREST 리샘플링(미리보기/저장)
- 입력은 5'→3', 렌더/저장은 3'→5'(역순)
- 채널별 X 오프셋(px) 적용(ACT, A, C, G, T)
- 저장은 BMP 1비트(흑/백)
"""

import os
import sys
import json
from typing import List, Tuple, Dict

# --- 자동 패키지 설치(없으면 pip로 설치) ---
import subprocess
import importlib

def _ensure_packages() -> None:
    required = [("PyQt5", "PyQt5"), ("pandas", "pandas"), ("PIL", "Pillow"), ("openpyxl", "openpyxl")]
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
            print("[경고] 패키지 자동 설치 실패:", e)

_ensure_packages()

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QSpinBox, QSlider,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QLineEdit,
    QAbstractSpinBox, QToolButton
)

import pandas as pd
from PIL import Image

# --- PIL(Image) → QImage 변환(호환용) ---
def pil_to_qimage(img: Image.Image) -> QtGui.QImage:
    if img.mode == "L":
        w, h = img.size
        data = img.tobytes("raw", "L")
        qimg = QtGui.QImage(data, w, h, w, QtGui.QImage.Format_Grayscale8)
        return qimg.copy()
    if img.mode == "RGB":
        w, h = img.size
        data = img.tobytes("raw", "RGB")
        qimg = QtGui.QImage(data, w, h, w * 3, QtGui.QImage.Format_RGB888)
        return qimg.copy()
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    data = img.tobytes("raw", "RGBA")
    qimg = QtGui.QImage(data, w, h, w * 4, QtGui.QImage.Format_RGBA8888)
    return qimg.copy()

# ------------------- 상수 -------------------
NOZZLE_COUNT_X = 128
NOZZLE_PITCH_UM = 137.1  # µm
CHANNELS = ["A", "C", "G", "T", "ACT"]
COLOR_WHITE = 255
COLOR_BLACK = 0
PREVIEW_COLORS = {"A": (255, 0, 0), "C": (0, 180, 0), "G": (0, 0, 255), "T": (200, 0, 200), "ACT": (160, 160, 160)}

# ------------------- 유틸 -------------------
def clamp(v: int, vmin: int, vmax: int) -> int:
    return max(vmin, min(v, vmax))

# 안전 도장(L/1/RGB 지원, 경계/음수 좌표 클리핑)
def _paste_square_L(img: Image.Image, x: int, y: int, size: int) -> None:
    size = max(1, int(size))
    W, H = img.size
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + size)
    y1 = min(H, y + size)
    if x1 <= x0 or y1 <= y0:
        return
    mode = img.mode if img.mode in ("1", "L") else "L"
    black = 0
    tile = Image.new(mode, (x1 - x0, y1 - y0), color=black)
    img.paste(tile, (x0, y0))

def _paste_square_RGB(img: Image.Image, x: int, y: int, size: int, rgb: tuple) -> None:
    size = max(1, int(size))
    W, H = img.size
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + size)
    y1 = min(H, y + size)
    if x1 <= x0 or y1 <= y0:
        return
    tile = Image.new("RGB", (x1 - x0, y1 - y0), color=rgb)
    img.paste(tile, (x0, y0))

# ------------------- 위젯 -------------------
class PitchControl(QWidget):
    changed = QtCore.pyqtSignal(int)
    def __init__(self, parent=None, m_init: int = 4) -> None:  # 초기값 4
        super().__init__(parent)
        self.m = max(1, int(m_init))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.btn_minus = QToolButton(self); self.btn_minus.setText("-"); self.btn_minus.clicked.connect(self.dec); layout.addWidget(self.btn_minus)
        self.label = QLabel(self); self.label.setAlignment(Qt.AlignCenter); layout.addWidget(self.label, 1)
        self.btn_plus = QToolButton(self); self.btn_plus.setText("+"); self.btn_plus.clicked.connect(self.inc); layout.addWidget(self.btn_plus)
        self.update_label()
    def inc(self) -> None:
        self.m += 1; self.update_label(); self.changed.emit(self.m)
    def dec(self) -> None:
        if self.m > 1:
            self.m -= 1; self.update_label(); self.changed.emit(self.m)
    def set_value(self, m: int) -> None:
        m = max(1, int(m))
        if m != self.m:
            self.m = m; self.update_label(); self.changed.emit(self.m)
    def value(self) -> int:
        return self.m
    def update_label(self) -> None:
        pitch_um = self.m * NOZZLE_PITCH_UM
        self.label.setText(f"피치: {pitch_um:.1f} µm  (m = {self.m})")

class ImagePreview(QWidget):
    class CanvasView(QtWidgets.QGraphicsView):
        zoomChanged = QtCore.pyqtSignal(int)
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.setScene(QtWidgets.QGraphicsScene(self))
            self._pix = QtWidgets.QGraphicsPixmapItem(); self.scene().addItem(self._pix)
            self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(17, 17, 17)))
            self.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
            self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._zoom = 1.0
        def set_image(self, qimg: QtGui.QImage | None) -> None:
            if qimg is None:
                self._pix.setPixmap(QtGui.QPixmap()); self.scene().setSceneRect(QtCore.QRectF()); return
            pm = QtGui.QPixmap.fromImage(qimg); self._pix.setPixmap(pm); self.scene().setSceneRect(QtCore.QRectF(pm.rect()))
        def set_zoom_percent(self, p: int) -> None:
            p = max(10, min(800, int(p))); self._zoom = p / 100.0; self._apply_zoom()
        def _apply_zoom(self) -> None:
            self.resetTransform(); self.scale(self._zoom, self._zoom)
        def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
            angle = event.angleDelta().y() / 120.0
            if angle == 0: return
            factor = 1.1 ** angle; new_zoom = max(0.1, min(8.0, self._zoom * factor)); self._zoom = new_zoom
            self._apply_zoom(); self.zoomChanged.emit(int(round(self._zoom * 100))); event.accept()
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        ctr = QHBoxLayout(); ctr.setSpacing(6)
        self.lbl_zoom = QLabel("줌: 100%"); self.btn_zoom_out = QToolButton(); self.btn_zoom_out.setText("-"); self.btn_zoom_in = QToolButton(); self.btn_zoom_in.setText("+")
        self.btn_zoom_1x = QToolButton(); self.btn_zoom_1x.setText("100%")
        self.slider_zoom = QSlider(Qt.Horizontal); self.slider_zoom.setRange(10, 800); self.slider_zoom.setValue(100)
        for w in (QLabel("줌:"), self.btn_zoom_out, self.slider_zoom, self.btn_zoom_in, self.btn_zoom_1x, self.lbl_zoom): ctr.addWidget(w)
        v.addLayout(ctr)
        self.view = self.CanvasView(self); self.view.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        v.addWidget(self.view, 1)
        self._src_qimg: QtGui.QImage | None = None
        self.slider_zoom.valueChanged.connect(self._on_zoom_slider)
        self.btn_zoom_out.clicked.connect(lambda: self.set_zoom_percent(self.zoom_percent() - 10))
        self.btn_zoom_in.clicked.connect(lambda: self.set_zoom_percent(self.zoom_percent() + 10))
        self.btn_zoom_1x.clicked.connect(lambda: self.set_zoom_percent(100))
        self.view.zoomChanged.connect(self._sync_zoom_from_view)
    def _sync_zoom_from_view(self, p: int) -> None:
        self.slider_zoom.blockSignals(True); self.slider_zoom.setValue(p); self.slider_zoom.blockSignals(False); self.lbl_zoom.setText(f"줌: {p}%")
    def set_qimage(self, qimg: QtGui.QImage | None) -> None:
        self._src_qimg = qimg; self.view.set_image(qimg)
    def zoom_percent(self) -> int:
        return self.slider_zoom.value()
    def set_zoom_percent(self, p: int) -> None:
        p = max(10, min(800, int(p))); self.view.set_zoom_percent(p); self._sync_zoom_from_view(p)
    def _on_zoom_slider(self, v: int) -> None:
        self.view.set_zoom_percent(v); self.lbl_zoom.setText(f"줌: {v}%")

# ------------------- 메인 윈도우 -------------------
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Printhead Mask Generator (PyQt5)")
        self.resize(1350, 860)
        self.multipler_m = 4              # 초기 피치 배수 4
        self.cols = 25
        self.rows = 40
        self.oligo_len = 0
        self.well_size_px = 3             # 초기 웰 도트 3
        self.sequences: List[str] = []
        self.output_dir = os.path.abspath("out")
        self.channel_offsets: Dict[str, int] = {ch: 0 for ch in ["ACT", "A", "C", "G", "T"]}
        self.y_scale_px = 471             # 초기 세로 스케일 471
        self._build_ui()
        # 설정 자동 불러오기(있으면 UI/내부 적용)
        try:
            self.load_settings()
        except Exception as e:
            print("[설정 불러오기 경고]", e)
        self._refresh_constraints()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        cw = QWidget(self); self.setCentralWidget(cw)
        root = QHBoxLayout(cw); root.setContentsMargins(8, 8, 8, 8); root.setSpacing(8)
        left = QVBoxLayout(); left.setSpacing(8)

        # 기하/그리드
        geo_group = QGroupBox("기하/그리드 설정"); geo = QGridLayout(geo_group); geo.setHorizontalSpacing(8); geo.setVerticalSpacing(6)
        geo.addWidget(QLabel("노즐 수(X 픽셀):"), 0, 0); self.lbl_nozzles = QLabel(str(NOZZLE_COUNT_X)); geo.addWidget(self.lbl_nozzles, 0, 1)
        geo.addWidget(QLabel("웰 간격(노즐 피치 배수):"), 1, 0); self.pitch_ctrl = PitchControl(m_init=self.multipler_m); self.pitch_ctrl.changed.connect(self.on_pitch_changed); geo.addWidget(self.pitch_ctrl, 1, 1, 1, 2)
        self.spin_cols = QSpinBox(); self.spin_cols.setRange(1, 128); self.spin_cols.setValue(self.cols); self.spin_cols.setAccelerated(True); self.spin_cols.setButtonSymbols(QAbstractSpinBox.PlusMinus); self.spin_cols.valueChanged.connect(self.on_cols_changed)
        self.spin_rows = QSpinBox(); self.spin_rows.setRange(1, 10000); self.spin_rows.setValue(self.rows); self.spin_rows.setAccelerated(True); self.spin_rows.setButtonSymbols(QAbstractSpinBox.PlusMinus); self.spin_rows.valueChanged.connect(self.on_rows_changed)
        geo.addWidget(QLabel("웰 열 수(가로, X):"), 2, 0); geo.addWidget(self.spin_cols, 2, 1)
        geo.addWidget(QLabel("웰 행 수(세로, Y):"), 3, 0); geo.addWidget(self.spin_rows, 3, 1)
        geo.addWidget(QLabel("기본 높이 H0 (px):"), 4, 0); self.lbl_y_base = QLabel(str(self._calc_y_base())); geo.addWidget(self.lbl_y_base, 4, 1)
        geo.addWidget(QLabel("세로 스케일(출력 높이, px):"), 5, 0); self.spin_y_scale = QSpinBox(); self.spin_y_scale.setRange(1, 200000); self.spin_y_scale.setValue(self.y_scale_px); self.spin_y_scale.setAccelerated(True); self.spin_y_scale.valueChanged.connect(self.on_y_scale_changed); geo.addWidget(self.spin_y_scale, 5, 1)
        geo.addWidget(QLabel("웰 도트 크기(px, 정사각):"), 6, 0); self.spin_well_px = QSpinBox(); self.spin_well_px.setRange(1, 512); self.spin_well_px.setValue(self.well_size_px); self.spin_well_px.setAccelerated(True); self.spin_well_px.setButtonSymbols(QAbstractSpinBox.PlusMinus); self.spin_well_px.valueChanged.connect(self.on_well_px_changed); geo.addWidget(self.spin_well_px, 6, 1)
        geo.addWidget(QLabel("올리고 길이(자동):"), 7, 0); self.lbl_len_auto = QLabel("0 bp"); geo.addWidget(self.lbl_len_auto, 7, 1)
        self.lbl_constraints = QLabel(""); self.lbl_constraints.setStyleSheet("color:#c77; font-weight:600;"); geo.addWidget(self.lbl_constraints, 8, 0, 1, 3)
        left.addWidget(geo_group)

        # 채널 오프셋
        off_group = QGroupBox("채널 X 오프셋(px)"); off = QGridLayout(off_group)
        self.offset_spins: Dict[str, QSpinBox] = {}
        for i, ch in enumerate(["ACT", "A", "C", "G", "T"]):
            off.addWidget(QLabel(ch + ":"), i, 0)
            sp = QSpinBox(); sp.setRange(-128, 128); sp.setValue(self.channel_offsets[ch]); sp.setAccelerated(True); sp.valueChanged.connect(lambda v, ch=ch: self.on_offset_changed(ch, v)); off.addWidget(sp, i, 1)
            self.offset_spins[ch] = sp
        left.addWidget(off_group)

        # 시퀀스 입력
        seq_group = QGroupBox("시퀀스 입력"); seq = QGridLayout(seq_group); seq.setHorizontalSpacing(8); seq.setVerticalSpacing(6)
        self.btn_load = QPushButton("시퀀스 불러오기(다중 파일)"); self.btn_load.clicked.connect(self.on_load_sequences); seq.addWidget(self.btn_load, 0, 0, 1, 2)
        self.lbl_seq_hint = QLabel("불러오는 서열은 5'→3' 기준입니다. 이미지는 3'→5' 방향으로 생성됩니다."); self.lbl_seq_hint.setStyleSheet("color:#888;"); seq.addWidget(self.lbl_seq_hint, 1, 0, 1, 2)
        self.list_files = QListWidget(); self.list_files.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection); seq.addWidget(self.list_files, 2, 0, 3, 2)
        self.btn_clear = QPushButton("목록 비우기"); self.btn_clear.clicked.connect(self.on_clear_sequences); seq.addWidget(self.btn_clear, 5, 0)
        self.lbl_seq_summary = QLabel("로드된 시퀀스: 0"); seq.addWidget(self.lbl_seq_summary, 5, 1)
        left.addWidget(seq_group, 1)

        # 출력 및 실행
        out_group = QGroupBox("출력 및 실행"); out = QGridLayout(out_group); out.setHorizontalSpacing(8); out.setVerticalSpacing(6)
        out.addWidget(QLabel("출력 폴더:"), 0, 0); self.edit_outdir = QLineEdit(self.output_dir); self.edit_outdir.setReadOnly(True); out.addWidget(self.edit_outdir, 0, 1)
        self.btn_browse = QPushButton("변경…"); self.btn_browse.clicked.connect(self.on_browse_outdir); out.addWidget(self.btn_browse, 0, 2)
        self.btn_generate = QPushButton("마스크 생성"); self.btn_generate.setStyleSheet("font-weight:700; padding:8px 12px;"); self.btn_generate.clicked.connect(self.on_generate); out.addWidget(self.btn_generate, 1, 0, 1, 3)
        self.progress = QProgressBar(); self.progress.setValue(0); out.addWidget(self.progress, 2, 0, 1, 3)
        self.btn_save_settings = QPushButton("설정 저장"); self.btn_save_settings.clicked.connect(self.on_save_settings); out.addWidget(self.btn_save_settings, 3, 0, 1, 3)
        left.addWidget(out_group)

        # 우측 미리보기
        right = QVBoxLayout()
        prev_group = QGroupBox("미리보기(컬러 오버레이)"); prev_group.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        prev = QGridLayout(prev_group)
        prev.addWidget(QLabel("사이클:"), 0, 0)
        self.slider_cycle = QSlider(Qt.Horizontal); self.slider_cycle.setRange(1, 1); self.slider_cycle.setValue(1); self.slider_cycle.valueChanged.connect(self.update_preview); prev.addWidget(self.slider_cycle, 0, 1)
        self.lbl_cycle_val = QLabel("1"); prev.addWidget(self.lbl_cycle_val, 0, 2)
        self.lbl_legend = QLabel("A=빨강  C=초록  G=파랑  T=보라  ACT=회색"); self.lbl_legend.setStyleSheet("color:#aaa;"); prev.addWidget(self.lbl_legend, 1, 0, 1, 3)
        self.preview = ImagePreview(); prev.addWidget(self.preview, 2, 0, 1, 3)
        right.addWidget(prev_group, 1)

        root.addLayout(left, 0); root.addLayout(right, 1)
        self._sync_to_state()

    # ---------- 상태/제약 ----------
    def _calc_y_base(self) -> int:
        return max(1, (self.rows - 1) * self.multipler_m + 1)

    def _sync_to_state(self) -> None:
        self.pitch_ctrl.set_value(self.multipler_m)
        self.spin_cols.setValue(self.cols); self.spin_rows.setValue(self.rows)
        self.lbl_y_base.setText(str(self._calc_y_base()))
        # 유지 모드(B): y_scale_px 값은 유지, 스핀박스 표시만 동기화
        self.spin_y_scale.blockSignals(True); self.spin_y_scale.setValue(self.y_scale_px); self.spin_y_scale.blockSignals(False)
        self._sync_oligo_ui(); self.slider_cycle.setRange(1, max(1, self.oligo_len))
        self._update_seq_summary(); self._refresh_constraints(); self.update_preview()

    def _sync_oligo_ui(self) -> None:
        self.lbl_len_auto.setText(f"{self.oligo_len} bp")

    def _update_seq_summary(self) -> None:
        n = len(self.sequences); max_len = max((len(s) for s in self.sequences), default=0)
        self.lbl_seq_summary.setText(f"로드된 시퀀스: {n} (최장 {max_len} bp)")

    def _refresh_constraints(self) -> None:
        max_cols = NOZZLE_COUNT_X // self.multipler_m
        if self.cols > max_cols:
            self.cols = max_cols; self.spin_cols.blockSignals(True); self.spin_cols.setValue(self.cols); self.spin_cols.blockSignals(False)
        warn = []
        if max_cols <= 0:
            warn.append("피치 배수가 너무 큽니다. 열 수를 0보다 크게 유지하려면 m을 줄이세요.")
        if self.cols * self.multipler_m > NOZZLE_COUNT_X:
            warn.append("열 수 × 피치(px)가 128을 초과합니다.")
        if self.well_size_px > self.multipler_m:
            warn.append("웰 도트 크기가 피치보다 큽니다: 인접 웰과 겹칠 수 있습니다.")
        if len(self.sequences) > (self.cols * self.rows):
            warn.append("로드된 시퀀스가 웰 개수보다 많아 초과분은 무시됩니다.")
        self.lbl_constraints.setText("\n".join(warn))

    # ---------- 이벤트 ----------
    def on_pitch_changed(self, m: int) -> None:
        self.multipler_m = max(1, int(m)); self._sync_to_state()
    def on_cols_changed(self, v: int) -> None:
        self.cols = int(v); self._refresh_constraints(); self.update_preview()
    def on_rows_changed(self, v: int) -> None:
        self.rows = int(v); self._sync_to_state()
    def on_y_scale_changed(self, v: int) -> None:
        self.y_scale_px = int(v); self.update_preview()
    def on_well_px_changed(self, v: int) -> None:
        self.well_size_px = int(v); self._refresh_constraints(); self.update_preview()
    def on_offset_changed(self, ch: str, v: int) -> None:
        self.channel_offsets[ch] = int(v); self.update_preview()
    def on_browse_outdir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "출력 폴더 선택", self.output_dir)
        if d:
            self.output_dir = d; self.edit_outdir.setText(self.output_dir)
    def on_clear_sequences(self) -> None:
        self.sequences.clear(); self.list_files.clear(); self.oligo_len = 0; self._sync_oligo_ui(); self.slider_cycle.setRange(1, 1); self._update_seq_summary(); self.update_preview()

    def on_load_sequences(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "시퀀스 파일 선택(다중)", "", "지원 형식 (*.xlsx *.xls *.csv *.txt);;모든 파일 (*)")
        if not files:
            return
        errors = []
        for fp in files:
            try:
                seqs, info = self._read_sequences_from_file(fp)
                for s in seqs:
                    clean = "".join(str(s).strip().upper().replace(" ", "").replace("\t", ""))
                    self.sequences.append(clean)
                item = QListWidgetItem(f"{os.path.basename(fp)}  —  {info}"); item.setToolTip(fp); self.list_files.addItem(item)
            except Exception as e:
                errors.append(f"{os.path.basename(fp)}: {e}")
        self.oligo_len = max((len(s) for s in self.sequences), default=0)
        self._sync_to_state()
        if errors:
            QMessageBox.warning(self, "읽기 오류", "\n".join(errors))

    def _read_sequences_from_file(self, fp: str) -> Tuple[List[str], str]:
        ext = os.path.splitext(fp)[1].lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(fp, header=None, engine=("openpyxl" if ext == ".xlsx" else None))
        elif ext == ".csv":
            df = pd.read_csv(fp, header=None)
        else:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip()]
            if lines and all(len(x) == 1 for x in lines):
                return (["".join(lines)], f"세로형 1개, 길이 {len(lines)}")
            return (lines, f"가로형 {len(lines)}개")
        col = df.iloc[:, 0].dropna().astype(str).str.strip()
        vals = [v for v in col.tolist() if v != ""]
        if not vals:
            return ([], "비어 있음")
        if all(len(v) == 1 for v in vals):
            return (["".join(vals)], f"세로형 1개, 길이 {len(vals)}")
        return (vals, f"가로형 {len(vals)}개")

    # ---------- 좌표/렌더 ----------
    def _well_positions(self) -> List[Tuple[int, int]]:
        pos: List[Tuple[int, int]] = []
        m = self.multipler_m
        for r in range(self.rows):
            for c in range(self.cols):
                x = c * m; y = r * m; pos.append((x, y))
        return pos

    def _render_preview_overlay_qimage(self, cycle_idx_1based: int) -> QtGui.QImage:
        W = NOZZLE_COUNT_X
        H0 = self._calc_y_base()
        img = Image.new("RGB", (W, H0), color=(255, 255, 255))
        idx = clamp(cycle_idx_1based - 1, 0, max(0, self.oligo_len - 1))
        pos = self._well_positions(); use_n = min(len(self.sequences), len(pos))
        for i in range(use_n):
            s = self.sequences[i]
            if idx >= len(s):
                continue
            b = s[::-1][idx].upper()  # 3'→5' 역방향
            if b not in ("A", "C", "G", "T"):
                continue
            x, y = pos[i]
            _paste_square_RGB(img, x + self.channel_offsets["ACT"], y, self.well_size_px, PREVIEW_COLORS["ACT"])
            _paste_square_RGB(img, x + self.channel_offsets[b], y, self.well_size_px, PREVIEW_COLORS[b])
        if self.y_scale_px != H0:
            img = img.resize((W, self.y_scale_px), resample=Image.NEAREST)
        return pil_to_qimage(img)

    # ---------- 미리보기 갱신 ----------
    def update_preview(self) -> None:
        cycle = self.slider_cycle.value(); self.lbl_cycle_val.setText(str(cycle))
        qimg = self._render_preview_overlay_qimage(cycle); self.preview.set_qimage(qimg)

    # ---------- 저장 ----------
    def on_generate(self) -> None:
        # 설정 먼저 저장(사용자 의도: 저장하기 누르면 다음 시작 시 자동 불러오기)
        try:
            self.save_settings()
        except Exception as e:
            print("[설정 저장 경고]", e)
        if (not self.sequences) or (self.oligo_len <= 0):
            QMessageBox.warning(self, "경고", "시퀀스를 먼저 불러오세요."); return
        outdir = self.output_dir
        if os.path.isdir(outdir):
            reply = QMessageBox.question(self, "폴더 확인", "출력 폴더가 이미 존재합니다:\n" + outdir + "\n\n덮어쓰시겠습니까?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        os.makedirs(outdir, exist_ok=True)
        outdirs = {ch: os.path.join(outdir, ch) for ch in CHANNELS}
        for d in outdirs.values(): os.makedirs(d, exist_ok=True)
        W = NOZZLE_COUNT_X
        H0 = self._calc_y_base()
        pos = self._well_positions(); use_n = min(len(self.sequences), len(pos))
        total_steps = max(1, self.oligo_len * len(CHANNELS)); self.progress.setValue(0); step = 0
        for cyc in range(self.oligo_len):
            canv = {ch: Image.new("1", (W, H0), color=1) for ch in CHANNELS}  # 1비트, 흰색 배경
            for i in range(use_n):
                s = self.sequences[i]
                base = s[::-1][cyc].upper() if cyc < len(s) else ""
                if base not in ("A", "C", "G", "T"):
                    continue
                x, y = pos[i]
                _paste_square_L(canv[base], x + self.channel_offsets[base], y, self.well_size_px)
                _paste_square_L(canv["ACT"],  x + self.channel_offsets["ACT"], y, self.well_size_px)
            for ch in CHANNELS:
                step += 1
                out_img = canv[ch]
                if self.y_scale_px != H0:
                    out_img = out_img.resize((W, self.y_scale_px), resample=Image.NEAREST)
                if out_img.mode != "1":
                    out_img = out_img.convert("1", dither=Image.NONE)
                fn = os.path.join(outdirs[ch], f"{cyc + 1}_{ch}.bmp")
                try:
                    out_img.save(fn, format="BMP")
                except Exception as e:
                    QMessageBox.critical(self, "저장 오류", f"{fn}: {e}"); return
                self.progress.setValue(int(step * 100 / total_steps)); QApplication.processEvents()
        QMessageBox.information(self, "완료", "마스크 생성 완료! 출력 폴더: " + outdir)

    # ---------- 설정 저장/불러오기 ----------
    def _settings_path(self) -> str:
        # main.py 기준 프로젝트 루트 경로
        root_dir = os.path.dirname(os.path.abspath(__file__))
        # 루트에 고정 저장
        return os.path.join(root_dir, "printhead_mask_settings.json")

    def save_settings(self) -> None:
        data = {
            "y_scale_px": int(self.y_scale_px),
            "well_size_px": int(self.well_size_px),
            "multipler_m": int(self.multipler_m),
            "offsets": {ch: int(self.channel_offsets.get(ch, 0)) for ch in ["ACT", "A", "C", "G", "T"]},
            "output_dir": str(self.output_dir)
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
            self.multipler_m = data["multipler_m"]; self.pitch_ctrl.set_value(self.multipler_m)
        if isinstance(data.get("y_scale_px"), int) and data["y_scale_px"] >= 1:
            self.y_scale_px = data["y_scale_px"]
        if isinstance(data.get("well_size_px"), int) and 1 <= data["well_size_px"] <= 512:
            self.well_size_px = data["well_size_px"]; self.spin_well_px.setValue(self.well_size_px)
        if isinstance(data.get("output_dir"), str) and data["output_dir"]:
            self.output_dir = data["output_dir"]; self.edit_outdir.setText(self.output_dir)
        offs = data.get("offsets", {})
        for ch in ["ACT", "A", "C", "G", "T"]:
            try: val = int(offs.get(ch, 0))
            except Exception: val = 0
            self.channel_offsets[ch] = max(-128, min(128, val))
            if ch in self.offset_spins:
                self.offset_spins[ch].setValue(self.channel_offsets[ch])
        # 수치 UI 표시에 반영
        self.spin_y_scale.setValue(self.y_scale_px)
        self._sync_to_state()

    def on_save_settings(self) -> None:
        try:
            self.save_settings()
            QMessageBox.information(self, "설정", "현재 설정을 저장했습니다.")
        except Exception as e:
            QMessageBox.warning(self, "설정", "설정 저장 실패: " + str(e))

# ---------- 엔트리 포인트 ----------
def main() -> None:
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
