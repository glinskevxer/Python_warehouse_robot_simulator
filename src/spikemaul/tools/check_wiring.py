"""Every public name is used by somebody.

A function nobody calls is read as working code. It is in the coverage report
if a test calls it, it is in the docs if the docs are generated, and it is
maintained by whoever next changes the thing it was written beside. The only
signal that it is dead is that nothing refers to it, and nothing checks that
by itself.

Tests count as a caller, and so does the module the name is defined in. A
helper called only by its own module is not dead, it is private with a public
name, and that is a different argument. What this catches is the name nothing
anywhere refers to.

Decorated functions are left alone. A click command is called by click, a
pytest fixture by pytest, and neither is referred to by name anywhere.
"""

from __future__ import annotations

import ast
from pathlib import Path

from spikemaul.tools.sources import (
    Problem,
    parsed,
    public_classes,
    public_functions,
    run,
    source_files,
    suite_files,
)


def defined_in(path: Path) -> list[tuple[str, int]]:
    """Every public name a file defines, with the line it is on."""
    tree = parsed(path)
    out = [(one.name, one.lineno) for one in public_functions(tree) if not one.decorator_list]
    out.extend((one.name, one.lineno) for one in public_classes(tree))
    return out


def names_used(path: Path) -> set[str]:
    """Every name a file refers to, however it refers to it."""
    used: set[str] = set()
    tree = parsed(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            used.update(one.name for one in node.names)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            used.update(node.value.split())
    return used


def problems() -> list[Problem]:
    """Every public name nothing refers to."""
    used: set[str] = set()
    for one in source_files() + suite_files():
        used |= names_used(one)
    found = []
    for path in source_files():
        for name, line in defined_in(path):
            if name not in used:
                found.append(Problem(path, line, f"{name} is not used by anything"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "wiring")


if __name__ == "__main__":
    main()
