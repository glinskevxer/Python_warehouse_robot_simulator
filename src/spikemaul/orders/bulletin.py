"""The general track bulletin, which is what the crew is handed.

A bulletin is a list of restrictions in force on one subdivision on one day,
in milepost order, with the ones that come off by themselves separated from
the ones that stay until somebody takes them off. That separation is not
cosmetic. A crew reading a heat order needs to know it lapses tonight; a
dispatcher reading a standing order needs to know it will still be there in
October.

Nothing is computed here that a slow order does not already carry. The
bulletin sorts, splits and prints, and the reason it is its own module is that
the sorting is a decision worth having in one place: by milepost, then by
speed, so two orders starting at the same place print the slower one first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from spikemaul.model.ids import Ident
from spikemaul.model.order import SlowOrder
from spikemaul.units.span import Span, merge_all
from spikemaul.units.speed import Speed, slowest


@dataclass(frozen=True)
class Bulletin:
    """Everything in force on one subdivision on one day."""

    subdivision: Ident
    on: date
    standing: tuple[SlowOrder, ...]
    lapsing: tuple[SlowOrder, ...]

    @property
    def orders(self) -> tuple[SlowOrder, ...]:
        """Every order on the bulletin, standing ones first."""
        return self.standing + self.lapsing

    @property
    def is_clear(self) -> bool:
        """Whether the subdivision is running with nothing on it."""
        return not self.orders

    @property
    def restricted_miles(self) -> float:
        """Route miles under a restriction, counting overlap once."""
        return float(sum(one.miles for one in merge_all([one.span for one in self.orders])))

    def slowest_speed(self) -> Speed | None:
        """The lowest speed anywhere on the bulletin."""
        if not self.orders:
            return None
        return slowest([one.speed for one in self.orders])

    def covering(self, span: Span) -> list[SlowOrder]:
        """Orders on the bulletin that touch a stretch."""
        return [one for one in self.orders if one.span.overlaps(span)]

    def lines(self) -> list[str]:
        """The bulletin as the lines that get printed."""
        out = [f"{self.subdivision.tail} track bulletin {self.on.isoformat()}"]
        if self.is_clear:
            out.append("no restrictions in force")
            return out
        for order in self.standing:
            out.append(order.describe())
        for order in self.lapsing:
            out.append(f"{order.describe()} (lapses)")
        return out

    def describe(self) -> str:
        """One line summarising the bulletin, for the front of a report."""
        if self.is_clear:
            return f"{self.subdivision.tail} {self.on.isoformat()}, nothing in force"
        return (
            f"{self.subdivision.tail} {self.on.isoformat()}, {len(self.orders)} orders, "
            f"{self.restricted_miles} miles, slowest {self.slowest_speed()}"
        )


def _in_order(orders: list[SlowOrder]) -> tuple[SlowOrder, ...]:
    return tuple(
        sorted(orders, key=lambda one: (one.span.begin.hundredths, one.speed.mph, str(one.ident)))
    )


def build(subdivision: Ident, on: date, orders: list[SlowOrder]) -> Bulletin:
    """The bulletin for a subdivision on a day, out of the orders in the book."""
    in_force = [one for one in orders if one.subdivision == subdivision and one.in_effect_on(on)]
    standing = [one for one in in_force if not one.reason.comes_off_by_itself]
    lapsing = [one for one in in_force if one.reason.comes_off_by_itself]
    return Bulletin(
        subdivision=subdivision,
        on=on,
        standing=_in_order(standing),
        lapsing=_in_order(lapsing),
    )


def changes_between(first: Bulletin, second: Bulletin) -> tuple[list[SlowOrder], list[SlowOrder]]:
    """What went on and what came off between two bulletins.

    The first list is what is on the second bulletin and not the first, the
    second is the other way round, both in milepost order.
    """
    before = {one.ident for one in first.orders}
    after = {one.ident for one in second.orders}
    put_on = [one for one in second.orders if one.ident not in before]
    came_off = [one for one in first.orders if one.ident not in after]
    return list(_in_order(put_on)), list(_in_order(came_off))
