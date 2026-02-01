"""The check that every module has a test file with its name on it."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_tests import CROSS_CUTTING, mirrored, problems, wanted_name


def test_every_module_in_this_package_has_a_test_file() -> None:
    assert [one.describe() for one in problems()] == []


def test_no_test_file_is_left_behind_by_a_module_that_went_away() -> None:
    assert [one.describe() for one in mirrored()] == []


def test_the_wanted_name_is_the_module_with_a_prefix() -> None:
    assert wanted_name(Path("src/spikemaul/units/milepost.py")) == "test_milepost.py"


def test_a_cross_cutting_test_file_says_why_it_is_one() -> None:
    assert CROSS_CUTTING
    for name, reason in CROSS_CUTTING.items():
        assert name.startswith("test_")
        assert len(reason.split()) > 4
