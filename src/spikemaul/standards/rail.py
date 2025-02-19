"""Rail sections, how much head they may lose, and how often they get tested.

Rail wears in two directions at once. The head goes down under the wheel and
the gauge side goes in under the flange, and neither number on its own says
whether the rail is finished. The combined figure, vertical plus half the
gauge face, is the one this railroad condemns on, and all three are read off a
row picked by how heavy the rail is and what class the track is held to.

Internal rail flaw testing is on a tonnage cycle with a calendar backstop, and
the lower classes have no requirement at all. That is not an oversight. A
branch carrying two trains a week does not develop a detail fracture on the
same clock as the main.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from spikemaul.errors import InputError
from spikemaul.standards.classes import ALL, ClassOfTrack
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.tonnage import Tonnage

SHARP_CURVE: Final = Curvature.of(4)
"""Sharper than this and the gauge face limit comes in a sixteenth."""


@dataclass(frozen=True)
class RailSection:
    """A rail section as it was rolled, before anything wore off it."""

    name: str
    pounds_per_yard: int
    head_height: Inches

    @property
    def band(self) -> str:
        """Which row of the wear table this section is judged on."""
        if self.pounds_per_yard < 110:
            return "light"
        if self.pounds_per_yard <= 130:
            return "medium"
        return "heavy"


SECTIONS: Final[dict[str, RailSection]] = {
    "90 ASCE": RailSection("90 ASCE", 90, Inches.parse("1 3/8")),
    "100 RA": RailSection("100 RA", 100, Inches.parse("1 1/2")),
    "115 RE": RailSection("115 RE", 115, Inches.parse("1 11/16")),
    "132 RE": RailSection("132 RE", 132, Inches.parse("1 13/16")),
    "136 RE": RailSection("136 RE", 136, Inches.parse("1 13/16")),
}


def section(name: str) -> RailSection:
    """Look up a rail section by the name stencilled on the web."""
    try:
        return SECTIONS[name.strip().upper()]
    except KeyError as exc:
        named = ", ".join(sorted(SECTIONS))
        raise InputError(f"{name!r} is not a rail section here, we have {named}") from exc


@dataclass(frozen=True)
class WearLimits:
    """How much head a rail may have lost and stay in the track."""

    vertical: Inches
    gauge_face: Inches
    combined: Inches

    def tightened_for(self, curve: Curvature) -> WearLimits:
        """The same limits with the curve allowance taken off the gauge face."""
        if curve <= SHARP_CURVE:
            return self
        return WearLimits(
            vertical=self.vertical,
            gauge_face=self.gauge_face - Inches.of(0, 1, 16),
            combined=self.combined,
        )


def _row(vertical: str, gauge_face: str, combined: str) -> WearLimits:
    return WearLimits(Inches.parse(vertical), Inches.parse(gauge_face), Inches.parse(combined))


_WEAR: Final[dict[str, dict[ClassOfTrack, WearLimits]]] = {
    "light": {
        ClassOfTrack.EXCEPTED: _row("5/8", "3/4", "15/16"),
        ClassOfTrack.ONE: _row("1/2", "5/8", "13/16"),
        ClassOfTrack.TWO: _row("1/2", "5/8", "13/16"),
        ClassOfTrack.THREE: _row("7/16", "9/16", "11/16"),
        ClassOfTrack.FOUR: _row("3/8", "1/2", "5/8"),
        ClassOfTrack.FIVE: _row("3/8", "1/2", "5/8"),
    },
    "medium": {
        ClassOfTrack.EXCEPTED: _row("3/4", "7/8", "1 1/8"),
        ClassOfTrack.ONE: _row("5/8", "3/4", "15/16"),
        ClassOfTrack.TWO: _row("5/8", "3/4", "15/16"),
        ClassOfTrack.THREE: _row("9/16", "11/16", "13/16"),
        ClassOfTrack.FOUR: _row("1/2", "5/8", "3/4"),
        ClassOfTrack.FIVE: _row("1/2", "5/8", "3/4"),
    },
    "heavy": {
        ClassOfTrack.EXCEPTED: _row("7/8", "1", "1 1/4"),
        ClassOfTrack.ONE: _row("3/4", "7/8", "1 1/16"),
        ClassOfTrack.TWO: _row("3/4", "7/8", "1 1/16"),
        ClassOfTrack.THREE: _row("11/16", "13/16", "15/16"),
        ClassOfTrack.FOUR: _row("5/8", "3/4", "7/8"),
        ClassOfTrack.FIVE: _row("5/8", "3/4", "7/8"),
    },
}


@dataclass(frozen=True)
class FlawCycle:
    """How often a rail gets tested for what is inside it."""

    tonnage: Tonnage | None
    days: int | None

    @property
    def is_required(self) -> bool:
        """Whether this class has a flaw testing requirement at all."""
        return self.tonnage is not None or self.days is not None


_FLAW: Final[dict[ClassOfTrack, FlawCycle]] = {
    ClassOfTrack.EXCEPTED: FlawCycle(None, None),
    ClassOfTrack.ONE: FlawCycle(None, None),
    ClassOfTrack.TWO: FlawCycle(None, None),
    ClassOfTrack.THREE: FlawCycle(Tonnage.of(40), 365),
    ClassOfTrack.FOUR: FlawCycle(Tonnage.of(30), 210),
    ClassOfTrack.FIVE: FlawCycle(Tonnage.of(20), 180),
}


def wear_limits(
    rail: RailSection,
    track_class: ClassOfTrack,
    curve: Curvature = TANGENT,
) -> WearLimits:
    """The wear limits for a section held to a class, curve allowance included."""
    return _WEAR[rail.band][track_class].tightened_for(curve)


def combined_wear(vertical: Inches, gauge_face: Inches) -> Inches:
    """Vertical wear plus half the gauge face, which is what we condemn on."""
    if vertical.sixteenths < 0 or gauge_face.sixteenths < 0:
        raise InputError("rail does not wear backwards")
    return vertical + Inches(gauge_face.sixteenths // 2)


def class_for_wear(
    rail: RailSection,
    vertical: Inches,
    gauge_face: Inches,
    curve: Curvature = TANGENT,
) -> ClassOfTrack | None:
    """The highest class a worn rail still holds, or ``None`` if it is done."""
    both = combined_wear(vertical, gauge_face)
    for track_class in sorted(ALL, reverse=True):
        limits = wear_limits(rail, track_class, curve)
        if (
            vertical <= limits.vertical
            and gauge_face <= limits.gauge_face
            and both <= limits.combined
        ):
            return track_class
    return None


def flaw_cycle(track_class: ClassOfTrack) -> FlawCycle:
    """The flaw testing cycle for a class, which may be no cycle at all."""
    return _FLAW[track_class]
