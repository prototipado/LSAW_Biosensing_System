import math
from typing import List

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import pyqtSignal

from NanoVNASaver import RFTools
from NanoVNASaver.Formatting import (
    format_capacitance,
    format_complex_adm,
    format_complex_imp,
    format_frequency_space,
    format_gain,
    format_mag_Z,
    format_phase_Z,
    format_phase_Y,
    format_mag_Y,
    format_conduct,
    format_group_delay,
    format_complex_s,
    format_inductance,
    format_magnitude,
    format_phase,
    format_q_factor,
    format_resistance,
    format_vswr,
    format_wavelength,
    parse_frequency,
)
from NanoVNASaver.Inputs import MarkerFrequencyInputWidget as FrequencyInput
from NanoVNASaver.Marker.Values import TYPES, Value, default_label_ids

COLORS = (
    QtGui.QColor(QtCore.Qt.darkGray),
    QtGui.QColor(255, 0, 0),
    QtGui.QColor(0, 255, 0),
    QtGui.QColor(0, 0, 255),
    QtGui.QColor(0, 255, 255),
    QtGui.QColor(255, 0, 255),
    QtGui.QColor(255, 255, 0),
)


class MarkerLabel(QtWidgets.QLabel):
    def __init__(self, name):
        super().__init__("")
        self.name = name


class Marker(QtCore.QObject, Value):
    _instances = 0
    coloredText = True
    location = -1
    returnloss_is_positive = False
    updated = pyqtSignal(object)
    active_labels = []

    @classmethod
    def count(cls):
        return cls._instances

    def __init__(self, name: str = "", qsettings: QtCore.QSettings = None):
        super().__init__()
        self.qsettings = qsettings
        self.name = name
        self.color = QtGui.QColor()
        self.index = 0

        if self.qsettings:
            Marker._instances += 1
            Marker.active_labels = self.qsettings.value(
                "MarkerFields", defaultValue=default_label_ids())
            self.index = Marker._instances

        if not self.name:
            self.name = f"Marcador {Marker._instances}"

        self.frequencyInput = FrequencyInput()
        self.frequencyInput.setMinimumHeight(20)
        self.frequencyInput.setAlignment(QtCore.Qt.AlignRight)
        self.frequencyInput.editingFinished.connect(
            lambda: self.setFrequency(
                parse_frequency(self.frequencyInput.text())))

        ###############################################################
        # Data display labels
        ###############################################################

        self.label = {
            label.label_id: MarkerLabel(label.name) for label in TYPES
        }
        self.label['actualfreq'].setMinimumWidth(100)
        #self.label['returnloss'].setMinimumWidth(80)

        ###############################################################
        # Marker control layout
        ###############################################################

        self.btnColorPicker = QtWidgets.QPushButton("█")
        self.btnColorPicker.setMinimumHeight(20)
        self.btnColorPicker.setFixedWidth(20)
        self.btnColorPicker.clicked.connect(
            lambda: self.setColor(QtWidgets.QColorDialog.getColor(
                self.color, options=QtWidgets.QColorDialog.ShowAlphaChannel))
        )
        self.isMouseControlledRadioButton = QtWidgets.QRadioButton()

        self.layout = QtWidgets.QHBoxLayout()
        self.layout.addWidget(self.frequencyInput)
        self.layout.addWidget(self.btnColorPicker)
        self.layout.addWidget(self.isMouseControlledRadioButton)

        ###############################################################
        # Data display layout
        ###############################################################

        self.group_box = QtWidgets.QGroupBox(self.name)
        self.group_box.setMaximumWidth(340)
        box_layout = QtWidgets.QHBoxLayout(self.group_box)

        try:
            self.setColor(
                self.qsettings.value(
                    f"Marker{self.count()}Color", COLORS[self.count()]))
        except AttributeError:  # happens when qsettings == None
            self.setColor(COLORS[1])
        except IndexError:
            self.setColor(COLORS[0])

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.VLine)

        #line only if more then 3 selected
        self.left_form = QtWidgets.QFormLayout()
        self.left_form.setVerticalSpacing(0)
        self.right_form = QtWidgets.QFormLayout()
        self.right_form.setVerticalSpacing(0)
        box_layout.addLayout(self.left_form)
        #box_layout.addWidget(line)
        box_layout.addLayout(self.right_form)

        self.buildForm()

    def __del__(self):
        if self.qsettings:
            Marker._instances -= 1

    def _add_active_labels(self, label_id, form):
        if label_id in self.label:
            form.addRow(
                f"{self.label[label_id].name}:", self.label[label_id])
            self.label[label_id].show()

    def _size_str(self) -> str:
        return str(self.group_box.font().pointSize())

    def update_settings(self):
        self.qsettings.setValue(f"Marker{self.index}Color", self.color)

    def setScale(self, scale):
        self.group_box.setMaximumWidth(int(340 * scale))
        self.label['actualfreq'].setMinimumWidth(int(100 * scale))
        self.label['actualfreq'].setMinimumWidth(int(100 * scale))
        #self.label['returnloss'].setMinimumWidth(int(80 * scale))
        if self.coloredText:
            color_string = QtCore.QVariant(self.color)
            color_string.convert(QtCore.QVariant.String)
            self.group_box.setStyleSheet(
                f"QGroupBox {{ color: {color_string.value()}; "
                f"font-size: {self._size_str()}}};"
            )
        else:
            self.group_box.setStyleSheet(
                f"QGroupBox {{ font-size: {self._size_str()}}};"
            )

    def buildForm(self):
        while self.left_form.count() > 0:
            old_row = self.left_form.takeRow(0)
            old_row.fieldItem.widget().hide()
            old_row.labelItem.widget().hide()

        while self.right_form.count() > 0:
            old_row = self.right_form.takeRow(0)
            old_row.fieldItem.widget().hide()
            old_row.labelItem.widget().hide()

        if len(self.active_labels) <= 3:
            for label_id in self.active_labels:
                self._add_active_labels(label_id, self.left_form)
        else:
            left_half = math.ceil(len(self.active_labels) / 2)
            right_half = len(self.active_labels)
            for i in range(left_half):
                label_id = self.active_labels[i]
                self._add_active_labels(label_id, self.left_form)
            for i in range(left_half, right_half):
                label_id = self.active_labels[i]
                self._add_active_labels(label_id, self.right_form)

    def setFrequency(self, frequency):
        self.freq = parse_frequency(frequency)
        self.frequencyInput.setText(frequency)
        self.updated.emit(self)

    def setFieldSelection(self, fields):
        self.active_labels = fields[:]
        self.buildForm()

    def setColor(self, color):
        if color.isValid():
            self.color = color
            p = self.btnColorPicker.palette()
            p.setColor(QtGui.QPalette.ButtonText, self.color)
            self.btnColorPicker.setPalette(p)
        if self.coloredText:
            color_string = QtCore.QVariant(color)
            color_string.convert(QtCore.QVariant.String)
            self.group_box.setStyleSheet(
                f"QGroupBox {{ color: {color_string.value()}; "
                f"font-size: {self._size_str()}}};"
            )
        else:
            self.group_box.setStyleSheet(
                f"QGroupBox {{ font-size: {self._size_str()}}};"
            )

    def setColoredText(self, colored_text):
        self.coloredText = colored_text
        self.setColor(self.color)

    def getRow(self):
        return QtWidgets.QLabel(self.name), self.layout

    def findLocation(self, data: List[RFTools.Datapoint]):
        self.location = -1
        self.frequencyInput.nextFrequency = -1
        self.frequencyInput.previousFrequency = -1
        datasize = len(data)
        if datasize == 0:
            # Set the frequency before loading any data
            return

        min_freq = data[0].freq
        max_freq = data[-1].freq
        lower_stepsize = data[1].freq - data[0].freq
        upper_stepsize = data[-1].freq - data[-2].freq

        # We are outside the bounds of the data, so we can't put in a marker
        if (self.freq + lower_stepsize / 2 < min_freq or
                self.freq - upper_stepsize / 2 > max_freq):
            return

        min_distance = max_freq
        for i, item in enumerate(data):
            if abs(item.freq - self.freq) <= min_distance:
                min_distance = abs(item.freq - self.freq)
            else:
                # We have now started moving away from the nearest point
                self.location = i - 1
                if i < datasize:
                    self.frequencyInput.nextFrequency = item.freq
                if i >= 2:
                    self.frequencyInput.previousFrequency = data[i - 2].freq
                return
        # If we still didn't find a best spot, it was the last value
        self.location = datasize - 1
        self.frequencyInput.previousFrequency = data[-2].freq

    def get_data_layout(self) -> QtWidgets.QGroupBox:
        return self.group_box

    def resetLabels(self):
        for v in self.label.values():
            v.setText("")

    def updateLabels(self,
                     s11: List[RFTools.Datapoint],
                     s21: List[RFTools.Datapoint]):
        if not s11:
            return
        if self.location == -1:  # initial position
            try:
                location = (self.index - 1) / (
                    (self._instances - 1) * (len(s11) - 1))
                self.location = int(location)
            except ZeroDivisionError:
                self.location = 0
        try:
            _s11 = s11[self.location]
            _s21 = s21[self.location]
        except IndexError:
            self.location = 0
            return

        self.frequencyInput.setText(_s11.freq)
        self.store(self.location, s11, s21)

        imp = _s11.impedance()
        cap_str = format_capacitance(
            RFTools.impedance_to_capacitance(imp, _s11.freq))
        ind_str = format_inductance(
            RFTools.impedance_to_inductance(imp, _s11.freq))

        imp_p = RFTools.serial_to_parallel(imp)
        cap_p_str = format_capacitance(
            RFTools.impedance_to_capacitance(imp_p, _s11.freq))
        ind_p_str = format_inductance(
            RFTools.impedance_to_inductance(imp_p, _s11.freq))

        x_str = cap_str if imp.imag < 0 else ind_str
        x_p_str = cap_p_str if imp_p.imag < 0 else ind_p_str

        self.label["actualfreq"].setText(format_frequency_space(_s11.freq))
        _s21 = s21[self.location]
        self.label["s21gain"].setText(format_gain(_s21.gain))
        if len(s21) == len(s11):
            _s21 = s21[self.location]
            self.label["s21gain"].setText(format_gain(_s21.gain))
            self.label["s21groupdelay"].setText(
                format_group_delay(RFTools.groupDelay(s21, self.location) / 2) )
            self.label["s21phase"].setText(format_phase(_s21.phase))


