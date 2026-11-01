"""Modality facets and cell properties of an intervention, read from its own entry (add-scoped-reasoning,
Decision 11).

Modality is several facets, not one class: antibody, conjugate, radioactive, cell, gene and vaccine function.
Cell properties are separate again: lineage, engineering, preparation and donor relationship. Both are read
only from wording bound to the intervention's own entry in the record (its name, other names and description),
never from an arm (an arm names its whole combination) or from eligibility ("prior CAR-T excluded" is an
eligibility assertion about the patient, not the intervention's modality). Inside the entry too, wording of
the patient's history or eligibility ("no prior CAR-T", "previously treated with", "patients who received") is
`history`: it never asserts the intervention's modality and never unlocks its cell properties. Every
extraction keeps its subject, property, value, polarity, scope, evidence location, rule and status; the
reading adds its warrant. One mention is one extraction ("CAR-T cell therapy" is one cell facet, not two). A
span of the entry's own wording is known; a guess from a name's stem (-mab, -cel, a conjugate's payload word)
is interpolated at most. A cell property is read only where the entry asserts a cell facet (a T cell named in
an antibody's mechanism is not the antibody's lineage), and is interpolated when that facet is.
"""

from __future__ import annotations

import re

Extraction = tuple[str, str, str, str, str, str, str, str]
# (subject, property, value, polarity, scope, evidence location, rule, status)

SCOPE = "intervention entry"

FACETS = (
    ("antibody", r"(?i:\bantibod(?:y|ies)\b)|\bmAbs?\b"),
    ("conjugate", r"(?i:\bantibody[- ]drug conjugates?\b|\bconjugated?\b)|\bADCs?\b"),
    (
        "radioactive",
        r"(?i:\bradio(?:labell?ed|ligands?|pharmaceuticals?|conjugates?|isotopes?)\b"
        r"|\b(?:lutetium|yttrium|actinium|iodine)[- ]?\d{2,3}\b)|\b\d{2,3}(?:Lu|Y|Ac|I)\b",
    ),
    (
        "cell",
        r"(?i:\bcell(?:ular)? (?:therapy|therapies|product|immunotherapy|infusion)\b"
        r"|\btumou?r[- ]infiltrating lymphocytes\b)|\bCAR[- ]?(?:T|NK)\b|\bTILs?\b",
    ),
    (
        "gene",
        r"(?i:\bgene (?:therapy|transfer)\b|\b(?:viral|AAV|adenoviral|lentiviral|retroviral) vectors?\b"
        r"|\boncolytic virus\b|\bplasmid\b)|\bmRNA\b",
    ),
    ("vaccine", r"(?i:\bvaccines?\b|\bvaccination\b)"),
)

CELL_PROPERTIES = (
    ("lineage", "T cell", r"(?i:\bT[- ]cells?\b|\bT[- ]lymphocytes?\b)|\bCAR[- ]?T\b"),
    ("lineage", "NK cell", r"(?i:\bnatural killer cells?\b)|\bNK[- ]cells?\b|\bCAR[- ]?NK\b"),
    ("lineage", "dendritic cell", r"(?i:\bdendritic cells?\b)"),
    ("lineage", "tumour-infiltrating lymphocyte", r"(?i:\btumou?r[- ]infiltrating lymphocytes\b)|\bTILs?\b"),
    ("lineage", "macrophage", r"(?i:\bmacrophages?\b)"),
    ("lineage", "stem cell", r"(?i:\bstem cells?\b)"),
    (
        "engineering",
        "chimeric antigen receptor",
        r"(?i:\bchimeric antigen receptor\b)|\bCAR\b|\bCAR[- ]?(?:T|NK)\b",
    ),
    (
        "engineering",
        "engineered TCR",
        r"\bTCR[- ](?:engineered|transduced|T)\b|(?i:\bT[- ]cell receptor[- ]engineered\b)",
    ),
    ("engineering", "genetically modified", r"(?i:\bgene(?:tically)?[- ]?(?:modified|engineered)\b)"),
    ("preparation", "expanded", r"(?i:\b(?:ex[- ]vivo[- ])?expanded\b)"),
    ("preparation", "cryopreserved", r"(?i:\bcryopreserved\b)"),
    ("donor relationship", "autologous", r"(?i:\bautologous\b)"),
    ("donor relationship", "allogeneic", r"(?i:\ballogene?ic\b)"),
)

# Name stems (USAN conventions), read from the names alone: a guess, interpolated at most.
NAME_STEMS = (
    ("antibody", r"(?i:\b[a-z]{2,}mab\b)"),
    ("cell", r"(?i:\b[a-z]{2,}cel\b)"),
    ("gene", r"(?i:\b[a-z]{2,}(?:vec|gene)\b)"),
    (
        "conjugate",
        r"(?i:\b(?:vedotin|deruxtecan|govitecan|emtansine|mafodotin|ozogamicin|tesirine|soravtansine)\b)",
    ),
)

_NEGATION = re.compile(r"(?i:\bnon[- ]?|\bnot (?:an? )?|\bwithout (?:an? )?)$")
# Wording of the patient's history or eligibility; its clause runs back to the last ".", ";", ":" or break.
_HISTORY = re.compile(
    r"(?i:\bno prior\b|\bprior\b(?!\s+to\b)|\bprevious(?:ly)?\b|\bpre-?treated\b"
    r"|\b(?:have |has |had )?received\b|\btreated with\b"
    r"|\b(?:patients?|subjects?|participants?) (?:who|whose|with prior|having)\b"
    r"|\bhistory of\b|\bexpos(?:ure|ed) to\b|\brefractory\b|\bfail(?:ed|ure)\b|\bprogress(?:ed|ion)\b"
    r"|\beligib\w*|\bexclu\w*|\binclu(?:ded|sion)\b)"
)
_CLAUSE = re.compile(r"[.;:\n]")


def history_clause(before: str) -> bool:
    """Whether a mention's clause, before it, states the patient's history or eligibility (pure — pinned).

    The clause is what follows the last ".", ";", ":" or line break of `before`. True when it holds any
    _HISTORY wording ("no prior", "previously", "treated with", "patients who", "received", "eligible",
    "excluded" ...; "prior to" is a time, not a history): what follows is about the patient, not the
    intervention. False otherwise, an empty clause
    included.
    """
    return bool(_HISTORY.search(_CLAUSE.split(before)[-1]))


def mentions(pattern: str, text: str) -> list[tuple[int, int]]:
    """The mentions one rule's pattern finds in a text, as (start, end) (pure — pinned).

    Matches separated only by spaces or hyphens are one mention ("CAR-T" and "cell therapy" in "CAR-T cell
    therapy" are one span), so a mention is extracted once; in order of position.
    """
    spans: list[tuple[int, int]] = []
    for match in re.finditer(pattern, text):
        if spans and re.fullmatch(r"[\s-]*", text[spans[-1][1] : match.start()]):
            spans[-1] = (spans[-1][0], match.end())
        else:
            spans.append((match.start(), match.end()))
    return spans


def _polarity(text: str, start: int) -> str:
    """history when the mention's clause states the patient's history, negated when "non-", "not a" or
    "without" stands right before it, asserted otherwise."""
    if history_clause(text[:start]):
        return "history"
    return "negated" if _NEGATION.search(text[:start]) else "asserted"


def entry_properties(subject: str, texts: list[tuple[str, str, bool]]) -> list[Extraction]:
    """The modality facets and cell properties one intervention's own entry states (pure — pinned).

    `texts` are the entry's fields as (evidence location, text, is a name). Each mention (`mentions`) of a
    FACETS rule in any field is a known `modality` extraction: `history` when its clause states the patient's
    history or eligibility (`history_clause`), `negated` when "non-", "not a" or "without" stands right before
    it, `asserted` otherwise; each NAME_STEMS mention in a name is an interpolated `modality` extraction (rule
    name_stem:<facet>), `history` likewise. CELL_PROPERTIES are read only when some asserted cell facet is
    extracted (a history or negated one unlocks nothing): known when a known cell facet is, interpolated when
    only a name stem gives one; each with its own polarity. Every extraction is (subject, property, value,
    polarity, scope, "<location>[start:end]", rule, status), in field order, then rule order, then position.
    """
    out: list[Extraction] = []
    for location, text, is_name in texts:
        for facet, pattern in FACETS:
            for start, end in mentions(pattern, text):
                polarity = _polarity(text, start)
                span = f"{location}[{start}:{end}]"
                out.append((subject, "modality", facet, polarity, SCOPE, span, f"facet:{facet}", "known"))
        for facet, pattern in NAME_STEMS if is_name else ():
            for start, end in mentions(pattern, text):
                polarity = "history" if history_clause(text[:start]) else "asserted"
                span = f"{location}[{start}:{end}]"
                rule = f"name_stem:{facet}"
                out.append((subject, "modality", facet, polarity, SCOPE, span, rule, "interpolated"))
    cell = {e[7] for e in out if e[2] == "cell" and e[3] == "asserted"}
    if not cell:
        return out
    status = "known" if "known" in cell else "interpolated"
    for location, text, _is_name in texts:
        for prop, value, pattern in CELL_PROPERTIES:
            for start, end in mentions(pattern, text):
                span = f"{location}[{start}:{end}]"
                rule = f"cell:{prop}:{value}"
                out.append((subject, prop, value, _polarity(text, start), SCOPE, span, rule, status))
    return out
