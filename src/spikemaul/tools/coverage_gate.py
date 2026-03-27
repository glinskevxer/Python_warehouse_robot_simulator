"""A floor under the coverage, and a list of what is closest to it.

Two numbers rather than one. A total, because a package that is ninety eight
percent covered with one file at forty is not ninety eight percent covered
where it matters, and a per file floor that catches exactly that.

The gate reads the json report rather than running the tests itself. That
keeps it out of the way of how the tests are run and means the same report can
be uploaded as a build artifact and read later, which is the only way to argue
about whether a number moved.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from spikemaul.tools.sources import project_root

REPORT = "coverage.json"
"""Where the json report is written, relative to the checkout."""


@dataclass(frozen=True)
class FileCoverage:
    """One file's coverage, as the report gives it."""

    name: str
    percent: float
    missing: int

    def describe(self) -> str:
        """One line for the gate's output."""
        return f"{self.percent:6.2f}%  {self.missing:4d} missing  {self.name}"


@dataclass(frozen=True)
class Coverage:
    """The whole report, read."""

    total: float
    files: list[FileCoverage]

    def worst(self, count: int) -> list[FileCoverage]:
        """The files with the least coverage, fewest first."""
        return sorted(self.files, key=lambda one: (one.percent, one.name))[:count]

    def below(self, floor: float) -> list[FileCoverage]:
        """Every file under a floor."""
        return [one for one in self.worst(len(self.files)) if one.percent < floor]


def read(path: Path) -> Coverage:
    """Read a coverage json report."""
    if not path.exists():
        raise SystemExit(f"there is no coverage report at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    files = [
        FileCoverage(
            name=name,
            percent=float(one["summary"]["percent_covered"]),
            missing=int(one["summary"]["missing_lines"]),
        )
        for name, one in data.get("files", {}).items()
    ]
    total = float(data["totals"]["percent_covered"])
    return Coverage(total=total, files=files)


def gate(coverage: Coverage, floor: float, file_floor: float, worst: int) -> tuple[int, list[str]]:
    """Say whether the report clears the floors, and what to print."""
    lines = [f"total {coverage.total:.2f}%, floor {floor:.2f}%"]
    status = 0
    if coverage.total < floor:
        lines.append(f"the total is under the floor by {floor - coverage.total:.2f} points")
        status = 1
    under = coverage.below(file_floor)
    for one in under:
        lines.append(f"under the file floor: {one.describe()}")
    if under:
        status = 1
    if worst:
        lines.append(f"the {worst} least covered files:")
        lines.extend(f"  {one.describe()}" for one in coverage.worst(worst))
    return status, lines


def main() -> None:
    """Read the report, apply the floors and exit."""
    parser = argparse.ArgumentParser(description="put a floor under the coverage")
    parser.add_argument("--floor", type=float, default=95.0, help="the floor for the total")
    parser.add_argument("--file-floor", type=float, default=80.0, help="the floor per file")
    parser.add_argument("--worst", type=int, default=5, help="how many thin files to list")
    parser.add_argument("--report", default=None, help="where the json report is")
    given = parser.parse_args()
    path = Path(given.report) if given.report else project_root() / REPORT
    status, lines = gate(read(path), given.floor, given.file_floor, given.worst)
    for line in lines:
        print(line)
    sys.exit(status)


if __name__ == "__main__":
    main()
