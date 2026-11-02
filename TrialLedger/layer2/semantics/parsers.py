"""Literal-expression parsers: numbers, comparators, units, durations, time windows, intervals and
reference expressions at a supplied position in the original text.

These local encoders preserve literal readings and spans. They do not resolve clinical subject, force or
scope, and are not an automatic source-to-assertion compiler.

Each reader takes the criterion's text and a position, skips whitespace, and reads one expression there, as
written, into a `Parse`: its kind, its status (`parsed`, one reading; `ambiguous`, every reading the words
allow, none chosen; `abstained`, no reading, with its note), its readings (each a tuple of named fields, every
value a string as written or normalised, never a float, a bool or NaN), its evidence spans (half-open on the
original text, `contracts.Span`) and the position it ends at. Nothing is unescaped first: the API's escaped
forms ("=\\<", "\\>=", "\\^", "\\~") are read where they stand, so a span covers its backslash.

What is read, and what never is:
- A number: digits, with a decimal point or grouping marks, or a written form (zero to ninety-nine). A mark
  that may be a grouping mark or a decimal mark ("50,000", "1.500") is ambiguous; a comma between digits
  that cannot be grouping ("0,1": a decimal comma or a list) is abstained. A sign is read only where no digit
  stands before it, so "0-1" is a range, never minus one; digits inside a name ("PD-L1", "CTLA-4", "B12")
  are not.
- A comparator: <, <=, >, >=, =, ≤, ≥, the API's escaped forms and the word forms, normalised to <, ≤, >, ≥
  or =; the longest form wins ("less than or equal to" is ≤); a strict sign never reads the start of a form
  the table does not hold ("> =" is abstained, never >). A caller reads a comparator from its phrase's head.
- A unit: the UCUM form where one exists (UNITS, each mapped form a valid UCUM code; UCUM's edition is not
  pinned in `provenance.CONCEPT_AUTHORITIES`, so none is cited), the unit as written always kept; a unit with
  no UCUM form here ("half-lives", "mL/min/1.73 m2", a slash compound of unit symbols the table does not hold)
  is kept as written and named unmapped, never dropped or guessed. A pair of words ("AST/ALT") is no unit, nor
  is a power of ten written with neither its sign nor a superscript ("109/L"). A reference expression is
  never a unit.
- A reference expression: an optional factor, then ×, x, * or "times", then ULN or LLN in any of their forms
  ("the institutional upper limit of normal"). Its span has the role `reference`, which the contract's span
  roles do not yet hold (contracts.SPAN_ROLES; named for its owner). A reference with no factor written ("≤
  ULN") has the factor "", never 1; one with a factor after it ("ULN x 2.5") is abstained. A form not held
  here ("ULRR", "upper limit of institutional normal", "2.5-fold ULN") is no reference, and the number before
  it is no bound.
- A duration: a number then a unit of time.
- An event-anchored time window: "within", "in the last", "during the past" or a
  comparator, a duration, and an orientation (before, prior to, preceding, ago; after, following; after a
  marker, "of" and "from" leave it unspecified) with its anchor kept as written, or "unresolved" when none is
  written (never the enrollment). "Within N" bounds the time by N, its inclusivity unspecified; a comparator
  gives its own ("at least N before" is N, inclusive). A duration with a direction (before or after) and no
  marker ("4 weeks prior to randomization") is ambiguous: within N, or at least N. A duration with neither
  ("life expectancy ≥ 12 weeks") is no window, and one on both sides of its anchor ("before or after") is
  abstained.
- An interval: a comparator and a bound (one-sided; the comparator's inclusivity), two comparators on two
  sides (explicit), a range ("18 to 75 years", "0-1", "0\\~1", "between 18 and 75") whose inclusivity is
  unspecified unless "inclusive" or "exclusive" is written, or a bound with "or more", "or older", "or less".
  A unit or reference written once is the range's; two different ones are abstained. A number followed by a
  factor or digits not read is no bound: a unit or reference is written there, unread.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from TrialLedger.layer2.semantics.contracts import Span

STATUSES = ("parsed", "ambiguous", "abstained")
KINDS = ("number", "comparator", "unit", "reference", "duration", "window", "interval")
# The span roles a parse gives: the contract's, and `reference`, which the contract does not yet hold.
PARSE_ROLES = ("value", "comparator", "unit", "reference", "window", "qualifier")
INCLUSIVITY = ("inclusive", "exclusive", "unspecified")

Fields = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Parse:
    kind: str
    status: str
    readings: tuple[Fields, ...]  # one when parsed, two or more when ambiguous, none when abstained
    spans: tuple[Span, ...]
    end: int  # where the expression ends in the text; the position given when abstained
    note: str  # why ambiguous or abstained; "" when parsed


def _abstained(kind: str, start: int, note: str) -> Parse:
    return Parse(kind, "abstained", (), (), start, note)


def _parse(kind: str, readings: Sequence[Fields], spans: Sequence[Span], end: int, note: str) -> Parse:
    single = len(readings) == 1
    return Parse(
        kind, "parsed" if single else "ambiguous", tuple(readings), tuple(spans), end, "" if single else note
    )


_SPACE = re.compile(r"\s*")


def _skip(text: str, start: int) -> int:
    return _SPACE.match(text, start).end()  # ty: ignore[unresolved-attribute]


def _inside(text: str, start: int) -> bool:
    return 0 <= start <= len(text)


# ── numbers ─────────────────────────────────────────────────────────────────────────────────────────

_SMALL = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven")
_SMALL += ("twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
_TENS = ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_BY_LENGTH = sorted(_SMALL, key=len, reverse=True)
# A fraction written with a number word ("one-third", "two-thirds") is no whole number: never read as one.
_FRACTION = r"-(?:thirds?|half|halves|quarters?|fourths?|fifths?|sixths?|sevenths?|eighths?|ninths?|tenths?)"
# ASCII only: case-insensitive matching would fold "ı" onto "i" and "ſ" onto "s". A tens word alone before a
# hyphen and a word ("twenty-something") is no number.
_WORD_NUMBER = re.compile(
    rf"(?ai:(?P<tens>{'|'.join(_TENS)})(?:[- ](?P<ones>{'|'.join(_SMALL[9:0:-1])})(?![a-z])(?!{_FRACTION})"
    rf"|(?![a-z]|-[a-z]))|(?P<small>{'|'.join(_BY_LENGTH)})(?![a-z])(?!{_FRACTION}))"
)
_DIGITS = re.compile(r"(?P<sign>[-−])?(?P<digits>\d+(?:[.,]\d+)*)")
_IN_A_NAME = re.compile(r"[A-Za-z]-?$")
_DIGIT_BEFORE = re.compile(r"\d\s*$")


def _grouping(groups: list[str]) -> bool:
    """Whether digit groups are a thousands grouping: a lead of 1-3 digits, not starting with 0, then 3s."""
    return 1 <= len(groups[0]) <= 3 and groups[0][0] != "0" and all(len(group) == 3 for group in groups[1:])


def _number_values(digits: str) -> tuple[tuple[str, ...], str]:
    """The values digits with marks may have (one, or two when the marks allow both), or none with a note."""
    marks = [char for char in digits if char in ".,"]
    groups = re.split(r"[.,]", digits)
    if not marks:
        return (digits,), ""
    if len(set(marks)) == 2:
        if marks.count(marks[-1]) == 1 and _grouping(groups[:-1]):
            return ("".join(groups[:-1]) + "." + groups[-1],), ""
        return (), "marks that are neither a grouping nor one decimal mark"
    if len(marks) > 1:
        return (("".join(groups),), "") if _grouping(groups) else ((), "marks that are no grouping")
    if _grouping(groups):
        return ("".join(groups), groups[0] + "." + groups[1]), "a grouping mark or a decimal mark"
    if marks[0] == ".":
        return (groups[0] + "." + groups[1],), ""
    return (), "a comma between digits: a decimal comma or a list"


def read_number(text: str, start: int) -> Parse:
    """The number at text[start:], after whitespace, as written (pure — pinned).

    Digits ("45", "8.0", "100,000", "1,234.5"), signed where no digit stands before the sign ("≥ -2"), or a
    written form, zero to ninety-nine ("six", "twenty-four"). Each reading: value (digits with "." as the
    decimal mark and no grouping, as written otherwise: "8.0" stays "8.0") and as_written; one span, value.
    Ambiguous: one mark followed by three digits after a lead of 1-3 digits ("50,000": 50000 or 50.000;
    "1.500"). Abstained: no number there, digits inside a name ("PD-L1", "CTLA-4", "B12"), a comma between
    digits that is no grouping ("0,1": a decimal comma or a list), marks that are no grouping, a fraction
    ("one-third"), a tens word before a hyphenated word ("twenty-something"), a number word in other than
    ASCII letters ("fıve"), or a start outside the text. Never a float, a bool or NaN.
    """
    if not _inside(text, start):
        return _abstained("number", start, "a start outside the text")
    pos = _skip(text, start)
    if _IN_A_NAME.search(text, 0, pos):
        return _abstained("number", start, "inside a name")
    word = _WORD_NUMBER.match(text, pos)
    if word:
        small, tens, ones = word.group("small"), word.group("tens"), word.group("ones")
        if small:
            value = _SMALL.index(small.lower())
        else:
            value = 10 * (_TENS.index(tens.lower()) + 2) + (_SMALL.index(ones.lower()) if ones else 0)
        fields = (("value", str(value)), ("as_written", word.group(0)))
        return _parse("number", [fields], [Span("value", pos, word.end())], word.end(), "")
    found = _DIGITS.match(text, pos)
    if not found:
        return _abstained("number", start, "no number")
    sign = found.group("sign")
    if sign and _DIGIT_BEFORE.search(text, 0, pos):
        return _abstained("number", start, "a dash after a digit: a range, not a sign")
    values, note = _number_values(found.group("digits"))
    if not values:
        return _abstained("number", start, note)
    readings = [
        (("value", ("-" if sign else "") + value), ("as_written", found.group(0))) for value in values
    ]
    return _parse("number", readings, [Span("value", pos, found.end())], found.end(), note)


# ── comparators ─────────────────────────────────────────────────────────────────────────────────────

COMPARATORS = {
    "≥": "≥",
    ">=": "≥",
    "=>": "≥",
    "\\>=": "≥",
    "=\\>": "≥",
    ">/=": "≥",
    "\\>/=": "≥",
    "> or =": "≥",
    "\\> or =": "≥",
    ">or=": "≥",
    "\\>or=": "≥",
    "greater than or equal to": "≥",
    "more than or equal to": "≥",
    "equal to or greater than": "≥",
    "at least": "≥",
    "no less than": "≥",
    "not less than": "≥",
    "no fewer than": "≥",
    "not fewer than": "≥",
    "≤": "≤",
    "<=": "≤",
    "=<": "≤",
    "\\<=": "≤",
    "=\\<": "≤",
    "</=": "≤",
    "\\</=": "≤",
    "< or =": "≤",
    "\\< or =": "≤",
    "<or=": "≤",
    "\\<or=": "≤",
    "less than or equal to": "≤",
    "equal to or less than": "≤",
    "at most": "≤",
    "no more than": "≤",
    "not more than": "≤",
    "no greater than": "≤",
    "not greater than": "≤",
    "not exceeding": "≤",
    "up to": "≤",
    ">": ">",
    "\\>": ">",
    "greater than": ">",
    "more than": ">",
    "higher than": ">",
    "older than": ">",
    "above": ">",
    "over": ">",
    "exceeding": ">",
    "<": "<",
    "\\<": "<",
    "less than": "<",
    "fewer than": "<",
    "lower than": "<",
    "younger than": "<",
    "below": "<",
    "under": "<",
    "=": "=",
    "equal to": "=",
    "equals": "=",
}


# A strict sign or "=" never reads the start of a two-symbol form the table does not hold ("> =", "< /=",
# "= <"): the words state ≥, ≤ or a sign not read here, never the strict one.
_UNHELD_AFTER = {
    ">": r"(?!\s*(?:(?i:or)\s*)?/?\s*=)",
    "<": r"(?!\s*(?:(?i:or)\s*)?/?\s*=)",
    "=": r"(?!\s*\\?[<>])",
}


def _form_pattern(form: str) -> str:
    pattern = r"\s+".join(re.escape(part) for part in form.split(" "))
    if form[-1].isalpha():
        return pattern + r"(?![A-Za-z])"
    return pattern + _UNHELD_AFTER.get(form.lstrip("\\"), "")


# Each form its own group, the longest first: the sign is the matched form's, never the matched text looked
# up again (case-insensitive matching folds "ſ" onto "s" and "ı" onto "i", which no lower-casing undoes).
_COMPARATOR_FORMS = tuple(sorted(COMPARATORS, key=len, reverse=True))
_COMPARATOR = re.compile(
    "|".join(f"(?P<c{i}>{_form_pattern(form)})" for i, form in enumerate(_COMPARATOR_FORMS)), re.IGNORECASE
)


def read_comparator(text: str, start: int) -> Parse:
    """The comparator at text[start:], after whitespace (pure — pinned).

    A symbol (<, <=, >, >=, =, ≤, ≥, "=<", ">/="), the API's escaped forms ("\\<", "\\>=", "=\\<") or a word
    form in any case ("at least", "no more than", "less than or equal to", "up to", "over"); the longest form
    at the position wins (">or=" is ≥). One reading: sign (<, ≤, >, ≥ or =) and as_written; one span,
    comparator. No form there, a word form that runs on into a longer word ("overall"), a strict sign or "="
    at the start of a two-symbol form the table does not hold ("> =", "< /=", "= <"), or a start outside the
    text: abstained. A form is read where it is given: a caller starts at the phrase's head, since "more than"
    read inside "not more than" is the shorter form.
    """
    if not _inside(text, start):
        return _abstained("comparator", start, "a start outside the text")
    pos = _skip(text, start)
    found = _COMPARATOR.match(text, pos)
    if not found:
        return _abstained("comparator", start, "no comparator")
    sign = COMPARATORS[_COMPARATOR_FORMS[int(str(found.lastgroup)[1:])]]
    fields = (("sign", sign), ("as_written", found.group(0)))
    return _parse("comparator", [fields], [Span("comparator", pos, found.end())], found.end(), "")


# ── units and reference expressions ─────────────────────────────────────────────────────────────────

_CUBED = r"(?:3|³|\^3|\\\^3)"
_SQUARED = r"(?:2|²|\^2|\\\^2)"
_MICRO = r"(?:µ|μ|u|mc)"
# A power of ten is written with its sign ("10^9", "10\\^9", "10e9") or a superscript ("10⁹"); digits run on
# ("109/L", a superscript lost in the text) state no power and are not read as one.
_POWER = r"(?:[×xX*]\s*)?10(?:\s*(?:\^|\\\^)\s*|[eE])"
# (pattern as written, UCUM code or "" when unmapped, dimension). Each mapped code is a UCUM expression.
UNITS: tuple[tuple[str, str, str], ...] = (
    (rf"(?:{_POWER}9|(?:[×xX*]\s*)?10⁹)\s*/\s*L", "10*9/L", "other"),
    (rf"(?:{_POWER}12|(?:[×xX*]\s*)?10¹²)\s*/\s*L", "10*12/L", "other"),
    (rf"(?:{_POWER}3|(?:[×xX*]\s*)?10³)\s*/\s*{_MICRO}L", "10*3/uL", "other"),
    (rf"m[lL]\s*/\s*min\s*/\s*1\.73\s*m{_SQUARED}", "", "other"),
    (rf"cells\s*/\s*mm{_CUBED}", "{cells}/mm3", "other"),
    (rf"cells\s*/\s*{_MICRO}L", "{cells}/uL", "other"),
    (rf"/\s*mm{_CUBED}", "/mm3", "other"),
    (rf"/\s*{_MICRO}L", "/uL", "other"),
    (r"m[lL]\s*/\s*min", "mL/min", "other"),
    (r"mg\s*/\s*d[lL]", "mg/dL", "other"),
    (r"g\s*/\s*d[lL]", "g/dL", "other"),
    (r"g\s*/\s*L", "g/L", "other"),
    (rf"{_MICRO}mol\s*/\s*L", "umol/L", "other"),
    (r"mmol\s*/\s*L", "mmol/L", "other"),
    (r"mEq\s*/\s*L", "meq/L", "other"),
    (r"(?:IU|iu)\s*/\s*L", "[IU]/L", "other"),
    (r"U\s*/\s*L", "U/L", "other"),
    (r"ng\s*/\s*m[lL]", "ng/mL", "other"),
    (r"pg\s*/\s*m[lL]", "pg/mL", "other"),
    (rf"kg\s*/\s*m{_SQUARED}", "kg/m2", "other"),
    (rf"mg\s*/\s*m{_SQUARED}", "mg/m2", "other"),
    (r"mg\s*/\s*kg", "mg/kg", "other"),
    (r"mm\s*Hg|mmHg", "mm[Hg]", "other"),
    (r"%", "%", "other"),
    (r"kg", "kg", "other"),
    (r"cm", "cm", "other"),
    (r"mm", "mm", "other"),
    (r"ms(?:ec)?", "ms", "other"),
    (r"mg", "mg", "other"),
    (rf"{_MICRO}g", "ug", "other"),
    (r"(?i:years?|yrs?)", "a", "time"),
    (r"(?i:months?|mos?)", "mo", "time"),
    (r"(?i:weeks?|wks?)", "wk", "time"),
    (r"(?i:days?)", "d", "time"),
    (r"(?i:hours?|hrs?)|h", "h", "time"),  # "h" lower case only: "H. pylori" is no hour
    (r"(?i:minutes?|mins?)", "min", "time"),
    (r"(?i:half[- ]li(?:ves|fe))", "", "time"),
    (r"(?i:pack[- ]years?)", "", "other"),
    (r"(?i:cycles?)", "", "other"),
)
_UNIT = re.compile(
    "(?:"
    + "|".join(f"(?P<u{i}>{pattern})" for i, (pattern, _, _) in enumerate(UNITS))
    + r")(?![A-Za-zµμ0-9/^²³])"
)
# A slash compound the table does not hold ("G/L", "IU/dL", "copies/mL"): a unit as written, unmapped. Each
# of its parts is a unit symbol from a closed set (an SI prefix and a base, a power after it, a counted thing,
# a unit of time, or "G" as written), the parts after a slash optionally after a number ("/1.73 m2", "/24 h"),
# so a pair of words ("and/or", "AST/ALT", "Male/female", "inclusion/exclusion") is never a unit.
_ATOM = (
    r"(?:(?:mc|[pnuµμmcdkMG])?(?:g|L|l|mol|eq|Eq|IU|U|m|s)(?:(?:\\?\^)?[23]|[²³])?"
    r"|min|hr|h|day|d|wk|week|cells|copies|G)"
)
_COMPOUND = re.compile(
    rf"{_ATOM}(?:[^\S\r\n]*/[^\S\r\n]*(?:\d+(?:\.\d+)?[^\S\r\n]?)?{_ATOM})+(?![A-Za-zµμ0-9/])"
)
_REFERENCE = re.compile(
    r"(?P<op>[×xX*]|(?i:times))?\s*(?:(?i:the)\s+)?(?:(?i:institutional|site|local)\s+)?"
    r"(?:(?P<upper>I?ULN|(?i:upper\s+limits?\s+of\s+(?:the\s+)?normal(?:\s+range)?|upper\s+normal\s+limit))"
    r"|(?P<lower>LLN|(?i:lower\s+limits?\s+of\s+(?:the\s+)?normal(?:\s+range)?|lower\s+normal\s+limit)))"
    r"(?![A-Za-z])"
)
# Horizontal whitespace only: a bullet "*" on the next line multiplies nothing.
_TIMES = r"[^\S\r\n]*(?:[×*]|[xX](?![A-Za-z])|(?i:times|-?fold)(?![A-Za-z]))"
_FACTOR_AFTER_REFERENCE = re.compile(rf"{_TIMES}[^\S\r\n]*\d")
FACTOR_AFTER = "a factor written after the reference: not read"


def read_unit(text: str, start: int) -> Parse:
    """The unit at text[start:], after whitespace (pure — pinned).

    A unit of UNITS (the longest written form at the position; "× 10^9/L", "mg/dl", "/mm\\^3", "%", "weeks"),
    or a slash compound of unit symbols the table does not hold ("G/L", "IU/dL"). One reading: as_written,
    ucum (its UCUM form, "" when it has none), mapping ("ucum", or "unmapped": kept as written, never
    dropped or guessed) and dimension ("time", "other", or "unknown" for a compound the table does not hold);
    one span, unit. Abstained: a reference expression ("× ULN", "x ULN", "times the upper limit of normal": a
    reference, never a unit), no unit there (a pair of words, "AST/ALT"; "109/L", a power of ten whose sign
    or superscript is not written; "H" in capitals), or a start outside the text.
    """
    if not _inside(text, start):
        return _abstained("unit", start, "a start outside the text")
    pos = _skip(text, start)
    if _REFERENCE.match(text, pos):
        return _abstained("unit", start, "a reference expression, never a unit")
    found = _UNIT.match(text, pos)
    if found:
        ucum, dimension = next(
            (u, d) for i, (_, u, d) in enumerate(UNITS) if found.group(f"u{i}") is not None
        )
    else:
        found = _COMPOUND.match(text, pos)
        ucum, dimension = "", "unknown"
    if not found:
        return _abstained("unit", start, "no unit")
    fields = (
        ("as_written", found.group(0)),
        ("ucum", ucum),
        ("mapping", "ucum" if ucum else "unmapped"),
        ("dimension", dimension),
    )
    return _parse("unit", [fields], [Span("unit", pos, found.end())], found.end(), "")


def read_reference(text: str, start: int) -> Parse:
    """The reference expression at text[start:], after whitespace (pure — pinned).

    An optional factor (a number), then ×, x, *, "times" or nothing, then the upper or lower limit of normal
    in any of its forms (ULN, IULN, LLN, "the institutional upper limit of normal", "upper normal limit"):
    "2.5×ULN", "3 x ULN", "1.5 × ULN", "≤ ULN" read at "ULN". Each reading: factor (the number's value, ""
    when none is written, never 1), reference (ULN or LLN) and as_written (the reference's words); spans:
    value (the factor's) and reference. Ambiguous when the factor is ("1,500 × ULN"). Abstained: no reference
    after the number or at the position, a factor that is abstained, a factor written after the reference
    ("ULN x 2.5": FACTOR_AFTER, not read, never read as no factor), or a start outside the text.
    """
    if not _inside(text, start):
        return _abstained("reference", start, "a start outside the text")
    pos = _skip(text, start)
    number = read_number(text, pos)
    after = _skip(text, number.end)
    found = _REFERENCE.match(text, after)
    if not found:
        return _abstained("reference", start, "no reference expression")
    if _FACTOR_AFTER_REFERENCE.match(text, found.end()):
        return _abstained("reference", start, FACTOR_AFTER)
    reference = "ULN" if found.group("upper") else "LLN"
    words = (("reference", reference), ("as_written", found.group(0)))
    factors = [dict(reading)["value"] for reading in number.readings] or [""]
    readings: list[Fields] = [(("factor", factor), *words) for factor in factors]
    spans = [*number.spans, Span("reference", found.start(), found.end())]
    return _parse("reference", readings, spans, found.end(), number.note)


# ── durations and time windows ──────────────────────────────────────────────────────────────────────


def read_duration(text: str, start: int) -> Parse:
    """The duration at text[start:]: a number then a unit of time (pure — pinned).

    "30 days", "six months", "12 weeks", "5 half-lives" (time, no UCUM form: unmapped). Each reading: value,
    unit (as written), ucum, mapping; spans: value and unit. Ambiguous when the number is. Abstained: no
    number, a number with no unit of time after it ("18 lines", "45 mL/min"), or a start outside the text.
    """
    number = read_number(text, start)
    if number.status == "abstained":
        return _abstained("duration", start, number.note)
    unit = read_unit(text, number.end + 1 if text[number.end : number.end + 1] == "-" else number.end)
    if unit.status == "abstained" or dict(unit.readings[0])["dimension"] != "time":
        return _abstained("duration", start, "no unit of time after the number")
    written = dict(unit.readings[0])
    tail = (("unit", written["as_written"]), ("ucum", written["ucum"]), ("mapping", written["mapping"]))
    readings: list[Fields] = [(("value", dict(reading)["value"]), *tail) for reading in number.readings]
    return _parse("duration", readings, [*number.spans, *unit.spans], unit.end, number.note)


_WINDOW_MARK = re.compile(
    r"(?i:within(?:\s+the)?(?P<past1>\s+(?:last|past|previous|preceding|prior))?"
    r"|(?:in|during)\s+the(?P<past2>\s+(?:last|past|previous|preceding)))(?![A-Za-z])"
)
_ORIENTATION = re.compile(
    r"(?i:(?P<before>before|prior\s+to|prior|preceding|ago)|(?P<after>after|following)|(?P<either>of|from))"
    r"(?![A-Za-z])"
)
# A clause word ends the anchor wherever it stands, its first word included ("before or after ...").
_ANCHOR_END = re.compile(
    r"[.;,:()\[\]\n]|(?<![A-Za-z])(?i:is|are|was|were|will|must|should|shall|and|or|unless|except|if|but"
    r"|with|without|for|has|have)(?![A-Za-z])"
)
# A second orientation joined to the first ("before or after", "prior to and/or following"): both sides.
_SECOND_SIDE = re.compile(r"\s*(?:/|(?i:and/or|or|and)(?![A-Za-z]))\s*")
# A comparator's bounds on the time from the anchor: (lower, lower inclusivity, upper, upper inclusivity),
# "N" standing for the duration's value.
_WINDOW_BOUNDS = {
    "≥": ("N", "inclusive", "", ""),
    ">": ("N", "exclusive", "", ""),
    "≤": ("0", "unspecified", "N", "inclusive"),
    "<": ("0", "unspecified", "N", "exclusive"),
    "=": ("N", "inclusive", "N", "inclusive"),
}
_WITHIN = ("0", "unspecified", "N", "unspecified")
_AT_LEAST_UNSTATED = ("N", "unspecified", "", "")
_BOUND_NAMES = ("lower", "lower_inclusive", "upper", "upper_inclusive")


def _orientation(found: re.Match[str] | None, past: bool) -> str:
    if found is None:
        return "before" if past else "unspecified"
    return "before" if found.group("before") else "after" if found.group("after") else "unspecified"


def read_window(text: str, start: int) -> Parse:
    """The time window at text[start:], after whitespace (pure — pinned).

    A marker ("within", "within the past", "within prior", "in the last", "during the past") or a
    comparator ("at least", "less than or equal to", "≥"), a duration, and an orientation: before ("before",
    "prior to", "preceding", "ago", or a past marker), after ("after", "following"), or unspecified ("of" or
    "from" after a marker, or none). The anchor is the words after the orientation up to punctuation or a
    clause word ("is", "and", "unless"), as written; "unresolved" when none is written, or after "ago" (never
    the enrollment, never assumed). Each reading: marker (as written, "" when none), orientation, anchor,
    lower, lower_inclusive, upper, upper_inclusive (in the duration's unit; "" for an unbounded side), value,
    unit, ucum, mapping. A marker bounds the time by N, inclusivity unspecified, from 0 (unspecified); a
    comparator gives its own (≥ N inclusive, < N exclusive). Ambiguous: a duration with a direction and no
    marker ("4 weeks prior to randomization": within N, or at least N), or an ambiguous number. Spans:
    window (the whole), comparator, value, unit, qualifier (the anchor). Abstained: a marker and a comparator
    together ("within ≥ 5 years": the bound is not stated clearly), no duration, a duration with no marker
    and no direction before or after ("≥ 12 weeks", "2 years of smoking": a length of time, not a window), a
    window on both sides of its anchor ("within 14 days before or after randomization": no one orientation,
    and no orientation value names both), or a start outside the text.
    """
    if not _inside(text, start):
        return _abstained("window", start, "a start outside the text")
    pos = _skip(text, start)
    mark = _WINDOW_MARK.match(text, pos)
    comparator = read_comparator(text, mark.end() if mark else pos)
    if mark and comparator.status == "parsed":
        return _abstained("window", start, "a window marker and a comparator together: the bound is unclear")
    if comparator.status == "parsed":
        duration = read_duration(text, comparator.end)
    else:
        duration = read_duration(text, mark.end() if mark else pos)
    if duration.status == "abstained":
        return _abstained("window", start, "no duration")
    orient = _ORIENTATION.match(text, _skip(text, duration.end))
    if not mark and (orient is None or orient.group("either")):
        return _abstained("window", start, "a duration with no marker and no direction: no window")
    joined = _SECOND_SIDE.match(text, orient.end()) if orient else None
    second = _ORIENTATION.match(text, joined.end()) if joined else None
    if second and not second.group("either"):
        return _abstained("window", start, "a window on both sides of its anchor: no one orientation")
    end = orient.end() if orient else duration.end
    anchor, spans = "unresolved", [*comparator.spans, *duration.spans]
    if orient and orient.group(0).lower() != "ago":
        anchor_start = _skip(text, orient.end())
        stop = _ANCHOR_END.search(text, anchor_start)
        anchor_end = len(text[: stop.start() if stop else len(text)].rstrip())
        if anchor_end > anchor_start:
            anchor, end = text[anchor_start:anchor_end], anchor_end
            spans.append(Span("qualifier", anchor_start, anchor_end))
    if comparator.status == "parsed":
        options = [_WINDOW_BOUNDS[dict(comparator.readings[0])["sign"]]]
    else:
        options = [_WITHIN] if mark else [_WITHIN, _AT_LEAST_UNSTATED]
    marker = (
        mark.group(0) if mark else dict(comparator.readings[0])["as_written"] if comparator.readings else ""
    )
    past = bool(mark and (mark.group("past1") or mark.group("past2")))
    head = (("marker", marker), ("orientation", _orientation(orient, past)), ("anchor", anchor))
    readings: list[Fields] = []
    for written, bounds in product(duration.readings, options):
        value = dict(written)["value"]
        named = tuple(
            (name, value if bound == "N" else bound) for name, bound in zip(_BOUND_NAMES, bounds, strict=True)
        )
        readings.append((*head, *named, *written))
    note = duration.note or "a duration and an orientation with no marker: within it, or at least it"
    return _parse("window", readings, [Span("window", pos, end), *spans], end, note)


# ── intervals ───────────────────────────────────────────────────────────────────────────────────────

_RANGE = re.compile(r"\s*(?:-|–|—|\\~|~|(?i:to|through|thru)(?![A-Za-z]))\s*")
_BETWEEN = re.compile(r"(?i:(?P<between>between)|from)\s+")
_BETWEEN_AND = re.compile(r"\s*(?i:and|to|-|–)(?![A-Za-z])\s*")
_PAIR = re.compile(r"\s*(?:,|(?i:and|but)(?![A-Za-z]))?\s*")
_INCLUSIVE = re.compile(r"\s*\(?(?i:(?P<inclusive>inclusive)|(?P<exclusive>exclusive))(?![A-Za-z])\)?")
_POSTFIX = re.compile(
    r"\s*(?i:(?P<lower>or\s+(?:more|older|greater|higher|above|over)|and\s+(?:above|older|over))"
    r"|(?P<upper>or\s+(?:less|younger|fewer|lower|below|under)|and\s+(?:below|under|younger)))(?![A-Za-z])"
)
_SIDE = {"≥": "lower", ">": "lower", "≤": "upper", "<": "upper", "=": "point"}
_NO_UNIT: Fields = (("unit", ""), ("ucum", ""), ("mapping", ""), ("reference", ""))


@dataclass(frozen=True)
class _Bound:
    values: tuple[str, ...]  # the number's readings ("" for a reference written with no factor)
    unit: Fields  # unit, ucum, mapping, reference; all "" when none is written
    spans: tuple[Span, ...]
    end: int
    note: str


# After a number whose unit is not read: a multiplication ("× ULRR", "x 10 9/L", "-fold ULN") or digits
# ("109/L", "000/mm3") say a unit or a reference is written there, unread; never a bare number.
_UNREAD_AFTER = re.compile(rf"{_TIMES}|[^\S\r\n]*\d")
UNREAD_AFTER = "a factor or digits after the number, not read: its unit or reference is unknown"


def _bound(text: str, start: int) -> _Bound | str | None:
    """A bound: a reference expression, or a number with the unit after it if one is written; None when no
    number is there, or the note of an abstention a bare number would hide (a factor or digits not read)."""
    reference = read_reference(text, start)
    if reference.status != "abstained":
        values = tuple(dict(reading)["factor"] for reading in reference.readings)
        unit = (
            ("unit", ""),
            ("ucum", ""),
            ("mapping", ""),
            ("reference", dict(reference.readings[0])["reference"]),
        )
        return _Bound(values, unit, reference.spans, reference.end, reference.note)
    if reference.note == FACTOR_AFTER:
        return FACTOR_AFTER
    number = read_number(text, start)
    if number.status == "abstained":
        return None
    values = tuple(dict(reading)["value"] for reading in number.readings)
    unit = read_unit(text, number.end)
    if unit.status == "abstained" and _UNREAD_AFTER.match(text, number.end):
        return UNREAD_AFTER
    if unit.status == "abstained":
        return _Bound(values, _NO_UNIT, number.spans, number.end, number.note)
    written = dict(unit.readings[0])
    fields = (("unit", written["as_written"]), ("ucum", written["ucum"]), ("mapping", written["mapping"]))
    return _Bound(values, (*fields, ("reference", "")), (*number.spans, *unit.spans), unit.end, number.note)


def _range_unit(first: _Bound, second: _Bound) -> Fields | None:
    """The unit of a range: the one written (once, or alike twice), or None when two different ones are."""
    if first.unit == _NO_UNIT:
        return second.unit
    return first.unit if second.unit in (_NO_UNIT, first.unit) else None


def _interval(
    lower: tuple[_Bound | None, str],
    upper: tuple[_Bound | None, str],
    unit: Fields,
    spans: list[Span],
    end: int,
) -> Parse:
    """The interval of two sides (each a bound or None for unbounded, with its inclusivity) in one unit; a
    point (one bound on both sides) keeps each of its readings on both sides alike."""
    (low, low_inclusive), (high, high_inclusive) = lower, upper
    notes = dict.fromkeys(bound.note for bound in (low, high) if bound is not None and bound.note)
    low_values, high_values = (low.values if low else ("",)), (high.values if high else ("",))
    pairs = zip(low_values, high_values, strict=True) if low is high else product(low_values, high_values)
    readings: list[Fields] = []
    for low_value, high_value in pairs:
        sides = (("lower", low_value), ("lower_inclusive", low_inclusive if low else ""))
        sides += (("upper", high_value), ("upper_inclusive", high_inclusive if high else ""))
        readings.append((*sides, *unit))
    return _parse("interval", readings, spans, end, "; ".join(notes))


def read_interval(text: str, start: int) -> Parse:
    """The interval at text[start:], after whitespace (pure — pinned).

    One-sided: a comparator and a bound ("≥ 45 mL/min", "\\> 1.4 mg/dl", "≤2.5×ULN"; ≥ and ≤ inclusive, >
    and < exclusive, = both sides inclusive), or a bound and "or more", "or older", "or less" (inclusive).
    Two-sided explicit: two comparators on two sides ("≥ 18 years and \\<75 years": [18, 75)). Two-sided
    unspecified: a range ("18 to 75 years", "0-1", "0\\~1", "6 through 35 years", "between 18 and 75", "from
    1 to 2"), inclusive or exclusive only when the word follows. A bound is a reference expression (its
    factor the bound, "" when none is written) or a number with its unit. Each reading: lower,
    lower_inclusive, upper, upper_inclusive ("" for an unbounded side), unit, ucum, mapping, reference (a unit
    or reference written once is the range's); spans: comparator, value, unit, reference. Ambiguous when a
    number is. Abstained: no bound, a number alone ("1 or 2"), two bounds on one side, two different units, a
    comparator with no bound, a number followed by a factor or digits not read ("≤ 1.5 × ULRR", "≥ 1.5 x 10
    9/L", "≥ 100 109/L": UNREAD_AFTER, never a bare number with its unit or reference lost), a factor written
    after its reference ("≤ ULN x 2.5": FACTOR_AFTER), or a start outside the text.
    """
    if not _inside(text, start):
        return _abstained("interval", start, "a start outside the text")
    pos = _skip(text, start)
    between = _BETWEEN.match(text, pos)
    first_comparator = read_comparator(text, pos)
    if between or first_comparator.status == "abstained":
        first = _bound(text, between.end() if between else pos)
        if not isinstance(first, _Bound):
            return _abstained("interval", start, first or "no bound")
        joined = (_BETWEEN_AND if between else _RANGE).match(text, first.end)
        second = _bound(text, joined.end()) if joined else None
        if isinstance(second, str):
            return _abstained("interval", start, second)
        if second is not None:
            unit = _range_unit(first, second)
            if unit is None:
                return _abstained("interval", start, "bounds in two different units")
            written = _INCLUSIVE.match(text, second.end)
            inclusivity = (
                "unspecified" if not written else "inclusive" if written.group("inclusive") else "exclusive"
            )
            end = written.end() if written else second.end
            spans = [*first.spans, *second.spans]
            return _interval((first, inclusivity), (second, inclusivity), unit, spans, end)
        postfix = _POSTFIX.match(text, first.end)
        if between or not postfix:
            return _abstained("interval", start, "a number alone states no interval")
        side = (first, "inclusive")
        sides = (side, (None, "")) if postfix.group("lower") else ((None, ""), side)
        return _interval(sides[0], sides[1], first.unit, list(first.spans), postfix.end())
    first = _bound(text, first_comparator.end)
    if not isinstance(first, _Bound):
        return _abstained("interval", start, first or "a comparator with no bound")
    sign = dict(first_comparator.readings[0])["sign"]
    inclusivity = "inclusive" if sign in "≥≤=" else "exclusive"
    spans = [*first_comparator.spans, *first.spans]
    second_comparator = read_comparator(text, _PAIR.match(text, first.end).end())  # ty: ignore[unresolved-attribute]
    second = _bound(text, second_comparator.end) if second_comparator.status == "parsed" else None
    if isinstance(second, str):
        return _abstained("interval", start, second)
    if second is not None:
        other = dict(second_comparator.readings[0])["sign"]
        if {_SIDE[sign], _SIDE[other]} != {"lower", "upper"}:
            return _abstained("interval", start, "two bounds on one side")
        unit = _range_unit(first, second)
        if unit is None:
            return _abstained("interval", start, "bounds in two different units")
        pair = [(first, inclusivity), (second, "inclusive" if other in "≥≤" else "exclusive")]
        low, high = pair if _SIDE[sign] == "lower" else pair[::-1]
        spans += [*second_comparator.spans, *second.spans]
        return _interval(low, high, unit, spans, second.end)
    side = (first, inclusivity)
    low, high = {"lower": (side, (None, "")), "upper": ((None, ""), side), "point": (side, side)}[_SIDE[sign]]
    return _interval(low, high, first.unit, spans, first.end)
