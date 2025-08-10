"""Rail wear, measured on the head and projected against tonnage.

A wear reading is two numbers on one rail at one place: how far the head has
gone down and how far the gauge side has gone in. Neither of them condemns the
rail on its own and the combined figure often does, which is the whole reason
both are written down.

The projection is the part the roadmaster actually plans off. Two readings on
the same rail a year apart, with the tonnage between them, give a wear rate in
thirty seconds of an inch per million gross tons, and that says which curve
needs rail before the next budget rather than which curve needs rail today.
The rate is only as good as the two readings, so a projection off readings
taken by different people with different gauges is worth exactly what it cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from spikemaul.errors import InputError
from spikemaul.geometry.finding import Finding
from spikemaul.model.defect import Condition
from spikemaul.model.side import Hand
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.rail import class_for_wear, combined_wear, section, wear_limits
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.tonnage import Tonnage


@dataclass(frozen=True)
class WearReading:
    """One rail measured at one place on one day."""

    at: Milepost
    hand: Hand
    rail_section: str
    vertical: Inches
    gauge_face: Inches
    measured_on: date
    curve: Curvature = TANGENT

    def __post_init__(self) -> None:
        section(self.rail_section)
        if self.vertical.sixteenths < 0 or self.gauge_face.sixteenths < 0:
            raise InputError("rail does not wear backwards")

    @property
    def combined(self) -> Inches:
        """Vertical plus half the gauge face, which is what condemns rail."""
        return combined_wear(self.vertical, self.gauge_face)

    def class_supported(self) -> ClassOfTrack | None:
        """The highest class this rail still holds."""
        return class_for_wear(
            section(self.rail_section), self.vertical, self.gauge_face, self.curve
        )

    def left_to_lose(self, track_class: ClassOfTrack) -> Inches:
        """Combined wear the rail has left before it fails a class."""
        limits = wear_limits(section(self.rail_section), track_class, self.curve)
        return Inches(max(limits.combined.sixteenths - self.combined.sixteenths, 0))

    def describe(self) -> str:
        """One line for the rail wear listing."""
        holds = self.class_supported()
        held = "nothing" if holds is None else str(holds)
        return (
            f"MP {self.at} {self.hand.value} rail {self.rail_section} "
            f"vertical {self.vertical} gauge face {self.gauge_face} holds {held}"
        )


def wear_findings(readings: list[WearReading], held_at: ClassOfTrack) -> list[Finding]:
    """Every reading that does not hold the class the track is held to."""
    out = []
    for reading in readings:
        meets = reading.class_supported()
        if meets is not None and meets >= held_at:
            continue
        out.append(
            Finding(
                at=reading.at,
                condition=Condition.RAIL_WEAR,
                reading=reading.combined,
                meets=meets,
            )
        )
    return out


def wear_rate(first: WearReading, second: WearReading, over: Tonnage) -> Decimal:
    """Sixteenths of combined wear per million gross tons between two readings.

    Refuses a pair that is not the same rail at the same place, because a rate
    off two different rails is a number with a unit and no meaning.
    """
    if first.at != second.at or first.hand is not second.hand:
        raise InputError("a wear rate needs two readings of the same rail at the same place")
    if second.measured_on <= first.measured_on:
        raise InputError("the second reading is not after the first")
    if over.hundredths <= 0:
        raise InputError("a wear rate needs tonnage between the two readings")
    gone = second.combined.sixteenths - first.combined.sixteenths
    if gone < 0:
        raise InputError("rail does not grow back, so check which reading is which")
    return (Decimal(gone) / over.mgt).quantize(Decimal("0.001"))


def tonnage_left(reading: WearReading, track_class: ClassOfTrack, rate: Decimal) -> Tonnage:
    """Tonnage this rail has left before it fails a class, at that rate."""
    if rate <= 0:
        raise InputError("rail that is not wearing has no date to plan against")
    left = Decimal(reading.left_to_lose(track_class).sixteenths) / rate
    return Tonnage.of(left.quantize(Decimal("0.01")))
