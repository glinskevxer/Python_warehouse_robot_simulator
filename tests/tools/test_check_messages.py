"""The check on how the messages read."""

from __future__ import annotations

from pathlib import Path

from spikemaul.tools.check_messages import problems, problems_in


def test_every_message_in_this_package_reads_like_a_sentence() -> None:
    assert [one.describe() for one in problems()] == []


def test_a_message_that_starts_in_upper_case_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nfrom spikemaul.errors import InputError\n\n\n'
        'def check() -> None:\n    raise InputError("Milepost is wrong")\n',
        encoding="utf-8",
    )
    assert "starts in upper case" in problems_in(where)[0].says


def test_a_message_that_ends_in_a_full_stop_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nfrom spikemaul.errors import InputError\n\n\n'
        'def check() -> None:\n    raise InputError("that is not a milepost.")\n',
        encoding="utf-8",
    )
    assert "ends in a full stop" in problems_in(where)[0].says


def test_a_message_that_shouts_is_reported(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nfrom spikemaul.errors import InputError\n\n\n'
        'def check() -> None:\n    raise InputError("stop that!")\n',
        encoding="utf-8",
    )
    assert "shouts" in problems_in(where)[0].says


def test_a_message_starting_with_a_value_is_left_alone(tmp_path: Path) -> None:
    where = tmp_path / "sample.py"
    where.write_text(
        '"""A file."""\nfrom spikemaul.errors import InputError\n\n\n'
        'def check(text: str) -> None:\n    raise InputError(f"{text!r} is not a milepost")\n',
        encoding="utf-8",
    )
    assert problems_in(where) == []
