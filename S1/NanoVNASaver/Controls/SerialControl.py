import logging
from time import sleep

from PyQt5 import QtWidgets

from NanoVNASaver.Hardware.Hardware import Interface, get_interfaces, get_VNA
from NanoVNASaver.Controls.Control import Control

logger = logging.getLogger(__name__)

a = 76876458


class SerialControl(Control):

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__(app, "Control de puerto serie")

        self.interfaceVNA = Interface("serial", "none")
        self.connectflag = 0

        self.inp_port = QtWidgets.QComboBox()
        self.inp_port.setMinimumHeight(20)

        self.rescanSerialPort()
        self.inp_port.setEditable(True)

        self.btn_rescan = QtWidgets.QPushButton("Reescanear")
        self.btn_rescan.setMinimumHeight(20)
        self.btn_rescan.setFixedWidth(60)
        self.btn_rescan.clicked.connect(self.rescanSerialPort)

        intput_layout = QtWidgets.QHBoxLayout()
        intput_layout.addWidget(QtWidgets.QLabel("Puerto"), stretch=0)
        intput_layout.addWidget(self.inp_port, stretch=0)
        intput_layout.addWidget(self.btn_rescan, stretch=0)
        self.layout.addRow(intput_layout)

        button_layout = QtWidgets.QHBoxLayout()

        self.btn_toggle = QtWidgets.QPushButton("Conectar Sistema")
        self.btn_toggle.setMinimumHeight(20)
        self.btn_toggle.clicked.connect(self.serialButtonClick)

        self.btn_toggle.setStyleSheet("background-color : red")

        button_layout.addWidget(self.btn_toggle, stretch=1)

        self.btn_settings = QtWidgets.QPushButton("Administrar")
        self.btn_settings.setMinimumHeight(20)
        self.btn_settings.setFixedWidth(60)
        self.btn_settings.clicked.connect(
            lambda: self.app.display_window("device_settings"))

        button_layout.addWidget(self.btn_settings, stretch=0)
        self.layout.addRow(button_layout)

    def rescanSerialPort(self):

        if self.connectflag == 0:

            self.inp_port.clear()

            for iface in get_interfaces():
                #if iface.comment == "H":
                    self.inp_port.insertItem(1, f"{iface}", iface)

            self.inp_port.repaint()

        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Sistema Conectado")
            return

    def serialButtonClick(self):
        if not self.app.vna.connected():
            self.connect_device()
            self.connectflag = 1

        else:
            self.disconnect_device()
            self.connectflag = 0

    def connect_device(self):
        self.interfaceVNA = self.inp_port.currentData()

        if self.interfaceVNA == None:
            QtWidgets.QMessageBox.warning(self, "Error", "Sistema desconectado")
            return None

        with self.interfaceVNA.lock:

            logger.error("Connection %s", self.interfaceVNA)
            try:
                self.interfaceVNA.open()

            except (IOError, AttributeError) as exc:
                logger.error("Tried to open %s and failed: %s", self.interfaceVNA, exc)
                return
            if not self.interfaceVNA.isOpen():
                logger.error("Unable to open port %s", self.interfaceVNA)
                return
            self.interfaceVNA.timeout = 0.05
        sleep(0.1)
        try:
            self.app.vna = get_VNA(self.interfaceVNA)
        except IOError as exc:
            logger.error("Unable to connect to VNA: %s", exc)

        self.app.vna.validateInput = self.app.settings.value("SerialInputValidation", True, bool)

        # connected

        self.btn_toggle.setText("Desconectar Sistema")

        self.btn_toggle.setStyleSheet("background-color : green")
        self.btn_toggle.repaint()

        self.app.sweep_control.set_start(120000000)
        self.app.sweep_control.set_end(124000000)
        self.app.sweep_control.set_segments(1)  # speed up things
        self.app.sweep_control.update_center_span()
        self.app.sweep_control.update_step_size()

        QtWidgets.QMessageBox.warning(self, "Aviso", "Sistema Conectado")

        self.app.sweep_start()

    def disconnect_device(self):

        with self.interfaceVNA.lock:
            if self.interfaceVNA == None :
                QtWidgets.QMessageBox.warning(self, "Error", "Dispositivos desconectados")
                return

            logger.info("Closing connection to %s", self.interfaceVNA)
            self.interfaceVNA.close()
            self.btn_toggle.setText("Conectar Sistema")
            self.btn_toggle.setStyleSheet("background-color : red")

            QtWidgets.QMessageBox.warning(self, "Aviso", "Sistema Desconectado")

            self.btn_toggle.repaint()
            self.connectflag = 0

