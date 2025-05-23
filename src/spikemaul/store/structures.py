"""The crossing and bridge registers.

Both are points on the railroad and both are shared with somebody else: a
crossing with the road authority and the inventory, a bridge with the bridge
inspector. That is why the inventory number is unique in the book. Two
crossings with the same number is not a duplicate record, it is a copying
mistake that has already been sent out on a letter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from spikemaul.errors import DuplicateError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.structure import Bridge, Crossing, Structure, Surface, WarningDevice
from spikemaul.store.codec import (
    decode_bool,
    decode_enum,
    decode_ident,
    decode_post,
    encode_bool,
    encode_enum,
    encode_ident,
    encode_post,
    encode_span,
)
from spikemaul.store.register import Register
from spikemaul.units.span import Span


@dataclass
class Crossings(Register[Crossing]):
    """Every grade crossing on the railroad."""

    table: ClassVar[str] = "crossings"
    kind: ClassVar[Kind] = Kind.CROSSING
    ordered_by: ClassVar[str] = "subdivision, at_post"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "at_post",
        "road",
        "inventory",
        "surface",
        "warning",
        "public",
    )

    def ident_of(self, record: Crossing) -> Ident:
        """The crossing number."""
        return record.ident

    def row_of(self, record: Crossing) -> tuple[Any, ...]:
        """The crossing as columns."""
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            encode_post(record.at),
            record.road,
            record.inventory,
            encode_enum(record.surface),
            encode_enum(record.warning),
            encode_bool(record.public),
        )

    def record_of(self, row: Any) -> Crossing:
        """The columns back as a crossing."""
        fields = dict(row)
        return Crossing(
            ident=decode_ident(fields["ident"], Kind.CROSSING),
            subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
            at=decode_post(fields["at_post"]),
            road=str(fields["road"]),
            inventory=str(fields["inventory"]),
            surface=decode_enum(Surface, fields["surface"]),
            warning=decode_enum(WarningDevice, fields["warning"]),
            public=decode_bool(fields["public"]),
        )

    def add(self, record: Crossing) -> None:
        """Write a new crossing, refusing a repeated inventory number."""
        if self.by_inventory(record.inventory) is not None:
            raise DuplicateError("crossing inventory number", record.inventory)
        super().add(record)

    def by_inventory(self, inventory: str) -> Crossing | None:
        """The crossing carrying an inventory number, which the road quotes."""
        return self.first("inventory = ?", (inventory.strip().upper(),))

    def within(self, subdivision: Ident, span: Span) -> list[Crossing]:
        """Every crossing inside a stretch, in milepost order."""
        begin, end = encode_span(span)
        return self.where(
            "subdivision = ? AND at_post >= ? AND at_post < ?",
            (str(subdivision), begin, end),
            "at_post",
        )


@dataclass
class Bridges(Register[Bridge]):
    """Every structure carrying the track."""

    table: ClassVar[str] = "bridges"
    kind: ClassVar[Kind] = Kind.BRIDGE
    ordered_by: ClassVar[str] = "subdivision, at_post"
    columns: ClassVar[tuple[str, ...]] = (
        "ident",
        "subdivision",
        "at_post",
        "kind",
        "spans",
        "length_feet",
        "normal_rating",
        "maximum_rating",
        "built",
    )

    def ident_of(self, record: Bridge) -> Ident:
        """The bridge number."""
        return record.ident

    def row_of(self, record: Bridge) -> tuple[Any, ...]:
        """The bridge as columns."""
        return (
            encode_ident(record.ident),
            encode_ident(record.subdivision),
            encode_post(record.at),
            encode_enum(record.kind),
            record.spans,
            record.length_feet,
            record.normal_rating,
            record.maximum_rating,
            record.built,
        )

    def record_of(self, row: Any) -> Bridge:
        """The columns back as a bridge."""
        fields = dict(row)
        return Bridge(
            ident=decode_ident(fields["ident"], Kind.BRIDGE),
            subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
            at=decode_post(fields["at_post"]),
            kind=decode_enum(Structure, fields["kind"]),
            spans=int(fields["spans"]),
            length_feet=int(fields["length_feet"]),
            normal_rating=int(fields["normal_rating"]),
            maximum_rating=int(fields["maximum_rating"]),
            built=int(fields["built"]),
        )

    def within(self, subdivision: Ident, span: Span) -> list[Bridge]:
        """Every bridge inside a stretch, in milepost order."""
        begin, end = encode_span(span)
        return self.where(
            "subdivision = ? AND at_post >= ? AND at_post < ?",
            (str(subdivision), begin, end),
            "at_post",
        )

    def weakest(self) -> Bridge | None:
        """The bridge with the lowest maximum rating, which sets the line."""
        found = self.where("1 = 1", (), "maximum_rating, ident")
        return found[0] if found else None
