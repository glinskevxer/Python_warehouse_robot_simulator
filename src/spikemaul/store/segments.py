"""The segment register, which is asked two questions all day.

The first is what segment is this milepost on, because a defect card carries a
milepost and everything downstream of it needs the class. The second is what
segments are on this subdivision in order, because that is a bulletin.

Both are answered with sql rather than by reading everything and filtering in
python. There are only a few hundred segments, so it makes no difference to
the clock, but it makes a difference to what the code says: the index is on
subdivision and milepost because that is how the register is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from spikemaul.errors import NotFoundError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Segment
from spikemaul.standards.classes import ClassOfTrack, TrackKind
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
from spikemaul.store.register import Register
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


@dataclass
class Segments(Register[Segment]):
    """Every segment on the railroad."""

    table: ClassVar[str] = "segments"
    kind: ClassVar[Kind] = Kind.SEGMENT
    ordered_by: ClassVar[str] = "subdivision, begin_post"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "begin_post",
        "end_post",
        "kind",
        "authorized",
        "rail_section",
        "rail_laid",
        "welded",
        "note",
    )

    def ident_of(self, record: Segment) -> Ident:
        """The segment number."""
        return record.ident

    def row_of(self, record: Segment) -> tuple[Any, ...]:
        """The segment as columns."""
        begin, end = encode_span(record.span)
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            begin,
            end,
            encode_enum(record.kind),
            record.authorized.rank,
            record.rail_section,
            encode_date(record.rail_laid),
            encode_bool(record.welded),
            record.note,
        )

    def record_of(self, row: Any) -> Segment:
        """The columns back as a segment."""
        fields = dict(row)
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

    def add(self, record: Segment) -> None:
        """Write a new segment, refusing one that lies on top of another."""
        clash = [
            one
            for one in self.covering(record.subdivision, record.span)
            if one.ident != record.ident
        ]
        if clash:
            raise RuleError(f"{record.ident} lies on top of {clash[0].ident}")
        super().add(record)

    def on(self, subdivision: Ident) -> list[Segment]:
        """Every segment on one subdivision, in milepost order."""
        return self.where("subdivision = ?", (str(subdivision),), "begin_post")

    def at(self, subdivision: Ident, post: Milepost) -> Segment:
        """The segment a milepost falls on, which is the common question."""
        found = self.first(
            "subdivision = ? AND begin_post <= ? AND end_post > ?",
            (str(subdivision), post.hundredths, post.hundredths),
            "begin_post",
        )
        if found is None:
            raise NotFoundError("segment at", f"{subdivision.tail} MP {post}")
        return found

    def covering(self, subdivision: Ident, span: Span) -> list[Segment]:
        """Every segment that shares any track with a stretch."""
        begin, end = encode_span(span)
        return self.where(
            "subdivision = ? AND begin_post < ? AND end_post > ?",
            (str(subdivision), end, begin),
            "begin_post",
        )
