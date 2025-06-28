"""The monthly tonnage sheets, as they arrive from the operating department.

Tonnage is kept per subdivision and per month, because that is the shape of
what arrives. It is not kept per segment. Every train that runs the Plains
runs all of it, so splitting one figure across forty segments would be
inventing detail the sheet does not have and then reporting it as though
somebody had counted.

Where a branch really does carry different traffic, it is a different
subdivision, which is how the railroad already thinks about it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import DuplicateError, InputError, NotFoundError
from spikemaul.model.ids import Ident
from spikemaul.store.book import Book
from spikemaul.store.codec import decode_tonnage, encode_ident, encode_tonnage
from spikemaul.units.tonnage import ZERO, Tonnage


@dataclass(frozen=True)
class MonthlyTonnage:
    """One month's figure for one subdivision."""

    subdivision: Ident
    year: int
    month: int
    tonnage: Tonnage

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise InputError(f"{self.month} is not a month")

    @property
    def first_day(self) -> date:
        """The first of the month, which is what ranges are compared on."""
        return date(self.year, self.month, 1)

    def describe(self) -> str:
        """One line for the tonnage listing."""
        return f"{self.subdivision.tail} {self.year}-{self.month:02d} {self.tonnage}"


@dataclass
class TonnageSheets:
    """Every monthly tonnage figure in the book."""

    book: Book

    def add(self, sheet: MonthlyTonnage) -> None:
        """Write a month's figure, refusing to overwrite one already there."""
        if self.has(sheet.subdivision, sheet.year, sheet.month):
            raise DuplicateError(
                "tonnage sheet", f"{sheet.subdivision.tail} {sheet.year}-{sheet.month:02d}"
            )
        self.book.execute(
            "INSERT INTO tonnage (subdivision, year, month, hundredths) VALUES (?,?,?,?)",
            (
                encode_ident(sheet.subdivision),
                sheet.year,
                sheet.month,
                encode_tonnage(sheet.tonnage),
            ),
        )

    def has(self, subdivision: Ident, year: int, month: int) -> bool:
        """Whether that month has been posted."""
        found = self.book.one(
            "SELECT 1 FROM tonnage WHERE subdivision = ? AND year = ? AND month = ?",
            (str(subdivision), year, month),
        )
        return found is not None

    def get(self, subdivision: Ident, year: int, month: int) -> MonthlyTonnage:
        """One month's figure."""
        row = self.book.one(
            "SELECT hundredths FROM tonnage WHERE subdivision = ? AND year = ? AND month = ?",
            (str(subdivision), year, month),
        )
        if row is None:
            raise NotFoundError("tonnage sheet", f"{subdivision.tail} {year}-{month:02d}")
        return MonthlyTonnage(subdivision, year, month, decode_tonnage(row["hundredths"]))

    def correct(self, sheet: MonthlyTonnage) -> None:
        """Write a month's figure over one already posted, which happens."""
        if not self.has(sheet.subdivision, sheet.year, sheet.month):
            raise NotFoundError(
                "tonnage sheet", f"{sheet.subdivision.tail} {sheet.year}-{sheet.month:02d}"
            )
        self.book.execute(
            "UPDATE tonnage SET hundredths = ? WHERE subdivision = ? AND year = ? AND month = ?",
            (encode_tonnage(sheet.tonnage), str(sheet.subdivision), sheet.year, sheet.month),
        )

    def months(self, subdivision: Ident) -> list[MonthlyTonnage]:
        """Every month posted for a subdivision, oldest first."""
        rows = self.book.query(
            "SELECT year, month, hundredths FROM tonnage WHERE subdivision = ? "
            "ORDER BY year, month",
            (str(subdivision),),
        )
        return [
            MonthlyTonnage(
                subdivision, int(row["year"]), int(row["month"]), decode_tonnage(row["hundredths"])
            )
            for row in rows
        ]

    def since(self, subdivision: Ident, first: date, last: date) -> Tonnage:
        """Tonnage over a subdivision between two days, counted by whole months.

        A month is counted when its first day falls in the range. Half a month
        of tonnage is not a figure anybody has, so nothing here pretends to
        prorate one.
        """
        if last < first:
            raise InputError("a tonnage range runs forward")
        total = ZERO
        for sheet in self.months(subdivision):
            if first <= sheet.first_day <= last:
                total = total + sheet.tonnage
        return total

    def latest(self, subdivision: Ident) -> MonthlyTonnage | None:
        """The most recent month posted, or nothing."""
        posted = self.months(subdivision)
        return posted[-1] if posted else None
