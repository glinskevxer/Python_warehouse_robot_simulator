"""Commands for rail wear and the flaw testing cycle."""

from __future__ import annotations

from decimal import Decimal

import click

from spikemaul.cli.common import book_of, day_of, failing, say
from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.side import Hand
from spikemaul.rail.flaw import status
from spikemaul.rail.wear import WearReading, tonnage_left, wear_rate
from spikemaul.report.layout import Column, Table
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.rails import FlawTest
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.tonnage import Tonnage


@click.group()
def rail() -> None:
    """Rail wear, and when the detector was last over it."""


@rail.command("measure")
@click.argument("code")
@click.argument("post")
@click.option("--hand", default="left", help="which rail")
@click.option("--section", default="115 RE", help="the rail section")
@click.option("--vertical", required=True, help="head loss, as 1/4")
@click.option("--gauge-face", required=True, help="gauge face wear, as 1/4")
@click.option("--degrees", default=None, help="the curve it is in")
@click.pass_context
@failing
def measure(
    context: click.Context,
    code: str,
    post: str,
    hand: str,
    section: str,
    vertical: str,
    gauge_face: str,
    degrees: str | None,
) -> None:
    """Record a wear reading on one rail."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    reading = WearReading(
        at=Milepost.parse(post),
        hand=Hand.parse(hand),
        rail_section=section,
        vertical=Inches.parse(vertical),
        gauge_face=Inches.parse(gauge_face),
        measured_on=day_of(context),
        curve=Curvature.parse(degrees) if degrees else TANGENT,
    )
    records.wear.add(reading, subdivision)
    holds = reading.class_supported()
    say(f"{reading.describe()}")
    if holds is None:
        say("this rail holds no class of track")
    records.close()


@rail.command("wear")
@click.argument("code")
@click.argument("span")
@click.pass_context
@failing
def wear(context: click.Context, code: str, span: str) -> None:
    """List the latest reading of each rail in a stretch."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    table = Table(
        [
            Column("milepost"),
            Column("rail"),
            Column("section"),
            Column("vertical"),
            Column("gauge face"),
            Column("combined"),
            Column("holds"),
            Column("measured"),
        ]
    )
    for one in records.wear.within(subdivision, Span.parse(span), day_of(context)):
        holds = one.class_supported()
        table.add(
            one.at,
            one.hand.value,
            one.rail_section,
            one.vertical,
            one.gauge_face,
            one.combined,
            "nothing" if holds is None else holds,
            one.measured_on,
        )
    for row in table.lines():
        say(row)
    records.close()


@rail.command("project")
@click.argument("code")
@click.argument("post")
@click.option("--hand", default="left", help="which rail")
@click.option("--tonnage", required=True, help="MGT between the two readings")
@click.option("--class", "against", default="3", help="the class to project against")
@click.pass_context
@failing
def project(
    context: click.Context, code: str, post: str, hand: str, tonnage: str, against: str
) -> None:
    """Work a wear rate off two readings and say what is left."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    readings = records.wear.at(subdivision, Milepost.parse(post), Hand.parse(hand))
    if len(readings) < 2:
        raise InputError(f"MP {post} has fewer than two readings of that rail")
    first, second = readings[0], readings[-1]
    over = Tonnage.parse(tonnage)
    rate = wear_rate(first, second, over)
    wanted = ClassOfTrack.parse(against)
    say(f"{rate} sixteenths per MGT between {first.measured_on} and {second.measured_on}")
    if rate <= Decimal(0):
        say("this rail is not wearing, so there is no date to plan against")
    else:
        say(f"{tonnage_left(second, wanted, rate)} left before it fails {wanted}")
    records.close()


@rail.command("tested")
@click.argument("code")
@click.argument("span")
@click.option("--inspection", required=True, help="the inspection the run was on")
@click.option("--tonnage", required=True, help="the tonnage standing at the time")
@click.option("--found", default=0, type=int, help="how many flaws it found")
@click.pass_context
@failing
def tested(
    context: click.Context, code: str, span: str, inspection: str, tonnage: str, found: int
) -> None:
    """Record a rail flaw detector run."""
    records = book_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    number = Ident.parse(inspection, Kind.INSPECTION)
    records.inspections.get(number)
    records.flaw_tests.add(
        FlawTest(
            inspection=number,
            subdivision=subdivision,
            span=Span.parse(span),
            on=day_of(context),
            tonnage_at=Tonnage.parse(tonnage),
            found=found,
        )
    )
    say(f"recorded {number} over {span}, {found} found")
    records.close()


@rail.command("cycle")
@click.argument("code")
@click.pass_context
@failing
def cycle(context: click.Context, code: str) -> None:
    """Say where each segment stands in its flaw testing cycle."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    latest = records.tonnage.latest(subdivision)
    table = Table(
        [
            Column("segment"),
            Column("class"),
            Column("last tested"),
            Column("since"),
            Column("state"),
            Column("clock"),
        ]
    )
    for segment in records.segments.on(subdivision):
        last = records.flaw_tests.last_covering(subdivision, segment.span, on)
        since = Tonnage(0)
        if last is not None and latest is not None:
            standing = records.tonnage.since(subdivision, last.on, on)
            since = standing
        standing_state = status(
            segment.authorized,
            on,
            last_tested=None if last is None else last.on,
            tonnage_since=since,
        )
        table.add(
            segment.ident,
            segment.authorized,
            last.on if last is not None else "never",
            since,
            "due" if standing_state.is_due else "in cycle",
            standing_state.governing,
        )
    for row in table.lines():
        say(row)
    records.close()
