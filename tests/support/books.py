"""Books and records the tests build on, so no test has to spell one out."""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Subdivision
from spikemaul.store.book import Book, new_book
from spikemaul.store.migrations import migrate
from spikemaul.units.chainage import Chainage, Equation
from spikemaul.units.milepost import Milepost

OPENED_ON = date(2025, 1, 6)


def a_book() -> Book:
    """A book in memory with the schema on it."""
    book = new_book()
    migrate(book, OPENED_ON)
    return book


def a_chainage() -> Chainage:
    """The Plains subdivision mileposting, with both of its equations."""
    return Chainage(
        Milepost.parse("0.00"),
        Milepost.parse("120.00"),
        (
            Equation(Milepost.parse("61.40"), Milepost.parse("61.15")),
            Equation(Milepost.parse("94.00"), Milepost.parse("94.60")),
        ),
    )


def a_subdivision(code: str = "PLAINS", name: str = "Plains") -> Subdivision:
    """A subdivision record, equations and all."""
    return Subdivision(Ident.named(Kind.SUBDIVISION, code), name, a_chainage())


def a_plain_subdivision(code: str = "RIVER", name: str = "River") -> Subdivision:
    """A subdivision whose mileposting was never equated."""
    return Subdivision(
        Ident.named(Kind.SUBDIVISION, code),
        name,
        Chainage(Milepost.parse("0.00"), Milepost.parse("54.00")),
    )
