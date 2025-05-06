from typing import List, NamedTuple
from NanoVNASaver.RFTools import Datapoint


class Label(NamedTuple):
    label_id: str
    name: str
    description: str
    default_active: bool


TYPES = (

    Label("s21gain", "S21 Gain", "S21 Gain", True),
    Label("actualfreq", "Frequencia", "Actual frequency", True),
    Label("s21phase", "S21 Phase", "S21 Phase", True),
    Label("s21groupdelay", "S21 Group Delay", "S21 Group Delay", True),

    #Label("returnloss", "Return loss", "Return loss", False),
    )


def default_label_ids() -> str:
    return [label.label_id for label in TYPES if label.default_active]


class Value():
    """Contains the data area to calculate marker values from"""

    def __init__(self, freq: int = 0,
                 s11: List[Datapoint] = None,
                 s21: List[Datapoint] = None):
        self.freq = freq
        self.s11 = [] if s11 is None else s11[:]
        self.s21 = [] if s21 is None else s21[:]

    def store(self, index: int,
              s11: List[Datapoint],
              s21: List[Datapoint]):
        # handle boundaries
        if index == 0:
            index = 1
            s11 = [s11[0], ] + s11
            if s21:
                s21 = [s21[0], ] + s21
        if index == len(s11):
            s11 += [s11[-1], ]
            if s21:
                s21 += [s21[-1], ]

        self.freq = s11[1].freq
        self.s11 = s11[index - 1:index + 2]
        if s21:
            self.s21 = s21[index - 1:index + 2]
