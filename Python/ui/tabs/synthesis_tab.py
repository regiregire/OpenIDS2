# ui/tabs/synthesis_tab.py
import os, time
from pathlib import Path
from PyQt5 import QtWidgets, QtCore


class SynthesisTab(QtWidgets.QWidget):
    tab_name = "Synthesis"

    def __init__(self, services=None, parent=None):
        super().__init__(parent)
        self.s = services
        self._build_ui()
        self._connect()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        g = QtWidgets.QGroupBox("Synthesis");
        gl = QtWidgets.QGridLayout(g)
        self.lbl_seq = QtWidgets.QLabel("Sequence: -")
        self.btn_seq_load = QtWidgets.QPushButton("Load Sequence Folder…")
        self.btn_run = QtWidgets.QPushButton("Run");
        self.btn_run.setEnabled(False)
        gl.addWidget(self.lbl_seq, 0, 0, 1, 3);
        gl.addWidget(self.btn_seq_load, 0, 3);
        gl.addWidget(self.btn_run, 0, 4)
        self.table = QtWidgets.QTableWidget(0, 3);
        self.table.setHorizontalHeaderLabels(["Step", "Volume", "Incubation Time"]);
        self.table.horizontalHeader().setStretchLastSection(True);
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.btn_protocol_load = QtWidgets.QPushButton("Load Protocol…");
        self.lbl_protocol_name = QtWidgets.QLabel("Protocol: -")
        gl.addWidget(self.btn_protocol_load, 1, 0);
        gl.addWidget(self.lbl_protocol_name, 1, 1, 1, 4);
        gl.addWidget(self.table, 2, 0, 1, 5)
        st = QtWidgets.QHBoxLayout();
        self.lbl_cycle = QtWidgets.QLabel("Cycle: -");
        self.lbl_total_cycles = QtWidgets.QLabel("Total Cycles: -")
        self.lbl_step = QtWidgets.QLabel("Step: -");
        st.addWidget(self.lbl_cycle);
        st.addWidget(self.lbl_total_cycles);
        st.addWidget(self.lbl_step);
        st.addStretch(1);
        gl.addLayout(st, 3, 0, 1, 5)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)
        self.btn_pause = QtWidgets.QPushButton("Pause")
        self.btn_pause.setEnabled(False)
        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        button_layout.addWidget(self.btn_pause)
        button_layout.addWidget(self.btn_stop)
        gl.addLayout(button_layout, 4, 0, 1, 5)

        self.log = QtWidgets.QPlainTextEdit();
        self.log.setReadOnly(True)
        root.addWidget(g, 1);
        root.addWidget(self.log, 1)

    def _connect(self):
        self.btn_seq_load.clicked.connect(self._on_load_sequence)
        self.btn_protocol_load.clicked.connect(self._on_load_protocol)
        self.btn_run.clicked.connect(self._on_run)
        self.btn_pause.clicked.connect(self._on_pause_resume)
        self.btn_stop.clicked.connect(self._on_stop)

        if self.s:
            manager = self.s.synthesis_manager
            manager.status_updated.connect(self._on_status_update)
            manager.synthesis_finished.connect(self._on_synthesis_finished)
            manager.log_message.connect(self._append_log)

    def _append_log(self, message: str):
        timestamp = time.strftime('%H:%M:%S')
        self.log.appendPlainText(f"[{timestamp}] {message}")

    def _on_load_sequence(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Sequence Folder", ".")
        if not folder_path: return

        if self.s and hasattr(self.s, 'load_sequence_directory'):
            try:
                total_cycles = self.s.load_sequence_directory(folder_path)
                self.s.synthesis_manager.set_total_cycles(total_cycles)
                self.lbl_seq.setText(f"Sequence: {os.path.basename(folder_path)}")
                self.lbl_total_cycles.setText(f"Total Cycles: {total_cycles}")
                self._append_log(f"Sequence folder loaded: {folder_path} ({total_cycles} cycles found).")
            except Exception as e:
                self._append_log(f"[ERR] Failed to load sequence folder: {e}")
        else:
            self._append_log("[WARN] Service for sequence loading not available.")

    def _on_load_protocol(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Protocol File", ".", "*.protocol;;All Files (*)")
        if not fn: return

        if self.s and hasattr(self.s, 'load_protocol'):
            try:
                protocol = self.s.load_protocol(fn)
                self.s.synthesis_manager.set_protocol(protocol)

                self.table.setRowCount(len(protocol))
                for i, row_data in enumerate(protocol):
                    for j, item_data in enumerate(row_data):
                        self.table.setItem(i, j, QtWidgets.QTableWidgetItem(str(item_data)))

                self.lbl_protocol_name.setText(f"Protocol: {os.path.basename(fn)}")
                self.btn_run.setEnabled(True)
                self._append_log(f"Protocol loaded: {fn}")
            except Exception as e:
                self._append_log(f"[ERR] Failed to load protocol: {e}")
        else:
            self._append_log("[WARN] Service for protocol loading not available.")

    def _on_run(self):
        if self.s:
            self.s.synthesis_manager.start_synthesis()
            self.btn_run.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.btn_pause.setEnabled(True)
            self.btn_pause.setText("Pause")

    def _on_pause_resume(self):
        if self.s:
            is_paused = self.s.synthesis_manager.toggle_pause_resume()
            self.btn_pause.setText("Resume" if is_paused else "Pause")

    def _on_stop(self):
        if self.s:
            self.s.synthesis_manager.stop_synthesis()
            self.btn_run.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.btn_pause.setText("Pause")

    @QtCore.pyqtSlot(int, str)
    def _on_status_update(self, cycle: int, step: str):
        total = self.s.synthesis_manager._total_cycles if self.s else 0
        self.lbl_cycle.setText(f"Cycle: {cycle}/{total}")
        self.lbl_step.setText(f"Step: {step}")

    def _on_synthesis_finished(self):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("Pause")
        self.lbl_cycle.setText("Cycle: -")
        self.lbl_step.setText("Step: -")
        self.lbl_total_cycles.setText("Total Cycles: -")


# 단독 실행용
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()
    tab = SynthesisTab(None)
    w.setCentralWidget(tab)
    w.resize(1100, 750)
    w.setWindowTitle('SynthesisTab - Standalone')
    w.show()
    sys.exit(app.exec_())

