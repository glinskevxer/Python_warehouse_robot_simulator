"""What a subpackage says it exports is what it has.

Every subpackage's ``__init__`` names a few things in ``__all__``, and those
names are what the rest of the package is supposed to reach for. Two things go
wrong with that list and neither is visible in a review: a name in it that no
longer exists, which is an import error waiting for the first person to use
the documented spelling, and a name imported into the file but left out of the
list, which ruff reports as unused and somebody then deletes.

The order of the list is not checked here. Ruff already has an opinion about
it and two checks with different opinions about the same line is a fight
somebody has to referee every time either one changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from spikemaul.tools.sources import Problem, package_root, parsed, run


def init_files() -> list[Path]:
    """Every subpackage's init file."""
    return sorted(
        one for one in package_root().rglob("__init__.py") if "__pycache__" not in one.parts
    )


def declared(tree: ast.Module) -> list[str] | None:
    """The names in ``__all__``, or nothing where there is no list."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            named = isinstance(target, ast.Name) and target.id == "__all__"
            if named and isinstance(node.value, ast.List):
                return [
                    one.value
                    for one in node.value.elts
                    if isinstance(one, ast.Constant) and isinstance(one.value, str)
                ]
    return None


def imported_names(tree: ast.Module) -> list[str]:
    """Every name the init file imports."""
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            out.extend(one.asname or one.name for one in node.names)
    return out


def problems_in(path: Path) -> list[Problem]:
    """What one init file says that it does not have."""
    tree = parsed(path)
    names = declared(tree)
    if names is None:
        return []
    imported = imported_names(tree)
    defined = {one.name for one in tree.body if isinstance(one, ast.FunctionDef | ast.ClassDef)}
    assigned = {
        target.id
        for one in tree.body
        if isinstance(one, ast.Assign)
        for target in one.targets
        if isinstance(target, ast.Name)
    }
    have = set(imported) | defined | assigned
    found = []
    for name in names:
        if name not in have:
            found.append(Problem(path, 1, f"{name} is exported and is not here"))
    for name in imported:
        if name not in names:
            found.append(Problem(path, 1, f"{name} is imported and is not exported"))
    return found


def problems() -> list[Problem]:
    """Every export list that disagrees with its file."""
    found: list[Problem] = []
    for path in init_files():
        found.extend(problems_in(path))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "exports")


if __name__ == "__main__":
    main()
