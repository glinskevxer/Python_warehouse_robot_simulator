"""Commands for tie surveys and what they say the gang needs."""

from __future__ import annotations

import click

from spikemaul.cli.common import as_day, book_of, day_of, failing, say
from spikemaul.loading.surveys import read_survey
from spikemaul.model.ids import Ident, Kind, next_number
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.report.layout import Column, Table
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.ties.condition import class_supported, governing_rule
from spikemaul.units.span import Span
from spikemaul.work.needs import needs_from_survey


@click.group()
def ties() -> None:
    """Tie surveys, what they hold and what they need."""


@ties.command("load")
@click.argument("code")
@click.argument("span")
@click.argument("path", type=click.Path())
@click.option("--by", required=True, help="who walked it")
@click.pass_context
@failing
def load(context: click.Context, code: str, span: str, path: str, by: str) -> None:
    """Load a tie survey sheet and record the walk it belongs to."""
    records = book_of(context)
    on = day_of(context)
    subdivision = Ident.named(Kind.SUBDIVISION, code)
    records.subdivisions.get(subdivision)
    who = records.people.get(Ident.named(Kind.PERSON, by))
    over = Span.parse(span)
    survey = read_survey(path, subdivision, over, on)
    number = next_number(Kind.INSPECTION, on.year, [one.ident for one in records.inspections.all()])
    records.inspections.add(
        Inspection(
            ident=number,
            subdivision=subdivision,
            span=over,
            on=on,
            by=who.ident,
            method=Method.WALKING,
            scope=Scope.TRACK,
            note=f"tie survey from {path}",
        )
    )
    records.surveys.add(survey, number)
    held = survey.class_supported()
    holds = "nothing" if held is None else str(held)
    say(f"loaded {number}, {survey.counted} lengths, holds {holds}")
    records.close()


@ties.command("show")
@click.argument("inspection")
@click.option("--class", "against", default=None, help="the class to judge it against")
@click.pass_context
@failing
def show_survey(context: click.Context, inspection: str, against: str | None) -> None:
    """Print a survey length by length, worst first where it fails."""
    records = book_of(context)
    number = Ident.parse(inspection, Kind.INSPECTION)
    survey = records.surveys.get(number)
    table = Table(
        [
            Column("milepost"),
            Column("good", numeric=True),
            Column("of", numeric=True),
            Column("run", numeric=True),
            Column("joints"),
            Column("holds"),
            Column("rule"),
        ]
    )
    for one in survey.lengths:
        held = class_supported(one)
        table.add(
            one.at,
            one.good,
            one.total,
            one.longest_run,
            f"{one.joints_supported}/{one.joints}",
            "nothing" if held is None else held,
            governing_rule(one),
        )
    for row in table.lines():
        say(row)
    if against is not None:
        wanted = ClassOfTrack.parse(against)
        failing_lengths = survey.failing(wanted)
        say(f"{len(failing_lengths)} lengths below {wanted}")
        say(f"{survey.ties_needed(wanted)} ties to hold {wanted}")
    records.close()


@ties.command("needs")
@click.argument("inspection")
@click.option("--class", "against", required=True, help="the class to bring it to")
@click.option("--due", default=None, help="the day the work is wanted by")
@click.pass_context
@failing
def survey_needs(context: click.Context, inspection: str, against: str, due: str | None) -> None:
    """Say what a survey calls for, one need per run of bad lengths."""
    records = book_of(context)
    number = Ident.parse(inspection, Kind.INSPECTION)
    survey = records.surveys.get(number)
    wanted = ClassOfTrack.parse(against)
    found = needs_from_survey(survey, wanted, as_day(due))
    if not found:
        say(f"nothing needed to hold {wanted}")
    for one in found:
        say(one.describe())
    records.close()
