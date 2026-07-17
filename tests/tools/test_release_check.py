"""The check that this tree would ship."""

from __future__ import annotations

from spikemaul import __version__
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
