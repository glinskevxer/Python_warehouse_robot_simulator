"""Columns to quantities and back, and every decode refusing rubbish."""

from __future__ import annotations

from datetime import date

import pytest

from spikemaul.errors import BookError
from spikemaul.model.ids import Ident, Kind
from spikemaul.model.inspection import Method
from spikemaul.store.codec import (
    decode_bool,
    decode_curvature,
    decode_date,
    decode_enum,
    decode_ident,
    decode_inches,
    decode_optional_date,
    decode_optional_ident,
    decode_post,
    decode_span,
    decode_speed,
    decode_temperature,
    decode_tonnage,
    encode_bool,
    encode_curvature,
    encode_date,
    encode_enum,
    encode_ident,
    encode_inches,
    encode_optional_date,
    encode_post,
    encode_span,
    encode_speed,
    encode_temperature,
    encode_tonnage,
)
from spikemaul.units.curvature import Curvature
from spikemaul.units.measure import Inches
from spikemaul.units.milepost import Milepost
from spikemaul.units.span import Span
from spikemaul.units.speed import Speed
from spikemaul.units.temperature import Temperature
from spikemaul.units.tonnage import Tonnage


def test_a_milepost_goes_out_as_hundredths_and_comes_back() -> None:
    post = Milepost.parse("43.20")
    assert encode_post(post) == 4320
    assert decode_post(encode_post(post)) == post


def test_a_span_is_two_columns() -> None:
    span = Span.parse("13.00-13.60")
    assert encode_span(span) == (1300, 1360)
    assert decode_span(*encode_span(span)) == span


def test_a_measurement_goes_out_as_sixteenths() -> None:
    reading = Inches.parse("56 5/8")
    assert encode_inches(reading) == 906
    assert decode_inches(encode_inches(reading)) == reading


def test_a_date_goes_out_as_an_iso_string() -> None:
    assert encode_date(date(2025, 5, 6)) == "2025-05-06"
    assert decode_date("2025-05-06") == date(2025, 5, 6)


def test_a_date_that_may_be_absent_stays_absent() -> None:
    assert encode_optional_date(None) is None
    assert decode_optional_date(None) is None
    assert decode_optional_date(encode_optional_date(date(2025, 5, 6))) == date(2025, 5, 6)


def test_an_enumeration_goes_out_as_its_value() -> None:
    assert encode_enum(Method.HI_RAIL) == "hi rail"
    assert decode_enum(Method, "hi rail") == Method.HI_RAIL


def test_a_record_number_goes_out_as_it_is_written() -> None:
    ident = Ident.numbered(Kind.DEFECT, 2025, 142)
    assert encode_ident(ident) == "DF-2025-0142"
    assert decode_ident("DF-2025-0142", Kind.DEFECT) == ident
    assert decode_optional_ident(None) is None


def test_the_other_quantities_round_trip() -> None:
    assert decode_speed(encode_speed(Speed(25))) == Speed(25)
    assert decode_curvature(encode_curvature(Curvature.of(3, 30))) == Curvature.of(3, 30)
    assert decode_tonnage(encode_tonnage(Tonnage.of("12.40"))) == Tonnage.of("12.40")
    assert decode_temperature(encode_temperature(Temperature(95))) == Temperature(95)
    assert decode_bool(encode_bool(True)) is True
    assert decode_bool(encode_bool(False)) is False


@pytest.mark.parametrize(
    ("decoder", "value"),
    [
        (decode_post, "43.20"),
        (decode_post, -1),
        (decode_inches, "1/2"),
        (decode_date, 20250506),
        (decode_date, "the sixth"),
        (decode_ident, 142),
        (decode_ident, "not a number"),
        (decode_bool, 2),
        (decode_speed, "25 mph"),
        (decode_speed, 300),
        (decode_curvature, "3-30"),
        (decode_curvature, -5),
        (decode_tonnage, "12.40"),
        (decode_tonnage, -1),
        (decode_temperature, "95F"),
        (decode_temperature, 900),
    ],
)
def test_a_column_that_is_not_what_it_should_be_is_refused(decoder: object, value: object) -> None:
    with pytest.raises(BookError):
        decoder(value)  # type: ignore[operator]


def test_a_span_out_of_two_bad_columns_is_refused() -> None:
    with pytest.raises(BookError, match="is not a milepost column"):
        decode_span("13.00", 1360)
    with pytest.raises(BookError, match="is not a span"):
        decode_span(1360, 1300)


def test_an_enumeration_value_this_version_does_not_know_is_refused() -> None:
    with pytest.raises(BookError, match="is not a Method"):
        decode_enum(Method, "drone")
    with pytest.raises(BookError, match="is not a Method column"):
        decode_enum(Method, 4)


def test_a_number_of_the_wrong_kind_in_a_column_is_refused() -> None:
    with pytest.raises(BookError, match="not a record number here"):
        decode_ident("DF-2025-0142", Kind.ORDER)
