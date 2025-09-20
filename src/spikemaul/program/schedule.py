"""What the inspector has to cover this week, and what the weather just added.

The cycle work is predictable and the special work is not, so they are worked
out separately and printed together. A week's list that mixes them without
saying which is which gets the special inspection done last, and the special
inspection is the one somebody is waiting on.

A special inspection after a flood or an earthquake has no due date, it has a
train. Nothing runs over that stretch until somebody has walked it. That is
carried here as a flag rather than as a date, for the same reason the
remedial deadlines are kept on their own clocks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import InputError
from spikemaul.model.inspection import Scope
from spikemaul.program.compliance import Standing
from spikemaul.standards.inspection import Weather
from spikemaul.units.span import Span


@dataclass(frozen=True)
class Due:
    """One piece of the cycle, and when it has to be done by."""

    span: Span
    scope: Scope
    due_on: date | None
    days_left: int | None
    late: bool

    @property
    def is_now(self) -> bool:
        """Whether this is due today or already past."""
        return self.late or (self.days_left is not None and self.days_left <= 0)

    def describe(self) -> str:
        """One line for the week's list."""
        if self.due_on is None:
            return f"{self.span} {self.scope.value}, never inspected, due now"
        when = "overdue" if self.late else f"due {self.due_on.isoformat()}"
        return f"{self.span} {self.scope.value}, {when}"


@dataclass(frozen=True)
class Special:
    """An inspection the weather has just made necessary."""

    span: Span
    event: Weather
    called_on: date
    before_a_train: bool

    def describe(self) -> str:
        """One line for the week's list."""
        when = "before the next train" if self.before_a_train else "as soon as possible"
        return f"{self.span} special after {self.event.value} on {self.called_on}, {when}"


def due_from(standing: Standing, on: date) -> Due:
    """Turn a compliance standing into a line on the week's list."""
    due_on = standing.due_on
    days_left = None if due_on is None else (due_on - on).days
    return Due(
        span=standing.span,
        scope=standing.scope,
        due_on=due_on,
        days_left=days_left,
        late=standing.is_late,
    )


def due_between(standings: list[Standing], first: date, last: date) -> list[Due]:
    """Everything falling due in a range of days, soonest first.

    Anything already late is on the list whatever its date, because a stretch
    three weeks overdue does not stop being this week's work by being last
    week's as well.
    """
    if last < first:
        raise InputError("a week runs forward")
    out = []
    for standing in standings:
        due = due_from(standing, first)
        if due.late or (due.due_on is not None and first <= due.due_on <= last):
            out.append(due)
    return sorted(
        out,
        key=lambda one: (
            0 if one.late else 1,
            one.due_on or date.min,
            one.span.begin.hundredths,
        ),
    )


def special_for(event: Weather, span: Span, on: date) -> Special:
    """The special inspection an event calls for over a stretch."""
    return Special(
        span=span,
        event=event,
        called_on=on,
        before_a_train=event.before_a_train,
    )


def week_ahead(
    standings: list[Standing], specials: list[Special], first: date, last: date
) -> list[str]:
    """The week's list, specials first and then the cycle work."""
    lines = [f"week of {first.isoformat()} to {last.isoformat()}"]
    for special in sorted(specials, key=lambda one: (not one.before_a_train, one.called_on)):
        lines.append(special.describe())
    for due in due_between(standings, first, last):
        lines.append(due.describe())
    if len(lines) == 1:
        lines.append("nothing due")
    return lines
