"""Would this tree ship.

Three things go wrong on the day somebody cuts a release and all three are
quiet. The version in the package and the version in the packaging disagree,
so the wheel is built with a number nobody meant. The changelog has nothing
under the version being cut, so whatever shipped is whatever was in git. And a
generated document is stale, so the reference the release publishes describes
the release before it.

None of that is caught by the tests, because none of it is wrong until
somebody tries to ship.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from spikemaul import __version__
from spikemaul.tools.build_docs import is_current as docs_are_current
from spikemaul.tools.build_glossary import is_current as glossary_is_current
from spikemaul.tools.schema_dump import is_current as schema_is_current
from spikemaul.tools.sources import Problem, project_root, run

CHANGELOG: Final = "CHANGELOG.md"
PACKAGING: Final = "pyproject.toml"

VERSION_IN_PACKAGING = re.compile(r'^version = "([^"]+)"', re.MULTILINE)
RELEASE_HEADING = re.compile(r"^## +([0-9][0-9A-Za-z.\-]*)", re.MULTILINE)


def packaged_version() -> str | None:
    """The version the wheel would be built with."""
    text = (project_root() / PACKAGING).read_text(encoding="utf-8")
    found = VERSION_IN_PACKAGING.search(text)
    return found.group(1) if found else None


def releases() -> list[str]:
    """Every version the changelog has a section for, newest first."""
    path = project_root() / CHANGELOG
    if not path.exists():
        return []
    return RELEASE_HEADING.findall(path.read_text(encoding="utf-8"))


def problems() -> list[Problem]:
    """Everything that would make this a bad day to cut a release."""
    where = Path(project_root() / CHANGELOG)
    found = []
    packaged = packaged_version()
    if packaged is None:
        found.append(Problem(Path(project_root() / PACKAGING), 1, "the packaging has no version"))
    elif packaged != __version__:
        found.append(
            Problem(
                Path(project_root() / PACKAGING),
                1,
                f"the packaging says {packaged} and the package says {__version__}",
            )
        )
    sections = releases()
    if not sections:
        found.append(Problem(where, 1, "the changelog has no released version in it"))
    elif __version__ not in sections:
        found.append(Problem(where, 1, f"the changelog has nothing under {__version__}"))
    elif sections[0] != __version__:
        found.append(
            Problem(where, 1, f"the changelog's newest section is {sections[0]}, not {__version__}")
        )
    if not schema_is_current():
        found.append(Problem(where, 1, "the schema document is stale"))
    if not docs_are_current():
        found.append(Problem(where, 1, "the command reference is stale"))
    if not glossary_is_current():
        found.append(Problem(where, 1, "the glossary is stale"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "release")


if __name__ == "__main__":
    main()
