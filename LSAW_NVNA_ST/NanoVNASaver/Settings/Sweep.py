import logging
from enum import Enum
from math import log
from threading import Lock
from typing import Iterator, Tuple

logger = logging.getLogger(__name__)


class SweepMode(Enum):
    SINGLE = 0
    CONTINOUS = 1
    AVERAGE = 2


class Properties:
    def __init__(self, name: str = "",
                 mode: 'SweepMode' = SweepMode.SINGLE,
                 averages: Tuple[int, int] = (3, 0),
                 logarithmic: bool = False, nsweeps: int = 0, anmode: int = 0):
        #anmode : 1(Max) 0(Min)
        self.name = name
        self.mode = mode
        self.averages = averages
        self.logarithmic = logarithmic
        self.nsweeps = nsweeps
        self.anmode = anmode

    def __repr__(self):
        return (
            f"Properties('{self.name}', {self.mode}, {self.averages},"
            f" {self.logarithmic})")


class Sweep:
    def __init__(self, start: int = 3600000, end: int = 30000000,
                 points: int = 301
                 , segments: int = 1,
                 properties: 'Properties' = Properties()):
        self.start = start
        self.end = end
        self.points = points
        self.segments = segments
        self.properties = properties
        self.lock = Lock()
        self.check()
        logger.debug("%s", self)

    def __repr__(self) -> str:
        return (
            f"Sweep({self.start}, {self.end}, {self.points}, {self.segments},"
            f" {self.properties})")

    def __eq__(self, other) -> bool:
        return (self.start == other.start and
                self.end == other.end and
                self.points == other.points and
                self.segments == other.segments and
                self.properties == other.properties)

    def copy(self) -> 'Sweep':
        return Sweep(self.start, self.end, self.points, self.segments,
                     self.properties)

    @property
    def span(self) -> int:
        return self.end - self.start

    @property
    def stepsize(self) -> int:
        return round(self.span / (self.points * self.segments - 1))

    def check(self):
        if (
                self.segments <= 0
                or self.points <= 0
                or self.start <= 0
                or self.end <= 0
                or self.stepsize < 1
        ):
            raise ValueError(f"Illegal sweep settings: {self}")

    def _exp_factor(self, index: int) -> float:
        return 1 - log(self.segments + 1 - index) / log(self.segments + 1)

    def get_index_range(self, index: int) -> Tuple[int, int]:
        if not self.properties.logarithmic:
            start = self.start + index * self.points * self.stepsize
            end = start + (self.points - 1) * self.stepsize
        else:
            start = round(self.start + self.span * self._exp_factor(index))
            end = round(self.start + self.span * self._exp_factor(index + 1))
        logger.debug("get_index_range(%s) -> (%s, %s)", index, start, end)
        return start, end

    def get_frequencies(self) -> Iterator[int]:
        for i in range(self.segments):
            start, stop = self.get_index_range(i)
            step = (stop - start) / self.points
            freq = start
            for _ in range(self.points):
                yield round(freq)
                freq += step
