import contextlib
import logging
import os
import sys
import threading
import time
import math,cmath
import pandas as pd
from pandas import ExcelWriter
from time import strftime, localtime
from PyQt5 import QtWidgets, QtCore, QtGui

import matplotlib.pyplot as plt
import pyqtgraph as pg
from typing import List, Tuple

from NanoVNASaver import Defaults

from .Windows import (
    AboutWindow, CalibrationWindow,
    DeviceSettingsWindow, DisplaySettingsWindow, SweepSettingsWindow)

from NanoVNASaver.Files import FilesWindow

from .Controls.MarkerControl import MarkerControl
from .Controls.SweepControl import SweepControl
from .Controls.SerialControl import SerialControl
from .Hardware.Hardware import Interface
from .Hardware.VNA import VNA

from .RFTools import corr_att_data

from .Charts.Chart import Chart

from .Charts import ( GroupDelayChart,LogMagChart, PhaseChart, MagnitudeChart, ReYChart)

from .Calibration import Calibration
from .Marker.Widget import Marker
from .Marker.Delta import DeltaMarker
from .SweepWorker import SweepWorker
from .Settings.Bands import BandsModel
from .Touchstone import Touchstone
from .About import VERSION
from NanoVNASaver.Settings.Sweep import Sweep,SweepMode

logger = logging.getLogger(__name__)



class NanoVNASaver(QtWidgets.QWidget):
    version = VERSION
    dataAvailable = QtCore.pyqtSignal()
    scaleFactor = 1

    def __init__(self):
        super().__init__()
        self.s21att = 0.0
        if getattr(sys, 'frozen', False):
            logger.debug("Running from pyinstaller bundle")
            self.icon = QtGui.QIcon(
                f"{sys._MEIPASS}/icon_48x48.png")  # pylint: disable=no-member
        else:
            self.icon = QtGui.QIcon("icon_48x48.png")
        self.setWindowIcon(self.icon)
        self.settings = Defaults.AppSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            "NanoVNASaver",
            "NanoVNASaver")
        logger.info("Settings from: %s", self.settings.fileName())
        Defaults.cfg = Defaults.restore(self.settings)
        self.threadpool = QtCore.QThreadPool()
        self.sweep = Sweep()

        self.worker = SweepWorker(self)
        self.worker.signals.updated.connect(self.dataUpdated)
        self.worker.signals.finished.connect(self.sweepFinished)
        self.worker.signals.sweepError.connect(self.showSweepError)
        self.worker.signals.calcnow.connect(lambda : self.calcnow())

        self.markers = []
        self.marker_ref = False

        self.tm: List[float] = []
        self.db: List[float] = []

        self.marker_column = QtWidgets.QVBoxLayout()
        self.marker_frame = QtWidgets.QFrame()
        self.marker_column.setContentsMargins(0, 0, 0, 0)
        self.marker_frame.setLayout(self.marker_column)

        self.sweep_control = SweepControl(self)
        self.marker_control = MarkerControl(self)
        self.serial_control = SerialControl(self)
        self.bands = BandsModel()

        self.interface = Interface("serial", "None")
        self.vna = VNA(self.interface)

        self.dataLock = threading.Lock()
        self.data = Touchstone()
        self.ref_data = Touchstone()

        self.sweepSource = ""
        self.referenceSource = ""

        self.calibration = Calibration()

        logger.debug("Building user interface")

        self.baseTitle = f"Bio - LSAW"
        self.updateTitle()
        layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight)

        scrollarea = QtWidgets.QScrollArea()
        outer = QtWidgets.QVBoxLayout()
        outer.addWidget(scrollarea)
        self.setLayout(outer)
        scrollarea.setWidgetResizable(True)
        self.resize(Defaults.cfg.gui.window_width,
                    Defaults.cfg.gui.window_height)
        scrollarea.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        scrollarea.setWidget(widget)

        self.charts = {
            "s21": {
                "group_delay": GroupDelayChart("S21 Group Delay", reflective=False),
                "log_mag": LogMagChart("S21 Gain"),
                "magnitude": MagnitudeChart("|S21|"),
                "phase": PhaseChart("S21 Phase"),
                "ReY": ReYChart("ReY"),
            }
        }

        # List of all the S21 charts, for selecting
        self.s21charts = list(self.charts["s21"].values())

        # List of all charts that can be selected for display
        self.selectable_charts = self.s21charts

        # List of all charts that subscribe to updates (including duplicates!)
        self.subscribing_charts = []
        self.subscribing_charts.extend(self.selectable_charts)

        for c in self.subscribing_charts:
            c.popoutRequested.connect(self.popoutChart)

        self.charts_layout = QtWidgets.QGridLayout()

        QtWidgets.QShortcut(QtGui.QKeySequence("Ctrl+Q"), self, self.close)

        ###############################################################
        #  Create main layout
        ###############################################################

        left_column = QtWidgets.QVBoxLayout()
        right_column = QtWidgets.QVBoxLayout()
        #right_column.addLayout(self.charts_layout)
        self.marker_frame.setHidden(Defaults.cfg.gui.markers_hidden)
        chart_widget = QtWidgets.QWidget()
        chart_widget.setLayout(right_column)
        self.splitter = QtWidgets.QSplitter()
        self.splitter.addWidget(self.marker_frame)
        self.splitter.addWidget(chart_widget)

        self.splitter.restoreState(Defaults.cfg.gui.splitter_sizes)

        layout.addLayout(left_column)
        layout.addWidget(self.splitter, 2)

        ###############################################################
        #  Windows
        ###############################################################

        self.windows = {
            "about": AboutWindow(self),
            "calibration": CalibrationWindow(self),
            "device_settings": DeviceSettingsWindow(self),
            "files": FilesWindow(self),
            "sweep_settings": SweepSettingsWindow(self),
            "setup": DisplaySettingsWindow(self)
        }

        ###############################################################
        #  Sweep control
        ###############################################################

        left_column.addWidget(self.sweep_control)

        # ###############################################################

        d_barrido_box = QtWidgets.QGroupBox()

        d_barrido_box.setTitle("Datos del barrido")
        d_barrido_box.setMaximumWidth(840)

        d_barrido_layout = QtWidgets.QFormLayout()
        d_barrido_box.setLayout(d_barrido_layout)


        self.tst_sweep = QtWidgets.QLabel()
        self.tst_sweep.setMinimumHeight(20)
        self.tst_sweep.setText("OFF")

        d_barrido_layout.addRow("Estado Actual: ", self.tst_sweep)

        self.mode_sweep = QtWidgets.QLabel()
        self.mode_sweep.setMinimumHeight(20)
        self.mode_sweep.setText(" ")

        d_barrido_layout.addRow("Nº de Barrido: ", self.mode_sweep)

        self.ttot=0
        self.t_sweep = QtWidgets.QLabel()
        self.t_sweep.setMinimumHeight(20)
        self.t_sweep.setText(f"{self.ttot}")

        d_barrido_layout.addRow("Duración Ùltimo Barrido [ seg ] : ", self.t_sweep)


        self.ttot_sweep = QtWidgets.QLabel()
        self.ttot_sweep.setMinimumHeight(20)
        self.ttot_sweep.setText(f"{self.ttot}")

        d_barrido_layout.addRow("Duración Total [ seg ] : ", self.ttot_sweep)

        left_column.addWidget(d_barrido_box)

        ###############################################################
        #  Marker control
        ###############################################################

        left_column.addWidget(self.marker_control)

        for c in self.subscribing_charts:
            c.setMarkers(self.markers)
            c.setBands(self.bands)

        self.marker_data_layout = QtWidgets.QVBoxLayout()
        self.marker_data_layout.setContentsMargins(0, 0, 0, 0)

        for m in self.markers:
            self.marker_data_layout.addWidget(m.get_data_layout())

        scroll2 = QtWidgets.QScrollArea()
        # scroll2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll2.setWidgetResizable(True)
        scroll2.setVisible(True)

        widget2 = QtWidgets.QWidget()
        widget2.setLayout(self.marker_data_layout)
        scroll2.setWidget(widget2)
        self.marker_column.addWidget(scroll2)

        # init delta marker (but assume only one marker exists)
        self.delta_marker = DeltaMarker("Delta Marker 2 - Marker 1")
        self.delta_marker_layout = self.delta_marker.get_data_layout()
        self.delta_marker_layout.hide()
        #self.marker_column.addWidget(self.delta_marker_layout)

        ###############################################################
        #  Statistics
        ###############################################################

        s21_control_box = QtWidgets.QGroupBox()
        s21_control_box.setTitle("Parámetros del Barrido")

        s21_control_layout = QtWidgets.QFormLayout()
        s21_control_layout.setVerticalSpacing(0)
        s21_control_box.setLayout(s21_control_layout)

        # Boton para mostrar estadisticas del último barrido realizado

        btn_calc = QtWidgets.QPushButton("Calcular")
        btn_calc.setFixedHeight(20)
        btn_calc.clicked.connect(lambda: self.calc())
        s21_control_layout.addRow(btn_calc)
        self.actfr = 0


        btn_calc_res = QtWidgets.QPushButton("Resetear")
        btn_calc_res.setFixedHeight(20)
        btn_calc_res.clicked.connect(lambda: self.calcpr_res())
        s21_control_layout.addRow(btn_calc_res)

        self.gain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Pico[dB]:", self.gain_label)

        self.phgain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Pico[Deg]:", self.phgain_label)

        self.frgain_label = QtWidgets.QLabel()
        s21_control_layout.addRow("Pico[MHz]:", self.frgain_label)

        ##########################################################

        self.difdb=0
        self.gain_label_dif = QtWidgets.QLabel()
        s21_control_layout.addRow("Dif[dB]:", self.gain_label_dif)

        self.difph=0
        self.phgain_label_dif = QtWidgets.QLabel()
        s21_control_layout.addRow("Dif[Deg]:", self.phgain_label_dif)

        self.difhz=0
        self.frgain_label_dif = QtWidgets.QLabel()
        s21_control_layout.addRow("Dif[KHz]:", self.frgain_label_dif)
        ###########################################################

        self.marker_column.addWidget(s21_control_box)

        ###############################################################
        #  Time Chart
        ###############################################################
        self.graf = QtWidgets.QLabel(self)
        self.graf.setText("GRAFICOS (t)")
        self.graf.setFont(QtGui.QFont("Times", 12, QtGui.QFont.Bold))
        self.graf.setAlignment(QtCore.Qt.AlignHCenter)
        self.marker_column.addWidget(self.graf)

        self.tly = QtWidgets.QGridLayout()

        self.graphWidget = pg.PlotWidget()

        self.difdb = 0
        self.difhz = 0
        self.difph = 0

        self.tx: List[float] = []
        self.yv: List[float] = []
        #self.tx.append(0)
        #self.yv.append(0)

        self.graphWidget.setLabel('left', 'Phase', units='Degrees')
        self.graphWidget.setLabel('bottom', 'Time', units='s')
        self.graphWidget.setYRange(-30, 15)

        # plot data: x, y values
        self.plot = self.graphWidget.plot(self.tx, self.yv)
        self.graphWidget.resize(50, 50)
        self.tly.addWidget(self.graphWidget)
        self.boxtly = QtWidgets.QGroupBox()
        self.boxtly.setMaximumSize(450, 350)
        self.boxtly.setLayout(self.tly)

        self.marker_column.addWidget(self.boxtly)

        # ###############################################################

        ###############################################################
        #  Spacer
        ###############################################################

        left_column.addSpacerItem(
            QtWidgets.QSpacerItem(1, 1, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding))

        ###############################################################
        #  Serial control
        ###############################################################

        left_column.addWidget(self.serial_control)

        ###############################################################
        #  Calibration
        ###############################################################

        btnOpenCalibrationWindow = QtWidgets.QPushButton("Calibración")
        btnOpenCalibrationWindow.setMinimumHeight(20)
        self.calibrationWindow = CalibrationWindow(self)
        btnOpenCalibrationWindow.clicked.connect(lambda : self.display_cali())
        ###############################################################
        #  Display setup
        ###############################################################


        btn_datasave = QtWidgets.QPushButton("Guardar Datos")
        btn_datasave.setMinimumHeight(20)
        btn_datasave.setMaximumWidth(240)

        btn_datasave.clicked.connect(lambda: self.smart_save())

        btn_open_file_window = QtWidgets.QPushButton("Cargar/Guardar S2P")
        btn_open_file_window.setMinimumHeight(20)
        btn_open_file_window.setMaximumWidth(240)

        btn_open_file_window.clicked.connect(
            lambda: self.display_window("files"))


        btn_display_setup = QtWidgets.QPushButton("Configuración de la pantalla")
        btn_display_setup.setMinimumHeight(20)
        btn_display_setup.setMaximumWidth(240)
        btn_display_setup.clicked.connect(
            lambda: self.display_window("setup"))



        button_grid = QtWidgets.QGridLayout()
        button_grid.addWidget(btn_open_file_window, 0, 0)
        button_grid.addWidget(btnOpenCalibrationWindow, 0, 1)
        button_grid.addWidget(btn_display_setup, 1, 1)
        button_grid.addWidget(btn_datasave, 1, 0)
        #left_column.addLayout(button_grid)

        logger.debug("Finished building interface")

        ########################################################
        #  Color y titulos
        ###############################################################

        self.marker_control.setStyleSheet('background-color:lightBlue;')
        self.sweep_control.setStyleSheet('background-color:lightBlue;')
        self.serial_control.setStyleSheet('background-color:lightBlue;')
        btnOpenCalibrationWindow.setStyleSheet('background-color:lightBlue;')
        btn_datasave.setStyleSheet('background-color:lightBlue;')
        btn_open_file_window.setStyleSheet('background-color:lightBlue;')
        btn_display_setup.setStyleSheet('background-color:lightBlue;')
        self.marker_frame.setStyleSheet('background-color:lightGreen;')

        self.graf = QtWidgets.QLabel(self)
        self.graf.setText("GRAFICOS (f)")
        self.graf.setFont(QtGui.QFont("Times", 12, QtGui.QFont.Bold))
        self.graf.setAlignment(QtCore.Qt.AlignHCenter)
        right_column.addWidget(self.graf)
        right_column.addLayout(self.charts_layout)  # hay que comentar o eliminar
        ##esta sentencia anteriormente, la ubico después de agregar el titulo poque sino
        ##lo agrega abajo

        self.confi = QtWidgets.QLabel(self)
        self.confi.setText("CONFIGURACION")
        self.confi.setFont(QtGui.QFont("Times", 12, QtGui.QFont.Bold))
        self.confi.setAlignment(QtCore.Qt.AlignHCenter)
        self.confi.setStyleSheet('background-color:lightblue;')
        left_column.addWidget(self.confi)
        left_column.addWidget(self.sweep_control)  ##idem anterior, comentar antes
        left_column.addWidget(self.marker_control)  ####idem anterior,comentar antes
        left_column.addWidget(self.serial_control)  ####idem anterior,comentar antes
        left_column.addLayout(button_grid)  ####idem anterior,comentar antes

        self.moni = QtWidgets.QLabel(self)
        self.moni.setText("MONITOREO")
        self.moni.setFont(QtGui.QFont("Times", 12, QtGui.QFont.Bold))
        self.moni.setAlignment(QtCore.Qt.AlignHCenter)
        self.marker_column.addWidget(self.moni)
        self.marker_column.addWidget(scroll2)  ##idem anterior comentar antes
        self.marker_column.addWidget(self.delta_marker_layout)
        self.marker_column.addWidget(s21_control_box)  ####idem anterior,comentar antes

    def sweep_start(self):

        # Run the device data update
        if not self.vna.connected():
            QtWidgets.QMessageBox.warning(self, "Error", "Sistema sin conexión")
            return
        self.worker.stopped = False

        if self.sweep_control.get_stepsize()==1:
            QtWidgets.QMessageBox.warning(self, "Error", "Paso menor a 1 Hz")
            return

        # Arranca el barrido

        self.worker.fr.clear()
        self.worker.mg.clear()
        self.worker.dg.clear()

        self.worker.alls21.clear()
        self.worker.tm.clear()

        self.tst_sweep.setText("ON")

        if self.sweep.properties.mode == SweepMode.SINGLE:
            self.mode_sweep.setText("Simple (1)")

        if self.sweep.properties.mode == SweepMode.CONTINOUS:
            self.mode_sweep.setText("Continuo ()")

        self.sweep_control.progress_bar.setValue(0)
        self.sweep_control.btn_start.setDisabled(True)
        self.sweep_control.btn_stop.setDisabled(False)
        self.sweep_control.toggle_settings(True)

        self.settings.setValue("Segments", self.sweep_control.get_segments())

        if self.sweep.properties.mode == SweepMode.CONTINOUS:
            self.graphWidget.clear()
            self.ttot=0

        logger.debug("Starting worker thread")
        self.threadpool.start(self.worker)

    def sweep_stop(self):

        self.worker.stopped = True

    def saveData(self, data, data21, source=None):
        with self.dataLock:
            self.data.s11 = data
            self.data.s21 = data21
            if self.s21att > 0:
                self.data.s21 = corr_att_data(self.data.s21, self.s21att)
        if source is not None:
            self.sweepSource = source
        else:
            self.sweepSource = (
                f"{self.sweep.properties.name}"
                f" {strftime('%Y-%m-%d %H:%M:%S', localtime())}"
            ).lstrip()

    def markerUpdated(self, marker: Marker):
        with self.dataLock:
            marker.findLocation(self.data.s11)
            marker.resetLabels()
            marker.updateLabels(self.data.s11, self.data.s21)
            for c in self.subscribing_charts:
                c.update()
        if not self.delta_marker_layout.isHidden():
            m1 = self.markers[0]
            m2 = None
            if self.marker_ref:
                if self.ref_data:
                    m2 = Marker("Reference")
                    m2.location = self.markers[0].location
                    m2.resetLabels()
                    m2.updateLabels(self.ref_data.s11,
                                    self.ref_data.s21)
                else:
                    logger.warning("No reference data for marker")

            elif Marker.count() >= 2:
                m2 = self.markers[1]

            if m2 is None:
                logger.error("No data for delta, missing marker or reference")
            else:
                self.delta_marker.set_markers(m1, m2)
                self.delta_marker.resetLabels()
                with contextlib.suppress(IndexError):
                    self.delta_marker.updateLabels()

    def dataUpdated(self):
        with self.dataLock:
            s11 = self.data.s11[:]
            s21 = self.data.s21[:]

        for m in self.markers:
            m.resetLabels()
            m.updateLabels(s11, s21)

        #for c in self.s11charts:
        #    c.setData(s11)

        for c in self.s21charts:
            c.setData(s21)

        #for c in self.combinedCharts:
        #    c.setCombinedData(s11, s21)

        self.sweep_control.progress_bar.setValue(int(self.worker.percentage))

        self.updateTitle()
        self.dataAvailable.emit()

    def sweepFinished(self):
        self.sweep_control.progress_bar.setValue(100)
        self.sweep_control.btn_start.setDisabled(False)
        self.sweep_control.btn_stop.setDisabled(True)
        self.sweep_control.toggle_settings(False)

        for marker in self.markers:
            marker.frequencyInput.textEdited.emit(
                marker.frequencyInput.text())

        #for c in self.s21charts:
        #    c.setData(self.as21)

        self.tst_sweep.setText("OFF")


    def setReference(self, s11=None, s21=None, source=None):
        if not s11:
            with self.dataLock:
                s11 = self.data.s11[:]
                s21 = self.data.s21[:]

        self.ref_data.s11 = s11
        for c in self.s11charts:
            c.setReference(s11)

        self.ref_data.s21 = s21
        for c in self.s21charts:
            c.setReference(s21)

        for c in self.combinedCharts:
            c.setCombinedReference(s11, s21)

        self.btnResetReference.setDisabled(False)

        self.referenceSource = source or self.sweepSource
        self.updateTitle()

    def updateTitle(self):
        insert = "("
        if self.sweepSource != "":
            insert += (
                f"Sweep: {self.sweepSource} @ {len(self.data.s11)} points"
                f"{', ' if self.referenceSource else ''}")
        if self.referenceSource != "":
            insert += (
                f"Reference: {self.referenceSource} @"
                f" {len(self.ref_data.s11)} points")
        insert += ")"
        title = f"{self.baseTitle} {insert or ''}"
        self.setWindowTitle(title)

    def resetReference(self):
        self.ref_data = Touchstone()
        self.referenceSource = ""
        self.updateTitle()
        for c in self.subscribing_charts:
            c.resetReference()
        self.btnResetReference.setDisabled(True)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(1100, 950)

    def display_window(self, name):
        self.windows[name].show()
        QtWidgets.QApplication.setActiveWindow(self.windows[name])
    def showError(self, text):
        QtWidgets.QMessageBox.warning(self, "Error", text)

    def showSweepError(self):
        self.showError(self.worker.error_message)
        with contextlib.suppress(IOError):
            self.vna.flushSerialBuffers()  # Remove any left-over data
            self.vna.reconnect()  # try reconnection
        self.sweepFinished()

    def popoutChart(self, chart: Chart):
        logger.debug("Requested popout for chart: %s", chart.name)
        new_chart = self.copyChart(chart)
        new_chart.isPopout = True
        new_chart.show()
        new_chart.setWindowTitle(new_chart.name)

    def copyChart(self, chart: Chart):
        new_chart = chart.copy()
        self.subscribing_charts.append(new_chart)
        if chart in self.s11charts:
            self.s11charts.append(new_chart)
        new_chart.popoutRequested.connect(self.popoutChart)
        return new_chart

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.worker.stopped = True
        for marker in self.markers:
            marker.update_settings()
        self.settings.sync()
        self.bands.saveSettings()
        self.threadpool.waitForDone(2500)

        Defaults.cfg.chart.marker_count = Marker.count()
        Defaults.cfg.gui.window_width = self.width()
        Defaults.cfg.gui.window_height = self.height()
        Defaults.cfg.gui.splitter_sizes = self.splitter.saveState()
        Defaults.store(self.settings, Defaults.cfg)

        a0.accept()
        sys.exit()

    def changeFont(self, font: QtGui.QFont) -> None:
        qf_new = QtGui.QFontMetricsF(font)
        normal_font = QtGui.QFont(font)
        normal_font.setPointSize(8)
        qf_normal = QtGui.QFontMetricsF(normal_font)
        # Characters we would normally display
        standard_string = "0.123456789 0.123456789 MHz \N{OHM SIGN}"
        new_width = qf_new.horizontalAdvance(standard_string)
        old_width = qf_normal.horizontalAdvance(standard_string)
        self.scaleFactor = new_width / old_width
        logger.debug("New font width: %f, normal font: %f, factor: %f",
                     new_width, old_width, self.scaleFactor)
        # TODO: Update all the fixed widths to account for the scaling
        for m in self.markers:
            m.get_data_layout().setFont(font)
            m.setScale(self.scaleFactor)

    def update_sweep_title(self):
        for c in self.subscribing_charts:
            c.setSweepTitle(self.sweep.properties.name)

    def calcpr_res(self):

        self.difdb=0
        self.difhz=0
        self.difph=0

        self.gain_label.setText(" ")
        self.gain_label_dif.setText(" ")
        self.frgain_label.setText(" ")
        self.frgain_label_dif.setText(" ")
        self.phgain_label.setText(" ")
        self.phgain_label_dif.setText(" ")
        self.t_sweep.setText(" ")
        self.ttot_sweep.setText(" ")

        self.tx.clear()
        #self.tx.append(0)
        self.yv.clear()
        #self.yv.append(0)
        self.ttot=0

        self.graphWidget.clear()

    def calcnow(self):

            with self.dataLock:
                s21 = self.data.s21[:]

            if not s21 :
                QtWidgets.QMessageBox.warning(self, "Error", "Sin datos disponibles")
                return
            else:
                self.gain_label.setText(f"{self.worker.actm:.3f}")
                self.phgain_label.setText(f"{self.worker.actg:.3f}")
                self.frgain_label.setText(f"{(self.worker.actf / 1000000):.6f}")

                ddb=self.worker.actm-self.difdb
                dhz=self.worker.actf-self.difhz
                dph=self.worker.actg-self.difph

                self.gain_label_dif.setText(f"{ddb:.3f} ({self.difdb:.3f})")
                self.phgain_label_dif.setText(f"{dph:.3f} ({self.difph:.3f})")
                self.frgain_label_dif.setText(f"{(dhz/1000):.3f} ({self.difhz/1000000:.6f})")
                self.difdb=self.worker.actm
                self.difhz=self.worker.actf
                self.difph=self.worker.actg

                self.ttot = round (self.ttot + self.worker.actt , 2)
                self.tx.append(self.ttot)

                self.yv.append(self.worker.actg)

                self.graphWidget.plot(self.tx, self.yv)


                self.t_sweep.setText((f"{self.worker.actt}"))
                self.ttot_sweep.setText((f"{self.ttot}"))


                if self.sweep.properties.mode == SweepMode.CONTINOUS:
                    numb=str(self.worker.inic)
                    modeswp=("Continuo (") + numb + (")")
                    self.mode_sweep.setText(modeswp)

                self.updateTitle()
                self.dataAvailable.emit()
    ########################################################################333

    def calc(self):

            with self.dataLock:
                s21 = self.data.s21[:]

            if not s21 :
                QtWidgets.QMessageBox.warning(self, "Error", "Sin datos disponibles")
                return

            else:

                actm = 0
                actf = 0
                actg = 0

                if self.sweep.properties.anmode == 0:

                    mg = -100
                    cont = 0

                    for i in s21:
                        if i.gain > mg:
                            if  -2 < i.phase * (180 / 3.14) < 2:
                                actm = i.gain
                                actf = i.freq
                                actg = i.phase * (180 / 3.14)
                                self.actfr = cont
                                mg = i.gain
                        cont = cont + 1

                if self.sweep.properties.anmode == 1:

                        actm = s21[self.actfr].gain
                        actf = s21[self.actfr].freq
                        actg = s21[self.actfr].phase * (180 / 3.14)


                self.gain_label.setText(f"{actm:.3f}")
                self.phgain_label.setText(f"{actg:.3f}")
                self.frgain_label.setText(f"{(actf / 1000000):.6f}")

                if self.difdb == 0 and self.difhz == 0:
                    self.difdb = self.worker.actm
                    self.difhz = self.worker.actf
                    self.difph = self.worker.actg

                else:
                    ddb = self.worker.actm - self.difdb
                    dhz = self.worker.actf - self.difhz
                    dph = self.worker.actg - self.difph

                    self.gain_label_dif.setText(f"{ddb:.3f} ({self.difdb:.3f})")
                    self.phgain_label_dif.setText(f"{dph:.3f} ({self.difph:.3f})")
                    self.frgain_label_dif.setText(f"{(dhz / 1000):.3f} ({self.difhz / 1000000:.6f})")
                    self.difdb = self.worker.actm
                    self.difhz = self.worker.actf
                    self.difph = self.worker.actg


                self.updateTitle()
                self.dataAvailable.emit()
    ########################################################################333

    def display_cali(self):

        if self.sweep_control.get_stepsize()==1:
            QtWidgets.QMessageBox.warning(self, "Error", "Paso menor a 1 Hz")
            return
        else:
            self.display_window("calibration")

    #Guardado Inteligente
    def smart_save(self):

        s21 = self.data.s21[:]
        banderita=1

        if not s21 :
            QtWidgets.QMessageBox.warning(self, "Error", "Sin datos disponibles")
            banderita=0
            return None

        #Si el barrido es simple
        else :

            if banderita == 1 and self.sweep.properties.mode == SweepMode.SINGLE :

                s21 = self.data.s21[:]
                rows = len(s21)

                tm = self.worker.tmedia

                mat = [[0 for _ in range(3)] for _ in range(rows)]

                for i in range(rows):
                    mat[i][0] = ' '
                    mat[i][1] = ' '
                    mat[i][2] = ' '

                    mat[i][0] = s21[i].gain
                    mat[i][1] = s21[i].phase
                    mat[i][2] = s21[i].freq


                df = pd.DataFrame({
                    'IL[dB]': [row[0] for row in mat],
                    'PH[Deg]': [row[1] for row in mat],
                    'Frec[Hz]': [row[2] for row in mat],
                })

                df = df[['IL[dB]', 'PH[Deg]', 'Frec[Hz]',  ]]

                filedialog = QtWidgets.QFileDialog(self)
                filedialog.setNameFilter("xlsx files (*.xlsx)")
                filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)

                selected = filedialog.exec()
                if not selected:
                    return
                else:
                    where_is = filedialog.selectedFiles()
                    writer = ExcelWriter(where_is[0])
                    df.to_excel(writer, 'Hoja de datos', index=False)
                    writer.save()

            if banderita == 1 and self.sweep.properties.mode == SweepMode.CONTINOUS :

                rows = len(self.worker.mg)

                mat = [[0 for _ in range(4)] for _ in range(rows)]


                for i in range(rows):
                    mat[i][0] = ' '
                    mat[i][1] = ' '
                    mat[i][2] = ' '
                    mat[i][3] = ' '

                    mat[i][0] = self.worker.mg[i]
                    mat[i][1] = self.worker.dg[i]
                    mat[i][2] = self.worker.fr[i]
                    mat[i][3] = self.worker.tm[i]

                df = pd.DataFrame({
                    'IL[dB]': [row[0] for row in mat],
                    'PH[Deg]': [row[1] for row in mat],
                    'Frec[Hz]': [row[2] for row in mat],
                    'Time[Seg]': [row[3] for row in mat],
                })

                df = df[['IL[dB]', 'PH[Deg]', 'Frec[Hz]', 'Time[Seg]',]]

                filedialog = QtWidgets.QFileDialog(self)
                filedialog.setNameFilter("xlsx files (*.xlsx)")
                filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)

                selected = filedialog.exec()
                if not selected:
                    return
                else:
                    where_is = filedialog.selectedFiles()
                    writer = ExcelWriter(where_is[0])
                    df.to_excel(writer, 'Hoja de datos', index=False)
                    writer.save()

