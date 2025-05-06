
import logging
import re

logger = logging.getLogger(__name__)


class Version:
    RXP = re.compile(r"""^
        \D*
        (?P<major>\d+)\.
        (?P<minor>\d+)\.?
        (?P<revision>\d+)?
        (?P<note>.*)
        $""", re.VERBOSE)

    def __init__(self, vstring: str = "0.0.0"):
        self.data = {
            "major": 0,
            "minor": 0,
            "revision": 0,
            "note": "",
        }
        try:
            self.data = Version.RXP.search(vstring).groupdict()
            for name in ("major", "minor", "revision"):
                self.data[name] = int(self.data[name])
        except TypeError:
            self.data["revision"] = 0
        except AttributeError:
            logger.error("Unable to parse version: %s", vstring)

    def __gt__(self, other: "Version") -> bool:
        l, r = self.data, other.data
        for name in ("major", "minor", "revision"):
            if l[name] > r[name]:
                return True
            if l[name] < r[name]:
                return False
        return False

    def __lt__(self, other: "Version") -> bool:
        return other.__gt__(self)

    def __ge__(self, other: "Version") -> bool:
        return self.__gt__(other) or self.__eq__(other)

    def __le__(self, other: "Version") -> bool:
        return other.__gt__(self) or self.__eq__(other)

    def __eq__(self, other: "Version") -> bool:
        return self.data == other.data

    def __str__(self) -> str:
        return (f'{self.data["major"]}.{self.data["minor"]}'
                f'.{self.data["revision"]}{self.data["note"]}')

    @property
    def major(self) -> int:
        return self.data["major"]

    @property
    def minor(self) -> int:
        return self.data["minor"]

    @property
    def revision(self) -> int:
        return self.data["revision"]

    @property
    def note(self) -> str:
        return self.data["note"]
