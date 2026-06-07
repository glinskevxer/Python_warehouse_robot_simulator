"""Commands for the people and the gangs, and for the designations that make
an inspection count."""

from __future__ import annotations

import click

from spikemaul.cli.common import as_day, book_of, day_of, failing, say
from spikemaul.errors import InputError
from spikemaul.model.crew import Craft, Gang, Person
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Scope
from spikemaul.program.qualification import (
    WINDOW_DAYS,
    lapsed,
    lapsing,
    uncovered,
    window_from,
)
from spikemaul.report.layout import Column, Table


def _scopes(text: str) -> frozenset[Scope]:
    if not text.strip():
        return frozenset()
    out = set()
    for one in text.split(","):
        try:
            out.add(Scope(one.strip().lower()))
        except ValueError as exc:
            named = ", ".join(scope.value for scope in Scope)
            raise InputError(f"{one.strip()!r} is not a scope, we have {named}") from exc
    return frozenset(out)


@click.group()
def person() -> None:
    """The people on the books and what they are designated for."""


@person.command("add")
@click.argument("initials")
@click.argument("name")
@click.option("--craft", default="trackman", help="what they do")
@click.option("--for", "scopes", default="", help="scopes, comma separated")
@click.option("--until", default=None, help="the day the designation runs to")
@click.pass_context
@failing
def add_person(
    context: click.Context,
    initials: str,
    name: str,
    craft: str,
    scopes: str,
    until: str | None,
) -> None:
    """Put somebody on the books."""
    records = book_of(context)
    records.people.add(
        Person(
            ident=Ident.named(Kind.PERSON, initials),
            name=name,
            craft=Craft(craft),
            qualified_for=_scopes(scopes),
            qualified_until=as_day(until),
        )
    )
    say(f"added {initials} {name}")
    records.close()


@person.command("qualify")
@click.argument("initials")
@click.option("--until", required=True, help="the day the designation runs to")
@click.option("--for", "scopes", default="", help="scopes, comma separated")
@click.pass_context
@failing
def qualify(context: click.Context, initials: str, until: str, scopes: str) -> None:
    """Renew somebody's designation, or change what it covers."""
    records = book_of(context)
    ident = Ident.named(Kind.PERSON, initials)
    who = records.people.get(ident)
    wanted = _scopes(scopes) if scopes.strip() else None
    day = as_day(until)
    if day is None:
        raise InputError("a designation runs to a day")
    records.people.update(who.requalified(day, wanted))
    say(f"{initials} designated through {until}")
    records.close()


@person.command("list")
@click.option("--scope", default=None, help="only those designated for a scope")
@click.pass_context
@failing
def list_people(context: click.Context, scope: str | None) -> None:
    """List the people, with what they are designated for and until when."""
    records = book_of(context)
    on = day_of(context)
    people = (
        records.people.all()
        if scope is None
        else records.people.qualified_for(Scope(scope.strip().lower()))
    )
    table = Table(
        [
            Column("person"),
            Column("name"),
            Column("craft"),
            Column("designated for"),
            Column("until"),
            Column("state"),
        ]
    )
    for one in people:
        lapsed = one.qualified_until is not None and one.qualified_until < on
        table.add(
            one.ident,
            one.name,
            one.craft.value,
            ", ".join(sorted(scope.value for scope in one.qualified_for)),
            one.qualified_until,
            "lapsed" if lapsed else "",
        )
    for row in table.lines():
        say(row)
    records.close()


@person.command("due")
@click.option("--within", default=None, type=int, help="days to look ahead")
@click.pass_context
@failing
def designations_due(context: click.Context, within: int | None) -> None:
    """Say whose designation has run out or runs out soon."""
    records = book_of(context)
    on = day_of(context)
    people = records.people.all()
    window = WINDOW_DAYS if within is None else within
    say(f"looking through {window_from(on, window).isoformat()}")
    for standing in lapsed(people, on):
        say(f"lapsed   {standing.describe()}")
    for standing in lapsing(people, on, window):
        say(f"{standing.days_left:>3} days {standing.describe()}")
    for scope in uncovered(people, on, tuple(Scope)):
        say(f"nobody   is designated for {scope.value}")
    records.close()


@click.group()
def gang() -> None:
    """The gangs and the machines they have."""


@gang.command("add")
@click.argument("code")
@click.argument("name")
@click.option("--foreman", required=True, help="the foreman's initials")
@click.option("--headcount", default=1, type=int, help="how many people")
@click.option("--machines", default="", help="machines, comma separated")
@click.option("--at", "headquarters", default="", help="where they tie up")
@click.pass_context
@failing
def add_gang(
    context: click.Context,
    code: str,
    name: str,
    foreman: str,
    headcount: int,
    machines: str,
    headquarters: str,
) -> None:
    """Put a gang in the book."""
    records = book_of(context)
    records.gangs.add(
        Gang(
            ident=Ident.named(Kind.GANG, code),
            name=name,
            foreman=Ident.named(Kind.PERSON, foreman),
            headcount=headcount,
            machines=tuple(one.strip() for one in machines.split(",") if one.strip()),
            headquarters=headquarters,
        )
    )
    say(f"added gang {code} {name}")
    records.close()


@gang.command("machine")
@click.argument("code")
@click.argument("machine")
@click.pass_context
@failing
def add_machine(context: click.Context, code: str, machine: str) -> None:
    """Assign a machine to a gang."""
    records = book_of(context)
    ident = Ident.named(Kind.GANG, code)
    records.gangs.update(records.gangs.get(ident).with_machine(machine))
    say(f"{machine} is on {code}")
    records.close()


@gang.command("list")
@click.pass_context
@failing
def list_gangs(context: click.Context) -> None:
    """List the gangs."""
    records = book_of(context)
    table = Table(
        [
            Column("gang"),
            Column("name"),
            Column("foreman"),
            Column("men", numeric=True),
            Column("machines"),
            Column("at"),
        ]
    )
    for one in records.gangs.all():
        table.add(
            one.ident,
            one.name,
            one.foreman.tail,
            one.headcount,
            ", ".join(one.machines),
            one.headquarters,
        )
    for row in table.lines():
        say(row)
    records.close()
