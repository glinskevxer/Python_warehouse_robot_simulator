"""Commands that print a page rather than a line."""

from __future__ import annotations

import click

from spikemaul.cli.common import book_of, day_of, failing, say, show
from spikemaul.model.ids import Ident, Kind
from spikemaul.report.audit import audit_page
from spikemaul.report.compliance import compliance_page, standings_for
from spikemaul.report.layout import Column, Table
from spikemaul.report.morning import morning_page
from spikemaul.report.rails import rail_page
from spikemaul.report.week import week_page
from spikemaul.store.tonnage import MonthlyTonnage
from spikemaul.units.tonnage import Tonnage


@click.group()
def report() -> None:
    """The pages the office prints."""


@report.command("morning")
@click.argument("code")
@click.pass_context
@failing
def morning(context: click.Context, code: str) -> None:
    """The roadmaster's morning page."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    standings = standings_for(records, subdivision, on)
    show(morning_page(records, subdivision, on, standings))
    records.close()


@report.command("compliance")
@click.argument("code")
@click.pass_context
@failing
def compliance(context: click.Context, code: str) -> None:
    """The inspection compliance page."""
    records = book_of(context)
    show(compliance_page(records, Ident.named(Kind.SUBDIVISION, code), day_of(context)))
    records.close()


@report.command("rail")
@click.argument("code")
@click.pass_context
@failing
def rail(context: click.Context, code: str) -> None:
    """The rail page: what is worn and what is due for testing."""
    records = book_of(context)
    show(rail_page(records, Ident.named(Kind.SUBDIVISION, code), day_of(context)))
    records.close()


@report.command("audit")
@click.argument("code")
@click.pass_context
@failing
def audit(context: click.Context, code: str) -> None:
    """What the book does not say, which makes every other page wrong."""
    records = book_of(context)
    show(audit_page(records, Ident.named(Kind.SUBDIVISION, code), day_of(context)))
    records.close()


@report.command("week")
@click.argument("code")
@click.argument("gang")
@click.option("--days", default=5, type=int, help="how many working days to fill")
@click.pass_context
@failing
def week(context: click.Context, code: str, gang: str, days: int) -> None:
    """The gang's week on one sheet, material and all."""
    records = book_of(context)
    show(
        week_page(
            records,
            Ident.named(Kind.SUBDIVISION, code),
            Ident.named(Kind.GANG, gang),
            day_of(context),
            days,
        )
    )
    records.close()


@click.group()
def tonnage() -> None:
    """The monthly tonnage sheets."""


@tonnage.command("post")
@click.argument("code")
@click.argument("month")
@click.argument("mgt")
@click.option("--correct", is_flag=True, help="write over a month already posted")
@click.pass_context
@failing
def post(context: click.Context, code: str, month: str, mgt: str, correct: bool) -> None:
    """Post a month's tonnage, as MONTH like 2025-01."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    year, _, number = month.partition("-")
    if not (year.isdigit() and number.isdigit()):
        raise click.UsageError("a month is written as 2025-01")
    sheet = MonthlyTonnage(
        subdivision=subdivision,
        year=int(year),
        month=int(number),
        tonnage=Tonnage.parse(mgt),
    )
    if correct:
        records.tonnage.correct(sheet)
        say(f"corrected {month} to {sheet.tonnage}")
    else:
        records.tonnage.add(sheet)
        say(f"posted {month} at {sheet.tonnage}")
    records.close()


@tonnage.command("list")
@click.argument("code")
@click.pass_context
@failing
def list_months(context: click.Context, code: str) -> None:
    """List the months posted for a subdivision, oldest first."""
    records = book_of(context)
    months = records.tonnage.months(Ident.named(Kind.SUBDIVISION, code))
    if not months:
        say("no tonnage posted")
    table = Table([Column("month"), Column("mgt", numeric=True)])
    total = Tonnage(0)
    for one in months:
        table.add(f"{one.year}-{one.month:02d}", one.tonnage.mgt)
        total = total + one.tonnage
    for row in table.lines():
        say(row)
    if months:
        say(f"{total} over {len(months)} months")
    records.close()
