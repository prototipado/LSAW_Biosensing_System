import logging
from functools import partial

from PyQt5 import QtWidgets, QtCore

from NanoVNASaver.Calibration import Calibration
from NanoVNASaver.Settings.Sweep import SweepMode

logger = logging.getLogger(__name__)


def _format_cal_label(size: int, prefix: str = "Set") -> str:
    return f"{prefix} ({size} points)"


class CalibrationWindow(QtWidgets.QWidget):
    nextStep = -1

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setMinimumWidth(450)
        self.setWindowTitle("Calibración")
        self.setWindowIcon(self.app.icon)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.MinimumExpanding)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)



        top_layout = QtWidgets.QHBoxLayout()
        left_layout = QtWidgets.QVBoxLayout()
        right_layout = QtWidgets.QVBoxLayout()
        top_layout.addLayout(left_layout)
        top_layout.addLayout(right_layout)
        self.setLayout(top_layout)

        calibration_status_group = QtWidgets.QGroupBox("Calibración activa")
        calibration_status_layout = QtWidgets.QFormLayout()
        self.calibration_status_label = QtWidgets.QLabel("Sin calibrar")
        self.calibration_source_label = QtWidgets.QLabel("-----")
        calibration_status_layout.addRow("Calibración:",
                                         self.calibration_status_label)
        calibration_status_layout.addRow("Fuente:",
                                         self.calibration_source_label)
        calibration_status_group.setLayout(calibration_status_layout)
        left_layout.addWidget(calibration_status_group)

        calibration_control_group = QtWidgets.QGroupBox("Calibración")
        calibration_control_layout = QtWidgets.QFormLayout(
            calibration_control_group)
        cal_btn = {}
        self.cal_label = {}
        for label_name in Calibration.CAL_NAMES:
            self.cal_label[label_name] = QtWidgets.QLabel("Sin calibrar")
            cal_btn[label_name] = QtWidgets.QPushButton(
                label_name.capitalize())
            cal_btn[label_name].setMinimumHeight(20)
            cal_btn[label_name].clicked.connect(
                partial(self.manual_save, label_name))
            #calibration_control_layout.addRow(
             #   cal_btn[label_name], self.cal_label[label_name])

        self.input_offset_delay = QtWidgets.QDoubleSpinBox()
        self.input_offset_delay.setMinimumHeight(20)
        self.input_offset_delay.setValue(0)
        self.input_offset_delay.setSuffix(" ps")
        self.input_offset_delay.setAlignment(QtCore.Qt.AlignRight)
        self.input_offset_delay.valueChanged.connect(self.setOffsetDelay)
        self.input_offset_delay.setRange(-10e6, 10e6)

        calibration_control_layout.addRow(QtWidgets.QLabel(""))
      #  calibration_control_layout.addRow(
      #     "Offset delay", self.input_offset_delay)

        self.btn_automatic = QtWidgets.QPushButton("Asistente de calibración")
        self.btn_automatic.setMinimumHeight(20)
        calibration_control_layout.addRow(self.btn_automatic)
        self.btn_automatic.clicked.connect(self.automaticCalibration)

        apply_reset_layout = QtWidgets.QHBoxLayout()

        btn_apply = QtWidgets.QPushButton("Aplicar")
        btn_apply.setMinimumHeight(20)
        btn_apply.clicked.connect(self.calculate)

        btn_reset = QtWidgets.QPushButton("Reiniciar")
        btn_reset.setMinimumHeight(20)
        btn_reset.clicked.connect(self.reset)

       # apply_reset_layout.addWidget(btn_apply)
        apply_reset_layout.addWidget(btn_reset)

        calibration_control_layout.addRow(apply_reset_layout)

        left_layout.addWidget(calibration_control_group)

        calibration_notes_group = QtWidgets.QGroupBox("Notes")
        #calibration_notes_layout = QtWidgets.QVBoxLayout(
            #calibration_notes_group)
        self.notes_textedit = QtWidgets.QPlainTextEdit()
        #calibration_notes_layout.addWidget(self.notes_textedit)

        #left_layout.addWidget(calibration_notes_group)

        file_box = QtWidgets.QGroupBox("Archivos")
        file_layout = QtWidgets.QFormLayout(file_box)
        btn_save_file = QtWidgets.QPushButton("Guardar calibración")
        btn_save_file.setMinimumHeight(20)
        btn_save_file.clicked.connect(lambda: self.saveCalibration())
        btn_load_file = QtWidgets.QPushButton("Cargar calibración")
        btn_load_file.setMinimumHeight(20)
        btn_load_file.clicked.connect(lambda: self.loadCalibration())

        save_load_layout = QtWidgets.QHBoxLayout()
        save_load_layout.addWidget(btn_save_file)
        save_load_layout.addWidget(btn_load_file)

        file_layout.addRow(save_load_layout)

        left_layout.addWidget(file_box)

        #cal_standard_box = QtWidgets.QGroupBox("Calibration standards")
        #cal_standard_layout = QtWidgets.QFormLayout(cal_standard_box)
        self.use_ideal_values = QtWidgets.QCheckBox("Use ideal values")
        self.use_ideal_values.setChecked(True)
        self.use_ideal_values.stateChanged.connect(self.idealCheckboxChanged)
        #cal_standard_layout.addRow(self.use_ideal_values)

        self.cal_short_box = QtWidgets.QGroupBox("Short")
        cal_short_form = QtWidgets.QFormLayout(self.cal_short_box)
        self.cal_short_box.setDisabled(True)
        self.short_l0_input = QtWidgets.QLineEdit("0")
        self.short_l0_input.setMinimumHeight(20)
        self.short_l1_input = QtWidgets.QLineEdit("0")
        self.short_l1_input.setMinimumHeight(20)
        self.short_l2_input = QtWidgets.QLineEdit("0")
        self.short_l2_input.setMinimumHeight(20)
        self.short_l3_input = QtWidgets.QLineEdit("0")
        self.short_l3_input.setMinimumHeight(20)
        self.short_length = QtWidgets.QLineEdit("0")
        self.short_length.setMinimumHeight(20)
        cal_short_form.addRow("L0 (H(e-12))", self.short_l0_input)
        cal_short_form.addRow("L1 (H(e-24))", self.short_l1_input)
        cal_short_form.addRow("L2 (H(e-33))", self.short_l2_input)
        cal_short_form.addRow("L3 (H(e-42))", self.short_l3_input)
        cal_short_form.addRow("Offset Delay (ps)", self.short_length)

        self.cal_open_box = QtWidgets.QGroupBox("Open")
        cal_open_form = QtWidgets.QFormLayout(self.cal_open_box)
        self.cal_open_box.setDisabled(True)
        self.open_c0_input = QtWidgets.QLineEdit("50")
        self.open_c0_input.setMinimumHeight(20)
        self.open_c1_input = QtWidgets.QLineEdit("0")
        self.open_c1_input.setMinimumHeight(20)
        self.open_c2_input = QtWidgets.QLineEdit("0")
        self.open_c2_input.setMinimumHeight(20)
        self.open_c3_input = QtWidgets.QLineEdit("0")
        self.open_c3_input.setMinimumHeight(20)
        self.open_length = QtWidgets.QLineEdit("0")
        self.open_length.setMinimumHeight(20)
        cal_open_form.addRow("C0 (F(e-15))", self.open_c0_input)
        cal_open_form.addRow("C1 (F(e-27))", self.open_c1_input)
        cal_open_form.addRow("C2 (F(e-36))", self.open_c2_input)
        cal_open_form.addRow("C3 (F(e-45))", self.open_c3_input)
        cal_open_form.addRow("Offset Delay (ps)", self.open_length)

        self.cal_load_box = QtWidgets.QGroupBox("Load")
        cal_load_form = QtWidgets.QFormLayout(self.cal_load_box)
        self.cal_load_box.setDisabled(True)
        self.load_resistance = QtWidgets.QLineEdit("50")
        self.load_resistance.setMinimumHeight(20)
        self.load_inductance = QtWidgets.QLineEdit("0")
        self.load_inductance.setMinimumHeight(20)
        self.load_capacitance = QtWidgets.QLineEdit("0")
        self.load_capacitance.setMinimumHeight(20)
        # self.load_capacitance.setDisabled(True)  # Not yet implemented
        self.load_length = QtWidgets.QLineEdit("0")
        self.load_length.setMinimumHeight(20)
        cal_load_form.addRow("Resistance (\N{OHM SIGN})", self.load_resistance)
        cal_load_form.addRow("Inductance (H(e-12))", self.load_inductance)
        cal_load_form.addRow("Capacitance (F(e-15))", self.load_capacitance)
        cal_load_form.addRow("Offset Delay (ps)", self.load_length)

        self.cal_through_box = QtWidgets.QGroupBox("Through")
        cal_through_form = QtWidgets.QFormLayout(self.cal_through_box)
        self.cal_through_box.setDisabled(True)
        self.through_length = QtWidgets.QLineEdit("0")
        self.through_length.setMinimumHeight(20)
        cal_through_form.addRow("Offset Delay (ps)", self.through_length)

        #cal_standard_layout.addWidget(self.cal_short_box)
        #cal_standard_layout.addWidget(self.cal_open_box)
        #cal_standard_layout.addWidget(self.cal_load_box)
        #cal_standard_layout.addWidget(self.cal_through_box)

        self.cal_standard_save_box = QtWidgets.QGroupBox("Saved settings")
        cal_standard_save_layout = QtWidgets.QVBoxLayout(
            self.cal_standard_save_box)
        self.cal_standard_save_box.setDisabled(True)

        self.cal_standard_save_selector = QtWidgets.QComboBox()
        self.cal_standard_save_selector.setMinimumHeight(20)
        self.listCalibrationStandards()
#        cal_standard_save_layout.addWidget(self.cal_standard_save_selector)
 #       cal_standard_save_button_layout = QtWidgets.QHBoxLayout()
        btn_save_standard = QtWidgets.QPushButton("Save")
        btn_save_standard.setMinimumHeight(20)
        btn_save_standard.clicked.connect(self.saveCalibrationStandard)
        btn_load_standard = QtWidgets.QPushButton("Load")
        btn_load_standard.setMinimumHeight(20)
        btn_load_standard.clicked.connect(self.loadCalibrationStandard)
        btn_delete_standard = QtWidgets.QPushButton("Delete")
        btn_delete_standard.setMinimumHeight(20)
        btn_delete_standard.clicked.connect(self.deleteCalibrationStandard)
      #  cal_standard_save_button_layout.addWidget(btn_load_standard)
      #  cal_standard_save_button_layout.addWidget(btn_save_standard)
      #  cal_standard_save_button_layout.addWidget(btn_delete_standard)
      #  cal_standard_save_layout.addLayout(cal_standard_save_button_layout)

       # cal_standard_layout.addWidget(self.cal_standard_save_box)
       # right_layout.addWidget(cal_standard_box)

    def checkExpertUser(self):
        if not self.app.settings.value("ExpertCalibrationUser", False, bool):
            response = QtWidgets.QMessageBox.question(
                self, "Are you sure?",
                (
                    "Use of the manual calibration buttons is non-intuitive,"
                    " and primarily suited for users with very specialized"
                    " needs. The buttons do not sweep for you, nor do"
                    " they interact with the NanoVNA calibration.\n\n"
                    "If you are trying to do a calibration of the NanoVNA, do"
                    "so on the device itself instead. If you are trying to do"
                    "a calibration with NanoVNA-Saver, use the Calibration"
                    "Assistant if possible.\n\n"
                    "If you are certain you know what you are doing, click"
                    " Yes."
                ),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                QtWidgets.QMessageBox.Cancel)

            if response == QtWidgets.QMessageBox.Yes:
                self.app.settings.setValue("ExpertCalibrationUser", True)
                return True
            return False
        return True

    def cal_save(self, name: str):
        if name in {"through", "isolation"}:
            self.app.calibration.insert(name, self.app.data.s21)
        else:
            self.app.calibration.insert(name, self.app.data.s11)
        self.cal_label[name].setText(
            _format_cal_label(len(self.app.data.s11)))

    def manual_save(self, name: str):
        if self.checkExpertUser():
            self.cal_save(name)

    def listCalibrationStandards(self):
        self.cal_standard_save_selector.clear()
        num_standards = self.app.settings.beginReadArray(
            "CalibrationStandards")
        for i in range(num_standards):
            self.app.settings.setArrayIndex(i)
            name = self.app.settings.value("Name", defaultValue="INVALID NAME")
            self.cal_standard_save_selector.addItem(name, userData=i)
        self.app.settings.endArray()
        self.cal_standard_save_selector.addItem("New", userData=-1)
        self.cal_standard_save_selector.setCurrentText("New")

    def saveCalibrationStandard(self):
        num_standards = self.app.settings.beginReadArray(
            "CalibrationStandards")
        self.app.settings.endArray()

        if self.cal_standard_save_selector.currentData() == -1:
            # New cal standard
            # Get a name
            name, selected = QtWidgets.QInputDialog.getText(
                self, "Calibration standard name", "Enter name to save as")
            if not selected or not name:
                return
            write_num = num_standards
            num_standards += 1
        else:
            write_num = self.cal_standard_save_selector.currentData()
            name = self.cal_standard_save_selector.currentText()

        self.app.settings.beginWriteArray(
            "CalibrationStandards", num_standards)
        self.app.settings.setArrayIndex(write_num)
        self.app.settings.setValue("Name", name)

        self.app.settings.setValue("ShortL0", self.short_l0_input.text())
        self.app.settings.setValue("ShortL1", self.short_l1_input.text())
        self.app.settings.setValue("ShortL2", self.short_l2_input.text())
        self.app.settings.setValue("ShortL3", self.short_l3_input.text())
        self.app.settings.setValue("ShortDelay", self.short_length.text())

        self.app.settings.setValue("OpenC0", self.open_c0_input.text())
        self.app.settings.setValue("OpenC1", self.open_c1_input.text())
        self.app.settings.setValue("OpenC2", self.open_c2_input.text())
        self.app.settings.setValue("OpenC3", self.open_c3_input.text())
        self.app.settings.setValue("OpenDelay", self.open_length.text())

        self.app.settings.setValue("LoadR", self.load_resistance.text())
        self.app.settings.setValue("LoadL", self.load_inductance.text())
        self.app.settings.setValue("LoadC", self.load_capacitance.text())
        self.app.settings.setValue("LoadDelay", self.load_length.text())

        self.app.settings.setValue("ThroughDelay", self.through_length.text())

        self.app.settings.endArray()
        self.app.settings.sync()
        self.listCalibrationStandards()
        self.cal_standard_save_selector.setCurrentText(name)

    def loadCalibrationStandard(self):
        if self.cal_standard_save_selector.currentData() == -1:
            return
        read_num = self.cal_standard_save_selector.currentData()
        logger.debug("Loading calibration no %d", read_num)
        self.app.settings.beginReadArray("CalibrationStandards")
        self.app.settings.setArrayIndex(read_num)

        name = self.app.settings.value("Name")
        logger.info("Loading: %s", name)

        self.short_l0_input.setText(str(self.app.settings.value("ShortL0", 0)))
        self.short_l1_input.setText(str(self.app.settings.value("ShortL1", 0)))
        self.short_l2_input.setText(str(self.app.settings.value("ShortL2", 0)))
        self.short_l3_input.setText(str(self.app.settings.value("ShortL3", 0)))
        self.short_length.setText(
            str(self.app.settings.value("ShortDelay", 0)))

        self.open_c0_input.setText(str(self.app.settings.value("OpenC0", 50)))
        self.open_c1_input.setText(str(self.app.settings.value("OpenC1", 0)))
        self.open_c2_input.setText(str(self.app.settings.value("OpenC2", 0)))
        self.open_c3_input.setText(str(self.app.settings.value("OpenC3", 0)))
        self.open_length.setText(str(self.app.settings.value("OpenDelay", 0)))

        self.load_resistance.setText(str(self.app.settings.value("LoadR", 50)))
        self.load_inductance.setText(str(self.app.settings.value("LoadL", 0)))
        self.load_capacitance.setText(str(self.app.settings.value("LoadC", 0)))
        self.load_length.setText(str(self.app.settings.value("LoadDelay", 0)))

        self.through_length.setText(
            str(self.app.settings.value("ThroughDelay", 0)))

        self.app.settings.endArray()

    def deleteCalibrationStandard(self):
        if self.cal_standard_save_selector.currentData() == -1:
            return
        delete_num = self.cal_standard_save_selector.currentData()
        logger.debug("Deleting calibration no %d", delete_num)
        num_standards = self.app.settings.beginReadArray(
            "CalibrationStandards")
        self.app.settings.endArray()

        logger.debug("Number of standards known: %d", num_standards)

        if num_standards == 1:
            logger.debug("Only one standard known")
            self.app.settings.beginWriteArray("CalibrationStandards", 0)
            self.app.settings.endArray()
        else:
            names = []

            shortL0 = []
            shortL1 = []
            shortL2 = []
            shortL3 = []
            shortDelay = []

            openC0 = []
            openC1 = []
            openC2 = []
            openC3 = []
            openDelay = []

            loadR = []
            loadL = []
            loadC = []
            loadDelay = []

            throughDelay = []

            self.app.settings.beginReadArray("CalibrationStandards")
            for i in range(num_standards):
                if i == delete_num:
                    continue
                self.app.settings.setArrayIndex(i)
                names.append(self.app.settings.value("Name"))

                shortL0.append(self.app.settings.value("ShortL0"))
                shortL1.append(self.app.settings.value("ShortL1"))
                shortL2.append(self.app.settings.value("ShortL2"))
                shortL3.append(self.app.settings.value("ShortL3"))
                shortDelay.append(self.app.settings.value("ShortDelay"))

                openC0.append(self.app.settings.value("OpenC0"))
                openC1.append(self.app.settings.value("OpenC1"))
                openC2.append(self.app.settings.value("OpenC2"))
                openC3.append(self.app.settings.value("OpenC3"))
                openDelay.append(self.app.settings.value("OpenDelay"))

                loadR.append(self.app.settings.value("LoadR"))
                loadL.append(self.app.settings.value("LoadL"))
                loadC.append(self.app.settings.value("LoadC"))
                loadDelay.append(self.app.settings.value("LoadDelay"))

                throughDelay.append(self.app.settings.value("ThroughDelay"))
            self.app.settings.endArray()

            self.app.settings.beginWriteArray("CalibrationStandards")
            self.app.settings.remove("")
            self.app.settings.endArray()

            self.app.settings.beginWriteArray(
                "CalibrationStandards", len(names))
            for i, name in enumerate(names):
                self.app.settings.setArrayIndex(i)
                self.app.settings.setValue("Name", name)

                self.app.settings.setValue("ShortL0", shortL0[i])
                self.app.settings.setValue("ShortL1", shortL1[i])
                self.app.settings.setValue("ShortL2", shortL2[i])
                self.app.settings.setValue("ShortL3", shortL3[i])
                self.app.settings.setValue("ShortDelay", shortDelay[i])

                self.app.settings.setValue("OpenC0", openC0[i])
                self.app.settings.setValue("OpenC1", openC1[i])
                self.app.settings.setValue("OpenC2", openC2[i])
                self.app.settings.setValue("OpenC3", openC3[i])
                self.app.settings.setValue("OpenDelay", openDelay[i])

                self.app.settings.setValue("LoadR", loadR[i])
                self.app.settings.setValue("LoadL", loadL[i])
                self.app.settings.setValue("LoadC", loadC[i])
                self.app.settings.setValue("LoadDelay", loadDelay[i])

                self.app.settings.setValue("ThroughDelay", throughDelay[i])
            self.app.settings.endArray()

        self.app.settings.sync()
        self.listCalibrationStandards()

    def reset(self):
        self.app.calibration = Calibration()
        for label in self.cal_label.values():
            label.setText("Uncalibrated")
        self.calibration_status_label.setText("Calibración por defecto")
        self.calibration_source_label.setText("Dispositivo")
        self.notes_textedit.clear()

        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Saving and displaying raw data.")
            self.app.saveData(self.app.worker.rawData11,
                              self.app.worker.rawData21, self.app.sweepSource)
            self.app.worker.signals.updated.emit()

    def setOffsetDelay(self, value: float):
        logger.debug("New offset delay value: %f ps", value)
        self.app.worker.offsetDelay = value / 1e12
        if len(self.app.worker.rawData11) > 0:
            # There's raw data, so we can get corrected data
            logger.debug("Applying new offset to existing sweep data.")
            self.app.worker.data11, self.app.worker.data21 = \
                self.app.worker.applyCalibration(
                    self.app.worker.rawData11, self.app.worker.rawData21)
            logger.debug("Saving and displaying corrected data.")
            self.app.saveData(self.app.worker.data11,
                              self.app.worker.data21, self.app.sweepSource)
            self.app.worker.signals.updated.emit()

    def calculate(self):
        def _warn_ideal(cal_type: str) -> str:
            return (
                'Invalid data for "{cal_type}" calibration standard.'
                ' Using ideal values.')

        if self.app.sweep_control.btn_stop.isEnabled():
            # Currently sweeping
            self.app.showError(
                "Unable to apply calibration while a sweep is running."
                " Please stop the sweep and try again.")
            return
        if self.use_ideal_values.isChecked():
            self.app.calibration.useIdealShort = True
            self.app.calibration.useIdealOpen = True
            self.app.calibration.useIdealLoad = True
            self.app.calibration.useIdealThrough = True
        else:
            # We are using custom calibration standards
            try:
                self.app.calibration.shortL0 = self.getFloatValue(
                    self.short_l0_input.text()) / 10 ** 12
                self.app.calibration.shortL1 = self.getFloatValue(
                    self.short_l1_input.text()) / 10 ** 24
                self.app.calibration.shortL2 = self.getFloatValue(
                    self.short_l2_input.text()) / 10 ** 33
                self.app.calibration.shortL3 = self.getFloatValue(
                    self.short_l3_input.text()) / 10 ** 42
                self.app.calibration.shortLength = self.getFloatValue(
                    self.short_length.text()) / 10 ** 12
                self.app.calibration.useIdealShort = False
            except ValueError:
                self.app.calibration.useIdealShort = True
                logger.warning(_warn_ideal("short"))

            try:
                self.app.calibration.openC0 = self.getFloatValue(
                    self.open_c0_input.text()) / 10 ** 15
                self.app.calibration.openC1 = self.getFloatValue(
                    self.open_c1_input.text()) / 10 ** 27
                self.app.calibration.openC2 = self.getFloatValue(
                    self.open_c2_input.text()) / 10 ** 36
                self.app.calibration.openC3 = self.getFloatValue(
                    self.open_c3_input.text()) / 10 ** 45
                self.app.calibration.openLength = self.getFloatValue(
                    self.open_length.text()) / 10 ** 12
                self.app.calibration.useIdealOpen = False
            except ValueError:
                self.app.calibration.useIdealOpen = True
                logger.warning(_warn_ideal("open"))

            try:
                self.app.calibration.loadR = self.getFloatValue(
                    self.load_resistance.text())
                self.app.calibration.loadL = self.getFloatValue(
                    self.load_inductance.text()) / 10 ** 12
                self.app.calibration.loadC = self.getFloatValue(
                    self.load_capacitance.text()) / 10 ** 15
                self.app.calibration.loadLength = self.getFloatValue(
                    self.load_length.text()) / 10 ** 12
                self.app.calibration.useIdealLoad = False
            except ValueError:
                self.app.calibration.useIdealLoad = True
                logger.warning(_warn_ideal("load"))

            try:
                self.app.calibration.throughLength = self.getFloatValue(
                    self.through_length.text()) / 10 ** 12
                self.app.calibration.useIdealThrough = False
            except ValueError:
                self.app.calibration.useIdealThrough = True
                logger.warning(_warn_ideal("through"))

        logger.debug("Attempting calibration calculation.")
        try:
            self.app.calibration.calc_corrections()
            self.calibration_status_label.setText(
                _format_cal_label(self.app.calibration.size(),
                                  "Sistema calibrado"))
            if self.use_ideal_values.isChecked():
                self.calibration_source_label.setText(
                    self.app.calibration.source)
            else:
                self.calibration_source_label.setText(
                    f"{self.app.calibration.source} (Standards: Custom)")

            if self.app.worker.rawData11:
                # There's raw data, so we can get corrected data
                logger.debug("Applying calibration to existing sweep data.")
                self.app.worker.data11, self.app.worker.data21 = (
                    self.app.worker.applyCalibration(
                        self.app.worker.rawData11,
                        self.app.worker.rawData21))
                logger.debug("Saving and displaying corrected data.")
                self.app.saveData(self.app.worker.data11,
                                  self.app.worker.data21, self.app.sweepSource)
                self.app.worker.signals.updated.emit()
        except ValueError as e:
            # showError here hides the calibration window,
            # so we need to pop up our own
            QtWidgets.QMessageBox.warning(
                self, "Error applying calibration", str(e))
            self.calibration_status_label.setText(
                "Applying calibration failed.")
            self.calibration_source_label.setText(self.app.calibration.source)

    @staticmethod
    def getFloatValue(text: str) -> float:
        return float(text) if text else 0.0

    def loadCalibration(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Calibration Files (*.cal);;All files (*.*)")

        if filename:
            self.app.calibration.load(filename)
            file_cal = open(filename, "r")
            f=file_cal.readlines()

            seg=int((len(f)-2)/101)
            a=f[2].split()#primer F
            b=f[len(f)-1].split()#ultima F

            fi=a[0]
            fs=b[0]
            #print(fi)
            #print(fs)
            #print(seg)

        if not self.app.calibration.isValid1Port():
            return
        for i, name in enumerate(
                ("short", "open", "load", "through", "isolation", "thrurefl")):
            self.cal_label[name].setText(
                _format_cal_label(self.app.calibration.data_size(name),
                                  "Loaded"))
            if i == 2 and not self.app.calibration.isValid2Port():
                break
        self.calculate()
        self.notes_textedit.clear()
        for note in self.app.calibration.notes:
            self.notes_textedit.appendPlainText(note)
        self.app.settings.setValue("CalibrationFile", filename)

        self.app.sweep_control.set_start(fi)
        self.app.sweep_control.set_end(fs)


        self.app.sweep_control.set_segments(seg)
        #self.app.sweep_control.update_step_size()

    def saveCalibration(self):
        if not self.app.calibration.isCalculated:
            logger.debug("Attempted to save an uncalculated calibration.")
            self.app.showError("No se puede guardar un estado de calibración no aplicado.")
            return
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("cal")
        filedialog.setNameFilter("Calibration Files (*.cal);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        if filedialog.exec():
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if not filename:
            logger.debug("No file name selected.")
            return
        self.app.calibration.notes = self.notes_textedit.toPlainText(
        ).splitlines()
        try:
            self.app.calibration.save(filename)
            self.app.settings.setValue("CalibrationFile", filename)
        except IOError:
            logger.error("Calibration save failed!")
            self.app.showError("Calibration save failed.")

    def idealCheckboxChanged(self):
        self.cal_short_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_open_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_load_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_through_box.setDisabled(self.use_ideal_values.isChecked())
        self.cal_standard_save_box.setDisabled(
            self.use_ideal_values.isChecked())


    def automaticCalibration(self):
        self.btn_automatic.setDisabled(True)
        introduction = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information,
            "Asistente de calibración",
            (
                 "El proceso es válido para S1P y S2P\n\n"
                "Si está listo para proceder, presione Ok."
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        response = introduction.exec()
        if response != QtWidgets.QMessageBox.Ok:
            self.btn_automatic.setDisabled(False)
            return
        logger.info("Starting automatic calibration assistant.")
        if not self.app.vna.connected():
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Dispositivo no conectado",
                ("Asegurese que el dispositivo esté conectado antes de realizar la"
                 " calibración.")
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        if self.app.sweep.properties.mode == SweepMode.CONTINOUS:
            QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Barrido Continuo Habilitado",
                ("Habilite el Barrido Simple")
            ).exec()
            self.btn_automatic.setDisabled(False)
            return

        short_step = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Information,
            "Calibración Modo Corto",
            (
               "Conecte la ficha correspondiente \n\n"
                "Presione Ok cuando esté listo para continuar."
            ),
            QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

        response = short_step.exec()
        if response != QtWidgets.QMessageBox.Ok:
            self.btn_automatic.setDisabled(False)
            return
        self.reset()
        self.app.calibration.source = "Asistente de calibración" #"Calibration assistant"
        self.nextStep = 0
        self.app.worker.signals.finished.connect(self.automaticCalibrationStep)
        self.app.sweep_start()
        return

    def automaticCalibrationStep(self):
        if self.nextStep == -1:
            self.app.worker.signals.finished.disconnect(
                self.automaticCalibrationStep)
            return

        if self.nextStep == 0:
            # Short
            self.cal_save("short")
            self.nextStep = 1

            open_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibración Modo Abierto",
                (
                    "Conecte la ficha correspondiente\n\n"
                    "Presione Ok cuando esté listo para continuar."
                ),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = open_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.nextStep = -1
                self.btn_automatic.setDisabled(False)
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep_start()
            return

        if self.nextStep == 1:
            # Open
            self.cal_save("open")
            self.nextStep = 2
            load_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibración Modo Carga",
                (
                     "Conecte la ficha correspondiente en el puerto 1\n\n"
                    "Presione Ok cuando esté listo para continuar."
                ),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = load_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep_start()
            return

        if self.nextStep == 2:
            # Load
            self.cal_save("load")
            self.nextStep = 3
            continue_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibración S1P Completa",
                (
                    "Presione Yes para continuar a S2P\n\n"
                    "Presione Apply para finalizar S1P \n\n"
                    "Presione Cancel para abortar\n\n"
                ),
                QtWidgets.QMessageBox.Yes
                | QtWidgets.QMessageBox.Apply
                | QtWidgets.QMessageBox.Cancel,)

            response = continue_step.exec()
            if response == QtWidgets.QMessageBox.Apply:
                self.calculate()
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                self.btn_automatic.setDisabled(False)
                return
            if response != QtWidgets.QMessageBox.Yes:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return

            isolation_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibración Modo Aislación",
                (
                    "Conecte la ficha de Carga en el Puerto 2\n\n"
                    "Si dispone de una segunda ficha de Carga, conectela en el puerto 1 \n\n"
                    "Presione Ok cuando este listo para continuar"
                ),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = isolation_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep_start()
            return

        if self.nextStep == 3:
            # Isolation
            self.cal_save("isolation")
            self.nextStep = 4
            through_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibración Modo Puerto a Puerto",
                (
                    "Conecte el cable SMA en ambos Puertos\n\n"
                    "Presione Ok cuando esté listo para continuar"
                ),
                QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)

            response = through_step.exec()
            if response != QtWidgets.QMessageBox.Ok:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.app.sweep_start()
            return

        if self.nextStep == 4:
            # Done
            self.cal_save("thrurefl")
            self.cal_save("through")
            apply_step = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Calibración Completa",
                (
                    "Presione Apply para aplicar\n\n"
                    "Presione Cancel para abortar"
                ),
                QtWidgets.QMessageBox.Apply | QtWidgets.QMessageBox.Cancel)

            response = apply_step.exec()
            if response != QtWidgets.QMessageBox.Apply:
                self.btn_automatic.setDisabled(False)
                self.nextStep = -1
                self.app.worker.signals.finished.disconnect(
                    self.automaticCalibrationStep)
                return
            self.calculate()
            self.btn_automatic.setDisabled(False)
            self.nextStep = -1
            self.app.worker.signals.finished.disconnect(
                self.automaticCalibrationStep)
            QtWidgets.QMessageBox.warning(self, "Aviso", "Calibración Aplicada")
            return
