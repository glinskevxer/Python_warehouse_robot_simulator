"""Finding and reading this package's own source, for the checks to work on.

Everything here is about the tree rather than about the railroad. The one
decision worth stating is that the checks read the files rather than importing
them: a check that imports the package to look at it cannot report a module
that fails to import, which is exactly the module worth reporting.
"""

from __future__ import annotations

import ast
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

PACKAGE = "spikemaul"


def package_root() -> Path:
    """The directory the package's source is in."""
    return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    """The checkout the package was installed from, or the one beside it."""
    return package_root().parent.parent


def source_files(subpackage: str | None = None) -> list[Path]:
    """Every python file in the package, in path order."""
    root = package_root() if subpackage is None else package_root() / subpackage
    return sorted(one for one in root.rglob("*.py") if "__pycache__" not in one.parts)


def suite_files() -> list[Path]:
    """Every python file in the test suite, in path order."""
    tests = project_root() / "tests"
    if not tests.exists():
        return []
    return sorted(one for one in tests.rglob("*.py") if "__pycache__" not in one.parts)


def module_name(path: Path) -> str:
    """The dotted name of a source file, as it is imported."""
    relative = path.relative_to(package_root().parent)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def parsed(path: Path) -> ast.Module:
    """The file as a syntax tree."""
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def public_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    """Every top level function whose name does not start with an underscore."""
    return [
        one
        for one in tree.body
        if isinstance(one, ast.FunctionDef) and not one.name.startswith("_")
    ]


def public_classes(tree: ast.Module) -> list[ast.ClassDef]:
    """Every top level class whose name does not start with an underscore."""
    return [
        one for one in tree.body if isinstance(one, ast.ClassDef) and not one.name.startswith("_")
    ]


def methods_of(node: ast.ClassDef) -> list[ast.FunctionDef]:
    """Every method on a class whose name does not start with an underscore."""
    return [
        one
        for one in node.body
        if isinstance(one, ast.FunctionDef) and not one.name.startswith("_")
    ]


def imported_modules(tree: ast.Module) -> list[str]:
    """Every module this file imports, dotted."""
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(one.name for one in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.append(node.module)
    return out


@dataclass(frozen=True)
class Problem:
    """One thing a check found, and where."""

    where: Path
    line: int
    says: str

    def describe(self, root: Path | None = None) -> str:
        """One line, with the path relative to the checkout where it can be."""
        where = self.where
        if root is not None:
            with suppress(ValueError):
                where = self.where.relative_to(root)
        return f"{where}:{self.line} {self.says}"


def report(problems: list[Problem], checking: str) -> int:
    """Print what a check found and give back the exit status."""
    root = project_root()
    if not problems:
        print(f"{checking}: nothing to report")
        return 0
    for problem in problems:
        print(problem.describe(root))
    print(f"{checking}: {len(problems)} to fix")
    return 1


def run(problems: list[Problem], checking: str) -> None:
    """Print what a check found and exit."""
    sys.exit(report(problems, checking))
