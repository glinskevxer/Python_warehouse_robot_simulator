"""The tie survey register, which stores a walk rather than a row per tie.

A tie survey is written whole, the way a geometry run is, and for the same
reason. The class a stretch holds is its worst length, and a survey missing
three of its lengths is a survey that says the stretch is better than it is.
Half a walk is not a small walk.

The lengths are keyed by their position in the walk rather than by milepost,
because two lengths can share a milepost number either side of an equation and
the walk still has an order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.store.book import Book
from spikemaul.store.codec import (
    decode_curvature,
    decode_date,
    decode_ident,
    decode_post,
    decode_span,
    encode_curvature,
    encode_date,
    encode_ident,
    encode_post,
    encode_span,
)
from spikemaul.ties.condition import TieLength
from spikemaul.ties.survey import TieSurvey
from spikemaul.units.span import Span

LENGTH_COLUMNS = (
    "inspection, ordinal, at_post, total, good, longest_run, joints, joints_supported, curvature"
)


@dataclass
class TieSurveys:
    """Every tie walk in the book, kept whole."""

    book: Book

    def add(self, survey: TieSurvey, inspection: Ident) -> None:
        """Write a whole survey against the inspection it was recorded on."""
        if inspection.kind is not Kind.INSPECTION:
            raise NotFoundError("inspection", str(inspection))
        if self.exists(inspection):
            raise DuplicateError("tie survey", str(inspection))
        begin, end = encode_span(survey.span)
        with self.book.writing():
            self.book.execute(
                "INSERT INTO tie_surveys (inspection, subdivision, begin_post, end_post, on_day) "
                "VALUES (?,?,?,?,?)",
                (
                    encode_ident(inspection),
                    encode_ident(survey.subdivision),
                    begin,
                    end,
                    encode_date(survey.on),
                ),
            )
            for ordinal, one in enumerate(survey.lengths, start=1):
                self.book.execute(
                    f"INSERT INTO tie_lengths ({LENGTH_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        encode_ident(inspection),
                        ordinal,
                        encode_post(one.at),
                        one.total,
                        one.good,
                        one.longest_run,
                        one.joints,
                        one.joints_supported,
                        encode_curvature(one.curve),
                    ),
                )

    def exists(self, inspection: Ident) -> bool:
        """Whether a survey was recorded against that inspection."""
        found = self.book.one("SELECT 1 FROM tie_surveys WHERE inspection = ?", (str(inspection),))
        return found is not None

    def get(self, inspection: Ident) -> TieSurvey:
        """The survey recorded against an inspection, lengths in walk order."""
        head = self.book.one(
            "SELECT subdivision, begin_post, end_post, on_day FROM tie_surveys "
            "WHERE inspection = ?",
            (str(inspection),),
        )
        if head is None:
            raise NotFoundError("tie survey", str(inspection))
        rows = self.book.query(
            f"SELECT {LENGTH_COLUMNS} FROM tie_lengths WHERE inspection = ? ORDER BY ordinal",
            (str(inspection),),
        )
        return TieSurvey(
            subdivision=decode_ident(head["subdivision"], Kind.SUBDIVISION),
            span=decode_span(head["begin_post"], head["end_post"]),
            on=decode_date(head["on_day"]),
            lengths=[_read(row) for row in rows],
        )

    def on(self, subdivision: Ident) -> list[Ident]:
        """The inspections that carry a survey on a subdivision, oldest first."""
        rows = self.book.query(
            "SELECT inspection FROM tie_surveys WHERE subdivision = ? ORDER BY on_day, inspection",
            (str(subdivision),),
        )
        return [decode_ident(row["inspection"], Kind.INSPECTION) for row in rows]

    def covering(self, subdivision: Ident, span: Span, on_or_before: date) -> Ident | None:
        """The most recent survey taking in the whole of a stretch."""
        begin, end = encode_span(span)
        rows = self.book.query(
            "SELECT inspection FROM tie_surveys WHERE subdivision = ? AND begin_post <= ? "
            "AND end_post >= ? AND on_day <= ? ORDER BY on_day DESC, inspection DESC LIMIT 1",
            (str(subdivision), begin, end, encode_date(on_or_before)),
        )
        if not rows:
            return None
        return decode_ident(rows[0]["inspection"], Kind.INSPECTION)

    def remove(self, inspection: Ident) -> None:
        """Take a whole survey out of the book."""
        if not self.exists(inspection):
            raise NotFoundError("tie survey", str(inspection))
        with self.book.writing():
            self.book.execute("DELETE FROM tie_lengths WHERE inspection = ?", (str(inspection),))
            self.book.execute("DELETE FROM tie_surveys WHERE inspection = ?", (str(inspection),))

    def count(self) -> int:
        """How many surveys are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM tie_surveys")
        return 0 if row is None else int(row["n"])


def _read(row: object) -> TieLength:
    fields = dict(row)  # type: ignore[call-overload]
    return TieLength(
        at=decode_post(fields["at_post"]),
        total=int(fields["total"]),
        good=int(fields["good"]),
        longest_run=int(fields["longest_run"]),
        joints=int(fields["joints"]),
        joints_supported=int(fields["joints_supported"]),
        curve=decode_curvature(fields["curvature"]),
    )
