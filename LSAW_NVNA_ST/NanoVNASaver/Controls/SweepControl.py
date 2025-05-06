import logging

from PyQt5 import QtWidgets, QtCore

from PyQt5.QtWidgets import * 
from PyQt5 import QtGui 
from PyQt5.QtGui import *  
import sys

from NanoVNASaver.Formatting import (
    format_frequency_sweep, format_frequency_short,
    parse_frequency)
from NanoVNASaver.Inputs import FrequencyInputWidget
from NanoVNASaver.Controls.Control import Control
from NanoVNASaver.Windows.CalibrationSettings import CalibrationWindow


logger = logging.getLogger(__name__)
content="a"#Creación de una variable global, indica la unidad elegida en el combobox

class SweepControl(Control):


    def __init__(self, app: QtWidgets.QWidget):
        super().__init__(app, "Control de barrido")

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)

        input_layout = QtWidgets.QHBoxLayout()
        input_left_layout = QtWidgets.QFormLayout()
        input_right_layout = QtWidgets.QFormLayout()
        input_layout.addLayout(input_left_layout)
        input_layout.addWidget(line)
        input_layout.addLayout(input_right_layout)
        self.layout.addRow(input_layout)

        self.input_start = FrequencyInputWidget()
        self.input_start.setFixedHeight(20)
        self.input_start.setFixedWidth(40)
        self.input_start.setAlignment(QtCore.Qt.AlignRight)
        regex = QtCore.QRegExp('^[0-9]+([.][0-9]+)?$')#validación de textbox, solo toma digitos y punto como decimal
        self.input_start.setValidator(QRegExpValidator(regex))
        self.input_start.textEdited.connect(self.update_center_span)
        self.input_start.textChanged.connect(self.update_step_size)
        input_left_layout.addRow(QtWidgets.QLabel("FI"), self.input_start)

        #input_left_layout.addRow(QtWidgets.QLabel("Empezar"), self.input_start)

        self.input_end = FrequencyInputWidget()
        self.input_end.setFixedHeight(20)
        self.input_end.setFixedWidth(40)
        self.input_end.setAlignment(QtCore.Qt.AlignRight)
        self.input_end.textEdited.connect(self.update_center_span)
        self.input_end.textChanged.connect(self.update_step_size)
        self.input_end.setValidator(QRegExpValidator(regex))
        input_left_layout.addRow(QtWidgets.QLabel("FF"), self.input_end)
        
    
        self.combo_FF= QComboBox(self)#creación del combobox
        self.combo_FF.addItem("Hz")
        self.combo_FF.addItem("KHz")
        self.combo_FF.addItem("MHz")
        self.combo_FF.addItem("GHz")
        self.combo_FF.move(70, 35)
        self.combo_FF.adjustSize()
        self.combo_FF.currentTextChanged.connect(self.texto_cambiado_1)
        self.combo_FF.currentTextChanged.connect(self.update_center_span)
        self.combo_FF.currentTextChanged.connect(self.update_step_size)
        
        self.input_center = FrequencyInputWidget()
        self.input_center.setFixedHeight(20)
        self.input_center.setFixedWidth(80)
        self.input_center.setAlignment(QtCore.Qt.AlignRight)
        self.input_center.textEdited.connect(self.update_start_end)
        self.input_center.setReadOnly(True)
        self.input_center.setStyleSheet("background-color: yellow")

        input_right_layout.addRow(QtWidgets.QLabel(
            "FC"), self.input_center)

        self.input_span = FrequencyInputWidget()
        self.input_span.setFixedHeight(20)
        self.input_span.setFixedWidth(80)
        self.input_span.setAlignment(QtCore.Qt.AlignRight)
        self.input_span.textEdited.connect(self.update_start_end)
        self.input_span.setReadOnly(True)
        self.input_span.setStyleSheet("background-color: yellow")
        

        input_right_layout.addRow(QtWidgets.QLabel("FL"), self.input_span)

        self.input_segments = QtWidgets.QLineEdit(
            self.app.settings.value("Segmentos", "1"))
        self.input_segments.setAlignment(QtCore.Qt.AlignRight)
        self.input_segments.setFixedHeight(20)
        self.input_segments.setFixedWidth(60)
        self.input_segments.textEdited.connect(self.update_step_size)
        regex_seg = QtCore.QRegExp('^[0-9]+([0-9]+)?$')#validación del textbox de segmentos para que acepte solo numeros
        self.input_segments.setValidator(QRegExpValidator(regex_seg))
        
        self.fstep = 0
        self.label_step = QtWidgets.QLabel("Hz/paso")
        self.label_step.setAlignment(
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        segment_layout = QtWidgets.QHBoxLayout()
        segment_layout.addWidget(self.input_segments)
        segment_layout.addWidget(self.label_step)
        self.layout.addRow(QtWidgets.QLabel("Segmentos"), segment_layout)

        btn_settings_window = QtWidgets.QPushButton("Configuración de barrido ...")
        btn_settings_window.setFixedHeight(20)
        btn_settings_window.clicked.connect(
            lambda: self.app.display_window("sweep_settings"))

        self.layout.addRow(btn_settings_window)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.layout.addRow(self.progress_bar)

        self.btn_start = QtWidgets.QPushButton("Barrer")
        self.btn_start.setFixedHeight(20)
        self.btn_start.clicked.connect(self.app.sweep_start)
        self.btn_start.setShortcut(QtCore.Qt.Key_W | QtCore.Qt.CTRL)
        self.btn_stop = QtWidgets.QPushButton("Detener")
        self.btn_stop.setFixedHeight(20)
        self.btn_stop.clicked.connect(self.app.sweep_stop)
        self.btn_stop.setShortcut(QtCore.Qt.Key_Escape)
        self.btn_stop.setDisabled(True)
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout_widget = QtWidgets.QWidget()
        btn_layout_widget.setLayout(btn_layout)
        self.layout.addRow(btn_layout_widget)

        self.input_start.textEdited.emit(self.input_start.text())
        self.input_start.textChanged.emit(self.input_start.text())

    def get_start(self) -> int:
        if content=="KHz":
           return parse_frequency(self.input_start.text()+"Khz") 
        elif content=="MHz":
           return parse_frequency(self.input_start.text()+"Mhz")
        elif content=="GHz":
           return parse_frequency(self.input_start.text()+"Ghz")
        else: 
           return parse_frequency(self.input_start.text())

    def set_start(self, start: int):
        self.input_start.setText(format_frequency_sweep(start))
        self.input_start.textEdited.emit(self.input_start.text())
        self.updated.emit(self)

    def get_end(self) -> int:
        if content=="KHz":
           return parse_frequency(self.input_end.text()+"Khz") 
        elif content=="MHz":
           return parse_frequency(self.input_end.text()+"Mhz")
        elif content=="GHz":
           return parse_frequency(self.input_end.text()+"Ghz")
        else: 
           return parse_frequency(self.input_end.text())
           

    def set_end(self, end: int):
        self.input_end.setText(format_frequency_sweep(end))
        self.input_end.textEdited.emit(self.input_end.text())
        self.updated.emit(self)

    def get_center(self) -> int:
        return parse_frequency(self.input_center.text())

    def set_center(self, center: int):
        self.input_center.setText(format_frequency_sweep(center))
        self.input_center.textEdited.emit(self.input_center.text())
        self.updated.emit(self)

    def get_segments(self) -> int:
        try:
            result = int(self.input_segments.text())
        except ValueError:
            result = 1
        return result

    def get_stepsize(self) -> int:

        if self.fstep < 1:
            return 1
        else:
            return 0


    def set_segments(self, count: int):
        self.input_segments.setText(str(count))
        self.input_segments.textEdited.emit(self.input_segments.text())
        self.updated.emit(self)

    def get_span(self) -> int:
        return parse_frequency(self.input_span.text())

    def set_span(self, span: int):
        self.input_span.setText((span))
        self.input_span.setText(format_frequency_sweep(span))
        self.input_span.textEdited.emit(self.input_span.text())
        self.updated.emit(self)

    def toggle_settings(self, disabled):
        self.input_start.setDisabled(disabled)
        self.input_end.setDisabled(disabled)
        self.input_span.setDisabled(disabled)
        self.input_center.setDisabled(disabled)
        self.input_segments.setDisabled(disabled)

    def update_center_span(self):
        fstart = self.get_start()
        fstop = self.get_end()
        fspan = fstop - fstart
        fcenter = ((fstart + fstop) / 2)
        
        if fspan < 0 or fstart < 0 or fstop < 0:
            return
        else:
            self.input_span.setText(fspan)
        self.input_center.setText(fcenter)
        self.update_sweep()

        
    def update_start_end(self):###al dejar fijo la central y el intervalo, no modifique esta función
         
        fcenter = self.get_center() 
        fspan = self.get_span()
        
        if fspan < 0 or fcenter < 0:
            return
        fstart = round(fcenter - fspan / 2)
        fstop = round(fcenter + fspan / 2)
        if fstart < 0 or fstop < 0:
            return
        self.input_start.setText(fstart)
        self.input_end.setText(fstop)
        self.update_sweep()

    def update_step_size(self):
        fspan = self.get_span()
        if fspan < 0:
            return
        segments = self.get_segments()
        if segments > 0:
            self.fstep = fspan / (segments * self.app.vna.datapoints - 1)
            self.label_step.setText(
                f"{format_frequency_short(self.fstep)}/step")
        self.update_sweep()

    def update_sweep(self):
        sweep = self.app.sweep
        with sweep.lock:
            sweep.start = self.get_start()
            sweep.end = self.get_end()
            sweep.segments = self.get_segments()
            sweep.points = self.app.vna.datapoints
            #sweep.points = 1023
  
    def texto_cambiado_1(self, texto):
            global content
            content=self.combo_FF.currentText()
            print(content)
            
