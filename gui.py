import sys
from PyQt6 import QtCore
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QWidget,
    QFileDialog,
    QLabel,
    QPushButton,
    QMessageBox,
    QSpacerItem,
    QSizePolicy
)
from PyQt6 import QtGui
import pyqtgraph as pg
import numpy as np
from util import GuiSignals, ControlSignals, SegmentType, Segment, Data
from control import ControlRunner
from MainWindow import Ui_MainWindow
from SegmentDialog import Ui_Dialog as Ui_SegDialog
from SegmentWidget import Ui_Form
from ConnectionDialog import Ui_Dialog as Ui_ConnDialog

WINDOW_TITLE = 'Eurotherm 2404 Controller'
CONNECT_DIALOG_TITLE = 'Connection Details'
SEGMENTS_DIALOG_TITLE = 'Configure Segments'

SET_POINT_COLOR_STR = '#FF0000'
PROCESS_VALUE_COLOR_STR = '#00FFFF'

def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        ###############################
        # custom initialization below #
        ###############################

        self.setWindowTitle(WINDOW_TITLE)

        self.setPointGroupBox.setStyleSheet(f'QGroupBox {{color: {SET_POINT_COLOR_STR}}}')
        self.processValueGroupBox.setStyleSheet(f'QGroupBox {{color: {PROCESS_VALUE_COLOR_STR}}}')

        # data
        self.segPlotItem = None
        self.pvPlotItem = None
        self.spPlotItem = None
        self.segments = [Segment(SegmentType.END, None, None, None, None)]
        self.time = []
        self.sp = [] # set points for plotting
        self.pv = [] # process values for plotting

        # signals object
        self.gui_signals = GuiSignals()

        # create control runner
        self.thread_pool = QtCore.QThreadPool()
        self.control_signals = ControlSignals()
        self.control = ControlRunner(self.gui_signals, self.control_signals)

        # set up graph
        self.graph = pg.PlotWidget()
        self.graph.setSizePolicy(self.graphPlaceholder.sizePolicy())
        self.graph.setMinimumSize(self.graphPlaceholder.minimumSize())
        self.graph.setObjectName('graph')
        self.operationBox.replaceWidget(self.graphPlaceholder, self.graph)
        self.graphPlaceholder.hide()

        self.graph.setBackground(background=None)
        self.graph.setLabel('left', 'Temperature (°C)')
        self.graph.setLabel('bottom', 'Time (s)')
        self.graph.setLimits(xMin=0, yMin=-10)

        # connect buttons to handlers
        self.segmentConfigButton.pressed.connect(self.segmentsConfigPress)
        self.connectionPushButton.pressed.connect(self.connectPress)
        self.startStopPushButton.pressed.connect(self.startStopPress)
        self.jumpPushButton.pressed.connect(self.jumpPress)
        self.pauseContinuePushButton.pressed.connect(self.pauseResumePress)

        # connect signals from control thread to handlers
        self.control_signals.connectingSig.connect(self.connecting)
        self.control_signals.connectedSig.connect(self.connected)
        self.control_signals.startingSig.connect(self.starting)
        self.control_signals.startedSig.connect(self.started)
        self.control_signals.stoppingSig.connect(self.stopping)
        self.control_signals.stoppedSig.connect(self.stopped)
        self.control_signals.pausingSig.connect(self.pausing)
        self.control_signals.pausedSig.connect(self.paused)
        self.control_signals.resumingSig.connect(self.resuming)
        self.control_signals.resumedSig.connect(self.resumed)
        self.control_signals.jumpingSig.connect(self.jumping)
        self.control_signals.jumpedSig.connect(self.jumped)
        self.control_signals.statusSig.connect(self.procStatus) # status updates

        # start control thread
        self.thread_pool.start(self.control)

    ####################
    # helper functions #
    ####################

    def graph_segments(self, start_idx : int, last_time : float | None = None, last_sp : float | None = None):
        x = []
        y = []

        if last_time == None:
            x.append(0)
        else:
            x.append(last_time)
        
        if last_sp != None:
            y.append(last_sp)
        elif self.control.status.connected:
            y.append(self.control.eurotherm.process_value)
        else:
            y.append(0)
        
        for i in range(start_idx, len(self.segments)):
            seg = self.segments[i]
            match seg.segment_type:
                case SegmentType.RAMP:
                    y.append(seg.target)
                    dur = abs(seg.target - y[i]) / seg.rate
                    x.append(x[i] + dur)
                case SegmentType.HOLD:
                    y.append(y[i])
                    x.append(x[i] + seg.time)

        # remove existing segments graph if it exists
        if self.segPlotItem != None:
            self.graph.getPlotItem().removeItem(self.segPlotItem)
        # plot the preview
        self.segPlotItem =  self.graph.plot(x, y, pen=pg.mkPen(color='r', style=QtCore.Qt.PenStyle.DashLine))
    
    #######################
    # user input handlers #
    #######################

    def connectPress(self):
        dlg = ConnectionDialog(self, self.gui_signals)
        dlg.exec()

    def startStopPress(self):
        self.startStopPushButton.setDisabled(True)
        if self.control.status.running == True:
            self.gui_signals.pauseSig.emit()
        else:
            self.control.segments = self.segments
            self.gui_signals.startSig.emit()

    def segmentsConfigPress(self):
        print('segment config time!')
        dlg = SegmentDialog(self.segmentCountSpinBox.value(), self)
        dlg.exec()

        # graph segments preview
        self.graph_segments(0)

    def jumpPress(self):
        self.jumpPushButton.setDisabled(True) # prevent multiple presses
        self.gui_signals.jumpSig.emit()

    def pauseResumePress(self):
        if self.control.status.paused == True:
            self.gui_signals.pauseSig.emit()
        else:
            self.gui_signals.resumeSig.emit()

    def closeEvent(self, event):
        print('exiting...')
        print('stopping process...')
        self.gui_signals.stopSig.emit()
        print('killing control thread...')
        self.gui_signals.exitSig.emit()
        return super().closeEvent(event)
    
    ###################
    # signal handlers #
    ###################

    def procStatus(self, status : str, data : Data):
        # receive status updates from control thread, display on status bar
        self.statusbar.showMessage(status)

        # update numerical display
        self.setPointLcdNumber.display(data.set_point)
        self.processValueLcdNumber.display(data.process_value)

        # graph process values / set points
        self.time.append(data.time)
        self.sp.append(data.set_point)
        self.pv.append(data.process_value)

        # remove existing graphs if they exist
        if self.pvPlotItem != None:
            self.graph.getPlotItem().removeItem(self.pvPlotItem)
        if self.spPlotItem != None:
            self.graph.getPlotItem().removeItem(self.spPlotItem)

        # plot new data graphs
        self.graph.plot(self.time, self.sp, pen=pg.mkPen(color=SET_POINT_COLOR_STR))
        self.graph.plot(self.time, self.pv, pen=pg.mkPen(color=PROCESS_VALUE_COLOR_STR))

        # update segments preview
        self.segments[data.segment_index] = data.segment # in case timing changed from pause
        self.graph_segments(data.segment_index, data.time, data.set_point)

    def jumping(self):
        self.statusbar.showMessage('Jumping...')

    def jumped(self):
        self.statusbar.showMessage('Jumped!', 1000)
        self.jumpPushButton.setDisabled(False)

    def connecting(self):
        self.statusbar.showMessage('Connecting...')

    def connected(self):
        self.statusbar.showMessage('Connected!', 1000)

    def starting(self):
        self.statusbar.showMessage('Starting...')
        self.segmentConfigButton.setDisabled(True)

    def started(self):
        self.statusbar.showMessage('Started!', 1000)
        self.setPointGroupBox.setDisabled(False)
        self.setPointLcdNumber.setDisabled(False)
        self.processValueGroupBox.setDisabled(False)
        self.processValueLcdNumber.setDisabled(False)

    def stopping(self):
        self.statusbar.showMessage('Stopping...')

    def stopped(self):
        self.statusbar.showMessage('Stopped!', 1000)
        self.segmentConfigButton.setDisabled(False)
        self.setPointGroupBox.setDisabled(True)
        self.setPointLcdNumber.setDisabled(True)
        self.processValueGroupBox.setDisabled(True)
        self.processValueLcdNumber.setDisabled(True)

    def pausing(self):
        self.statusbar.showMessage('Pausing...')

    def paused(self):
        self.statusbar.showMessage('Paused!', 1000)

    def resuming(self):
        self.statusbar.showMessage('Resuming...')

    def resumed(self):
        self.statusbar.showMessage('Resumed!', 1000)

class ConnectionDialog(QDialog, Ui_ConnDialog):
    def __init__(self, main_window : MainWindow, gui_signals : GuiSignals):
        super().__init__()
        self.setupUi(self)

        ###############################
        # custom initialization below #
        ###############################

        self.main_window = main_window
        self.gui_signals = gui_signals

        self.setWindowTitle(CONNECT_DIALOG_TITLE)

    def accept(self):
        self.main_window.connectionPushButton.setDisabled(True)
        self.gui_signals.connectSig.emit(
            self.portLineEdit.text(),
            self.addressSpinBox.value()
        )
        return super().accept()

class SegmentDialog(QDialog, Ui_SegDialog):
    def __init__(self, count : int, main_window : MainWindow):
        super().__init__()
        self.setupUi(self)

        ###############################
        # custom initialization below #
        ###############################

        self.setWindowTitle(SEGMENTS_DIALOG_TITLE)

        self.main_window = main_window
        self.segboxes : list[SegmentWidget] = []
        for i in range(count):
            w = SegmentWidget(i+1)
            self.segboxes.append(w)
            self.scrollAreaWidgetContents.layout().addWidget(w)

    def accept(self):
        segments = []
        for seg in self.segboxes:
            seg_type = SegmentType.HOLD
            if seg.rampRadioButton.isChecked():
                seg_type = SegmentType.RAMP

            segments.append(
                Segment(
                    seg_type, # type
                    seg.targetDoubleSpinBox.value(), # target value
                    seg.rateDoubleSpinBox.value(), # ramp rate
                    seg.timeDoubleSpinBox.value(), # hold time
                    None # entered (used internally in process control)
                )
            )

        # last item of segments list is end segment
        segments.append(Segment(SegmentType.END, None, None, None, None))

        self.main_window.segments = segments
        if self.main_window.control.status.connected:
            self.main_window.startStopPushButton.setDisabled(False)

        return super().accept()

class SegmentWidget(Ui_Form, QWidget):
    def __init__(self, num : int):
        super().__init__()
        self.setupUi(self)

        ###############################
        # custom initialization below #
        ###############################

        self.segBox.setTitle(f'Segment {num}')
        self.mode = 'hold'

        # connect button press listeners
        self.rampRadioButton.pressed.connect(self.rampSelect)
        self.holdRadioButton.pressed.connect(self.holdSelect)

    ########################
    # user input listeners #
    ########################

    def rampSelect(self):
        self.mode = 'ramp'
        # disable options for hold
        self.timeDoubleSpinBox.setDisabled(True)
        self.timeLabel.setDisabled(True)
        # enable options for ramp
        self.targetDoubleSpinBox.setDisabled(False)
        self.targetLabel.setDisabled(False)
        self.rateDoubleSpinBox.setDisabled(False)
        self.rateLabel.setDisabled(False)

    def holdSelect(self):
        self.mode = 'hold'
        # disable options for ramp
        self.targetDoubleSpinBox.setDisabled(True)
        self.targetLabel.setDisabled(True)
        self.rateDoubleSpinBox.setDisabled(True)
        self.rateLabel.setDisabled(True)
        # enable options for hold
        self.timeDoubleSpinBox.setDisabled(False)
        self.timeLabel.setDisabled(False)


if __name__ == "__main__":
    main()
