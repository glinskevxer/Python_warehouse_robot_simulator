"""One handle on all the registers, so nothing above here opens a book twice.

Everything above this layer wants three or four registers at once. A bulletin
needs orders and subdivisions, a compliance page needs inspections, segments
and people. Handing each of them a book and letting them build their own
registers works, and it also means eleven places that have to be changed when
a register gains an argument.

So this is the handle. It is not a service and it holds no rules. It opens the
book, checks the schema is one this package understands, and hands out the
registers already built.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from spikemaul.store.book import Book, new_book, open_book
from spikemaul.store.crew import Gangs, People
from spikemaul.store.curves import Curves
from spikemaul.store.defects import Defects
from spikemaul.store.inspections import Inspections
from spikemaul.store.migrations import migrate, require_current, version
from spikemaul.store.orders import Orders
from spikemaul.store.runs import Runs
from spikemaul.store.segments import Segments
from spikemaul.store.structures import Bridges, Crossings
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.store.tonnage import TonnageSheets
from spikemaul.store.turnouts import Turnouts
from spikemaul.store.work import WorkOrders


@dataclass
class Records:
    """Every register in the book, built once."""

    book: Book
    subdivisions: Subdivisions = field(init=False)
    segments: Segments = field(init=False)
    curves: Curves = field(init=False)
    turnouts: Turnouts = field(init=False)
    crossings: Crossings = field(init=False)
    bridges: Bridges = field(init=False)
    inspections: Inspections = field(init=False)
    runs: Runs = field(init=False)
    defects: Defects = field(init=False)
    orders: Orders = field(init=False)
    work: WorkOrders = field(init=False)
    people: People = field(init=False)
    gangs: Gangs = field(init=False)
    tonnage: TonnageSheets = field(init=False)

    def __post_init__(self) -> None:
        self.subdivisions = Subdivisions(self.book)
        self.segments = Segments(self.book)
        self.curves = Curves(self.book)
        self.turnouts = Turnouts(self.book)
        self.crossings = Crossings(self.book)
        self.bridges = Bridges(self.book)
        self.inspections = Inspections(self.book)
        self.runs = Runs(self.book)
        self.defects = Defects(self.book)
        self.orders = Orders(self.book)
        self.work = WorkOrders(self.book)
        self.people = People(self.book)
        self.gangs = Gangs(self.book)
        self.tonnage = TonnageSheets(self.book)

    @property
    def schema(self) -> int:
        """The migration number the book is at."""
        return version(self.book)

    def close(self) -> None:
        """Close the book underneath."""
        self.book.close()

    def counts(self) -> dict[str, int]:
        """How many of each record the book holds, for the front of a report."""
        return {
            "subdivisions": self.subdivisions.count(),
            "segments": self.segments.count(),
            "curves": self.curves.count(),
            "turnouts": self.turnouts.count(),
            "crossings": self.crossings.count(),
            "bridges": self.bridges.count(),
            "inspections": self.inspections.count(),
            "defects": self.defects.count(),
            "orders": self.orders.count(),
            "work orders": self.work.count(),
            "people": self.people.count(),
            "gangs": self.gangs.count(),
        }

    def is_empty(self) -> bool:
        """Whether anything at all has been written into the book."""
        return not any(self.counts().values())


def open_records(path: str | Path) -> Records:
    """Open an existing book and refuse one this package cannot read."""
    book = open_book(path)
    require_current(book)
    return Records(book)


def start_records(path: str | Path, on: date) -> Records:
    """Make a book where there is none, and bring an old one up to date."""
    book = open_book(path, create=True)
    migrate(book, on)
    return Records(book)


def records_in_memory(on: date) -> Records:
    """A book that is thrown away, which the dry runs and the tests use."""
    book = new_book()
    migrate(book, on)
    return Records(book)
