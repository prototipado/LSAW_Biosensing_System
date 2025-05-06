import logging

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QCheckBox

from NanoVNASaver import Defaults
from NanoVNASaver.Marker.Widget import Marker
from NanoVNASaver.Controls.Control import Control

logger = logging.getLogger(__name__)


class ShowButton(QtWidgets.QPushButton):
    def setText(self, text: str = ''):
        if not text:
            text = ("Mostrar ventana de monitoreo"
                    if Defaults.cfg.gui.markers_hidden else "Ocultar monitoreo")
        super().setText(text)
        self.setToolTip("Toggle visibility of marker readings area")


class MarkerControl(Control):

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__(app, "Marcadores")

        for i in range(Defaults.cfg.chart.marker_count):
            marker = Marker("", self.app.settings)
            # marker.setFixedHeight(20)
            marker.updated.connect(self.app.markerUpdated)
            label, layout = marker.getRow()
            self.layout.addRow(label, layout)
            self.app.markers.append(marker)
            if i == 0:
                marker.isMouseControlledRadioButton.setChecked(True)

        self.check_delta = QCheckBox("Habilitar marcador delta")
        self.check_delta.toggled.connect(self.toggle_delta)

        self.check_delta_reference = QCheckBox("Referencia")
        self.check_delta_reference.toggled.connect(self.toggle_delta_reference)

        layout2 = QtWidgets.QHBoxLayout()
        #layout2.addWidget(self.check_delta)
        #layout2.addWidget(self.check_delta_reference)

        self.layout.addRow(layout2)

        self.showMarkerButton = ShowButton()
        self.showMarkerButton.setFixedHeight(20)
        self.showMarkerButton.setText()
        self.showMarkerButton.clicked.connect(self.toggle_frame)

        lock_radiobutton = QtWidgets.QRadioButton("Bloquear")
        lock_radiobutton.setLayoutDirection(QtCore.Qt.RightToLeft)
        lock_radiobutton.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.showMarkerButton)
        hbox.addWidget(lock_radiobutton)
        self.layout.addRow(hbox)

    def toggle_frame(self):
        def settings(hidden: bool):
            Defaults.cfg.gui.markers_hidden = not hidden
            self.app.marker_frame.setHidden(
                Defaults.cfg.gui.markers_hidden)
            self.showMarkerButton.setText()
            self.showMarkerButton.repaint()

        settings(self.app.marker_frame.isHidden())

    def toggle_delta(self):
        self.app.delta_marker_layout.setVisible(self.check_delta.isChecked())

    def toggle_delta_reference(self):
        self.app.marker_ref = bool(self.check_delta_reference.isChecked())

        if self.app.marker_ref:
            new_name = "Referencia Delta - Marcador 1"

        else:
            new_name = "Referencia Delta 2 - Marcador 1"
            # FIXME: reset
        self.app.delta_marker.group_box.setTitle(new_name)
        self.app.delta_marker.resetLabels()
