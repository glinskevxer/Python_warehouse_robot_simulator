"""The check that the registers and the migrations agree."""

from __future__ import annotations

from spikemaul.tools.check_schema import (
    READ_ELSEWHERE,
    REGISTERS,
    columns_of,
    problems,
    tables,
)


def test_every_register_reads_columns_the_book_has() -> None:
    assert [one.describe() for one in problems()] == []


def test_the_columns_come_out_of_a_book_the_migrations_built() -> None:
    assert columns_of("segments")[0] == "ident"
    assert "authorized" in columns_of("segments")


def test_every_table_is_read_by_a_register_or_named_as_read_elsewhere() -> None:
    named = {one.table for one in REGISTERS}
    for table in tables():
        assert table in named or table in READ_ELSEWHERE


def test_the_registers_that_declare_columns_are_all_here() -> None:
    names = {one.__name__ for one in REGISTERS}
    assert "Segments" in names
    assert "WorkOrders" in names
    assert len(REGISTERS) > 8


def test_the_tables_a_bespoke_register_holds_are_named() -> None:
    assert "readings" in READ_ELSEWHERE
    assert "tie_lengths" in READ_ELSEWHERE
