"""The inspection register, which is read by date far more than by number.

Nobody looks up an inspection by its number. What gets asked is when this
stretch was last walked, what has been done on this subdivision since the
first of the month, and whether the gap between two of them was legal. So the
index is on subdivision, scope and day, and the queries here are the three
questions rather than a general search.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.store.codec import (
    decode_date,
    decode_enum,
    decode_ident,
    decode_span,
    encode_date,
    encode_enum,
    encode_ident,
    encode_span,
)
from spikemaul.store.register import Register
from spikemaul.units.span import Span


@dataclass
class Inspections(Register[Inspection]):
    """Every inspection anybody has recorded."""

    table: ClassVar[str] = "inspections"
    kind: ClassVar[Kind] = Kind.INSPECTION
    ordered_by: ClassVar[str] = "on_day, ident"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "begin_post",
        "end_post",
        "on_day",
        "by_person",
        "method",
        "scope",
        "note",
    )

    def ident_of(self, record: Inspection) -> Ident:
        """The inspection number."""
        return record.ident

    def row_of(self, record: Inspection) -> tuple[Any, ...]:
        """The inspection as columns."""
        begin, end = encode_span(record.span)
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            begin,
            end,
            encode_date(record.on),
            encode_ident(record.by),
            encode_enum(record.method),
            encode_enum(record.scope),
            record.note,
        )

    def record_of(self, row: Any) -> Inspection:
        """The columns back as an inspection."""
        fields = dict(row)
        return Inspection(
            ident=decode_ident(fields["ident"], Kind.INSPECTION),
            subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
            span=decode_span(fields["begin_post"], fields["end_post"]),
            on=decode_date(fields["on_day"]),
            by=decode_ident(fields["by_person"], Kind.PERSON),
            method=decode_enum(Method, fields["method"]),
            scope=decode_enum(Scope, fields["scope"]),
            note=str(fields["note"]),
        )

    def on(self, subdivision: Ident, scope: Scope | None = None) -> list[Inspection]:
        """Every inspection on a subdivision, oldest first."""
        if scope is None:
            return self.where("subdivision = ?", (str(subdivision),))
        return self.where("subdivision = ? AND scope = ?", (str(subdivision), encode_enum(scope)))

    def between(self, subdivision: Ident, first: date, last: date) -> list[Inspection]:
        """Every inspection on a subdivision in a range of days, ends included."""
        return self.where(
            "subdivision = ? AND on_day >= ? AND on_day <= ?",
            (str(subdivision), encode_date(first), encode_date(last)),
        )

    def covering(self, subdivision: Ident, span: Span, scope: Scope) -> list[Inspection]:
        """Every inspection of that scope that took in any of a stretch."""
        begin, end = encode_span(span)
        return self.where(
            "subdivision = ? AND scope = ? AND begin_post < ? AND end_post > ?",
            (str(subdivision), encode_enum(scope), end, begin),
        )

    def last_covering(
        self, subdivision: Ident, span: Span, scope: Scope, on_or_before: date
    ) -> Inspection | None:
        """The most recent inspection of that scope taking in the whole stretch."""
        found = [
            one
            for one in self.covering(subdivision, span, scope)
            if one.on <= on_or_before and one.covers_all_of(span)
        ]
        return max(found, key=lambda one: (one.on, str(one.ident))) if found else None
