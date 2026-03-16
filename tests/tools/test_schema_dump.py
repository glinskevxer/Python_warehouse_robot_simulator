"""The generated schema document."""

from __future__ import annotations

from spikemaul.store.migrations import MIGRATIONS
from spikemaul.tools.schema_dump import DOCUMENT, dump, is_current, where


def test_the_document_on_disk_is_what_the_migrations_would_write() -> None:
    assert is_current(), f"{DOCUMENT} is stale, run python -m spikemaul.tools.schema_dump"


def test_the_document_names_every_table_the_book_makes() -> None:
    text = dump()
    for table in ("segments", "defects", "orders", "work_orders", "tie_lengths"):
        assert f"## {table}" in text


def test_the_document_names_every_migration() -> None:
    text = dump()
    for one in MIGRATIONS:
        assert f"{one.number}. {one.name}" in text


def test_the_document_says_it_is_generated() -> None:
    assert "Do not edit" in dump()


def test_the_document_says_which_columns_are_keys() -> None:
    assert "Key: ident." in dump()


def test_the_document_lives_in_the_checkout() -> None:
    assert where().name == "schema.md"
    assert where().parent.name == "docs"
