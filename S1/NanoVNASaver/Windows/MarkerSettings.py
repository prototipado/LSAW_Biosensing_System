import logging

from PyQt5 import QtWidgets, QtCore, QtGui

from NanoVNASaver.RFTools import Datapoint
from NanoVNASaver.Marker.Widget import Marker
from NanoVNASaver.Marker.Values import TYPES, default_label_ids

logger = logging.getLogger(__name__)


class MarkerSettingsWindow(QtWidgets.QWidget):
    exampleData11 = [Datapoint(123000000, 0.89, -0.11),
                     Datapoint(123500000, 0.9, -0.1),
                     Datapoint(124000000, 0.91, -0.95)]
    exampleData21 = [Datapoint(123000000, -0.25, 0.49),
                     Datapoint(123456000, -0.3, 0.5),
                     Datapoint(124000000, -0.2, 0.5)]

    def __init__(self, app: QtWidgets.QWidget):
        super().__init__()
        self.app = app

        self.setWindowTitle("Ajustes del marcador")
        self.setWindowIcon(self.app.icon)

        QtWidgets.QShortcut(QtCore.Qt.Key_Escape, self, self.cancelButtonClick)

        self.exampleMarker = Marker("Ejemplo de marcador")
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        settings_group_box = QtWidgets.QGroupBox("Ajustes")
        settings_group_box_layout = QtWidgets.QFormLayout(settings_group_box)
        self.checkboxColouredMarker = QtWidgets.QCheckBox(
            "Nombre del marcador coloreado")
        self.checkboxColouredMarker.setChecked(
            self.app.settings.value("ColoredMarkerNames", True, bool))
        self.checkboxColouredMarker.stateChanged.connect(self.updateMarker)
        settings_group_box_layout.addRow(self.checkboxColouredMarker)

        fields_group_box = QtWidgets.QGroupBox("Datos mostrados")
        fields_group_box_layout = QtWidgets.QFormLayout(fields_group_box)

        self.savedFieldSelection = self.app.settings.value(
            "MarkerFields", defaultValue=default_label_ids()
        )

        if self.savedFieldSelection == "":
            self.savedFieldSelection = []

        self.currentFieldSelection = self.savedFieldSelection[:]

        self.active_labels_view = QtWidgets.QListView()
        self.update_displayed_data_form()

        fields_group_box_layout.addRow(self.active_labels_view)

        layout.addWidget(settings_group_box)
        layout.addWidget(fields_group_box)
        layout.addWidget(self.exampleMarker.get_data_layout())

        btn_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_ok = QtWidgets.QPushButton("OK")
        btn_apply = QtWidgets.QPushButton("Aplicar")
        btn_default = QtWidgets.QPushButton("Valores predeterminados")
        btn_cancel = QtWidgets.QPushButton("Cancelar")

        btn_ok.clicked.connect(self.okButtonClick)
        btn_apply.clicked.connect(self.applyButtonClick)
        btn_default.clicked.connect(self.defaultButtonClick)
        btn_cancel.clicked.connect(self.cancelButtonClick)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_default)
        btn_layout.addWidget(btn_cancel)

        self.updateMarker()
        for m in self.app.markers:
            m.setFieldSelection(self.currentFieldSelection)
            m.setColoredText(self.checkboxColouredMarker.isChecked())

    def updateMarker(self):
        self.exampleMarker.setFrequency(123456000)
        self.exampleMarker.setColoredText(
            self.checkboxColouredMarker.isChecked())
        self.exampleMarker.setFieldSelection(self.currentFieldSelection)
        self.exampleMarker.findLocation(self.exampleData11)
        self.exampleMarker.resetLabels()
        self.exampleMarker.updateLabels(self.exampleData11, self.exampleData21)

    def updateField(self, field: QtGui.QStandardItem):
        if field.checkState() == QtCore.Qt.Checked:
            if not field.data() in self.currentFieldSelection:
                self.currentFieldSelection = []
                for i in range(self.model.rowCount()):
                    field = self.model.item(i, 0)
                    if field.checkState() == QtCore.Qt.Checked:
                        self.currentFieldSelection.append(field.data())
        else:
            if field.data() in self.currentFieldSelection:
                self.currentFieldSelection.remove(field.data())
        self.updateMarker()

    def applyButtonClick(self):
        self.savedFieldSelection = self.currentFieldSelection[:]
        self.app.settings.setValue("MarkerFields", self.savedFieldSelection)
        self.app.settings.setValue(
            "ColoredMarkerNames", self.checkboxColouredMarker.isChecked())
        for m in self.app.markers + [self.app.delta_marker, ]:
            m.setFieldSelection(self.savedFieldSelection)
            m.setColoredText(self.checkboxColouredMarker.isChecked())

    def okButtonClick(self):
        self.applyButtonClick()
        self.close()

    def cancelButtonClick(self):
        self.currentFieldSelection = self.savedFieldSelection[:]
        self.update_displayed_data_form()
        self.updateMarker()
        self.close()

    def defaultButtonClick(self):
        self.currentFieldSelection = default_label_ids()
        self.update_displayed_data_form()
        self.updateMarker()

    def update_displayed_data_form(self):
        self.model = QtGui.QStandardItemModel()
        for label in TYPES:
            item = QtGui.QStandardItem(label.description)
            item.setData(label.label_id)
            item.setCheckable(True)
            item.setEditable(False)
            if label.label_id in self.currentFieldSelection:
                item.setCheckState(QtCore.Qt.Checked)
            self.model.appendRow(item)
        self.active_labels_view.setModel(self.model)
        self.model.itemChanged.connect(self.updateField)
