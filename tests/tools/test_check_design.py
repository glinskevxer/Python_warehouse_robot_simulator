"""The check that the design note names code that is there."""

from __future__ import annotations

from spikemaul.tools.check_design import modules, named_in, note, problems


def test_the_design_note_names_only_modules_that_are_here() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_note_names_more_than_a_handful_of_modules() -> None:
    named = named_in(note().read_text(encoding="utf-8"))
    assert len(named) > 5


def test_the_modules_are_the_package_dotted() -> None:
    assert "spikemaul.units.milepost" in modules()
    assert "spikemaul.units" in modules()


def test_a_path_in_backticks_is_what_the_note_is_read_for() -> None:
    assert named_in("see `spikemaul.units.span` for that") == ["spikemaul.units.span"]
    assert named_in("see the units package") == []
