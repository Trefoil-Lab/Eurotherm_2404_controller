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
from util import GuiSignals, ControlSignals

RAMP_INTERVAL_S = 0.200

class ControlRunner(QRunnable):
    def __init__(
        self,
        eurotherm_port : str,
        eurotherm_addr : int,
        gui_signals : GuiSignals,
    ):
        super().__init__()
        self.signals = ControlSignals()
        self.gui_signals = gui_signals
        self.eurotherm_port = eurotherm_port
        self.eurotherm_addr = eurotherm_addr

    def run(self):
        print('Control thread starting.')

        

        self.eventloop = QEventLoop()
        self.eventloop.exec()

    ######################
    # GUI event handlers #
    ######################

    def connect(self):
        self.signals.connectingSig.emit()
        self.eurotherm = Eurotherm2400(
            self.eurotherm_port,
            self.eurotherm_addr,
        )
        self.signals.connectedSig.emit()

    def start(self):
        # TODO
        pass

    def stop(self):
        # TODO
        pass

    def pause(self):
        # TODO
        pass

    def resume(self):
        # TODO
        pass

    def jump(self):
        # TODO
        pass

    def fire(self):
        # TODO
        pass

    ###################################
    # process control thread handlers #
    ###################################

    def receiveState(self):
        # TODO receive ramp/hold status, rate, and process value from
        #   process control thread. calculate estimated time remaining
        #   etc and forward to gui
        pass

class ProcessRunner(Thread):
    def __init__(self):
        super().__init__()
        # TODO

    def run(self):
        # TODO
        pass