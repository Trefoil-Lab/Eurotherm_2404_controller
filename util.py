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
    entered : float | None # time hold entered, for internal use

@dataclass
class Data:
    time : float
    segment : Segment
    segment_index : int
    set_point : float
    process_value : float
    paused : bool

class GuiSignals(QObject):
    jumpSig = pyqtSignal()
    startSig = pyqtSignal()
    stopSig = pyqtSignal()
    pauseSig = pyqtSignal()
    resumeSig = pyqtSignal()
    connectSig = pyqtSignal(str, int)
    exitSig = pyqtSignal()

class ControlSignals(QObject):
    connectingSig = pyqtSignal()
    connectedSig = pyqtSignal()
    startingSig = pyqtSignal()
    startedSig = pyqtSignal()
    stoppingSig = pyqtSignal()
    stoppedSig = pyqtSignal()
    pausingSig = pyqtSignal()
    pausedSig = pyqtSignal()
    resumingSig = pyqtSignal()
    resumedSig = pyqtSignal()
    jumpingSig = pyqtSignal()
    jumpedSig = pyqtSignal()
    statusSig = pyqtSignal(str, Data)

class ProcessSignals(QObject):
    dataSig = pyqtSignal(Data)