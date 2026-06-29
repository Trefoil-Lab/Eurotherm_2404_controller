from PyQt6.QtCore import QObject, QRunnable, QEventLoop, pyqtSignal, pyqtSlot
import time
import sched
import random
import math
import sys
import datetime
from threading import Thread, Lock, Event
from queue import SimpleQueue, Empty
from eurotherm2400 import Eurotherm2400
from util import (
    GuiSignals, 
    ControlSignals, 
    ProcessSignals, 
    Status, 
    Segment, 
    SegmentType, 
    Data
)

RAMP_INTERVAL_S = 0.500

class ControlRunner(QRunnable):
    def __init__(
        self,
        gui_signals : GuiSignals,
        control_signals : ControlSignals
    ):
        super().__init__()
        self.signals = control_signals
        self.gui_signals = gui_signals
        self.status = Status()

        # events for communication with process control thread
        self.process_signals = ProcessSignals()
        self.pause_event = Event()
        self.stop_event = Event()
        self.jump_event = Event()

        # connect gui events to handlers
        self.gui_signals.jumpSig.connect(self.jump)
        self.gui_signals.startSig.connect(self.start)
        self.gui_signals.stopSig.connect(self.stop)
        self.gui_signals.pauseSig.connect(self.pause)
        self.gui_signals.resumeSig.connect(self.resume)
        self.gui_signals.connectSig.connect(self.connect)

    def run(self):
        print('Control thread starting.')

        

        self.eventloop = QEventLoop()
        self.eventloop.exec()

    ######################
    # GUI event handlers #
    ######################

    def connect(self, eurotherm_port : str, eurotherm_addr : int,):
        self.signals.connectingSig.emit()
        self.eurotherm = Eurotherm2400(
            eurotherm_port,
            eurotherm_addr,
        )
        self.signals.connectedSig.emit()

    def start(self):
        self.signals.startingSig.emit()

        self.process_thread = ProcessRunner(
            self.eurotherm,
            self.segments,
            self.process_signals,
            self.signals,
            self.stop_event,
            self.pause_event,
            self.jump_event
        )
        self.process_thread.start()

        self.status.running = True
        self.signals.startedSig.emit()

    def stop(self):
        self.signals.stoppingSig.emit()

        self.stop_event.set()
        self.process_thread.join() # wait for process thread to stop

        self.signals.stoppedSig.emit()

    def pause(self):
        self.pause_event.set()

    def resume(self):
        self.pause_event.clear()

    def jump(self):
        self.signals.jumpingSig.emit()
        self.jump_event.set()

    ###################################
    # process control thread handlers #
    ###################################

    def receiveState(self):
        # TODO receive ramp/hold status, rate, and process value from
        #   process control thread. calculate estimated time remaining
        #   etc and forward to gui
        pass

class ProcessRunner(Thread):
    def __init__(self,
        eurotherm : Eurotherm2400,
        segments : list[Segment],
        process_signals : ProcessSignals,
        control_signals : ControlSignals,
        stop_event : Event,
        pause_event : Event,
        jump_event : Event
    ):
        super().__init__()
        
        self.eurotherm = eurotherm
        self.segments = segments
        self.process_signals = process_signals,
        self.control_signals = control_signals
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.jump_event = jump_event
        self.index = 0 # segment index

    def run(self):
        # TODO scheduler

        pause = False

        while not self.stop_event.is_set():
            if self.segments[self.index].segment_type != SegmentType.END:
                pause = self.pause_event.is_set()
                if not pause:
                    # TODO handle scheduling, ramping, holding, etc
                    pass

                if self.jump_event.is_set():
                    self.index += 1
                    self.jump_event.clear()

        # TODO send status information to control thread
        self.process_signals.dataSig.emit()