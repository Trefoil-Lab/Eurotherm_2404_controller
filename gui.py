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

    #######################
    # user input handlers #
    #######################

    def startStopPress(self):
        # TODO
        print('start/stop pressed!')

    def segmentsConfigPress(self):
        print('segment config time!')
        dlg = SegmentDialog(self.segmentCountSpinBox.value())
        dlg.exec()

    def firePress(self):
        # TODO
        print('fire press!')

    def jumpPress(self):
        # TODO
        print('jump pressed!')

    def pauseResumePress(self):
        # TODO
        print('pause/resume pressed!')

    def closeEvent(self, event):
        print('exiting...')
        # TODO kill control thread
        return super().closeEvent(event)
    
    ###################
    # signal handlers #
    ###################

class ConnectionDialog(QDialog, Ui_ConnDialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        ###############################
        # custom initialization below #
        ###############################

        self.setWindowTitle(CONNECT_DIALOG_TITLE)

    def accept(self):
        # TODO
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
