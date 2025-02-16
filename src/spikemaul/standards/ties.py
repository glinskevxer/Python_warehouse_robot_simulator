"""How many good crossties a stretch of track has to have, and where.

The count is per thirty nine foot segment, which is a rail length, and it is a
count of ties that are not defective rather than a count of ties. A segment
can hold thirty ties and fail because twelve of them are plate cut, spike
killed or split through.

Two of the three rules here are about position rather than number. A joint
needs a good tie beside it whatever the rest of the segment looks like, and a
run of defective ties in a row is worse than the same ties spread out. Both
are the reason this cannot be answered by dividing.

The curve numbers are this railroad's own standard practice rather than the
rule book's. A curve works ties harder, so the count goes up by one on
anything sharper than two degrees where the class is three or better.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from spikemaul.standards.classes import ALL, ClassOfTrack
from spikemaul.units.curvature import TANGENT, Curvature

SEGMENT_FEET: Final = 39
"""The rail length a tie count is taken over."""

JOINT_WINDOW_INCHES: Final = 24
"""How far from a joint a tie may be and still count as beside it."""

CURVE_THRESHOLD: Final = Curvature.of(2)
"""Sharper than this and the curve count applies."""


@dataclass(frozen=True)
class TieStandard:
    """The tie rules for one class of track."""

    minimum: int
    minimum_on_curve: int
    max_consecutive_defective: int

    def required(self, curve: Curvature) -> int:
        """Good ties needed in a segment, given the curve it sits in."""
        return self.minimum_on_curve if curve > CURVE_THRESHOLD else self.minimum


_TABLE: Final[dict[ClassOfTrack, TieStandard]] = {
    ClassOfTrack.EXCEPTED: TieStandard(minimum=5, minimum_on_curve=5, max_consecutive_defective=4),
    ClassOfTrack.ONE: TieStandard(minimum=5, minimum_on_curve=5, max_consecutive_defective=4),
    ClassOfTrack.TWO: TieStandard(minimum=8, minimum_on_curve=8, max_consecutive_defective=4),
    ClassOfTrack.THREE: TieStandard(minimum=8, minimum_on_curve=9, max_consecutive_defective=3),
    ClassOfTrack.FOUR: TieStandard(minimum=12, minimum_on_curve=13, max_consecutive_defective=2),
    ClassOfTrack.FIVE: TieStandard(minimum=12, minimum_on_curve=13, max_consecutive_defective=2),
}


def standard_for(track_class: ClassOfTrack) -> TieStandard:
    """The tie rules a segment held to this class is judged against."""
    return _TABLE[track_class]


def required_ties(track_class: ClassOfTrack, curve: Curvature = TANGENT) -> int:
    """Good ties a thirty nine foot segment needs at this class."""
    return standard_for(track_class).required(curve)


def class_for_tie_count(good: int, curve: Curvature = TANGENT) -> ClassOfTrack | None:
    """The highest class a count of good ties supports, or ``None`` for none."""
    if good < 0:
        raise ValueError("a segment cannot hold fewer than no good ties")
    for track_class in sorted(ALL, reverse=True):
        if good >= required_ties(track_class, curve):
            return track_class
    return None


def class_for_consecutive_defective(run: int) -> ClassOfTrack | None:
    """The highest class a run of defective ties in a row still supports."""
    if run < 0:
        raise ValueError("a run of defective ties cannot be negative")
    for track_class in sorted(ALL, reverse=True):
        if run <= standard_for(track_class).max_consecutive_defective:
            return track_class
    return None
