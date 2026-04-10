"""The rail page: what is worn and what is due for testing.

Two tables that get looked at once a month rather than every morning, and one
line at the top that is the only part anybody reads in a hurry. Rail that
holds no class is on that line, because rail in that state is a piece of
railroad running on a slow order until somebody changes it.

The wear side reports the latest reading of each rail rather than all of them.
The history matters for the projection and not for the question this page
answers, which is what is worn today.
"""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident
from spikemaul.rail.flaw import status
from spikemaul.rail.wear import WearReading
from spikemaul.report.layout import Column, Page, Table, count_of
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.records import Records
from spikemaul.units.span import Span
from spikemaul.units.tonnage import ZERO, Tonnage


def worn_out(readings: list[WearReading]) -> list[WearReading]:
    """Readings whose rail holds no class of track at all."""
    return [one for one in readings if one.class_supported() is None]


def wear_table(readings: list[WearReading], held_at: ClassOfTrack | None = None) -> Table:
    """The latest reading of each rail, worst first."""
    table = Table(
        [
            Column("milepost"),
            Column("rail"),
            Column("section"),
            Column("vertical"),
            Column("gauge face"),
            Column("combined"),
            Column("holds"),
            Column("measured"),
        ]
    )

    def rank(one: WearReading) -> tuple[int, int]:
        holds = one.class_supported()
        return (-1 if holds is None else holds.rank, one.at.hundredths)

    for one in sorted(readings, key=rank):
        holds = one.class_supported()
        below = held_at is not None and (holds is None or holds < held_at)
        table.add(
            one.at,
            one.hand.value,
            one.rail_section,
            one.vertical,
            one.gauge_face,
            one.combined,
            "nothing" if holds is None else holds,
            "below the class" if below else one.measured_on,
        )
    return table


def cycle_table(records: Records, subdivision: Ident, on: date) -> Table:
    """Where every segment stands in its flaw testing cycle."""
    table = Table(
        [
            Column("segment"),
            Column("from"),
            Column("to"),
            Column("class"),
            Column("last tested"),
            Column("since", numeric=True),
            Column("state"),
            Column("clock"),
        ]
    )
    for segment in records.segments.on(subdivision):
        last = records.flaw_tests.last_covering(subdivision, segment.span, on)
        since: Tonnage = ZERO
        if last is not None:
            since = records.tonnage.since(subdivision, last.on, on)
        standing = status(
            segment.authorized,
            on,
            last_tested=None if last is None else last.on,
            tonnage_since=since,
        )
        table.add(
            segment.ident,
            segment.span.begin,
            segment.span.end,
            segment.authorized,
            last.on if last is not None else "never",
            since.mgt,
            "due" if standing.is_due else "in cycle",
            standing.governing,
        )
    return table


def rail_page(records: Records, subdivision: Ident, on: date) -> Page:
    """The rail page for one subdivision."""
    record = records.subdivisions.get(subdivision)
    whole = Span(record.chainage.begin, record.chainage.end)
    readings = records.wear.within(subdivision, whole, on)
    page = Page(f"{record.name} rail {on.isoformat()}")

    done = worn_out(readings)
    page.say(
        f"{count_of(len(readings), 'rail')} measured, "
        f"{count_of(len(done), 'rail')} holding no class"
    )

    page.heading("wear")
    page.table(wear_table(readings), empty="no rail has been measured")

    page.heading("flaw testing")
    page.table(cycle_table(records, subdivision, on), empty="no segments on this subdivision")
    return page
