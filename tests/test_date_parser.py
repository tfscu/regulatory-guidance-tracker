from datetime import date, datetime

from app.normalizers.dates import parse_date


def test_parse_date_accepts_common_formats():
    assert parse_date("2026-06-18") == date(2026, 6, 18)
    assert parse_date("20260618") == date(2026, 6, 18)
    assert parse_date("06/18/2026") == date(2026, 6, 18)
    assert parse_date("18/06/2026") == date(2026, 6, 18)
    assert parse_date("June 18, 2026") == date(2026, 6, 18)
    assert parse_date("18 Jun 2026") == date(2026, 6, 18)


def test_parse_date_handles_empty_invalid_and_datetime_values():
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("not a date") is None
    assert parse_date(datetime(2026, 6, 18, 9, 30)) == date(2026, 6, 18)
