# ui/tabs/protocol_tab.py
import os
from PyQt5 import QtWidgets
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class ProtocolTab(QtWidgets.QWidget):
    tab_name = "Protocol"
    def __init__(self, services=None, parent=None):
        super().__init__(parent)
        self.s = services
        v = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["step","volume","incubation time"])
        self.table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.table)
        hb = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("행 추가")
        self.btn_del = QtWidgets.QPushButton("행 삭제")
        self.btn_load = QtWidgets.QPushButton("불러오기…")
        self.btn_save = QtWidgets.QPushButton("저장…")
        hb.addWidget(self.btn_add); hb.addWidget(self.btn_del); hb.addStretch(1); hb.addWidget(self.btn_load); hb.addWidget(self.btn_save)
        v.addLayout(hb)
        self.btn_add.clicked.connect(self._add)
        self.btn_del.clicked.connect(self._del)
        self.btn_load.clicked.connect(self._load)
        self.btn_save.clicked.connect(self._save)
    def _add(self):
        r = self.table.rowCount(); self.table.insertRow(r)
        for c in range(3): self.table.setItem(r, c, QtWidgets.QTableWidgetItem(""))
    def _del(self):
        r = self.table.currentRow()
        if r >= 0: self.table.removeRow(r)
    def _load(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Protocol 불러오기", os.getcwd(), "*.protocol;;All (*.*)")
        if not fn: return
        rows = []
        with open(fn, 'r', encoding='utf-8') as f:
            for line in f:
                p = [x.strip() for x in line.strip().split('\t')]
                if len(p) >= 3: rows.append([p[0], p[1], p[2]])
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j in range(3): self.table.setItem(i, j, QtWidgets.QTableWidgetItem(row[j]))
    def _save(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Protocol 저장", os.path.join(os.getcwd(), "protocol.protocol"), "*.protocol")
        if not fn: return
        if not fn.lower().endswith('.protocol'): fn += '.protocol'
        with open(fn, 'w', encoding='utf-8') as f:
            for i in range(self.table.rowCount()):
                row = [self.table.item(i, j).text() if self.table.item(i, j) else '' for j in range(3)]
                f.write('\t'.join(row) + '\n')

# 단독 실행용
if __name__ == '__main__':
    from PyQt5 import QtWidgets
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow(); tab = ProtocolTab()
    w.setCentralWidget(tab); w.resize(800, 500); w.setWindowTitle('ProtocolTab - Standalone'); w.show()
    sys.exit(app.exec_())