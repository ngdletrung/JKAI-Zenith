"""
Regex DSL — composable Term classes inspired by Outlines.
Allows building patterns programmatically:

    Digit ** 3                    => r'(?:\\d){3}'
    optional("https://") + url    => r"(?:https://)?..."
    either("cat", "dog")          => r"(?:cat|dog)"
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional as OptionalType, Union

__all__ = [
    "Term", "String", "Regex", "Sequence", "Alternatives",
    "KleeneStar", "KleenePlus", "Optional",
    "QuantifyExact", "QuantifyMinimum", "QuantifyMaximum", "QuantifyBetween",
    "to_regex",
    "optional", "one_or_more", "zero_or_more", "either",
    "exactly", "at_least", "at_most", "between",
]


class Term:
    def __add__(self, other: "Term") -> "Sequence":
        if isinstance(other, str):
            other = String(other)
        return Sequence([self, other])

    def __radd__(self, other: "Term") -> "Sequence":
        if isinstance(other, str):
            other = String(other)
        return Sequence([other, self])

    def __or__(self, other: "Term") -> "Alternatives":
        if isinstance(other, str):
            other = String(other)
        return Alternatives([self, other])

    def __ror__(self, other: "Term") -> "Alternatives":
        if isinstance(other, str):
            other = String(other)
        return Alternatives([other, self])

    def __pow__(self, count: int) -> "QuantifyExact":
        return QuantifyExact(self, count)

    def optional(self) -> "Optional":
        return Optional(self)

    def one_or_more(self) -> "KleenePlus":
        return KleenePlus(self)

    def zero_or_more(self) -> "KleeneStar":
        return KleeneStar(self)

    def exactly(self, count: int) -> "QuantifyExact":
        return QuantifyExact(self, count)

    def at_least(self, count: int) -> "QuantifyMinimum":
        return QuantifyMinimum(self, count)

    def at_most(self, count: int) -> "QuantifyMaximum":
        return QuantifyMaximum(self, count)

    def between(self, lo: int, hi: int) -> "QuantifyBetween":
        return QuantifyBetween(self, lo, hi)


@dataclass
class String(Term):
    value: str

    def __repr__(self):
        return f"String({self.value!r})"


@dataclass
class Regex(Term):
    pattern: str

    def __repr__(self):
        return f"Regex({self.pattern!r})"


@dataclass
class Sequence(Term):
    terms: List[Term] = field(default_factory=list)

    def __repr__(self):
        return f"Sequence({self.terms!r})"


@dataclass
class Alternatives(Term):
    terms: List[Term] = field(default_factory=list)

    def __repr__(self):
        return f"Alternatives({self.terms!r})"


@dataclass
class KleeneStar(Term):
    term: Term

    def __repr__(self):
        return f"KleeneStar({self.term!r})"


@dataclass
class KleenePlus(Term):
    term: Term

    def __repr__(self):
        return f"KleenePlus({self.term!r})"


@dataclass
class Optional(Term):
    term: Term

    def __repr__(self):
        return f"Optional({self.term!r})"


@dataclass
class QuantifyExact(Term):
    term: Term
    count: int

    def __repr__(self):
        return f"QuantifyExact({self.term!r}, {self.count})"


@dataclass
class QuantifyMinimum(Term):
    term: Term
    count: int

    def __repr__(self):
        return f"QuantifyMinimum({self.term!r}, {self.count})"


@dataclass
class QuantifyMaximum(Term):
    term: Term
    count: int

    def __repr__(self):
        return f"QuantifyMaximum({self.term!r}, {self.count})"


@dataclass
class QuantifyBetween(Term):
    term: Term
    lo: int
    hi: int

    def __repr__(self):
        return f"QuantifyBetween({self.term!r}, {self.lo}, {self.hi})"


# ── to_regex ──────────────────────────────────────────────────────────

def _wrap(sub: str) -> str:
    """Wrap sub-expression in parens if it contains | or is a sequence."""
    if "|" in sub or len(sub) > 1:
        return f"(?:{sub})"
    return sub


def to_regex(term: Term) -> str:
    if isinstance(term, String):
        return re.escape(term.value)
    if isinstance(term, Regex):
        return f"(?:{term.pattern})"
    if isinstance(term, Sequence):
        return "".join(to_regex(t) for t in term.terms)
    if isinstance(term, Alternatives):
        return "(?:" + "|".join(to_regex(t) for t in term.terms) + ")"
    if isinstance(term, KleeneStar):
        return f"(?:{to_regex(term.term)})*"
    if isinstance(term, KleenePlus):
        return f"(?:{to_regex(term.term)})+"
    if isinstance(term, Optional):
        return f"(?:{to_regex(term.term)})?"
    if isinstance(term, QuantifyExact):
        return f"(?:{to_regex(term.term)}){{{term.count}}}"
    if isinstance(term, QuantifyMinimum):
        return f"(?:{to_regex(term.term)}){{{term.count},}}"
    if isinstance(term, QuantifyMaximum):
        return f"(?:{to_regex(term.term)}){{0,{term.count}}}"
    if isinstance(term, QuantifyBetween):
        return f"(?:{to_regex(term.term)}){{{term.lo},{term.hi}}}"
    raise TypeError(f"Unknown term type: {type(term)}")


# ── Factory functions ─────────────────────────────────────────────────

def optional(term: Union[Term, str]) -> Optional:
    return Optional(String(term) if isinstance(term, str) else term)


def one_or_more(term: Union[Term, str]) -> KleenePlus:
    return KleenePlus(String(term) if isinstance(term, str) else term)


def zero_or_more(term: Union[Term, str]) -> KleeneStar:
    return KleeneStar(String(term) if isinstance(term, str) else term)


def either(*terms: Union[Term, str]) -> Alternatives:
    return Alternatives([
        String(t) if isinstance(t, str) else t for t in terms
    ])


def exactly(count: int, term: Union[Term, str]) -> QuantifyExact:
    return QuantifyExact(String(term) if isinstance(term, str) else term, count)


def at_least(count: int, term: Union[Term, str]) -> QuantifyMinimum:
    return QuantifyMinimum(String(term) if isinstance(term, str) else term, count)


def at_most(count: int, term: Union[Term, str]) -> QuantifyMaximum:
    return QuantifyMaximum(String(term) if isinstance(term, str) else term, count)


def between(lo: int, hi: int, term: Union[Term, str]) -> QuantifyBetween:
    return QuantifyBetween(String(term) if isinstance(term, str) else term, lo, hi)


# ── Pattern helpers using DSL ─────────────────────────────────────────

DIGIT = Regex(r"\d")
WORD_CHAR = Regex(r"\w")
WHITESPACE = Regex(r"\s")
