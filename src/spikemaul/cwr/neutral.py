"""The rail neutral temperature, and the log that is the only record of it.

Neutral temperature is the rail temperature at which a length of welded rail
is in neither tension nor compression. It is set when the rail is laid and
reset when the rail is destressed, and it cannot be measured afterwards with
anything the section gang carries. So it is a log: what was done, where, on
what day, at what rail temperature, by whom.

Everything that follows from it is only as good as that log. A stretch with no
destress record has no neutral temperature, and the honest answer to what it
is standing at today is that nobody knows. This module returns nothing in that
case rather than the design temperature, because the design temperature is
what the standard says should have happened, not what did.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.span import Span
from spikemaul.units.temperature import Temperature

DESIGN_NEUTRAL = Temperature(95)
"""What this railroad lays and destresses rail to when it can choose."""

TOLERANCE = 10
"""How far either side of the design temperature is still in specification."""


@dataclass(frozen=True)
class Destress:
    """One entry in the destress log."""

    subdivision: Ident
    span: Span
    on: date
    neutral: Temperature
    by: Ident
    method: str = "heater"
    note: str = ""

    def __post_init__(self) -> None:
        if self.subdivision.kind is not Kind.SUBDIVISION:
            raise InputError(f"{self.subdivision} is not a subdivision number")
        if self.by.kind is not Kind.PERSON:
            raise InputError(f"{self.by} is not a person")
        if not self.method.strip():
            raise InputError("a destress entry says how it was done")

    @property
    def in_specification(self) -> bool:
        """Whether the rail was left inside the range this railroad lays to."""
        return abs(self.neutral.above(DESIGN_NEUTRAL)) <= TOLERANCE

    def covers(self, span: Span) -> bool:
        """Whether this entry took in the whole of a stretch."""
        return self.span.covers(span)

    def describe(self) -> str:
        """One line for the destress log."""
        state = "" if self.in_specification else ", out of specification"
        return (
            f"{self.on.isoformat()} {self.subdivision.tail} {self.span} "
            f"{self.method} to {self.neutral}{state}"
        )


def entries_covering(log: list[Destress], span: Span, on_or_before: date) -> list[Destress]:
    """Every entry that took in the whole stretch, up to a day, newest first."""
    found = [one for one in log if one.covers(span) and one.on <= on_or_before]
    return sorted(found, key=lambda one: one.on, reverse=True)


def neutral_at(log: list[Destress], span: Span, on: date) -> Temperature | None:
    """The neutral temperature of a stretch, or nothing if it has no record.

    Nothing is not the design temperature. A stretch with no entry has never
    been destressed on this railroad's watch and its neutral temperature is a
    question rather than a number.
    """
    found = entries_covering(log, span, on)
    return found[0].neutral if found else None


def last_destress(log: list[Destress], span: Span, on: date) -> Destress | None:
    """The most recent entry taking in the whole stretch."""
    found = entries_covering(log, span, on)
    return found[0] if found else None


def days_since_destress(log: list[Destress], span: Span, on: date) -> int | None:
    """Days since the stretch was last destressed, or nothing where never."""
    found = last_destress(log, span, on)
    return None if found is None else (on - found.on).days


def out_of_specification(log: list[Destress]) -> list[Destress]:
    """Entries that left the rail outside the range we lay to."""
    return [one for one in log if not one.in_specification]
