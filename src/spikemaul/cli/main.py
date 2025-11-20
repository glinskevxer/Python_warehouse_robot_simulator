"""The console script itself.

One group, one option for the book and one for the day, and the subcommands
hung off it. Every command takes the day from ``--on`` rather than reading the
clock, so a page can be reprinted for a day in the past and say what it said.
"""

from __future__ import annotations

import click

from spikemaul import __version__
from spikemaul.cli.common import as_day, book_of, book_path, day_of, failing, say
from spikemaul.store.records import start_records


@click.group()
@click.option("--book", "book", default=None, help="the sqlite file to work on")
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
@click.pass_context
@failing
def status(context: click.Context) -> None:
    """Say what is in the book."""
    records = book_of(context)
    say(f"book at {records.book.path}, schema {records.schema}")
    for name, count in records.counts().items():
        say(f"{count:>6}  {name}")
    records.close()


def run() -> None:
    """The entry point the console script is wired to."""
    cli(obj={})
