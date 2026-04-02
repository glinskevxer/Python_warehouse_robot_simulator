"""Everything under tools is run by CI.

A check nobody runs is a check that does not exist. Writing one and forgetting
the line in the workflow is easy, and the failure is silent for exactly as
long as it matters: the check passes locally when somebody remembers, and the
build is green either way.

So the workflow is read as text and every check module in the package has to
appear in it. The workflow is yaml and this does not parse it, because the
question is whether a string is in the file and a parser is a dependency to
answer that.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from spikemaul.tools.sources import Problem, package_root, project_root, run

WORKFLOW: Final = ".github/workflows/ci.yml"

GENERATED: Final[frozenset[str]] = frozenset({"schema_dump", "build_docs"})
"""Tools that CI runs with an argument rather than on their own."""

NOT_RUN: Final[frozenset[str]] = frozenset({"sources", "coverage_gate", "smoke"})
"""Tools that are not checks: a library, a gate with arguments, and a walk."""


def workflow() -> Path:
    """Where the workflow is."""
    return project_root() / WORKFLOW


def check_modules() -> list[str]:
    """Every check module in the package."""
    return sorted(
        one.stem
        for one in (package_root() / "tools").glob("*.py")
        if one.stem not in {"__init__"} and one.stem not in NOT_RUN
    )


def problems() -> list[Problem]:
    """Every check the workflow does not run."""
    path = workflow()
    if not path.exists():
        return [Problem(path, 1, "there is no workflow")]
    text = path.read_text(encoding="utf-8")
    found = []
    for name in check_modules():
        wanted = f"spikemaul.tools.{name}"
        if wanted not in text:
            found.append(Problem(path, 1, f"the workflow does not run {wanted}"))
    for name in sorted(GENERATED):
        if f"spikemaul.tools.{name} --check" not in text:
            found.append(Problem(path, 1, f"the workflow does not check {name} is current"))
    if "coverage_gate" not in text:
        found.append(Problem(path, 1, "the workflow does not put a floor under the coverage"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "workflow")


if __name__ == "__main__":
    main()
