"""The segment register, which is asked two questions all day.

The first is what segment is this milepost on, because a defect card carries a
milepost and everything downstream of it needs the class. The second is what
segments are on this subdivision in order, because that is a bulletin.

Both are answered here with sql rather than by reading everything and
filtering in python. There are only a few hundred segments, so it makes no
difference to the clock, but it makes a difference to what the code says: the
index is on subdivision and milepost because that is how the register is used.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.errors import DuplicateError, NotFoundError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Segment
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.store.book import Book
from spikemaul.store.codec import (
    decode_bool,
    decode_date,
    decode_enum,
    decode_ident,
    decode_span,
    encode_bool,
    encode_date,
    encode_enum,
    encode_ident,
    encode_span,
)
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

COLUMNS = (
    "ident, subdivision, begin_post, end_post, kind, authorized, "
    "rail_section, rail_laid, welded, note"
)


@dataclass
class Segments:
    """Every segment on the railroad."""

    book: Book

    def add(self, segment: Segment) -> None:
        """Write a new segment, refusing one that lies on top of another."""
        if self.exists(segment.ident):
            raise DuplicateError("segment", str(segment.ident))
        clash = self.covering(segment.subdivision, segment.span)
        if clash:
            raise RuleError(f"{segment.ident} lies on top of {clash[0].ident}")
        begin, end = encode_span(segment.span)
        self.book.execute(
            f"INSERT INTO segments ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                encode_ident(segment.ident),
                encode_ident(segment.subdivision),
                begin,
                end,
                encode_enum(segment.kind),
                segment.authorized.rank,
                segment.rail_section,
                encode_date(segment.rail_laid),
                encode_bool(segment.welded),
                segment.note,
            ),
        )

    def exists(self, ident: Ident) -> bool:
        """Whether that segment is in the book."""
        return self.book.one("SELECT 1 FROM segments WHERE ident = ?", (str(ident),)) is not None

    def get(self, ident: Ident) -> Segment:
        """One segment by its number."""
        row = self.book.one(
            f"SELECT {COLUMNS} FROM segments WHERE ident = ?",
            (str(ident),),
        )
        if row is None:
            raise NotFoundError("segment", str(ident))
        return _read(row)

    def all(self) -> list[Segment]:
        """Every segment, in subdivision and milepost order."""
        rows = self.book.query(f"SELECT {COLUMNS} FROM segments ORDER BY subdivision, begin_post")
        return [_read(row) for row in rows]

    def on(self, subdivision: Ident) -> list[Segment]:
        """Every segment on one subdivision, in milepost order."""
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM segments WHERE subdivision = ? ORDER BY begin_post",
            (str(subdivision),),
        )
        return [_read(row) for row in rows]

    def at(self, subdivision: Ident, post: Milepost) -> Segment:
        """The segment a milepost falls on, which is the common question."""
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM segments "
            "WHERE subdivision = ? AND begin_post <= ? AND end_post > ?",
            (str(subdivision), post.hundredths, post.hundredths),
        )
        if not rows:
            raise NotFoundError("segment at", f"{subdivision.tail} MP {post}")
        return _read(rows[0])

    def covering(self, subdivision: Ident, span: Span) -> list[Segment]:
        """Every segment that shares any track with a stretch."""
        begin, end = encode_span(span)
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM segments "
            "WHERE subdivision = ? AND begin_post < ? AND end_post > ? ORDER BY begin_post",
            (str(subdivision), end, begin),
        )
        return [_read(row) for row in rows]

    def update(self, segment: Segment) -> None:
        """Write a segment that is already in the book."""
        if not self.exists(segment.ident):
            raise NotFoundError("segment", str(segment.ident))
        begin, end = encode_span(segment.span)
        self.book.execute(
            "UPDATE segments SET subdivision = ?, begin_post = ?, end_post = ?, kind = ?, "
            "authorized = ?, rail_section = ?, rail_laid = ?, welded = ?, note = ? "
            "WHERE ident = ?",
            (
                encode_ident(segment.subdivision),
                begin,
                end,
                encode_enum(segment.kind),
                segment.authorized.rank,
                segment.rail_section,
                encode_date(segment.rail_laid),
                encode_bool(segment.welded),
                segment.note,
                encode_ident(segment.ident),
            ),
        )

    def remove(self, ident: Ident) -> None:
        """Take a segment out of the book."""
        if not self.exists(ident):
            raise NotFoundError("segment", str(ident))
        self.book.execute("DELETE FROM segments WHERE ident = ?", (str(ident),))

    def count(self) -> int:
        """How many segments are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM segments")
        return 0 if row is None else int(row["n"])


def _read(row: object) -> Segment:
    fields = dict(row)  # type: ignore[call-overload]
    return Segment(
        ident=decode_ident(fields["ident"], Kind.SEGMENT),
        subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
        span=decode_span(fields["begin_post"], fields["end_post"]),
        kind=decode_enum(TrackKind, fields["kind"]),
        authorized=ClassOfTrack(fields["authorized"]),
        rail_section=str(fields["rail_section"]),
        rail_laid=decode_date(fields["rail_laid"]),
        welded=decode_bool(fields["welded"]),
        note=str(fields["note"]),
    )
