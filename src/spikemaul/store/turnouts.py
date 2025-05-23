"""The turnout register.

Turnouts are recorded at a point rather than over a stretch, so the questions
here are which ones are on this subdivision and which ones are inside a
stretch a gang is working. Both come back in milepost order, because a foreman
walking a siding wants them in the order he will reach them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.model.turnout import FrogKind, Throw, Turnout
from spikemaul.store.codec import (
    decode_enum,
    decode_ident,
    decode_post,
    encode_enum,
    encode_ident,
    encode_post,
    encode_span,
)
from spikemaul.store.register import Register
from spikemaul.units.span import Span


@dataclass
class Turnouts(Register[Turnout]):
    """Every turnout on the railroad."""

    table: ClassVar[str] = "turnouts"
    kind: ClassVar[Kind] = Kind.TURNOUT
    ordered_by: ClassVar[str] = "subdivision, point_of_switch"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "point_of_switch",
        "size",
        "hand",
        "frog",
        "throw",
        "leads_to",
    )

    def ident_of(self, record: Turnout) -> Ident:
        """The turnout number."""
        return record.ident

    def row_of(self, record: Turnout) -> tuple[Any, ...]:
        """The turnout as columns."""
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            encode_post(record.point_of_switch),
            record.size,
            encode_enum(record.hand),
            encode_enum(record.frog),
            encode_enum(record.throw),
            record.leads_to,
        )

    def record_of(self, row: Any) -> Turnout:
        """The columns back as a turnout."""
        fields = dict(row)
        return Turnout(
            ident=decode_ident(fields["ident"], Kind.TURNOUT),
            subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
            point_of_switch=decode_post(fields["point_of_switch"]),
            size=int(fields["size"]),
            hand=decode_enum(Hand, fields["hand"]),
            frog=decode_enum(FrogKind, fields["frog"]),
            throw=decode_enum(Throw, fields["throw"]),
            leads_to=str(fields["leads_to"]),
        )

    def on(self, subdivision: Ident) -> list[Turnout]:
        """Every turnout on one subdivision, in milepost order."""
        return self.where("subdivision = ?", (str(subdivision),), "point_of_switch")

    def within(self, subdivision: Ident, span: Span) -> list[Turnout]:
        """Every turnout whose point of switch is inside a stretch."""
        begin, end = encode_span(span)
        return self.where(
            "subdivision = ? AND point_of_switch >= ? AND point_of_switch < ?",
            (str(subdivision), begin, end),
            "point_of_switch",
        )
