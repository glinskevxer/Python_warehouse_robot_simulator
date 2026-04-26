"""Copying the book, through sqlite rather than through the filesystem.

A book copied with ``cp`` while somebody has it open is a book with half a
transaction in it. Sqlite's own backup takes a consistent copy of a live
database, so that is what this uses, and it asks the copy both integrity
questions afterwards rather than assuming.

The copy is named after the day it was taken. A backup called
``plains-backup.sqlite3`` is a backup nobody can date, and the first thing
anybody asks about a restored book is how old it is.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from spikemaul.errors import BookError
from spikemaul.store.book import Book, open_book


@dataclass(frozen=True)
class Backup:
    """One copy taken, and what sqlite said about it."""

    where: Path
    tables: int
    problems: list[str]

    @property
    def is_sound(self) -> bool:
        """Whether sqlite is happy with the copy."""
        return not self.problems

    def describe(self) -> str:
        """One line for whoever ran it."""
        if self.is_sound:
            return f"{self.where} holds {self.tables} tables and reads clean"
        return f"{self.where} has {len(self.problems)} problems with it"


def named_for(book: Path, on: date) -> Path:
    """Where a backup taken on a day goes, beside the book it came from."""
    return book.with_name(f"{book.stem}-{on.isoformat()}{book.suffix}")


def take(book: Book, where: Path) -> Backup:
    """Copy a live book and ask the copy whether it is sound."""
    if where.exists():
        raise BookError(f"there is already a backup at {where}")
    where.parent.mkdir(parents=True, exist_ok=True)
    copy = sqlite3.connect(str(where))
    try:
        book.connection.backup(copy)
    except sqlite3.Error as exc:
        copy.close()
        where.unlink(missing_ok=True)
        raise BookError(f"the backup did not finish: {exc}") from exc
    copy.close()

    with open_book(where) as taken:
        problems = taken.check_integrity() + taken.foreign_key_problems()
        tables = len(taken.tables)
    return Backup(where=where, tables=tables, problems=problems)


def restore(backup: Path, onto: Path) -> Path:
    """Put a backup back, refusing to write over a book that is already there."""
    if not backup.exists():
        raise BookError(f"there is no backup at {backup}")
    if onto.exists():
        raise BookError(f"{onto} is already there, move it before restoring")
    with open_book(backup) as source:
        copy = sqlite3.connect(str(onto))
        try:
            source.connection.backup(copy)
        finally:
            copy.close()
    return onto
