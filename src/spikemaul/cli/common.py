"""What every command needs: the book, the day, and what to do when it fails.

The exit statuses are the contract. A script that runs this in a cron job
needs to tell the difference between the operator typing something wrong, the
book not holding what was asked for and the railroad's own rules refusing, and
it should not have to match on prose to do it.

    0  it worked
    2  the input was wrong
    3  the record is not there
    4  the rules refuse
    5  the book is missing, unreadable or at the wrong schema
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

import click

from spikemaul.cli.clock import today
from spikemaul.errors import (
    BookError,
    DuplicateError,
    InputError,
    NotFoundError,
    RuleError,
    SpikemaulError,
)
from spikemaul.model.ids import Ident, Kind
from spikemaul.report.layout import Page, render
from spikemaul.store.records import Records, open_records

STATUS = {
    InputError: 2,
    NotFoundError: 3,
    DuplicateError: 4,
    RuleError: 4,
    BookError: 5,
}
"""What each kind of failure exits with."""

Returns = TypeVar("Returns")

DEFAULT_BOOK = "spikemaul.sqlite3"

BOOK_VARIABLE = "SPIKEMAUL_BOOK"
"""The environment variable a cron job sets instead of repeating the path."""


def status_for(error: SpikemaulError) -> int:
    """The exit status for a failure, five for anything unexpected."""
    return STATUS.get(type(error), 5)


def failing(command: Callable[..., Returns]) -> Callable[..., Returns]:
    """Turn this package's errors into a message and an exit status."""

    @wraps(command)
    def wrapper(*args: Any, **kwargs: Any) -> Returns:
        try:
            return command(*args, **kwargs)
        except SpikemaulError as error:
            click.echo(f"{error}", err=True)
            raise SystemExit(status_for(error)) from error

    return wrapper


def book_of(context: click.Context) -> Records:
    """The book this invocation is working on."""
    path = context.obj["book"]
    return open_records(path)


def day_of(context: click.Context) -> date:
    """The day this invocation is working as of."""
    given = context.obj.get("on")
    return given if given is not None else today()


def as_day(text: str | None) -> date | None:
    """Read a day off the command line, refusing anything that is not one."""
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise InputError(f"{text!r} is not a day, write it as 2025-05-06") from exc


def as_ident(text: str, kind: Kind) -> Ident:
    """Read a record number off the command line."""
    return Ident.parse(text, kind)


def show(page: Page) -> None:
    """Print a page."""
    click.echo(render(page), nl=False)


def say(line: str) -> None:
    """Print one line."""
    click.echo(line)


def book_path(given: str | None) -> str:
    """Where the book is, which is the option or the name in this directory."""
    return str(Path(given or DEFAULT_BOOK))
