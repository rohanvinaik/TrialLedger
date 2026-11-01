"""Banks: deterministic typing of one criterion's text into atoms, or nothing.

An atom is (concept, values, params, start, end): the concept from this module's vocabulary, the values the
text allows (a set, as a sorted tuple), parameters exactly as written (a threshold's comparator, number and
unit), and the span of the words it rests on within the criterion. A bank that finds nothing returns no atom:
it abstains, and an untyped criterion is never read as stating the absence of anything. Polarity is not
decided here: an atom records what the text says, and the criterion's section (inclusion or exclusion) is
combined with it by the coherence layer, so neither is lost.

What is authored here is pattern syntax and surface vocabulary (gene symbols, analyte names, scale names,
agent-class words as written in criteria), measured on the 487 interventional Phase 3 NSCLC trials started
2015-2024. No clinical fact relating one thing to another is authored here; those come from a cited source or
are computed across trials and proposed. No model reads any text.
"""

from __future__ import annotations

import re

Atom = tuple[str, tuple[str, ...], tuple[tuple[str, str], ...], int, int]

# ── performance status ──────────────────────────────────────────────────────────────────────────────

_PS_SCALE = re.compile(
    r"ECOG|Zubrod|(?i:World Health Organization)|\bWHO\b|"
    r"(?i:Eastern (?:Cooperative Oncology|Cancer Cooperative) Group)"
)
_PS_EXPR = re.compile(
    r"(?P<le>(?:≤|<=|\\<=|=\\?<|\\</=)\s*(?P<le_n>[0-5]))"
    r"|(?P<a>[0-5])\s*(?:-|–|to|\\?~)\s*(?P<b>[0-5])"
    r"|(?P<list>[0-5](?:\s*,\s*[0-5])*\s*,?\s*(?:or|and)\s*[0-5])"
    r"|(?<![\d.])(?P<one>[0-5])(?![\d.%])"
)


def performance_status(text: str) -> list[Atom]:
    """ECOG (or Zubrod or WHO) performance status values a criterion allows (pure — pinned).

    The values are read from the first expression within 80 characters after the scale's name, or else the
    last whole expression ending within 12 characters before it ("0-1 ECOG score", "of 0 or 1 on the ECOG
    scale": the expression is read whole, from up to 40 characters back): a range ("0-1", "0 to 2", "0~1"),
    a list ("0, 1, or 2"), an upper bound ("≤1", "<= 1") or a single value. No expression near the name: no
    atom.
    """
    scale = _PS_SCALE.search(text)
    if not scale:
        return []
    after = _PS_EXPR.search(text, scale.end(), min(scale.end() + 80, len(text)))
    before = [
        found
        for found in _PS_EXPR.finditer(text, max(0, scale.start() - 40), scale.start())
        if found.end() >= scale.start() - 12
    ]
    for found in (after, before[-1] if before else None):
        if not found:
            continue
        if found.group("le"):
            values = range(int(found.group("le_n")) + 1)
        elif found.group("a"):
            values = range(int(found.group("a")), int(found.group("b")) + 1)
        elif found.group("list"):
            values = [int(digit) for digit in re.findall(r"[0-5]", found.group("list"))]
        else:
            values = [int(found.group("one"))]
        return [("ecog_ps", tuple(str(v) for v in sorted(set(values))), (), found.start(), found.end())]
    return []


# ── biomarker status ────────────────────────────────────────────────────────────────────────────────

GENES = {
    "EGFR": r"EGFR|epidermal growth (?:factor )?receptor(?: factor)?",
    "ALK": r"ALK|anaplastic lymphoma kinase",
    "ROS1": r"ROS1|ROS-1",
    "KRAS": r"KRAS|K-ras|K-RAS",
    "BRAF": r"BRAF",
    "MET": r"c-Met|c-MET|MET",
    "RET": r"RET",
    "NTRK": r"NTRK",
    "HER2": r"HER2|HER-2|ERBB2",
    "PD-L1": r"PD-L1|PD L1|PDL1|programm?e?d? (?:cell )?death[- ]ligand[- ]1",
}
_GENE = re.compile(
    "|".join(f"(?P<{name.replace('-', '_')}>\\b(?:{pattern})\\b)" for name, pattern in GENES.items())
)
# A gene named as a drug's target is an agent, not the tumour's status.
_AS_AGENT = re.compile(
    r"^[\s-]*(?:-?\s*)(?:targeted|directed|inhibitors?|TKIs?|tyrosine kinase inhibitors?|antibod|agents?|"
    r"drugs?|therap|blockade|blocking)",
    re.IGNORECASE,
)
_ANTI = re.compile(
    r"(?:anti[\s-]*|targeting\s+|targeted (?:to|against)\s+|directed against\s+|inhibitors? of\s+)$",
    re.IGNORECASE,
)
# "Confirmed tumor PD-L1 status", "documented EGFR test result": a status that is known, whatever it is.
_DOCUMENTED = re.compile(
    r"(?:confirmed|documented|documentation of|known|available|recorded|measurement of)[^.;]{0,40}"
    r"(?:status|result|expression|score|TPS)",
    re.IGNORECASE,
)
# "any PD-L1 TPS": the trial admits every state, so the text restricts nothing.
_ANY = re.compile(r"\bany\s+$", re.IGNORECASE)
# "... are excluded from the study": a sentence of an inclusion criterion that states an exclusion.
_EXCLUDED = re.compile(
    r"(?:are|is|will be)\s+(?:excluded|not eligible|ineligible)|not (?:allowed|permitted)", re.IGNORECASE
)
_POSITIVE = (
    r"positive|mutations?|mutated|mutant|rearrangements?|rearranged|fusions?|translocations?|amplifi\w*|"
    r"overexpress\w*|alterations?|exon \d+|L858R|del(?:etion)? ?19|G12C|V600E|\bhigh\b|presence"
)
_NEGATIVE = r"negative|wild[- ]?type|absence|absent|\bno\b|without|not (?:have|harbor|harbour)"
_UNKNOWN = r"unknown|not known|untested|not tested"
_STATE = re.compile(f"(?P<neg>{_NEGATIVE})|(?P<unk>{_UNKNOWN})|(?P<pos>{_POSITIVE})", re.IGNORECASE)
# Words that assert presence, and so end the scope of an earlier negation ("absence of ALK ... OR presence of
# a K-ras mutation").
_PRESENCE = re.compile(r"presence|positive|\bhas\b|\bhave\b|harbou?r", re.IGNORECASE)
_PERCENT = re.compile(
    r"(?:(?P<cmp>≥|>=|\\>=|<|\\<|≤|<=|\\<=|>|\\>)\s*)?(?P<a>\d{1,3})\s*%?(?:\s*(?:-|–"
    r"|to)\s*(?P<b>\d{1,3}))?\s*%"
)


def biomarker_status(text: str) -> list[Atom]:
    """Each named biomarker's states a criterion allows: positive, negative, unknown (pure — pinned).

    For each gene named as the tumour's attribute (not as a drug's target: "anti-PD-1", "EGFR TKI"), within
    its clause (bounded by ".", ";" or a line break): a negation or unknown word before the name (negative,
    wild-type, absence, no, without, unknown) decides, unless a presence word (presence, positive, has,
    harbour) stands between it and the name; the states are negative, unknown or both, as the words before the
    name say. Otherwise the nearest state word after the name decides, else the nearest before it: positive
    (positive, mutation, fusion, rearrangement, translocation, amplification, a named variant), negative or
    unknown. "positive" within 20 characters after the name ("ALK fusion positive") outranks an earlier
    negation. A gene named as a drug's target (after "anti", "targeting", "directed against", "inhibitor of",
    or before "inhibitor", "TKI", "antibody", "therapy") or after "any" gives no atom. A PD-L1 percentage is
    kept as written. A clause that says the patients so described "are excluded" adds the param
    text_polarity=excluded, which turns an inclusion criterion's atom into an exclusion. A gene with no state
    word and no percentage: no atom.
    """
    atoms = []
    for match in _GENE.finditer(text):
        gene = next(name for name in GENES if match.group(name.replace("-", "_")))
        if (
            _AS_AGENT.match(text[match.end() :])
            or _ANTI.search(text[max(0, match.start() - 25) : match.start()])
            or _ANY.search(text[max(0, match.start() - 6) : match.start()])
        ):
            continue
        clause_start = max(text.rfind(mark, 0, match.start()) for mark in (".", ";", "\n")) + 1
        ends = [i for i in (text.find(mark, match.end()) for mark in (". ", ";", "\n")) if i >= 0]
        clause_end = min(ends, default=len(text))
        before = list(_STATE.finditer(text, clause_start, match.start()))
        after = list(_STATE.finditer(text, match.end(), clause_end))
        params: tuple[tuple[str, str], ...] = ()
        if gene == "PD-L1":
            percent = _PERCENT.search(text, match.end(), min(clause_end, match.end() + 60))
            if percent:
                params = (("expression", re.sub(r"\s+", "", percent.group(0)).replace("\\", "")),)
        negations = [s for s in before if not s.group("pos")]
        stated_positive = re.match(r"[\w\s-]{0,20}?positive", text[match.end() : clause_end], re.IGNORECASE)
        values: set[str] = set()
        if stated_positive:
            values = {"positive"}
        elif negations and not _PRESENCE.search(text, negations[-1].end(), match.start()):
            values = {"negative" if s.group("neg") else "unknown" for s in negations}
        elif after or before:
            state = after[0] if after else before[-1]
            values = {"negative" if state.group("neg") else "unknown" if state.group("unk") else "positive"}
        if not values and _DOCUMENTED.search(text, clause_start, clause_end):
            values = {"negative", "positive"}  # a documented status is known: either, never unknown
        if not values and not params:
            continue
        if _EXCLUDED.search(text, match.end(), clause_end):
            params = (*params, ("text_polarity", "excluded"))
        atoms.append(("biomarker:" + gene, tuple(sorted(values)), params, match.start(), match.end()))
    return atoms


# ── prior therapy ───────────────────────────────────────────────────────────────────────────────────

_ADVANCED = re.compile(
    r"advanced|metasta|stage\s*(?:IV|Ⅳ|III[BC]|Ⅲ[BC])|recurren|first[- ]line", re.IGNORECASE
)
_NO_PRIOR = re.compile(
    r"(?:\bno\b|not (?:have |had |been )?(?:received|treated with)(?: any)?|"
    r"never (?:received|been treated)|without)"
    r"\s+(?:any\s+)?(?:prior|previous)?\s*(?:systemic|chemotherapy|anti-?\s?(?:tumou?r|cancer|neoplastic)|"
    r"first[- ]line)"
    r"|(?:treatment|chemotherapy|therapy|systemic(?: therapy)?)[- ]na[iï]ve|previously untreated"
    r"|untreated (?:advanced|metastatic|locally advanced|stage|recurrent|NSCLC|non-small)",
    re.IGNORECASE,
)
_COUNT_WORDS = (
    (r"(?:1|one) or (?:2|two)", ("1", "2")),
    (r"(?:at least|≥|>=|\\>=)\s*(?:2|two)|(?:2|two) or more", ("2", "3+")),
    (r"(?:at least|≥|>=|\\>=)\s*(?:1|one)|(?:1|one) or more", ("1", "2", "3+")),
    (r"(?:no more than|not more than|at most|≤|<=|\\<=)\s*(?:1|one)", ("0", "1")),
    (r"(?:no more than|not more than|at most|≤|<=|\\<=)\s*(?:2|two)", ("0", "1", "2")),
    (r"(?:only )?(?:1|one)(?! or)", ("1",)),
    (r"(?:2|two)(?! or)", ("2",)),
)
_PRIOR_COUNT = re.compile(
    r"(?P<count>" + "|".join(f"(?:{words})" for words, _ in _COUNT_WORDS) + r")\s+"
    r"(?:prior\s+|previous\s+)?(?:line|regimen|platinum|systemic|chemotherapy|treatment)",
    re.IGNORECASE,
)
_PROGRESSED = re.compile(
    r"(?:progress(?:ed|ion|ive disease)?|relapsed?|recurr\w*|failed|failure|intoleran\w*)\s+"
    r"(?:\w+\s+){0,3}?(?:on|after|during|following|to|of)\b"
    r"(?=[^.;]{0,40}?(?:therap|treatment|regimen|chemotherapy|platinum|TKI|inhibitor|immunotherapy|agent|"
    r"\bline|drug|antibod|docetaxel|pemetrexed))",
    re.IGNORECASE,
)
AGENT_WORDS = {
    "PD-1": r"anti[- ]?PD[- ]?1|PD[- ]?1 (?:inhibitor|antibod|blockade|blocking|drugs?|therap)",
    "PD-L1": r"anti[- ]?PD[- ]?L1|PD[- ]?L1 (?:inhibitor|antibod|blockade|blocking|drugs?|therap)",
    "CTLA-4": r"anti[- ]?CTLA[- ]?4|CTLA[- ]?4 (?:inhibitor|antibod)",
    "immune checkpoint": r"immune[- ]checkpoint|checkpoint inhibitor|immunotherapy",
    "EGFR inhibitor": r"EGFR[- ](?:TKI|tyrosine kinase inhibitor|inhibitor|directed|targeted)",
    "ALK inhibitor": r"ALK[- ](?:TKI|tyrosine kinase inhibitor|inhibitor|directed|targeted)",
    "MET inhibitor": r"c?-?MET[- ](?:TKI|inhibitor|targeted|directed)",
    "platinum": r"platinum|cisplatin|carboplatin",
    "docetaxel": r"docetaxel",
    "taxane": r"taxane|paclitaxel",
    "pemetrexed": r"pemetrexed",
    "VEGF inhibitor": r"bevacizumab|anti[- ]?VEGF|VEGF(?:R)? (?:inhibitor|antibod)",
    "chemotherapy": r"chemotherapy",
    "radiotherapy": r"radiotherapy|radiation therapy|chemoradiation|chemoradiotherapy",
}
_AGENT = re.compile("|".join(f"(?P<a{i}>{p})" for i, p in enumerate(AGENT_WORDS.values())), re.IGNORECASE)
_EXPOSURE = re.compile(
    r"prior|previous|previously|received|treated with|exposure|progress|after|following", re.IGNORECASE
)


def prior_therapy(text: str) -> list[Atom]:
    """Prior lines of systemic therapy, and prior agents, as a criterion states them (pure — pinned).

    prior_lines: "no prior systemic therapy", "treatment-naive", "previously untreated" give 0; a count of
    prior lines or regimens gives its values (1, 2, "3+"; "at least one" is 1, 2, 3+); progression, relapse,
    failure or intolerance on or after a therapy, with no count, gives 1, 2, 3+. Its param scope is
    "advanced" when the criterion names advanced, metastatic, stage IIIB/IIIC/IV, recurrent or first-line
    disease, else "unspecified". prior_agent: each agent-class word named in a criterion that speaks of
    prior exposure (prior, previous, received, treated with, after, following, progression). Nothing stated:
    no atom.
    """
    atoms: list[Atom] = []
    scope = (("scope", "advanced" if _ADVANCED.search(text) else "unspecified"),)
    zero = _NO_PRIOR.search(text)
    count = _PRIOR_COUNT.search(text)
    progressed = _PROGRESSED.search(text)
    if zero:
        atoms.append(("prior_lines", ("0",), scope, zero.start(), zero.end()))
    elif count:
        words = count.group("count")
        values = next(v for pattern, v in _COUNT_WORDS if re.fullmatch(pattern, words, re.IGNORECASE))
        atoms.append(("prior_lines", values, scope, count.start(), count.end()))
    elif progressed:
        atoms.append(("prior_lines", ("1", "2", "3+"), scope, progressed.start(), progressed.end()))
    if _EXPOSURE.search(text):
        names = list(AGENT_WORDS)
        for agent in _AGENT.finditer(text):
            name = names[int(next(key for key, value in agent.groupdict().items() if value)[1:])]
            atoms.append(("prior_agent", (name,), (), agent.start(), agent.end()))
    return atoms


# ── stage, extent and setting ───────────────────────────────────────────────────────────────────────

_ROMAN = str.maketrans({"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV"})
# A negation ending just before a stage or extent word: "no", "not", "without", "excluding", "other than".
_NEGATED = re.compile(
    r"\b(?:no|not|without|excluding|except|other than|non)\b[\w\s,/-]{0,20}$", re.IGNORECASE
)
_STAGE_TOKEN = r"(?:IV|I{1,3}|Ⅰ|Ⅱ|Ⅲ|Ⅳ)[ABCabc]?\d?"
_STAGE = re.compile(
    rf"\bstages?\s*(?P<expr>{_STAGE_TOKEN}(?:(?:\s*\([^()]{{0,40}}\))?\s*(?:-|–|to|/|,|and|or|through)\s*"
    rf"(?:stage\s*)?{_STAGE_TOKEN})*)\b",
    re.IGNORECASE,
)
_GROUPS = ("I", "II", "III", "IV")
EXTENT_WORDS = {
    "metastatic": r"\bmetastatic\b",
    "locally advanced": r"locally[- ]advanced",
    "advanced": r"(?<!locally )(?<!locally-)\badvanced\b",
    "unresectable": r"unresectable|not amenable to (?:curative )?(?:surgery|resection)|inoperable",
    "recurrent": r"\brecurren(?:t|ce)\b",
}
SETTING_WORDS = {
    "adjuvant": r"(?<!neo)(?<!neo-)\badjuvant\b",
    "neoadjuvant": r"\bneo-?adjuvant\b",
    "perioperative": r"\bperi-?operative\b",
    "consolidation": r"\bconsolidation\b",
    "maintenance": r"\bmaintenance\b",
}
_RESECTED = re.compile(
    r"(?:complete(?:ly)?|surgical(?:ly)?|radical(?:ly)?)\s+resect\w*|\bresected\b|\bR0\b", re.IGNORECASE
)
_RESECTABLE = re.compile(r"\bresectable\b|candidates? for (?:complete )?(?:resection|surgery)", re.IGNORECASE)
# A resection counts as the trial's tumour's only near the lung tumour, not near another malignancy, not
# negated ("cannot be completely resected", "incompletely resected") and not as a specimen's source.
_LUNG = re.compile(r"NSCLC|non-small|lung|primary tumou?r", re.IGNORECASE)
_OTHER_SITE = re.compile(
    r"skin|prostate|breast|cervi|bladder|thyroid|malignan|carcinoma in situ", re.IGNORECASE
)
_NOT_RESECTED = re.compile(r"cannot(?: be)?|\bnot(?: be)?\b|incomplete(?:ly)?", re.IGNORECASE)
_SPECIMEN = re.compile(r"\s*(?:tumou?r\s+)?(?:samples?|specimens?|tissues?)", re.IGNORECASE)


def _stage_groups(expression: str) -> tuple[str, ...]:
    """The major stage groups (I to IV) an expression spans: a range covers every group between its ends."""
    tokens = re.findall(r"IV|III|II|I", expression.translate(_ROMAN).upper())
    indices = [_GROUPS.index(token) for token in tokens]
    ranged = re.search(r"-|–|\bto\b|through", expression, re.IGNORECASE)
    if ranged and len(indices) >= 2:
        indices = list(range(min(indices), max(indices) + 1))
    return tuple(_GROUPS[i] for i in sorted(set(indices)))


def disease_setting(text: str) -> list[Atom]:
    """Stage groups, disease extent, resection status and treatment-setting words a criterion states
    (pure — pinned).

    stage: the major groups (I-IV) a "stage ..." expression spans, the expression kept as written; extent:
    metastatic, locally advanced, advanced, unresectable, recurrent; resection: "resected" (complete,
    surgical or radical resection, R0) or "resectable", only within 60 characters of the lung tumour (NSCLC,
    non-small, lung, primary tumour) and of no other site or malignancy, not negated ("cannot be", "not",
    "incompletely") and not a specimen's source ("resected samples");
    setting_word: adjuvant, neoadjuvant, perioperative, consolidation, maintenance. A stage or extent negated
    within the 30 characters before it ("no metastatic disease", "excluding stage IV") is no atom. Nothing
    stated: no atom.
    """
    atoms: list[Atom] = []
    for stage in _STAGE.finditer(text):
        groups = _stage_groups(stage.group("expr"))
        if groups and not _NEGATED.search(text[max(0, stage.start() - 30) : stage.start()]):
            atoms.append(
                ("stage", groups, (("expression", stage.group("expr")),), stage.start(), stage.end())
            )
    for concept, table in (("extent", EXTENT_WORDS), ("setting_word", SETTING_WORDS)):
        for name, pattern in table.items():
            for found in re.finditer(pattern, text, re.IGNORECASE):
                if concept == "extent" and _NEGATED.search(text[max(0, found.start() - 30) : found.start()]):
                    continue
                atoms.append((concept, (name,), (), found.start(), found.end()))
    for status, pattern in (("resected", _RESECTED), ("resectable", _RESECTABLE)):
        for found in pattern.finditer(text):
            near = text[max(0, found.start() - 60) : found.end() + 60]
            if (
                _LUNG.search(near)
                and not _OTHER_SITE.search(near)
                and not _NOT_RESECTED.search(text[max(0, found.start() - 25) : found.start()])
                and not _SPECIMEN.match(text[found.end() : found.end() + 15])
            ):
                atoms.append(("resection", (status,), (), found.start(), found.end()))
    return sorted(atoms, key=lambda atom: (atom[3], atom[0]))


# ── organ-function thresholds ───────────────────────────────────────────────────────────────────────

ANALYTES = {
    "neutrophils": r"absolute neutrophil count|neutrophils?(?: count)?|(?-i:\bANC\b)",
    "platelets": r"platelets?(?: count)?|(?-i:\bPLT\b)",
    "hemoglobin": r"ha?emoglobin|(?-i:\bHb\b|\bHGB\b)",
    "creatinine clearance": (
        r"creatinine clearance|glomerular filtration rate|(?-i:\bCrCl\b|\bCLcr\b|\beGFR\b)"
    ),
    "creatinine": r"(?:serum )?creatinine(?! clearance)|(?-i:\bCr\b)",
    "bilirubin": r"(?:total |serum )?bilirubin|(?-i:\bTBIL\b)",
    "AST": r"aspartate (?:amino)?transferase|(?-i:\bAST\b|\bSGOT\b)",
    "ALT": r"alanine (?:amino)?transferase|(?-i:\bALT\b|\bSGPT\b)",
    "albumin": r"albumin",
    "leukocytes": r"leukocytes?|white blood cells?(?: count)?|(?-i:\bWBC\b)",
}
# Names match in any case; acronyms only as written, so "eGFR" (kidney) is never "EGFR" (the gene).
_ANALYTE = re.compile("|".join(f"(?P<n{i}>{p})" for i, p in enumerate(ANALYTES.values())), re.IGNORECASE)
_COMPARATORS = (
    (r"≥|>=|=\\?>|\\>=|\\>/=|>/=|greater than or equal to|at least|no less than|not less than", "≥"),
    (r"≤|<=|=\\?<|\\<=|\\</=|</=|less than or equal to|no (?:more|greater) than|not exceed\w*|up to", "≤"),
    (r">|\\>|greater than|more than|above|exceeding", ">"),
    (r"<|\\<|less than|below", "<"),
)
_THRESHOLD = re.compile(
    r"(?P<cmp>" + "|".join(p for p, _ in _COMPARATORS) + r")\s*(?P<value>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>(?:[×xX*]|times)\s*(?:the\s+)?(?:institutional\s+)?(?:upper limit of normal|ULN)|"
    r"[×xX*]\s*10\s*(?:\^|e)?\s*(?:9|⁹|12)\s*/\s*L|×\s*10⁹/L|/\s*(?:mm3|mm³|µL|μL|uL|L)|"
    r"/\s*mcL|g/dL|g/L|mg/dL|mg/dl|µmol/L|μmol/L|umol/L|mL/min(?:/1\.73\s*m(?:2|²))?"
    r"|ml/min(?:/1\.73\s*m(?:2|²))?|%)?",
    re.IGNORECASE,
)
_UNSPECIFIED = re.compile(
    r"adequate\s+(?:(?:baseline\s+)?(?:end-organ|organ|bone marrow|hematologic|haematologic|hepatic"
    r"|liver|renal|"
    r"kidney)(?:\s*(?:,|and|or)\s*)?)+\s*(?:and\s+\w+\s+)?function"
    r"|(?:major )?organ (?:and bone marrow )?functions? (?:that )?(?:meets?|that meet)",
    re.IGNORECASE,
)


def organ_function(text: str) -> list[Atom]:
    """Laboratory thresholds a criterion states, and unspecified "adequate organ function" (pure — pinned).

    lab: an analyte (neutrophils, platelets, hemoglobin, creatinine clearance, creatinine, bilirubin, AST,
    ALT, albumin; "eGFR" in that case is kidney function, never the EGFR gene) followed within 40 characters
    by a comparator and a number, with the unit as written (× ULN, × 10^9/L, mg/dL, mL/min ...), the
    comparator normalised to ≥, ≤, > or <, never a converted value. organ_function_unspecified: "adequate
    organ / hematologic / hepatic / renal function" with no threshold in the criterion. Nothing: no atom.
    """
    atoms: list[Atom] = []
    names = list(ANALYTES)
    for analyte in _ANALYTE.finditer(text):
        name = names[int(next(key for key, value in analyte.groupdict().items() if value)[1:])]
        threshold = _THRESHOLD.search(text, analyte.end())
        if not threshold or threshold.start() - analyte.end() > 40:
            continue
        found = [threshold]
        following = _THRESHOLD.search(text, threshold.end())
        if (
            following
            and following.start() - threshold.end() <= 30
            and re.search(r"\b(?:or|and)\b", text[threshold.end() : following.start()], re.IGNORECASE)
        ):
            found.append(following)
        for each in found:
            comparator = next(
                sign
                for pattern, sign in _COMPARATORS
                if re.fullmatch(pattern, each.group("cmp"), re.IGNORECASE)
            )
            params = (
                ("comparator", comparator),
                ("value", each.group("value")),
                ("unit", (each.group("unit") or "").strip()),
            )
            qualifier = re.match(r"\s*\(([^()]{1,30})\)", text[each.end() :])
            if qualifier and len(found) > 1:
                params = (*params, ("qualifier", qualifier.group(1).strip()))
            atoms.append(("lab", (name,), params, analyte.start(), each.end()))
    if not atoms:
        for found in _UNSPECIFIED.finditer(text):
            atoms.append(("organ_function_unspecified", ("adequate",), (), found.start(), found.end()))
    return atoms


# ── named conditions, boilerplate, age and histology ────────────────────────────────────────────────

# Each concept is a surface vocabulary as criteria write it (measured on the NSCLC residual); a match is the
# concept's atom, with any time window or CTCAE grade written beside it. The table names things; it states no
# relation between them, so whether a condition tracks a drug class is computed across trials and proposed.
CONDITIONS = {
    "informed_consent": r"informed consent|\bICF\b|sign(?:ed)? (?:the )?consent",
    "compliance": r"(?:willing|able|ability)\b[^.;]{0,40}\bcompl(?:y|iance)|follow[- ]up (?:procedures"
    r"|visits)",
    "contraception": r"contracepti\w+|birth control|abstinen\w+|sterili[sz]|\bcondoms?\b",
    "pregnancy_or_breastfeeding": r"(?<!of becoming )(?<!able to become )pregnan\w*"
    r"|breast[- ]?feeding|lactat\w+|nursing",
    "life_expectancy": r"life expectancy|expected survival|survival (?:duration"
    r"|time) (?:of )?(?:more than|≥|>)",
    "measurable_disease": r"measurable (?:disease|lesion)|RECIST",
    "cns_metastases": r"(?:brain|CNS|central nervous system|intracranial|cerebral)\W{0,3}metasta\w+"
    r"|leptomeningeal",
    "other_malignancy": r"(?:other|another|second|prior|previous|concurrent|additional"
    r"|active) (?:\w+ )?malignan\w+"
    r"|malignan\w+ other than|other (?:primary )?(?:cancer|tumou?r)s?\b",
    "hiv": r"\bHIV\b|human immunodeficiency virus|(?-i:\bAIDS\b)",
    "hepatitis": r"hepatitis|\bHBV\b|\bHCV\b|HBsAg",
    "tuberculosis": r"tubercul\w+",
    "active_infection": r"(?:active|acute|uncontrolled|serious|severe|systemic)\s+(?:\w+\s+){0,3}infections?",
    "autoimmune_disease": r"autoimmun\w+|immune[- ]mediated disease",
    "pneumonitis_ild": r"pneumonitis|interstitial lung disease|\bILD\b|pulmonary fibrosis"
    r"|organi[sz]ing pneumonia",
    "organ_transplant": r"transplant",
    "immunosuppression_steroids": r"immunosuppress\w+ "
    r"(?:therap\w+|treatment|drugs?|agents?|medications?|medicinal)"
    r"|systemic immunosuppression|immunosuppressants?|corticosteroid|steroid|prednison\w*",
    "qtc": r"\bQTc\w*\b|QT interval|QT prolongation",
    "cardiac_disease": r"myocardial infarction|heart failure|\bNYHA\b|angina|arrhythmi\w+|cardiomyopath\w+"
    r"|cardiac (?:disease|dysfunction|event)|cardiovascular disease|LVEF|ejection fraction",
    "hypertension": r"hypertension|blood pressure",
    "bleeding_thrombosis": r"bleeding|haemorrhag\w+|hemorrhag\w+|haemoptysis|hemoptysis|coagulopath\w+"
    r"|thrombo\w+|embolism|bleeding diathesis",
    "anticoagulant_use": r"anticoagula\w+|antiplatelet|\bheparin\b|\bwarfarin\b|\bLMWH\b",
    "gi_perforation_fistula": r"perforation|fistula|bowel obstruction|intestinal obstruction",
    "malabsorption": r"malabsorption|swallow|absorption of (?:oral )?(?:medication|drug)",
    "hypersensitivity": r"hypersensitiv\w+|allerg\w+|anaphyla\w+",
    "live_vaccine": r"(?:live|attenuated)[\w\s-]{0,20}vaccin\w+",
    "recent_surgery": r"(?:major )?surg(?:ery|ical procedure)\w*|thoracotomy",
    "recent_radiotherapy": r"radiotherapy|radiation therapy|irradiat\w+|radiosurgery",
    "unresolved_toxicity": r"toxicit(?:y|ies)[^.;]{0,60}(?:resolved|recover)|(?:resolved"
    r"|recover\w*)[^.;]{0,40}"
    r"grade|CTCAE",
    "tissue_available": r"(?:archiv\w+|fresh)[\w\s-]{0,30}(?:tissue|tumou?r sample|biopsy|specimen)"
    r"|tissue (?:sample )?(?:available|availability)",
    "other_investigational": r"(?:other|another) (?:clinical )?(?:study|trial|investigational)"
    r"|(?<!with )investigational (?:drug|agent|product|device)(?! administration)",
    "interacting_medication": r"CYP\s?3A\w*|strong (?:inhibitors?|inducers?)|P-?gp"
    r"|concomitant (?:medication|use)",
    "substance_or_psychiatric": r"psychiatric|substance abuse|drug abuse|alcohol",
    "smoking": r"smok\w+|tobacco|pack[- ]years?",
    "effusion": r"effusion|ascites",
    "neurologic_disorder": r"seizure|epilep\w+|encephalitis|meningitis|neurolog\w+ (?:disorder|disease)",
    "pulmonary_function": r"pulmonary function|lung function|\bFEV1\b|\bDLCO\b",
    "weight_loss": r"weight loss",
    "investigator_judgment": r"investigator(?:'s)? (?:opinion|judge?ment|discretion)|in the opinion of",
    "serious_comorbidity": r"(?:serious|significant|uncontrolled|severe) (?:\w+ ){0,2}"
    r"(?:comorbidit\w+|illness|medical conditions?)",
    "sex": r"both sexes|\bmale (?:or|and) female|\bmales? (?:or|and) females?|either sex|all genders",
    "diagnosis_confirmed": r"histolog\w+|cytolog\w+|patholog\w+ (?:confirmed|diagnosis|proven)",
    "prior_enrollment": r"already (?:been )?(?:included|enrolled|randomi[sz]ed)|previously (?:enrolled"
    r"|randomi[sz]ed)",
    "vitamin_premedication": r"(?:take|taking|receive|use|supplement\w*|premedicat\w+|pre-?treat\w*)"
    r"[\w\s,/-]{0,30}(?:folic acid|vitamin B-?12)"
    r"|(?:folic acid|vitamin B-?12)[\w\s,/-]{0,30}(?:supplement\w*|premedicat\w+|pre-?treat\w*|injection)",
    "organ_impairment": r"hepatic impairment|renal (?:impairment|failure|insufficiency)|cirrhosis"
    r"|liver disease",
}
_CONDITION = re.compile("|".join(f"(?P<c{i}>{p})" for i, p in enumerate(CONDITIONS.values())), re.IGNORECASE)
_WINDOW = re.compile(
    r"(?:within|in the (?:last|past|previous)|during the (?:last|past|previous)|for at least|at least|"
    r"≥|>=|\\>=)\s*(?:(?:the\s+)?(?:prior|past|last|previous)\s+)?(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|months?|years?|half-lives)\b"
    r"(?:\s*(?:prior|before|of|from|after|preceding))?"
    r"|(?P<n2>\d+(?:\.\d+)?)\s*(?P<unit2>days?|weeks?|months?|years?|half-lives)\s+(?:prior|before|preceding|ago)\b",
    re.IGNORECASE,
)
# A negation just before a condition's mention, in its clause: "non-pregnant", "negative pregnancy test",
# "to avoid pregnancy", "unless using effective contraception", "unwillingness to use birth control".
_NEGATED_MENTION = re.compile(
    r"\b(?:non|not(?! limited| only)|no|negative|without|avoid\w*|unwilling\w*|unable to|unless)\b"
    r"[\w\s,/-]{0,40}$",
    re.IGNORECASE,
)
_GRADE = re.compile(r"grade\s*(?P<cmp>≤|<=|\\<=|>|≥|>=|\\>=|<)?\s*(?P<g>[0-5])", re.IGNORECASE)


def named_conditions(text: str) -> list[Atom]:
    """Each named condition, procedure or protocol requirement a criterion mentions (pure — pinned).

    Every concept of CONDITIONS whose words appear gives one atom (the first mention), with the span of its
    words; a time window ("within 4 weeks", "in the last 5 years", "30 days prior") within 60 characters
    after it, and a CTCAE grade ("grade ≤ 1") in the criterion, are kept as written in its params. The
    values are ("mentioned",): whether the criterion requires, allows or excludes the condition is its section
    and wording, recorded elsewhere, never guessed here. Nothing named: no atom.
    """
    atoms: list[Atom] = []
    names = list(CONDITIONS)
    seen: set[str] = set()
    for found in _CONDITION.finditer(text):
        name = names[int(next(key for key, value in found.groupdict().items() if value)[1:])]
        if name in seen:
            continue
        seen.add(name)
        params: list[tuple[str, str]] = []
        window = _WINDOW.search(text, found.end(), min(len(text), found.end() + 60))
        if window:
            amount, unit = (
                window.group("n") or window.group("n2"),
                window.group("unit") or window.group("unit2"),
            )
            params.append(("window", f"{amount} {unit.lower()}"))
        grade = _GRADE.search(text)
        if grade:
            params.append(("grade", f"{(grade.group('cmp') or '').replace(chr(92), '')}{grade.group('g')}"))
        clause_start = max(text.rfind(mark, 0, found.start()) for mark in (". ", ";", "\n")) + 1
        if _NEGATED_MENTION.search(text[clause_start : found.start()]):
            params.append(("text_polarity", "excluded"))
        atoms.append(("condition", (name,), tuple(params), found.start(), found.end()))
    return atoms


_AGE = re.compile(
    r"(?:aged?|years? of age|years old|age (?:of|at)|≥|>=|\\>=|at least|older than|over)\s*[:\-]?\s*"
    r"(?P<a>\d{1,3})\s*(?:(?:-|–|to|and)\s*(?P<b>\d{1,3}))?\s*(?:years?|yrs?)?",
    re.IGNORECASE,
)


# "≥ 18 years" with no other word for age, but never a duration ("≥ 5 years prior", "within 3 years").
_BARE_AGE = re.compile(
    r"(?:≥|>=|\\>=|over|older than)\s*(?P<a>\d{2})\s*years?\b(?!\s*(?:prior|before|ago|since|after|from))"
    r"(?P<b>)",
    re.IGNORECASE,
)
_AGE_UPPER = re.compile(
    r"(?:<|≤|<=|\\<|\\<=|younger than|under|no older than|not older than)\s*(?P<n>\d{2})\b"
)


def age_limits(text: str) -> list[Atom]:
    """An age range a criterion states, in years as written (pure — pinned).

    "aged 18 to 75 years", "≥ 18 years of age", "age ≥ 18", "≥ 18 years and <75 years": the lower bound,
    and an upper bound when the range or a following "<", "≤", "younger than" gives one, as params; only when
    the criterion speaks of age (age, aged, years of age, years old) or states "≥ N years" that is no
    duration ("prior", "before", "ago").
    Values ("stated",). No age: no atom.
    """
    bare = _BARE_AGE.search(text)
    if not bare and not re.search(r"\bage\b|\baged\b|years of age|years old", text, re.IGNORECASE):
        return []
    found = _AGE.search(text) or bare
    if not found:
        return []
    params = [("minimum", found.group("a"))]
    upper = _AGE_UPPER.search(text, found.end())
    if found.group("b"):
        params.append(("maximum", found.group("b")))
    elif upper:
        params.append(("maximum", upper.group("n")))
    return [("age", ("stated",), tuple(params), found.start(), found.end())]


HISTOLOGY = {
    "non_squamous": r"non[- ]?squamous|\bnsNSCLC\b",
    "squamous": r"(?<!non-)(?<!non )(?<!non)squamous",
    "adenocarcinoma": r"adenocarcinoma",
    "large_cell": r"large[- ]cell",
    "small_cell": r"small[- ]cell (?:lung )?(?:cancer|carcinoma)|\bSCLC\b",
}
_HISTOLOGY = re.compile("|".join(f"(?P<h{i}>{p})" for i, p in enumerate(HISTOLOGY.values())), re.IGNORECASE)


def histology(text: str) -> list[Atom]:
    """The histologies a criterion names, each once, as written (pure — pinned).

    non_squamous ("non-squamous", "nsNSCLC"), squamous (not preceded by "non"), adenocarcinoma, large_cell,
    small_cell ("small cell lung cancer", "SCLC"; "non-small cell" is never small cell). No histology: no
    atom. Whether it is required or excluded is the criterion's section.
    """
    atoms: list[Atom] = []
    names = list(HISTOLOGY)
    seen: set[str] = set()
    for found in _HISTOLOGY.finditer(text):
        name = names[int(next(key for key, value in found.groupdict().items() if value)[1:])]
        if name == "small_cell" and re.search(
            r"non[- ]?$", text[max(0, found.start() - 4) : found.start()], re.I
        ):
            continue
        if _OTHER_SITE.search(text[max(0, found.start() - 40) : found.end() + 40]):
            continue  # "squamous cell carcinoma of the skin" is another malignancy, not this tumour
        if name not in seen:
            seen.add(name)
            atoms.append(("histology", (name,), (), found.start(), found.end()))
    return atoms


# ── outcomes and record-stated targets ──────────────────────────────────────────────────────────────

ENDPOINTS = {
    "overall_survival": r"overall survival|(?-i:\bOS\b)",
    "progression_free_survival": r"progression[- ]free survival|(?-i:\bPFS\d?\b)",
    "objective_response_rate": r"objective response|overall response rate|best overall response"
    r"|(?-i:\bORR\b)",
    "disease_free_survival": r"disease[- ]free survival|(?-i:\bDFS\b)",
    "event_free_survival": r"event[- ]free survival|(?-i:\bEFS\b)",
    "duration_of_response": r"duration of (?:\w+ )?response|(?-i:\bDoR\b|\bDOR\b)",
    "disease_control_rate": r"disease control|clinical benefit rate|(?-i:\bDCR\b)",
    "pathologic_complete_response": r"pathologic(?:al)? complete response|(?-i:\bpCR\b)",
    "major_pathologic_response": r"major patholog\w+ response|(?-i:\bMPR\b)",
    "time_to_progression": r"time to (?:\w+ )?progression|time to treatment failure|(?-i:\bTTP\b)",
    "intracranial_response": r"intracranial|(?-i:CNS) (?:objective )?response|(?-i:CNS) progression",
    "safety": r"adverse events?|toxicit\w+|safety|tolerability|dose[- ]limiting"
    r"|(?-i:\bAEs?\b|\bTEAEs?\b|\bSAEs?\b)",
    "quality_of_life": r"quality of life|patient[- ]reported|EORTC|QLQ|LCSS|EQ-5D"
    r"|(?-i:\bQoL\b|\bHRQoL\b|\bPRO\b)",
    "pharmacokinetics": r"pharmacokinetic|concentration|clearance|half-life|(?-i:\bPK\b|\bCmax\b|\bAUC\b)",
    "immunogenicity": r"anti-drug antibod\w+|immunogenicity|neutrali[sz]ing antibod|(?-i:\bADA\b)",
    "biomarker_endpoint": r"ctDNA|circulating tumou?r DNA|biomarker|PD-L1 expression"
    r"|tumou?r mutational burden",
}
# Words in any case ("Overall Survival"); acronyms only as written, so "os" or "pro" in prose is no endpoint.
_ENDPOINT = re.compile("|".join(f"(?P<e{i}>{p})" for i, p in enumerate(ENDPOINTS.values())), re.IGNORECASE)
_TIME_POINT = re.compile(
    r"(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>days?|weeks?|months?|years?|cycles?|hours?)\b", re.IGNORECASE
)


def endpoint_classes(measure: str) -> list[str]:
    """The endpoint classes an outcome measure's title names, in the order first named (pure — pinned).

    Overall, progression-free, disease-free and event-free survival, objective response, duration of
    response, disease control, pathologic complete and major pathologic response, time to progression,
    intracranial response, safety, quality of life, pharmacokinetics, immunogenicity and biomarker endpoints,
    each by its words or its acronym as written (acronyms only in capitals: "OS", "PFS"). Each class once. A
    title naming none: an empty list, never a guessed class.
    """
    names = list(ENDPOINTS)
    found: dict[str, None] = {}
    for match in _ENDPOINT.finditer(measure):
        name = names[int(next(key for key, value in match.groupdict().items() if value)[1:])]
        found.setdefault(name, None)
    return list(found)


def time_points(time_frame: str) -> list[str]:
    """The time points a time frame states, as "N unit" (unit singular, lower case), in order, each once
    (pure — pinned). "Up to approximately 3 years" gives ["3 year"]; "Week 3 - Week 96" gives none (no
    number precedes a unit). A time frame with none: an empty list."""
    found: dict[str, None] = {}
    for match in _TIME_POINT.finditer(time_frame):
        unit = match.group("unit").lower().rstrip("s")
        found.setdefault(f"{match.group('n')} {unit}", None)
    return list(found)


def stated_targets(description: str) -> list[str]:
    """The drug classes an intervention's or arm's own description states (pure — pinned).

    The agent words of the prior-therapy vocabulary (anti-PD-1, PD-L1 inhibitor, CTLA-4, EGFR or ALK
    inhibitor, MET inhibitor, VEGF inhibitor, platinum, taxane ...), each once in the order first named; used
    for an intervention RxClass does not classify, and marked as stated by the record. None named: an empty
    list.
    """
    names = list(AGENT_WORDS)
    found: dict[str, None] = {}
    for agent in _AGENT.finditer(description):
        found.setdefault(names[int(next(key for key, value in agent.groupdict().items() if value)[1:])], None)
    found.pop("chemotherapy", None)
    found.pop("radiotherapy", None)
    return list(found)


BANKS = {
    "performance_status": performance_status,
    "biomarker": biomarker_status,
    "prior_therapy": prior_therapy,
    "setting": disease_setting,
    "organ_function": organ_function,
    "conditions": named_conditions,
    "age": age_limits,
    "histology": histology,
}


_PERMITTED = re.compile(r"\b(?:permissible|permitted|allowed)\b", re.IGNORECASE)


def permitted(text: str, start: int, end: int) -> bool:
    """Whether the sentence holding text[start:end] grants a permission rather than a requirement (pure —
    pinned): it says "permissible", "permitted" or "allowed" ("acceptable" describes a method, not a
    permission), and does not say the thing is excluded or not allowed. "All lines of prior therapy are
    permissible" permits; "prior therapy is not allowed" does not."""
    sentence_start = max(text.rfind(mark, 0, start) for mark in (". ", ";", "\n")) + 1
    ends = [i for i in (text.find(mark, end) for mark in (". ", ";", "\n")) if i >= 0]
    sentence = text[sentence_start : min(ends, default=len(text))]
    return bool(_PERMITTED.search(sentence)) and not _EXCLUDED.search(sentence)


def type_criterion(
    text: str,
) -> list[tuple[str, str, tuple[str, ...], tuple[tuple[str, str], ...], int, int]]:
    """Every bank's atoms for one criterion, each prefixed by its bank's name, in bank order; an atom in a
    sentence that grants a permission carries ("modality", "permitted"), so no reader takes it for a
    requirement."""
    atoms = [(bank, *atom) for bank, function in BANKS.items() for atom in function(text)]
    return [
        (
            bank,
            concept,
            values,
            (*params, ("modality", "permitted")) if permitted(text, s, e) else params,
            s,
            e,
        )
        for bank, concept, values, params, s, e in atoms
    ]
