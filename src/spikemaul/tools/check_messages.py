"""The messages this package raises read like a sentence somebody said.

They end up on a terminal in front of a foreman with a defect card in his
hand, and they get read out loud over a radio. So they start in lower case
because they are usually printed after something else, they do not end in a
full stop because nothing follows them, and they do not shout.

The check is on the literal text rather than on the whole message. An f-string
that starts with a value is fine: the value is what it is, and what this is
looking for is a message written as a headline.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from spikemaul.tools.sources import Problem, parsed, run, source_files

RAISED: Final[frozenset[str]] = frozenset(
    {"InputError", "NotFoundError", "DuplicateError", "RuleError", "BookError"}
)
"""The errors whose messages this checks."""

SHOUTS: Final = "!"


def _first_text(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        for piece in node.values:
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                return piece.value
            return None
    return None


def _whole_text(node: ast.expr) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            piece.value
            for piece in node.values
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str)
        )
    return ""


def problems_in(path: Path) -> list[Problem]:
    """Every message in one file that reads like a headline."""
    found = []
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if name not in RAISED:
            continue
        first = _first_text(node.args[0])
        whole = _whole_text(node.args[0])
        if first is not None and first[:1].isupper() and not first.split()[0].isupper():
            found.append(Problem(path, node.lineno, f"{first[:30]!r} starts in upper case"))
        if whole.endswith("."):
            found.append(Problem(path, node.lineno, f"{whole[-30:]!r} ends in a full stop"))
        if SHOUTS in whole:
            found.append(Problem(path, node.lineno, "a message shouts"))
    return found


def problems() -> list[Problem]:
    """Every message in the package that reads like a headline."""
    found: list[Problem] = []
    for path in source_files():
        found.extend(problems_in(path))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "messages")


if __name__ == "__main__":
    main()
