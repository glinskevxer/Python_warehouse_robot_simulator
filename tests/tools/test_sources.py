"""Finding and reading the package's own source."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.sources import (
    Problem,
    imported_modules,
    methods_of,
    module_name,
    package_root,
    parsed,
    project_root,
    public_classes,
    public_functions,
    report,
    source_files,
    suite_files,
)


def test_the_package_root_is_the_installed_source() -> None:
    assert package_root().name == "spikemaul"
    assert (package_root() / "units" / "milepost.py").exists()


def test_the_project_root_holds_the_tests() -> None:
    assert (project_root() / "tests").exists()


def test_every_source_file_is_found_and_no_cache_files_are() -> None:
    found = source_files()
    assert any(one.name == "milepost.py" for one in found)
    assert all("__pycache__" not in one.parts for one in found)


def test_a_subpackage_can_be_asked_for_on_its_own() -> None:
    found = source_files("units")
    assert all("units" in one.parts for one in found)
    assert len(found) < len(source_files())


def test_the_test_files_are_found() -> None:
    assert any(one.name == "test_sources.py" for one in suite_files())


def test_a_file_says_the_name_it_is_imported_as() -> None:
    assert module_name(package_root() / "units" / "milepost.py") == "spikemaul.units.milepost"
    assert module_name(package_root() / "units" / "__init__.py") == "spikemaul.units"


def test_the_public_names_of_a_file_are_read_off_it(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\n\n\n'
        "def public() -> None:\n    pass\n\n\n"
        "def _private() -> None:\n    pass\n\n\n"
        "class Thing:\n    def method(self) -> None:\n        pass\n\n"
        "    def _hidden(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    tree = parsed(where)
    assert [one.name for one in public_functions(tree)] == ["public"]
    assert [one.name for one in public_classes(tree)] == ["Thing"]
    assert [one.name for one in methods_of(public_classes(tree)[0])] == ["method"]


def test_the_imports_of_a_file_are_read_off_it(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nimport csv\nfrom pathlib import Path\nfrom . import thing\n',
        encoding="utf-8",
    )
    assert imported_modules(parsed(where)) == ["csv", "pathlib"]


def test_a_problem_prints_relative_to_the_checkout() -> None:
    problem = Problem(package_root() / "units" / "milepost.py", 12, "something")
    assert problem.describe(project_root()).startswith("src/spikemaul/units/milepost.py:12")
    assert "something" in problem.describe()


def test_a_check_with_nothing_to_report_gives_zero(capsys: object) -> None:
    assert report([], "sample") == 0


def test_a_check_with_something_to_report_gives_one() -> None:
    problem = Problem(package_root() / "units" / "milepost.py", 1, "wrong")
    assert report([problem], "sample") == 1
