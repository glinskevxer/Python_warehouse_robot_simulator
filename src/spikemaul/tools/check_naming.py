"""A test name says what is true, not that something works.

``test_gauge_works`` tells a reader nothing when it fails at two in the
morning. ``test_a_gauge_reading_that_meets_nothing_is_not_excepted_track``
tells them what was supposed to be true and therefore what to look at. So the
rule is a length, in words, and a short list of words that carry no
information.

The vague list is shorter than it looks, and one absence is deliberate. Good
is not on it. A good tie is the term the rule book uses for a tie that is not
defective, and a check that refuses it makes the tie tests worse.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from spikemaul.tools.sources import Problem, parsed, run, suite_files

LEAST_WORDS: Final = 5
"""How many words a test name carries before it says anything."""

VAGUE: Final[frozenset[str]] = frozenset(
    {
        "works",
        "correct",
        "correctly",
        "ok",
        "okay",
        "fine",
        "stuff",
        "things",
        "handles",
        "properly",
        "basic",
        "simple",
        "misc",
    }
)
"""Words that describe nothing. Good is not here, and that is on purpose."""


def words_of(name: str) -> list[str]:
    """The words in a test name, with the test prefix taken off."""
    return [one for one in name.removeprefix("test_").split("_") if one]


def problems_in(path: Path) -> list[Problem]:
    """Every thin test name in one file."""
    found = []
    for node in ast.walk(parsed(path)):
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
            continue
        words = words_of(node.name)
        if len(words) < LEAST_WORDS:
            found.append(
                Problem(
                    path,
                    node.lineno,
                    f"{node.name} is {len(words)} words, which does not say much",
                )
            )
        vague = sorted(set(words) & VAGUE)
        if vague:
            found.append(
                Problem(path, node.lineno, f"{node.name} says {vague[0]}, which says nothing")
            )
    return found


def problems() -> list[Problem]:
    """Every thin test name in the suite."""
    found: list[Problem] = []
    for path in suite_files():
        found.extend(problems_in(path))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "naming")


if __name__ == "__main__":
    main()
