"""The package ships everything it has.

A subdirectory with no init file is not a subpackage. It works in a checkout,
because the directory is right there on the path, and it is missing from the
wheel, so the first person to install the package finds an import error that
nobody could reproduce. The same goes for a subpackage that exists and is
never imported by anything: it ships, and it is dead weight.

This is a two line check that has caught a real one, which is the only reason
it is here.
"""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.sources import Problem, package_root, project_root, run, source_files


def directories() -> list[Path]:
    """Every directory inside the package."""
    return sorted(
        one for one in package_root().rglob("*") if one.is_dir() and one.name != "__pycache__"
    )


def problems() -> list[Problem]:
    """Every directory that would not ship, and every packaging line that lies."""
    found = []
    for one in directories():
        if not (one / "__init__.py").exists():
            found.append(Problem(one, 1, f"{one.name} has no init file, so it will not ship"))
    if not any(path.name == "__init__.py" for path in source_files()):
        found.append(Problem(package_root(), 1, "the package itself has no init file"))
    pyproject = project_root() / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        if f'packages = ["src/{package_root().name}"]' not in text:
            found.append(Problem(pyproject, 1, "the wheel does not name the package it builds"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "package")


if __name__ == "__main__":
    main()
