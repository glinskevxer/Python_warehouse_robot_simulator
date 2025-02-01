"""Curves, their elevation, and the speed the two of them allow.

A curve is written on the track chart as a degree of curvature, which is the
angle subtended by a hundred foot chord. Three degrees thirty minutes is a
sharper curve than two degrees, and the number is not a radius, so the
arithmetic here is worth having in one place.

The speed a curve allows comes off the elevation the outside rail is carrying
and the unbalance the railroad permits. Unbalance is the elevation the curve
would need at that speed and does not have, and three inches is as far as
freight goes here without written authority.

Nothing in this module knows what class of track it is looking at. The class
speed and the curve speed are two separate caps and it is the caller's job to
take the lower of them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from spikemaul.errors import InputError
from spikemaul.units.measure import Inches
from spikemaul.units.speed import Speed

MINUTES_PER_DEGREE: Final = 60

ELEVATION_FACTOR: Final = Decimal("0.0007")
"""The constant in E = 0.0007 V squared D, which the rule book prints."""

MAX_UNBALANCE: Final = Inches.of(3)
"""How far a freight train is allowed to run out of balance on this railroad."""

MAX_ELEVATION: Final = Inches.of(6)
"""How much elevation the track may carry at all."""

_TEXT = re.compile(r"^(\d{1,2})(?:\s*(?:d|deg|degrees|-)\s*(\d{1,2})(?:\s*(?:m|min|minutes))?)?$")


@dataclass(frozen=True, order=True)
class Curvature:
    """A degree of curvature, held in minutes. Zero minutes is tangent track."""

    minutes: int

    def __post_init__(self) -> None:
        if self.minutes < 0:
            raise InputError("a curve cannot be less than tangent")
        if self.minutes > 20 * MINUTES_PER_DEGREE:
            raise InputError(f"{self.degrees} degrees is sharper than any curve on this railroad")

    @classmethod
    def of(cls, degrees: int, minutes: int = 0) -> Curvature:
        """Build from degrees and minutes, as ``of(3, 30)``."""
        if minutes < 0 or minutes >= MINUTES_PER_DEGREE:
            raise InputError(f"{minutes} is not a number of minutes")
        return cls(degrees * MINUTES_PER_DEGREE + minutes)

    @classmethod
    def parse(cls, text: str) -> Curvature:
        """Read ``3-30``, ``3d30``, ``3 deg 30 min`` or the decimal ``3.5``."""
        raw = text.strip().lower()
        if not raw:
            raise InputError("a degree of curvature was expected and the field was empty")
        if re.fullmatch(r"\d{1,2}(?:\.\d+)?", raw):
            scaled = Decimal(raw) * MINUTES_PER_DEGREE
            if scaled != scaled.to_integral_value():
                raise InputError(f"{text!r} is finer than a minute of curvature")
            return cls(int(scaled))
        found = _TEXT.match(raw)
        if found is None:
            raise InputError(f"{text!r} is not a degree of curvature")
        return cls.of(int(found.group(1)), int(found.group(2) or 0))

    @property
    def is_tangent(self) -> bool:
        """Whether this is straight track, which has no curve speed at all."""
        return self.minutes == 0

    @property
    def degrees(self) -> Decimal:
        """The curvature in degrees, as the formulas want it."""
        return Decimal(self.minutes) / MINUTES_PER_DEGREE

    @property
    def radius_feet(self) -> Decimal:
        """The radius, by the chord definition the track chart is drawn to."""
        if self.is_tangent:
            raise InputError("tangent track has no radius")
        return (Decimal("5729.58") / self.degrees).quantize(Decimal("0.1"))

    def __str__(self) -> str:
        degrees, minutes = divmod(self.minutes, MINUTES_PER_DEGREE)
        return f"{degrees} deg {minutes:02d} min"


def equilibrium_elevation(curve: Curvature, speed: Speed) -> Decimal:
    """The elevation a curve would need to be in balance at that speed."""
    if curve.is_tangent:
        return Decimal(0)
    return (ELEVATION_FACTOR * curve.degrees * speed.mph * speed.mph).quantize(Decimal("0.01"))


def unbalance_at(curve: Curvature, elevation: Inches, speed: Speed) -> Decimal:
    """How far out of balance a train runs at that speed on that elevation."""
    return equilibrium_elevation(curve, speed) - elevation.value


def maximum_speed(
    curve: Curvature,
    elevation: Inches,
    unbalance: Inches = MAX_UNBALANCE,
) -> Speed | None:
    """The fastest a train may take the curve, or ``None`` on tangent track.

    Rounded down to the whole mile per hour, because a bulletin does not carry
    a fraction and rounding up would post a speed the elevation does not
    support.
    """
    if elevation.sixteenths < 0:
        raise InputError("elevation is measured on the outside rail and is not negative")
    if elevation > MAX_ELEVATION:
        raise InputError(f"{elevation} inches of elevation is past what track may carry")
    if unbalance > MAX_UNBALANCE:
        raise InputError(f"{unbalance} inches of unbalance is past what freight may run")
    if curve.is_tangent:
        return None
    total = elevation.value + unbalance.value
    squared = total / (ELEVATION_FACTOR * curve.degrees)
    return Speed(int(squared.sqrt()))


def elevation_for(curve: Curvature, speed: Speed, unbalance: Inches = MAX_UNBALANCE) -> Decimal:
    """The elevation needed to run a curve at a speed within the unbalance."""
    needed = equilibrium_elevation(curve, speed) - unbalance.value
    return max(needed, Decimal(0))
