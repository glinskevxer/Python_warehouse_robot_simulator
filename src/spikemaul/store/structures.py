"""The crossing and bridge registers.

Both are points on the railroad and both are shared with somebody else: a
crossing with the road authority and the inventory, a bridge with the bridge
inspector. That is why the inventory number is unique in the book. Two
crossings with the same number is not a duplicate record, it is a copying
mistake that has already been sent out on a letter.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.structure import Bridge, Crossing, Structure, Surface, WarningDevice
from spikemaul.store.book import Book
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
from spikemaul.units.span import Span

CROSSING_COLUMNS = "ident, subdivision, at_post, road, inventory, surface, warning, public"
BRIDGE_COLUMNS = (
    "ident, subdivision, at_post, kind, spans, length_feet, normal_rating, maximum_rating, built"
)


@dataclass
class Crossings:
    """Every grade crossing on the railroad."""

    book: Book

    def add(self, crossing: Crossing) -> None:
        """Write a new crossing, refusing a repeated inventory number."""
        if self.exists(crossing.ident):
            raise DuplicateError("crossing", str(crossing.ident))
        if self.by_inventory(crossing.inventory) is not None:
            raise DuplicateError("crossing inventory number", crossing.inventory)
        self.book.execute(
            f"INSERT INTO crossings ({CROSSING_COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
            (
                encode_ident(crossing.ident),
                encode_ident(crossing.subdivision),
                encode_post(crossing.at),
                crossing.road,
                crossing.inventory,
                encode_enum(crossing.surface),
                encode_enum(crossing.warning),
                encode_bool(crossing.public),
            ),
        )

    def exists(self, ident: Ident) -> bool:
        """Whether that crossing is in the book."""
        return self.book.one("SELECT 1 FROM crossings WHERE ident = ?", (str(ident),)) is not None

    def get(self, ident: Ident) -> Crossing:
        """One crossing by its number."""
        row = self.book.one(
            f"SELECT {CROSSING_COLUMNS} FROM crossings WHERE ident = ?",
            (str(ident),),
        )
        if row is None:
            raise NotFoundError("crossing", str(ident))
        return _read_crossing(row)

    def by_inventory(self, inventory: str) -> Crossing | None:
        """The crossing carrying an inventory number, which the road quotes."""
        row = self.book.one(
            f"SELECT {CROSSING_COLUMNS} FROM crossings WHERE inventory = ?",
            (inventory.strip().upper(),),
        )
        return None if row is None else _read_crossing(row)

    def all(self) -> list[Crossing]:
        """Every crossing, in subdivision and milepost order."""
        rows = self.book.query(
            f"SELECT {CROSSING_COLUMNS} FROM crossings ORDER BY subdivision, at_post"
        )
        return [_read_crossing(row) for row in rows]

    def within(self, subdivision: Ident, span: Span) -> list[Crossing]:
        """Every crossing inside a stretch, in milepost order."""
        begin, end = encode_span(span)
        rows = self.book.query(
            f"SELECT {CROSSING_COLUMNS} FROM crossings "
            "WHERE subdivision = ? AND at_post >= ? AND at_post < ? ORDER BY at_post",
            (str(subdivision), begin, end),
        )
        return [_read_crossing(row) for row in rows]

    def remove(self, ident: Ident) -> None:
        """Take a crossing out of the book."""
        if not self.exists(ident):
            raise NotFoundError("crossing", str(ident))
        self.book.execute("DELETE FROM crossings WHERE ident = ?", (str(ident),))

    def count(self) -> int:
        """How many crossings are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM crossings")
        return 0 if row is None else int(row["n"])


@dataclass
class Bridges:
    """Every structure carrying the track."""

    book: Book

    def add(self, bridge: Bridge) -> None:
        """Write a new bridge."""
        if self.exists(bridge.ident):
            raise DuplicateError("bridge", str(bridge.ident))
        self.book.execute(
            f"INSERT INTO bridges ({BRIDGE_COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                encode_ident(bridge.ident),
                encode_ident(bridge.subdivision),
                encode_post(bridge.at),
                encode_enum(bridge.kind),
                bridge.spans,
                bridge.length_feet,
                bridge.normal_rating,
                bridge.maximum_rating,
                bridge.built,
            ),
        )

    def exists(self, ident: Ident) -> bool:
        """Whether that bridge is in the book."""
        return self.book.one("SELECT 1 FROM bridges WHERE ident = ?", (str(ident),)) is not None

    def get(self, ident: Ident) -> Bridge:
        """One bridge by its number."""
        row = self.book.one(
            f"SELECT {BRIDGE_COLUMNS} FROM bridges WHERE ident = ?",
            (str(ident),),
        )
        if row is None:
            raise NotFoundError("bridge", str(ident))
        return _read_bridge(row)

    def all(self) -> list[Bridge]:
        """Every bridge, in subdivision and milepost order."""
        rows = self.book.query(
            f"SELECT {BRIDGE_COLUMNS} FROM bridges ORDER BY subdivision, at_post"
        )
        return [_read_bridge(row) for row in rows]

    def within(self, subdivision: Ident, span: Span) -> list[Bridge]:
        """Every bridge inside a stretch, in milepost order."""
        begin, end = encode_span(span)
        rows = self.book.query(
            f"SELECT {BRIDGE_COLUMNS} FROM bridges "
            "WHERE subdivision = ? AND at_post >= ? AND at_post < ? ORDER BY at_post",
            (str(subdivision), begin, end),
        )
        return [_read_bridge(row) for row in rows]

    def weakest(self) -> Bridge | None:
        """The bridge with the lowest maximum rating, which sets the line."""
        rows = self.book.query(
            f"SELECT {BRIDGE_COLUMNS} FROM bridges ORDER BY maximum_rating, ident LIMIT 1"
        )
        return _read_bridge(rows[0]) if rows else None

    def remove(self, ident: Ident) -> None:
        """Take a bridge out of the book."""
        if not self.exists(ident):
            raise NotFoundError("bridge", str(ident))
        self.book.execute("DELETE FROM bridges WHERE ident = ?", (str(ident),))

    def count(self) -> int:
        """How many bridges are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM bridges")
        return 0 if row is None else int(row["n"])


def _read_crossing(row: object) -> Crossing:
    fields = dict(row)  # type: ignore[call-overload]
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


def _read_bridge(row: object) -> Bridge:
    fields = dict(row)  # type: ignore[call-overload]
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
