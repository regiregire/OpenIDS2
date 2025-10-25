# ui/tabs/sequence_tab.py
import os
import sys
from PyQt5 import QtWidgets

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
# --- End of Fix ---

try:

    import sequence_manager as manager
except ImportError as e:
    # Prints the error message to the terminal for debugging.
    print(f"Failed to import sequence_manager: {e}")
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
            v.addWidget(QtWidgets.QLabel("Could not find the sequence_manager_binary.py module.\n"
                                          "Check for typos in the filename and make sure the file is in the ui/tabs/ folder."))
            return
        try:
            self._host = manager.MainWindow()  # QMainWindow
            cw = self._host.centralWidget()
            if cw is None and hasattr(self._host, "_build_ui"):
                self._host._build_ui(); cw = self._host.centralWidget()
            if cw is not None:
                cw.setParent(self); v.addWidget(cw); self._embed_widget = cw; self._host.hide()
            else:
                v.addWidget(QtWidgets.QLabel("Could not find the sequence_manager central widget."))
        except Exception as e:
            v.addWidget(QtWidgets.QLabel(f"Failed to embed sequence_manager: {e}"))

        # Bus connection: Synthesis → Sequence synchronization
        if self.s and getattr(self.s, 'bus', None):
            self.s.bus.sequencesSelected.connect(self._on_sequences_selected)

    # Pass file array from external (Synthesis tab)
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

    # Bus signal handler
    def _on_sequences_selected(self, paths):
        ok = self.load_sequences_from_external(paths)
        if not ok:
            # Minimum guarantee: Update status label
            self._status.setText(f"External sequences(mirror): {len(paths)} files")

# For standalone execution
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow(); tab = SequenceTab(None)
    w.setCentralWidget(tab); w.resize(1000, 700); w.setWindowTitle('SequenceTab - Standalone'); w.show()
    sys.exit(app.exec_())