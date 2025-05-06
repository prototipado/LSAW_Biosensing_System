import logging

from PyQt6 import QtWidgets

logger = logging.getLogger(__name__)


def make_scrollable(
    window: QtWidgets.QWidget, layout: QtWidgets.QLayout
) -> None:
    area = QtWidgets.QScrollArea()
    area.setWidgetResizable(True)
    outer = QtWidgets.QVBoxLayout()
    outer.addWidget(area)
    widget = QtWidgets.QWidget()
    widget.setLayout(layout)
    area.setWidget(widget)
    window.setLayout(outer)
    window.resize(area.size())