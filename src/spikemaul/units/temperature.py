"""Rail temperature, which is not air temperature and is what buckles track.

Continuous welded rail is laid at a temperature it is neutral at. Above that
it wants to grow and cannot, so it pushes, and a hot afternoon on a curve with
soft shoulders is where that ends badly. Below it the rail pulls and a pull
apart is the other end of the same story.

Rail sitting in the sun runs hotter than the air around it, by a lot. The
office has no rail thermometer on every subdivision, so the working rule is a
number added to the forecast air temperature, and the number depends on the
sky. It is a rule of thumb and it is written here as one, plainly, so that
nobody later mistakes it for a measurement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from spikemaul.errors import InputError

COLDEST: Final = -60
HOTTEST: Final = 200

_TEXT = re.compile(r"^(-?\d{1,3})\s*(?:deg|degrees)?\s*f?$", re.IGNORECASE)


class Sky(Enum):
    """How much sun the rail is standing in."""

    CLEAR = "clear"
    PARTLY = "partly"
    OVERCAST = "overcast"

    @property
    def rail_above_air(self) -> int:
        """Degrees the rail runs above the air under this sky."""
        return {Sky.CLEAR: 30, Sky.PARTLY: 20, Sky.OVERCAST: 5}[self]

    @classmethod
    def parse(cls, text: str) -> Sky:
        """Read the sky off the morning forecast."""
        try:
            return cls(text.strip().lower())
        except ValueError as exc:
            named = ", ".join(sky.value for sky in cls)
            raise InputError(f"{text!r} is not a sky, expected one of {named}") from exc


@dataclass(frozen=True, order=True)
class Temperature:
    """A temperature in whole degrees Fahrenheit."""

    degrees: int

    def __post_init__(self) -> None:
        if not COLDEST <= self.degrees <= HOTTEST:
            raise InputError(f"{self.degrees} degrees is not a temperature this railroad sees")

    @classmethod
    def parse(cls, text: str) -> Temperature:
        """Read ``95``, ``95F`` or ``-10 degrees`` off a form."""
        found = _TEXT.match(text.strip())
        if found is None:
            raise InputError(f"{text!r} is not a temperature")
        return cls(int(found.group(1)))

    def above(self, other: Temperature) -> int:
        """Degrees this temperature stands above another, signed."""
        return self.degrees - other.degrees

    def warmer(self, degrees: int) -> Temperature:
        """The temperature so many degrees warmer, which may be colder."""
        return Temperature(self.degrees + degrees)

    def __str__(self) -> str:
        return f"{self.degrees}F"


def rail_temperature(air: Temperature, sky: Sky) -> Temperature:
    """What the rail is standing at, given the air and the sky.

    A rule of thumb, not a reading. Where a rail thermometer has been put on
    the ground its reading is the one to use.
    """
    return air.warmer(sky.rail_above_air)


def above_neutral(rail: Temperature, neutral: Temperature) -> int:
    """Degrees the rail is above where it was laid or last destressed."""
    return rail.above(neutral)


def hottest_of(readings: list[Temperature]) -> Temperature:
    """The hottest of several readings, refusing to guess from none."""
    if not readings:
        raise InputError("no temperatures to take the hottest of")
    return max(readings)
