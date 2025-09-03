# core/bus.py
from PyQt5.QtCore import QObject, pyqtSignal

class AppBus(QObject):
    """탭 간 통신을 위한 신호 버스"""
    # Synthesis 탭에서 시퀀스 파일들을 선택했을 때 -> Sequence 탭에 전달
    sequencesSelected = pyqtSignal(list)  # list[str]
    # (필요시) 진행/로그 신호 등 추가 가능