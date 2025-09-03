# ui/tabs/sequence_tab.py
import os
import sys
from PyQt5 import QtWidgets

# --- Start of Fix ---
# 현재 파일(sequence_tab.py)이 위치한 폴더의 경로를 Python이 모듈을 찾는 경로에 추가합니다.
# 이렇게 하면 같은 폴더에 있는 다른 .py 파일을 확실하게 import 할 수 있습니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
# --- End of Fix ---

try:
    # 이제 같은 폴더에 있는 모듈을 직접 import 할 수 있습니다.
    # 파일 이름 오타(bianry -> binary)를 수정한 이름으로 import 합니다.
    import sequence_manager_binary as manager
except ImportError as e:
    # 디버깅을 위해 에러 메시지를 터미널에 출력합니다.
    print(f"Failed to import sequence_manager_binary: {e}")
    manager = None

class SequenceTab(QtWidgets.QWidget):
    tab_name = "Sequence"

    def __init__(self, services=None, parent=None):
        super().__init__(parent)
        self.s = services
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)

        self._status = QtWidgets.QLabel("")
        v.addWidget(self._status)

        self._host = None
        self._embed_widget = None
        if manager is None:
            v.addWidget(QtWidgets.QLabel("sequence_manager_binary.py 모듈을 찾을 수 없습니다.\n"
                                          "파일 이름의 오타를 확인하고, 파일이 ui/tabs/ 폴더에 있는지 확인하세요."))
            return
        try:
            self._host = manager.MainWindow()  # QMainWindow
            cw = self._host.centralWidget()
            if cw is None and hasattr(self._host, "_build_ui"):
                self._host._build_ui(); cw = self._host.centralWidget()
            if cw is not None:
                cw.setParent(self); v.addWidget(cw); self._embed_widget = cw; self._host.hide()
            else:
                v.addWidget(QtWidgets.QLabel("sequence_manager 중앙 위젯을 찾을 수 없습니다."))
        except Exception as e:
            v.addWidget(QtWidgets.QLabel(f"sequence_manager 임베드 실패: {e}"))

        # 버스 연결: Synthesis → Sequence 동기화
        if self.s and getattr(self.s, 'bus', None):
            self.s.bus.sequencesSelected.connect(self._on_sequences_selected)

    # 외부(Synthesis 탭)에서 파일 배열을 전달
    def load_sequences_from_external(self, paths):
        loaded = False
        if not paths:
            return False
        try:
            if self._host is not None:
                for cand in ("load_multi_sequences", "load_sequences", "load_files", "open_sequences"):
                    if hasattr(self._host, cand):
                        try:
                            getattr(self._host, cand)(paths)
                            loaded = True
                            break
                        except Exception:
                            pass
        except Exception as e:
             print(f"Error calling external sequence loader: {e}")
        self._status.setText(f"External sequences: {len(paths)} files")
        return loaded

    # 버스 신호 핸들러
    def _on_sequences_selected(self, paths):
        ok = self.load_sequences_from_external(paths)
        if not ok:
            # 최소 보장: 상태 라벨 갱신
            self._status.setText(f"External sequences(미러): {len(paths)} files")

# 단독 실행용
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow(); tab = SequenceTab(None)
    w.setCentralWidget(tab); w.resize(1000, 700); w.setWindowTitle('SequenceTab - Standalone'); w.show()
    sys.exit(app.exec_())

