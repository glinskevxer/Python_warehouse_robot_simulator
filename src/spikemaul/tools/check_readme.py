"""The readme names the commands that exist, and only those.

A readme goes stale in one direction first: somebody adds a command group and
nobody adds the row. The other direction happens too and is worse, because a
reader tries the command and it is not there.

So the check is both ways. Every group on the console script is named in the
readme, and every command spelled in the readme in backticks is one the script
has.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from spikemaul.cli.main import cli
from spikemaul.tools.sources import Problem, project_root, run

README: Final = "README.md"

SPELLED = re.compile(r"`([a-z][a-z ]+)`")
"""Anything written in backticks that could be a command."""


def readme() -> Path:
    """Where the readme is."""
    return project_root() / README


def groups() -> set[str]:
    """Every group on the console script."""
    return set(cli.commands)


def named_in(text: str) -> set[str]:
    """Every command spelled in backticks in the readme."""
    return {one.strip() for one in SPELLED.findall(text)}


def problems() -> list[Problem]:
    """Every group the readme leaves out, and every command it invents."""
    path = readme()
    if not path.exists():
        return [Problem(path, 1, "there is no readme")]
    text = path.read_text(encoding="utf-8")
    spelled = named_in(text)
    found = []
    for group in sorted(groups()):
        if group not in spelled:
            found.append(Problem(path, 1, f"the readme does not name the {group} group"))
    for one in sorted(spelled):
        first = one.split()[0]
        if first in groups():
            command = cli.commands[first]
            rest = one.split()[1:]
            names = getattr(command, "commands", {})
            if rest and rest[0] not in names:
                found.append(
                    Problem(path, 1, f"the readme names {one}, which the script does not have")
                )
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "readme")


if __name__ == "__main__":
    main()
