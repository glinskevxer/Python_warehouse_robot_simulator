"""Running the console script from a test, without spelling it out each time.

Twelve test modules were each carrying the same two helpers: one to invoke the
script with a book in front of it, and one to make that book. They had drifted
apart in small ways, which is how a test file ends up asserting against a
subdivision another file did not create.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner, Result

from spikemaul.cli.main import cli


def run(book: str, *args: str) -> Result:
    """Invoke the console script against a book."""
    return CliRunner().invoke(cli, ["--book", book, *args], obj={})


def a_book(tmp_path: Path, name: str = "plains.sqlite3") -> str:
    """A book with the schema on it and nothing in it."""
    where = str(tmp_path / name)
    run(where, "init")
    return where


def with_a_subdivision(book: str, code: str = "PLAINS", name: str = "Plains") -> str:
    """The same book with one subdivision on it."""
    run(book, "line", "add", code, name, "--end", "120.00")
    return book


def with_a_segment(
    book: str,
    number: str = "014",
    span: str = "12.00-16.00",
    track_class: str = "3",
) -> str:
    """The same book with a segment on the Plains subdivision."""
    run(
        book,
        "line",
        "segment",
        "PLAINS",
        number,
        span,
        "--laid",
        "1998-06-01",
        "--class",
        track_class,
    )
    return book


def with_an_inspector(book: str, initials: str = "RSTIVERS", until: str = "2025-12-31") -> str:
    """The same book with somebody designated for track and turnouts."""
    run(
        book,
        "person",
        "add",
        initials,
        "R Stivers",
        "--craft",
        "inspector",
        "--for",
        "track,turnouts",
        "--until",
        until,
    )
    return book


def with_a_gang(book: str, code: str = "SEC2", foreman: str = "DKEHOE") -> str:
    """The same book with a foreman and a gang."""
    run(book, "person", "add", foreman, "D Kehoe", "--craft", "foreman")
    run(book, "gang", "add", code, "Section 2", "--foreman", foreman, "--headcount", "4")
    return book


def a_covered_book(tmp_path: Path) -> str:
    """A book whose one segment covers the whole subdivision, so nothing is a hole."""
    book = a_book(tmp_path)
    with_a_subdivision(book)
    with_a_segment(book, span="0.00-120.00")
    return book


def a_worked_book(tmp_path: Path) -> str:
    """A book with a subdivision, a segment, an inspector and a gang on it."""
    book = a_book(tmp_path)
    with_a_subdivision(book)
    with_a_segment(book)
    with_an_inspector(book)
    with_a_gang(book)
    return book
