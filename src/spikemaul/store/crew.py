"""The people and gang registers.

The qualification scopes are a set, and a set in one column is a compromise.
It is written as a sorted comma separated list, which is readable in a sqlite
browser and sorts stably, and it is read back through the same enumeration
every other scope goes through so a value this version does not know is
refused rather than silently dropped.

A separate table would be tidier and would be five joins in the reports for a
list that never has more than six things on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from spikemaul.errors import BookError
from spikemaul.model.crew import Craft, Gang, Person
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Scope
from spikemaul.store.codec import (
    decode_enum,
    decode_ident,
    decode_optional_date,
    encode_enum,
    encode_ident,
    encode_optional_date,
)
from spikemaul.store.register import Register

SEPARATOR = ","
"""What the scope list and the machine list are joined with."""


def _joined(values: object) -> list[str]:
    if not isinstance(values, str):
        raise BookError(f"{values!r} is not a list column")
    return [one for one in values.split(SEPARATOR) if one]


@dataclass
class People(Register[Person]):
    """Everybody the track department has on the books."""

    table: ClassVar[str] = "people"
    kind: ClassVar[Kind] = Kind.PERSON
    ordered_by: ClassVar[str] = "ident"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "name",
        "craft",
        "qualified_for",
        "qualified_until",
    )

    def ident_of(self, record: Person) -> Ident:
        """The person's number."""
        return record.ident

    def row_of(self, record: Person) -> tuple[Any, ...]:
        """The person as columns, scopes joined into one."""
        scopes = SEPARATOR.join(sorted(encode_enum(one) for one in record.qualified_for))
        return (
            encode_ident(record.ident),
            record.name,
            encode_enum(record.craft),
            scopes,
            encode_optional_date(record.qualified_until),
        )

    def record_of(self, row: Any) -> Person:
        """The columns back as a person."""
        fields = dict(row)
        scopes = frozenset(decode_enum(Scope, one) for one in _joined(fields["qualified_for"]))
        return Person(
            ident=decode_ident(fields["ident"], Kind.PERSON),
            name=str(fields["name"]),
            craft=decode_enum(Craft, fields["craft"]),
            qualified_for=scopes,
            qualified_until=decode_optional_date(fields["qualified_until"]),
        )

    def qualified_for(self, scope: Scope) -> list[Person]:
        """Everybody designated for a scope, lapsed or not."""
        return [one for one in self.all() if scope in one.qualified_for]

    def of_craft(self, craft: Craft) -> list[Person]:
        """Everybody of one craft."""
        return self.where("craft = ?", (encode_enum(craft),))


@dataclass
class Gangs(Register[Gang]):
    """Every gang on the property."""

    table: ClassVar[str] = "gangs"
    kind: ClassVar[Kind] = Kind.GANG
    ordered_by: ClassVar[str] = "ident"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "name",
        "foreman",
        "headcount",
        "machines",
        "headquarters",
    )

    def ident_of(self, record: Gang) -> Ident:
        """The gang number."""
        return record.ident

    def row_of(self, record: Gang) -> tuple[Any, ...]:
        """The gang as columns, machines joined into one."""
        return (
            encode_ident(record.ident),
            record.name,
            encode_ident(record.foreman),
            record.headcount,
            SEPARATOR.join(record.machines),
            record.headquarters,
        )

    def record_of(self, row: Any) -> Gang:
        """The columns back as a gang."""
        fields = dict(row)
        return Gang(
            ident=decode_ident(fields["ident"], Kind.GANG),
            name=str(fields["name"]),
            foreman=decode_ident(fields["foreman"], Kind.PERSON),
            headcount=int(fields["headcount"]),
            machines=tuple(_joined(fields["machines"])),
            headquarters=str(fields["headquarters"]),
        )

    def with_machine(self, machine: str) -> list[Gang]:
        """Every gang that has one of a machine assigned to it."""
        return [one for one in self.all() if one.has(machine)]

    def led_by(self, foreman: Ident) -> list[Gang]:
        """Every gang a foreman has."""
        return self.where("foreman = ?", (str(foreman),))
