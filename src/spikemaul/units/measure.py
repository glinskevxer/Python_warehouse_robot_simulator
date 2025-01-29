"""Track measurements, which are written in sixteenths of an inch.

A gauge bar reads 56 1/2. A track level reads 1 1/4 low on the right rail. The
geometry car prints decimals, but the paperwork and the limits in the rule
book are fractions, and a limit of 1 1/4 compared against a reading of 1.26
should not turn on a float. Everything here is a whole number of sixteenths.

Crosslevel and any other reading that has a direction is signed, and the sign
means the right rail is high looking in the direction the mileposts increase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from spikemaul.errors import InputError

SIXTEENTHS_PER_INCH: Final = 16

_MIXED = re.compile(r"^(-)?(?:(\d+))?(?:[\s-]*(\d+)/(\d+))?$")
_DECIMAL = re.compile(r"^-?\d+(?:\.\d+)?$")


@dataclass(frozen=True, order=True)
class Inches:
    """A length in sixteenths of an inch, signed."""

    sixteenths: int

    @classmethod
    def of(cls, whole: int, numerator: int = 0, denominator: int = 1) -> Inches:
        """Build from a mixed number, as ``of(56, 1, 2)`` for 56 1/2."""
        if denominator <= 0 or SIXTEENTHS_PER_INCH % denominator != 0:
            raise InputError(f"a sixteenth does not divide into {denominator}ths")
        if numerator < 0:
            raise InputError("the sign belongs on the whole part, not the fraction")
        part = numerator * SIXTEENTHS_PER_INCH // denominator
        magnitude = abs(whole) * SIXTEENTHS_PER_INCH + part
        return cls(-magnitude if whole < 0 else magnitude)

    @classmethod
    def parse(cls, text: str) -> Inches:
        """Read ``56 1/2``, ``56-1/2``, ``-1/4`` or ``56.5``."""
        raw = text.strip().replace('"', "")
        if not raw:
            raise InputError("a measurement was expected and the field was empty")
        if _DECIMAL.match(raw):
            return cls.from_decimal(Decimal(raw))
        found = _MIXED.match(raw)
        if found is None or (found.group(2) is None and found.group(3) is None):
            raise InputError(f"{text!r} is not a measurement in inches")
        whole = int(found.group(2) or 0)
        numerator = int(found.group(3) or 0)
        denominator = int(found.group(4) or 1)
        value = cls.of(whole, numerator, denominator)
        return -value if found.group(1) else value

    @classmethod
    def from_decimal(cls, value: Decimal) -> Inches:
        """Take a reading off the geometry car, refusing anything finer."""
        scaled = value * SIXTEENTHS_PER_INCH
        if scaled != scaled.to_integral_value():
            raise InputError(f"{value} inches is finer than a sixteenth")
        return cls(int(scaled))

    @property
    def value(self) -> Decimal:
        """The measurement in inches."""
        return Decimal(self.sixteenths) / SIXTEENTHS_PER_INCH

    def __add__(self, other: Inches) -> Inches:
        return Inches(self.sixteenths + other.sixteenths)

    def __sub__(self, other: Inches) -> Inches:
        return Inches(self.sixteenths - other.sixteenths)

    def __neg__(self) -> Inches:
        return Inches(-self.sixteenths)

    def __abs__(self) -> Inches:
        return Inches(abs(self.sixteenths))

    def __str__(self) -> str:
        sign = "-" if self.sixteenths < 0 else ""
        whole, part = divmod(abs(self.sixteenths), SIXTEENTHS_PER_INCH)
        if part == 0:
            return f"{sign}{whole}"
        numerator, denominator = part, SIXTEENTHS_PER_INCH
        while numerator % 2 == 0:
            numerator //= 2
            denominator //= 2
        if whole == 0:
            return f"{sign}{numerator}/{denominator}"
        return f"{sign}{whole} {numerator}/{denominator}"


STANDARD_GAUGE: Final = Inches.of(56, 1, 2)
"""What the gauge bar is set to. Everything else is a deviation from it."""

ZERO: Final = Inches(0)


def gauge_deviation(measured: Inches) -> Inches:
    """How far off standard a gauge reading is, positive for wide."""
    return measured - STANDARD_GAUGE


def widest(readings: list[Inches]) -> Inches:
    """The reading furthest from zero, keeping its sign."""
    if not readings:
        raise InputError("no readings to take the widest of")
    return max(readings, key=lambda reading: (abs(reading.sixteenths), reading.sixteenths))
