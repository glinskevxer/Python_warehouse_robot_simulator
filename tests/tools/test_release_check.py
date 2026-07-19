"""The check that this tree would ship."""

from __future__ import annotations

from pathlib import Path

import pytest

from spikemaul import __version__
from spikemaul.tools import release_check
from spikemaul.tools.release_check import packaged_version, problems, releases


def test_this_tree_would_ship_as_it_stands() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_packaging_and_the_package_agree_on_the_version() -> None:
    assert packaged_version() == __version__


def test_the_changelog_has_a_section_for_this_version() -> None:
    assert __version__ in releases()


def test_the_newest_section_is_the_version_being_shipped() -> None:
    assert releases()[0] == __version__


def test_an_unreleased_heading_is_not_read_as_a_version() -> None:
    assert "Unreleased" not in releases()


def a_tree(tmp_path: Path, version: str, sections: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "spikemaul"\nversion = "{version}"\n', encoding="utf-8"
    )
    (tmp_path / "CHANGELOG.md").write_text(f"# Changelog\n\n{sections}\n", encoding="utf-8")
    return tmp_path


def test_a_packaging_version_that_disagrees_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(release_check, "project_root", lambda: a_tree(tmp_path, "9.9.9", ""))
    monkeypatch.setattr(release_check, "schema_is_current", lambda: True)
    monkeypatch.setattr(release_check, "docs_are_current", lambda: True)
    monkeypatch.setattr(release_check, "glossary_is_current", lambda: True)
    found = [one.says for one in release_check.problems()]
    assert any("the packaging says 9.9.9" in one for one in found)


def test_a_changelog_with_nothing_in_it_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        release_check, "project_root", lambda: a_tree(tmp_path, __version__, "## Unreleased")
    )
    monkeypatch.setattr(release_check, "schema_is_current", lambda: True)
    monkeypatch.setattr(release_check, "docs_are_current", lambda: True)
    monkeypatch.setattr(release_check, "glossary_is_current", lambda: True)
    found = [one.says for one in release_check.problems()]
    assert any("no released version" in one for one in found)


def test_a_changelog_whose_newest_section_is_older_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sections = f"## 9.9.9\n\nsomething\n\n## {__version__}\n\nsomething\n"
    monkeypatch.setattr(
        release_check, "project_root", lambda: a_tree(tmp_path, __version__, sections)
    )
    monkeypatch.setattr(release_check, "schema_is_current", lambda: True)
    monkeypatch.setattr(release_check, "docs_are_current", lambda: True)
    monkeypatch.setattr(release_check, "glossary_is_current", lambda: True)
    found = [one.says for one in release_check.problems()]
    assert any("newest section is 9.9.9" in one for one in found)


def test_a_stale_document_stops_the_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sections = f"## {__version__}\n\nsomething\n"
    monkeypatch.setattr(
        release_check, "project_root", lambda: a_tree(tmp_path, __version__, sections)
    )
    monkeypatch.setattr(release_check, "schema_is_current", lambda: False)
    monkeypatch.setattr(release_check, "docs_are_current", lambda: False)
    monkeypatch.setattr(release_check, "glossary_is_current", lambda: False)
    found = [one.says for one in release_check.problems()]
    assert "the schema document is stale" in found
    assert "the command reference is stale" in found
    assert "the glossary is stale" in found


def test_packaging_with_no_version_at_all_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "spikemaul"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(f"## {__version__}\n\nsomething\n", encoding="utf-8")
    monkeypatch.setattr(release_check, "project_root", lambda: tmp_path)
    monkeypatch.setattr(release_check, "schema_is_current", lambda: True)
    monkeypatch.setattr(release_check, "docs_are_current", lambda: True)
    monkeypatch.setattr(release_check, "glossary_is_current", lambda: True)
    assert release_check.packaged_version() is None
    assert any("no version" in one.says for one in release_check.problems())
