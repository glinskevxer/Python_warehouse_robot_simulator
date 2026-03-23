"""A short walk through the package, for a machine that has just installed it.

The tests are run against a checkout. This is run against whatever came out of
the wheel, in a directory with nothing else in it, and it is the only thing
that would catch a subpackage that did not ship or a console script wired to
the wrong function.

It writes into a temporary directory and takes the day as an argument, so it
says the same thing every time it is run and leaves nothing behind.
"""

from __future__ import annotations

import argparse
import tempfile
from datetime import date
from pathlib import Path

from spikemaul import __version__
from spikemaul.geometry.assessment import assess
from spikemaul.model.defect import Condition, Defect
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Segment, Subdivision
from spikemaul.model.reading import Reading, Run
from spikemaul.orders.bulletin import build
from spikemaul.report.layout import render
from spikemaul.report.morning import morning_page
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.store.records import open_records, start_records
from spikemaul.units.chainage import Chainage, Equation
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span

ON = date(2025, 5, 20)
"""The day the walk is taken on, fixed so the output does not move."""

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")


def _reading(post: str, gauge: str = "56 5/8") -> Reading:
    return Reading(
        at=Milepost.parse(post),
        gauge=Inches.parse(gauge),
        crosslevel=Inches.parse("1/4"),
        profile=Inches.parse("1/2"),
        alignment=Inches.parse("3/8"),
    )


def walk(where: Path) -> list[str]:
    """Build a small book, read it back and say what happened."""
    said = [f"spikemaul {__version__}"]
    book = where / "plains.sqlite3"
    records = start_records(book, ON)
    said.append(f"schema {records.schema}")

    records.subdivisions.add(
        Subdivision(
            PLAINS,
            "Plains",
            Chainage(
                Milepost.parse("0.00"),
                Milepost.parse("120.00"),
                (Equation(Milepost.parse("61.40"), Milepost.parse("61.15")),),
            ),
        )
    )
    records.segments.add(
        Segment(
            ident=Ident.named(Kind.SEGMENT, "014"),
            subdivision=PLAINS,
            span=Span.parse("12.00-14.00"),
            kind=TrackKind.MAIN,
            authorized=ClassOfTrack.THREE,
            rail_section="115 RE",
            rail_laid=date(1998, 6, 1),
        )
    )
    records.close()

    again = open_records(book)
    segment = again.segments.at(PLAINS, Milepost.parse("13.00"))
    said.append(f"{segment.ident} holds {segment.authorized} at {segment.speed()}")

    run = Run(
        inspection=Ident.numbered(Kind.INSPECTION, 2025, 1),
        subdivision=PLAINS,
        on=ON,
        readings=[_reading("12.00"), _reading("13.00", "57 7/8"), _reading("13.50")],
    )
    reading = assess(run, segment.authorized)
    said.append(f"the run supports {reading.supports}, {reading.action.describe()}")

    again.defects.add(
        Defect(
            ident=again.defects.next_number(ON.year),
            subdivision=PLAINS,
            at=Milepost.parse("13.00"),
            found_on=ON,
            found_by=Ident.named(Kind.PERSON, "RSTIVERS"),
            condition=Condition.GAUGE,
            reading="57 7/8",
            meets=ClassOfTrack.ONE,
        )
    )
    bulletin = build(PLAINS, ON, again.orders.all())
    said.append(f"bulletin: {bulletin.describe()}")

    page = render(morning_page(again, PLAINS, ON))
    said.append(f"morning page is {len(page.splitlines())} lines")
    again.close()
    return said


def main() -> None:
    """Take the walk and print what happened."""
    parser = argparse.ArgumentParser(description="walk through the package once")
    parser.add_argument("--quiet", action="store_true", help="say nothing unless it fails")
    quiet = parser.parse_args().quiet
    with tempfile.TemporaryDirectory() as where:
        for line in walk(Path(where)):
            if not quiet:
                print(line)
    if quiet:
        print("smoke: the walk finished")


if __name__ == "__main__":
    main()
