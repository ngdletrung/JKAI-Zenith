"""
Tests for validator (validator.py). Converted to proper pytest.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils.regex.validator import (
    is_valid_json,
    is_valid_email,
    is_valid_url,
    validate_against_schema,
    validate_json_against_schema,
    matches_any_pattern,
)

from core.utils.regex import URL, EMAIL as EMAIL_PATTERN


# ── is_valid_json ─────────────────────────────────────────────────────
def test_is_valid_json():
    assert is_valid_json('{"a": 1}')
    assert is_valid_json('[1, 2, 3]')
    assert is_valid_json('"hello"')
    assert is_valid_json('42')
    assert not is_valid_json("{broken}")
    assert not is_valid_json("")


# ── is_valid_email ────────────────────────────────────────────────────
def test_is_valid_email():
    assert is_valid_email("user@example.com")
    assert is_valid_email("user@sub.example.com")
    assert not is_valid_email("notanemail")
    assert not is_valid_email("user @example.com")


# ── is_valid_url ──────────────────────────────────────────────────────
def test_is_valid_url():
    assert is_valid_url("https://example.com/path")
    assert is_valid_url("http://example.com")
    assert not is_valid_url("not a url")
    assert not is_valid_url("ftp://example.com")


# ── validate_against_schema ───────────────────────────────────────────
USER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
    },
    "required": ["name", "age"],
}


def test_validate_against_schema():
    assert validate_against_schema({"name": "Alice", "age": 30}, USER_SCHEMA)
    assert not validate_against_schema({"name": "Alice", "age": "thirty"}, USER_SCHEMA)
    assert not validate_against_schema({"name": "Alice"}, USER_SCHEMA)


# ── validate_json_against_schema ──────────────────────────────────────
def test_validate_json_against_schema():
    assert validate_json_against_schema('{"name": "Bob", "age": 25}', USER_SCHEMA)
    assert not validate_json_against_schema('{"name": "Bob", "age": "old"}', USER_SCHEMA)
    assert not validate_json_against_schema("not json", USER_SCHEMA)


# ── matches_any_pattern ───────────────────────────────────────────────
def test_matches_any_pattern():
    patterns = [URL, EMAIL_PATTERN]
    assert matches_any_pattern("visit https://example.com", patterns)
    assert matches_any_pattern("contact user@example.com", patterns)
    assert not matches_any_pattern("hello world", patterns)
