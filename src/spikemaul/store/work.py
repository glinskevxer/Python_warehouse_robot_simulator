"""The work order register, which the week's plan is drawn from.

Two questions get asked of it and they are not the same question. What is open
on this subdivision, which is a backlog, and what is this gang doing, which is
a plan. An order can be open and unassigned for a season and that is a
different problem from one assigned to a gang that has not got to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar

from spikemaul.model.ids import Ident, Kind
from spikemaul.model.work import WorkKind, WorkOrder
from spikemaul.store.codec import (
    decode_date,
    decode_enum,
    decode_ident,
    decode_optional_date,
    decode_optional_ident,
    decode_span,
    encode_date,
    encode_enum,
    encode_ident,
    encode_optional_date,
    encode_span,
)
from spikemaul.store.register import Register
from spikemaul.units.span import Span


@dataclass
class WorkOrders(Register[WorkOrder]):
    """Every work order raised, open or finished."""

    table: ClassVar[str] = "work_orders"
    kind: ClassVar[Kind] = Kind.WORK
    ordered_by: ClassVar[str] = "raised_on, ident"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "begin_post",
        "end_post",
        "kind",
        "quantity",
        "raised_on",
        "raised_by",
        "due_on",
        "gang",
        "defect",
        "done_on",
        "done_quantity",
        "note",
    )

    def ident_of(self, record: WorkOrder) -> Ident:
        """The work order number."""
        return record.ident

    def row_of(self, record: WorkOrder) -> tuple[Any, ...]:
        """The order as columns."""
        begin, end = encode_span(record.span)
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            begin,
            end,
            encode_enum(record.kind),
            record.quantity,
            encode_date(record.raised_on),
            encode_ident(record.raised_by),
            encode_optional_date(record.due_on),
            None if record.gang is None else encode_ident(record.gang),
            None if record.defect is None else encode_ident(record.defect),
            encode_optional_date(record.done_on),
            record.done_quantity,
            record.note,
        )

    def record_of(self, row: Any) -> WorkOrder:
        """The columns back as an order."""
        fields = dict(row)
        done = fields["done_quantity"]
        return WorkOrder(
            ident=decode_ident(fields["ident"], Kind.WORK),
            subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
            span=decode_span(fields["begin_post"], fields["end_post"]),
            kind=decode_enum(WorkKind, fields["kind"]),
            quantity=int(fields["quantity"]),
            raised_on=decode_date(fields["raised_on"]),
            raised_by=decode_ident(fields["raised_by"], Kind.PERSON),
            due_on=decode_optional_date(fields["due_on"]),
            gang=decode_optional_ident(fields["gang"], Kind.GANG),
            defect=decode_optional_ident(fields["defect"], Kind.DEFECT),
            done_on=decode_optional_date(fields["done_on"]),
            done_quantity=None if done is None else int(done),
            note=str(fields["note"]),
        )

    def open_on(self, subdivision: Ident) -> list[WorkOrder]:
        """Every order on a subdivision still to do, oldest first."""
        return self.where("subdivision = ? AND done_on IS NULL", (str(subdivision),))

    def unassigned(self, subdivision: Ident) -> list[WorkOrder]:
        """Open orders with nobody on them, which is a different problem."""
        return self.where(
            "subdivision = ? AND done_on IS NULL AND gang IS NULL", (str(subdivision),)
        )

    def for_gang(self, gang: Ident) -> list[WorkOrder]:
        """Everything a gang has open, oldest first."""
        return self.where("gang = ? AND done_on IS NULL", (str(gang),))

    def overdue(self, subdivision: Ident, on: date) -> list[WorkOrder]:
        """Open orders past their date as of a day."""
        return self.where(
            "subdivision = ? AND done_on IS NULL AND due_on IS NOT NULL AND due_on < ?",
            (str(subdivision), encode_date(on)),
        )

    def within(self, subdivision: Ident, span: Span) -> list[WorkOrder]:
        """Every order sharing track with a stretch, finished or not."""
        begin, end = encode_span(span)
        return self.where(
            "subdivision = ? AND begin_post < ? AND end_post > ?",
            (str(subdivision), end, begin),
            "begin_post",
        )

    def for_defect(self, defect: Ident) -> list[WorkOrder]:
        """Every order raised off one defect card."""
        return self.where("defect = ?", (str(defect),))
