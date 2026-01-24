"""Every module, public class, public function and public method says what it
is for.

The rule is narrow on purpose. It does not ask for a particular style, it does
not check the wording, and it says nothing about private helpers. It asks that
anything somebody outside the file can call has a sentence attached, because a
name and a signature do not say why something exists and the reason is what
gets lost.
"""

from __future__ import annotations

import ast
from pathlib import Path

from spikemaul.tools.sources import (
    Problem,
    methods_of,
    parsed,
    public_classes,
    public_functions,
    run,
    source_files,
)


def _missing(node: ast.AST, path: Path, what: str, name: str) -> Problem | None:
    if ast.get_docstring(node) is not None:  # type: ignore[arg-type]
        return None
    line = getattr(node, "lineno", 1)
    return Problem(path, line, f"{what} {name} has no docstring")


def problems_in(path: Path) -> list[Problem]:
    """What one file is missing."""
    tree = parsed(path)
    found: list[Problem] = []
    module = _missing(tree, path, "module", path.stem)
    if module is not None:
        found.append(module)
    for function in public_functions(tree):
        one = _missing(function, path, "function", function.name)
        if one is not None:
            found.append(one)
    for klass in public_classes(tree):
        one = _missing(klass, path, "class", klass.name)
        if one is not None:
            found.append(one)
        for method in methods_of(klass):
            other = _missing(method, path, "method", f"{klass.name}.{method.name}")
            if other is not None:
                found.append(other)
    return found


def problems() -> list[Problem]:
    """Everything in the package that does not say what it is for."""
    found: list[Problem] = []
    for path in source_files():
        found.extend(problems_in(path))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "docstrings")


if __name__ == "__main__":
    main()
