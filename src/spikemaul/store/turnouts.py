"""The turnout register.

Turnouts are recorded at a point rather than over a stretch, so the questions
here are which ones are on this subdivision and which ones are inside a
stretch a gang is working. Both come back in milepost order, because a foreman
walking a siding wants them in the order he will reach them.
"""

from __future__ import annotations

from dataclasses import dataclass

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.model.turnout import FrogKind, Throw, Turnout
from spikemaul.store.book import Book
from spikemaul.store.codec import (
    decode_enum,
    decode_ident,
    decode_post,
    encode_enum,
    encode_ident,
    encode_post,
    encode_span,
)
from spikemaul.units.span import Span

COLUMNS = "ident, subdivision, point_of_switch, size, hand, frog, throw, leads_to"


@dataclass
class Turnouts:
    """Every turnout on the railroad."""

    book: Book

    def add(self, turnout: Turnout) -> None:
        """Write a new turnout."""
        if self.exists(turnout.ident):
            raise DuplicateError("turnout", str(turnout.ident))
        self.book.execute(
            f"INSERT INTO turnouts ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
            (
                encode_ident(turnout.ident),
                encode_ident(turnout.subdivision),
                encode_post(turnout.point_of_switch),
                turnout.size,
                encode_enum(turnout.hand),
                encode_enum(turnout.frog),
                encode_enum(turnout.throw),
                turnout.leads_to,
            ),
        )

    def exists(self, ident: Ident) -> bool:
        """Whether that turnout is in the book."""
        return self.book.one("SELECT 1 FROM turnouts WHERE ident = ?", (str(ident),)) is not None

    def get(self, ident: Ident) -> Turnout:
        """One turnout by its number."""
        row = self.book.one(
            f"SELECT {COLUMNS} FROM turnouts WHERE ident = ?",
            (str(ident),),
        )
        if row is None:
            raise NotFoundError("turnout", str(ident))
        return _read(row)

    def all(self) -> list[Turnout]:
        """Every turnout, in subdivision and milepost order."""
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM turnouts ORDER BY subdivision, point_of_switch"
        )
        return [_read(row) for row in rows]

    def on(self, subdivision: Ident) -> list[Turnout]:
        """Every turnout on one subdivision, in milepost order."""
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM turnouts WHERE subdivision = ? ORDER BY point_of_switch",
            (str(subdivision),),
        )
        return [_read(row) for row in rows]

    def within(self, subdivision: Ident, span: Span) -> list[Turnout]:
        """Every turnout whose point of switch is inside a stretch."""
        begin, end = encode_span(span)
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM turnouts "
            "WHERE subdivision = ? AND point_of_switch >= ? AND point_of_switch < ? "
            "ORDER BY point_of_switch",
            (str(subdivision), begin, end),
        )
        return [_read(row) for row in rows]

    def update(self, turnout: Turnout) -> None:
        """Write a turnout that is already in the book."""
        if not self.exists(turnout.ident):
            raise NotFoundError("turnout", str(turnout.ident))
        self.book.execute(
            "UPDATE turnouts SET subdivision = ?, point_of_switch = ?, size = ?, hand = ?, "
            "frog = ?, throw = ?, leads_to = ? WHERE ident = ?",
            (
                encode_ident(turnout.subdivision),
                encode_post(turnout.point_of_switch),
                turnout.size,
                encode_enum(turnout.hand),
                encode_enum(turnout.frog),
                encode_enum(turnout.throw),
                turnout.leads_to,
                encode_ident(turnout.ident),
            ),
        )

    def remove(self, ident: Ident) -> None:
        """Take a turnout out of the book."""
        if not self.exists(ident):
            raise NotFoundError("turnout", str(ident))
        self.book.execute("DELETE FROM turnouts WHERE ident = ?", (str(ident),))

    def count(self) -> int:
        """How many turnouts are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM turnouts")
        return 0 if row is None else int(row["n"])


def _read(row: object) -> Turnout:
    fields = dict(row)  # type: ignore[call-overload]
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
