"""
Tests for regex DSL (dsl.py). Converted to proper pytest.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils.regex.dsl import (
    String, Regex, Sequence, Alternatives,
    KleeneStar, KleenePlus, Optional,
    QuantifyExact, QuantifyMinimum, QuantifyMaximum, QuantifyBetween,
    to_regex,
    optional, one_or_more, zero_or_more, either,
    exactly, at_least, at_most, between,
    DIGIT, WORD_CHAR,
)


# ── String ────────────────────────────────────────────────────────────
def test_string_renders_escaped():
    assert to_regex(String("hello.")) == re.escape("hello.")
    assert to_regex(String("a") + String("b")) == f"{re.escape('a')}{re.escape('b')}"


# ── Regex ─────────────────────────────────────────────────────────────
def test_regex_wraps_pattern():
    assert to_regex(Regex(r"\d+")) == r"(?:\d+)"


# ── Sequence ──────────────────────────────────────────────────────────
def test_sequence_concatenates():
    assert to_regex(Sequence([String("a"), String("b")])) == re.escape("a") + re.escape("b")


# ── Alternatives ──────────────────────────────────────────────────────
def test_alternatives_pipes():
    assert to_regex(Alternatives([String("cat"), String("dog")])) == r"(?:cat|dog)"


# ── Quantifiers ───────────────────────────────────────────────────────
def test_quantifiers():
    assert to_regex(KleeneStar(String("a"))) == r"(?:a)*"
    assert to_regex(KleenePlus(String("a"))) == r"(?:a)+"
    assert to_regex(Optional(String("a"))) == r"(?:a)?"
    assert to_regex(QuantifyExact(String("a"), 3)) == r"(?:a){3}"
    assert to_regex(QuantifyMinimum(String("a"), 2)) == r"(?:a){2,}"
    assert to_regex(QuantifyMaximum(String("a"), 5)) == r"(?:a){0,5}"
    assert to_regex(QuantifyBetween(String("a"), 2, 5)) == r"(?:a){2,5}"


# ── Operator overloads ────────────────────────────────────────────────
def test_operator_overloads():
    assert to_regex(String("a") + "b") == re.escape("a") + re.escape("b")
    assert to_regex(String("a") | "b") == r"(?:a|b)"
    assert to_regex(String("a") ** 3) == r"(?:a){3}"


# ── Factory functions ─────────────────────────────────────────────────
def test_factory_functions():
    assert to_regex(optional("a")) == r"(?:a)?"
    assert to_regex(one_or_more("a")) == r"(?:a)+"
    assert to_regex(zero_or_more("a")) == r"(?:a)*"
    assert to_regex(either("cat", "dog")) == r"(?:cat|dog)"
    assert to_regex(exactly(3, "a")) == r"(?:a){3}"
    assert to_regex(at_least(2, "a")) == r"(?:a){2,}"
    assert to_regex(at_most(5, "a")) == r"(?:a){0,5}"
    assert to_regex(between(2, 5, "a")) == r"(?:a){2,5}"


# ── DSL composition ───────────────────────────────────────────────────
def test_phone_pattern():
    phone_pattern = to_regex(optional("0") + exactly(9, DIGIT))
    assert bool(re.fullmatch(phone_pattern, "0912345678"))
    assert not re.fullmatch(phone_pattern, "123")


def test_word_pattern():
    wp = to_regex(one_or_more(WORD_CHAR))
    assert bool(re.fullmatch(wp, "hello"))
    assert not re.fullmatch(wp, "")


def test_choice_pattern():
    cp = to_regex(either("yes", "no"))
    assert bool(re.fullmatch(cp, "yes"))
    assert bool(re.fullmatch(cp, "no"))
    assert not re.fullmatch(cp, "maybe")


# ── Term methods ──────────────────────────────────────────────────────
def test_term_methods():
    assert to_regex(String("a").optional()) == r"(?:a)?"
    assert to_regex(String("a").one_or_more()) == r"(?:a)+"
    assert to_regex(String("a").zero_or_more()) == r"(?:a)*"
    assert to_regex(String("a").exactly(3)) == r"(?:a){3}"
    assert to_regex(String("a").at_least(2)) == r"(?:a){2,}"
    assert to_regex(String("a").at_most(5)) == r"(?:a){0,5}"
    assert to_regex(String("a").between(2, 5)) == r"(?:a){2,5}"
