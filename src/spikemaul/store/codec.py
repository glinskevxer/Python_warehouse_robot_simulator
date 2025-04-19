"""Turning the quantities into columns and back.

Sqlite has integers, text and nothing else worth using here, so every unit in
this package has one column shape and exactly one place that knows it. A
milepost is an integer of hundredths, a measurement is an integer of
sixteenths, a date is an ISO string, and an enumeration is the value it was
declared with.

The rule that pays for this module is that every decode refuses rubbish. A
book that has been edited by hand, restored from a bad backup or written by an
older version of this package will hand back something that does not fit, and
finding that out at the register is much cheaper than finding it out three
layers up where the value has already been averaged into a report.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import TypeVar

from spikemaul.errors import BookError
from spikemaul.model.ids import Ident, Kind
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed
from spikemaul.units.temperature import Temperature
from spikemaul.units.tonnage import Tonnage

AnEnum = TypeVar("AnEnum", bound=Enum)


def encode_post(post: Milepost) -> int:
    """A milepost as the integer hundredths the column holds."""
    return post.hundredths


def decode_post(value: object) -> Milepost:
    """A milepost back out of a column, refusing anything that is not one."""
    if not isinstance(value, int):
        raise BookError(f"{value!r} is not a milepost column")
    try:
        return Milepost(value)
    except Exception as exc:
        raise BookError(f"{value!r} is not a milepost") from exc


def encode_span(span: Span) -> tuple[int, int]:
    """A span as the pair of columns it is held in."""
    return span.begin.hundredths, span.end.hundredths


def decode_span(begin: object, end: object) -> Span:
    """A span back out of its pair of columns."""
    try:
        return Span(decode_post(begin), decode_post(end))
    except BookError:
        raise
    except Exception as exc:
        raise BookError(f"{begin!r} to {end!r} is not a span") from exc


def encode_inches(measure: Inches) -> int:
    """A measurement as the integer sixteenths the column holds."""
    return measure.sixteenths


def decode_inches(value: object) -> Inches:
    """A measurement back out of a column."""
    if not isinstance(value, int):
        raise BookError(f"{value!r} is not a measurement column")
    return Inches(value)


def encode_date(day: date) -> str:
    """A date as the ISO string the column holds."""
    return day.isoformat()


def decode_date(value: object) -> date:
    """A date back out of a column, refusing anything that is not one."""
    if not isinstance(value, str):
        raise BookError(f"{value!r} is not a date column")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BookError(f"{value!r} is not a date") from exc


def encode_optional_date(day: date | None) -> str | None:
    """A date that may be absent, which stays absent rather than becoming one."""
    return None if day is None else encode_date(day)


def decode_optional_date(value: object) -> date | None:
    """A date column that may be null."""
    return None if value is None else decode_date(value)


def encode_enum(member: Enum) -> str:
    """An enumeration member as the value it was declared with."""
    value = member.value
    if not isinstance(value, str):
        raise BookError(f"{member!r} is not stored as text")
    return value


def decode_enum(kind: type[AnEnum], value: object) -> AnEnum:
    """An enumeration member back out of a column."""
    if not isinstance(value, str):
        raise BookError(f"{value!r} is not a {kind.__name__} column")
    try:
        return kind(value)
    except ValueError as exc:
        raise BookError(f"{value!r} is not a {kind.__name__}") from exc


def encode_ident(ident: Ident) -> str:
    """A record number as the string it is written as."""
    return str(ident)


def decode_ident(value: object, expected: Kind | None = None) -> Ident:
    """A record number back out of a column, refusing the wrong kind."""
    if not isinstance(value, str):
        raise BookError(f"{value!r} is not a record number column")
    try:
        return Ident.parse(value, expected)
    except Exception as exc:
        raise BookError(f"{value!r} is not a record number here") from exc


def decode_optional_ident(value: object, expected: Kind | None = None) -> Ident | None:
    """A record number column that may be null."""
    return None if value is None else decode_ident(value, expected)


def encode_bool(flag: bool) -> int:
    """A flag as the zero or one the column holds."""
    return 1 if flag else 0


def decode_bool(value: object) -> bool:
    """A flag back out of a column, refusing anything but zero and one."""
    if value not in (0, 1):
        raise BookError(f"{value!r} is not a flag column")
    return value == 1


def encode_speed(speed: Speed) -> int:
    """A speed as whole miles per hour."""
    return speed.mph


def decode_speed(value: object) -> Speed:
    """A speed back out of a column."""
    if not isinstance(value, int):
        raise BookError(f"{value!r} is not a speed column")
    try:
        return Speed(value)
    except Exception as exc:
        raise BookError(f"{value!r} is not a speed") from exc


def encode_curvature(curve: Curvature) -> int:
    """A curvature as whole minutes."""
    return curve.minutes


def decode_curvature(value: object) -> Curvature:
    """A curvature back out of a column."""
    if not isinstance(value, int):
        raise BookError(f"{value!r} is not a curvature column")
    try:
        return Curvature(value)
    except Exception as exc:
        raise BookError(f"{value!r} is not a curvature") from exc


def encode_tonnage(tonnage: Tonnage) -> int:
    """A tonnage as hundredths of an MGT."""
    return tonnage.hundredths


def decode_tonnage(value: object) -> Tonnage:
    """A tonnage back out of a column."""
    if not isinstance(value, int):
        raise BookError(f"{value!r} is not a tonnage column")
    try:
        return Tonnage(value)
    except Exception as exc:
        raise BookError(f"{value!r} is not a tonnage") from exc


def encode_temperature(reading: Temperature) -> int:
    """A temperature as whole degrees."""
    return reading.degrees


def decode_temperature(value: object) -> Temperature:
    """A temperature back out of a column."""
    if not isinstance(value, int):
        raise BookError(f"{value!r} is not a temperature column")
    try:
        return Temperature(value)
    except Exception as exc:
        raise BookError(f"{value!r} is not a temperature") from exc
