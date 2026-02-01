"""One place asks what day it is.

Every report in this package can be printed for a day in the past and has to
say what it said on the day. That only works if the day arrives as an
argument, and it only stays working if nobody quietly adds a call to the
system clock three layers down where it looks harmless.

So there is one module allowed to ask, and this check fails the build when a
second one appears. It reads the source rather than importing it, so a call
inside a function that never runs is caught the same as one at the top.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from spikemaul.tools.sources import Problem, module_name, parsed, run, source_files

ALLOWED: Final = "spikemaul.cli.clock"
"""The one module that may read the clock."""

CALLS: Final[tuple[str, ...]] = (
    "date.today",
    "datetime.now",
    "datetime.today",
    "datetime.utcnow",
    "time.time",
    "time.monotonic",
)
"""What asking the clock looks like."""


def _called(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
        return f"{func.value.attr}.{func.attr}"
    return None


def problems_in(path: Path) -> list[Problem]:
    """Every call to the clock in one file."""
    if module_name(path) == ALLOWED:
        return []
    found = []
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.Call):
            continue
        called = _called(node)
        if called in CALLS:
            found.append(Problem(path, node.lineno, f"{called} is only called in {ALLOWED}"))
    return found


def problems() -> list[Problem]:
    """Every call to the clock outside the one place allowed to make it."""
    found: list[Problem] = []
    for path in source_files():
        found.extend(problems_in(path))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "clock")


if __name__ == "__main__":
    main()
