"""Everything under tools is run by CI, and the walk runs commands that exist.

A check nobody runs is a check that does not exist. Writing one and forgetting
the line in the workflow is easy, and the failure is silent for exactly as
long as it matters: the check passes locally when somebody remembers, and the
build is green either way.

So the workflow is read as text and every check module in the package has to
appear in it. The workflow is yaml and this does not parse it, because the
question is whether a string is in the file and a parser is a dependency to
answer that.

The walk job is the other half. It is a shell script inside yaml, so nothing
compiles it and nothing type checks it, and a command renamed in the package
leaves a line in there that fails ten minutes into a build. Every command the
walk calls is looked up in the click tree, which is the same tree the script
is built from.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from spikemaul.cli.main import cli
from spikemaul.tools.sources import Problem, package_root, project_root, run

WORKFLOW: Final = ".github/workflows/ci.yml"

GENERATED: Final[frozenset[str]] = frozenset({"schema_dump", "build_docs", "build_glossary"})
"""Tools that CI runs with an argument rather than on their own."""

NOT_RUN: Final[frozenset[str]] = frozenset({"sources", "coverage_gate", "smoke"})
"""Tools that are not checks: a library, a gate with arguments, and a walk."""

PYTHONS: Final[tuple[str, ...]] = ("3.12", "3.13")
"""The interpreters the tests are run on. The second one is not decoration:
unclosed sqlite connections are a warning on 3.13 and silence on 3.12."""


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


def walk_lines() -> list[str]:
    """The lines of the walk job's shell script, joined where they continue."""
    path = workflow()
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    marker = "run: |\n"
    out: list[str] = []
    for block in text.split(marker)[1:]:
        joined = ""
        for line in block.splitlines():
            if line and not line.startswith("          "):
                break
            stripped = line.strip()
            if stripped.endswith("\\"):
                joined += stripped[:-1] + " "
                continue
            out.append((joined + stripped).strip())
            joined = ""
    return [one for one in out if one.startswith("spikemaul ")]


def walk_commands() -> list[list[str]]:
    """The command each walk line calls, as the words click would match."""
    out = []
    for line in walk_lines():
        words = []
        skip = False
        for word in line.split()[1:]:
            if skip:
                skip = False
                continue
            if word.startswith("--"):
                skip = "=" not in word
                continue
            if word.startswith(('"', "$", "/")):
                break
            words.append(word)
        if words:
            out.append(words)
    return out


def _known(words: list[str]) -> bool:
    command: object = cli
    for word in words:
        commands = getattr(command, "commands", None)
        if commands is None:
            return True
        if word not in commands:
            return False
        command = commands[word]
    return True


def walk_problems() -> list[Problem]:
    """Every command the walk calls that the console script does not have."""
    path = workflow()
    found = []
    for words in walk_commands():
        if not _known(words):
            found.append(
                Problem(path, 1, f"the walk calls {' '.join(words)}, which is not a command")
            )
    return found


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
    for version in PYTHONS:
        if f'"{version}"' not in text:
            found.append(Problem(path, 1, f"the workflow does not run the tests on {version}"))
    return found + walk_problems()


def main() -> None:
    """Run the check and exit."""
    run(problems(), "workflow")


if __name__ == "__main__":
    main()
