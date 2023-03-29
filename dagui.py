import os
import json
import numpy as np
import select
import datetime
from uuid import uuid4

import pyqtgraph as pg
from PyQt5 import QtGui, QtCore, QtWidgets

from helpers.my_bluetooth import *
from helpers.my_data_processing import *

class DAGUI:
    def __init__(self, parser) -> None:
        self.address = ''
        self.socket = None
        self.pause = False

        self.folderName = None
        self.isRecording = False
        self.recordingStartIndex = 0
        self.recordingStartTime = None
        self.recordingEndIndex = 0
        self.recordingEndTime = None

        self.numSecLong = 20
        self.numSecShort = 5

        self.parser = parser
        self.update_speed_ms = 40
        self.sf = 512
        self.maxFrequency = 45

        self.app = QtGui.QApplication([])
        self.mainWindow: QtGui.QWidget = QtGui.QWidget()
        self.mainWindow.setWindowIcon(QtGui.QIcon('images/brain.png'))
        self.mainWindow.setWindowTitle('DAGUI')
        
        self.message = QtWidgets.QLabel("Connect a device.")
        self.message.setStyleSheet("color : white")

        self.win1: pg.GraphicsLayoutWidget  = pg.GraphicsLayoutWidget()
        self.win2: pg.GraphicsLayoutWidget  = pg.GraphicsLayoutWidget()
        self.win3: pg.GraphicsLayoutWidget  = pg.GraphicsLayoutWidget()

        self._init_styles()
        self._init_timeseries()
        self._init_layout()
        
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(self.update_speed_ms)

        self.app.exec_()
    
    def _init_styles(self):
        self.app.setStyle("Fusion")
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.GlobalColor.black)
        palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.Text, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.GlobalColor.white)
        palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.GlobalColor.red)
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.GlobalColor.black)
        self.app.setPalette(palette)

    def _init_timeseries(self):
        self.plots = list()
        self.curves = list()

        #---------
        # Set plots' characteristics
        self.win1.ci.setContentsMargins(2,2,2,2)
        self.win1.ci.setBorder(color=(100, 100, 100), width=2)

        self.win2.ci.setContentsMargins(0,0,2,2)
        self.win2.ci.setSpacing(0)
        self.win2.ci.setBorder(color=(220, 220, 220), width=0.5)
        #---------
        # Long Plot
        labels = [(i,f'{"       " if i==0 else ""}{round((-self.numSecLong*self.sf + i)/self.sf,2)}s{"       " if i==self.numSecLong*self.sf else ""}') 
                  for i in range(0,self.numSecLong*self.sf+1, self.numSecLong*self.sf//16)]
        
        p = self.win1.addPlot()
        
        p.setContentsMargins(0,10,0,10)
        p.setTitle(f'Raw Data {self.numSecLong}s')
        
        p.disableAutoRange()
        p.showAxis('left', False)
        p.setMenuEnabled('left', False)
        
        p.setLimits(xMin = 0, xMax = self.numSecLong*self.sf)
        p.setRange(xRange = (0, self.numSecLong*self.sf), yRange = (-3000, 3000), padding = 0.0)
        
        p.setMenuEnabled('bottom', False)
        p.setMouseEnabled(False, False)

        ax=p.getAxis('bottom')
        ax.setTicks([labels])

        curve = p.plot(name = 'Raw Data')
        self.plots.append(p)
        self.curves.append(curve)
        
        #----------
        # Short Plot
        # labels = [(i, f'{"       " if i==0 else ""}{round((-self.numSecShort*self.sf + i)/self.sf,2)}s{"        " if i==self.numSecShort*self.sf else ""}') 
        #           for i in range(0,self.numSecShort*self.sf+1, self.numSecShort*self.sf//8)]
        
        p = self.win2.addPlot(row = 0, col = 0)
        
        p.setContentsMargins(0,16,0,16)

        p.disableAutoRange()
        p.setMouseEnabled(False, False)
        p.setMenuEnabled('left', False)
        p.setMenuEnabled('bottom', False)
        p.showAxis('left', False)
        p.showAxis('bottom', False)

        p.setRange(xRange = (0, self.numSecShort*self.sf), yRange = (-2000, 2000), padding = 0)
        p.addLegend(horSpacing = 30)
        
        # ax=p.getAxis('bottom')
        # ax.setTicks([labels])
        
        curve = p.plot(name = f'Raw Data')
        self.plots.append(p)
        self.curves.append(curve)

        #-----------
        # Filtered data
        labels = [(i, f'{"       " if i==0 else ""}{round((-self.numSecShort*self.sf + i)/self.sf,2)}s{"        " if i==self.numSecShort*self.sf else ""}') 
                  for i in range(0,self.numSecShort*self.sf+1, self.numSecShort*self.sf//8)]

        p = self.win2.addPlot(row = 1, col = 0)
        
        p.setContentsMargins(0,0,0,12)
        
        p.disableAutoRange()
        p.setMouseEnabled(False, False)
        p.setMenuEnabled('left', False)
        p.setMenuEnabled('bottom', False)
        p.showAxis('left', False)

        p.setRange(xRange = (0, self.numSecShort*self.sf), yRange = (-2000, 2000), padding = 0)
        p.addLegend(horSpacing = 30)
        
        ax=p.getAxis('bottom')
        ax.setTicks([labels])
        
        curve = p.plot(name = f'Filtered Data')
        self.plots.append(p)
        self.curves.append(curve)
        #-----------
        # Power Spectrum
        p = self.win2.addPlot(row = 2, col = 0)

        p.setTitle(f'Power Spectrum 1Hz - {self.maxFrequency}Hz')
        p.setContentsMargins(0,12,0,12)

        p.disableAutoRange()
        p.setMouseEnabled(False, False)
        p.setMenuEnabled('left', False)
        p.setMenuEnabled('bottom', False)
        p.showAxis('left', False)

        p.setXRange(1, self.maxFrequency, padding = 0)
        p.setYRange(0,1000)
        
        curve = p.plot()
        self.plots.append(p)
        self.curves.append(curve)
        #-------
        # Power Bands       
        self.powerBarItem, self.powerBarPlot = self.addPowerBarPlot()
        #-------

    def _init_layout(self):
        mainLayout = QtWidgets.QVBoxLayout()
        bottomLayout = QtWidgets.QHBoxLayout()
        controlLayout = QtWidgets.QVBoxLayout()
        cTopButtonsLayout = QtWidgets.QGridLayout()
        cRecordingHistoryLayout = QtWidgets.QHBoxLayout()
        cRecordingHistoryButtonsLayout = QtWidgets.QVBoxLayout()

        b1 = QtWidgets.QPushButton('Connect Device')
        b2 = QtWidgets.QPushButton('Disconnect Device')
        b3 = QtWidgets.QPushButton('Start Recording')
        b4 = QtWidgets.QPushButton('Stop Recording')
        b5 = QtWidgets.QPushButton('Play')
        b6 = QtWidgets.QPushButton('Pause')
        b7 = QtWidgets.QPushButton('S')

        b1.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding))
        b2.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding))
        b3.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding))
        b4.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding))
        b5.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding))
        b6.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding))
        b7.setFixedSize(70,70)


        b1.clicked.connect(lambda: self.onButtonClick(b1))
        b2.clicked.connect(lambda: self.onButtonClick(b2))
        b3.clicked.connect(lambda: self.onButtonClick(b3))
        b4.clicked.connect(lambda: self.onButtonClick(b4))
        b5.clicked.connect(lambda: self.onButtonClick(b5))
        b6.clicked.connect(lambda: self.onButtonClick(b6))
        b7.clicked.connect(lambda: self.onButtonClick(b7))
        
        self.recordingsWidget = QtWidgets.QListWidget() 
        self.recordingsWidget.clicked.connect(self.onListItemClick)
        self.recordingsWidget.doubleClicked.connect(self.onListItemDoubleClick)
        self.recordingsWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        
        #Buttons
        cTopButtonsLayout.addWidget(b1, 0, 0)
        cTopButtonsLayout.addWidget(b2, 1, 0)
        cTopButtonsLayout.addWidget(b3, 0, 1)
        cTopButtonsLayout.addWidget(b4, 1, 1)
        cTopButtonsLayout.addWidget(b5, 0, 2)
        cTopButtonsLayout.addWidget(b6, 1, 2)
        cRecordingHistoryButtonsLayout.addWidget(b7, alignment= QtCore.Qt.AlignmentFlag.AlignTop)

        #List+Button
        cRecordingHistoryLayout.addWidget(self.recordingsWidget)
        cRecordingHistoryLayout.addLayout(cRecordingHistoryButtonsLayout)

        #Message + Buttons + List + Power Bands 
        self.message.setFixedHeight(30)
        controlLayout.addWidget(self.message)
        controlLayout.addLayout(cTopButtonsLayout, stretch = 1)
        controlLayout.addLayout(cRecordingHistoryLayout, stretch = 1)
        controlLayout.addWidget(self.win3, stretch = 2)
        
        #Control Layout + All the bottom plots
        bottomLayout.addLayout(controlLayout, stretch=2)
        bottomLayout.addWidget(self.win2, stretch=3)
        
        #The whole layout
        mainLayout.setContentsMargins(10,10,10,10)
        mainLayout.addWidget(self.win1, stretch= 1)
        mainLayout.addLayout(bottomLayout, stretch=4)
        
        #Layout attached to the main window
        self.mainWindow.setLayout(mainLayout)
        self.mainWindow.showMaximized()

    def getAverageOfPowerBands(self, freqScale, power):
        bands = [1, 4, 8, 13, 30, 45]
        avgPow = []

        for i in range(len(bands)-1):
            argMinF = np.argmin(np.abs(freqScale-bands[i]))
            argMaxF = np.argmin(np.abs(freqScale-bands[i+1]))
            avgPow.append(np.sum(power[argMinF:argMaxF]) / (bands[i+1]-bands[i]))

        return avgPow

    def addPowerBarPlot(self):
        x = [1, 2, 3, 4, 5]		
        y = [0, 0, 0, 0, 0]
        
        powerBarPlot = self.win3.addPlot()
        self.win3.ci.setContentsMargins(1,1,1,1)
        self.win3.ci.setBorder(color=(220, 220, 220), width=0.5)
        
        powerBarPlot.setTitle(f'Frequency Bands')
        powerBarPlot.setContentsMargins(0,10,0,10)
        powerBarPlot.setMouseEnabled(False, False)
        powerBarPlot.showAxis('left',False)
        powerBarPlot.setRange(xRange = (1,5),yRange = (0,1),padding = 0.15)

        labels = [(1, 'delta'),(2, 'theta'),(3, 'alpha'),(4, 'beta'),(5, 'gamma')]
        ax=powerBarPlot.getAxis('bottom')
        ax.setTicks([labels])

        bargraph = pg.BarGraphItem(x = x, height = y, width = 0.9, brush ='g')
        powerBarPlot.addItem(bargraph)

        return bargraph, powerBarPlot

    def addBluetoothDevice(self, addr, name, cl):
        QtWidgets.QListWidgetItem(f'{addr} | {name} | {cl}', self.recordingsWidget)

    def addRecording(self, start, end, id):
        lastPos = self.recordingsWidget.count()
        QtWidgets.QListWidgetItem(f'R{lastPos+1} | {end-start} | {start} : {end} | {id}', self.recordingsWidget)

    def startRecording(self):
        if self.isRecording is False and self.socket is not None and self.pause is False:
            if self.folderName is None:
                self.chooseFile()
            else:
                self.setMessage('Recording...')
                self.recordingStartIndex = len(self.parser.recorder.raw)
                self.recordingStartTime = datetime.datetime.now()
                self.isRecording = True

    def stopRecording(self):
        if self.isRecording is True:
            self.setMessage('')
            
            self.recordingEndIndex = len(self.parser.recorder.raw)
            self.recordingEndTime = datetime.datetime.now()

            recId = self.recordingEndTime.strftime('%Y-%m%d-%H%M%S-') + str(uuid4())
            rec = self.parser.recorder.raw[self.recordingStartIndex:self.recordingEndIndex]
            
            self.saveRecording(recId, rec)
            self.addRecording(self.recordingStartTime, self.recordingEndTime, recId)
            
            self.isRecording = False

    def saveRecording(self, id, rec):
        d = {}
        d['id'] = id
        d['sf'] = 512
        d['data'] = rec
        if self.folderName is not None:
            file = os.path.join(self.folderName, f"{id}.json")
            with open(file, 'w') as f:
                json.dump(d, f)

    def chooseFile(self):
        folderName = str(QtWidgets.QFileDialog.getExistingDirectory(self.mainWindow, "Select Folder"))
        self.folderName = folderName

    def setMessage(self, text):
        self.message.setText(text)
        self.app.processEvents()

    def onButtonClick(self, but: QtWidgets.QPushButton):
        text = but.text()
        match text:
            case 'Connect Device':
                if self.socket is None:
                    self.setMessage("Searching for a device...")
                    self.waitCursorOn(True)
                    self.recordingsWidget.clear()

                    dev = search_blueetooth_devices()
                    for addr, name, cl in dev:
                        self.addBluetoothDevice(addr,name,cl)

                    self.setMessage("")
                    self.waitCursorOn(False)

            case 'Disconnect Device':
                self.stopRecording()
                self.disconnectDevice()

            case 'Start Recording':
                self.startRecording()

            case 'Stop Recording':
                self.stopRecording()

            case 'Play':
                if self.pause is True:
                    self.parser.recorder.cleanSlate()
                    self.pause = False
                    self.setMessage('')

            case 'Pause':
                if self.socket is not None:
                    self.pause = True
                    self.setMessage('Paused')
                    self.stopRecording()
            case 'S':
                self.chooseFile()
            case _:
                pass

    def onListItemClick(self, qmodelindex):
        pass        

    def onListItemDoubleClick(self, qmodelindex):
        text = self.recordingsWidget.currentItem().text()

        if text[2] == ':':
            if text.find("CURV") != -1:
                self.setMessage('Connecting...')
                self.waitCursorOn(True)
                
                addr = text[:17]
                self.socket = start_headset(addr)
                if self.socket is not None:
                    self.addr = addr
                    self.pause = False
                    self.recordingsWidget.clear()
                    self.setMessage('')
                else:
                    self.setMessage('Failed to connect. Try again.')
                
                self.waitCursorOn(False)
            else:
                self.setMessage('Not a Curvex Device.')

    def disconnectDevice(self):
        if self.socket!= None:
            self.socket.close()
            self.socket = None
            self.addr = ''
            self.parser.recorder.cleanSlate()
            self.setMessage('Connect a device.')

    def waitCursorOn(self, wait):
        if wait:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.WaitCursor)
        else:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)

    def update(self):
        try:
            if self.socket is not None:
                r, w, er = select.select([self.socket],[],[self.socket])
                if len(r) > 0:
                    byteData = r[0].recv(20000)
                    if len(byteData) == 0:
                        self.disconnectDevice()
                    else:
                        if self.pause is False:
                            self.parser.feed(byteData)
        except Exception as e:        
            self.setMessage('An error occurred')

        longPlotData = self.parser.recorder.get_last_n_raw_second(self.numSecLong)
        shortPlotData = self.parser.recorder.get_last_n_raw_second(self.numSecShort)

        filtShortData = filter_data(shortPlotData)

        freqScale, power = get_power(filtShortData, self.sf)

        self.curves[0].setData(longPlotData)
        self.curves[1].setData(shortPlotData)
        self.curves[2].setData(filtShortData)
        self.curves[3].setData(freqScale, power)

        powBands = self.getAverageOfPowerBands(freqScale,power)
        self.powerBarItem.setOpts(height = normalize(powBands))

        self.app.processEvents()


if __name__ == '__main__':
        
    recorder = DataRecorder()
    parser = DataParser(recorder)

    DAGUI(parser)

