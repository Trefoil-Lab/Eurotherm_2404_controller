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
LOOP_SLEEP_S = 0.05

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
        self.signals.pausingSig.emit()
        self.pause_event.set()

    def resume(self):
        self.signals.resumingSig.emit()
        self.pause_event.clear()

    def jump(self):
        self.signals.jumpingSig.emit()
        self.jump_event.set()

    ###################################
    # process control thread handlers #
    ###################################

    def receiveState(self, data : Data):
        # receive ramp/hold status, rate, and process value from
        #   process control thread. calculate estimated time remaining
        #   etc and forward to gui
        status = f'{data.segment_index + 1} '
        if data.paused:
            status += 'PAUSED '
        status += f'{data.segment.segment_type.name}'
        match data.segment.segment_type:
            case SegmentType.RAMP:
                rem = abs(data.set_point - data.segment.target) / abs(data.segment.rate)
                status += f' to {data.segment.target} at {data.segment.rate}\N{DEGREE SIGN}C/s, {rem}s remaining'
            case SegmentType.HOLD:
                elapsed = time.monotonic - data.segment.entered
                rem = data.segment.time - elapsed
                status += f' {rem}s remaining'
        
        self.signals.statusSig.emit(
            status, # status string
            data.set_point,
            data.process_value,
            data.paused
        )

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

        self.idx = 0 # segment index

    def schedule_next(self, sc : sched.scheduler):
        match self.segments[self.idx].segment_type:
            case SegmentType.RAMP:
                # we are ramping, so schedule next increment
                sc.enter(RAMP_INTERVAL_S, 1, self.ramp, (sc,))
            case SegmentType.HOLD:
                # we are holding
                self.segments[self.idx].entered = time.monotonic()
                sc.enter(self.segments[self.idx].time, 1, self.hold_end, (sc,))

    def ramp(self, sc : sched.scheduler):
        if (abs(self.segments[self.idx].target - self.eurotherm.active_setpoint)
        <= abs(RAMP_INTERVAL_S * self.segments[self.idx].rate)):
            # we are within one step of the target, so just jump to it
            self.eurotherm.active_setpoint = self.segments[self.idx].target
            # go to next segment
            self.idx += 1
        elif self.segments[self.idx].target > self.eurotherm.active_setpoint:
            # we are below the target, so increase set point
            self.eurotherm.active_setpoint += RAMP_INTERVAL_S * self.segments[self.idx].rate
        elif self.segments[self.idx].target < self.eurotherm.active_setpoint:
            # we are above the target, so decrease set point
            self.eurotherm.active_setpoint -= RAMP_INTERVAL_S * self.segments[self.idx].rate

        self.schedule_next(sc) # schedule next change

    def hold_end(self, sc : sched.scheduler):
        # a hold has ended
        self.idx += 1 # go to next segment
        self.schedule_next(sc) # schedule next change

    def send_data(self):
        # send status information to control thread
            self.process_signals.dataSig.emit(
                Data(
                    self.segments[self.idx],
                    self.idx,
                    self.eurotherm.active_setpoint,
                    self.eurotherm.process_value,
                    self.paused
                )
            )

    def run(self):
        sc = sched.scheduler(time.monotonic, time.sleep)

        self.paused = False

        while not self.stop_event.is_set() and self.segments[self.idx].segment_type != SegmentType.END:
            if self.paused == False:
                # we are not paused, proceed as normal
                sc.run(False) # run any pending actions

            if self.paused == False and self.pause_event.is_set() == True:
                # we have just now entered pause
                self.control_signals.pausedSig.emit() # notify gui that we've paused
                if self.segments[self.idx].segment_type == SegmentType.HOLD:
                    # if we are in a hold, subtract the time we have already held
                    #   from the prescribed hold time
                    elapsed = time.monotonic() - self.segments[self.idx].entered
                    self.segments[self.idx].time -= elapsed

                    # clear everything from the scheduler queue
                    sc.queue.clear()

            elif self.paused == True and self.pause_event.is_set() == False:
                # we have just been unpaused, so schedule the next change
                self.schedule_next(sc)
                self.control_signals.resumedSig.emit()

            self.send_data() # let control thread know what's happening
            time.sleep(LOOP_SLEEP_S)

        # if we are here, we have reached the END segment or received a stop signal
        sc.queue.clear() # clear remaining changes
        self.eurotherm.active_setpoint = 0 # setpoint to below ambient

        # if we weren't stopped, continue sending data
        while not self.stop_event.is_set():
            self.send_data()

        sys.exit() # close thread