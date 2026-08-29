"""The console script itself.

One group, one option for the book and one for the day, and the subcommands
hung off it. Every command takes the day from ``--on`` rather than reading the
clock, so a page can be reprinted for a day in the past and say what it said.
"""

from __future__ import annotations

from pathlib import Path

import click

from spikemaul import __version__
from spikemaul.cli.assets import bridge, crossing, curve, turnout
from spikemaul.cli.common import (
    BOOK_VARIABLE,
    as_day,
    book_of,
    book_path,
    day_of,
    failing,
    say,
)
from spikemaul.cli.crew import gang, person
from spikemaul.cli.cwr import cwr
from spikemaul.cli.defects import defect
from spikemaul.cli.geometry import geometry
from spikemaul.cli.inspections import inspect
from spikemaul.cli.line import line
from spikemaul.cli.orders import order
from spikemaul.cli.rails import rail
from spikemaul.cli.reports import report, tonnage
from spikemaul.cli.ties import ties
from spikemaul.cli.work import work
from spikemaul.report.audit import holes
from spikemaul.store.backup import named_for, take
from spikemaul.store.export import write_all
from spikemaul.store.migrations import MIGRATIONS
from spikemaul.store.records import start_records
from spikemaul.store.search import find as search


@click.group()
@click.option(
    "--book",
    "book",
    default=None,
    envvar=BOOK_VARIABLE,
    help="the sqlite file to work on, or set SPIKEMAUL_BOOK",
)
@click.option("--on", "on", default=None, help="the day to work as of, as 2025-05-06")
@click.version_option(__version__, prog_name="spikemaul")
@click.pass_context
@failing
def cli(context: click.Context, book: str | None, on: str | None) -> None:
    """Track department records for a shortline railroad."""
    context.ensure_object(dict)
    context.obj["book"] = book_path(book)
    context.obj["on"] = as_day(on)


@cli.command()
@click.pass_context
@failing
def init(context: click.Context) -> None:
    """Make a book, or bring an existing one up to this schema."""
    records = start_records(context.obj["book"], day_of(context))
    say(f"book at {records.book.path}, schema {records.schema}")
    records.close()


@cli.command()
@click.option("--to", "where", default=None, help="where to put the copy")
@click.pass_context
@failing
def backup(context: click.Context, where: str | None) -> None:
    """Take a copy of the book through sqlite, and check the copy."""
    records = book_of(context)
    book = Path(records.book.path)
    taken = take(records.book, Path(where) if where else named_for(book, day_of(context)))
    say(taken.describe())
    records.close()
    if not taken.is_sound:
        raise SystemExit(5)


@cli.command()
@click.argument("into", type=click.Path())
@click.pass_context
@failing
def export(context: click.Context, into: str) -> None:
    """Write the book out as one csv per table."""
    records = book_of(context)
    for written in write_all(records.book, Path(into)):
        say(written.describe())
    records.close()


@cli.command()
@click.option("--quiet", is_flag=True, help="say nothing unless something is wrong")
@click.pass_context
@failing
def verify(context: click.Context, quiet: bool) -> None:
    """Check the file, the schema and the records, and exit one if anything is wrong.

    This is the command to put in a cron job. It asks sqlite whether the file
    is sound, asks the migrations whether the schema is one this package
    understands, and asks every subdivision whether the records cover it.
    """
    records = book_of(context)
    on = day_of(context)
    said: list[str] = []
    wrong = 0

    said.append(f"schema {records.schema} of {latest_schema()}")
    for complaint in records.book.check_integrity() + records.book.foreign_key_problems():
        said.append(f"file: {complaint}")
        wrong += 1

    for subdivision in records.subdivisions.all():
        found = holes(records, subdivision.ident, on)
        said.append(f"{subdivision.code}: {len(found)} holes")
        for hole in found:
            said.append(f"  {hole.describe()}")
        wrong += len(found)

    if not records.subdivisions.all():
        said.append("the book holds no subdivisions")

    if not quiet or wrong:
        for one in said:
            say(one)
    if wrong:
        say(f"{wrong} things to put right")
        raise SystemExit(1)
    if quiet:
        say("verify: nothing to put right")


@cli.command()
@click.argument("text")
@click.pass_context
@failing
def find(context: click.Context, text: str) -> None:
    """Look for a number or a name in every register at once."""
    records = book_of(context)
    hits = search(records, text)
    if not hits:
        say(f"nothing in the book matches {text!r}")
    for hit in hits:
        say(hit.describe())
    records.close()


@cli.command()
@click.pass_context
@failing
def status(context: click.Context) -> None:
    """Say what is in the book."""
    records = book_of(context)
    say(f"book at {records.book.path}, schema {records.schema}")
    for name, count in records.counts().items():
        say(f"{count:>6}  {name}")
    records.close()


cli.add_command(line)
cli.add_command(curve)
cli.add_command(turnout)
cli.add_command(crossing)
cli.add_command(bridge)
cli.add_command(person)
cli.add_command(gang)
cli.add_command(inspect)
cli.add_command(geometry)
cli.add_command(defect)
cli.add_command(order)
cli.add_command(work)
cli.add_command(ties)
cli.add_command(rail)
cli.add_command(cwr)
cli.add_command(report)
cli.add_command(tonnage)


def latest_schema() -> int:
    """The migration number this package writes."""
    return max(one.number for one in MIGRATIONS)


def run() -> None:
    """The entry point the console script is wired to."""
    cli(obj={})
