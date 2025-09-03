import os
import sys
from typing import List

# --- 자동 패키지 설치(없으면 pip로 설치) ---
import subprocess
import importlib


def _ensure_packages() -> None:
    required = [("PyQt5", "PyQt5"), ("PIL", "Pillow")]
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
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QSlider,
    QListWidget, QListWidgetItem, QLineEdit, QToolButton
)
from PIL import Image


# --- PIL(Image) → QImage 변환(호환용) ---
def pil_to_qimage(img: Image.Image) -> QtGui.QImage:
    if img.mode == "L" or img.mode == "1":
        # '1' 모드는 'L'로 변환하여 처리
        if img.mode == '1':
            img = img.convert('L')
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
BYTES_PER_LINE = NOZZLE_COUNT_X // 8


# ------------------- 이미지 미리보기 위젯 (sequence_manager.py에서 가져옴) -------------------
class ImagePreview(QWidget):
    class CanvasView(QtWidgets.QGraphicsView):
        zoomChanged = QtCore.pyqtSignal(int)

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.setScene(QtWidgets.QGraphicsScene(self))
            self._pix = QtWidgets.QGraphicsPixmapItem();
            self.scene().addItem(self._pix)
            self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(17, 17, 17)))
            self.setFrameShape(QtWidgets.QFrame.NoFrame)
            self.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.SmoothPixmapTransform)
            self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
            self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorViewCenter)
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._zoom = 1.0

        def set_image(self, qimg: QtGui.QImage | None) -> None:
            if qimg is None:
                self._pix.setPixmap(QtGui.QPixmap());
                self.scene().setSceneRect(QtCore.QRectF());
                return
            pm = QtGui.QPixmap.fromImage(qimg);
            self._pix.setPixmap(pm);
            self.scene().setSceneRect(QtCore.QRectF(pm.rect()))

        def set_zoom_percent(self, p: int) -> None:
            p = max(10, min(800, int(p)));
            self._zoom = p / 100.0;
            self._apply_zoom()

        def _apply_zoom(self) -> None:
            self.resetTransform();
            self.scale(self._zoom, self._zoom)

        def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
            angle = event.angleDelta().y() / 120.0
            if angle == 0: return
            factor = 1.1 ** angle;
            new_zoom = max(0.1, min(8.0, self._zoom * factor));
            self._zoom = new_zoom
            self._apply_zoom();
            self.zoomChanged.emit(int(round(self._zoom * 100)));
            event.accept()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        v = QVBoxLayout(self);
        v.setContentsMargins(0, 0, 0, 0)
        ctr = QHBoxLayout();
        ctr.setSpacing(6)
        self.lbl_zoom = QLabel("줌: 100%");
        self.btn_zoom_out = QToolButton();
        self.btn_zoom_out.setText("-");
        self.btn_zoom_in = QToolButton();
        self.btn_zoom_in.setText("+")
        self.btn_zoom_1x = QToolButton();
        self.btn_zoom_1x.setText("100%")
        self.slider_zoom = QSlider(Qt.Horizontal);
        self.slider_zoom.setRange(10, 800);
        self.slider_zoom.setValue(100)
        for w in (QLabel("줌:"), self.btn_zoom_out, self.slider_zoom, self.btn_zoom_in, self.btn_zoom_1x,
                  self.lbl_zoom): ctr.addWidget(w)
        v.addLayout(ctr)
        self.view = self.CanvasView(self);
        self.view.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        v.addWidget(self.view, 1)
        self._src_qimg: QtGui.QImage | None = None
        self.slider_zoom.valueChanged.connect(self._on_zoom_slider)
        self.btn_zoom_out.clicked.connect(lambda: self.set_zoom_percent(self.zoom_percent() - 10))
        self.btn_zoom_in.clicked.connect(lambda: self.set_zoom_percent(self.zoom_percent() + 10))
        self.btn_zoom_1x.clicked.connect(lambda: self.set_zoom_percent(100))
        self.view.zoomChanged.connect(self._sync_zoom_from_view)

    def _sync_zoom_from_view(self, p: int) -> None:
        self.slider_zoom.blockSignals(True);
        self.slider_zoom.setValue(p);
        self.slider_zoom.blockSignals(False);
        self.lbl_zoom.setText(f"줌: {p}%")

    def set_qimage(self, qimg: QtGui.QImage | None) -> None:
        self._src_qimg = qimg;
        self.view.set_image(qimg)

    def zoom_percent(self) -> int:
        return self.slider_zoom.value()

    def set_zoom_percent(self, p: int) -> None:
        p = max(10, min(800, int(p)));
        self.view.set_zoom_percent(p);
        self._sync_zoom_from_view(p)

    def _on_zoom_slider(self, v: int) -> None:
        self.view.set_zoom_percent(v);
        self.lbl_zoom.setText(f"줌: {v}%")


# ------------------- 메인 윈도우 -------------------
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("바이너리 데이터 뷰어")
        self.resize(1024, 768)
        self._build_ui()

    def _build_ui(self) -> None:
        cw = QWidget(self);
        self.setCentralWidget(cw)
        root = QHBoxLayout(cw);
        root.setContentsMargins(8, 8, 8, 8);
        root.setSpacing(8)

        # 좌측 컨트롤 패널
        left = QVBoxLayout();
        left.setSpacing(8)

        # 폴더 선택 그룹
        folder_group = QGroupBox("파일 로드");
        folder_layout = QGridLayout(folder_group)
        self.btn_browse = QPushButton("폴더 선택...");
        self.btn_browse.clicked.connect(self.on_select_folder)
        self.edit_folder = QLineEdit();
        self.edit_folder.setPlaceholderText("결과물 'out' 폴더를 선택하세요")
        folder_layout.addWidget(self.edit_folder, 0, 0);
        folder_layout.addWidget(self.btn_browse, 0, 1)

        # 파일 목록
        self.list_files = QListWidget();
        self.list_files.currentItemChanged.connect(self.on_file_selected)

        left.addWidget(folder_group)
        left.addWidget(self.list_files, 1)  # 남은 공간 모두 차지

        # 우측 미리보기 패널
        right = QVBoxLayout()
        preview_group = QGroupBox("이미지 미리보기");
        preview_layout = QVBoxLayout(preview_group)
        self.preview = ImagePreview()
        self.lbl_info = QLabel("이미지 정보: ");
        self.lbl_info.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.lbl_info)
        preview_layout.addWidget(self.preview, 1)
        right.addWidget(preview_group)

        root.addLayout(left, 1);
        root.addLayout(right, 3)  # 1:3 비율로 공간 분할

    def on_select_folder(self):
        """ 폴더 선택 대화상자를 열고 내부의 바이너리 파일을 찾아서 목록에 추가합니다. """
        directory = QFileDialog.getExistingDirectory(self, "결과 폴더 선택", ".")
        if not directory:
            return

        self.edit_folder.setText(directory)
        self.list_files.clear()
        self.preview.set_qimage(None)
        self.lbl_info.setText("이미지 정보: ")

        binary_files = find_binary_files(directory)
        for file_path in binary_files:
            item = QListWidgetItem(os.path.relpath(file_path, directory))
            item.setData(Qt.UserRole, file_path)  # 전체 경로를 데이터로 저장
            self.list_files.addItem(item)

    def on_file_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """ 파일 목록에서 항목을 선택했을 때 미리보기를 업데이트합니다. """
        if current is None:
            return

        file_path = current.data(Qt.UserRole)
        image = binary_to_image(file_path)

        if image:
            q_image = pil_to_qimage(image)
            self.preview.set_qimage(q_image)
            self.lbl_info.setText(f"이미지 정보: {image.width} x {image.height} px")
        else:
            self.preview.set_qimage(None)
            self.lbl_info.setText("이미지 정보: 로드 실패")


# --- 로직 수정 ---
def find_binary_files(root_dir: str) -> List[str]:
    """지정된 디렉토리에서 .bin 확장자를 가진 파일을 찾습니다."""
    if not os.path.isdir(root_dir):
        print(f"[오류] 디렉토리를 찾을 수 없습니다: {root_dir}", file=sys.stderr)
        return []

    binary_files = []
    # os.walk를 사용하지 않고 해당 폴더만 검색
    for filename in os.listdir(root_dir):
        if filename.lower().endswith('.bin'):
            full_path = os.path.join(root_dir, filename)
            if os.path.isfile(full_path):
                 binary_files.append(full_path)

    if not binary_files:
        print(f"[정보] '{root_dir}' 에서 .bin 파일을 찾지 못했습니다.", file=sys.stderr)

    return sorted(binary_files)


def binary_to_image(file_path: str) -> Image.Image | None:
    """지정된 경로의 바이너리 파일을 읽어 Pillow 이미지 객체로 변환합니다."""
    if not os.path.exists(file_path):
        print(f"[오류] 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
        return None

    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except IOError as e:
        print(f"[오류] 파일을 읽는 중 문제가 발생했습니다: {e}", file=sys.stderr)
        return None

    if len(data) % BYTES_PER_LINE != 0:
        print(f"[경고] 파일 크기({len(data)}B)가 한 줄 크기({BYTES_PER_LINE}B)의 배수가 아닙니다.", file=sys.stderr)

    if not data:
        print(f"[정보] 파일이 비어있습니다: {file_path}", file=sys.stderr)
        return None

    height = len(data) // BYTES_PER_LINE
    width = NOZZLE_COUNT_X

    img = Image.new('1', (width, height), 1)
    pixels = img.load()

    for y in range(height):
        for byte_idx in range(BYTES_PER_LINE):
            data_idx = y * BYTES_PER_LINE + byte_idx
            if data_idx < len(data): # 데이터 길이 초과 방지
                current_byte = data[data_idx]

                for bit_idx in range(8):
                    if (current_byte >> (7 - bit_idx)) & 1:
                        px_x = byte_idx * 8 + bit_idx
                        pixels[px_x, y] = 0

    return img


# ------------------- 엔트리 포인트 -------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())
