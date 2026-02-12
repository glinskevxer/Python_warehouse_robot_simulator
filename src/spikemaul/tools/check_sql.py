"""Values reach sqlite as parameters, and only identifiers are interpolated.

Every value that comes from outside this package goes into a statement as a
question mark and is bound. What is interpolated into the sql text is the name
of a table or a list of columns, and those come from constants in this package
rather than from anything anybody typed.

The check works by listing what may be interpolated. That list is short and
adding to it is a decision somebody makes on purpose, which is the point: a
new f-string in a statement fails the build until its name is on the list, and
putting it there is where somebody asks whether it is a value.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from spikemaul.tools.sources import Problem, parsed, run, source_files

RUNS_SQL: Final[frozenset[str]] = frozenset({"execute", "query", "one"})
"""The calls that take a statement."""

IDENTIFIERS: Final[frozenset[str]] = frozenset(
    {
        "table",
        "_column_list",
        "COLUMNS",
        "APPLIED_TABLE",
        "LENGTH_COLUMNS",
        "WEAR_COLUMNS",
        "CROSSING_COLUMNS",
        "BRIDGE_COLUMNS",
        "clause",
        "assignments",
        "marks",
        "order",
        "ordered_by",
        "by",
    }
)
"""What may be interpolated into a statement, all of them names of columns or
tables that this package owns."""


def _interpolated(node: ast.JoinedStr) -> list[str]:
    out = []
    for piece in node.values:
        if not isinstance(piece, ast.FormattedValue):
            continue
        value = piece.value
        if isinstance(value, ast.Name):
            out.append(value.id)
        elif isinstance(value, ast.Attribute):
            out.append(value.attr)
        elif isinstance(value, ast.BoolOp | ast.IfExp):
            out.append("an expression")
        else:
            out.append("something that is not a name")
    return out


def problems_in(path: Path) -> list[Problem]:
    """Every statement in one file that interpolates something it should not."""
    found = []
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else None
        if name not in RUNS_SQL or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.BinOp):
            found.append(Problem(path, node.lineno, "a statement is built with an operator"))
            continue
        if not isinstance(first, ast.JoinedStr):
            continue
        for interpolated in _interpolated(first):
            if interpolated not in IDENTIFIERS:
                found.append(
                    Problem(
                        path,
                        node.lineno,
                        f"{interpolated} is interpolated into a statement and is not"
                        " a known identifier",
                    )
                )
    return found


def problems() -> list[Problem]:
    """Every statement in the package that interpolates something it should not."""
    found: list[Problem] = []
    for path in source_files():
        found.extend(problems_in(path))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "sql")


if __name__ == "__main__":
    main()
