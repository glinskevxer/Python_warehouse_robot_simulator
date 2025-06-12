"""The slow order register, which is asked one question and asked it every day.

What is in force on this subdivision on this day. Everything else here is in
support of that: an order that has lapsed or been lifted stays in the book, so
the same question can be asked about a day last July and get the answer the
crew actually had.

Orders are never deleted once they have been in force. The remove here is for
one raised in error and taken back the same morning, and it says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar

from spikemaul.errors import RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.order import Reason, SlowOrder
from spikemaul.store.codec import (
    decode_date,
    decode_enum,
    decode_ident,
    decode_optional_date,
    decode_optional_ident,
    decode_span,
    decode_speed,
    encode_date,
    encode_enum,
    encode_ident,
    encode_optional_date,
    encode_span,
    encode_speed,
)
from spikemaul.store.register import Register
from spikemaul.units.span import Span


@dataclass
class Orders(Register[SlowOrder]):
    """Every slow order the railroad has issued."""

    table: ClassVar[str] = "orders"
    kind: ClassVar[Kind] = Kind.ORDER
    ordered_by: ClassVar[str] = "subdivision, begin_post, ident"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "begin_post",
        "end_post",
        "speed",
        "reason",
        "effective",
        "authority",
        "expires",
        "lifted_on",
        "defect",
        "note",
    )

    def ident_of(self, record: SlowOrder) -> Ident:
        """The slow order number."""
        return record.ident

    def row_of(self, record: SlowOrder) -> tuple[Any, ...]:
        """The order as columns."""
        begin, end = encode_span(record.span)
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            begin,
            end,
            encode_speed(record.speed),
            encode_enum(record.reason),
            encode_date(record.effective),
            record.authority,
            encode_optional_date(record.expires),
            encode_optional_date(record.lifted_on),
            None if record.defect is None else encode_ident(record.defect),
            record.note,
        )

    def record_of(self, row: Any) -> SlowOrder:
        """The columns back as an order."""
        fields = dict(row)
        return SlowOrder(
            ident=decode_ident(fields["ident"], Kind.ORDER),
            subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
            span=decode_span(fields["begin_post"], fields["end_post"]),
            speed=decode_speed(fields["speed"]),
            reason=decode_enum(Reason, fields["reason"]),
            effective=decode_date(fields["effective"]),
            authority=str(fields["authority"]),
            expires=decode_optional_date(fields["expires"]),
            lifted_on=decode_optional_date(fields["lifted_on"]),
            defect=decode_optional_ident(fields["defect"], Kind.DEFECT),
            note=str(fields["note"]),
        )

    def in_force(self, subdivision: Ident, on: date) -> list[SlowOrder]:
        """Every order a crew is given on that subdivision on that day."""
        day = encode_date(on)
        found = self.where(
            "subdivision = ? AND effective <= ? AND (expires IS NULL OR expires >= ?)",
            (str(subdivision), day, day),
        )
        return [one for one in found if one.in_effect_on(on)]

    def covering(self, subdivision: Ident, span: Span, on: date) -> list[SlowOrder]:
        """Orders in force that share any track with a stretch."""
        return [one for one in self.in_force(subdivision, on) if one.span.overlaps(span)]

    def standing(self, subdivision: Ident) -> list[SlowOrder]:
        """Orders with no end date that nobody has lifted."""
        return self.where(
            "subdivision = ? AND expires IS NULL AND lifted_on IS NULL", (str(subdivision),)
        )

    def for_defect(self, defect: Ident) -> list[SlowOrder]:
        """Every order raised against one defect card."""
        return self.where("defect = ?", (str(defect),))

    def next_number(self, year: int) -> Ident:
        """The next order number for a year."""
        row = self.book.one(
            "SELECT MAX(ident) AS last FROM orders WHERE ident LIKE ?", (f"SO-{year}-%",)
        )
        if row is None or row["last"] is None:
            return Ident.numbered(Kind.ORDER, year, 1)
        last = Ident.parse(str(row["last"]), Kind.ORDER)
        return Ident.numbered(Kind.ORDER, year, last.sequence + 1)

    def remove(self, ident: Ident) -> None:
        """Take back an order raised in error, which is not the same as lifting one."""
        order = self.get(ident)
        if order.lifted_on is not None:
            raise RuleError(f"{ident} was in force and lifted, so it stays in the book")
        super().remove(ident)
