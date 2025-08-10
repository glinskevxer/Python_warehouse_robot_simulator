"""Rail wear readings and flaw test records.

Neither of these has a number of its own. A wear reading is identified by
where it was taken, which rail it was, and when, because that is exactly what
makes two readings comparable and a projection possible. A flaw test is
identified by the inspection it was recorded on, because the run itself is
already a record.

The tonnage at the time of a flaw test is stored with it rather than worked
out later from the monthly sheets. Sheets get corrected, and a cycle that
moves because somebody reissued a sheet from two years ago is a cycle nobody
can plan against.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.rail.wear import WearReading
from spikemaul.store.book import Book
from spikemaul.store.codec import (
    decode_curvature,
    decode_date,
    decode_enum,
    decode_ident,
    decode_inches,
    decode_post,
    decode_tonnage,
    encode_curvature,
    encode_date,
    encode_enum,
    encode_ident,
    encode_inches,
    encode_post,
    encode_span,
    encode_tonnage,
)
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.tonnage import Tonnage

WEAR_COLUMNS = (
    "subdivision, at_post, hand, measured_on, rail_section, vertical, gauge_face, curvature"
)


@dataclass(frozen=True)
class FlawTest:
    """One detector run over a stretch, and what it found."""

    inspection: Ident
    subdivision: Ident
    span: Span
    on: date
    tonnage_at: Tonnage
    found: int = 0

    def describe(self) -> str:
        """One line for the flaw testing page."""
        return (
            f"{self.inspection} {self.on.isoformat()} {self.subdivision.tail} {self.span} "
            f"at {self.tonnage_at}, {self.found} found"
        )


@dataclass
class WearReadings:
    """Every rail wear reading anybody has taken."""

    book: Book

    def add(self, reading: WearReading, subdivision: Ident) -> None:
        """Write a reading, refusing a second one of the same rail on a day."""
        if self.has(subdivision, reading.at, reading.hand, reading.measured_on):
            raise DuplicateError(
                "wear reading",
                f"{subdivision.tail} MP {reading.at} {reading.hand.value} {reading.measured_on}",
            )
        self.book.execute(
            f"INSERT INTO wear_readings ({WEAR_COLUMNS}) VALUES (?,?,?,?,?,?,?,?)",
            (
                encode_ident(subdivision),
                encode_post(reading.at),
                encode_enum(reading.hand),
                encode_date(reading.measured_on),
                reading.rail_section,
                encode_inches(reading.vertical),
                encode_inches(reading.gauge_face),
                encode_curvature(reading.curve),
            ),
        )

    def has(self, subdivision: Ident, at: Milepost, hand: Hand, on: date) -> bool:
        """Whether that rail was already measured on that day."""
        found = self.book.one(
            "SELECT 1 FROM wear_readings WHERE subdivision = ? AND at_post = ? "
            "AND hand = ? AND measured_on = ?",
            (str(subdivision), at.hundredths, encode_enum(hand), encode_date(on)),
        )
        return found is not None

    def at(self, subdivision: Ident, at: Milepost, hand: Hand) -> list[WearReading]:
        """Every reading of one rail at one place, oldest first."""
        rows = self.book.query(
            f"SELECT {WEAR_COLUMNS} FROM wear_readings WHERE subdivision = ? AND at_post = ? "
            "AND hand = ? ORDER BY measured_on",
            (str(subdivision), at.hundredths, encode_enum(hand)),
        )
        return [_read_wear(row) for row in rows]

    def within(self, subdivision: Ident, span: Span, on_or_before: date) -> list[WearReading]:
        """The latest reading of each rail inside a stretch, up to a day."""
        begin, end = encode_span(span)
        rows = self.book.query(
            f"SELECT {WEAR_COLUMNS} FROM wear_readings WHERE subdivision = ? "
            "AND at_post >= ? AND at_post < ? AND measured_on <= ? "
            "ORDER BY at_post, hand, measured_on",
            (str(subdivision), begin, end, encode_date(on_or_before)),
        )
        latest: dict[tuple[int, str], WearReading] = {}
        for row in rows:
            reading = _read_wear(row)
            latest[(reading.at.hundredths, reading.hand.value)] = reading
        return [latest[key] for key in sorted(latest)]

    def count(self) -> int:
        """How many readings are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM wear_readings")
        return 0 if row is None else int(row["n"])


@dataclass
class FlawTests:
    """Every detector run recorded."""

    book: Book

    def add(self, test: FlawTest) -> None:
        """Write a detector run."""
        if self.exists(test.inspection):
            raise DuplicateError("flaw test", str(test.inspection))
        begin, end = encode_span(test.span)
        self.book.execute(
            "INSERT INTO flaw_tests (inspection, subdivision, begin_post, end_post, on_day, "
            "tonnage_at, found) VALUES (?,?,?,?,?,?,?)",
            (
                encode_ident(test.inspection),
                encode_ident(test.subdivision),
                begin,
                end,
                encode_date(test.on),
                encode_tonnage(test.tonnage_at),
                test.found,
            ),
        )

    def exists(self, inspection: Ident) -> bool:
        """Whether a detector run was recorded against that inspection."""
        found = self.book.one("SELECT 1 FROM flaw_tests WHERE inspection = ?", (str(inspection),))
        return found is not None

    def get(self, inspection: Ident) -> FlawTest:
        """One detector run."""
        row = self.book.one(
            "SELECT inspection, subdivision, begin_post, end_post, on_day, tonnage_at, found "
            "FROM flaw_tests WHERE inspection = ?",
            (str(inspection),),
        )
        if row is None:
            raise NotFoundError("flaw test", str(inspection))
        return _read_test(row)

    def on(self, subdivision: Ident) -> list[FlawTest]:
        """Every detector run on a subdivision, oldest first."""
        rows = self.book.query(
            "SELECT inspection, subdivision, begin_post, end_post, on_day, tonnage_at, found "
            "FROM flaw_tests WHERE subdivision = ? ORDER BY on_day, inspection",
            (str(subdivision),),
        )
        return [_read_test(row) for row in rows]

    def last_covering(self, subdivision: Ident, span: Span, on_or_before: date) -> FlawTest | None:
        """The most recent run taking in the whole of a stretch."""
        begin, end = encode_span(span)
        rows = self.book.query(
            "SELECT inspection, subdivision, begin_post, end_post, on_day, tonnage_at, found "
            "FROM flaw_tests WHERE subdivision = ? AND begin_post <= ? AND end_post >= ? "
            "AND on_day <= ? ORDER BY on_day DESC, inspection DESC LIMIT 1",
            (str(subdivision), begin, end, encode_date(on_or_before)),
        )
        return _read_test(rows[0]) if rows else None

    def count(self) -> int:
        """How many detector runs are in the book."""
        row = self.book.one("SELECT COUNT(*) AS n FROM flaw_tests")
        return 0 if row is None else int(row["n"])


def _read_wear(row: object) -> WearReading:
    fields = dict(row)  # type: ignore[call-overload]
    return WearReading(
        at=decode_post(fields["at_post"]),
        hand=decode_enum(Hand, fields["hand"]),
        rail_section=str(fields["rail_section"]),
        vertical=decode_inches(fields["vertical"]),
        gauge_face=decode_inches(fields["gauge_face"]),
        measured_on=decode_date(fields["measured_on"]),
        curve=decode_curvature(fields["curvature"]),
    )


def _read_test(row: object) -> FlawTest:
    fields = dict(row)  # type: ignore[call-overload]
    return FlawTest(
        inspection=decode_ident(fields["inspection"], Kind.INSPECTION),
        subdivision=decode_ident(fields["subdivision"], Kind.SUBDIVISION),
        span=Span(decode_post(fields["begin_post"]), decode_post(fields["end_post"])),
        on=decode_date(fields["on_day"]),
        tonnage_at=decode_tonnage(fields["tonnage_at"]),
        found=int(fields["found"]),
    )
