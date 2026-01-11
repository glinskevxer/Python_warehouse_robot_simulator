"""Commands for continuous welded rail: the destress log and the heat call."""

from __future__ import annotations

import click

from spikemaul.cli.common import book_of, day_of, failing, say
from spikemaul.cwr.heat import call_from_forecast
from spikemaul.cwr.neutral import Destress, days_since_destress, neutral_at
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.order import Reason, SlowOrder
from spikemaul.report.layout import Column, Table
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.span import Span
from spikemaul.units.temperature import Sky, Temperature


@click.group()
def cwr() -> None:
    """Welded rail: the neutral temperature and what the heat says to do."""


@cwr.command("destress")
@click.argument("code")
@click.argument("span")
@click.option("--neutral", required=True, help="the rail temperature it was left at")
@click.option("--by", required=True, help="who did it")
@click.option("--method", default="heater", help="heater, rollers or cut and pull")
@click.option("--note", default="", help="anything worth writing down")
@click.pass_context
@failing
def destress(
    context: click.Context,
    code: str,
    span: str,
    neutral: str,
    by: str,
    method: str,
    note: str,
) -> None:
    """Write a destress entry into the log."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    who = records.people.get(Ident.named(Kind.PERSON, by))
    entry = Destress(
        subdivision=subdivision,
        span=Span.parse(span),
        on=day_of(context),
        neutral=Temperature.parse(neutral),
        by=who.ident,
        method=method,
        note=note,
    )
    records.destress.add(entry)
    say(entry.describe())
    records.close()


@cwr.command("log")
@click.argument("code")
@click.pass_context
@failing
def log(context: click.Context, code: str) -> None:
    """Print the destress log for a subdivision, oldest first."""
    records = book_of(context)
    entries = records.destress.on(Ident.named(Kind.SUBDIVISION, code))
    if not entries:
        say("nothing in the destress log")
    table = Table(
        [
            Column("day"),
            Column("from"),
            Column("to"),
            Column("neutral"),
            Column("method"),
            Column("by"),
            Column("state"),
        ]
    )
    for one in entries:
        table.add(
            one.on,
            one.span.begin,
            one.span.end,
            one.neutral,
            one.method,
            one.by.tail,
            "" if one.in_specification else "out of specification",
        )
    for row in table.lines():
        say(row)
    records.close()


@cwr.command("neutral")
@click.argument("code")
@click.argument("span")
@click.pass_context
@failing
def neutral(context: click.Context, code: str, span: str) -> None:
    """Say what a stretch is standing at, or that nobody knows."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    entries = records.destress.on(subdivision)
    over = Span.parse(span)
    found = neutral_at(entries, over, on)
    if found is None:
        say(f"{over} has no destress entry covering it, so its neutral temperature is unknown")
    else:
        days = days_since_destress(entries, over, on)
        say(f"{over} stands at {found}, destressed {days} days ago")
    records.close()


@cwr.command("heat")
@click.argument("code")
@click.argument("span")
@click.option("--air", required=True, help="the forecast air temperature")
@click.option("--sky", default="clear", help="clear, partly or overcast")
@click.option("--degrees", default=None, help="the curve, where the stretch is one")
@click.option("--issue", is_flag=True, help="put the order on if one is called for")
@click.option("--authority", default="", help="whose authority the order goes on")
@click.pass_context
@failing
def heat(
    context: click.Context,
    code: str,
    span: str,
    air: str,
    sky: str,
    degrees: str | None,
    issue: bool,
    authority: str,
) -> None:
    """Make the morning heat call for a stretch."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    over = Span.parse(span)
    called = call_from_forecast(
        Temperature.parse(air),
        Sky.parse(sky),
        records.destress.on(subdivision),
        over,
        on,
        curve=Curvature.parse(degrees) if degrees else TANGENT,
    )
    say(called.describe())
    if issue and called.is_restricted and called.cap is not None:
        if not authority.strip():
            records.close()
            raise click.UsageError("a heat order needs an authority to go on")
        number = records.orders.next_number(on.year)
        records.orders.add(
            SlowOrder(
                ident=number,
                subdivision=subdivision,
                span=over,
                speed=called.cap,
                reason=Reason.HEAT,
                effective=on,
                authority=authority,
                expires=on,
            )
        )
        say(f"issued {number}, lapses {on.isoformat()}")
    records.close()
