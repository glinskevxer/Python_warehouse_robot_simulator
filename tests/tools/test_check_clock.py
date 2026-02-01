"""The clock check."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_clock import ALLOWED, problems, problems_in


def test_only_one_module_asks_what_day_it_is() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_one_place_allowed_is_the_command_line_clock() -> None:
    assert ALLOWED == "spikemaul.cli.clock"


def test_a_call_to_the_clock_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nfrom datetime import date\n\n\n'
        "def when() -> date:\n    return date.today()\n",
        encoding="utf-8",
    )
    found = problems_in(where)
    assert len(found) == 1
    assert "date.today is only called in" in found[0].says


def test_a_call_inside_a_function_nobody_runs_is_still_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nimport time\n\n\n'
        "def never() -> None:\n    if False:\n        time.time()\n",
        encoding="utf-8",
    )
    assert problems_in(where) != []


def test_a_file_that_does_not_ask_is_left_alone(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nfrom datetime import date\n\n\n'
        "def when(on: date) -> date:\n    return on\n",
        encoding="utf-8",
    )
    assert problems_in(where) == []
