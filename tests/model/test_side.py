"""Which side, answered once and looking the same way every time."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.model.side import Hand


def test_a_hand_reads_off_a_chart_or_a_card() -> None:
    assert Hand.parse("left") == Hand.LEFT
    assert Hand.parse(" RIGHT ") == Hand.RIGHT
    assert Hand.parse("l") == Hand.LEFT
    assert Hand.parse("R") == Hand.RIGHT


@pytest.mark.parametrize("text", ["", "west", "north", "lefty", "1"])
def test_anything_that_is_not_a_side_is_refused(text: str) -> None:
    with pytest.raises(InputError, match="is not a hand"):
        Hand.parse(text)


def test_the_other_side_is_the_other_side() -> None:
    assert Hand.LEFT.other == Hand.RIGHT
    assert Hand.RIGHT.other == Hand.LEFT
    assert Hand.LEFT.other.other == Hand.LEFT


def test_a_curve_is_elevated_on_the_outside_rail() -> None:
    assert Hand.LEFT.high_rail == Hand.RIGHT
    assert Hand.RIGHT.high_rail == Hand.LEFT


def test_a_hand_prints_as_the_word() -> None:
    assert str(Hand.LEFT) == "left"
    assert f"{Hand.RIGHT} hand" == "right hand"
