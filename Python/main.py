# main.py
import sys
from PyQt5 import QtWidgets
from core.bus import AppBus
from core.services import Services
from ui.main_window import MainWindow


def main():
    app = QtWidgets.QApplication(sys.argv)
    bus = AppBus()
    services = Services(bus)
    win = MainWindow(services)
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

