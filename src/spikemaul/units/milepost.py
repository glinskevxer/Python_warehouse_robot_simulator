"""Mileposts, written the way the track charts write them.

A milepost is a position on the railroad, not a distance along it. MP 43.20
means the point twenty hundredths of a mile beyond milepost 43, measured the
way the last survey measured it. Two mileposts on the same line can be
subtracted to get a nominal distance, and that distance is only the true one
when no equation point lies between them. The equation points live in
``spikemaul.units.chainage``; this module is deliberately ignorant of them so
that the arithmetic here has one meaning.

Everything is held as a whole number of hundredths of a mile because that is
the resolution the field paperwork carries. Anything finer is a false
precision the section foreman is not going to honour with a tape measure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from spikemaul.errors import InputError

FEET_PER_MILE = 5280
"""Feet in a nominal mile. Real miles between equation points are not this."""

HUNDREDTHS_PER_MILE = 100

_TEXT = re.compile(r"^(?:MP\s*)?(\d{1,4})(?:\.(\d{1,2}))?$", re.IGNORECASE)
_STATION = re.compile(r"^(?:MP\s*)?(\d{1,4})\s*\+\s*(\d{1,4})$")


@dataclass(frozen=True, order=True)
class Milepost:
    """A position on one line, held in hundredths of a mile.

    Ordering is by position, which is what the bulletin printer wants, and
    comparing mileposts from two different lines is a mistake this class
    cannot catch. The register that holds them is where that is enforced.
    """

    hundredths: int

    def __post_init__(self) -> None:
        if self.hundredths < 0:
            raise InputError(f"milepost {self.hundredths} is before the start of the line")

    @classmethod
    def of(cls, miles: int, hundredths: int = 0) -> Milepost:
        """Build from a whole milepost and hundredths, as ``of(43, 20)``."""
        if hundredths < 0 or hundredths >= HUNDREDTHS_PER_MILE:
            raise InputError(f"{hundredths} is not a hundredth of a mile")
        return cls(miles * HUNDREDTHS_PER_MILE + hundredths)

    @classmethod
    def parse(cls, text: str) -> Milepost:
        """Read a milepost the way it is written on a track chart or a form.

        Accepts ``43.2``, ``43.20``, ``MP 43.20`` and the station form
        ``43+1056``, which means 1056 feet beyond milepost 43. Refuses a third
        decimal place rather than rounding it away, because a reading carried
        to feet should be written in the station form where it stays exact.
        """
        raw = text.strip()
        if not raw:
            raise InputError("a milepost was expected and the field was empty")
        station = _STATION.match(raw)
        if station is not None:
            feet = int(station.group(2))
            if feet >= FEET_PER_MILE:
                raise InputError(f"{feet} feet is past the next milepost in {text!r}")
            scaled = Decimal(feet) * HUNDREDTHS_PER_MILE / FEET_PER_MILE
            if scaled != scaled.to_integral_value():
                raise InputError(
                    f"{text!r} is {feet} feet, which is not a whole hundredth of a mile"
                )
            return cls.of(int(station.group(1)), int(scaled))
        found = _TEXT.match(raw)
        if found is None:
            raise InputError(f"{text!r} is not a milepost")
        miles = int(found.group(1))
        digits = found.group(2) or "0"
        hundredths = int(digits.ljust(2, "0"))
        return cls.of(miles, hundredths)

    @classmethod
    def from_miles(cls, miles: Decimal | str) -> Milepost:
        """Build from a decimal number of miles, refusing anything finer."""
        try:
            value = Decimal(miles)
        except InvalidOperation as exc:
            raise InputError(f"{miles!r} is not a number of miles") from exc
        scaled = value * HUNDREDTHS_PER_MILE
        if scaled != scaled.to_integral_value():
            raise InputError(f"{value} miles is finer than a hundredth")
        return cls(int(scaled))

    @property
    def miles(self) -> Decimal:
        """The position as a decimal number of miles."""
        return Decimal(self.hundredths) / HUNDREDTHS_PER_MILE

    @property
    def whole(self) -> int:
        """The milepost the position is beyond, as painted on the post."""
        return self.hundredths // HUNDREDTHS_PER_MILE

    @property
    def into_mile(self) -> int:
        """Hundredths of a mile past that post."""
        return self.hundredths % HUNDREDTHS_PER_MILE

    def station(self) -> str:
        """The position in the station form, as ``43+1056``."""
        feet = round(self.into_mile * FEET_PER_MILE / HUNDREDTHS_PER_MILE)
        return f"{self.whole}+{feet}"

    def nominal_feet_to(self, other: Milepost) -> int:
        """Feet from here to ``other`` if no equation point lies between.

        Signed, so a milepost behind this one gives a negative answer. Callers
        that have a line in hand should ask the line instead.
        """
        return round((other.hundredths - self.hundredths) * FEET_PER_MILE / HUNDREDTHS_PER_MILE)

    def advanced(self, hundredths: int) -> Milepost:
        """The position ``hundredths`` further along, which may be backwards."""
        moved = self.hundredths + hundredths
        if moved < 0:
            raise InputError(f"moving {hundredths} from {self} runs off the start of the line")
        return Milepost(moved)

    def advanced_feet(self, feet: int) -> Milepost:
        """The position ``feet`` further along, rounded to the hundredth."""
        return self.advanced(round(feet * HUNDREDTHS_PER_MILE / FEET_PER_MILE))

    def __str__(self) -> str:
        return f"{self.whole}.{self.into_mile:02d}"
