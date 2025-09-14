"""Where a piece of railroad stands against its inspection cycle.

Three things have to hold and they fail in different ways. The inspection has
to have happened, it has to have covered the whole stretch rather than the
easy end of it, and it has to have been done by somebody designated for that
scope on that day. The third is the one that gets missed, because an
inspection by somebody whose designation lapsed looks exactly like an
inspection in every register, report and file drawer.

So this module takes the people as well as the inspections, and an inspection
by somebody it cannot vouch for does not count towards the cycle. It is
reported separately rather than silently dropped, because a stretch that is
overdue and a stretch that was walked by the wrong person are two different
conversations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from spikemaul.model.crew import Person
from spikemaul.model.ids import Ident
from spikemaul.model.inspection import Inspection, Scope
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.standards.inspection import (
    Frequency,
    is_overdue,
    track_frequency,
)
from spikemaul.units.span import Span


@dataclass(frozen=True)
class Standing:
    """What one stretch's cycle looks like as of a day."""

    span: Span
    scope: Scope
    frequency: Frequency
    on: date
    last: Inspection | None
    uncounted: tuple[Inspection, ...] = field(default_factory=tuple)

    @property
    def never_inspected(self) -> bool:
        """Whether nothing that counts has ever covered this stretch."""
        return self.last is None

    @property
    def days_since(self) -> int | None:
        """Days since the last inspection that counted."""
        return None if self.last is None else (self.on - self.last.on).days

    @property
    def due_on(self) -> date | None:
        """The day the next one is due, or nothing where none has happened."""
        if self.last is None:
            return None
        return self.last.on + timedelta(days=self.frequency.max_gap_days)

    @property
    def is_late(self) -> bool:
        """Whether the cycle has run out."""
        if self.last is None:
            return True
        return is_overdue(self.frequency, self.days_since or 0)

    @property
    def days_late(self) -> int:
        """How many days past due, which is zero while it is in cycle."""
        due = self.due_on
        if due is None or self.on <= due:
            return 0
        return (self.on - due).days

    @property
    def has_uncounted(self) -> bool:
        """Whether somebody inspected this and it did not count."""
        return bool(self.uncounted)

    def describe(self) -> str:
        """One line for the compliance page."""
        note = f", {len(self.uncounted)} did not count" if self.has_uncounted else ""
        if self.never_inspected:
            return f"{self.span} {self.scope.value}, never inspected{note}"
        state = f"{self.days_late} days late" if self.is_late else "in cycle"
        return (
            f"{self.span} {self.scope.value}, last {self.last.on if self.last else ''}, "
            f"{state}{note}"
        )


def counted(
    inspections: list[Inspection], people: dict[Ident, Person], scope: Scope
) -> tuple[list[Inspection], list[Inspection]]:
    """Split inspections into the ones that count and the ones that do not."""
    good: list[Inspection] = []
    bad: list[Inspection] = []
    for one in inspections:
        person = people.get(one.by)
        if person is not None and person.may_inspect(scope, one.on):
            good.append(one)
        else:
            bad.append(one)
    return good, bad


def standing_for(
    span: Span,
    scope: Scope,
    track_class: ClassOfTrack,
    kind: TrackKind,
    inspections: list[Inspection],
    people: dict[Ident, Person],
    on: date,
) -> Standing:
    """Work out where a stretch stands as of a day.

    ``inspections`` is everything recorded for the scope on the subdivision.
    What it does with them is the point: only the ones covering the whole
    stretch, on or before the day, by a designated person, count.
    """
    over = [one for one in inspections if one.scope is scope and one.on <= on]
    covering = [one for one in over if one.covers_all_of(span)]
    good, bad = counted(covering, people, scope)
    last = max(good, key=lambda one: (one.on, str(one.ident))) if good else None
    uncounted = tuple(one for one in bad if last is None or one.on > last.on)
    return Standing(
        span=span,
        scope=scope,
        frequency=track_frequency(track_class, kind),
        on=on,
        last=last,
        uncounted=uncounted,
    )


def late(standings: list[Standing]) -> list[Standing]:
    """The stretches out of cycle, worst first."""
    return sorted(
        (one for one in standings if one.is_late),
        key=lambda one: (-one.days_late, one.span.begin.hundredths),
    )


def gap_between(first: Inspection, second: Inspection, frequency: Frequency) -> str:
    """Whether two inspections are a legal cycle apart, in words.

    Two inspections a day apart on a weekly cycle do not cover the week, and
    the register will happily hold both. This names what is wrong with them.
    """
    days = first.days_before(second)
    if days < frequency.minimum_gap_days:
        return f"{days} days apart, closer than the {frequency.minimum_gap_days} the cycle wants"
    if days > frequency.max_gap_days:
        return f"{days} days apart, past the {frequency.max_gap_days} the cycle allows"
    return f"{days} days apart"
