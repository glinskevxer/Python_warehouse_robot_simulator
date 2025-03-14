"""The record that somebody looked at a piece of railroad on a day.

An inspection record is worth more than what it found. A week with no
exceptions on it is still a week that was covered, and the compliance question
the roadmaster gets asked is almost never about defects. It is about whether
this subdivision was walked inside its cycle, by somebody qualified, over the
whole of it rather than the easy end.

So the record carries the span it covered rather than a point, and two
inspections of the same track on the same day by different methods are two
records. A hi rail trip does not see what a walk sees and the paperwork should
not pretend otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


class Method(Enum):
    """How the track was looked at."""

    WALKING = "walking"
    HI_RAIL = "hi rail"
    GEOMETRY_CAR = "geometry car"
    FLAW_DETECTOR = "flaw detector"

    @property
    def is_on_foot(self) -> bool:
        """Whether the inspector could reach down and touch what they saw."""
        return self is Method.WALKING

    @property
    def is_contracted(self) -> bool:
        """Whether it is a service bought in rather than our own people."""
        return self in {Method.GEOMETRY_CAR, Method.FLAW_DETECTOR}


class Scope(Enum):
    """What the inspection was of, which is not the same as how."""

    TRACK = "track"
    TURNOUTS = "turnouts"
    JOINT_BARS = "joint bars"
    RAIL_FLAW = "rail flaw"
    STRUCTURES = "structures"
    SPECIAL = "special"

    @property
    def methods(self) -> frozenset[Method]:
        """The methods that can carry out this scope of inspection."""
        return {
            Scope.TRACK: frozenset({Method.WALKING, Method.HI_RAIL, Method.GEOMETRY_CAR}),
            Scope.TURNOUTS: frozenset({Method.WALKING}),
            Scope.JOINT_BARS: frozenset({Method.WALKING, Method.HI_RAIL}),
            Scope.RAIL_FLAW: frozenset({Method.FLAW_DETECTOR}),
            Scope.STRUCTURES: frozenset({Method.WALKING}),
            Scope.SPECIAL: frozenset({Method.WALKING, Method.HI_RAIL}),
        }[self]


@dataclass(frozen=True)
class Inspection:
    """One person, one method, one day, one stretch of railroad."""

    ident: Ident
    subdivision: Ident
    span: Span
    on: date
    by: Ident
    method: Method
    scope: Scope
    note: str = ""

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.INSPECTION:
            raise InputError(f"{self.ident} is not an inspection number")
        if self.by.kind is not Kind.PERSON:
            raise InputError(f"{self.by} is not a person")
        if self.ident.year != self.on.year:
            raise InputError(f"{self.ident} was numbered in a different year to {self.on}")
        if self.method not in self.scope.methods:
            allowed = ", ".join(sorted(one.value for one in self.scope.methods))
            raise RuleError(
                f"a {self.scope.value} inspection is not done by {self.method.value}, "
                f"it is done by {allowed}"
            )

    @property
    def is_special(self) -> bool:
        """Whether this was run because of an event rather than on the cycle."""
        return self.scope is Scope.SPECIAL

    def covers(self, post: Milepost) -> bool:
        """Whether the inspection took in that milepost."""
        return self.span.contains(post)

    def covers_all_of(self, span: Span) -> bool:
        """Whether the inspection took in the whole of a stretch."""
        return self.span.covers(span)

    def days_before(self, other: Inspection) -> int:
        """Days from this inspection to a later one, refusing a backwards pair."""
        if other.on < self.on:
            raise InputError(f"{other.ident} on {other.on} is before {self.ident} on {self.on}")
        return (other.on - self.on).days

    def same_cycle_as(self, other: Inspection) -> bool:
        """Whether two records count towards the same cycle on the same track."""
        return (
            self.subdivision == other.subdivision
            and self.scope is other.scope
            and self.span.overlaps(other.span)
        )

    def describe(self) -> str:
        """One line for the inspection register."""
        return (
            f"{self.ident} {self.on.isoformat()} {self.subdivision.tail} {self.span} "
            f"{self.scope.value} by {self.method.value} {self.by.tail}"
        )
