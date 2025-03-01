"""The numbers written on the paperwork, and what shape each of them is.

Every record in the book carries an identifier that somebody writes on a
defect card, a bulletin or a work order by hand. They are not opaque keys.
A defect number carries the year it was raised, a segment number carries the
subdivision it is on, and a foreman who reads DF-2025-0142 on a card knows
where to look without asking.

Because they are written by hand they are also mistyped, so every one of them
is parsed rather than accepted, and the parse is strict about the year and the
sequence width. A defect number with three digits sorts wrongly next to one
with four and that is a bug you find in October.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from spikemaul.errors import InputError

SEQUENCE_WIDTH: Final = 4
"""Digits in the sequence part of a numbered record."""


class Kind(Enum):
    """A kind of record, and the prefix its numbers carry."""

    SUBDIVISION = "SD"
    SEGMENT = "SG"
    CURVE = "CV"
    TURNOUT = "TO"
    CROSSING = "XG"
    BRIDGE = "BR"
    INSPECTION = "IN"
    DEFECT = "DF"
    ORDER = "SO"
    WORK = "WO"
    GANG = "GG"
    PERSON = "PN"

    @property
    def label(self) -> str:
        """What the office calls this kind of record out loud."""
        return {
            Kind.SUBDIVISION: "subdivision",
            Kind.SEGMENT: "segment",
            Kind.CURVE: "curve",
            Kind.TURNOUT: "turnout",
            Kind.CROSSING: "crossing",
            Kind.BRIDGE: "bridge",
            Kind.INSPECTION: "inspection",
            Kind.DEFECT: "defect",
            Kind.ORDER: "slow order",
            Kind.WORK: "work order",
            Kind.GANG: "gang",
            Kind.PERSON: "person",
        }[self]

    @property
    def is_numbered_by_year(self) -> bool:
        """Whether numbers of this kind carry the year they were raised."""
        return self in {Kind.INSPECTION, Kind.DEFECT, Kind.ORDER, Kind.WORK}

    @classmethod
    def parse(cls, text: str) -> Kind:
        """Read a kind from its prefix."""
        try:
            return cls(text.strip().upper())
        except ValueError as exc:
            raise InputError(f"{text!r} is not a kind of record") from exc


_YEARLY = re.compile(r"^([A-Z]{2})-(\d{4})-(\d{4})$")
_PLAIN = re.compile(r"^([A-Z]{2})-([A-Z0-9]{1,10})$")


@dataclass(frozen=True, order=True)
class Ident:
    """One record's number, kept in the pieces it is written in."""

    kind: Kind
    year: int | None
    tail: str

    def __post_init__(self) -> None:
        if self.kind.is_numbered_by_year:
            if self.year is None:
                raise InputError(f"a {self.kind.label} number carries the year it was raised")
            if not 1900 <= self.year <= 2999:
                raise InputError(f"{self.year} is not a year")
            if not (self.tail.isdigit() and len(self.tail) == SEQUENCE_WIDTH):
                raise InputError(f"{self.tail!r} is not a {SEQUENCE_WIDTH} digit sequence")
        else:
            if self.year is not None:
                raise InputError(f"a {self.kind.label} number does not carry a year")
            if not re.fullmatch(r"[A-Z0-9]{1,10}", self.tail):
                raise InputError(f"{self.tail!r} is not the tail of a record number")

    @classmethod
    def parse(cls, text: str, expected: Kind | None = None) -> Ident:
        """Read a record number off a card, refusing one of the wrong kind."""
        raw = text.strip().upper()
        yearly = _YEARLY.match(raw)
        plain = _PLAIN.match(raw)
        if yearly is not None:
            found = cls(Kind.parse(yearly.group(1)), int(yearly.group(2)), yearly.group(3))
        elif plain is not None:
            found = cls(Kind.parse(plain.group(1)), None, plain.group(2))
        else:
            raise InputError(f"{text!r} is not a record number")
        if expected is not None and found.kind is not expected:
            raise InputError(f"{text!r} is a {found.kind.label} number, not a {expected.label} one")
        return found

    @classmethod
    def numbered(cls, kind: Kind, year: int, sequence: int) -> Ident:
        """Build a yearly number from its sequence, as ``numbered(DEFECT, 2025, 142)``."""
        if sequence < 1 or sequence >= 10**SEQUENCE_WIDTH:
            raise InputError(f"{sequence} is not a sequence number this year can hold")
        return cls(kind, year, str(sequence).zfill(SEQUENCE_WIDTH))

    @classmethod
    def named(cls, kind: Kind, tail: str) -> Ident:
        """Build a plain number, as ``named(SEGMENT, "014")``."""
        return cls(kind, None, tail.strip().upper())

    @property
    def sequence(self) -> int:
        """The sequence part as a number, for a record numbered by year."""
        if not self.kind.is_numbered_by_year:
            raise InputError(f"a {self.kind.label} number has no sequence")
        return int(self.tail)

    def __str__(self) -> str:
        if self.year is None:
            return f"{self.kind.value}-{self.tail}"
        return f"{self.kind.value}-{self.year}-{self.tail}"


def next_number(kind: Kind, year: int, taken: list[Ident]) -> Ident:
    """The next number of that kind for that year, given the ones already used.

    Sequences are per year and do not carry over. A gap left by a cancelled
    record is not filled in, because two cards with the same number are worse
    than a number nobody used.
    """
    if not kind.is_numbered_by_year:
        raise InputError(f"a {kind.label} number is not issued by sequence")
    used = [one.sequence for one in taken if one.kind is kind and one.year == year]
    return Ident.numbered(kind, year, max(used, default=0) + 1)
