"""Declared expectations: one predicate, its observation status per trial, its conditional rarity,
and the status of each deviation (openspec/changes/add-design-surprise).

An expectation is declared, never discovered here: a predicate, the trials it applies to, the cell and
parent it is measured over, the support each needs, and its provenance. A trial's observation of the
predicate is one of five statuses, read from its whole eligibility text:

  present            — the trial excludes it (an exclusion criterion names it; or an inclusion
                       criterion negates it or says its patients are excluded);
  explicitly_negated — the trial admits it (an inclusion criterion names it as eligible, or an
                       exclusion criterion says such patients are eligible);
  not_documented     — the whole text was read and nothing names it: never "admitted";
  unresolved         — it is named where its scope cannot be told (unsectioned text, or cohorts
                       that disagree);
  not_applicable     — the expectation does not apply to the trial (the caller decides, from its
                       experimental drugs' classes).

Rarity is conditional corpus rarity, −log2 of a frequency in a declared cell, not the derivational
significance of SIGNIFICANCE_WEIGHTING.md (that needs a space of admissible alternatives, a later
target). A deviation that is valid and unexplained stays a verified deviation; it is never noise.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

# Surface vocabulary of autoimmune disease as eligibility criteria name it: the class words, and the
# named diseases a criterion lists without them. Authored from domain knowledge (provenance: prior).
AUTOIMMUNE = re.compile(
    r"auto-?immun\w*|immune[- ]mediated (?:disease|disorder)|lupus|\bSLE\b|rheumatoid arthritis|"
    r"inflammatory bowel disease|Crohn|ulcerative colitis|multiple sclerosis|myasthenia gravis|"
    r"Guillain|vasculitis|Wegener|Sj[oö]gren|scleroderma|systemic sclerosis|psoriatic arthritis|"
    r"ankylosing spondylitis|Hashimoto|Graves|sarcoidosis|celiac disease",
    re.IGNORECASE,
)
# A negation earlier in the same clause ("must not have significant gastrointestinal disorders ... (e.g.,
# Crohn's disease"): the periods of "e.g." and "i.e." do not end a clause.
_NEGATED = re.compile(r"\b(?:no|not|without|free of|absence of|none)\b[^.;:]{0,200}$", re.IGNORECASE)
_ADMITS = re.compile(
    r"(?:are|is|may be|will be|can be)\s+(?:eligible|allowed|permitted|included|enrolled)"
    r"|are not excluded",
    re.IGNORECASE,
)
_EXCLUDED = re.compile(
    r"(?:are|is|will be)\s+(?:excluded|not eligible|ineligible)|not (?:allowed|permitted)",
    re.IGNORECASE,
)
# An exception inside an exclusion ("except vitiligo, type 1 diabetes ..."), kept as written.
_EXCEPTION = re.compile(
    r"(?:except(?:ion)?(?: for| of)?|other than|with the exception of|excluding|"
    r"(?:the following|subjects|patients|participants)[^.;]{0,40}"
    r"(?:are|is|will be) (?:eligible|allowed|permitted))[^.;]{0,160}",
    re.IGNORECASE,
)
# A condition on an admission ("eligible if controlled on replacement therapy"), kept as written.
_CONDITIONAL = re.compile(
    r"\b(?:if|provided(?: that)?|as long as|only if|when|unless)\b[^.;]{0,160}", re.IGNORECASE
)

# A record that says it lists only some criteria: its silence says less than a complete record's.
_ABBREVIATED = re.compile(
    r"\b(?:key|main|major|most important|selected)\s+(?:inclusion|exclusion|eligibility)\b"
    r"|other\s+(?:protocol[- ]?defined\s+)?(?:inclusion\s*/\s*exclusion\s+|inclusion\s+|exclusion\s+)?"
    r"criteria\s+(?:may|could|will|might)\s+apply"
    r"|further\s+(?:inclusion|exclusion)\s+criteria\s+apply|include,? but (?:are|is) not limited to",
    re.IGNORECASE,
)

STATUSES = ("present", "explicitly_negated", "not_documented", "unresolved", "not_applicable")


def autoimmune_exclusion(pieces: list[tuple[str, str]]) -> tuple[str, str, list[int], list[str]]:
    """The status of "excludes autoimmune disease" in one trial's eligibility (pure — pinned).

    `pieces` are (section, text) for every criterion and prose piece of the trial, in order.
    Returns (status, reason, the indices of the pieces it rests on, the qualifiers written beside
    them). A piece naming autoimmune disease (the class words, or a named autoimmune disease):
      exclusion section — excludes it; a sentence in it that allows or permits something ("replacement
                          therapy is allowed", "vitiligo ... are permitted to enroll") is an
                          exception, kept as a qualifier, never an admission;
      inclusion section — excludes it when the name is negated before it ("no autoimmune disease")
                          or the piece says such patients are excluded; otherwise admits it;
      unsectioned       — unresolved scope.
    Excluding and admitting pieces together are cohorts that disagree: unresolved,
    "conflicting_scopes". Only excluding: present, its exceptions kept as qualifiers. Only
    admitting: explicitly_negated, its conditions ("if controlled ...") kept as qualifiers. Only
    unsectioned: unresolved, "unsectioned_mention". None names it, in a record that says it lists
    only key criteria ("Key Exclusion Criteria", "other protocol-defined criteria may apply"):
    unresolved, "abbreviated_criteria". None names it otherwise: not_documented, "not_named" — the
    text was read, and nothing in it says the trial admits it.
    """
    excludes: list[int] = []
    admits: list[int] = []
    unscoped: list[int] = []
    exceptions: list[str] = []
    conditions: list[str] = []
    for index, (section, text) in enumerate(pieces):
        mention = AUTOIMMUNE.search(text)
        if not mention:
            continue
        if section == "exclusion":
            target = excludes  # its permissive sentences are its exceptions, never an admission
        elif section == "inclusion":
            before = re.sub(r"\b(?:e\.g|i\.e|etc)\.", "eg", text[: mention.start()], flags=re.IGNORECASE)
            negated = _NEGATED.search(before) or _EXCLUDED.search(text)
            target = excludes if negated else admits
        else:
            target = unscoped
        target.append(index)
        if target is excludes:
            exceptions.extend(m.group(0).strip() for m in _EXCEPTION.finditer(text))
            exceptions.extend(
                s.strip() for s in re.split(r"(?<=[.;])\s+|\n+", text) if s.strip() and _ADMITS.search(s)
            )
        elif target is admits:
            conditions.extend(m.group(0).strip() for m in _CONDITIONAL.finditer(text))
    if excludes and admits:
        return "unresolved", "conflicting_scopes", excludes + admits, exceptions + conditions
    if excludes:
        return "present", "excluded", excludes, exceptions
    if admits:
        return "explicitly_negated", "admitted", admits, conditions
    if unscoped:
        return "unresolved", "unsectioned_mention", unscoped, []
    if any(_ABBREVIATED.search(text) for _, text in pieces):
        return "unresolved", "abbreviated_criteria", [], []
    return "not_documented", "not_named", [], []


@dataclass(frozen=True)
class Expectation:
    id: str
    statement: str
    applies_to: tuple[str, ...]  # experimental-drug classes (FDA EPC names, or "stated: <target>")
    cell: str  # the coordinate the cell is keyed by
    parent: str  # the parent cell: "all" (every applicable trial)
    support: int  # the fewest known observations a cell needs before it reports a rarity
    provenance: str


FROZEN = (
    Expectation(
        "checkpoint_blockers_exclude_autoimmune_disease",
        "A trial whose experimental drug blocks PD-1 or PD-L1 excludes patients with autoimmune disease.",
        (
            "Programmed Death Receptor-1 Blocking Antibody",
            "Programmed Death Ligand-1 Blocker",
            "stated: PD-1",
            "stated: PD-L1",
        ),
        "setting",
        "all",
        10,
        "prior: immune-related adverse events of checkpoint blockade (domain knowledge; the "
        "drugs' label warnings); surfaced as a mechanism signal on development data (487 Phase 3 "
        "NSCLC trials, 2026-10-31); frozen 2026-10-31 at the founder's word; confirmation needs "
        "a population no rule was written against",
    ),
)


def conditional_rarity(
    observations: list[tuple[str, str]], cell: str, support: int
) -> tuple[str, float | None, int, float | None, float | None]:
    """The share of "present" among known observations in a cell, with rarities (pure — pinned).

    `observations` are (cell key, status) for every applicable trial. Known statuses are present,
    explicitly_negated and not_documented; unresolved and not_applicable count nowhere. Returns
    (source, P(present), known count, bits of a present observation, bits of an absent one).
    Source is "cell" when the cell has at least `support` known observations, "parent" (every
    applicable trial) when only the parent has, and "abstain" (no share, no bits) when neither
    does. A share of 0 or 1 gives None for the observation that never occurred: an unobserved
    event has no finite rarity here.
    """
    known = [(key, status) for key, status in observations if status in STATUSES[:3]]
    in_cell = [status for key, status in known if key == cell]
    if len(in_cell) >= support:
        source, chosen = "cell", in_cell
    elif len(known) >= support:
        source, chosen = "parent", [status for _, status in known]
    else:
        return "abstain", None, len(in_cell), None, None
    share = sum(1 for status in chosen if status == "present") / len(chosen)
    present_bits = round(-math.log2(share), 3) if share > 0 else None
    absent_bits = round(-math.log2(1 - share), 3) if share < 1 else None
    return source, round(share, 4), len(chosen), present_bits, absent_bits


def deviation_status(status: str, qualifiers: int, audit: str) -> str:
    """How an observation stands against an expectation that its predicate is present
    (pure — pinned).

    audit "invalid" (the founder found the span does not say what was read) → invalid_extraction,
    whatever the status; not_applicable → not_applicable; unresolved → scope_unresolved; present →
    conforms; not_documented → omission (silence is not admission, and never shares its label);
    explicitly_negated with a condition recorded → explanation_supported; explicitly_negated
    otherwise → verified_deviation (valid, and unexplained until something explains it).
    """
    if audit == "invalid":
        return "invalid_extraction"
    if status == "not_applicable":
        return "not_applicable"
    if status == "unresolved":
        return "scope_unresolved"
    if status == "present":
        return "conforms"
    if status == "not_documented":
        return "omission"
    if status == "explicitly_negated" and qualifiers > 0:
        return "explanation_supported"
    return "verified_deviation"
