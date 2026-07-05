"""What the work needs on the ground before the gang gets there.

A work order says four hundred ties. The gang cannot renew four hundred ties
with four hundred ties: it needs the plates that go under them, the spikes
that hold them and the ballast to put back what the tamper disturbs. None of
that is on the order, all of it is in somebody's head, and the day it is not
is the day a gang stands around at ten in the morning.

The rates are this railroad's own and they are written here as numbers with
names rather than buried in a calculation. They are worth arguing about, which
is a reason to keep them where they can be found.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from spikemaul.model.work import WorkKind
from spikemaul.work.needs import Need

PLATES_PER_TIE: Final = 2
SPIKES_PER_TIE: Final = 4
BALLAST_TONS_PER_TIE: Final = 0.7
"""What goes in with a renewed tie, ballast included because the gang surfaces after."""

BALLAST_TONS_PER_FOOT: Final = 0.35
"""Ballast a surfacing gang puts in per foot of track lifted."""

JOINT_BARS_PER_RAIL: Final = 2
BOLTS_PER_JOINT: Final = 4
RAIL_LENGTH_FEET: Final = 39
"""A stick of rail, which is what rail is ordered in."""


@dataclass(frozen=True)
class Material:
    """One thing the work needs, in the unit it is ordered in."""

    name: str
    quantity: float
    unit: str

    def describe(self) -> str:
        """One line for the material sheet."""
        rounded = int(self.quantity) if float(self.quantity).is_integer() else self.quantity
        return f"{rounded} {self.unit} {self.name}"


def for_need(need: Need) -> list[Material]:
    """What one piece of work needs on the ground."""
    if need.kind is WorkKind.TIE_RENEWAL:
        return [
            Material("crossties", need.quantity, "each"),
            Material("tie plates", need.quantity * PLATES_PER_TIE, "each"),
            Material("spikes", need.quantity * SPIKES_PER_TIE, "each"),
            Material("ballast", round(need.quantity * BALLAST_TONS_PER_TIE, 1), "tons"),
        ]
    if need.kind is WorkKind.SURFACING:
        return [Material("ballast", round(need.quantity * BALLAST_TONS_PER_FOOT, 1), "tons")]
    if need.kind is WorkKind.RAIL_CHANGE:
        sticks = -(-need.quantity // RAIL_LENGTH_FEET)
        return [
            Material("rail", need.quantity, "feet"),
            Material("joint bars", sticks * JOINT_BARS_PER_RAIL, "each"),
            Material("track bolts", sticks * JOINT_BARS_PER_RAIL * BOLTS_PER_JOINT, "each"),
        ]
    if need.kind is WorkKind.JOINT_REPAIR:
        return [
            Material("joint bars", need.quantity * JOINT_BARS_PER_RAIL, "each"),
            Material("track bolts", need.quantity * BOLTS_PER_JOINT, "each"),
        ]
    if need.kind is WorkKind.GAUGE_REPAIR:
        return [Material("spikes", need.quantity, "each")]
    if need.kind is WorkKind.CROSSING_REBUILD:
        return [
            Material("crossing panels", need.quantity, "each"),
            Material("ballast", round(need.quantity * 20, 1), "tons"),
        ]
    return []


def for_needs(needs: list[Need]) -> list[Material]:
    """Everything a list of work needs, added up by material and unit."""
    totals: dict[tuple[str, str], float] = {}
    for need in needs:
        for one in for_need(need):
            key = (one.name, one.unit)
            totals[key] = totals.get(key, 0.0) + one.quantity
    return [
        Material(name=name, quantity=round(quantity, 1), unit=unit)
        for (name, unit), quantity in sorted(totals.items())
    ]


def sheet(needs: list[Need]) -> list[str]:
    """The material sheet, as the lines that get printed."""
    found = for_needs(needs)
    if not found:
        return ["nothing to order"]
    return [one.describe() for one in found]
