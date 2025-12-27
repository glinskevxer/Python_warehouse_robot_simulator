"""Commands for defect cards: raising one, repairing one, listing what is open."""

from __future__ import annotations

import click

from spikemaul.cli.common import as_day, book_of, day_of, failing, say
from spikemaul.errors import NotFoundError
from spikemaul.model.defect import Condition, Defect
from spikemaul.model.ids import Ident, Kind
from spikemaul.report.layout import Column, Table
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.units.milepost import Milepost


def _class(text: str | None) -> ClassOfTrack | None:
    if text is None or text.strip().lower() in {"none", "nothing"}:
        return None
    return ClassOfTrack.parse(text)


@click.group()
def defect() -> None:
    """Defect cards and what they leave the track holding."""


@defect.command("raise")
@click.argument("code")
@click.argument("post")
@click.argument("condition")
@click.option("--reading", required=True, help="what was measured")
@click.option("--meets", default=None, help="the class it meets, or none")
@click.option("--by", required=True, help="who found it")
@click.option("--inspection", default=None, help="the inspection it came off")
@click.option("--note", default="", help="anything worth writing down")
@click.pass_context
@failing
def raise_card(
    context: click.Context,
    code: str,
    post: str,
    condition: str,
    reading: str,
    meets: str | None,
    by: str,
    inspection: str | None,
    note: str,
) -> None:
    """Raise a defect card at a milepost."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    who = records.people.get(Ident.named(Kind.PERSON, by))
    number = records.defects.next_number(on.year)
    card = Defect(
        ident=number,
        subdivision=subdivision,
        at=Milepost.parse(post),
        found_on=on,
        found_by=who.ident,
        condition=Condition.parse(condition),
        reading=reading,
        meets=_class(meets),
        inspection=(None if inspection is None else Ident.parse(inspection, Kind.INSPECTION)),
        note=note,
    )
    records.defects.add(card)
    try:
        held = records.segments.at(subdivision, card.at).authorized
        say(f"raised {number}, {card.action(held).describe()}")
    except NotFoundError:
        say(f"raised {number}, no segment covers MP {post} so no action was worked out")
    records.close()


@defect.command("repair")
@click.argument("number")
@click.pass_context
@failing
def repair(context: click.Context, number: str) -> None:
    """Write the repair date on a card."""
    records = book_of(context)
    ident = Ident.parse(number, Kind.DEFECT)
    card = records.defects.get(ident)
    records.defects.update(card.repaired(day_of(context)))
    say(f"{ident} repaired {day_of(context).isoformat()}")
    records.close()


@defect.command("list")
@click.argument("code")
@click.option("--all", "everything", is_flag=True, help="repaired cards as well")
@click.option("--since", default=None, help="only cards raised on or after a day")
@click.pass_context
@failing
def list_cards(context: click.Context, code: str, everything: bool, since: str | None) -> None:
    """List the cards on a subdivision, open ones by default."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    from_day = as_day(since)
    if everything:
        cards = [one for one in records.defects.all() if one.subdivision == subdivision]
    else:
        cards = records.defects.open_on(subdivision)
    if from_day is not None:
        cards = [one for one in cards if one.found_on >= from_day]
    table = Table(
        [
            Column("card"),
            Column("found"),
            Column("milepost"),
            Column("condition"),
            Column("reading"),
            Column("meets"),
            Column("state"),
        ]
    )
    for card in cards:
        try:
            held = records.segments.at(subdivision, card.at).authorized
            state = "overdue" if card.is_overdue(held, on) else "open"
        except NotFoundError:
            state = "no segment"
        table.add(
            card.ident,
            card.found_on,
            card.at,
            card.condition.value,
            card.reading,
            "nothing" if card.meets is None else card.meets,
            state if card.is_open else f"repaired {card.repaired_on}",
        )
    for row in table.lines():
        say(row)
    records.close()


@defect.command("action")
@click.argument("number")
@click.pass_context
@failing
def action(context: click.Context, number: str) -> None:
    """Say what the rule requires for one card, against the class held today."""
    records = book_of(context)
    ident = Ident.parse(number, Kind.DEFECT)
    card = records.defects.get(ident)
    segment = records.segments.at(card.subdivision, card.at)
    remedy = card.action(segment.authorized)
    say(f"{ident} at MP {card.at} on {segment.ident}, held at {segment.authorized}")
    say(remedy.describe())
    due = card.due_on(segment.authorized)
    if due is not None:
        say(f"due {due.isoformat()}")
    records.close()


@defect.command("out")
@click.argument("code")
@click.pass_context
@failing
def out_of_service(context: click.Context, code: str) -> None:
    """List the cards whose condition meets no class of track at all."""
    records = book_of(context)
    cards = records.defects.out_of_service(Ident.named(Kind.SUBDIVISION, code))
    if not cards:
        say("nothing out of service")
    for card in cards:
        say(card.describe())
    records.close()


@defect.command("conditions")
@failing
def conditions() -> None:
    """List the conditions this package records."""
    for one in Condition:
        say(f"{one.value:<12} {'geometry' if one.is_geometry else 'walking'}")
