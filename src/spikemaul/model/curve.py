"""Curves as they are recorded on the track chart.

A curve record carries what the chart carries: where it starts and ends, how
sharp it is, and how much elevation the outside rail is supposed to have. The
designated elevation is a decision, not a measurement, and the difference
between it and what the level actually reads is the thing that gets written up.

The spirals at each end matter for two reasons. Elevation is run in and out
through them, so a reading taken in a spiral is judged against a different
number than one taken in the body of the curve, and a curve whose spirals are
too short for its elevation cannot be run at its own speed however good the
body is.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.units.curvature import (
    MAX_UNBALANCE,
    Curvature,
    elevation_for,
    equilibrium_elevation,
)
from spikemaul.units.curvature import maximum_speed as curve_maximum_speed
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed

RUNOFF_INCHES_PER_FOOT = Decimal("0.0125")
"""The steepest elevation runoff this railroad builds, an inch in eighty feet."""


@dataclass(frozen=True)
class Curve:
    """One curve, from the start of its first spiral to the end of its last."""

    ident: Ident
    subdivision: Ident
    body: Span
    curvature: Curvature
    elevation: Inches
    hand: Hand
    entry_spiral_feet: int = 0
    exit_spiral_feet: int = 0

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.CURVE:
            raise InputError(f"{self.ident} is not a curve number")
        if self.subdivision.kind is not Kind.SUBDIVISION:
            raise InputError(f"{self.subdivision} is not a subdivision number")
        if self.curvature.is_tangent:
            raise InputError("a curve of no degrees is tangent track and is not recorded")
        if self.elevation.sixteenths < 0:
            raise InputError("elevation is carried on the outside rail and is not negative")
        if self.entry_spiral_feet < 0 or self.exit_spiral_feet < 0:
            raise InputError("a spiral does not have a negative length")

    @property
    def span(self) -> Span:
        """The whole curve including both spirals."""
        begin = self.body.begin.advanced_feet(-self.entry_spiral_feet)
        end = self.body.end.advanced_feet(self.exit_spiral_feet)
        return Span(begin, end)

    def holds(self, post: Milepost) -> bool:
        """Whether a milepost falls anywhere in the curve, spirals included."""
        return self.span.contains(post)

    def in_spiral(self, post: Milepost) -> bool:
        """Whether a milepost is in a spiral rather than the body."""
        return self.holds(post) and not self.body.contains(post)

    def maximum_speed(self, unbalance: Inches | None = None) -> Speed:
        """The fastest the curve may be taken on the elevation it carries."""
        found = curve_maximum_speed(self.curvature, self.elevation, unbalance or MAX_UNBALANCE)
        if found is None:
            raise InputError("a recorded curve always has a curve speed")
        return found

    def balance_speed(self) -> Speed:
        """The speed the elevation is exactly right for, rounded down."""
        speed = 1
        while equilibrium_elevation(self.curvature, Speed(speed + 1)) <= self.elevation.value:
            speed += 1
        return Speed(speed)

    def elevation_needed(self, speed: Speed) -> Decimal:
        """Elevation this curve would need to be run at that speed."""
        return elevation_for(self.curvature, speed)

    def runoff_feet(self) -> int:
        """Spiral length the elevation needs at the runoff we build to."""
        return int(self.elevation.value / RUNOFF_INCHES_PER_FOOT)

    def spirals_are_long_enough(self) -> bool:
        """Whether both spirals can run the elevation in and out."""
        needed = self.runoff_feet()
        return self.entry_spiral_feet >= needed and self.exit_spiral_feet >= needed

    def describe(self) -> str:
        """One line for the curve list."""
        return (
            f"{self.ident} {self.subdivision.tail} {self.body} "
            f"{self.curvature} {self.hand.value} {self.elevation} in"
        )
