"""The error hierarchy, which the CLI's exit statuses are read off."""

from __future__ import annotations

import pytest

from spikemaul import __version__
from spikemaul.errors import (
    BookError,
    DuplicateError,
    InputError,
    NotFoundError,
    RuleError,
    SpikemaulError,
)


def test_the_package_states_its_version() -> None:
    assert __version__.count(".") == 2


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        (InputError, "input"),
        (NotFoundError, "not_found"),
        (DuplicateError, "exists"),
        (RuleError, "rule"),
        (BookError, "book"),
    ],
)
def test_every_error_carries_its_own_code(kind: type[SpikemaulError], code: str) -> None:
    assert kind.code == code


def test_every_error_can_be_caught_as_the_base_one() -> None:
    for kind in (InputError, RuleError, BookError):
        with pytest.raises(SpikemaulError):
            raise kind("something")


def test_the_message_survives_being_raised() -> None:
    with pytest.raises(InputError) as caught:
        raise InputError("milepost 43.9x will not parse")
    assert str(caught.value) == "milepost 43.9x will not parse"
    assert caught.value.message == "milepost 43.9x will not parse"


def test_a_missing_record_names_what_was_looked_for() -> None:
    with pytest.raises(NotFoundError) as caught:
        raise NotFoundError("segment", "MAIN-014")
    assert caught.value.kind == "segment"
    assert caught.value.ident == "MAIN-014"
    assert str(caught.value) == "no segment MAIN-014 in the book"


def test_a_duplicate_record_names_what_is_already_there() -> None:
    with pytest.raises(DuplicateError) as caught:
        raise DuplicateError("curve", "C-118")
    assert caught.value.kind == "curve"
    assert str(caught.value) == "curve C-118 is already in the book"


def test_the_codes_are_all_different() -> None:
    kinds: list[type[SpikemaulError]] = [
        SpikemaulError,
        InputError,
        NotFoundError,
        DuplicateError,
        RuleError,
        BookError,
    ]
    codes = [kind.code for kind in kinds]
    assert len(set(codes)) == len(codes)
