"""Every command says what it does, and every group is on the script.

Two things go wrong with a click program and both are silent. A command with
no docstring prints an empty line in the help, which reads as a command
nobody bothered to explain. And a group defined in a module but never added to
the top level group is a command that exists in the source and not on the
console script, which is a whole afternoon to find.

Options are checked too. An option with no help is a flag somebody has to read
the source to understand, and the source is not on the section house wall.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Final

from spikemaul.tools.sources import Problem, package_root, parsed, run, source_files

MAIN: Final = "cli/main.py"
"""Where the groups are added to the console script."""


def _decorator_names(node: ast.FunctionDef) -> list[str]:
    out = []
    for decorator in node.decorator_list:
        call = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(call, ast.Attribute):
            out.append(call.attr)
        elif isinstance(call, ast.Name):
            out.append(call.id)
    return out


def _option_calls(node: ast.FunctionDef) -> list[ast.Call]:
    return [
        one
        for one in node.decorator_list
        if isinstance(one, ast.Call)
        and isinstance(one.func, ast.Attribute)
        and one.func.attr == "option"
    ]


def commands_in(path: Path) -> list[ast.FunctionDef]:
    """Every click command or group defined in a file."""
    return [
        node
        for node in parsed(path).body
        if isinstance(node, ast.FunctionDef) and {"command", "group"} & set(_decorator_names(node))
    ]


def groups_in(path: Path) -> list[str]:
    """Every click group defined in a file."""
    return [node.name for node in commands_in(path) if "group" in _decorator_names(node)]


def registered() -> set[str]:
    """Every group the console script adds."""
    main = package_root() / "cli" / "main.py"
    out = set()
    for node in ast.walk(parsed(main)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_command"
            and node.args
            and isinstance(node.args[0], ast.Name)
        ):
            out.add(node.args[0].id)
    return out


def problems() -> list[Problem]:
    """Every command with no help, and every group not on the script."""
    found = []
    on_the_script = registered() | {"cli"}
    for path in source_files("cli"):
        for node in commands_in(path):
            if ast.get_docstring(node) is None:
                found.append(Problem(path, node.lineno, f"{node.name} has no help"))
            for option in _option_calls(node):
                named = {one.arg for one in option.keywords}
                if "help" not in named and "is_eager" not in named:
                    flag = option.args[0] if option.args else None
                    spelled = flag.value if isinstance(flag, ast.Constant) else "an option"
                    found.append(
                        Problem(path, option.lineno, f"{spelled} on {node.name} has no help")
                    )
        if path.name == "main.py":
            continue
        for group in groups_in(path):
            if group not in on_the_script:
                found.append(Problem(path, 1, f"{group} is not added to the console script"))
    return found


def main() -> None:
    """Run the check and exit."""
    run(problems(), "help")


if __name__ == "__main__":
    main()
