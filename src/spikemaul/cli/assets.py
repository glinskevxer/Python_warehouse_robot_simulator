"""Commands for the things sitting on the railroad: curves, turnouts,
crossings and bridges."""

from __future__ import annotations

import click

from spikemaul.cli.common import book_of, failing, say
from spikemaul.model.curve import Curve
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.model.structure import Bridge, Crossing, Structure, Surface, WarningDevice
from spikemaul.model.turnout import FrogKind, Throw, Turnout
from spikemaul.report.layout import Column, Table
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span


def _print(table: Table) -> None:
    for row in table.lines():
        say(row)


@click.group()
def curve() -> None:
    """Curves and the elevation they carry."""


@curve.command("add")
@click.argument("code")
@click.argument("number")
@click.argument("body")
@click.option("--degrees", required=True, help="degree of curvature, as 3-30")
@click.option("--elevation", default="0", help="the designated elevation")
@click.option("--hand", default="left", help="which way it turns")
@click.option("--spiral", default=0, type=int, help="spiral length at each end")
@click.pass_context
@failing
def add_curve(
    context: click.Context,
    code: str,
    number: str,
    body: str,
    degrees: str,
    elevation: str,
    hand: str,
    spiral: int,
) -> None:
    """Put a curve in the book, as BODY like 13.10-13.40."""
    records = book_of(context)
    records.curves.add(
        Curve(
            ident=Ident.named(Kind.CURVE, number),
            subdivision=Ident.named(Kind.SUBDIVISION, code),
            body=Span.parse(body),
            curvature=Curvature.parse(degrees),
            elevation=Inches.parse(elevation),
            hand=Hand.parse(hand),
            entry_spiral_feet=spiral,
            exit_spiral_feet=spiral,
        )
    )
    say(f"added curve {number} {body}")
    records.close()


@curve.command("list")
@click.argument("code")
@click.pass_context
@failing
def list_curves(context: click.Context, code: str) -> None:
    """List the curves on a subdivision, with the speed each allows."""
    records = book_of(context)
    table = Table(
        [
            Column("curve"),
            Column("from"),
            Column("to"),
            Column("degrees"),
            Column("hand"),
            Column("elevation", numeric=True),
            Column("speed", numeric=True),
        ]
    )
    for one in records.curves.on(Ident.named(Kind.SUBDIVISION, code)):
        table.add(
            one.ident,
            one.body.begin,
            one.body.end,
            one.curvature,
            one.hand.value,
            one.elevation,
            one.maximum_speed().mph,
        )
    _print(table)
    records.close()


@click.group()
def turnout() -> None:
    """Turnouts and their diverging speeds."""


@turnout.command("add")
@click.argument("code")
@click.argument("number")
@click.argument("post")
@click.option("--size", required=True, type=int, help="the frog number")
@click.option("--hand", default="right", help="which way the diverging route goes")
@click.option("--frog", default="rigid", help="rigid, spring, self guarded or moveable")
@click.option("--throw", default="hand", help="hand, spring or power")
@click.option("--leads-to", default="", help="what the diverging route serves")
@click.pass_context
@failing
def add_turnout(
    context: click.Context,
    code: str,
    number: str,
    post: str,
    size: int,
    hand: str,
    frog: str,
    throw: str,
    leads_to: str,
) -> None:
    """Put a turnout in the book, recorded at its point of switch."""
    records = book_of(context)
    records.turnouts.add(
        Turnout(
            ident=Ident.named(Kind.TURNOUT, number),
            subdivision=Ident.named(Kind.SUBDIVISION, code),
            point_of_switch=Milepost.parse(post),
            size=size,
            hand=Hand.parse(hand),
            frog=FrogKind(frog),
            throw=Throw(throw),
            leads_to=leads_to,
        )
    )
    say(f"added turnout {number} at MP {post}")
    records.close()


@turnout.command("list")
@click.argument("code")
@click.pass_context
@failing
def list_turnouts(context: click.Context, code: str) -> None:
    """List the turnouts on a subdivision."""
    records = book_of(context)
    table = Table(
        [
            Column("turnout"),
            Column("milepost"),
            Column("size", numeric=True),
            Column("hand"),
            Column("frog"),
            Column("diverging", numeric=True),
            Column("leads to"),
        ]
    )
    for one in records.turnouts.on(Ident.named(Kind.SUBDIVISION, code)):
        table.add(
            one.ident,
            one.point_of_switch,
            one.size,
            one.hand.value,
            one.frog.value,
            one.diverging_speed.mph,
            one.leads_to,
        )
    _print(table)
    records.close()


@click.group()
def crossing() -> None:
    """Grade crossings and their inventory numbers."""


@crossing.command("add")
@click.argument("code")
@click.argument("number")
@click.argument("post")
@click.argument("road")
@click.option("--inventory", required=True, help="six digits and a check letter")
@click.option("--surface", default="timber", help="timber, rubber, concrete or asphalt")
@click.option("--warning", default="crossbucks", help="crossbucks, flashers or gates")
@click.option("--private", is_flag=True, help="a private crossing")
@click.pass_context
@failing
def add_crossing(
    context: click.Context,
    code: str,
    number: str,
    post: str,
    road: str,
    inventory: str,
    surface: str,
    warning: str,
    private: bool,
) -> None:
    """Put a grade crossing in the book."""
    records = book_of(context)
    records.crossings.add(
        Crossing(
            ident=Ident.named(Kind.CROSSING, number),
            subdivision=Ident.named(Kind.SUBDIVISION, code),
            at=Milepost.parse(post),
            road=road,
            inventory=inventory,
            surface=Surface(surface),
            warning=WarningDevice(warning),
            public=not private,
        )
    )
    say(f"added crossing {number} at MP {post}")
    records.close()


@click.group()
def bridge() -> None:
    """Structures and their load ratings."""


@bridge.command("add")
@click.argument("code")
@click.argument("number")
@click.argument("post")
@click.option("--kind", default="deck girder", help="what sort of structure")
@click.option("--spans", default=1, type=int, help="how many spans")
@click.option("--length", required=True, type=int, help="length in feet")
@click.option("--normal", required=True, type=int, help="normal rating, Cooper E")
@click.option("--maximum", required=True, type=int, help="maximum rating, Cooper E")
@click.option("--built", required=True, type=int, help="the year it was built")
@click.pass_context
@failing
def add_bridge(
    context: click.Context,
    code: str,
    number: str,
    post: str,
    kind: str,
    spans: int,
    length: int,
    normal: int,
    maximum: int,
    built: int,
) -> None:
    """Put a structure in the book."""
    records = book_of(context)
    records.bridges.add(
        Bridge(
            ident=Ident.named(Kind.BRIDGE, number),
            subdivision=Ident.named(Kind.SUBDIVISION, code),
            at=Milepost.parse(post),
            kind=Structure(kind),
            spans=spans,
            length_feet=length,
            normal_rating=normal,
            maximum_rating=maximum,
            built=built,
        )
    )
    say(f"added bridge {number} at MP {post}")
    records.close()


@bridge.command("list")
@click.argument("code")
@click.pass_context
@failing
def list_bridges(context: click.Context, code: str) -> None:
    """List the structures on a subdivision, weakest rating marked."""
    records = book_of(context)
    weakest = records.bridges.weakest()
    table = Table(
        [
            Column("bridge"),
            Column("milepost"),
            Column("kind"),
            Column("spans", numeric=True),
            Column("length", numeric=True),
            Column("rating"),
            Column(""),
        ]
    )
    for one in records.bridges.within(
        Ident.named(Kind.SUBDIVISION, code),
        records.subdivisions.get(Ident.named(Kind.SUBDIVISION, code)).span,
    ):
        table.add(
            one.ident,
            one.at,
            one.kind.value,
            one.spans,
            one.length_feet,
            f"E {one.normal_rating}/{one.maximum_rating}",
            "weakest" if weakest is not None and weakest.ident == one.ident else "",
        )
    _print(table)
    records.close()
