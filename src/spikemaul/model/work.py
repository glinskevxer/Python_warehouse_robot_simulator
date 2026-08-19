"""Work orders: what has to be done, where, by when and by whom.

A work order is not a defect. A defect is a condition the rule has something
to say about; a work order is a decision to send people and material at a
piece of railroad. Most work orders come off defects and some do not, because
a curve that needs surfacing before it gets bad enough to write a card is
exactly the work worth doing.

Quantities are carried in the unit the work is measured in, and the unit is
part of the record rather than an assumption. Four hundred is four hundred
ties on one order and four hundred feet of rail on another, and a report that
adds them has said something false.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum
from typing import Final

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.span import Span


class WorkKind(Enum):
    """What sort of work it is."""

    TIE_RENEWAL = "tie renewal"
    SURFACING = "surfacing"
    RAIL_CHANGE = "rail change"
    JOINT_REPAIR = "joint repair"
    GAUGE_REPAIR = "gauge repair"
    CROSSING_REBUILD = "crossing rebuild"
    DRAINAGE = "drainage"
    VEGETATION = "vegetation"
    TURNOUT_REPAIR = "turnout repair"

    @property
    def unit(self) -> str:
        """The unit this kind of work is counted in."""
        return _UNITS[self]

    @property
    def needs_track_time(self) -> bool:
        """Whether the gang has to hold the track to do it."""
        return self not in {WorkKind.VEGETATION, WorkKind.DRAINAGE}

    @classmethod
    def parse(cls, text: str) -> WorkKind:
        """Read the kind of work off an order."""
        try:
            return cls(text.strip().lower())
        except ValueError as exc:
            named = ", ".join(one.value for one in cls)
            raise InputError(f"{text!r} is not work we order, we order {named}") from exc


_UNITS: Final[dict[WorkKind, str]] = {
    WorkKind.TIE_RENEWAL: "ties",
    WorkKind.SURFACING: "feet",
    WorkKind.RAIL_CHANGE: "feet",
    WorkKind.JOINT_REPAIR: "joints",
    WorkKind.GAUGE_REPAIR: "feet",
    WorkKind.CROSSING_REBUILD: "crossings",
    WorkKind.DRAINAGE: "feet",
    WorkKind.VEGETATION: "acres",
    WorkKind.TURNOUT_REPAIR: "turnouts",
}


@dataclass(frozen=True)
class WorkOrder:
    """One piece of work, raised on a day and closed on another."""

    ident: Ident
    subdivision: Ident
    span: Span
    kind: WorkKind
    quantity: int
    raised_on: date
    raised_by: Ident
    due_on: date | None = None
    gang: Ident | None = None
    defect: Ident | None = None
    done_on: date | None = None
    done_quantity: int | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.WORK:
            raise InputError(f"{self.ident} is not a work order number")
        if self.ident.year != self.raised_on.year:
            raise InputError(f"{self.ident} was numbered in a different year to {self.raised_on}")
        if self.raised_by.kind is not Kind.PERSON:
            raise InputError(f"{self.raised_by} is not a person")
        if self.gang is not None and self.gang.kind is not Kind.GANG:
            raise InputError(f"{self.gang} is not a gang")
        if self.defect is not None and self.defect.kind is not Kind.DEFECT:
            raise InputError(f"{self.defect} is not a defect number")
        if self.quantity < 1:
            raise InputError(f"a {self.kind.value} order for nothing is not an order")
        if self.due_on is not None and self.due_on < self.raised_on:
            raise InputError(f"{self.ident} is due before it was raised")
        if self.done_on is not None and self.done_on < self.raised_on:
            raise InputError(f"{self.ident} was done before it was raised")
        if (self.done_on is None) != (self.done_quantity is None):
            raise RuleError("a finished order carries both the day and what was done")

    @property
    def unit(self) -> str:
        """The unit the quantity is in, which comes off the kind of work."""
        return self.kind.unit

    @property
    def is_open(self) -> bool:
        """Whether the work is still to do."""
        return self.done_on is None

    @property
    def is_assigned(self) -> bool:
        """Whether a gang has been put on it."""
        return self.gang is not None

    def is_overdue(self, on: date) -> bool:
        """Whether it is past its date and still open."""
        return self.is_open and self.due_on is not None and on > self.due_on

    def assigned_to(self, gang: Ident) -> WorkOrder:
        """The same order with a gang on it."""
        if self.gang is not None:
            raise RuleError(f"{self.ident} is already on {self.gang}")
        return replace(self, gang=gang)

    def amended(
        self, quantity: int | None = None, due_on: date | None = None, note: str | None = None
    ) -> WorkOrder:
        """The same order with the quantity or the date put right.

        Only while it is open. A finished order carries what was actually
        done, and changing what was asked for afterwards makes the shortfall a
        number nobody can check.
        """
        if not self.is_open:
            raise RuleError(f"{self.ident} was finished on {self.done_on} and stands as it is")
        wanted = self.quantity if quantity is None else quantity
        if wanted < 1:
            raise InputError(f"a {self.kind.value} order for nothing is not an order")
        if due_on is not None and due_on < self.raised_on:
            raise RuleError(f"{self.ident} cannot be due before it was raised")
        return replace(
            self,
            quantity=wanted,
            due_on=self.due_on if due_on is None else due_on,
            note=self.note if note is None else note,
        )

    def finished(self, on: date, quantity: int | None = None) -> WorkOrder:
        """The same order closed out, with what was actually done."""
        if not self.is_open:
            raise RuleError(f"{self.ident} was finished on {self.done_on}")
        done = self.quantity if quantity is None else quantity
        if done < 0:
            raise InputError("a quantity done is not negative")
        return replace(self, done_on=on, done_quantity=done)

    @property
    def shortfall(self) -> int:
        """How much of the order was not done, which is zero while it is open."""
        if self.done_quantity is None:
            return 0
        return max(self.quantity - self.done_quantity, 0)

    def describe(self) -> str:
        """One line for the work list."""
        state = "open" if self.is_open else f"done {self.done_on}"
        gang = self.gang.tail if self.gang is not None else "unassigned"
        return (
            f"{self.ident} {self.subdivision.tail} {self.span} {self.kind.value} "
            f"{self.quantity} {self.unit} {gang} {state}"
        )
