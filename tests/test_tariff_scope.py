"""Tests for parsing HTS codes out of official tariff list text."""

from src.ingest.tariff_scope import parse_codes


def test_parse_codes_levels_and_chapter_99_dropped():
    text = "9903.81.90 covers 7301.20.10 and 7326.90.86.70; heading 8708.29 and 7616.99.51.60."
    assert parse_codes(text) == {
        ("73012010", 8),
        ("7326908670", 10),
        ("870829", 6),
        ("7616995160", 10),
    }


def test_parse_codes_ignores_longer_numbers():
    assert parse_codes("value 12345.67.89 and 1.2208.10.00") == set()
