"""Grade crossings and bridges, the two things on the railroad that other
departments and other agencies also have a file on.

A crossing carries an inventory number that is six digits and a check letter.
The letter is not decoration. Numbers get copied onto work orders, road
authority correspondence and signal prints by hand, and a wrong digit that
still checks out is the one that costs a day. The letter is the six digit
number modulo twenty two, read off an alphabet with the letters that look like
digits taken out, which is how the inventory here computes it.

A bridge carries a load rating rather than a class of track. The rating is in
Cooper E numbers, and a car heavier than the rating does not get a slow order,
it gets refused, which is the one place in this package where the answer to
too heavy is not a lower speed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from spikemaul.errors import InputError, RuleError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.milepost import Milepost
from spikemaul.units.speed import Speed

CHECK_ALPHABET: Final = "ABCDEFGHJKLMNPRSTUVWXY"
"""Twenty two letters, with the ones that read as digits left out."""


class Surface(Enum):
    """What the road runs on where it crosses the track."""

    TIMBER = "timber"
    RUBBER = "rubber"
    CONCRETE = "concrete"
    ASPHALT = "asphalt"

    @property
    def is_removable(self) -> bool:
        """Whether a tie gang can lift it and put it back the same day."""
        return self in {Surface.TIMBER, Surface.RUBBER, Surface.CONCRETE}


class WarningDevice(Enum):
    """What warns the road, in the order the inventory ranks it."""

    CROSSBUCKS = "crossbucks"
    FLASHERS = "flashers"
    GATES = "gates"

    @property
    def is_active(self) -> bool:
        """Whether it does something when a train comes."""
        return self is not WarningDevice.CROSSBUCKS


def check_letter(number: int) -> str:
    """The check letter for a six digit inventory number."""
    if not 0 <= number <= 999_999:
        raise InputError(f"{number} is not a six digit inventory number")
    return CHECK_ALPHABET[number % len(CHECK_ALPHABET)]


def parse_inventory(text: str) -> str:
    """Read an inventory number and refuse one whose check letter is wrong."""
    raw = text.strip().upper().replace(" ", "")
    if len(raw) != 7 or not raw[:6].isdigit():
        raise InputError(f"{text!r} is not an inventory number")
    wanted = check_letter(int(raw[:6]))
    if raw[6] != wanted:
        raise InputError(f"{text!r} does not check, {raw[:6]} ends {wanted}")
    return raw


@dataclass(frozen=True)
class Crossing:
    """A public or private road crossing the track at grade."""

    ident: Ident
    subdivision: Ident
    at: Milepost
    road: str
    inventory: str
    surface: Surface
    warning: WarningDevice
    public: bool = True

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.CROSSING:
            raise InputError(f"{self.ident} is not a crossing number")
        if not self.road.strip():
            raise InputError("a crossing carries the name of the road over it")
        object.__setattr__(self, "inventory", parse_inventory(self.inventory))
        if self.public and not self.warning.is_active and self.surface is Surface.TIMBER:
            raise RuleError(f"{self.ident} is a public crossing on timber with no active warning")

    def describe(self) -> str:
        """One line for the crossing list."""
        kind = "public" if self.public else "private"
        return (
            f"{self.ident} {self.subdivision.tail} MP {self.at} {self.road} "
            f"{self.inventory} {kind} {self.surface.value} {self.warning.value}"
        )


class Structure(Enum):
    """What kind of bridge it is, which decides who inspects it and how."""

    TIMBER_TRESTLE = "timber trestle"
    DECK_GIRDER = "deck girder"
    THROUGH_TRUSS = "through truss"
    BALLAST_DECK = "ballast deck"
    CULVERT = "culvert"

    @property
    def is_open_deck(self) -> bool:
        """Whether the ties sit straight on the steel or timber, with no ballast."""
        return self in {Structure.TIMBER_TRESTLE, Structure.DECK_GIRDER, Structure.THROUGH_TRUSS}


@dataclass(frozen=True)
class Bridge:
    """A structure carrying the track, with a load rating rather than a class."""

    ident: Ident
    subdivision: Ident
    at: Milepost
    kind: Structure
    spans: int
    length_feet: int
    normal_rating: int
    maximum_rating: int
    built: int

    def __post_init__(self) -> None:
        if self.ident.kind is not Kind.BRIDGE:
            raise InputError(f"{self.ident} is not a bridge number")
        if self.spans < 1 or self.length_feet < 1:
            raise InputError("a bridge has at least one span and some length to it")
        if self.maximum_rating < self.normal_rating:
            raise InputError("the maximum rating is not below the normal rating")
        if self.built < 1860 or self.built > 2100:
            raise InputError(f"{self.built} is not a year a bridge was built in")

    @property
    def average_span_feet(self) -> int:
        """Length divided by spans, which is what the inspector plans around."""
        return self.length_feet // self.spans

    def carries(self, load: int) -> bool:
        """Whether a car of that Cooper rating may cross at all."""
        return load <= self.maximum_rating

    def restricted_for(self, load: int, normal: Speed) -> Speed:
        """The speed a load crosses at, which is not always the timetable one.

        A load inside the normal rating crosses at track speed. A load above
        it but inside the maximum crosses at ten. A load above the maximum
        does not cross, and asking for a speed for it is a mistake.
        """
        if not self.carries(load):
            raise RuleError(
                f"{self.ident} is rated E {self.maximum_rating} and will not take {load}"
            )
        if load <= self.normal_rating:
            return normal
        return Speed(10).slower_of(normal)

    def describe(self) -> str:
        """One line for the structure list."""
        return (
            f"{self.ident} {self.subdivision.tail} MP {self.at} {self.kind.value} "
            f"{self.spans} spans {self.length_feet} ft E {self.normal_rating}/{self.maximum_rating}"
        )
