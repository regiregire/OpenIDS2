# core/bus.py
from PyQt5.QtCore import QObject, pyqtSignal

class AppBus(QObject):
    """Signal bus for communication between tabs"""
    # When sequence files are selected in the Synthesis tab -> Pass to the Sequence tab
    sequencesSelected = pyqtSignal(list)  # list[str]
    # (If necessary) Can add progress/log signals, etc.