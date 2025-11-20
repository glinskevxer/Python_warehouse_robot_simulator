"""The console script, which is the only part of this package that prints.

Everything below here returns records and pages. This layer parses what was
typed, opens the book, calls one thing, prints the answer and picks an exit
status. Where a command starts doing arithmetic of its own, the arithmetic
belongs somewhere else.
"""

from spikemaul.cli.main import run

__all__ = ["run"]
