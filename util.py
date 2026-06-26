from dataclasses import dataclass
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

@dataclass
class Status:
    connected : bool = False
    running : bool = False

class GuiSignals(QObject):
    jumpSig = pyqtSignal()
    fireSig = pyqtSignal()
    pauseSig = pyqtSignal()
    resumeSig = pyqtSignal()
    connectSig = pyqtSignal()
    disconnectSig = pyqtSignal()

class ControlSignals(QObject):
    connectingSig = pyqtSignal()
    connectedSig = pyqtSignal()
    startingSig = pyqtSignal()
    startedSig = pyqtSignal()
    statusSig = pyqtSignal()