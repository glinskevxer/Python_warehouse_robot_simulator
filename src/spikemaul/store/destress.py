"""The destress log register.

An entry is keyed by where it started and when, because a gang destresses one
stretch on one day and two entries starting at the same milepost on the same
day are one entry written twice. The log is append only in practice: an entry
is a record of work done, and correcting one means the work was recorded
wrongly rather than that it did not happen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.cwr.neutral import Destress
from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.book import Book
from spikemaul.store.codec import (
    decode_date,
    decode_ident,
    decode_span,
    decode_temperature,
    encode_date,
    encode_ident,
    encode_span,
    encode_temperature,
)
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

COLUMNS = "subdivision, begin_post, end_post, on_day, neutral, by_person, method, note"


@dataclass
class DestressLog:
    """Every destress entry on the railroad."""

    book: Book

    def add(self, entry: Destress) -> None:
        """Write an entry, refusing the same stretch and day twice."""
        if self.has(entry.subdivision, entry.span.begin, entry.on):
            raise DuplicateError(
                "destress entry", f"{entry.subdivision.tail} {entry.span.begin} {entry.on}"
            )
        begin, end = encode_span(entry.span)
        self.book.execute(
            f"INSERT INTO destress ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
            (
                encode_ident(entry.subdivision),
                begin,
                end,
                encode_date(entry.on),
                encode_temperature(entry.neutral),
                encode_ident(entry.by),
                entry.method,
                entry.note,
            ),
        )

    def has(self, subdivision: Ident, begin: Milepost, on: date) -> bool:
        """Whether that stretch was recorded as destressed on that day."""
        found = self.book.one(
            "SELECT 1 FROM destress WHERE subdivision = ? AND begin_post = ? AND on_day = ?",
            (str(subdivision), begin.hundredths, encode_date(on)),
        )
        return found is not None

    def on(self, subdivision: Ident) -> list[Destress]:
        """Every entry on a subdivision, oldest first."""
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM destress WHERE subdivision = ? ORDER BY on_day, begin_post",
            (str(subdivision),),
        )
        return [_read(row) for row in rows]

    def covering(self, subdivision: Ident, span: Span, on_or_before: date) -> list[Destress]:
        """Entries that took in the whole of a stretch, newest first."""
        begin, end = encode_span(span)
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM destress WHERE subdivision = ? AND begin_post <= ? "
            "AND end_post >= ? AND on_day <= ? ORDER BY on_day DESC, begin_post",
            (str(subdivision), begin, end, encode_date(on_or_before)),
        )
        return [_read(row) for row in rows]

    def correct(self, entry: Destress) -> None:
        """Write an entry over one already recorded, which is a correction."""
        if not self.has(entry.subdivision, entry.span.begin, entry.on):
            raise NotFoundError(
                "destress entry", f"{entry.subdivision.tail} {entry.span.begin} {entry.on}"
            )
        _, end = encode_span(entry.span)
        self.book.execute(
            "UPDATE destress SET end_post = ?, neutral = ?, by_person = ?, method = ?, note = ? "
            "WHERE subdivision = ? AND begin_post = ? AND on_day = ?",
            (
                end,
                encode_temperature(entry.neutral),
                encode_ident(entry.by),
                entry.method,
                entry.note,
                encode_ident(entry.subdivision),
                entry.span.begin.hundredths,
                encode_date(entry.on),
            ),
        )

    def count(self) -> int:
        """How many entries are in the log."""
        row = self.book.one("SELECT COUNT(*) AS n FROM destress")
        return 0 if row is None else int(row["n"])


def _read(row: object) -> Destress:
    fields = dict(row)  # type: ignore[call-overload]
    return Destress(
        subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
        span=decode_span(fields["begin_post"], fields["end_post"]),
        on=decode_date(fields["on_day"]),
        neutral=decode_temperature(fields["neutral"]),
        by=decode_ident(fields["by_person"], Kind.PERSON),
        method=str(fields["method"]),
        note=str(fields["note"]),
    )
