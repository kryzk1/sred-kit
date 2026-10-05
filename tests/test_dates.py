from datetime import datetime, timezone

import pytest

from sredlib.dates import iso, parse_datetime, parse_iso

UTC = timezone.utc


def test_iso_roundtrip_and_offsets():
    assert parse_iso("2026-09-01T10:00:00Z") == datetime(2026, 9, 1, 10, tzinfo=UTC)
    assert parse_iso("2026-09-01T12:00:00.000+0200") == datetime(2026, 9, 1, 10, tzinfo=UTC)
    assert iso(datetime(2026, 9, 1, 10, tzinfo=UTC)) == "2026-09-01T10:00:00Z"


def test_parse_formats_in_order():
    assert parse_datetime("Fri Sep 27 2024 22:10:24 GMT+0000 (GMT+00:00)", ["js"]) == datetime(2024, 9, 27, 22, 10, 24, tzinfo=UTC)
    assert parse_datetime("07/Mar/26 2:15 PM", ["iso", "%d/%b/%y %I:%M %p"]) == datetime(2026, 3, 7, 14, 15, tzinfo=UTC)
    assert parse_datetime("1767225600000", ["epoch_ms"]) == datetime(2026, 1, 1, tzinfo=UTC)
    assert parse_datetime("", ["iso"]) is None


def test_parse_failure_names_value():
    with pytest.raises(ValueError, match="nonsense"):
        parse_datetime("nonsense", ["iso"])
