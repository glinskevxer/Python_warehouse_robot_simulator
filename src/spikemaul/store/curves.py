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
from typing import Any, ClassVar

from spikemaul.model.curve import Curve
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
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
from spikemaul.store.register import Register
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

WIDEST_SPIRAL_FEET = 1000
"""How far either side of a body the search looks for spirals."""


@dataclass
class Curves(Register[Curve]):
    """Every curve on the railroad."""

    table: ClassVar[str] = "curves"
    kind: ClassVar[Kind] = Kind.CURVE
    ordered_by: ClassVar[str] = "subdivision, begin_post"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "begin_post",
        "end_post",
        "curvature",
        "elevation",
        "hand",
        "entry_spiral_feet",
        "exit_spiral_feet",
    )

    def ident_of(self, record: Curve) -> Ident:
        """The curve number."""
        return record.ident

    def row_of(self, record: Curve) -> tuple[Any, ...]:
        """The curve as columns."""
        begin, end = encode_span(record.body)
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            begin,
            end,
            encode_curvature(record.curvature),
            encode_inches(record.elevation),
            encode_enum(record.hand),
            record.entry_spiral_feet,
            record.exit_spiral_feet,
        )

    def record_of(self, row: Any) -> Curve:
        """The columns back as a curve."""
        fields = dict(row)
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

    def on(self, subdivision: Ident) -> list[Curve]:
        """Every curve on one subdivision, in milepost order."""
        return self.where("subdivision = ?", (str(subdivision),), "begin_post")

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
        return self.where(
            "subdivision = ? AND begin_post < ? AND end_post > ?",
            (str(subdivision), end, begin),
            "begin_post",
        )
