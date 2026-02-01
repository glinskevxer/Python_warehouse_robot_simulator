"""Every module has a test file with its name on it.

This is a weak check and it is worth having anyway. It does not ask whether
the tests are any good, whether they cover anything, or whether they assert
more than that the code runs. It asks that somebody opened a file called
``test_thing.py`` when they wrote ``thing.py``, which is the smallest possible
statement that the module was thought about from outside.

A module tested only through something else is the shape this catches. That is
not always wrong, and where it is deliberate the fix is a small file that says
so out loud rather than an exception in this list.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from spikemaul.tools.sources import (
    Problem,
    package_root,
    project_root,
    run,
    source_files,
    suite_files,
)

CROSS_CUTTING: Final[dict[str, str]] = {
    "test_persistence.py": (
        "reads the book back through a second connection, which is not one module's job"
    ),
}
"""Test files that deliberately do not mirror a module, and why."""


def wanted_name(path: Path) -> str:
    """The test file a module is expected to have."""
    return f"test_{path.stem}.py"


def problems() -> list[Problem]:
    """Every module with no test file named after it."""
    have = {one.name for one in suite_files()}
    found = []
    for path in source_files():
        if path.name == "__init__.py":
            continue
        if wanted_name(path) not in have:
            found.append(
                Problem(
                    path,
                    1,
                    f"there is no {wanted_name(path)} anywhere in {project_root().name}/tests",
                )
            )
    return found


def mirrored() -> list[Problem]:
    """Test files whose module is not there any more."""
    modules = {one.stem for one in source_files()}
    found = []
    for path in suite_files():
        if not path.name.startswith("test_"):
            continue
        if path.name in CROSS_CUTTING:
            continue
        stem = path.stem.removeprefix("test_")
        if stem not in modules and stem != package_root().name:
            found.append(Problem(path, 1, f"{path.name} tests a module that is not here"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems() + mirrored(), "tests")


if __name__ == "__main__":
    main()
