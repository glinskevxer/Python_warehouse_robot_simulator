"""Raising and lowering the class a segment is held to.

Lowering is always allowed. It is more restrictive than what is there, the
speed goes down, and every limit the track is judged against gets looser, so
nothing that was legal becomes illegal.

Raising is the one with a rule on it. Every open defect card on the segment is
a condition that has already been measured, and a card that meets class one is
still a card that meets class one after somebody types class four into a
terminal. So a segment cannot be raised past what its open cards support, and
the refusal names the cards rather than saying no.

The rule is here rather than in the register because it is a rule, and because
the register would have to know what a defect card is to enforce it.
"""

from __future__ import annotations

from dataclasses import replace

from spikemaul.errors import RuleError
from spikemaul.model.defect import Defect
from spikemaul.model.line import Segment
from spikemaul.standards.classes import ClassOfTrack


def cards_on(segment: Segment, cards: list[Defect]) -> list[Defect]:
    """The open cards that sit on a segment."""
    return [
        one
        for one in cards
        if one.is_open and one.subdivision == segment.subdivision and segment.holds(one.at)
    ]


def supported_by_cards(segment: Segment, cards: list[Defect]) -> ClassOfTrack | None:
    """The highest class the open cards on a segment leave it, or nothing."""
    open_cards = cards_on(segment, cards)
    if not open_cards:
        return ClassOfTrack.FIVE
    if any(one.meets is None for one in open_cards):
        return None
    return min(one.meets for one in open_cards if one.meets is not None)


def reasons_against(segment: Segment, to: ClassOfTrack, cards: list[Defect]) -> list[str]:
    """Why a segment cannot be held to a higher class today."""
    if to <= segment.authorized:
        return []
    return [
        f"{one.ident} {one.condition.value} {one.reading} meets "
        f"{'nothing' if one.meets is None else one.meets}"
        for one in cards_on(segment, cards)
        if one.meets is None or one.meets < to
    ]


def held_to(segment: Segment, to: ClassOfTrack, cards: list[Defect]) -> Segment:
    """The segment held to another class, refusing a raise the cards do not allow."""
    if to == segment.authorized:
        raise RuleError(f"{segment.ident} is already held at {to}")
    against = reasons_against(segment, to, cards)
    if against:
        named = "; ".join(against)
        raise RuleError(f"{segment.ident} cannot be raised to {to} with {named}")
    if to.is_excepted and segment.kind.is_main:
        raise RuleError("main track is not carried as excepted here")
    return replace(segment, authorized=to)


def would_change(segment: Segment, to: ClassOfTrack) -> str:
    """One line saying what the change does to the speed."""
    was = segment.authorized.speed()
    now = to.speed()
    if now == was:
        return f"{segment.ident} stays at {was}"
    direction = "up" if now > was else "down"
    return f"{segment.ident} goes {direction} from {was} to {now}"
