"""Everything the book knows about one milepost.

The question the roadmaster is asked on the telephone, in this order: what is
the track here, what is on it, what is wrong with it and how fast can they go.
Answering it out of six commands is why people keep their own notebooks.

Nothing here is computed that another module does not already compute. The
page exists because the answer is spread across nine registers and a rule, and
looking it up nine times is where the mistake gets made.
"""

from __future__ import annotations

from datetime import date

from spikemaul.errors import NotFoundError
from spikemaul.model.ids import Ident
from spikemaul.model.line import Segment
from spikemaul.orders.governing import governing_at
from spikemaul.report.layout import Page
from spikemaul.report.speed import caps_for
from spikemaul.store.records import Records
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


def around(post: Milepost) -> Span:
    """A short stretch either side of a milepost, for asking registers with."""
    begin = post.advanced(-1) if post.hundredths > 0 else post
    return Span(begin, post.advanced(2))


def _track_section(
    page: Page, records: Records, subdivision: Ident, post: Milepost
) -> Segment | None:
    """What the track is here, and the curve if there is one."""
    try:
        segment = records.segments.at(subdivision, post)
        page.say(segment.describe())
        page.say(f"timetable speed {segment.speed()}")
    except NotFoundError:
        page.say("no segment covers this milepost")
        segment = None
    curve = records.curves.at(subdivision, post)
    if curve is None:
        page.say("tangent track")
        return segment
    page.say(curve.describe())
    page.say(f"curve speed {curve.maximum_speed()}")
    if curve.in_spiral(post):
        page.say("this is in a spiral rather than the body of the curve")
    return segment


def _standing_section(page: Page, records: Records, subdivision: Ident, nearby: Span) -> None:
    """What is built at this milepost."""
    said = False
    for turnout in records.turnouts.within(subdivision, nearby):
        page.say(turnout.describe())
        said = True
    for crossing in records.crossings.within(subdivision, nearby):
        page.say(crossing.describe())
        said = True
    for bridge in records.bridges.within(subdivision, nearby):
        page.say(bridge.describe())
        said = True
    if not said:
        page.say("plain track, nothing recorded within a hundredth")


def place_page(records: Records, subdivision: Ident, post: Milepost, on: date) -> Page:
    """What the book knows at one milepost."""
    record = records.subdivisions.get(subdivision)
    page = Page(f"{record.name} MP {post} on {on.isoformat()}")
    nearby = around(post)

    page.heading("track")
    segment = _track_section(page, records, subdivision, post)

    page.heading("what is here")
    _standing_section(page, records, subdivision, nearby)

    page.heading("what is wrong")
    cards = records.defects.open_within(subdivision, nearby)
    if not cards:
        page.say("no open cards here")
    for card in cards:
        page.say(card.describe())
        if segment is not None:
            page.say(f"  {card.action(segment.authorized).describe()}")

    page.heading("how fast")
    piece = governing_at(post, caps_for(records, subdivision, nearby, on))
    if piece is None:
        page.say("nothing on record sets a speed here")
    else:
        page.say(f"{piece.speed} because of the {piece.because} {piece.detail}".rstrip())
    for order in records.orders.covering(subdivision, nearby, on):
        page.say(order.describe())
    return page
