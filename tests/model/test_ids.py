"""Record numbers, which are written by hand and therefore mistyped."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.model.ids import Ident, Kind, next_number


def test_a_kind_says_what_the_office_calls_it() -> None:
    assert Kind.DEFECT.label == "defect"
    assert Kind.ORDER.label == "slow order"
    assert {one.label for one in Kind}.__len__() == len(Kind)


def test_a_kind_reads_off_its_prefix() -> None:
    assert Kind.parse("DF") == Kind.DEFECT
    assert Kind.parse(" sg ") == Kind.SEGMENT
    with pytest.raises(InputError, match="not a kind of record"):
        Kind.parse("ZZ")


def test_the_records_raised_in_a_year_carry_the_year() -> None:
    assert Kind.DEFECT.is_numbered_by_year
    assert Kind.ORDER.is_numbered_by_year
    assert not Kind.SEGMENT.is_numbered_by_year
    assert not Kind.CURVE.is_numbered_by_year


def test_a_defect_number_reads_and_prints_the_way_it_is_written() -> None:
    got = Ident.parse("DF-2025-0142")
    assert got.kind is Kind.DEFECT
    assert got.year == 2025
    assert got.sequence == 142
    assert str(got) == "DF-2025-0142"


def test_a_segment_number_has_no_year() -> None:
    got = Ident.parse("sg-014")
    assert got.kind is Kind.SEGMENT
    assert got.year is None
    assert str(got) == "SG-014"


def test_the_sequence_width_is_fixed_so_the_numbers_sort() -> None:
    with pytest.raises(InputError, match="4 digit sequence"):
        Ident(Kind.DEFECT, 2025, "142")
    numbers = [Ident.numbered(Kind.DEFECT, 2025, n) for n in (9, 10, 100)]
    assert [str(one) for one in sorted(numbers)] == [
        "DF-2025-0009",
        "DF-2025-0010",
        "DF-2025-0100",
    ]


def test_a_year_on_a_record_that_does_not_carry_one_is_refused() -> None:
    with pytest.raises(InputError, match="does not carry a year"):
        Ident(Kind.SEGMENT, 2025, "014")
    with pytest.raises(InputError, match="carries the year"):
        Ident(Kind.DEFECT, None, "0142")


def test_a_year_that_is_not_a_year_is_refused() -> None:
    with pytest.raises(InputError, match="is not a year"):
        Ident(Kind.DEFECT, 25, "0142")


@pytest.mark.parametrize("text", ["", "DF2025-0142", "DF-25-0142", "DF-2025-014", "sg_014", "014"])
def test_rubbish_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        Ident.parse(text)


def test_a_number_of_the_wrong_kind_is_refused_where_a_kind_is_expected() -> None:
    assert Ident.parse("DF-2025-0142", Kind.DEFECT).sequence == 142
    with pytest.raises(InputError, match="is a defect number, not a slow order one"):
        Ident.parse("DF-2025-0142", Kind.ORDER)


def test_a_sequence_out_of_range_is_refused() -> None:
    with pytest.raises(InputError, match="not a sequence number"):
        Ident.numbered(Kind.DEFECT, 2025, 0)
    with pytest.raises(InputError, match="not a sequence number"):
        Ident.numbered(Kind.DEFECT, 2025, 10000)


def test_a_plain_number_has_no_sequence_to_ask_for() -> None:
    with pytest.raises(InputError, match="has no sequence"):
        assert Ident.named(Kind.SEGMENT, "014").sequence


def test_the_next_number_follows_the_highest_one_used_that_year() -> None:
    taken = [
        Ident.numbered(Kind.DEFECT, 2025, 1),
        Ident.numbered(Kind.DEFECT, 2025, 7),
        Ident.numbered(Kind.ORDER, 2025, 31),
        Ident.numbered(Kind.DEFECT, 2024, 900),
    ]
    assert next_number(Kind.DEFECT, 2025, taken) == Ident.numbered(Kind.DEFECT, 2025, 8)
    assert next_number(Kind.ORDER, 2025, taken) == Ident.numbered(Kind.ORDER, 2025, 32)


def test_a_year_with_nothing_in_it_starts_at_one() -> None:
    assert str(next_number(Kind.DEFECT, 2026, [])) == "DF-2026-0001"


def test_a_gap_left_by_a_cancelled_record_is_not_filled_in() -> None:
    taken = [Ident.numbered(Kind.DEFECT, 2025, 1), Ident.numbered(Kind.DEFECT, 2025, 3)]
    assert next_number(Kind.DEFECT, 2025, taken) == Ident.numbered(Kind.DEFECT, 2025, 4)


def test_a_kind_that_is_not_issued_by_sequence_is_refused() -> None:
    with pytest.raises(InputError, match="not issued by sequence"):
        next_number(Kind.SEGMENT, 2025, [])
