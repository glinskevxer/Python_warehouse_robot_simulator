"""Turnouts, which are the part of the railroad that wears out fastest.

A turnout is recorded at its point of switch and carries its size, which is
the frog number and decides the diverging speed. Everything else about it is a
condition: the points fit or they do not, the frog is worn or it is not, the
guard rail is where it should be or it is not.

The diverging speed does not come off the class of track. A number eight
turnout in class four track is still fifteen miles an hour through the
diverging route, and a bulletin that prints the class speed for it is wrong in
the direction that derails cars.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.speed import Speed

POINT_GAP_LIMIT: Final = Inches.of(0, 1, 4)
"""A switch point standing this far off its stock rail is a defect."""

FROG_FLANGEWAY_MIN: Final = Inches.of(1, 1, 2)
"""The narrowest a frog flangeway may be worn to."""

GUARD_CHECK_MIN: Final = Inches.of(54, 1, 8)
"""Guard check gauge, measured from the guard face to the far running rail."""


class FrogKind(Enum):
    """What the frog is made of, which decides how it is inspected."""

    RIGID = "rigid"
    SPRING = "spring"
    SELF_GUARDED = "self guarded"
    MOVEABLE = "moveable"

    @property
    def wears_by_batter(self) -> bool:
        """Whether the wear that finishes it is the point battering down."""
        return self in {FrogKind.RIGID, FrogKind.SELF_GUARDED}


class Throw(Enum):
    """How the switch is operated."""

    HAND = "hand"
    SPRING = "spring"
    POWER = "power"


_DIVERGING: Final[dict[int, Speed]] = {
    7: Speed(10),
    8: Speed(15),
    9: Speed(15),
    10: Speed(20),
    11: Speed(20),
    14: Speed(25),
    15: Speed(30),
    20: Speed(40),
}


@dataclass(frozen=True)
class Turnout:
    """One turnout, recorded at its point of switch."""

    ident: Ident
    subdivision: Ident
    point_of_switch: Milepost
    size: int
    hand: Hand
    frog: FrogKind
    throw: Throw
    leads_to: str = ""

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.TURNOUT:
            raise InputError(f"{self.ident} is not a turnout number")
        if self.subdivision.kind is not Kind.SUBDIVISION:
            raise InputError(f"{self.subdivision} is not a subdivision number")
        if self.size not in _DIVERGING:
            sizes = ", ".join(str(one) for one in sorted(_DIVERGING))
            raise InputError(f"number {self.size} is not a turnout size here, we have {sizes}")
        if self.throw is Throw.SPRING and self.frog is FrogKind.MOVEABLE:
            raise InputError("a spring switch is not built with a moveable point frog")

    @property
    def diverging_speed(self) -> Speed:
        """The speed through the diverging route, whatever the class allows."""
        return _DIVERGING[self.size]

    def speed_through(self, diverging: bool, class_speed: Speed) -> Speed:
        """What a train gets through here, on either route."""
        if not diverging:
            return class_speed
        return self.diverging_speed.slower_of(class_speed)

    def point_gap_is_a_defect(self, gap: Inches) -> bool:
        """Whether a measured gap between point and stock rail is a defect."""
        if gap.sixteenths < 0:
            raise InputError("a point gap is not negative")
        return gap >= POINT_GAP_LIMIT

    def flangeway_is_a_defect(self, width: Inches) -> bool:
        """Whether a worn frog flangeway is now too narrow."""
        return width < FROG_FLANGEWAY_MIN

    def guard_check_is_a_defect(self, measured: Inches) -> bool:
        """Whether the guard check gauge has gone below the minimum."""
        return measured < GUARD_CHECK_MIN

    def describe(self) -> str:
        """One line for the turnout list."""
        leads = f" to {self.leads_to}" if self.leads_to else ""
        return (
            f"{self.ident} {self.subdivision.tail} MP {self.point_of_switch} "
            f"no {self.size} {self.hand.value} hand {self.frog.value} frog "
            f"{self.throw.value} throw{leads}"
        )
