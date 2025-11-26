"""Commands for recording inspections and asking what is due."""

from __future__ import annotations

import click

from spikemaul.cli.common import as_day, book_of, day_of, failing, say
from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind, next_number
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.program.schedule import due_between
from spikemaul.report.compliance import standings_for
from spikemaul.report.layout import Column, Table
from spikemaul.store.records import Records
from spikemaul.units.span import Span


def _method(text: str) -> Method:
    try:
        return Method(text.strip().lower())
    except ValueError as exc:
        named = ", ".join(one.value for one in Method)
        raise InputError(f"{text!r} is not a method, we have {named}") from exc


def _scope(text: str) -> Scope:
    try:
        return Scope(text.strip().lower())
    except ValueError as exc:
        named = ", ".join(one.value for one in Scope)
        raise InputError(f"{text!r} is not a scope, we have {named}") from exc


@click.group()
def inspect() -> None:
    """Inspections, and what they leave due."""


@inspect.command("record")
@click.argument("code")
@click.argument("span")
@click.option("--by", required=True, help="the inspector's initials")
@click.option("--method", default="hi rail", help="walking, hi rail, geometry car")
@click.option("--scope", default="track", help="track, turnouts, joint bars")
@click.option("--note", default="", help="anything worth writing down")
@click.option("--force", is_flag=True, help="record it even though it will not count")
@click.pass_context
@failing
def record(
    context: click.Context,
    code: str,
    span: str,
    by: str,
    method: str,
    scope: str,
    note: str,
    force: bool,
) -> None:
    """Record an inspection over a stretch, as SPAN like 0.00-61.40."""
    records = book_of(context)
    on = day_of(context)
    wanted = _scope(scope)
    who = records.people.get(Ident.named(Kind.PERSON, by))
    if not who.may_inspect(wanted, on) and not force:
        records.close()
        raise RuleError(
            f"{who.name} is not designated for {wanted.value} on {on}, "
            "record it with --force if it happened anyway"
        )
    number = _next_inspection(records, on.year)
    records.inspections.add(
        Inspection(
            ident=number,
            subdivision=Ident.named(Kind.SUBDIVISION, code),
            span=Span.parse(span),
            on=on,
            by=who.ident,
            method=_method(method),
            scope=wanted,
            note=note,
        )
    )
    counted = "" if who.may_inspect(wanted, on) else ", which will not count"
    say(f"recorded {number} over {span} on {on}{counted}")
    records.close()


def _next_inspection(records: Records, year: int) -> Ident:
    """The next inspection number for a year, off what is already in the book."""
    return next_number(Kind.INSPECTION, year, [one.ident for one in records.inspections.all()])


@inspect.command("list")
@click.argument("code")
@click.option("--scope", default=None, help="only one scope")
@click.pass_context
@failing
def list_inspections(context: click.Context, code: str, scope: str | None) -> None:
    """List the inspections recorded on a subdivision, oldest first."""
    records = book_of(context)
    wanted = None if scope is None else _scope(scope)
    table = Table(
        [
            Column("inspection"),
            Column("day"),
            Column("from"),
            Column("to"),
            Column("scope"),
            Column("method"),
            Column("by"),
        ]
    )
    for one in records.inspections.on(Ident.named(Kind.SUBDIVISION, code), wanted):
        table.add(
            one.ident,
            one.on,
            one.span.begin,
            one.span.end,
            one.scope.value,
            one.method.value,
            one.by.tail,
        )
    for row in table.lines():
        say(row)
    records.close()


@inspect.command("due")
@click.argument("code")
@click.option("--through", default=None, help="the last day of the window")
@click.pass_context
@failing
def due(context: click.Context, code: str, through: str | None) -> None:
    """Say what is due between today and a day, late work first."""
    records = book_of(context)
    on = day_of(context)
    last = as_day(through) or on
    if last < on:
        raise InputError("a window runs forward")
    standings = standings_for(records, Ident.named(Kind.SUBDIVISION, code), on)
    lines = due_between(standings, on, last)
    if not lines:
        say("nothing due")
    for one in lines:
        say(one.describe())
    records.close()
