"""Slow orders: a speed, a stretch of railroad, and the days it is in force.

A slow order is the only thing in this package a train crew ever sees. It says
run no faster than this between here and here, and it is right or it is wrong
with nothing in between. Everything else here exists to decide what one should
say.

Two things about them are easy to get wrong and both are on the record rather
than in the printing. An order that has come off is not deleted, because the
question of what was in force on the eighth of July is asked months later. And
an order with no end date is not an order with a very late end date, it is one
that stays until somebody takes it off, which is a different thing to report.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


class Reason(Enum):
    """Why the restriction is on, which decides who can take it off."""

    TRACK_CONDITION = "track condition"
    TIE_RENEWAL = "tie renewal"
    SURFACING = "surfacing"
    RAIL_WORK = "rail work"
    HEAT = "heat"
    WASHOUT = "washout"
    BRIDGE = "bridge"
    CROSSING_WORK = "crossing work"

    @property
    def is_planned(self) -> bool:
        """Whether the gang put it on to work under rather than found it."""
        return self in {
            Reason.TIE_RENEWAL,
            Reason.SURFACING,
            Reason.RAIL_WORK,
            Reason.CROSSING_WORK,
        }

    @property
    def comes_off_by_itself(self) -> bool:
        """Whether it lapses on its own, without anybody inspecting first."""
        return self is Reason.HEAT

    @classmethod
    def parse(cls, text: str) -> Reason:
        """Read the reason off the bulletin."""
        try:
            return cls(text.strip().lower())
        except ValueError as exc:
            named = ", ".join(one.value for one in cls)
            raise InputError(f"{text!r} is not a reason, we issue for {named}") from exc


@dataclass(frozen=True)
class SlowOrder:
    """One temporary speed restriction, as it goes on the bulletin."""

    ident: Ident
    subdivision: Ident
    span: Span
    speed: Speed
    reason: Reason
    effective: date
    authority: str
    expires: date | None = None
    lifted_on: date | None = None
    defect: Ident | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.ORDER:
            raise InputError(f"{self.ident} is not a slow order number")
        if self.ident.year != self.effective.year:
            raise InputError(f"{self.ident} was numbered in a different year to {self.effective}")
        if not self.authority.strip():
            raise InputError("a slow order carries the authority it was issued on")
        if self.expires is not None and self.expires < self.effective:
            raise InputError(f"{self.ident} comes off before it goes on")
        if self.lifted_on is not None and self.lifted_on < self.effective:
            raise InputError(f"{self.ident} was lifted before it went on")
        if self.defect is not None and self.defect.kind is not Kind.DEFECT:
            raise InputError(f"{self.defect} is not a defect number")
        if self.reason.comes_off_by_itself and self.expires is None:
            raise RuleError("a heat order carries the day it lapses")

    @property
    def is_standing(self) -> bool:
        """Whether it stays on until somebody takes it off."""
        return self.expires is None

    def in_effect_on(self, day: date) -> bool:
        """Whether a crew running that day is given this restriction."""
        if day < self.effective:
            return False
        if self.lifted_on is not None and day >= self.lifted_on:
            return False
        return not (self.expires is not None and day > self.expires)

    def covers(self, post: Milepost) -> bool:
        """Whether a milepost is inside the restricted stretch."""
        return self.span.contains(post)

    def governs_over(self, other: SlowOrder) -> bool:
        """Whether this order is the one a crew obeys where both apply."""
        return self.speed <= other.speed

    def extended(self, until: date | None) -> SlowOrder:
        """The same order with a new day it comes off, or none at all.

        An order that has been lifted is finished and cannot be extended. An
        order can be given no end date, which turns a lapsing order into a
        standing one, except a heat order, which carries the day it lapses by
        definition.
        """
        if self.lifted_on is not None:
            raise RuleError(f"{self.ident} was lifted on {self.lifted_on} and is finished")
        if until is not None and until < self.effective:
            raise RuleError(f"{self.ident} cannot come off before it went on")
        return replace(self, expires=until)

    def lifted(self, on: date) -> SlowOrder:
        """The same order with the day it came off written on it."""
        if self.lifted_on is not None:
            raise RuleError(f"{self.ident} was already lifted on {self.lifted_on}")
        return replace(self, lifted_on=on)

    def days_in_force(self, through: date) -> int:
        """How many days it has been on, up to and including a day."""
        if through < self.effective:
            return 0
        end = min(day for day in (through, self.expires, self.lifted_on) if day is not None)
        return (end - self.effective).days + 1

    def describe(self) -> str:
        """The line the bulletin prints."""
        until = f" until {self.expires.isoformat()}" if self.expires else " until removed"
        return (
            f"{self.ident} {self.subdivision.tail} {self.span} {self.speed} "
            f"{self.reason.value}{until}"
        )
