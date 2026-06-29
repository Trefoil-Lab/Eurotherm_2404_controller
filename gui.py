import sys
from PyQt6.QtCore import QSize, Qt, QThreadPool
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
from util import GuiSignals, ControlSignals
from control import ControlRunner
from MainWindow import Ui_MainWindow
from SegmentDialog import Ui_Dialog as Ui_SegDialog
from SegmentWidget import Ui_Form
from ConnectionDialog import Ui_Dialog as Ui_ConnDialog

WINDOW_TITLE = 'Eurotherm 2404 Controller'
CONNECT_DIALOG_TITLE = 'Connection Details'
SEGMENTS_DIALOG_TITLE = 'Configure Segments'

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

        # signals object
        self.gui_signals = GuiSignals()

        # create control runner
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
        self.control_signals.jumpingSig.connect(self.jumping)
        self.control_signals.jumpedSig.connect(self.jumped)
        self.control_signals.statusSig.connect(self.procStatus) # status updates

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
            self.gui_signals.startSig.emit()

    def segmentsConfigPress(self):
        print('segment config time!')
        dlg = SegmentDialog(self.segmentCountSpinBox.value())
        dlg.exec()

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
        # TODO kill control thread
        return super().closeEvent(event)
    
    ###################
    # signal handlers #
    ###################

    def procStatus(self):
        # TODO receive status updates from control thread
        pass

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

    def started(self):
        self.statusbar.showMessage('Started!', 1000)

    def stopping(self):
        self.statusbar.showMessage('Stopping...')

    def stopped(self):
        self.statusbar.showMessage('Stopped!', 1000)

    def pausing(self):
        self.statusbar.showMessage('Pausing...')

    def paused(self):
        self.statusbar.showMessage('Paused!', 1000)

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
    def __init__(self, count : int):
        super().__init__()
        self.setupUi(self)

        ###############################
        # custom initialization below #
        ###############################

        self.setWindowTitle(SEGMENTS_DIALOG_TITLE)

        segboxes : list[SegmentWidget] = []
        for i in range(count):
            w = SegmentWidget(i+1)
            segboxes.append(w)
            self.scrollAreaWidgetContents.layout().addWidget(w)

    def accept(self):
        # TODO
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
