"""The check that only identifiers are interpolated into statements."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_sql import IDENTIFIERS, problems, problems_in


def test_this_package_interpolates_only_identifiers() -> None:
    assert [one.describe() for one in problems()] == []


def test_a_value_interpolated_into_a_statement_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\n\n\ndef read(book: object, ident: str) -> None:\n'
        '    book.execute(f"SELECT * FROM segments WHERE ident = {ident}")\n',
        encoding="utf-8",
    )
    found = problems_in(where)
    assert "ident is interpolated" in found[0].says


def test_a_statement_built_with_an_operator_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\n\n\ndef read(book: object, ident: str) -> None:\n'
        '    book.execute("SELECT * FROM segments WHERE ident = " + ident)\n',
        encoding="utf-8",
    )
    assert "built with an operator" in problems_in(where)[0].says


def test_a_known_identifier_is_allowed(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\n\nCOLUMNS = "ident, name"\n\n\ndef read(book: object) -> None:\n'
        '    book.query(f"SELECT {COLUMNS} FROM segments")\n',
        encoding="utf-8",
    )
    assert problems_in(where) == []


def test_the_list_of_identifiers_is_short_enough_to_read() -> None:
    assert len(IDENTIFIERS) < 20
    assert "table" in IDENTIFIERS
