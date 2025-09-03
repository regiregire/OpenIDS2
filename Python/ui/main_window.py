# ui/main_window.py
from PyQt5 import QtWidgets
from ui.tabs.synthesis_tab import SynthesisTab
from ui.tabs.manual_tab import ManualTab
from ui.tabs.sequence_tab import SequenceTab
from ui.tabs.protocol_tab import ProtocolTab

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, services):
        super().__init__()
        self.s = services
        self.setWindowTitle("OpenIDS GUI v2")
        self.resize(1400, 900)
        self.tabs = QtWidgets.QTabWidget(); self.setCentralWidget(self.tabs)
        self._add_tabs()
    def _add_tabs(self):
        self._tab_seq = SequenceTab(self.s, self)
        self._tab_synth = SynthesisTab(self.s, self)
        self._tab_manual = ManualTab(self.s, self)
        self._tab_protocol = ProtocolTab(self.s, self)
        self.tabs.addTab(self._tab_synth, getattr(self._tab_synth, 'tab_name', 'Synthesis'))
        self.tabs.addTab(self._tab_manual, getattr(self._tab_manual, 'tab_name', 'Manual'))
        self.tabs.addTab(self._tab_seq, getattr(self._tab_seq, 'tab_name', 'Sequence'))
        self.tabs.addTab(self._tab_protocol, getattr(self._tab_protocol, 'tab_name', 'Protocol'))
