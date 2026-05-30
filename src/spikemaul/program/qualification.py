"""Who is designated for what, and when it runs out.

A designation is a date and it lapses quietly. Nobody is stopped at the door
on the first of January; the inspections keep happening and stop counting, and
the first anybody hears about it is a compliance page with a month of holes in
it or an inspector asking to see the designation file.

So this looks forward. Everything that lapses inside a window, everything that
already has, and the scopes nobody is designated for at all, which is the one
that gets missed because it does not look like a person's problem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from spikemaul.errors import InputError
from spikemaul.model.crew import Person
from spikemaul.model.inspection import Scope

WINDOW_DAYS = 60
"""How far ahead the page looks by default."""


@dataclass(frozen=True)
class Standing:
    """One person's designation as of a day."""

    person: Person
    on: date

    @property
    def has_one(self) -> bool:
        """Whether they are designated for anything at all."""
        return bool(self.person.qualified_for)

    @property
    def days_left(self) -> int | None:
        """Days before it lapses, negative once it has."""
        until = self.person.qualified_until
        return None if until is None else (until - self.on).days

    @property
    def has_lapsed(self) -> bool:
        """Whether it has run out."""
        left = self.days_left
        return left is not None and left < 0

    def lapses_within(self, days: int) -> bool:
        """Whether it runs out inside a window, having not already."""
        left = self.days_left
        return left is not None and 0 <= left <= days

    def describe(self) -> str:
        """One line for the designation page."""
        if not self.has_one:
            return f"{self.person.name} is designated for nothing"
        scopes = ", ".join(sorted(one.value for one in self.person.qualified_for))
        if self.has_lapsed:
            return f"{self.person.name} lapsed {self.person.qualified_until}, was {scopes}"
        return f"{self.person.name} {scopes} through {self.person.qualified_until}"


def standings(people: list[Person], on: date) -> list[Standing]:
    """Everybody's designation as of a day, soonest to lapse first."""
    out = [Standing(person=one, on=on) for one in people]
    return sorted(
        out,
        key=lambda one: (one.days_left if one.days_left is not None else 10**6, one.person.name),
    )


def lapsed(people: list[Person], on: date) -> list[Standing]:
    """Everybody whose designation has run out."""
    return [one for one in standings(people, on) if one.has_lapsed]


def lapsing(people: list[Person], on: date, days: int = WINDOW_DAYS) -> list[Standing]:
    """Everybody whose designation runs out inside a window."""
    if days < 0:
        raise InputError("a window looks forward")
    return [one for one in standings(people, on) if one.lapses_within(days)]


def uncovered(people: list[Person], on: date, scopes: tuple[Scope, ...]) -> list[Scope]:
    """Scopes nobody is designated for on that day."""
    covered = {scope for one in people for scope in one.qualified_for if one.may_inspect(scope, on)}
    return [one for one in scopes if one not in covered]


def next_to_lapse(people: list[Person], on: date) -> Standing | None:
    """The designation that runs out first, or nothing where none has a date."""
    ahead = [one for one in standings(people, on) if one.days_left is not None]
    return ahead[0] if ahead else None


def window_from(on: date, days: int = WINDOW_DAYS) -> date:
    """The last day the page looks at."""
    return on + timedelta(days=days)
