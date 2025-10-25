"""The roadmaster's morning page.

One page, printed before anybody goes out, in the order the questions get
asked. What is out of service, because that stops trains. What is on the
bulletin, because that is what the crews were given. What has to be fixed and
by when. What inspections are late. What the gangs have open.

The order is deliberate and it is not the order the records are in. Structural
questions first: a page that opens with a tidy list of work orders and buries
an out of service defect four sections down is a page that gets read to the
bottom once.
"""

from __future__ import annotations

from datetime import date

from spikemaul.errors import NotFoundError
from spikemaul.model.defect import Defect
from spikemaul.model.ids import Ident
from spikemaul.orders.bulletin import build
from spikemaul.program.compliance import Standing, late
from spikemaul.report.layout import Column, Page, Table, count_of
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.records import Records
from spikemaul.units.milepost import Milepost


def out_of_service_table(records: Records, subdivision: Ident) -> Table:
    """Open cards whose condition meets no class of track at all."""
    table = Table([Column("card"), Column("milepost"), Column("condition"), Column("reading")])
    for card in records.defects.out_of_service(subdivision):
        table.add(card.ident, f"MP {card.at}", card.condition.value, card.reading)
    return table


def bulletin_table(records: Records, subdivision: Ident, on: date) -> Table:
    """Every slow order in force on the day."""
    table = Table(
        [
            Column("order"),
            Column("from"),
            Column("to"),
            Column("speed", numeric=True),
            Column("reason"),
            Column("until"),
        ]
    )
    bulletin = build(subdivision, on, records.orders.all())
    for order in bulletin.orders:
        table.add(
            order.ident,
            order.span.begin,
            order.span.end,
            order.speed.mph,
            order.reason.value,
            order.expires or "removed",
        )
    return table


def held_at(records: Records, subdivision: Ident, post: Milepost) -> ClassOfTrack | None:
    """The class the track under a milepost is held to.

    Nothing where the book has no segment covering it, which is a hole in the
    records rather than track with no class.
    """
    try:
        return records.segments.at(subdivision, post).authorized
    except NotFoundError:
        return None


def defects_table(records: Records, subdivision: Ident, on: date) -> Table:
    """Open cards, the overdue ones first, with what they are held against.

    A card at a milepost no segment covers is printed with no class against it
    and marked, instead of being left off or given a class it does not have.
    """
    table = Table(
        [
            Column("card"),
            Column("milepost"),
            Column("condition"),
            Column("meets"),
            Column("due"),
            Column("state"),
        ]
    )
    rows: list[tuple[bool, date, Defect, date | None, str]] = []
    for card in records.defects.open_on(subdivision):
        authorized = held_at(records, subdivision, card.at)
        if authorized is None:
            rows.append((False, date.max, card, None, "no segment"))
            continue
        due = card.due_on(authorized)
        overdue = card.is_overdue(authorized, on)
        rows.append((overdue, due or date.max, card, due, "overdue" if overdue else "open"))
    for _, _, card, due, state in sorted(
        rows, key=lambda row: (not row[0], row[1], row[2].at.hundredths)
    ):
        table.add(
            card.ident,
            f"MP {card.at}",
            card.condition.value,
            "nothing" if card.meets is None else card.meets,
            due or "no date",
            state,
        )
    return table


def compliance_table(standings: list[Standing]) -> Table:
    """Inspection cycles that have run out."""
    table = Table(
        [Column("from"), Column("to"), Column("scope"), Column("last"), Column("late", True)]
    )
    for standing in late(standings):
        table.add(
            standing.span.begin,
            standing.span.end,
            standing.scope.value,
            standing.last.on if standing.last else "never",
            standing.days_late,
        )
    return table


def work_table(records: Records, subdivision: Ident, on: date) -> Table:
    """Work orders still open, the overdue ones marked."""
    table = Table(
        [
            Column("order"),
            Column("from"),
            Column("to"),
            Column("work"),
            Column("quantity", numeric=True),
            Column("gang"),
            Column("state"),
        ]
    )
    for order in records.work.open_on(subdivision):
        table.add(
            order.ident,
            order.span.begin,
            order.span.end,
            order.kind.value,
            f"{order.quantity} {order.unit}",
            order.gang.tail if order.gang else "",
            "overdue" if order.is_overdue(on) else "open",
        )
    return table


def morning_page(
    records: Records,
    subdivision: Ident,
    on: date,
    standings: list[Standing] | None = None,
) -> Page:
    """The whole page, structural questions first."""
    subdivision_record = records.subdivisions.get(subdivision)
    page = Page(f"{subdivision_record.name} morning page {on.isoformat()}")

    page.heading("out of service")
    page.table(out_of_service_table(records, subdivision), empty="nothing out of service")

    page.heading("bulletin")
    orders = bulletin_table(records, subdivision, on)
    page.table(orders, empty="no restrictions in force")

    page.heading("open defects")
    page.table(defects_table(records, subdivision, on), empty="no open defects")

    page.heading("inspections")
    page.table(compliance_table(standings or []), empty="every cycle in date")

    page.heading("work")
    work = work_table(records, subdivision, on)
    page.table(work, empty="no work open")
    page.say("")
    page.say(
        f"{count_of(len(orders.rows), 'order')} in force, "
        f"{count_of(len(work.rows), 'work order')} open"
    )
    return page
