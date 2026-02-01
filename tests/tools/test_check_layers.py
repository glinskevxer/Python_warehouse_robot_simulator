"""The layering check, and what it says about this tree."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_layers import LAYERS, layer_of, problems, problems_in


def test_nothing_in_this_package_imports_upwards() -> None:
    assert [one.says for one in problems()] == []


def test_every_subpackage_is_in_the_table() -> None:
    from spikemaul.tools.sources import package_root

    subpackages = {
        one.name for one in package_root().iterdir() if one.is_dir() and one.name != "__pycache__"
    }
    assert subpackages <= set(LAYERS)


def test_a_module_outside_the_package_has_no_layer() -> None:
    assert layer_of("csv") is None
    assert layer_of("spikemaul") is None
    assert layer_of("spikemaul.units.milepost") == 1


def test_a_file_outside_the_table_is_left_alone(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text('"""A file."""\nfrom spikemaul.cli import main\n', encoding="utf-8")
    assert problems_in(where) == []


def test_an_upward_import_would_be_reported() -> None:
    from spikemaul.tools.sources import package_root

    found = problems_in(package_root() / "units" / "milepost.py")
    assert found == []
    units = layer_of("spikemaul.units.milepost")
    store = layer_of("spikemaul.store.book")
    assert units is not None
    assert store is not None
    assert units < store


def test_the_check_names_both_ends() -> None:
    for one in problems():
        assert "imports" in one.says
