"""The one call to the system clock."""

from __future__ import annotations

from datetime import date

from spikemaul.cli.clock import today


def test_the_clock_gives_back_a_day() -> None:
    assert isinstance(today(), date)


def test_the_day_it_gives_back_is_not_in_the_last_century() -> None:
    assert today().year >= 2024
