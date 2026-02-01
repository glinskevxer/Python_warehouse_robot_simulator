"""Nothing imports upwards.

The package is layered and the layering is the design. Units know nothing
about records, records know nothing about storage, the rules know nothing
about printing, and the command line knows about all of it. Written down as a
table here, the layering is a fact that can be checked; left in the reviewer's
head it is an opinion that decays.

A module may import from a lower layer or from its own subpackage. Anything
else is reported with both ends named, because the fix is usually to move one
function rather than to argue about the table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from spikemaul.tools.sources import (
    PACKAGE,
    Problem,
    imported_modules,
    module_name,
    parsed,
    run,
    source_files,
)

LAYERS: Final[dict[str, int]] = {
    "errors": 0,
    "units": 1,
    "standards": 2,
    "model": 3,
    "geometry": 4,
    "ties": 4,
    "cwr": 4,
    "orders": 5,
    "program": 5,
    "rail": 5,
    "work": 5,
    "loading": 6,
    "store": 6,
    "report": 7,
    "cli": 8,
    "tools": 9,
}
"""What may import what. A module imports downwards or sideways within itself."""


def layer_of(dotted: str) -> int | None:
    """The layer a module sits in, or nothing where it is not in the table."""
    parts = dotted.split(".")
    if len(parts) < 2 or parts[0] != PACKAGE:
        return None
    return LAYERS.get(parts[1])


def subpackage_of(dotted: str) -> str | None:
    """Which subpackage a module belongs to."""
    parts = dotted.split(".")
    if len(parts) < 2 or parts[0] != PACKAGE:
        return None
    return parts[1]


def problems_in(path: Path) -> list[Problem]:
    """Every upward import in one file."""
    dotted = module_name(path)
    here = layer_of(dotted)
    if here is None:
        return []
    mine = subpackage_of(dotted)
    found = []
    for imported in imported_modules(parsed(path)):
        there = layer_of(imported)
        if there is None:
            continue
        if subpackage_of(imported) == mine:
            continue
        if there >= here:
            found.append(
                Problem(
                    path,
                    1,
                    f"{dotted} is layer {here} and imports {imported}, which is layer {there}",
                )
            )
    return found


def problems() -> list[Problem]:
    """Every upward import in the package."""
    found: list[Problem] = []
    for path in source_files():
        found.extend(problems_in(path))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "layers")


if __name__ == "__main__":
    main()
