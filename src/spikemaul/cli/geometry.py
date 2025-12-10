"""Commands for the geometry car: loading a run and reading it."""

from __future__ import annotations

import click

from spikemaul.cli.common import book_of, day_of, failing, say, show
from spikemaul.errors import InputError
from spikemaul.loading.runs import read_run
from spikemaul.model.ids import Ident, Kind, next_number
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.report.exceptions import assess_run, exception_page, worst_segment
from spikemaul.store.records import Records
from spikemaul.units.span import Span


def _next_inspection(records: Records, year: int) -> Ident:
    """The next inspection number for a year."""
    return next_number(Kind.INSPECTION, year, [one.ident for one in records.inspections.all()])


@click.group()
def geometry() -> None:
    """Geometry runs, and what they say against the class held to."""


@geometry.command("load")
@click.argument("code")
@click.argument("path", type=click.Path())
@click.option("--by", required=True, help="who ran the car, or who accepted the file")
@click.pass_context
@failing
def load(context: click.Context, code: str, path: str, by: str) -> None:
    """Load a run out of a csv and record the inspection it belongs to."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    who = records.people.get(Ident.named(Kind.PERSON, by))
    number = _next_inspection(records, on.year)
    run = read_run(path, number, subdivision, on)
    records.inspections.add(
        Inspection(
            ident=number,
            subdivision=subdivision,
            span=run.span,
            on=on,
            by=who.ident,
            method=Method.GEOMETRY_CAR,
            scope=Scope.TRACK,
            note=f"loaded from {path}",
        )
    )
    records.runs.add(run)
    say(f"loaded {number} over {run.span}, {len(run.readings)} readings")
    records.close()


@geometry.command("exceptions")
@click.argument("code")
@click.argument("inspection")
@click.pass_context
@failing
def exceptions(context: click.Context, code: str, inspection: str) -> None:
    """Print the exception log for a run already in the book."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    number = Ident.parse(inspection, Kind.INSPECTION)
    record = records.inspections.get(number)
    run = records.runs.get(number, subdivision, record.on)
    show(exception_page(records, run))
    records.close()


@geometry.command("worst")
@click.argument("code")
@click.argument("inspection")
@click.pass_context
@failing
def worst(context: click.Context, code: str, inspection: str) -> None:
    """Say which segment a run leaves holding the lowest class."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    number = Ident.parse(inspection, Kind.INSPECTION)
    record = records.inspections.get(number)
    run = records.runs.get(number, subdivision, record.on)
    found = worst_segment(assess_run(records, run))
    if found is None:
        say("the run crosses no segment with two readings on it")
    else:
        supports = found.assessment.supports
        holds = "nothing" if supports is None else str(supports)
        say(f"{found.segment.ident} {found.segment.span} holds {holds}")
        say(found.assessment.action.describe())
    records.close()


@geometry.command("runs")
@click.argument("code")
@click.pass_context
@failing
def runs(context: click.Context, code: str) -> None:
    """List the runs recorded on a subdivision."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    recorded = set(records.runs.runs_recorded())
    found = False
    for one in records.inspections.on(subdivision, Scope.TRACK):
        if one.ident not in recorded:
            continue
        found = True
        say(f"{one.ident} {one.on.isoformat()} {one.span} {records.runs.count_readings(one.ident)}")
    if not found:
        say("no runs recorded")
    records.close()


@geometry.command("span")
@click.argument("code")
@click.argument("span")
@click.pass_context
@failing
def over_span(context: click.Context, code: str, span: str) -> None:
    """Say which segments a stretch crosses and what class each is held to."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    covering = records.segments.covering(subdivision, Span.parse(span))
    if not covering:
        raise InputError(f"no segment covers {span} on {code}")
    for one in covering:
        say(one.describe())
    records.close()
