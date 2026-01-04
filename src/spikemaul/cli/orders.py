"""Commands for slow orders and the bulletin."""

from __future__ import annotations

import click

from spikemaul.cli.common import as_day, book_of, day_of, failing, say
from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.order import Reason, SlowOrder
from spikemaul.orders.bulletin import build, changes_between
from spikemaul.orders.governing import (
    caps_from_curves,
    caps_from_orders,
    caps_from_segments,
    gaps,
    profile,
)
from spikemaul.orders.running import cost_of, ranked_by_cost
from spikemaul.report.layout import Column, Table
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed


@click.group()
def order() -> None:
    """Slow orders, the bulletin and what they cost."""


@order.command("issue")
@click.argument("code")
@click.argument("span")
@click.argument("speed")
@click.option("--reason", default="track condition", help="why it is on")
@click.option("--authority", required=True, help="whose authority it is on")
@click.option("--until", default=None, help="the day it comes off by itself")
@click.option("--defect", default=None, help="the card it was raised against")
@click.pass_context
@failing
def issue(
    context: click.Context,
    code: str,
    span: str,
    speed: str,
    reason: str,
    authority: str,
    until: str | None,
    defect: str | None,
) -> None:
    """Put a slow order on, as SPAN like 13.00-13.60 and SPEED like 10."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    number = records.orders.next_number(on.year)
    records.orders.add(
        SlowOrder(
            ident=number,
            subdivision=subdivision,
            span=Span.parse(span),
            speed=Speed.parse(speed),
            reason=Reason.parse(reason),
            effective=on,
            authority=authority,
            expires=as_day(until),
            defect=None if defect is None else Ident.parse(defect, Kind.DEFECT),
        )
    )
    say(f"issued {number} {span} {speed}")
    records.close()


@order.command("lift")
@click.argument("number")
@click.pass_context
@failing
def lift(context: click.Context, number: str) -> None:
    """Take a slow order off."""
    records = book_of(context)
    ident = Ident.parse(number, Kind.ORDER)
    records.orders.update(records.orders.get(ident).lifted(day_of(context)))
    say(f"{ident} lifted {day_of(context).isoformat()}")
    records.close()


@order.command("bulletin")
@click.argument("code")
@click.pass_context
@failing
def bulletin(context: click.Context, code: str) -> None:
    """Print the bulletin for a subdivision on a day."""
    records = book_of(context)
    page = build(Ident.named(Kind.SUBDIVISION, code), day_of(context), records.orders.all())
    for line in page.lines():
        say(line)
    records.close()


@order.command("changes")
@click.argument("code")
@click.argument("since")
@click.pass_context
@failing
def changes(context: click.Context, code: str, since: str) -> None:
    """Say what went on and what came off between two days."""
    records = book_of(context)
    earlier = as_day(since)
    if earlier is None:
        raise InputError("a day is needed to compare against")
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    orders = records.orders.all()
    put_on, came_off = changes_between(
        build(subdivision, earlier, orders), build(subdivision, day_of(context), orders)
    )
    for one in put_on:
        say(f"on   {one.describe()}")
    for one in came_off:
        say(f"off  {one.describe()}")
    if not put_on and not came_off:
        say("no change")
    records.close()


@order.command("profile")
@click.argument("code")
@click.argument("span")
@click.pass_context
@failing
def speed_profile(context: click.Context, code: str, span: str) -> None:
    """Print the speed at every foot of a stretch, and what sets it."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    over = Span.parse(span)
    caps = (
        caps_from_segments(records.segments.covering(subdivision, over))
        + caps_from_curves(records.curves.covering(subdivision, over))
        + caps_from_orders(
            [one for one in records.orders.all() if one.subdivision == subdivision], on
        )
    )
    table = Table(
        [
            Column("from"),
            Column("to"),
            Column("speed", numeric=True),
            Column("because"),
            Column("detail"),
        ]
    )
    for piece in profile(over, caps):
        table.add(piece.span.begin, piece.span.end, piece.speed.mph, piece.because, piece.detail)
    for row in table.lines():
        say(row)
    for hole in gaps(over, caps):
        say(f"no record covers {hole}")
    records.close()


@order.command("cost")
@click.argument("code")
@click.argument("span")
@click.option("--timetable", required=True, help="the speed it would run at otherwise")
@click.pass_context
@failing
def cost(context: click.Context, code: str, span: str, timetable: str) -> None:
    """Say what the restrictions on a stretch cost in minutes."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    over = Span.parse(span)
    caps = (
        caps_from_segments(records.segments.covering(subdivision, over))
        + caps_from_curves(records.curves.covering(subdivision, over))
        + caps_from_orders(
            [one for one in records.orders.all() if one.subdivision == subdivision], on
        )
    )
    pieces = profile(over, caps)
    speed = Speed.parse(timetable)
    say(f"{cost_of(pieces, speed):.1f} minutes lost over {over}")
    for piece, minutes in ranked_by_cost(pieces, speed):
        say(f"{minutes:6.1f}  {piece.describe()}")
    records.close()
