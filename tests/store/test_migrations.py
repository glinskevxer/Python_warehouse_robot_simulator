"""The migration list itself, before anything is run against a book."""

from __future__ import annotations

from spikemaul.store.migrations import MIGRATIONS


def test_the_migration_numbers_are_unique() -> None:
    numbers = [one.number for one in MIGRATIONS]
    assert len(set(numbers)) == len(numbers)


def test_the_migrations_are_in_the_order_they_will_be_run() -> None:
    numbers = [one.number for one in MIGRATIONS]
    assert numbers == sorted(numbers)


def test_the_numbers_start_at_one_and_leave_no_gaps() -> None:
    numbers = [one.number for one in MIGRATIONS]
    assert numbers == list(range(1, len(numbers) + 1))


def test_every_migration_says_what_it_is_for() -> None:
    for one in MIGRATIONS:
        assert one.name.strip()
        assert one.statements


def test_no_migration_drops_a_table_the_package_still_reads() -> None:
    statements = [one for migration in MIGRATIONS for one in migration.statements]
    assert not any(one.strip().upper().startswith("DROP TABLE") for one in statements)
