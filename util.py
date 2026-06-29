from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

@dataclass
class Status:
    connected : bool = False
    running : bool = False
    paused : bool = False

class SegmentType(Enum):
    END = 0
    HOLD = 1
    RAMP = 2

@dataclass
class Segment:
    segment_type : SegmentType
    target : float | None # deg C
    rate : float | None # deg C / sec
    time : float | None # hold time

@dataclass
class Data:
    segment_type : SegmentType
    segment_index : int
    set_point : float
    process_value : float
    rate : float | None

class GuiSignals(QObject):
    jumpSig = pyqtSignal()
    startSig = pyqtSignal()
    stopSig = pyqtSignal()
    pauseSig = pyqtSignal()
    resumeSig = pyqtSignal()
    connectSig = pyqtSignal(str, int)
    exitSign = pyqtSignal()

class ControlSignals(QObject):
    connectingSig = pyqtSignal()
    connectedSig = pyqtSignal()
    startingSig = pyqtSignal()
    startedSig = pyqtSignal()
    stoppingSig = pyqtSignal()
    stoppedSig = pyqtSignal()
    jumpingSig = pyqtSignal()
    jumpedSig = pyqtSignal()
    statusSig = pyqtSignal(float, int, Data)

class ProcessSignals(QObject):
    dataSig = pyqtSignal(Data)