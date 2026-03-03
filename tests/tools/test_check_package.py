"""The check that the package ships what it has."""

from __future__ import annotations

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
