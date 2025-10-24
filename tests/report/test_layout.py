"""Fixed width layout, which knows nothing about the railroad."""

from __future__ import annotations

import pytest

from spikemaul.errors import InputError
from spikemaul.report.layout import Column, Page, Table, count_of, render


def table() -> Table:
    return Table([Column("milepost"), Column("speed", numeric=True)])


def test_an_empty_table_prints_only_its_headings() -> None:
    assert table().lines() == ["milepost  speed"]
    assert table().is_empty


def test_the_columns_are_as_wide_as_their_widest_cell() -> None:
    subject = table()
    subject.add("13.20", 10)
    subject.add("120.00", 40)
    assert subject.widths() == [8, 5]


def test_words_sit_left_and_numbers_sit_right() -> None:
    subject = table()
    subject.add("13.20", 10)
    assert subject.lines()[1] == "13.20        10"


def test_a_row_of_the_wrong_width_is_refused() -> None:
    subject = table()
    with pytest.raises(InputError, match="does not fit 2 columns"):
        subject.add("13.20")


def test_a_cell_with_nothing_in_it_prints_a_dash() -> None:
    subject = table()
    subject.add("13.20", None)
    subject.add("", 40)
    assert subject.rows == [["13.20", "-"], ["-", "40"]]


def test_trailing_space_is_not_printed() -> None:
    subject = Table([Column("a"), Column("b")])
    subject.add("x", "y")
    assert all(not line.endswith(" ") for line in subject.lines())


def test_a_page_underlines_its_title_and_its_headings() -> None:
    page = Page("roadmaster page")
    page.heading("bulletin")
    page.say("nothing in force")
    lines = page.lines()
    assert lines[0] == "roadmaster page"
    assert lines[1] == "=" * len("roadmaster page")
    assert lines[2] == "bulletin"
    assert lines[3] == "========"


def test_a_second_heading_is_separated_by_a_blank_line() -> None:
    page = Page("page")
    page.heading("first")
    page.heading("second")
    assert "" in page.lines()


def test_a_table_on_a_page_says_when_it_is_empty() -> None:
    page = Page("page")
    page.table(table(), empty="no orders in force")
    assert page.lines()[-1] == "no orders in force"


def test_a_table_with_rows_prints_them() -> None:
    page = Page("page")
    subject = table()
    subject.add("13.20", 10)
    page.table(subject)
    assert page.lines()[-1].startswith("13.20")


def test_rendering_ends_the_page_with_a_newline() -> None:
    page = Page("page")
    page.say("something")
    assert render(page).endswith("\n")
    assert render(page).count("\n") == 3


def test_a_count_carries_the_plural_the_office_uses() -> None:
    assert count_of(1, "order") == "1 order"
    assert count_of(0, "order") == "0 orders"
    assert count_of(4, "defect") == "4 defects"
