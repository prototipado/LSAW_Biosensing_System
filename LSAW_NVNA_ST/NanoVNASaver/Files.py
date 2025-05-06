import logging


from PyQt5 import QtWidgets, QtCore

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Settings.Sweep import Sweep, SweepMode
from NanoVNASaver.Touchstone import Touchstone
from typing import List, Tuple

logger = logging.getLogger(__name__)

class FilesWindow(QtWidgets.QWidget):
    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app
        self.sweep = Sweep()

        # Definicion de ventana
        self.setWindowTitle("Archivos")
        self.setWindowIcon(self.app.icon)
        self.setMinimumWidth(200)
        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.hide)
        file_window_layout = QtWidgets.QVBoxLayout()
        self.setLayout(file_window_layout)
        # Importar
        load_file_control_box = QtWidgets.QGroupBox()
        load_file_control_box.setMaximumWidth(300)
        load_file_control_layout = QtWidgets.QFormLayout(load_file_control_box)

        btn_load_sweep = QtWidgets.QPushButton("Importar")
        btn_load_sweep.clicked.connect(self.loadSweepFile)
        load_file_control_layout.addRow(btn_load_sweep)

        file_window_layout.addWidget(load_file_control_box)

        # Sector Guardar

        save_file_control_box = QtWidgets.QGroupBox()
        save_file_control_box.setMaximumWidth(300)
        save_file_control_layout = QtWidgets.QFormLayout(save_file_control_box)

        btn_export_file = QtWidgets.QPushButton("Exportar")
        btn_export_file.clicked.connect(lambda: self.exportFile(4))
        save_file_control_layout.addRow(btn_export_file)

        file_window_layout.addWidget(save_file_control_box)

        #btn_open_file_window = QtWidgets.QPushButton("Archivos")
        #btn_open_file_window.clicked.connect( lambda: self.app.display_window("file"))

    def exportFile(self, nr_params: int = 1):
        if len(self.app.data.s11) == 0:
            QtWidgets.QMessageBox.warning(
                self, "Error", "No hay datos")
            return
        if nr_params > 2 and len(self.app.data.s21) == 0:
            QtWidgets.QMessageBox.warning(
                self, "Error", "No hay datos")
            return

        filedialog = QtWidgets.QFileDialog(self)
        if nr_params == 1:
            filedialog.setDefaultSuffix("s1p")
            filedialog.setNameFilter(
                "Touchstone 1-Port Files (*.s1p);;All files (*.*)")
        else:
            filedialog.setDefaultSuffix("s2p")
            filedialog.setNameFilter("Touchstone 2-Port Files (*.s2p);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        selected = filedialog.exec()
        if not selected:
            return
        filename = filedialog.selectedFiles()[0]
        if filename == "":
            logger.debug("No file name selected.")
            return

        if self.sweep.properties.mode == SweepMode.CONTINOUS:
            letra = "x"
            posf = filename.rfind('B')
            print(len(self.app.worker.alls21))

            for i in range (0,len(self.app.worker.alls11)) :
                faux = filename[:posf]+str(i)+letra+filename[posf:]
                ts = Touchstone(faux)
                print(faux)
                ts.sdata[0] = self.app.worker.alls11[i]
                ts.sdata[1] = self.app.worker.alls21[i]

                for dp in self.app.worker.alls11[i]:
                    ts.sdata[2].append(Datapoint(dp.freq, 0, 0))
                    ts.sdata[3].append(Datapoint(dp.freq, 0, 0))

                print(i)
                ts.save(4)

                print(self.app.worker.alls21[i])

        if self.sweep.properties.mode == SweepMode.SINGLE:

                ts = Touchstone(filename)
                ts.sdata[0] = self.app.data.s11
                ts.sdata[1] = self.app.data.s21

                for dp in self.app.data.s11:
                    ts.sdata[2].append(Datapoint(dp.freq, 0, 0))
                    ts.sdata[3].append(Datapoint(dp.freq, 0, 0))

                ts.save(4)

    def loadSweepFile(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            filter="Touchstone Files (*.s1p *.s2p);;All files (*.*)")
        if filename != "":
            self.app.data.s11 = []
            self.app.data.s21 = []
            t = Touchstone(filename)
            t.load()
            self.app.saveData(t.s11, t.s21, filename)
            self.app.dataUpdated()


