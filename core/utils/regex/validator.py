import json
import re
from typing import Any

__all__ = [
    "is_valid_json", "is_valid_email", "is_valid_url",
    "validate_against_schema", "validate_json_against_schema",
    "matches_any_pattern",
]

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def is_valid_email(text: str) -> bool:
    return bool(re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+$", text))


def is_valid_url(text: str) -> bool:
    return bool(re.match(r"https?://[^\s]+", text, re.IGNORECASE))


def validate_against_schema(
    instance: Any, schema: dict, raise_on_error: bool = False
) -> bool:
    if not HAS_JSONSCHEMA:
        return True
    try:
        jsonschema.validate(instance, schema)
        return True
    except jsonschema.ValidationError:
        if raise_on_error:
            raise
        return False


def validate_json_against_schema(
    json_str: str, schema: dict, raise_on_error: bool = False
) -> bool:
    try:
        instance = json.loads(json_str)
    except json.JSONDecodeError:
        if raise_on_error:
            raise
        return False
    return validate_against_schema(instance, schema, raise_on_error)


def matches_any_pattern(text: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(text) for p in patterns)
