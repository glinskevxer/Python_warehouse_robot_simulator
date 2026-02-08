"""The check that every public name is used somewhere."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_wiring import defined_in, names_used, problems


def test_every_public_name_in_this_package_is_used() -> None:
    assert [one.describe() for one in problems()] == []


def test_a_name_nothing_refers_to_would_be_reported() -> None:
    for one in problems():
        assert "is not used by anything" in one.says


def test_the_public_names_of_a_file_are_read_off_it(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\n\n\ndef public() -> None:\n    """Does."""\n\n\n'
        'def _private() -> None:\n    """Does."""\n\n\n'
        'class Thing:\n    """A thing."""\n',
        encoding="utf-8",
    )
    assert [name for name, _ in defined_in(where)] == ["public", "Thing"]


def test_a_decorated_function_is_left_alone(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nimport click\n\n\n@click.command()\ndef run() -> None:\n    """Does."""\n',
        encoding="utf-8",
    )
    assert [name for name, _ in defined_in(where)] == []


def test_the_names_a_file_refers_to_include_attributes(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nimport csv\n\n\ndef read() -> None:\n    csv.DictReader("x")\n',
        encoding="utf-8",
    )
    used = names_used(where)
    assert "csv" in used
    assert "DictReader" in used
