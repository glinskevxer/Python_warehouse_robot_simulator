"""The check that the package ships what it has."""

from __future__ import annotations

from pathlib import Path

import pytest

from spikemaul.tools import check_package
from spikemaul.tools.check_package import directories, problems


def test_every_directory_in_this_package_would_ship() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_directories_are_the_subpackages() -> None:
    names = {one.name for one in directories()}
    assert "units" in names
    assert "store" in names
    assert "__pycache__" not in names


def test_every_directory_has_an_init_file() -> None:
    for one in directories():
        assert (one / "__init__.py").exists()


def test_a_directory_with_no_init_file_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "orphan").mkdir()
    (tmp_path / "__init__.py").write_text('"""A package."""\n', encoding="utf-8")
    monkeypatch.setattr(check_package, "package_root", lambda: tmp_path)
    monkeypatch.setattr(check_package, "project_root", lambda: tmp_path)
    monkeypatch.setattr(check_package, "source_files", lambda: [tmp_path / "__init__.py"])
    found = [one.says for one in check_package.problems()]
    assert any("has no init file" in one for one in found)


def test_packaging_that_does_not_name_the_package_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "__init__.py").write_text('"""A package."""\n', encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.setattr(check_package, "package_root", lambda: tmp_path)
    monkeypatch.setattr(check_package, "project_root", lambda: tmp_path)
    monkeypatch.setattr(check_package, "source_files", lambda: [tmp_path / "__init__.py"])
    found = [one.says for one in check_package.problems()]
    assert any("does not name the package" in one for one in found)
