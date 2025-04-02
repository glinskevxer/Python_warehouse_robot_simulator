"""Which side of the track something is on, and which way a curve turns.

Both questions are answered the same way and both are answered looking in the
direction the mileposts increase. That convention is the whole content of this
module. Written down once it is a fact everybody can check; written down twice
it is two facts that will disagree the first time somebody changes one.
"""

from __future__ import annotations

from enum import Enum

from spikemaul.errors import InputError


class Hand(Enum):
    """Left or right, looking in the direction the mileposts increase."""

    LEFT = "left"
    RIGHT = "right"

    @classmethod
    def parse(cls, text: str) -> Hand:
        """Read the hand off a chart or a card."""
        raw = text.strip().lower()
        if raw in {"l", "left"}:
            return cls.LEFT
        if raw in {"r", "right"}:
            return cls.RIGHT
        raise InputError(f"{text!r} is not a hand, expected left or right")

    @property
    def other(self) -> Hand:
        """The other side, which is what the low rail is on a curve."""
        return Hand.RIGHT if self is Hand.LEFT else Hand.LEFT

    @property
    def high_rail(self) -> Hand:
        """The rail that carries the elevation on a curve of this hand.

        A curve to the left is elevated on the right rail, because the right
        rail is the outside one.
        """
        return self.other

    def __str__(self) -> str:
        return self.value
