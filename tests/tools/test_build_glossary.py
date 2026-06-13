"""The generated glossary."""

from __future__ import annotations

from spikemaul.tools.build_glossary import DOCUMENT, build, is_current, problems, terms, where


def test_the_glossary_on_disk_is_what_the_source_would_write() -> None:
    assert is_current(), f"{DOCUMENT} is stale, run python -m spikemaul.tools.build_glossary"
    assert problems() == []


def test_every_enumeration_with_values_is_in_it() -> None:
    names = {one.name for one in terms()}
    assert "Condition" in names
    assert "ClassOfTrack" not in names
    assert "WorkKind" in names


def test_a_term_says_where_it_lives_and_what_it_means() -> None:
    found = next(one for one in terms() if one.name == "Clock")
    assert found.module == "spikemaul.standards.remedial"
    assert "not interchangeable" in found.says
    assert "days" in found.values


def test_the_document_lists_the_values_a_form_may_offer() -> None:
    text = build()
    assert "- tie renewal" in text
    assert "- crossbucks" in text


def test_the_document_says_it_is_generated() -> None:
    assert "Do not edit" in build()


def test_the_document_lives_in_the_checkout() -> None:
    assert where().name == "glossary.md"
    assert where().parent.name == "docs"
