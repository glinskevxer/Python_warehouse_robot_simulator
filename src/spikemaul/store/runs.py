"""The geometry readings, which are stored as a run and never as loose rows.

A reading on its own is close to meaningless. Warp needs its neighbours,
profile needs the run's spacing to be believed, and a reading with no run
around it cannot say whether the station before it was missing. So the
register writes and reads whole runs, and the only way to get a reading out of
here is to get the run it belongs to.

The ordinal column is the position in the file the geometry car handed over.
It is kept rather than derived so that a run reloaded from the book comes back
in the order it was recorded even if two stations share a milepost number,
which happens either side of an equation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.reading import Reading, Run
from spikemaul.store.book import Book
from spikemaul.store.codec import (
    decode_bool,
    decode_inches,
    decode_post,
    encode_bool,
    encode_ident,
    encode_inches,
    encode_post,
)
from spikemaul.units.measure import Inches

COLUMNS = (
    "inspection, ordinal, at_post, gauge, crosslevel, profile, alignment, "
    "on_curve, designated_elevation"
)


@dataclass
class Runs:
    """Every geometry run in the book, kept whole."""

    book: Book

    def add(self, run: Run) -> None:
        """Write a whole run, or none of it."""
        if self.exists(run.inspection):
            raise DuplicateError("geometry run", str(run.inspection))
        with self.book.writing():
            for ordinal, reading in enumerate(run.readings, start=1):
                self.book.execute(
                    f"INSERT INTO readings ({COLUMNS}) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        encode_ident(run.inspection),
                        ordinal,
                        encode_post(reading.at),
                        encode_inches(reading.gauge),
                        encode_inches(reading.crosslevel),
                        encode_inches(reading.profile),
                        encode_inches(reading.alignment),
                        encode_bool(reading.on_curve),
                        _elevation_out(reading.designated_elevation),
                    ),
                )

    def exists(self, inspection: Ident) -> bool:
        """Whether a run was recorded against that inspection."""
        found = self.book.one(
            "SELECT 1 FROM readings WHERE inspection = ? LIMIT 1", (str(inspection),)
        )
        return found is not None

    def get(self, inspection: Ident, subdivision: Ident, on: date) -> Run:
        """The run recorded against an inspection, in the order it was taken."""
        rows = self.book.query(
            f"SELECT {COLUMNS} FROM readings WHERE inspection = ? ORDER BY ordinal",
            (str(inspection),),
        )
        if not rows:
            raise NotFoundError("geometry run", str(inspection))
        readings = [_read(row) for row in rows]
        return Run(inspection=inspection, subdivision=subdivision, on=on, readings=readings)

    def remove(self, inspection: Ident) -> None:
        """Take a whole run out of the book."""
        if not self.exists(inspection):
            raise NotFoundError("geometry run", str(inspection))
        self.book.execute("DELETE FROM readings WHERE inspection = ?", (str(inspection),))

    def count_readings(self, inspection: Ident) -> int:
        """How many stations a run holds."""
        row = self.book.one(
            "SELECT COUNT(*) AS n FROM readings WHERE inspection = ?", (str(inspection),)
        )
        return 0 if row is None else int(row["n"])

    def runs_recorded(self) -> list[Ident]:
        """The inspection numbers that have a run against them."""
        rows = self.book.query("SELECT DISTINCT inspection FROM readings ORDER BY inspection")
        return [Ident.parse(str(row["inspection"]), Kind.INSPECTION) for row in rows]


def _elevation_out(elevation: Inches | None) -> int | None:
    return None if elevation is None else encode_inches(elevation)


def _read(row: object) -> Reading:
    fields = dict(row)  # type: ignore[call-overload]
    designated = fields["designated_elevation"]
    return Reading(
        at=decode_post(fields["at_post"]),
        gauge=decode_inches(fields["gauge"]),
        crosslevel=decode_inches(fields["crosslevel"]),
        profile=decode_inches(fields["profile"]),
        alignment=decode_inches(fields["alignment"]),
        on_curve=decode_bool(fields["on_curve"]),
        designated_elevation=None if designated is None else decode_inches(designated),
    )
