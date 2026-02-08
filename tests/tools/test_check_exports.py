"""The check that a subpackage exports what it has."""

from __future__ import annotations

import ast
from pathlib import Path

from spikemaul.tools.check_exports import declared, init_files, problems, problems_in


def test_every_export_list_in_this_package_agrees_with_its_file() -> None:
    assert [one.describe() for one in problems()] == []


def test_every_subpackage_has_an_init_file() -> None:
    names = {one.parent.name for one in init_files()}
    assert "units" in names
    assert "store" in names


def test_a_file_with_no_export_list_is_left_alone(tmp_path: Path) -> None:
    where = tmp_path / "__init__.py"
    where.write_text('"""A package."""\nfrom csv import reader\n', encoding="utf-8")
    assert declared(ast.parse(where.read_text())) is None
    assert problems_in(where) == []


def test_a_name_that_is_exported_and_not_there_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "__init__.py"
    where.write_text('"""A package."""\n\n__all__ = ["missing"]\n', encoding="utf-8")
    found = problems_in(where)
    assert "missing is exported and is not here" in found[0].says


def test_a_name_that_is_imported_and_not_exported_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "__init__.py"
    where.write_text(
        '"""A package."""\nfrom csv import reader, writer\n\n__all__ = ["reader"]\n',
        encoding="utf-8",
    )
    found = problems_in(where)
    assert any("writer is imported and is not exported" in one.says for one in found)


def test_the_order_of_the_list_is_left_to_ruff(tmp_path: Path) -> None:
    where = tmp_path / "__init__.py"
    where.write_text(
        '"""A package."""\nfrom csv import reader, writer\n\n__all__ = ["writer", "reader"]\n',
        encoding="utf-8",
    )
    assert problems_in(where) == []
