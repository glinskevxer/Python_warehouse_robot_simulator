"""The design note names code that is still there.

A design note is worth having and it rots faster than the code, because
nothing breaks when it goes stale. The cheapest fix is to make it name things
in a form a machine can check: every dotted module path written in backticks
has to be a module in this package.

It says nothing about whether the prose is true. That is what reviews are for.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from spikemaul.tools.sources import (
    PACKAGE,
    Problem,
    module_name,
    project_root,
    run,
    source_files,
)

NOTE: Final = "docs/design.md"

NAMED = re.compile(rf"`({PACKAGE}(?:\.[a-z_]+)+)`")
"""Every dotted module path the note writes in backticks."""


def note() -> Path:
    """Where the design note is."""
    return project_root() / NOTE


def modules() -> set[str]:
    """Every module in the package, dotted."""
    return {module_name(one) for one in source_files()}


def named_in(text: str) -> list[str]:
    """Every module path the note names."""
    return sorted(set(NAMED.findall(text)))


def problems() -> list[Problem]:
    """Every module the note names that is not here."""
    path = note()
    if not path.exists():
        return [Problem(path, 1, "there is no design note")]
    have = modules()
    found = []
    for named in named_in(path.read_text(encoding="utf-8")):
        if named not in have:
            found.append(Problem(path, 1, f"the note names {named}, which is not here"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "design")


if __name__ == "__main__":
    main()
