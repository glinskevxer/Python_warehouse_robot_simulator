"""Commands for work orders and the gang's week."""

from __future__ import annotations

import click

from spikemaul.cli.common import as_day, book_of, day_of, failing, say
from spikemaul.errors import InputError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.work import WorkKind, WorkOrder
from spikemaul.report.layout import Column, Table
from spikemaul.report.week import needs_from
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.units.span import Span
from spikemaul.work.material import sheet
from spikemaul.work.needs import needs_from_defects
from spikemaul.work.plan import days_needed, plan_week


@click.group()
def work() -> None:
    """Work orders, what is open and what the gang has this week."""


@work.command("raise")
@click.argument("code")
@click.argument("span")
@click.argument("kind")
@click.option("--quantity", required=True, type=int, help="how much, in the work's unit")
@click.option("--by", required=True, help="who raised it")
@click.option("--due", default=None, help="the day it is wanted by")
@click.option("--gang", "gang_code", default=None, help="the gang to put on it")
@click.option("--defect", default=None, help="the card it came off")
@click.pass_context
@failing
def raise_order(
    context: click.Context,
    code: str,
    span: str,
    kind: str,
    quantity: int,
    by: str,
    due: str | None,
    gang_code: str | None,
    defect: str | None,
) -> None:
    """Raise a work order, as SPAN like 13.00-13.60."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    who = records.people.get(Ident.named(Kind.PERSON, by))
    number = records.work.next_number(on.year)
    order = WorkOrder(
        ident=number,
        subdivision=subdivision,
        span=Span.parse(span),
        kind=WorkKind.parse(kind),
        quantity=quantity,
        raised_on=on,
        raised_by=who.ident,
        due_on=as_day(due),
        gang=None if gang_code is None else Ident.named(Kind.GANG, gang_code),
        defect=None if defect is None else Ident.parse(defect, Kind.DEFECT),
    )
    records.work.add(order)
    say(f"raised {number} for {quantity} {order.unit}")
    records.close()


@work.command("assign")
@click.argument("number")
@click.argument("gang_code")
@click.pass_context
@failing
def assign(context: click.Context, number: str, gang_code: str) -> None:
    """Put a gang on a work order."""
    records = book_of(context)
    ident = Ident.parse(number, Kind.WORK)
    gang = records.gangs.get(Ident.named(Kind.GANG, gang_code))
    records.work.update(records.work.get(ident).assigned_to(gang.ident))
    say(f"{ident} is on {gang.name}")
    records.close()


@work.command("finish")
@click.argument("number")
@click.option("--quantity", default=None, type=int, help="what was actually done")
@click.pass_context
@failing
def finish(context: click.Context, number: str, quantity: int | None) -> None:
    """Close a work order out."""
    records = book_of(context)
    ident = Ident.parse(number, Kind.WORK)
    order = records.work.get(ident).finished(day_of(context), quantity)
    records.work.update(order)
    short = f", {order.shortfall} {order.unit} short" if order.shortfall else ""
    say(f"{ident} finished {day_of(context).isoformat()}{short}")
    records.close()


@work.command("list")
@click.argument("code")
@click.option("--gang", "gang_code", default=None, help="only one gang's work")
@click.option("--unassigned", is_flag=True, help="only what nobody is on")
@click.pass_context
@failing
def list_work(context: click.Context, code: str, gang_code: str | None, unassigned: bool) -> None:
    """List the work still open on a subdivision."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    if gang_code is not None:
        orders = records.work.for_gang(Ident.named(Kind.GANG, gang_code))
    elif unassigned:
        orders = records.work.unassigned(subdivision)
    else:
        orders = records.work.open_on(subdivision)
    table = Table(
        [
            Column("order"),
            Column("from"),
            Column("to"),
            Column("work"),
            Column("quantity", numeric=True),
            Column("due"),
            Column("gang"),
            Column("state"),
        ]
    )
    for one in orders:
        table.add(
            one.ident,
            one.span.begin,
            one.span.end,
            one.kind.value,
            f"{one.quantity} {one.unit}",
            one.due_on,
            one.gang.tail if one.gang else "",
            "overdue" if one.is_overdue(on) else "open",
        )
    for row in table.lines():
        say(row)
    records.close()


@work.command("needs")
@click.argument("code")
@click.option("--class", "held", default=None, help="hold everything to one class")
@click.pass_context
@failing
def needs(context: click.Context, code: str, held: str | None) -> None:
    """Say what the open defect cards call for, before anybody is put on it."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    cards = records.defects.open_on(subdivision)
    if held is not None:
        wanted = [ClassOfTrack.parse(held)] * len(cards)
    else:
        wanted = []
        for card in cards:
            try:
                wanted.append(records.segments.at(subdivision, card.at).authorized)
            except NotFoundError as exc:
                raise InputError(
                    f"{card.ident} is at MP {card.at} where no segment is recorded, "
                    "so give a class with --class"
                ) from exc
    found = []
    for card, against in zip(cards, wanted, strict=True):
        found.extend(needs_from_defects([card], against))
    if not found:
        say("nothing needed")
    for one in found:
        say(one.describe())
    say(f"{days_needed(found)} gang days")
    records.close()


@work.command("material")
@click.argument("code")
@click.option("--gang", "gang_code", default=None, help="only one gang's work")
@click.pass_context
@failing
def material(context: click.Context, code: str, gang_code: str | None) -> None:
    """Say what the open work needs on the ground before anybody goes."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    orders = (
        records.work.for_gang(Ident.named(Kind.GANG, gang_code))
        if gang_code is not None
        else records.work.open_on(subdivision)
    )
    for line in sheet(needs_from(orders)):
        say(line)
    records.close()


@work.command("plan")
@click.argument("code")
@click.argument("gang_code")
@click.option("--days", default=5, type=int, help="how many working days to fill")
@click.pass_context
@failing
def plan(context: click.Context, code: str, gang_code: str, days: int) -> None:
    """Fill a gang's week from the work open on a subdivision."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    gang = records.gangs.get(Ident.named(Kind.GANG, gang_code))
    orders = records.work.for_gang(gang.ident) or records.work.open_on(subdivision)
    for line in plan_week(gang.ident, needs_from(orders), on, days).lines():
        say(line)
    records.close()
