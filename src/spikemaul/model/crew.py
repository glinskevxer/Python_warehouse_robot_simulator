"""The people and the gangs, and what each of them is signed off to do.

Qualification is the part that matters here. Part 213 does not care how good
an inspector is, it cares that the railroad has designated them, in writing,
for the kind of inspection they carried out, and that the designation had not
lapsed on the day they carried it out. An inspection by somebody whose
qualification ran out in March is not a bad inspection, it is not an
inspection, and the cycle it was supposed to cover is open.

A gang is a foreman and a headcount, plus whatever machines are assigned to
it. The machines are recorded because a tie gang without a spiker is a tie
gang that is not renewing ties this week.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Scope


class Craft(Enum):
    """What somebody does, which is not the same as what they may sign for."""

    ROADMASTER = "roadmaster"
    FOREMAN = "foreman"
    TRACKMAN = "trackman"
    OPERATOR = "machine operator"
    WELDER = "welder"
    INSPECTOR = "inspector"

    @property
    def may_hold_track_authority(self) -> bool:
        """Whether this craft can take track time in their own name."""
        return self in {Craft.ROADMASTER, Craft.FOREMAN, Craft.INSPECTOR}


@dataclass(frozen=True)
class Person:
    """One employee, and the scopes of inspection they are designated for."""

    ident: Ident
    name: str
    craft: Craft
    qualified_for: frozenset[Scope] = frozenset()
    qualified_until: date | None = None

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.PERSON:
            raise InputError(f"{self.ident} is not a person number")
        if not self.name.strip():
            raise InputError("a person has a name")
        if self.qualified_for and self.qualified_until is None:
            raise RuleError(f"{self.name} is designated but the designation has no end date")
        if self.qualified_until is not None and not self.qualified_for:
            raise RuleError(f"{self.name} has a designation date but nothing designated for")

    @property
    def initials(self) -> str:
        """What they sign a card with, which is the tail of their number."""
        return self.ident.tail

    def may_inspect(self, scope: Scope, on: date) -> bool:
        """Whether they were designated for that scope on that day."""
        if scope not in self.qualified_for:
            return False
        return self.qualified_until is not None and on <= self.qualified_until

    def requalified(self, until: date, scopes: frozenset[Scope] | None = None) -> Person:
        """The same person with the designation renewed to a later date."""
        wanted = scopes if scopes is not None else self.qualified_for
        if not wanted:
            raise RuleError(f"{self.name} cannot be requalified for nothing")
        if self.qualified_until is not None and until <= self.qualified_until:
            raise RuleError(f"{self.name} is already designated through {self.qualified_until}")
        return replace(self, qualified_for=wanted, qualified_until=until)

    def describe(self) -> str:
        """One line for the qualification register."""
        if not self.qualified_for:
            return f"{self.ident} {self.name}, {self.craft.value}, no designation"
        scopes = ", ".join(sorted(one.value for one in self.qualified_for))
        return (
            f"{self.ident} {self.name}, {self.craft.value}, {scopes} through {self.qualified_until}"
        )


@dataclass(frozen=True)
class Gang:
    """A foreman, a headcount and the machines they have this week."""

    ident: Ident
    name: str
    foreman: Ident
    headcount: int
    machines: tuple[str, ...] = ()
    headquarters: str = ""

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.GANG:
            raise InputError(f"{self.ident} is not a gang number")
        if self.foreman.kind is not Kind.PERSON:
            raise InputError(f"{self.foreman} is not a person")
        if self.headcount < 1:
            raise InputError("a gang is at least one person")
        if len(set(self.machines)) != len(self.machines):
            raise InputError("a machine is assigned to a gang once")

    def has(self, machine: str) -> bool:
        """Whether a machine is assigned to this gang."""
        return machine.strip().lower() in {one.lower() for one in self.machines}

    def with_machine(self, machine: str) -> Gang:
        """The same gang with another machine assigned to it."""
        if self.has(machine):
            raise RuleError(f"{machine} is already on {self.name}")
        return replace(self, machines=(*self.machines, machine))

    def describe(self) -> str:
        """One line for the gang list."""
        machines = ", ".join(self.machines) if self.machines else "no machines"
        where = f" at {self.headquarters}" if self.headquarters else ""
        return f"{self.ident} {self.name}, {self.headcount} men{where}, {machines}"
