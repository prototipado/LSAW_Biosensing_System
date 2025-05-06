import logging

from PyQt5 import QtWidgets, QtCore

logger = logging.getLogger(__name__)


class Control(QtWidgets.QGroupBox):
    updated = QtCore.pyqtSignal(object)

    def __init__(self, app: QtWidgets.QWidget, title: str = ""):
        super().__init__()
        self.app = app
        self.setMaximumWidth(240)
        self.setTitle(title)
        self.layout = QtWidgets.QFormLayout(self)
