"""The check that every command explains itself."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_help import commands_in, groups_in, problems, registered
from spikemaul.tools.sources import package_root


def test_every_command_on_this_script_has_help() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_groups_defined_are_the_groups_registered() -> None:
    defined = set()
    for path in package_root().glob("cli/*.py"):
        if path.name == "main.py":
            continue
        defined |= set(groups_in(path))
    assert defined <= registered()


def test_a_command_with_no_help_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nimport click\n\n\n@click.group()\ndef thing() -> None:\n    pass\n',
        encoding="utf-8",
    )
    assert [one.name for one in commands_in(where)] == ["thing"]
    assert groups_in(where) == ["thing"]


def test_the_console_script_registers_more_than_one_group() -> None:
    assert len(registered()) > 5
