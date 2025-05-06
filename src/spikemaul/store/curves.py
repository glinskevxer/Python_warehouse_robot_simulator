"""The curve register.

The question this one gets asked is which curve a milepost is in, and the
answer has to take in the spirals. A reading a hundred feet before the body of
the curve is still a reading on curved track, and judging it against the
tangent limits is how a real exception gets written off.

Spirals are held as lengths rather than as mileposts because that is what the
track chart carries, so the search on milepost is done on the body and then
widened. There are a few hundred curves and the widening is a fifty foot
question, so this is done in python where it can be read rather than in sql
where it cannot.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.curve import Curve
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.store.book import Book
from spikemaul.store.codec import (
    decode_curvature,
    decode_enum,
    decode_ident,
    decode_inches,
    decode_span,
    encode_curvature,
    encode_enum,
    encode_ident,
    encode_inches,
    encode_span,
)
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

COLUMNS = (
    "ident, subdivision, begin_post, end_post, curvature, elevation, hand, "
    "entry_spiral_feet, exit_spiral_feet"
)

WIDEST_SPIRAL_FEET = 1000
"""How far either side of a body the search looks for spirals."""


@dataclass
class Curves:
    """Every curve on the railroad."""

    book: Book

    def add(self, curve: Curve) -> None:
        """Write a new curve."""
        if self.exists(curve.ident):
            raise DuplicateError("curve", str(curve.ident))
        begin, end = encode_span(curve.body)
        self.book.execute(
            f"INSERT INTO curves ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                encode_ident(curve.ident),
                encode_ident(curve.subdivision),
                begin,
                end,
                encode_curvature(curve.curvature),
                encode_inches(curve.elevation),
                encode_enum(curve.hand),
                curve.entry_spiral_feet,
                curve.exit_spiral_feet,
            ),
        )

    def exists(self, ident: Ident) -> bool:
        """Whether that curve is in the book."""
        return self.book.one("SELECT 1 FROM curves WHERE ident = ?", (str(ident),)) is not None

    def get(self, ident: Ident) -> Curve:
        """One curve by its number."""
        row = self.book.one(
            f"SELECT {COLUMNS} FROM curves WHERE ident = ?",
            (str(ident),),
        )
        if row is None:
            raise NotFoundError("curve", str(ident))
        return _read(row)

    def all(self) -> list[Curve]:
        """Every curve, in subdivision and milepost order."""
        rows = self.book.query(f"SELECT {COLUMNS} FROM curves ORDER BY subdivision, begin_post")
        return [_read(row) for row in rows]

    def on(self, subdivision: Ident) -> list[Curve]:
        """Every curve on one subdivision, in milepost order."""
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM curves WHERE subdivision = ? ORDER BY begin_post",
            (str(subdivision),),
        )
        return [_read(row) for row in rows]

    def at(self, subdivision: Ident, post: Milepost) -> Curve | None:
        """The curve a milepost is in, spirals included, or nothing."""
        for curve in self._near(subdivision, Span(post, post.advanced(1))):
            if curve.holds(post):
                return curve
        return None

    def covering(self, subdivision: Ident, span: Span) -> list[Curve]:
        """Every curve that shares any track with a stretch, spirals included."""
        return [one for one in self._near(subdivision, span) if one.span.overlaps(span)]

    def _near(self, subdivision: Ident, span: Span) -> list[Curve]:
        reach = round(WIDEST_SPIRAL_FEET * 100 / 5280) + 1
        begin = max(span.begin.hundredths - reach, 0)
        end = span.end.hundredths + reach
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM curves "
            "WHERE subdivision = ? AND begin_post < ? AND end_post > ? ORDER BY begin_post",
            (str(subdivision), end, begin),
        )
        return [_read(row) for row in rows]

    def update(self, curve: Curve) -> None:
        """Write a curve that is already in the book."""
        if not self.exists(curve.ident):
            raise NotFoundError("curve", str(curve.ident))
        begin, end = encode_span(curve.body)
        self.book.execute(
            "UPDATE curves SET subdivision = ?, begin_post = ?, end_post = ?, curvature = ?, "
            "elevation = ?, hand = ?, entry_spiral_feet = ?, exit_spiral_feet = ? WHERE ident = ?",
            (
                encode_ident(curve.subdivision),
                begin,
                end,
                encode_curvature(curve.curvature),
                encode_inches(curve.elevation),
                encode_enum(curve.hand),
                curve.entry_spiral_feet,
                curve.exit_spiral_feet,
                encode_ident(curve.ident),
            ),
        )

    def remove(self, ident: Ident) -> None:
        """Take a curve out of the book."""
        if not self.exists(ident):
            raise NotFoundError("curve", str(ident))
        self.book.execute("DELETE FROM curves WHERE ident = ?", (str(ident),))

    def count(self) -> int:
        """How many curves are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM curves")
        return 0 if row is None else int(row["n"])


def _read(row: object) -> Curve:
    fields = dict(row)  # type: ignore[call-overload]
    return Curve(
        ident=decode_ident(fields["ident"], Kind.CURVE),
        subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
        body=decode_span(fields["begin_post"], fields["end_post"]),
        curvature=decode_curvature(fields["curvature"]),
        elevation=decode_inches(fields["elevation"]),
        hand=decode_enum(Hand, fields["hand"]),
        entry_spiral_feet=int(fields["entry_spiral_feet"]),
        exit_spiral_feet=int(fields["exit_spiral_feet"]),
    )
