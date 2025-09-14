"""Where a stretch stands against its cycle, and what did not count."""

from __future__ import annotations

from datetime import date

from spikemaul.model.crew import Person
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Inspection, Method, Scope
from spikemaul.program.compliance import Standing, counted, gap_between, late, standing_for
from spikemaul.standards.classes import ClassOfTrack, TrackKind
from spikemaul.standards.inspection import WEEKLY
from spikemaul.units.span import Span
from tests.support.books import a_person, an_inspection

SPAN = Span.parse("12.00-14.00")
ON = date(2025, 5, 20)
RSTIVERS = Ident.named(Kind.PERSON, "RSTIVERS")


def people(**changes: Person) -> dict[Ident, Person]:
    book = {RSTIVERS: a_person()}
    book.update({one.ident: one for one in changes.values()})
    return book


def standing(
    inspections: list[Inspection],
    on: date = ON,
    book: dict[Ident, Person] | None = None,
) -> Standing:
    return standing_for(
        span=SPAN,
        scope=Scope.TRACK,
        track_class=ClassOfTrack.THREE,
        kind=TrackKind.MAIN,
        inspections=inspections,
        people=people() if book is None else book,
        on=on,
    )


def test_a_stretch_nobody_has_walked_is_never_inspected_and_late() -> None:
    got = standing([])
    assert got.never_inspected
    assert got.is_late
    assert got.due_on is None
    assert "never inspected" in got.describe()


def test_an_inspection_inside_the_cycle_is_in_cycle() -> None:
    got = standing([an_inspection(on=date(2025, 5, 19))])
    assert not got.is_late
    assert got.days_since == 1
    assert got.due_on == date(2025, 5, 26)
    assert got.days_late == 0


def test_an_inspection_older_than_the_cycle_is_late_by_the_difference() -> None:
    got = standing([an_inspection(on=date(2025, 5, 1))])
    assert got.is_late
    assert got.days_late == 12
    assert "12 days late" in got.describe()


def test_an_inspection_that_did_not_cover_the_whole_stretch_does_not_count() -> None:
    got = standing([an_inspection(on=date(2025, 5, 19), span="12.00-13.00")])
    assert got.never_inspected


def test_an_inspection_by_somebody_undesignated_does_not_count_and_is_reported() -> None:
    got = standing([an_inspection(on=date(2025, 5, 19), by="JHOLT")])
    assert got.never_inspected
    assert got.has_uncounted
    assert "1 did not count" in got.describe()


def test_an_inspection_after_the_designation_lapsed_does_not_count() -> None:
    got = standing([an_inspection(on=date(2026, 5, 19))], on=date(2026, 5, 20))
    assert got.never_inspected
    assert got.has_uncounted


def test_the_latest_counting_inspection_is_the_one_used() -> None:
    got = standing(
        [
            an_inspection(sequence=41, on=date(2025, 5, 1)),
            an_inspection(sequence=44, on=date(2025, 5, 19)),
        ]
    )
    assert got.days_since == 1


def test_an_inspection_after_the_day_asked_about_is_not_used() -> None:
    got = standing([an_inspection(on=date(2025, 6, 1))])
    assert got.never_inspected


def test_another_scope_does_not_satisfy_this_one() -> None:
    got = standing(
        [an_inspection(on=date(2025, 5, 19), scope=Scope.JOINT_BARS, method=Method.WALKING)]
    )
    assert got.never_inspected


def test_the_split_says_which_inspections_counted() -> None:
    good, bad = counted(
        [an_inspection(sequence=41), an_inspection(sequence=44, by="JHOLT")],
        people(),
        Scope.TRACK,
    )
    assert [one.ident.sequence for one in good] == [41]
    assert [one.ident.sequence for one in bad] == [44]


def test_the_late_stretches_come_back_worst_first() -> None:
    first = standing([an_inspection(on=date(2025, 5, 1))])
    second = standing([])
    got = late([first, second])
    assert len(got) == 2


def test_two_inspections_too_close_together_are_named_as_such() -> None:
    first = an_inspection(sequence=41, on=date(2025, 5, 12))
    second = an_inspection(sequence=44, on=date(2025, 5, 13))
    assert "closer than the 3" in gap_between(first, second, WEEKLY)


def test_two_inspections_too_far_apart_are_named_as_such() -> None:
    first = an_inspection(sequence=41, on=date(2025, 5, 1))
    second = an_inspection(sequence=44, on=date(2025, 5, 19))
    assert "past the 7" in gap_between(first, second, WEEKLY)


def test_a_legal_gap_says_only_how_far_apart_they_are() -> None:
    first = an_inspection(sequence=41, on=date(2025, 5, 12))
    second = an_inspection(sequence=44, on=date(2025, 5, 16))
    assert gap_between(first, second, WEEKLY) == "4 days apart"
