"""Independent, adversarial specification check for `evidence_requests` (tasks 2a.1-2a.3).

Written from SCHEMA.md, the parallel handoff and the symbolic-trial-design spec delta alone; the
implementation was not read. Authored positive and MUST-NOT intents:

* a returned row is a hypothetical investigation request, never an observation, premise or recommendation;
* a rejected partial profile eliminates a candidate only when no completion is ineligible under it, never
  by asserting the unspecified attribute or a universal exclusion of the partial profile;
* every row replays through the real `design_bounds` consumer to the same per-candidate verdicts and
  complete decisions;
* incomplete search, unresolved witnesses and unrepresented variables never become "no separator";
* output truncation is separate from search completion and never invents an omitted count.

Expected separator sets were confirmed by brute force over the declared cells with the real consumer
(scratch/oracle.py, scratch/oracle-output.txt), not by hand reasoning alone.

Tests that need the new module request the `evaluate` fixture and skip until it imports. The helper
self-tests at the top run today and prove the literal builders and the design_bounds round trip.
"""

from __future__ import annotations

import copy
import json
import re

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail, run

STUDY = "test:invented-study-version-not-registry-evidence"
GENERAL = r"^evidence_requests:[\w.]+:\w+"
GENERAL_OR_BOUND = r"^(evidence_requests:[\w.]+:\w+|resource_bound:evidence_requests:[\w.]+)"
ROW_FORBIDDEN = ("count", "bridge", "basis", "status")
OUTCOMES = {"separated", "no_separator", "not_separated_in_declared_variables", "search_incomplete"}
VERDICT_LISTS = {"ruled_out": "eliminates", "not_ruled_out": "accommodates", "unresolved": "undecided"}


# --------------------------------------------------------------------------------------------------------
# Model builders (canonical tagged JSON, exactly as bounds_guide.example() writes it)
# --------------------------------------------------------------------------------------------------------


def model(item):
    return json.loads(a.canonical(item))


RULE = a.Rule("invented-candidate", "1", warrants=("user:invented-candidate",))
PARTICIPANT = a.Subject("participant")
ENROLLMENT_EXPLICIT = a.TemporalScope(
    "at", "enrollment", certainty="explicit", evidence=(a.Evidence("text_span", "invented:span"),)
)
ENROLLMENT_BARE = a.TemporalScope("at", "enrollment")


def required(ident, body, status="known", cohort=a.EVERY_PARTICIPANT):
    return a.ScopedAssertion(
        ident,
        "invented:criterion",
        "required",
        body,
        cohort=cohort,
        rule=RULE,
        status=status,
        resolution="resolved",
    )


def ecog(comparison, number, unit="ECOG", key="ecog", time=None):
    return a.Literal(
        PARTICIPANT,
        a.Predicate("measurement", key),
        a.Value("quantity", comparison, number=number, unit=unit),
        time=time,
    )


def score(comparison, number):
    return ecog(comparison, number, unit="points", key="score")


def flag(key, holds=True):
    return a.Literal(
        PARTICIPANT,
        a.Predicate("defined_term", key),
        a.Value("boolean", "eq"),
        polarity="positive" if holds else "negative",
    )


def histology(comparison, *members):
    return a.Literal(
        PARTICIPANT,
        a.Predicate("disease_attribute", "histology"),
        a.Value("enum", comparison, members=tuple(members)),
    )


def interval(low, high, unit="ECOG", key="ecog", inclusivity="exclusive"):
    return a.Literal(
        PARTICIPANT,
        a.Predicate("measurement", key),
        a.Value("interval", "in", number=low, upper=high, unit=unit, inclusivity=inclusivity),
    )


def candidate(ident, *items):
    return {"id": ident, "assertions": [model(item) for item in items]}


def variable(ident, predicate, domain, time=None):
    return {
        "id": ident,
        "subject": model(PARTICIPANT),
        "predicate": model(predicate),
        "time": model(time) if time is not None else None,
        "domain": domain,
    }


def boolean_variable(ident, key, kind="defined_term"):
    return variable(ident, a.Predicate(kind, key), {"kind": "boolean"})


def integer_variable(ident="ecog", minimum=0, maximum=5, unit="ECOG", key="ecog", time=None):
    domain = {"kind": "integer", "unit": unit, "minimum": minimum, "maximum": maximum}
    return variable(ident, a.Predicate("measurement", key), domain, time)


def continuous_variable(ident="score", minimum=None, maximum=None, cut_points=(), unit="points", key="score"):
    domain = {
        "kind": "continuous",
        "unit": unit,
        "minimum": minimum,
        "maximum": maximum,
        "cut_points": list(cut_points),
    }
    return variable(ident, a.Predicate("measurement", key), domain)


def enum_variable(ident, members, open_):
    domain = {"kind": "enum", "members": list(members), "open": open_}
    return variable(ident, a.Predicate("disease_attribute", "histology"), domain)


def request(candidates, survivors, variables, **extra):
    body = {
        "operation": "evidence_requests",
        "study_ref": STUDY,
        "candidates": copy.deepcopy(candidates),
        "survivors": list(survivors),
        "survival_basis": ["invented:design-bounds-result-remaining"],
        "variables": copy.deepcopy(variables),
    }
    body.update(copy.deepcopy(extra))
    return body


# The handoff's clinical family: A = adult AND ECOG <= 2; B = A AND marker.
A = candidate("A", required("A_adult", flag("adult")), required("A_ecog", ecog("le", 2)))
B = candidate(
    "B",
    required("B_adult", flag("adult")),
    required("B_ecog", ecog("le", 2)),
    required("B_marker", flag("marker")),
)
HANDOFF_VARIABLES = [
    boolean_variable("adult", "adult"),
    integer_variable(),
    boolean_variable("marker", "marker"),
]
# Accepted/rejected cutoff pair.
X = candidate("X", required("X_ecog", ecog("le", 2)))
Y = candidate("Y", required("Y_ecog", ecog("le", 3)))
W = candidate("W", required("W_ecog", ecog("le", 4)))
# Two survivors equal on integers but different on the reals.
XL = candidate("XL", required("XL_ecog", ecog("le", 2)))
YL = candidate("YL", required("YL_ecog", ecog("lt", 3)))
# Logically equivalent on every value.
XQ = candidate("XQ", required("XQ_ecog", ecog("le", 2)))
YQ = candidate("YQ", required("YQ_ecog", a.Not(ecog("gt", 2))))
# An inconsistent survivor.
Z = candidate("Z", required("Z_low", ecog("le", 2)), required("Z_high", ecog("ge", 3)))


def handoff(**extra):
    extra.setdefault("limits", {"max_requests_per_pair": 20})
    return request([A, B], ["A", "B"], copy.deepcopy(HANDOFF_VARIABLES), **extra)


def cutoffs(**extra):
    return request([X, Y], ["X", "Y"], [integer_variable()], **extra)


# --------------------------------------------------------------------------------------------------------
# Oracles: meaning is tested through the existing solver, never through the row's chosen JSON layout
# --------------------------------------------------------------------------------------------------------


def normalize(value):
    return json.loads(json.dumps(value))


def as_json(profile):
    return json.loads(profile) if isinstance(profile, str) else profile


def as_model(profile):
    return a.from_canonical(json.dumps(as_json(profile)))


def implies(profile, query):
    """Every participant satisfying the profile satisfies the query (solver as oracle)."""
    premise = required("profile_premise", as_model(profile))
    return entail.decide((premise,), query).result == "ENTAILED"


def literal_set(profile):
    def flatten(item):
        if isinstance(item, a.AllOf):
            return [leaf for part in item.parts for leaf in flatten(part)]
        return [a.canonical(item)]

    return frozenset(flatten(as_model(profile)))


def codes(value):
    """Every string inside a nested value (keys included), for shape-tolerant cause lookup."""
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return set(value) | {text for item in value.values() for text in codes(item)}
    if isinstance(value, list | tuple):
        return {text for item in value for text in codes(item)}
    return set()


def specified_ids(row):
    specified = row["specified"]
    if isinstance(specified, dict):
        return set(specified)
    ids = set()
    for item in specified:
        ids.add(item if isinstance(item, str) else item.get("variable", item.get("id")))
    return ids


def searched(result):
    survivors = result["survivors"]
    if isinstance(survivors, dict):
        return list(survivors.get("searched", survivors.get("consistent", [])))
    return list(survivors)


def excluded(result):
    if "inconsistent" in result:
        return list(result["inconsistent"])
    return list(result["survivors"]["inconsistent"])


def all_causes(result):
    found = set(codes(result["search"].get("causes", [])))
    found |= codes(result["output"].get("causes", []))
    found |= codes(result.get("representation", {}))
    found |= codes(result.get("input_conflicts", []))
    for pair in result["pairs"]:
        found |= codes(pair.get("causes", []))
    return found


def pair_of(result, first, second):
    matches = [pair for pair in result["pairs"] if set(pair["candidates"]) == {first, second}]
    assert len(matches) == 1, result["pairs"]
    return matches[0]


def returned_for_pair(pair):
    value = pair["requests"]
    return value if isinstance(value, int) else len(value)


def checks_by_candidate(row):
    return {check["candidate"]: check for check in row["checks"]}


def design_bounds_replay(candidates, row, context=None, bound=4096):
    """The real consumer, given the row's profile as one attributed observation under a resolved, known
    bridge with no exception allowance and the row's sign. Returns {candidate: witness row}."""
    observation = {
        "id": "hypothetical-replay",
        "count": 1,
        "denominator": 1,
        "population": "invented:replayed-hypothetical-request",
        "body": as_json(row["profile"]),
        "context": context or {},
        "status": "known",
        "basis": ["invented:hypothetical-request-replay"],
        "direction": row["sign"],
        "bridge": {
            "status": "known",
            "resolution": "resolved",
            "max_exceptions": 0,
            "basis": ["invented:hypothetical-eligibility-bridge"],
        },
    }
    reply = run(
        normalize(
            {
                "operation": "design_bounds",
                "study_ref": STUDY,
                "candidates": candidates,
                "observations": [observation],
                "query": as_json(row["profile"]),
                "context": context or {},
                "bound": bound,
            }
        )
    )
    assert reply["code"] == "complete", reply
    return {item["id"]: item["observations"][0] for item in reply["result"]["candidates"]}


def check_invariants(result, sent):
    """Contract clauses every result must satisfy, whatever its scenario."""
    json.dumps(result, allow_nan=False)
    assert result["premises"] == sent
    assert result["study_ref"] == sent["study_ref"]
    assert "basis" in result
    assert isinstance(result["limits"], str) and result["limits"]
    assert result["family"] in ("conflict", "single_survivor", "searched")
    search, output = result["search"], result["output"]
    assert search["state"] in ("complete", "incomplete")
    assert output["state"] in ("complete", "truncated")
    rows = result["requests"]
    assert output["returned"] == len(rows)
    assert output["omitted"] == output["found"] - output["returned"] >= 0
    assert (output["state"] == "truncated") == (output["omitted"] > 0)
    survivors = set(searched(result))
    signs = set(sent.get("signs", ["accepted", "rejected"]))
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    sizes = [row["profile_size"] for row in rows]
    assert sizes == sorted(sizes), "least-specified rows first"
    for row in rows:
        assert row["kind"] == "hypothetical_evidence_request"
        assert row["observed"] is False
        assert not set(ROW_FORBIDDEN) & set(row), "a request row must not be able to pass as an observation"
        assert row["sign"] in signs
        assert row["profile_size"] == len(specified_ids(row)) >= 1
        assert isinstance(as_model(row["profile"]), a.PROPOSITIONS)
        checks = checks_by_candidate(row)
        assert set(checks) == survivors and len(row["checks"]) == len(survivors)
        for verdict, field in VERDICT_LISTS.items():
            assert set(row[field]) == {c for c, check in checks.items() if check["verdict"] == verdict}
        assert row["eliminates"] and row["accommodates"], "a returned row separates at least one pair"
        tokens = {
            t for t in codes(row["required_premises"]) if t.startswith("complete_candidate_eligibility:")
        }
        if row["sign"] == "rejected":
            assert tokens == {f"complete_candidate_eligibility:{c}" for c in row["eliminates"]}
        else:
            assert not tokens
        eliminating = tuple(checks[c]["decision"]["status"] or "known" for c in row["eliminates"])
        assert row["conditional_status"] == entail.weakest_status(eliminating)
    for pair in result["pairs"]:
        assert pair["outcome"] in OUTCOMES
        assert set(pair["candidates"]) <= survivors and len(set(pair["candidates"])) == 2
        assert (pair["outcome"] == "separated") == (pair["found"] > 0)
        assert returned_for_pair(pair) <= pair["found"]
        if search["state"] == "incomplete":
            assert pair["outcome"] in ("separated", "search_incomplete"), "no completed-absence claim"
        if isinstance(pair["requests"], list):
            for ident in pair["requests"]:
                row = next(row for row in rows if row["id"] == ident)
                first, second = pair["candidates"]
                assert {first, second} & set(row["eliminates"]) and {first, second} & set(row["accommodates"])
    if len(survivors) >= 2:
        assert len(result["pairs"]) == len(survivors) * (len(survivors) - 1) // 2


@pytest.fixture
def evaluate():
    module = pytest.importorskip("TrialLedger.layer2.evidence_requests")

    def call(sent):
        before = copy.deepcopy(sent)
        result = module.evaluate(sent)
        assert sent == before, "evaluate must not mutate its request"
        check_invariants(result, before)
        return result

    return call


@pytest.fixture
def refuse():
    module = pytest.importorskip("TrialLedger.layer2.evidence_requests")

    def call(sent, pattern):
        with pytest.raises(ValueError, match=pattern) as caught:
            module.evaluate(sent)
        return str(caught.value)

    return call


# --------------------------------------------------------------------------------------------------------
# Helper self-tests: run today, without the new module
# --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "item",
    [
        ecog("le", 2),
        flag("adult"),
        flag("marker", False),
        histology("in", "adeno"),
        histology("not_in", "adeno", "squamous"),
        score("lt", 10),
        interval(2, 3),
        ecog("le", 2, time=ENROLLMENT_EXPLICIT),
    ],
)
def test_helper_literals_are_accepted_by_real_entailment(item):
    reply = run(
        normalize(
            {
                "operation": "entailment",
                "assertions": [model(required("helper", item))],
                "query": model(item),
            }
        )
    )
    assert reply["code"] == "complete", reply
    assert reply["result"]["decision"]["result"] == "ENTAILED"


def test_replay_helper_full_rejected_profile_eliminates_a_and_fits_b():
    row = {
        "sign": "rejected",
        "profile": model(a.AllOf((flag("adult"), ecog("eq", 2), flag("marker", False)))),
    }
    states = design_bounds_replay([A, B], row)
    assert states["A"]["state"] == "ruled_out" and states["A"]["decision"]["result"] == "REFUTED"
    assert states["B"]["state"] == "not_ruled_out" and states["B"]["decision"]["result"] == "ENTAILED"


def test_replay_helper_partial_rejected_profile_eliminates_a_and_b_explains_by_unspecified_marker():
    row = {"sign": "rejected", "profile": model(a.AllOf((flag("adult"), ecog("eq", 2))))}
    states = design_bounds_replay([A, B], row)
    assert states["A"]["state"] == "ruled_out"
    assert states["B"]["state"] == "not_ruled_out"
    # Not universal exclusion: some completion is eligible under B, some is not.
    assert states["B"]["decision"]["result"] == "UNDETERMINED"
    assert states["B"]["decision"]["blockers"] == ("undecided_by_constraints",)


def test_replay_helper_rejected_ecog2_without_adulthood_must_not_eliminate_a():
    states = design_bounds_replay([A, B], {"sign": "rejected", "profile": model(ecog("eq", 2))})
    assert states["A"]["state"] == states["B"]["state"] == "not_ruled_out"


def test_replay_helper_known_refutation_survives_proposed_conjunct_for_acceptance_only():
    states = design_bounds_replay([X, Y], {"sign": "accepted", "profile": model(ecog("eq", 3))})
    assert states["X"]["state"] == "ruled_out" and states["Y"]["state"] == "not_ruled_out"
    mixed = candidate(
        "P2", required("P2_ecog", ecog("le", 3)), required("P2_marker", flag("marker"), status="proposed")
    )
    states = design_bounds_replay([mixed, W], {"sign": "accepted", "profile": model(ecog("eq", 4))})
    # No completion of the withheld conjunct can loosen the confirmed ECOG <= 3 requirement.
    assert states["P2"]["decision"]["result"] == "REFUTED"
    assert states["P2"]["decision"]["status"] == "known"
    assert states["P2"]["decision"]["proof"] == ("P2_ecog",)
    assert "proposed_refused:P2_marker" in states["P2"]["decision"]["blockers"]
    assert states["P2"]["state"] == "ruled_out" and states["W"]["state"] == "not_ruled_out"
    rejected = design_bounds_replay([mixed, W], {"sign": "rejected", "profile": model(ecog("eq", 2))})
    # The withheld marker can explain an eligibility rejection when the known cutoff is satisfied.
    assert rejected["P2"]["state"] == "unresolved"
    assert "proposed_refused:P2_marker" in rejected["P2"]["decision"]["blockers"]


def test_oracle_helpers_read_meaning_not_layout():
    profile = model(a.AllOf((flag("adult"), ecog("eq", 2))))
    assert implies(profile, ecog("eq", 2)) and implies(profile, flag("adult"))
    assert not implies(profile, flag("marker")) and not implies(profile, flag("marker", False))
    assert implies(model(interval(2, 3)), ecog("gt", 2)) and not implies(
        model(interval(2, 3)), ecog("eq", 2.5)
    )
    assert literal_set(profile) < literal_set(model(a.AllOf((flag("adult"), ecog("eq", 2), flag("marker")))))


def test_variable_helpers_name_the_survivors_literal_keys():
    literal = model(ecog("le", 2))
    declared = integer_variable()
    assert declared["subject"] == literal["subject"] and declared["predicate"] == literal["predicate"]
    assert declared["domain"]["unit"] == literal["value"]["unit"] and declared["time"] is literal["time"]


# --------------------------------------------------------------------------------------------------------
# The handoff's clinical example
# --------------------------------------------------------------------------------------------------------


def test_partial_rejected_adult_ecog2_profile_eliminates_a_and_accommodates_b(evaluate):
    result = evaluate(handoff())
    rows = [
        row
        for row in result["requests"]
        if row["sign"] == "rejected" and implies(row["profile"], ecog("eq", 2))
    ]
    assert len(rows) == 1
    row = rows[0]
    assert row["eliminates"] == ["A"] and row["accommodates"] == ["B"] and row["undecided"] == []
    assert specified_ids(row) == {"adult", "ecog"} and row["profile_size"] == 2
    assert implies(row["profile"], flag("adult"))
    checks = checks_by_candidate(row)
    assert checks["A"]["decision"]["result"] == "REFUTED"
    assert normalize(checks["A"]["decision"]["proof"]) == ["A_adult", "A_ecog"]
    assert checks["B"]["decision"]["result"] == "UNDETERMINED"
    assert normalize(checks["B"]["decision"]["blockers"]) == ["undecided_by_constraints"]


def test_partial_rejected_profile_must_not_assert_a_marker_value_or_universal_exclusion(evaluate):
    result = evaluate(handoff())
    for row in result["requests"]:
        if row["sign"] != "rejected":
            continue
        assert "marker" not in specified_ids(row)
        assert not implies(row["profile"], flag("marker"))
        assert not implies(row["profile"], flag("marker", False))
        # B can explain the rejection only through an unspecified completion; it never says every such
        # person is excluded (that would be ENTAILED: every completion ineligible).
        assert checks_by_candidate(row)["B"]["decision"]["result"] == "UNDETERMINED"
        assert row["observed"] is False


def test_full_marker_negative_profile_separates_but_must_not_be_returned_as_non_minimal(evaluate):
    full = model(a.AllOf((flag("adult"), ecog("eq", 2), flag("marker", False))))
    replay = design_bounds_replay([A, B], {"sign": "rejected", "profile": full})
    assert replay["A"]["state"] == "ruled_out" and replay["B"]["state"] == "not_ruled_out"
    result = evaluate(handoff())
    assert all(literal_set(row["profile"]) != literal_set(full) for row in result["requests"])
    assert not [row for row in result["requests"] if row["sign"] == "rejected" and row["profile_size"] == 3]


def test_rejected_ecog2_of_unknown_adulthood_must_not_eliminate_a(evaluate):
    result = evaluate(handoff())
    for row in result["requests"]:
        if "A" in row["eliminates"]:
            assert implies(row["profile"], flag("adult")), "a minor with ECOG 2 can explain rejection under A"


def test_accepted_marker_negative_eliminates_b_with_one_attribute(evaluate):
    result = evaluate(handoff())
    accepted = [row for row in result["requests"] if row["sign"] == "accepted"]
    assert len(accepted) == 1
    row = accepted[0]
    assert specified_ids(row) == {"marker"} and row["profile_size"] == 1
    assert implies(row["profile"], flag("marker", False))
    assert row["eliminates"] == ["B"] and row["accommodates"] == ["A"]


def test_handoff_minimal_separators_are_exactly_the_brute_force_set(evaluate):
    result = evaluate(handoff())
    assert result["family"] == "searched" and result["search"]["state"] == "complete"
    assert result["output"] == {
        **result["output"],
        "state": "complete",
        "found": 4,
        "returned": 4,
        "omitted": 0,
    }
    signatures = set()
    for row in result["requests"]:
        value = next((k for k in range(6) if implies(row["profile"], ecog("eq", k))), None)
        signatures.add((row["sign"], frozenset(specified_ids(row)), value))
    assert signatures == {
        ("accepted", frozenset({"marker"}), None),
        ("rejected", frozenset({"adult", "ecog"}), 0),
        ("rejected", frozenset({"adult", "ecog"}), 1),
        ("rejected", frozenset({"adult", "ecog"}), 2),
    }
    assert pair_of(result, "A", "B")["outcome"] == "separated"
    assert pair_of(result, "A", "B")["found"] == 4


# --------------------------------------------------------------------------------------------------------
# Every returned row replays through the real design_bounds consumer
# --------------------------------------------------------------------------------------------------------


P_PROPOSED = candidate("P", required("P_ecog", ecog("le", 2), status="proposed"))
XS = candidate("XS", required("XS_ecog", ecog("le", 2), cohort=a.Scope("cohort_ref", "c1")))
XI = candidate("XI", required("XI_ecog", ecog("le", 2), status="interpolated"))
HX = candidate("HX", required("HX_histology", histology("in", "adeno")))
HY = candidate("HY", required("HY_histology", a.Not(histology("eq", "squamous"))))
HZ = candidate("HZ", required("HZ_histology", histology("in", "adeno", "squamous")))
XC = candidate("XC", required("XC_score", score("le", 10)))
YC = candidate("YC", required("YC_score", score("lt", 10)))

ROUND_TRIPS = {
    "handoff": handoff(),
    "cutoffs": cutoffs(),
    "three_survivors": request(
        [X, Y, W], ["X", "Y", "W"], [integer_variable()], limits={"max_requests_per_pair": 20}
    ),
    "open_interval": request([XL, YL], ["XL", "YL"], [continuous_variable("ecog", unit="ECOG", key="ecog")]),
    "exact_point": request([XC, YC], ["XC", "YC"], [continuous_variable()]),
    "enum_open": request([HX, HY], ["HX", "HY"], [enum_variable("histology", ["adeno", "squamous"], True)]),
    "enum_survivor_named": request([HX, HZ], ["HX", "HZ"], [enum_variable("histology", ["adeno"], False)]),
    "scoped_cohort": request([XS, Y], ["XS", "Y"], [integer_variable()], context={"cohort": "c1"}),
    "interpolated": request([XI, Y], ["XI", "Y"], [integer_variable()]),
    "proposed_third": request([X, Y, P_PROPOSED], ["X", "Y", "P"], [integer_variable()]),
    "non_survivor_and_inconsistent": request([X, Y, Z, W], ["X", "Y", "Z"], [integer_variable()]),
    # At bound 4 only the accepted marker-negative row survives; an implementation that ignored the bound
    # would return rows whose replay at the same bound disagrees.
    "tight_bound": handoff(bound=4),
}


@pytest.mark.parametrize("name", sorted(ROUND_TRIPS))
def test_every_request_replays_through_design_bounds_to_the_same_verdicts(evaluate, name):
    sent = ROUND_TRIPS[name]
    result = evaluate(copy.deepcopy(sent))
    assert result["requests"], "scenario was brute-forced to have separators"
    for row in result["requests"]:
        replay = design_bounds_replay(sent["candidates"], row, sent.get("context"), sent.get("bound", 4096))
        checks = checks_by_candidate(row)
        for ident in row["eliminates"]:
            assert replay[ident]["state"] == "ruled_out"
        for ident in row["accommodates"]:
            assert replay[ident]["state"] == "not_ruled_out"
        for ident in row["undecided"]:
            assert replay[ident]["state"] == "unresolved"
        for ident, check in checks.items():
            assert check["verdict"] == replay[ident]["state"]
            assert normalize(check["decision"]) == normalize(replay[ident]["decision"])


def test_a_row_itself_must_not_be_accepted_as_a_design_bounds_observation(evaluate):
    result = evaluate(cutoffs())
    row = result["requests"][0]
    reply = run(
        normalize(
            {
                "operation": "design_bounds",
                "study_ref": STUDY,
                "candidates": [X, Y],
                "observations": [row],
                "query": as_json(row["profile"]),
            }
        )
    )
    assert reply["code"] == "refused"


# --------------------------------------------------------------------------------------------------------
# Signs: accepted separation, mixed signs, sign restriction, several eliminated candidates
# --------------------------------------------------------------------------------------------------------


def test_accepted_ecog3_eliminates_the_lower_cutoff_and_rejected_ecog3_the_higher(evaluate):
    result = evaluate(cutoffs())
    by_sign = {row["sign"]: row for row in result["requests"]}
    assert len(result["requests"]) == 2 and set(by_sign) == {"accepted", "rejected"}
    for row in result["requests"]:
        assert implies(row["profile"], ecog("eq", 3)) and row["profile_size"] == 1
    assert by_sign["accepted"]["eliminates"] == ["X"] and by_sign["accepted"]["accommodates"] == ["Y"]
    assert by_sign["rejected"]["eliminates"] == ["Y"] and by_sign["rejected"]["accommodates"] == ["X"]
    assert pair_of(result, "X", "Y")["outcome"] == "separated"


@pytest.mark.parametrize("sign", ["accepted", "rejected"])
def test_declared_signs_restrict_the_rows(evaluate, sign):
    result = evaluate(cutoffs(signs=[sign]))
    assert [row["sign"] for row in result["requests"]] == [sign]


def test_one_row_may_eliminate_several_survivors(evaluate):
    result = evaluate(
        request([X, Y, W], ["X", "Y", "W"], [integer_variable()], limits={"max_requests_per_pair": 20})
    )
    rows = {
        (row["sign"], next(k for k in range(6) if implies(row["profile"], ecog("eq", k)))): row
        for row in result["requests"]
    }
    assert set(rows) == {("accepted", 3), ("rejected", 3), ("accepted", 4), ("rejected", 4)}
    assert sorted(rows[("accepted", 4)]["eliminates"]) == ["X", "Y"]
    assert rows[("accepted", 4)]["accommodates"] == ["W"]
    assert sorted(rows[("rejected", 3)]["eliminates"]) == ["W", "Y"]
    assert all(pair["outcome"] == "separated" for pair in result["pairs"])


# --------------------------------------------------------------------------------------------------------
# Family outcomes: conflict, single survivor, completed absence, inconsistent survivors
# --------------------------------------------------------------------------------------------------------


def test_zero_survivors_is_a_conflict_with_no_requests(evaluate):
    result = evaluate(request([X, Y], [], [integer_variable()]))
    assert result["family"] == "conflict"
    assert result["requests"] == [] and result["pairs"] == []


def test_one_survivor_needs_no_within_family_separation(evaluate):
    result = evaluate(request([X, Y], ["Y"], [integer_variable()]))
    assert result["family"] == "single_survivor"
    assert searched(result) == ["Y"]
    assert result["requests"] == [] and result["pairs"] == [] and result["output"]["found"] == 0


@pytest.mark.parametrize(
    "declared",
    [integer_variable(), continuous_variable("ecog", unit="ECOG", key="ecog")],
    ids=["integer", "continuous"],
)
def test_logically_equivalent_survivors_complete_with_no_separator(evaluate, declared):
    result = evaluate(request([XQ, YQ], ["XQ", "YQ"], [declared]))
    assert result["family"] == "searched" and result["search"]["state"] == "complete"
    assert result["requests"] == [] and result["output"]["found"] == 0
    assert pair_of(result, "XQ", "YQ")["outcome"] == "no_separator"


def test_inconsistent_survivor_is_reported_and_never_separated(evaluate):
    result = evaluate(request([X, Y, Z], ["X", "Y", "Z"], [integer_variable()]))
    assert excluded(result) == ["Z"] and "Z" not in searched(result)
    assert "survivor_inconsistent:Z" in all_causes(result)
    assert all("Z" not in pair["candidates"] for pair in result["pairs"])
    for row in result["requests"]:
        assert "Z" not in row["eliminates"] + row["accommodates"] + row["undecided"]
    assert result["family"] == "searched" and len(result["requests"]) == 2


def test_one_consistent_survivor_beside_an_inconsistent_one_is_single(evaluate):
    result = evaluate(request([X, Z], ["X", "Z"], [integer_variable()]))
    assert result["family"] == "single_survivor" and excluded(result) == ["Z"]
    assert result["requests"] == []


def test_only_inconsistent_survivors_is_a_conflict(evaluate):
    Z2 = candidate("Z2", required("Z2_low", ecog("lt", 1)), required("Z2_high", ecog("gt", 1)))
    result = evaluate(request([Z, Z2], ["Z", "Z2"], [integer_variable()]))
    assert result["family"] == "conflict" and sorted(excluded(result)) == ["Z", "Z2"]
    assert result["requests"] == []


def test_declared_candidates_outside_survivors_are_never_searched(evaluate):
    result = evaluate(request([X, Y, W], ["X", "Y"], [integer_variable()]))
    assert sorted(searched(result)) == ["X", "Y"]
    for row in result["requests"]:
        assert "W" not in checks_by_candidate(row)
    assert len(result["requests"]) == 2


# --------------------------------------------------------------------------------------------------------
# Ordering, minimality and determinism
# --------------------------------------------------------------------------------------------------------


def test_identical_requests_give_identical_results(evaluate):
    first = evaluate(handoff())
    second = evaluate(handoff())
    assert json.dumps(first, sort_keys=False) == json.dumps(second, sort_keys=False)


def test_least_specified_rows_come_first(evaluate):
    rows = evaluate(handoff())["requests"]
    assert [row["profile_size"] for row in rows] == [1, 2, 2, 2]
    assert rows[0]["sign"] == "accepted"


def test_no_returned_row_is_a_superset_of_a_found_separator_for_the_same_pair_sign_and_side(evaluate):
    three = request([X, Y, W], ["X", "Y", "W"], [integer_variable()], limits={"max_requests_per_pair": 20})
    for sent in (handoff(), three):
        rows = evaluate(sent)["requests"]
        for row in rows:
            for other in rows:
                if other is row or other["sign"] != row["sign"]:
                    continue
                if literal_set(other["profile"]) < literal_set(row["profile"]):
                    shared = {
                        (e, k)
                        for e in row["eliminates"]
                        for k in row["accommodates"]
                        if e in other["eliminates"] and k in other["accommodates"]
                    }
                    mine = {(e, k) for e in row["eliminates"] for k in row["accommodates"]}
                    assert shared != mine, "a row needs some pair for which it is minimal"


# --------------------------------------------------------------------------------------------------------
# Represented domains: integers, continuous points/open intervals/limits, enums
# --------------------------------------------------------------------------------------------------------


def test_integer_domain_rows_are_whole_patients(evaluate):
    for row in evaluate(cutoffs())["requests"]:
        assert any(implies(row["profile"], ecog("eq", k)) for k in range(6))


def test_integer_domain_must_not_separate_by_fractional_ecog(evaluate):
    result = evaluate(request([XL, YL], ["XL", "YL"], [integer_variable()]))
    assert result["requests"] == [] and result["search"]["state"] == "complete"
    # They differ only at 2.5, outside the declared domain: either completed-absence outcome is a coherent
    # reading (NOTES ambiguity 1); a fractional separator never is.
    assert pair_of(result, "XL", "YL")["outcome"] in ("no_separator", "not_separated_in_declared_variables")
    assert "2.5" not in json.dumps(result)


def test_continuous_domain_separates_by_the_open_interval_between_thresholds(evaluate):
    sent = request([XL, YL], ["XL", "YL"], [continuous_variable("ecog", unit="ECOG", key="ecog")])
    result = evaluate(sent)
    assert len(result["requests"]) == 2 and {row["sign"] for row in result["requests"]} == {
        "accepted",
        "rejected",
    }
    for row in result["requests"]:
        assert implies(row["profile"], ecog("gt", 2)) and implies(row["profile"], ecog("lt", 3))
        assert not implies(row["profile"], ecog("eq", 2.5)), "an open interval, not a chosen point"


def test_continuous_domain_includes_the_exact_threshold_point(evaluate):
    result = evaluate(request([XC, YC], ["XC", "YC"], [continuous_variable()]))
    by_sign = {row["sign"]: row for row in result["requests"]}
    assert len(result["requests"]) == 2
    for row in result["requests"]:
        assert implies(row["profile"], score("eq", 10))
    assert by_sign["accepted"]["eliminates"] == ["YC"] and by_sign["rejected"]["eliminates"] == ["XC"]


def test_continuous_declared_minimum_has_no_lower_tail(evaluate):
    XD = candidate("XD", required("XD_score", score("le", 10)))
    YD = candidate("YD", required("YD_high", score("le", 10)), required("YD_low", score("ge", -1)))
    unlimited = evaluate(request([XD, YD], ["XD", "YD"], [continuous_variable()]))
    assert unlimited["requests"] and all(
        implies(row["profile"], score("lt", -1)) for row in unlimited["requests"]
    )
    limited = evaluate(request([XD, YD], ["XD", "YD"], [continuous_variable(minimum=0)]))
    assert limited["requests"] == []
    assert pair_of(limited, "XD", "YD")["outcome"] != "separated"


def test_continuous_declared_maximum_has_no_upper_tail(evaluate):
    XE = candidate("XE", required("XE_score", score("ge", 0)))
    YE = candidate("YE", required("YE_low", score("ge", 0)), required("YE_high", score("le", 200)))
    unlimited = evaluate(request([XE, YE], ["XE", "YE"], [continuous_variable(minimum=0)]))
    assert unlimited["requests"] and all(
        implies(row["profile"], score("gt", 200)) for row in unlimited["requests"]
    )
    limited = evaluate(request([XE, YE], ["XE", "YE"], [continuous_variable(minimum=0, maximum=100)]))
    assert limited["requests"] == []
    assert pair_of(limited, "XE", "YE")["outcome"] != "separated"


def test_continuous_rows_respect_declared_inclusive_limits(evaluate):
    result = evaluate(request([XC, YC], ["XC", "YC"], [continuous_variable(minimum=0, maximum=20)]))
    assert len(result["requests"]) == 2
    for row in result["requests"]:
        assert implies(row["profile"], score("ge", 0)) and implies(row["profile"], score("le", 20))


def test_open_enum_has_a_none_of_these_cell(evaluate):
    result = evaluate(
        request([HX, HY], ["HX", "HY"], [enum_variable("histology", ["adeno", "squamous"], True)])
    )
    assert len(result["requests"]) == 2
    for row in result["requests"]:
        assert implies(row["profile"], histology("not_in", "adeno", "squamous"))


def test_closed_enum_must_not_invent_an_unlisted_member(evaluate):
    result = evaluate(
        request([HX, HY], ["HX", "HY"], [enum_variable("histology", ["adeno", "squamous"], False)])
    )
    assert result["requests"] == [] and result["search"]["state"] == "complete"
    # They differ only on an unlisted member the closed declaration excludes (NOTES ambiguity 1).
    assert pair_of(result, "HX", "HY")["outcome"] in ("no_separator", "not_separated_in_declared_variables")


def test_enum_cells_include_members_a_survivor_names(evaluate):
    result = evaluate(request([HX, HZ], ["HX", "HZ"], [enum_variable("histology", ["adeno"], False)]))
    assert len(result["requests"]) == 2
    for row in result["requests"]:
        assert implies(row["profile"], histology("eq", "squamous"))


# --------------------------------------------------------------------------------------------------------
# Representation: unrepresented variables and unsearched constraints are never "no separator"
# --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "declared",
    [
        integer_variable(unit="WHO"),
        integer_variable(key="ecog_ps"),
        integer_variable(time=ENROLLMENT_BARE),
    ],
    ids=["unit", "predicate", "time"],
)
def test_mismatched_variable_is_unrepresented_never_no_separator(evaluate, declared):
    result = evaluate(request([X, Y], ["X", "Y"], [declared]))
    assert "variable_unrepresented:ecog" in all_causes(result) or "ecog" in codes(
        result["representation"]["unrepresented_variables"]
    )
    assert result["requests"] == []
    assert pair_of(result, "X", "Y")["outcome"] not in ("no_separator", "separated")


def test_variable_time_matches_with_certainty_and_evidence_stripped(evaluate):
    XT = candidate("XT", required("XT_ecog", ecog("le", 2, time=ENROLLMENT_EXPLICIT)))
    YT = candidate("YT", required("YT_ecog", ecog("le", 3, time=ENROLLMENT_EXPLICIT)))
    result = evaluate(request([XT, YT], ["XT", "YT"], [integer_variable(time=ENROLLMENT_BARE)]))
    assert len(result["requests"]) == 2
    assert pair_of(result, "XT", "YT")["outcome"] == "separated"
    assert not {t for t in all_causes(result) if t.startswith("variable_unrepresented:")}


def test_unsearched_constraints_are_not_separated_in_declared_variables(evaluate):
    result = evaluate(request([A, B], ["A", "B"], [integer_variable()]))
    assert result["requests"] == [] and result["search"]["state"] == "complete"
    assert pair_of(result, "A", "B")["outcome"] == "not_separated_in_declared_variables"
    assert result["representation"]["unsearched_constraints"]


def test_undeclared_marker_can_still_explain_rejection_under_b(evaluate):
    variables = [boolean_variable("adult", "adult"), integer_variable()]
    result = evaluate(request([A, B], ["A", "B"], variables, limits={"max_requests_per_pair": 20}))
    assert len(result["requests"]) == 3
    assert all(row["sign"] == "rejected" and row["eliminates"] == ["A"] for row in result["requests"])
    assert result["representation"]["unsearched_constraints"]


def test_empty_profile_is_recorded_as_not_representable(evaluate):
    result = evaluate(cutoffs())
    assert "empty_profile_not_representable" in codes(result["representation"]["coverage"])


# --------------------------------------------------------------------------------------------------------
# Search budgets versus output caps
# --------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "limit,value,cause",
    [("max_profiles", 1, "resource_bound:profiles"), ("max_decisions", 3, "resource_bound:decisions")],
)
def test_exhausted_search_budget_is_incomplete_never_no_separator(evaluate, limit, value, cause):
    # Rejected-only: no size-1 profile separates A/B, so whatever the enumeration order, one profile or three
    # decisions cannot find a separator (124 rejected-sign decisions are needed for a complete search).
    result = evaluate(handoff(signs=["rejected"], limits={limit: value}))
    assert result["search"]["state"] == "incomplete"
    assert cause in codes(result["search"]["causes"])
    assert pair_of(result, "A", "B")["outcome"] == "search_incomplete"
    assert result["requests"] == []


def test_exhausted_budget_on_equivalent_survivors_must_not_claim_no_separator(evaluate):
    result = evaluate(request([XQ, YQ], ["XQ", "YQ"], [integer_variable()], limits={"max_profiles": 1}))
    assert result["search"]["state"] == "incomplete"
    assert pair_of(result, "XQ", "YQ")["outcome"] == "search_incomplete"


def test_profile_size_limit_is_named_and_must_not_claim_no_separator(evaluate):
    result = evaluate(handoff(signs=["rejected"], limits={"max_profile_size": 1}))
    assert result["requests"] == []
    assert "profile_size_limit" in all_causes(result)
    assert pair_of(result, "A", "B")["outcome"] not in ("no_separator", "separated")
    control = evaluate(
        handoff(signs=["rejected"], limits={"max_profile_size": 2, "max_requests_per_pair": 20})
    )
    assert len(control["requests"]) == 3


def test_tight_solver_bound_leaves_witnesses_unresolved_never_no_separator(evaluate):
    # Bound 4 still admits each survivor alone (3 assignments) but not ECOG 3 against ECOG <= 2.
    result = evaluate(cutoffs(bound=4))
    assert result["requests"] == []
    assert pair_of(result, "X", "Y")["outcome"] not in ("no_separator", "separated")
    assert {t for t in all_causes(result) if t.startswith("witness_unresolved:") or t == "resource_bound"}


def test_solver_bound_reaches_every_participant_decision(evaluate):
    result = evaluate(handoff(bound=4))
    assert len(result["requests"]) == 1
    row = result["requests"][0]
    assert row["sign"] == "accepted" and implies(row["profile"], flag("marker", False))
    assert pair_of(result, "A", "B")["outcome"] == "separated"


@pytest.mark.parametrize(
    "limits,cause",
    [
        ({"max_requests": 1, "max_requests_per_pair": 20}, "output_limit:requests"),
        ({"max_requests_per_pair": 1}, "output_limit:per_pair"),
        ({"max_bytes": 1, "max_requests_per_pair": 20}, "output_limit:bytes"),
    ],
)
def test_output_caps_truncate_without_touching_search(evaluate, limits, cause):
    baseline = evaluate(handoff())
    capped = evaluate(handoff(limits=limits))
    assert capped["search"] == baseline["search"]
    assert capped["output"]["found"] == baseline["output"]["found"] == 4
    assert capped["output"]["state"] == "truncated"
    assert capped["output"]["omitted"] == capped["output"]["found"] - capped["output"]["returned"] > 0
    assert cause in codes(capped["output"]["causes"])
    assert capped["requests"] == baseline["requests"][: len(capped["requests"])]
    assert pair_of(capped, "A", "B")["outcome"] == "separated"


def test_request_cap_keeps_the_least_specified_row(evaluate):
    capped = evaluate(handoff(limits={"max_requests": 1, "max_requests_per_pair": 20}))
    assert len(capped["requests"]) == 1 and capped["requests"][0]["profile_size"] == 1


def test_per_pair_cap_bounds_each_pair(evaluate):
    capped = evaluate(handoff(limits={"max_requests_per_pair": 1}))
    assert returned_for_pair(pair_of(capped, "A", "B")) <= 1 and len(capped["requests"]) == 1


# --------------------------------------------------------------------------------------------------------
# Rows cannot pass as evidence; premises, evidence location and standing
# --------------------------------------------------------------------------------------------------------


def test_rows_are_structurally_hypothetical(evaluate):
    for row in evaluate(handoff())["requests"]:
        assert row["kind"] == "hypothetical_evidence_request" and row["observed"] is False
        for key in ROW_FORBIDDEN:
            assert key not in row


def test_rejected_rows_require_complete_candidate_eligibility_for_each_eliminated_candidate(evaluate):
    rows = {row["sign"]: row for row in evaluate(cutoffs())["requests"]}
    assert "complete_candidate_eligibility:Y" in codes(rows["rejected"]["required_premises"])
    assert not {
        t for t in codes(rows["accepted"]["required_premises"]) if "complete_candidate_eligibility" in t
    }
    for row in rows.values():
        text = " ".join(codes(row["required_premises"])).lower()
        assert "bridge" in text and "attribut" in text, "attribution and bridge premises stay explicit"


def test_seek_names_where_to_look_by_sign(evaluate):
    rows = {row["sign"]: row for row in evaluate(cutoffs())["requests"]}
    accepted = " ".join(codes(rows["accepted"]["seek"])).lower()
    rejected = " ".join(codes(rows["rejected"]["seek"])).lower()
    assert "participation" in accepted
    assert "screening" in rejected or "adjudication" in rejected


def test_conditional_status_is_the_weakest_eliminating_decision(evaluate):
    rows = {
        row["sign"]: row for row in evaluate(request([XI, Y], ["XI", "Y"], [integer_variable()]))["requests"]
    }
    assert rows["accepted"]["eliminates"] == ["XI"]
    assert rows["accepted"]["conditional_status"] == "interpolated"
    assert rows["rejected"]["eliminates"] == ["Y"]
    assert rows["rejected"]["conditional_status"] == "known"


# --------------------------------------------------------------------------------------------------------
# Proposed readings and scope
# --------------------------------------------------------------------------------------------------------


def test_known_required_conjunct_eliminates_accepted_profile_but_not_unresolved_rejection(evaluate):
    mixed = candidate(
        "P2", required("P2_ecog", ecog("le", 3)), required("P2_marker", flag("marker"), status="proposed")
    )
    result = evaluate(request([mixed, W], ["P2", "W"], [integer_variable()]))
    assert len(result["requests"]) == 1
    accepted = result["requests"][0]
    assert accepted["sign"] == "accepted" and implies(accepted["profile"], ecog("eq", 4))
    assert accepted["eliminates"] == ["P2"] and accepted["accommodates"] == ["W"]
    deciding = checks_by_candidate(accepted)["P2"]["decision"]
    assert deciding["result"] == "REFUTED" and deciding["status"] == "known"
    assert normalize(deciding["proof"]) == ["P2_ecog"]
    assert "proposed_refused:P2_marker" in deciding["blockers"]
    assert all("P2" not in row["eliminates"] for row in result["requests"] if row["sign"] == "rejected")
    assert pair_of(result, "P2", "W")["outcome"] == "separated"
    assert "witness_unresolved:P2" in all_causes(result)


def test_proposed_survivor_is_undecided_with_its_blocker(evaluate):
    result = evaluate(request([X, Y, P_PROPOSED], ["X", "Y", "P"], [integer_variable()]))
    assert len(result["requests"]) == 2
    for row in result["requests"]:
        assert row["undecided"] == ["P"] and "P" not in row["eliminates"]
        assert "proposed_refused:P_ecog" in codes(checks_by_candidate(row)["P"]["decision"]["blockers"])
    for other in ("X", "Y"):
        assert pair_of(result, other, "P")["outcome"] not in ("no_separator", "separated")
    assert pair_of(result, "X", "Y")["outcome"] == "separated"


@pytest.mark.parametrize("context", [{}, {"cohort": "c2"}], ids=["open", "other_cohort"])
def test_scoped_criterion_outside_its_context_is_never_eliminated_or_called_inseparable(evaluate, context):
    result = evaluate(request([XS, Y], ["XS", "Y"], [integer_variable()], context=context))
    assert result["requests"] == []
    assert pair_of(result, "XS", "Y")["outcome"] not in ("no_separator", "separated")


def test_scoped_criterion_in_its_cohort_separates_and_keeps_the_scope(evaluate):
    result = evaluate(request([XS, Y], ["XS", "Y"], [integer_variable()], context={"cohort": "c1"}))
    assert len(result["requests"]) == 2
    for row in result["requests"]:
        assert "c1" in json.dumps(row["scope"])


# --------------------------------------------------------------------------------------------------------
# Refusals by name
# --------------------------------------------------------------------------------------------------------


def _mutated(change):
    sent = cutoffs()
    change(sent)
    return sent


def _set(path, value):
    def change(sent):
        target = sent
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return change


def _duplicate_key_variable(sent):
    twin = integer_variable(ident="ecog_again")
    sent["variables"].append(twin)


def _duplicate_key_by_certainty(sent):
    sent["variables"] = [
        integer_variable(ident="ecog_t1", time=ENROLLMENT_BARE),
        integer_variable(ident="ecog_t2", time=ENROLLMENT_EXPLICIT),
    ]


EXACT_REFUSALS = {
    "signal_claims": (
        _set(("candidates", 0, "signal_claims"), [{"signal": "s", "claim": {}}]),
        "evidence_requests:candidate:signal_claims_unsupported",
    ),
    "domain_enum_set": (
        _set(("variables", 0, "domain"), {"kind": "enum_set"}),
        "evidence_requests:variable:unsupported_domain",
    ),
    "domain_entity_ref": (
        _set(("variables", 0, "domain"), {"kind": "entity_ref"}),
        "evidence_requests:variable:unsupported_domain",
    ),
    "domain_definition_ref": (
        _set(("variables", 0, "domain"), {"kind": "definition_ref"}),
        "evidence_requests:variable:unsupported_domain",
    ),
    "domain_unresolved": (
        _set(("variables", 0, "domain"), {"kind": "unresolved"}),
        "evidence_requests:variable:unsupported_domain",
    ),
    "duplicate_variable_key": (_duplicate_key_variable, "evidence_requests:variables:duplicate_key"),
    "duplicate_key_time_certainty_stripped": (
        _duplicate_key_by_certainty,
        "evidence_requests:variables:duplicate_key",
    ),
}


@pytest.mark.parametrize("name", sorted(EXACT_REFUSALS))
def test_named_refusals_with_exact_codes(refuse, name):
    change, code = EXACT_REFUSALS[name]
    assert refuse(_mutated(change), "^" + re.escape(code)).startswith(code)


PATTERN_REFUSALS = {
    "unknown_request_field": (_set(("surprise",), 1), GENERAL),
    "unknown_variable_field": (_set(("variables", 0, "step"), 1), GENERAL),
    "unknown_domain_field": (_set(("variables", 0, "domain", "step"), 1), GENERAL),
    "unknown_candidate_field": (_set(("candidates", 0, "notes"), "x"), GENERAL),
    "survivor_not_in_candidates": (_set(("survivors",), ["X", "Q"]), r"^evidence_requests:survivors?:"),
    "duplicate_survivors": (_set(("survivors",), ["X", "X"]), r"^evidence_requests:survivors?:"),
    "duplicate_candidate_ids": (
        lambda sent: sent["candidates"].append(copy.deepcopy(sent["candidates"][0])),
        r"^evidence_requests:candidates?:",
    ),
    "duplicate_variable_ids": (
        lambda sent: sent["variables"].append(boolean_variable("ecog", "marker")),
        GENERAL,
    ),
    "empty_survival_basis": (_set(("survival_basis",), []), r"^evidence_requests:survival_basis:"),
    "blank_survival_basis_reference": (_set(("survival_basis",), [""]), GENERAL),
    "missing_survival_basis": (lambda sent: sent.pop("survival_basis"), GENERAL),
    "missing_variables": (lambda sent: sent.pop("variables"), GENERAL),
    "empty_variables": (_set(("variables",), []), GENERAL),
    "unknown_domain_kind": (_set(("variables", 0, "domain", "kind"), "ordinal"), GENERAL),
    "empty_signs": (_set(("signs",), []), GENERAL),
    "duplicate_signs": (_set(("signs",), ["accepted", "accepted"]), GENERAL),
    "unknown_sign": (_set(("signs",), ["eligible"]), GENERAL),
    "empty_study_ref": (_set(("study_ref",), ""), GENERAL),
    "wrong_operation": (_set(("operation",), "design_bounds"), GENERAL),
    "integer_minimum_above_maximum": (_set(("variables", 0, "domain", "minimum"), 6), GENERAL_OR_BOUND),
    "integer_fractional_limit": (_set(("variables", 0, "domain", "maximum"), 5.5), GENERAL_OR_BOUND),
    "integer_too_many_values": (_set(("variables", 0, "domain", "maximum"), 64), GENERAL_OR_BOUND),
    "enum_without_members": (
        _set(("variables", 0, "domain"), {"kind": "enum", "members": [], "open": True}),
        GENERAL,
    ),
    "enum_duplicate_members": (
        _set(("variables", 0, "domain"), {"kind": "enum", "members": ["a", "a"], "open": True}),
        GENERAL,
    ),
    "bound_zero": (_set(("bound",), 0), GENERAL_OR_BOUND),
    "bound_above_maximum": (_set(("bound",), 65537), GENERAL_OR_BOUND),
    "bound_boolean": (_set(("bound",), True), GENERAL_OR_BOUND),
    "unknown_limit": (_set(("limits",), {"max_widgets": 1}), GENERAL_OR_BOUND),
    "zero_profile_size": (_set(("limits",), {"max_profile_size": 0}), GENERAL_OR_BOUND),
    "too_many_survivors": (
        lambda sent: sent.update(
            candidates=[candidate(f"C{k}", required(f"C{k}_ecog", ecog("le", k))) for k in range(33)],
            survivors=[f"C{k}" for k in range(33)],
        ),
        GENERAL_OR_BOUND,
    ),
    "too_many_variables": (
        lambda sent: sent["variables"].extend(boolean_variable(f"flag{k}", f"flag{k}") for k in range(12)),
        GENERAL_OR_BOUND,
    ),
}


@pytest.mark.parametrize("name", sorted(PATTERN_REFUSALS))
def test_named_refusals(refuse, name):
    change, pattern = PATTERN_REFUSALS[name]
    refuse(_mutated(change), pattern)


def test_continuous_minimum_above_maximum_is_refused(refuse):
    sent = request([XC, YC], ["XC", "YC"], [continuous_variable(minimum=5, maximum=1)])
    refuse(sent, GENERAL_OR_BOUND)


HARD_MAXIMA = {
    "max_profile_size": 6,
    "max_profiles": 20000,
    "max_decisions": 50000,
    "max_requests_per_pair": 20,
    "max_requests": 200,
    "max_bytes": 262144,
}


@pytest.mark.parametrize("key", sorted(HARD_MAXIMA))
def test_limits_above_their_hard_maximum_are_refused(refuse, key):
    refuse(cutoffs(limits={key: HARD_MAXIMA[key] + 1}), GENERAL_OR_BOUND)


@pytest.mark.parametrize("key", sorted(HARD_MAXIMA))
def test_limits_at_their_hard_maximum_are_admitted(evaluate, key):
    result = evaluate(cutoffs(limits={key: HARD_MAXIMA[key]}))
    assert result["family"] == "searched"


def test_structural_maxima_are_admitted_at_the_boundary(evaluate):
    many = [candidate(f"C{k}", required(f"C{k}_ecog", ecog("le", k))) for k in range(32)]
    evaluate(request(many, [f"C{k}" for k in range(32)], [integer_variable()], limits={"max_profiles": 1}))
    flags = [boolean_variable(f"flag{k}", f"flag{k}") for k in range(11)]
    evaluate(request([X, Y], ["X", "Y"], [integer_variable(), *flags], limits={"max_profiles": 1}))
    evaluate(
        request([X, Y], ["X", "Y"], [integer_variable(minimum=0, maximum=63)], limits={"max_profiles": 1})
    )
    evaluate(cutoffs(bound=65536))


def test_malformed_model_objects_are_refused_not_coerced(refuse):
    sent = cutoffs()
    sent["variables"][0]["subject"] = "participant"
    refuse(sent, r".+")
    sent = cutoffs()
    sent["candidates"][0]["assertions"] = [model(ecog("le", 2))]
    refuse(sent, r".+")
