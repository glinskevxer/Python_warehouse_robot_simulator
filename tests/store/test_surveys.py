"""Tie surveys, which go into the book whole."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import DuplicateError, NotFoundError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method, Scope
from spikemaul.standards.classes import ClassOfTrack
from spikemaul.store.inspections import Inspections
from spikemaul.store.subdivisions import Subdivisions
from spikemaul.store.surveys import TieSurveys
from spikemaul.ties.condition import TieLength
from spikemaul.ties.survey import TieSurvey
from spikemaul.units.curvature import TANGENT, Curvature
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from tests.support.books import a_book, a_subdivision, an_inspection

PLAINS = Ident.named(Kind.SUBDIVISION, "PLAINS")
WALKED_ON = date(2025, 8, 4)
NUMBER = Ident.numbered(Kind.INSPECTION, 2025, 61)


def register() -> TieSurveys:
    book = a_book()
    Subdivisions(book).add(a_subdivision())
    Inspections(book).add(
        an_inspection(
            sequence=61,
            on=WALKED_ON,
            span="13.00-14.00",
            method=Method.WALKING,
            scope=Scope.TRACK,
        )
    )
    return TieSurveys(book)


def length(post: str, good: int = 16, curve: Curvature = TANGENT) -> TieLength:
    return TieLength(
        at=Milepost.parse(post),
        total=22,
        good=good,
        longest_run=2,
        joints=1,
        joints_supported=1,
        curve=curve,
    )


def survey(*lengths: TieLength) -> TieSurvey:
    return TieSurvey(
        subdivision=PLAINS, span=Span.parse("13.00-14.00"), on=WALKED_ON, lengths=list(lengths)
    )


def test_a_survey_comes_back_the_way_it_went_in() -> None:
    surveys = register()
    surveys.add(survey(length("13.10"), length("13.20", good=9)), NUMBER)
    got = surveys.get(NUMBER)
    assert got == survey(length("13.10"), length("13.20", good=9))
    assert got.class_supported() == ClassOfTrack.THREE


def test_a_length_on_a_curve_keeps_its_curvature() -> None:
    surveys = register()
    surveys.add(survey(length("13.10", curve=Curvature.of(4))), NUMBER)
    got = surveys.get(NUMBER)
    assert got.lengths[0].curve == Curvature.of(4)


def test_the_lengths_come_back_in_the_order_they_were_walked() -> None:
    surveys = register()
    surveys.add(survey(length("13.10"), length("13.20"), length("13.30")), NUMBER)
    got = surveys.get(NUMBER)
    assert [str(one.at) for one in got.lengths] == ["13.10", "13.20", "13.30"]


def test_the_same_survey_twice_is_refused() -> None:
    surveys = register()
    surveys.add(survey(length("13.10")), NUMBER)
    with pytest.raises(DuplicateError, match="tie survey"):
        surveys.add(survey(length("13.10")), NUMBER)


def test_a_survey_that_is_not_there_is_not_invented() -> None:
    surveys = register()
    with pytest.raises(NotFoundError, match="no tie survey"):
        surveys.get(NUMBER)
    with pytest.raises(NotFoundError, match="no tie survey"):
        surveys.remove(NUMBER)


def test_a_survey_can_be_taken_out_whole() -> None:
    surveys = register()
    surveys.add(survey(length("13.10")), NUMBER)
    surveys.remove(NUMBER)
    assert surveys.count() == 0
    assert surveys.on(PLAINS) == []


def test_the_surveys_on_a_subdivision_come_back_oldest_first() -> None:
    surveys = register()
    surveys.add(survey(length("13.10")), NUMBER)
    assert surveys.on(PLAINS) == [NUMBER]


def test_the_survey_covering_a_stretch_has_to_take_in_all_of_it() -> None:
    surveys = register()
    surveys.add(survey(length("13.10")), NUMBER)
    assert surveys.covering(PLAINS, Span.parse("13.20-13.40"), WALKED_ON) == NUMBER
    assert surveys.covering(PLAINS, Span.parse("13.00-20.00"), WALKED_ON) is None


def test_a_survey_after_the_day_asked_about_does_not_count() -> None:
    surveys = register()
    surveys.add(survey(length("13.10")), NUMBER)
    assert surveys.covering(PLAINS, Span.parse("13.20-13.40"), date(2025, 8, 1)) is None


def test_a_number_that_is_not_an_inspection_is_refused() -> None:
    surveys = register()
    with pytest.raises(NotFoundError, match="no inspection"):
        surveys.add(survey(length("13.10")), Ident.named(Kind.SEGMENT, "014"))
