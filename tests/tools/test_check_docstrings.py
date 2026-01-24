"""The docstring check, and what it says about this tree."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_docstrings import problems, problems_in


def test_this_package_says_what_everything_is_for() -> None:
    assert [one.describe() for one in problems()] == []


def test_a_module_with_no_docstring_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text('def thing() -> None:\n    """Does."""\n', encoding="utf-8")
    found = problems_in(where)
    assert len(found) == 1
    assert "module sample has no docstring" in found[0].says


def test_a_public_function_with_no_docstring_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text('"""A file."""\n\n\ndef thing() -> None:\n    pass\n', encoding="utf-8")
    found = problems_in(where)
    assert "function thing" in found[0].says


def test_a_private_function_is_not_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text('"""A file."""\n\n\ndef _thing() -> None:\n    pass\n', encoding="utf-8")
    assert problems_in(where) == []


def test_a_class_and_its_methods_are_both_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\n\n\nclass Thing:\n    def method(self) -> None:\n        pass\n',
        encoding="utf-8",
    )
    found = [one.says for one in problems_in(where)]
    assert "class Thing has no docstring" in found
    assert "method Thing.method has no docstring" in found


def test_a_private_method_is_not_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\n\n\nclass Thing:\n    """A thing."""\n\n'
        "    def _method(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    assert problems_in(where) == []
