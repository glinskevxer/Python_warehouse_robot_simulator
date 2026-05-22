"""The defect register, which is mostly asked what is still open.

An open defect is one with no repair date on it, and that is the only state
there is. There is no closed flag to disagree with the date, because the two
of them disagreeing is a bug that takes a year to find and a morning to
explain to an inspector.

The class a condition meets is stored as its rank, and null means it meets
none. Null there is load bearing: it is the difference between run slower and
do not run at all, so it is never turned into a zero on the way in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar

from spikemaul.model.defect import Condition, Defect
from spikemaul.model.ids import Ident, Kind
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.codec import (
    decode_date,
    decode_enum,
    decode_ident,
    decode_optional_date,
    decode_optional_ident,
    decode_post,
    encode_date,
    encode_enum,
    encode_ident,
    encode_optional_date,
    encode_post,
)
from spikemaul.store.register import Register
from spikemaul.units.span import Span


@dataclass
class Defects(Register[Defect]):
    """Every defect card raised, open or repaired."""

    table: ClassVar[str] = "defects"
    kind: ClassVar[Kind] = Kind.DEFECT
    ordered_by: ClassVar[str] = "found_on, ident"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "at_post",
        "found_on",
        "found_by",
        "condition",
        "reading",
        "meets",
        "inspection",
        "repaired_on",
        "note",
    )

    def ident_of(self, record: Defect) -> Ident:
        """The defect number."""
        return record.ident

    def row_of(self, record: Defect) -> tuple[Any, ...]:
        """The card as columns, with the class it meets kept nullable."""
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            encode_post(record.at),
            encode_date(record.found_on),
            encode_ident(record.found_by),
            encode_enum(record.condition),
            record.reading,
            None if record.meets is None else record.meets.rank,
            None if record.inspection is None else encode_ident(record.inspection),
            encode_optional_date(record.repaired_on),
            record.note,
        )

    def record_of(self, row: Any) -> Defect:
        """The columns back as a card."""
        fields = dict(row)
        meets = fields["meets"]
        return Defect(
            ident=decode_ident(fields["ident"], Kind.DEFECT),
            subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
            at=decode_post(fields["at_post"]),
            found_on=decode_date(fields["found_on"]),
            found_by=decode_ident(fields["found_by"], Kind.PERSON),
            condition=decode_enum(Condition, fields["condition"]),
            reading=str(fields["reading"]),
            meets=None if meets is None else ClassOfTrack(meets),
            inspection=decode_optional_ident(fields["inspection"], Kind.INSPECTION),
            repaired_on=decode_optional_date(fields["repaired_on"]),
            note=str(fields["note"]),
        )

    def open_on(self, subdivision: Ident) -> list[Defect]:
        """Every card on a subdivision with no repair date on it."""
        return self.where("subdivision = ? AND repaired_on IS NULL", (str(subdivision),), "at_post")

    def open_within(self, subdivision: Ident, span: Span) -> list[Defect]:
        """Every open card inside a stretch, in milepost order."""
        return self.where(
            "subdivision = ? AND repaired_on IS NULL AND at_post >= ? AND at_post < ?",
            (str(subdivision), span.begin.hundredths, span.end.hundredths),
            "at_post",
        )

    def raised_between(self, first: date, last: date) -> list[Defect]:
        """Every card raised in a range of days, ends included."""
        return self.where(
            "found_on >= ? AND found_on <= ?", (encode_date(first), encode_date(last))
        )

    def from_inspection(self, inspection: Ident) -> list[Defect]:
        """Every card written off one inspection."""
        return self.where("inspection = ?", (str(inspection),), "at_post")

    def out_of_service(self, subdivision: Ident) -> list[Defect]:
        """Open cards whose condition meets no class at all."""
        return self.where(
            "subdivision = ? AND repaired_on IS NULL AND meets IS NULL",
            (str(subdivision),),
            "at_post",
        )
