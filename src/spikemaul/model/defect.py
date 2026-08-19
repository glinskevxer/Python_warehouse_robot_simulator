"""A defect card: what was found, what class it leaves, and what happens now.

The card carries the reading rather than a verdict. A gauge of 57 7/8 is a
fact; whether it is a defect depends on the class the track is being held to,
and the class can change tomorrow. So the record holds the highest class the
condition itself meets, which is a property of the condition, and works out
the remedial action against the class the track is carrying at the time it is
asked.

That is why a card that was a restriction in June can be an out of service in
July without anybody touching it. The track went up a class and the condition
did not move.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import Enum

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.standards.remedial import Clock, RemedialAction, decide
from spikemaul.units.milepost import Milepost


class Condition(Enum):
    """What sort of thing was found."""

    GAUGE = "gauge"
    CROSSLEVEL = "crosslevel"
    WARP = "warp"
    ALIGNMENT = "alignment"
    PROFILE = "profile"
    ELEVATION = "elevation"
    TIES = "ties"
    RAIL_WEAR = "rail wear"
    RAIL_BREAK = "rail break"
    JOINT_BAR = "joint bar"
    SWITCH_POINT = "switch point"
    FROG = "frog"
    GUARD_RAIL = "guard rail"
    BALLAST = "ballast"
    DRAINAGE = "drainage"
    VEGETATION = "vegetation"

    @property
    def is_geometry(self) -> bool:
        """Whether the geometry car can find it without anybody walking."""
        return self in {
            Condition.GAUGE,
            Condition.CROSSLEVEL,
            Condition.WARP,
            Condition.ALIGNMENT,
            Condition.PROFILE,
            Condition.ELEVATION,
        }

    @property
    def stops_trains(self) -> bool:
        """Whether finding one of these stops traffic whatever it measures."""
        return self is Condition.RAIL_BREAK

    @classmethod
    def parse(cls, text: str) -> Condition:
        """Read the condition off a defect card."""
        try:
            return cls(text.strip().lower())
        except ValueError as exc:
            named = ", ".join(one.value for one in cls)
            raise InputError(f"{text!r} is not a condition, we record {named}") from exc


@dataclass(frozen=True)
class Defect:
    """One condition found at one place on one day."""

    ident: Ident
    subdivision: Ident
    at: Milepost
    found_on: date
    found_by: Ident
    condition: Condition
    reading: str
    meets: ClassOfTrack | None
    inspection: Ident | None = None
    repaired_on: date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.DEFECT:
            raise InputError(f"{self.ident} is not a defect number")
        if self.found_by.kind is not Kind.PERSON:
            raise InputError(f"{self.found_by} is not a person")
        if self.ident.year != self.found_on.year:
            raise InputError(f"{self.ident} was numbered in a different year to {self.found_on}")
        if self.inspection is not None and self.inspection.kind is not Kind.INSPECTION:
            raise InputError(f"{self.inspection} is not an inspection number")
        if self.repaired_on is not None and self.repaired_on < self.found_on:
            raise InputError(f"{self.ident} was repaired before it was found")
        if self.condition.stops_trains and self.meets is not None:
            raise RuleError(f"a {self.condition.value} does not meet a class of track")
        if not self.reading.strip():
            raise InputError("a defect card carries what was measured")

    @property
    def is_open(self) -> bool:
        """Whether the condition is still in the track."""
        return self.repaired_on is None

    def action(self, held_at: ClassOfTrack) -> RemedialAction:
        """The remedial action, against the class the track carries today."""
        return decide(held_at, self.meets)

    def due_on(self, held_at: ClassOfTrack) -> date | None:
        """The date the repair is due, where the deadline is on the calendar.

        A deadline in trains or inspections has no date and the answer is
        ``None`` rather than a date worked out from a guess about traffic.
        """
        deadline = self.action(held_at).deadline
        if deadline is None or deadline.clock is not Clock.DAYS:
            return None
        return self.found_on + timedelta(days=deadline.count)

    def is_overdue(self, held_at: ClassOfTrack, on: date) -> bool:
        """Whether the repair window has run out as of a date."""
        if not self.is_open:
            return False
        due = self.due_on(held_at)
        return due is not None and on > due

    def amended(
        self,
        reading: str | None = None,
        meets: ClassOfTrack | None = None,
        note: str | None = None,
    ) -> Defect:
        """The same card with the reading or the class put right.

        Only an open card. A repaired card is a record of what was found and
        what was done about it, and changing that after the fact is how an
        inspector ends up reading two different stories about one morning.
        The class is passed as it is, ``None`` included, so a card can be
        corrected to meeting nothing.
        """
        if not self.is_open:
            raise RuleError(f"{self.ident} was repaired on {self.repaired_on} and stands as it is")
        return replace(
            self,
            reading=self.reading if reading is None else reading,
            meets=meets,
            note=self.note if note is None else note,
        )

    def repaired(self, on: date) -> Defect:
        """The same card with the repair written on it."""
        if not self.is_open:
            raise RuleError(f"{self.ident} was already repaired on {self.repaired_on}")
        return replace(self, repaired_on=on)

    def describe(self) -> str:
        """One line for the exception log."""
        meets = "nothing" if self.meets is None else str(self.meets)
        state = "open" if self.is_open else f"repaired {self.repaired_on}"
        return (
            f"{self.ident} {self.found_on.isoformat()} {self.subdivision.tail} MP {self.at} "
            f"{self.condition.value} {self.reading} meets {meets}, {state}"
        )
