"""Tonnage over a segment, counted in million gross tons.

Tonnage arrives once a month from the operating department as a gross tons
figure per subdivision, and the track department cares about it for two
reasons. Rail flaw testing is on a tonnage cycle rather than a calendar one,
and rail wear is a tonnage question dressed up as a calendar one.

A million gross tons is written MGT and carried to a hundredth, which is ten
thousand gross tons. Anything finer than that is a rounding of somebody
else's estimate and pretending otherwise makes reports disagree.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from spikemaul.errors import InputError

GROSS_TONS_PER_MGT: Final = 1_000_000
HUNDREDTHS_PER_MGT: Final = 100

_TEXT = re.compile(r"^(\d{1,5})(?:\.(\d{1,2}))?\s*(?:mgt)?$", re.IGNORECASE)


@dataclass(frozen=True, order=True)
class Tonnage:
    """Traffic over a piece of track, in hundredths of a million gross tons."""

    hundredths: int

    def __post_init__(self) -> None:
        if self.hundredths < 0:
            raise InputError("tonnage does not run backwards over a segment")

    @classmethod
    def of(cls, mgt: Decimal | str | int) -> Tonnage:
        """Build from a figure in MGT, refusing anything finer than a hundredth."""
        scaled = Decimal(mgt) * HUNDREDTHS_PER_MGT
        if scaled != scaled.to_integral_value():
            raise InputError(f"{mgt} MGT is finer than the sheets are counted to")
        return cls(int(scaled))

    @classmethod
    def parse(cls, text: str) -> Tonnage:
        """Read ``12.4`` or ``12.40 MGT`` off the monthly sheet."""
        found = _TEXT.match(text.strip())
        if found is None:
            raise InputError(f"{text!r} is not a tonnage")
        digits = (found.group(2) or "0").ljust(2, "0")
        return cls(int(found.group(1)) * HUNDREDTHS_PER_MGT + int(digits))

    @classmethod
    def from_gross_tons(cls, tons: int) -> Tonnage:
        """Build from the gross tons figure the operating department sends."""
        if tons < 0:
            raise InputError("gross tons do not run backwards")
        return cls(round(tons * HUNDREDTHS_PER_MGT / GROSS_TONS_PER_MGT))

    @property
    def mgt(self) -> Decimal:
        """The tonnage in MGT."""
        return (Decimal(self.hundredths) / HUNDREDTHS_PER_MGT).quantize(Decimal("0.01"))

    @property
    def gross_tons(self) -> int:
        """The tonnage back in gross tons, to the ten thousand it is held to."""
        return self.hundredths * GROSS_TONS_PER_MGT // HUNDREDTHS_PER_MGT

    def __add__(self, other: Tonnage) -> Tonnage:
        return Tonnage(self.hundredths + other.hundredths)

    def __sub__(self, other: Tonnage) -> Tonnage:
        if other.hundredths > self.hundredths:
            raise InputError("taking more tonnage off a segment than went over it")
        return Tonnage(self.hundredths - other.hundredths)

    def __str__(self) -> str:
        return f"{self.mgt} MGT"


ZERO: Final = Tonnage(0)


def accumulated(readings: list[Tonnage]) -> Tonnage:
    """Total of several monthly figures, which is zero for no months."""
    total = ZERO
    for reading in readings:
        total = total + reading
    return total


def annual_rate(over: Tonnage, days: int) -> Decimal:
    """Tonnage a year, worked from a period of days.

    A short period gives a bad answer and the caller is the one who knows
    whether the period is representative, so nothing here refuses a month.
    """
    if days <= 0:
        raise InputError("a tonnage rate needs a period of at least a day")
    return (over.mgt * 365 / days).quantize(Decimal("0.01"))


def days_to_reach(target: Tonnage, standing: Tonnage, rate_per_year: Decimal) -> int:
    """Days until a segment reaches a tonnage, at a yearly rate.

    Rounded down, because the cycle comes due when the tonnage is reached and
    a day of slack is not the office's to give.
    """
    if rate_per_year <= 0:
        raise InputError("a segment with no tonnage over it never reaches a cycle")
    if standing >= target:
        return 0
    short = (target - standing).mgt
    return int(short * 365 / rate_per_year)
