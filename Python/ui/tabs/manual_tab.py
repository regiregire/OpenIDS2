from PyQt5 import QtWidgets
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class ManualTab(QtWidgets.QWidget):
    tab_name = "Manual"

    def __init__(self, services=None, parent=None):
        super().__init__(parent)
        self.s = services
        self._build_ui()
        self._connect()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        g = QtWidgets.QGroupBox("Manual Controls")
        v = QtWidgets.QVBoxLayout(g)

        h_pos = QtWidgets.QHBoxLayout()
        self.ed = QtWidgets.QLineEdit()
        self.ed.setPlaceholderText("Distance (mm/step)")
        h_pos.addWidget(QtWidgets.QLabel("Position:"))
        h_pos.addWidget(self.ed)

        h_buttons = QtWidgets.QHBoxLayout()
        self.btn_move = QtWidgets.QPushButton("Move")
        self.btn_init = QtWidgets.QPushButton("Linear Init")
        h_buttons.addStretch(1)  # Align buttons to the right
        h_buttons.addWidget(self.btn_move)
        h_buttons.addWidget(self.btn_init)

        # Process
        grid = QtWidgets.QGridLayout()
        self.btn_wash = QtWidgets.QPushButton("Wash");
        self.btn_deblock = QtWidgets.QPushButton("Detritylation");
        self.btn_oxid = QtWidgets.QPushButton("Oxidation")
        self.btn_blow = QtWidgets.QPushButton("Blow");
        self.btn_sblow = QtWidgets.QPushButton("SBlow");
        self.btn_waste = QtWidgets.QPushButton("Waste");
        self.btn_print = QtWidgets.QPushButton("Print(Test)")
        grid.addWidget(self.btn_wash, 0, 0);
        grid.addWidget(self.btn_deblock, 0, 1);
        grid.addWidget(self.btn_oxid, 0, 2);
        grid.addWidget(self.btn_blow, 1, 0);
        grid.addWidget(self.btn_sblow, 1, 1);
        grid.addWidget(self.btn_waste, 1, 2);
        grid.addWidget(self.btn_print, 0, 3)

        # Ink
        grid_ink = QtWidgets.QGridLayout()
        self.btn_act_p = QtWidgets.QPushButton("ACT +");
        self.btn_a_p = QtWidgets.QPushButton("A +");
        self.btn_t_p = QtWidgets.QPushButton("T +");
        self.btn_g_p = QtWidgets.QPushButton("G +");
        self.btn_c_p = QtWidgets.QPushButton("C +")
        self.btn_act_m = QtWidgets.QPushButton("ACT −");
        self.btn_a_m = QtWidgets.QPushButton("A −");
        self.btn_t_m = QtWidgets.QPushButton("T −");
        self.btn_g_m = QtWidgets.QPushButton("G −");
        self.btn_c_m = QtWidgets.QPushButton("C −")
        self.btn_ink_stop = QtWidgets.QPushButton("INK STOP")
        for i, w in enumerate(
            [self.btn_act_p, self.btn_a_p, self.btn_t_p, self.btn_g_p, self.btn_c_p]): grid_ink.addWidget(w, 0, i)
        for i, w in enumerate(
            [self.btn_act_m, self.btn_a_m, self.btn_t_m, self.btn_g_m, self.btn_c_m]): grid_ink.addWidget(w, 1, i)
        grid_ink.addWidget(self.btn_ink_stop, 2, 0, 1, 5)

        v.addLayout(h_pos)
        v.addLayout(h_buttons)

        v.addLayout(grid)
        v.addLayout(grid_ink)
        root.addWidget(g)

    def _on_move(self):
        """Reads the value from the input field (ed) and sends the `linear_move_` command."""
        value = self.ed.text().strip()
        if value:  # Send only if there is an input value
            command = f"linear_move_{value};"
            self._send_command(command)


    def _connect(self):
        self.btn_move.clicked.connect(self._on_move)
        self.ed.returnPressed.connect(self._on_move)

        self.btn_init.clicked.connect(lambda: self._send_command("linear_init;"))



        self.btn_wash.clicked.connect(lambda: self._send_command("bulk_wash_200;"))
        self.btn_deblock.clicked.connect(lambda: self._send_command("bulk_detritylation_200;"))
        self.btn_oxid.clicked.connect(lambda: self._send_command("bulk_oxidation_200;"))
        self.btn_blow.clicked.connect(lambda: self._send_command("blow;"))
        self.btn_sblow.clicked.connect(lambda: self._send_command("Sblow;"))
        self.btn_waste.clicked.connect(lambda: self._send_command("Lwaste;"))
        self.btn_print.clicked.connect(lambda: self._send_command("printing_Test;"))
        self.btn_act_p.clicked.connect(lambda: self._send_command("ink_act+;"))
        self.btn_a_p.clicked.connect(lambda: self._send_command("ink_A+;"))
        self.btn_t_p.clicked.connect(lambda: self._send_command("ink_T+;"))
        self.btn_g_p.clicked.connect(lambda: self._send_command("ink_G+;"))
        self.btn_c_p.clicked.connect(lambda: self._send_command("ink_C+;"))
        self.btn_act_m.clicked.connect(lambda: self._send_command("ink_act-;"))
        self.btn_a_m.clicked.connect(lambda: self._send_command("ink_A-;"))
        self.btn_t_m.clicked.connect(lambda: self._send_command("ink_T-;"))
        self.btn_g_m.clicked.connect(lambda: self._send_command("ink_G-;"))
        self.btn_c_m.clicked.connect(lambda: self._send_command("ink_C-;"))
        self.btn_ink_stop.clicked.connect(lambda: self._send_command("ink_stop;"))

    def _send_command(self, cmd) -> None:
        try:
            if self.s and getattr(self.s, 'arduino', None):
                self.s.arduino.send(cmd)
        except Exception as e:
            print('[ERR] send command to arduino :', e)


# For standalone execution
if __name__ == '__main__':
    from PyQt5 import QtWidgets
    import sys
    from core.bus import AppBus
    from core.services import Services

    app = QtWidgets.QApplication(sys.argv)
    bus = AppBus()
    services = Services(bus)
    w = QtWidgets.QMainWindow()
    tab = ManualTab(services)
    w.setCentralWidget(tab)
    w.resize(900, 600)
    w.setWindowTitle('ManualTab - Standalone')
    w.show()
    sys.exit(app.exec_())