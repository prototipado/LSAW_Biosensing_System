import logging
from functools import partial
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QIntValidator

from NanoVNASaver.Formatting import (
    format_frequency_short, format_frequency_sweep,
)
from NanoVNASaver.Settings.Sweep import SweepMode

logger = logging.getLogger(__name__)


class SweepSettingsWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app
        self.padding = 0

        self.setWindowTitle("Configuración de barrido")
        self.setWindowIcon(self.app.icon)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        #layout.addWidget(self.title_box())
        layout.addWidget(self.settings_box())
        # We can only populate this box after the VNA has been connected.
        self._power_box = QtWidgets.QGroupBox("Potencia")
        self._power_layout = QtWidgets.QFormLayout(self._power_box)
        #layout.addWidget(self._power_box)
        #layout.addWidget(self.sweep_box())
        #self.update_band()

    def title_box(self):
        box = QtWidgets.QGroupBox("Titulo del barrido")
        layout = QtWidgets.QFormLayout(box)

        input_title = QtWidgets.QLineEdit(self.app.sweep.properties.name)
        input_title.setMinimumHeight(20)
        input_title.editingFinished.connect(
            lambda: self.update_title(input_title.text()))
        layout.addRow(input_title)
        return box

    def settings_box(self) -> 'QtWidgets.QWidget':
        box = QtWidgets.QGroupBox("Ajustes")
        layout = QtWidgets.QFormLayout(box)

        # Sweep Mode
        sweep_btn_layout = QtWidgets.QHBoxLayout()

        self.input_nsweeps = QtWidgets.QLineEdit()
        self.input_nsweeps.setMinimumHeight(30)
        self.input_nsweeps.setValidator(QIntValidator())
        self.input_nsweeps.setEnabled(False)

        self.barrido_simple = QtWidgets.QRadioButton("Barrido Simple")
        self.barrido_simple.setMinimumHeight(20)
        self.barrido_simple.clicked.connect(lambda : self.input_nsweeps.setEnabled(False))
        sweep_btn_layout.addWidget(self.barrido_simple)

        self.barridos_sucesivos = QtWidgets.QRadioButton("Barridos sucesivos")
        self.barridos_sucesivos.setMinimumHeight(20)
        self.barridos_sucesivos.clicked.connect(lambda : self.input_nsweeps.setEnabled(True))
        sweep_btn_layout.addWidget(self.barridos_sucesivos)

        sweep_btn_layout.addWidget(self.input_nsweeps)
        layout.addRow(sweep_btn_layout)

        metodo_btn_layout = QtWidgets.QHBoxLayout()

        self.amph = QtWidgets.QCheckBox("Buscar Resonancia")
        self.barrido_simple.setMinimumHeight(20)
        metodo_btn_layout.addWidget(self.amph)

        self.anf = QtWidgets.QCheckBox("Analizar")
        self.anf.setMinimumHeight(20)
        metodo_btn_layout.addWidget(self.anf)

        layout.addRow((metodo_btn_layout))


        ok_btn_layout = QtWidgets.QHBoxLayout()

        self.ok_bt = QtWidgets.QPushButton("Confirmar")
        self.ok_bt.setFixedHeight(20)
        self.ok_bt.clicked.connect(lambda: self.update_mode())
        self.ok_bt.setShortcut(QtCore.Qt.Key_W | QtCore.Qt.CTRL)
        ok_btn_layout.addWidget(self.ok_bt)

        layout.addRow(ok_btn_layout)

        return box
    def vna_connected(self):
        while self._power_layout.rowCount():
            self._power_layout.removeRow(0)
        for freq_range, power_descs in self.app.vna.txPowerRanges:
            power_sel = QtWidgets.QComboBox()
            power_sel.addItems(power_descs)
            power_sel.currentTextChanged.connect(
                partial(self.update_tx_power, freq_range))
            self._power_layout.addRow("TX potencia {}..{}".format(
                *map(format_frequency_short, freq_range)), power_sel)

    def update_band(self, apply: bool = False):
        logger.debug("actualizar_banda(%s)", apply)
        index_start = self.band_list.model().index(
            self.band_list.currentIndex(), 1)
        index_stop = self.band_list.model().index(
            self.band_list.currentIndex(), 2)
        start = int(self.band_list.model().data(
            index_start, QtCore.Qt.ItemDataRole).value())
        stop = int(self.band_list.model().data(
            index_stop, QtCore.Qt.ItemDataRole).value())

        if self.padding > 0:
            span = stop - start
            start -= round(span * self.padding / 100)
            start = max(1, start)
            stop += round(span * self.padding / 100)

        self.band_label.setText(
            f"Sweep span: {format_frequency_short(start)}"
            f" to {format_frequency_short(stop)}")

        if not apply:
            return

        self.app.sweep_control.input_start.setText(
            format_frequency_sweep(start))
        self.app.sweep_control.input_end.setText(
            format_frequency_sweep(stop))
        self.app.sweep_control.input_end.textEdited.emit(
            self.app.sweep_control.input_end.text())

    def update_attenuator(self, value: 'QtWidgets.QLineEdit'):
        try:
            att = float(value.text())
            assert att >= 0
        except (ValueError, AssertionError):
            logger.warning("Values for attenuator are absolute and with no"
                           " minus sign, resetting.")
            att = 0
        logger.debug("Attenuator %sdB inline with S21 input", att)
        value.setText(str(att))
        self.app.s21att = att

    def update_averaging(self,
                         averages: 'QtWidgets.QLineEdit',
                         truncs: 'QtWidgets.QLineEdit'):
        try:
            amount = int(averages.text())
            truncates = int(truncs.text())
            assert amount > 0
            assert truncates >= 0
            assert amount > truncates
        except (AssertionError, ValueError):
            logger.warning("Illegal averaging values, set default")
            amount = 3
            truncates = 0
        logger.debug("update_averaging(%s, %s)", amount, truncates)
        averages.setText(str(amount))
        truncs.setText(str(truncates))
        with self.app.sweep.lock:
            self.app.sweep.properties.averages = (amount, truncates)

    def update_logarithmic(self, logarithmic: bool):
        logger.debug("update_logarithmic(%s)", logarithmic)
        with self.app.sweep.lock:
            self.app.sweep.properties.logarithmic = logarithmic

    def update_mode(self):
        #logger.debug("update_mode(%s)", mode)

        if self.amph.isChecked() and self.anf.isChecked():
            QtWidgets.QMessageBox.warning(self, "Aviso", "Elija UN método de análisis")

        else :
                if self.amph.isChecked() :
                    with self.app.sweep.lock:
                        self.app.sweep.properties.anmode = 0

                if self.anf.isChecked() :
                    with self.app.sweep.lock:
                        self.app.sweep.properties.anmode = 1


                if self.barrido_simple.isChecked():

                    with self.app.sweep.lock:
                        self.app.sweep.properties.mode = SweepMode.SINGLE
                    QtWidgets.QMessageBox.warning(self, "Aviso", "Datos Cargados")

                elif self.barridos_sucesivos.isChecked():

                        with self.app.sweep.lock:
                            self.app.sweep.properties.mode = SweepMode.CONTINOUS

                        if not self.input_nsweeps.text() :
                            QtWidgets.QMessageBox.warning(self, "Error", "Número de Barridos Incorrecto")
                            return
                        else:
                            number = int(self.input_nsweeps.text())
                            if number<1:
                                QtWidgets.QMessageBox.warning(self, "Error", "Número de Barridos Incorrecto")
                                return
                            else:
                                self.app.sweep.properties.nsweeps = number
                                QtWidgets.QMessageBox.warning(self, "Aviso", "Datos Cargados")
                else :
                    QtWidgets.QMessageBox.warning(self, "Error", "Seleccione tipo de Barrido")
                    return


    def update_padding(self, padding: int):
        logger.debug("update_padding(%s)", padding)
        self.padding = padding
        self.update_band()

    def update_title(self, title: str = ""):
        logger.debug("update_title(%s)", title)
        with self.app.sweep.lock:
            self.app.sweep.properties.name = title
        self.app.update_sweep_title()

    def update_tx_power(self, freq_range, power_desc):
        logger.debug("update_tx_power(%r)", power_desc)
        with self.app.sweep.lock:
            self.app.vna.setTXPower(freq_range, power_desc)
