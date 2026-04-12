"""The speed profile, built out of the book.

The profile itself is arithmetic over a list of caps and lives in
``spikemaul.orders.governing``, which knows nothing about a book. Getting the
caps out of the book is this module's job, and it was written twice in the
command line before it was written once here.

The page is worth having as well as the command. A profile with a gap in it is
the clearest way to see that a subdivision has track nobody has recorded a
segment for, and that reads better as a page than as a line of output.
"""

from __future__ import annotations

from datetime import date

from spikemaul.model.ids import Ident
from spikemaul.orders.governing import (
    Cap,
    SpeedPiece,
    caps_from_curves,
    caps_from_orders,
    caps_from_segments,
    gaps,
    profile,
)
from spikemaul.orders.running import cost_of, ranked_by_cost, running_time
from spikemaul.report.layout import Column, Page, Table
from spikemaul.standards.classes import Traffic
from spikemaul.store.records import Records
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


def caps_for(
    records: Records,
    subdivision: Ident,
    over: Span,
    on: date,
    traffic: Traffic = Traffic.FREIGHT,
) -> list[Cap]:
    """Every cap the book knows about over a stretch on a day."""
    orders = [one for one in records.orders.all() if one.subdivision == subdivision]
    return [
        *caps_from_segments(records.segments.covering(subdivision, over), traffic),
        *caps_from_curves(records.curves.covering(subdivision, over)),
        *caps_from_orders(orders, on),
    ]


def profile_for(
    records: Records,
    subdivision: Ident,
    over: Span,
    on: date,
    traffic: Traffic = Traffic.FREIGHT,
) -> list[SpeedPiece]:
    """The speed at every foot of a stretch, out of the book."""
    return profile(over, caps_for(records, subdivision, over, on, traffic))


def profile_table(pieces: list[SpeedPiece]) -> Table:
    """The profile as a table."""
    table = Table(
        [
            Column("from"),
            Column("to"),
            Column("miles", numeric=True),
            Column("speed", numeric=True),
            Column("because"),
            Column("detail"),
        ]
    )
    for piece in pieces:
        table.add(
            piece.span.begin,
            piece.span.end,
            piece.span.miles,
            piece.speed.mph,
            piece.because,
            piece.detail,
        )
    return table


def speed_page(
    records: Records,
    subdivision: Ident,
    over: Span,
    on: date,
    timetable: Speed | None = None,
) -> Page:
    """The speed profile page for one stretch."""
    record = records.subdivisions.get(subdivision)
    caps = caps_for(records, subdivision, over, on)
    pieces = profile(over, caps)
    page = Page(f"{record.name} speed profile {over} {on.isoformat()}")

    page.heading("profile")
    page.table(profile_table(pieces), empty="no record covers any of this stretch")

    holes = gaps(over, caps)
    if holes:
        page.heading("not covered")
        for hole in holes:
            page.say(f"{hole} has no segment recorded")

    time = running_time(pieces)
    page.heading("running time")
    page.say(time.describe())
    if timetable is not None:
        page.say(f"{cost_of(pieces, timetable):.1f} minutes lost against {timetable}")
        for piece, minutes in ranked_by_cost(pieces, timetable):
            page.say(f"{minutes:6.1f}  {piece.describe()}")
    return page
