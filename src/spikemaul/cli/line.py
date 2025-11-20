"""Commands for the railroad itself: subdivisions, equations and segments."""

from __future__ import annotations

import click

from spikemaul.cli.common import as_day, book_of, failing, say
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.line import Segment, Subdivision
from spikemaul.report.layout import Column, Table
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.units.chainage import Chainage, Equation
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


@click.group()
def line() -> None:
    """Subdivisions and the segments they are cut into."""


@line.command("add")
@click.argument("code")
@click.argument("name")
@click.option("--begin", default="0.00", help="the first milepost")
@click.option("--end", required=True, help="the last milepost")
@click.pass_context
@failing
def add_subdivision(context: click.Context, code: str, name: str, begin: str, end: str) -> None:
    """Put a subdivision in the book."""
    records = book_of(context)
    records.subdivisions.add(
        Subdivision(
            ident=Ident.named(Kind.SUBDIVISION, code),
            name=name,
            chainage=Chainage(Milepost.parse(begin), Milepost.parse(end)),
        )
    )
    say(f"added {code} {name}")
    records.close()


@line.command("equate")
@click.argument("code")
@click.argument("back")
@click.argument("ahead")
@click.pass_context
@failing
def add_equation(context: click.Context, code: str, back: str, ahead: str) -> None:
    """Add an equation point, written back equals ahead."""
    records = book_of(context)
    ident = Ident.named(Kind.SUBDIVISION, code)
    subdivision = records.subdivisions.get(ident)
    equations = (
        *subdivision.chainage.equations,
        Equation(Milepost.parse(back), Milepost.parse(ahead)),
    )
    records.subdivisions.update(
        Subdivision(
            ident=ident,
            name=subdivision.name,
            chainage=Chainage(subdivision.chainage.begin, subdivision.chainage.end, equations),
        )
    )
    say(f"{code} now MP {back} = MP {ahead}")
    records.close()


@line.command("list")
@click.pass_context
@failing
def list_subdivisions(context: click.Context) -> None:
    """List the subdivisions."""
    records = book_of(context)
    table = Table(
        [
            Column("code"),
            Column("name"),
            Column("from"),
            Column("to"),
            Column("miles", numeric=True),
            Column("equations", numeric=True),
        ]
    )
    for one in records.subdivisions.all():
        table.add(
            one.code,
            one.name,
            one.chainage.begin,
            one.chainage.end,
            one.miles,
            len(one.chainage.equations),
        )
    for row in table.lines():
        say(row)
    records.close()


@line.command("segment")
@click.argument("code")
@click.argument("number")
@click.argument("span")
@click.option("--class", "track_class", default="3", help="the class it is held to")
@click.option("--kind", default="main", help="main, siding, yard or industry")
@click.option("--rail", default="115 RE", help="the rail section")
@click.option("--laid", required=True, help="the day the rail was laid")
@click.option("--welded", is_flag=True, help="continuous welded rail")
@click.pass_context
@failing
def add_segment(
    context: click.Context,
    code: str,
    number: str,
    span: str,
    track_class: str,
    kind: str,
    rail: str,
    laid: str,
    welded: bool,
) -> None:
    """Put a segment in the book, as SPAN like 12.00-14.50."""
    records = book_of(context)
    laid_on = as_day(laid)
    if laid_on is None:
        raise click.UsageError("the day the rail was laid is needed")
    records.segments.add(
        Segment(
            ident=Ident.named(Kind.SEGMENT, number),
            subdivision=Ident.named(Kind.SUBDIVISION, code),
            span=Span.parse(span),
            kind=TrackKind.parse(kind),
            authorized=ClassOfTrack.parse(track_class),
            rail_section=rail,
            rail_laid=laid_on,
            welded=welded,
        )
    )
    say(f"added segment {number} {span} on {code}")
    records.close()


@line.command("segments")
@click.argument("code")
@click.pass_context
@failing
def list_segments(context: click.Context, code: str) -> None:
    """List the segments on a subdivision, in milepost order."""
    records = book_of(context)
    table = Table(
        [
            Column("segment"),
            Column("from"),
            Column("to"),
            Column("kind"),
            Column("class"),
            Column("rail"),
            Column("speed", numeric=True),
        ]
    )
    for one in records.segments.on(Ident.named(Kind.SUBDIVISION, code)):
        table.add(
            one.ident,
            one.span.begin,
            one.span.end,
            one.kind.value,
            one.authorized,
            f"{one.rail_section} {'cwr' if one.welded else 'jointed'}",
            one.speed().mph,
        )
    for row in table.lines():
        say(row)
    records.close()


@line.command("where")
@click.argument("code")
@click.argument("post")
@click.pass_context
@failing
def where(context: click.Context, code: str, post: str) -> None:
    """Say what is at a milepost: the segment, and any curve it is in."""
    records = book_of(context)
    ident = Ident.named(Kind.SUBDIVISION, code)
    milepost = Milepost.parse(post)
    segment = records.segments.at(ident, milepost)
    say(segment.describe())
    curve = records.curves.at(ident, milepost)
    say(curve.describe() if curve is not None else "no curve here")
    records.close()
