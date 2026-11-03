"""Entailment over scoped assertions (openspec/changes/add-scoped-assertions, design Decisions 6, 8 and 9;
tasks 3.1 and 3.2).

The assertions of one trial compile into an eligibility formula for an entry context: a required assertion
gives `scope ∧ applicability → body`, an excluded one `scope ∧ applicability → ¬body`, conjoined; a
permission, a definition, a description, an unresolved or conflicting assertion contributes nothing, and a
proposed one is never a premise. A query is decided by exact finite-domain enumeration over the variables it
depends on (its connected component of the formula), with measurements compared as typed numbers on their own
unit and time, enumerated members on an open domain, `Opaque` content a free variable (unresolved, never
false), and a declared resource bound that returns UNDETERMINED. Every other component is checked too, because
a contradiction anywhere is INCONSISTENT and nothing is entailed from it. Every decision carries its proof
(the premises used, a minimal set, from known premises alone when they suffice) and its blockers; its status
is the weakest of its premises, and nothing promotes interpolated to known.

The results: ENTAILED (no feasible assignment satisfies the formula with the query negated, and the formula is
satisfiable), REFUTED (likewise for the query's negation), UNDETERMINED (both feasible, nothing constrains the
query, or the bound was reached; never a negative finding), INCONSISTENT (the formula is unsatisfiable),
OUT_OF_SCOPE (only assertions scoped to other entry contexts speak of the query), UNSUPPORTED_QUERY (the query
is no proposition, or holds content that is unresolved).
"""

from __future__ import annotations

import dataclasses
import itertools
import json
import math
import operator
from fractions import Fraction

from TrialLedger.layer2.assertions import (
    PROPOSITIONS,
    STATUSES,
    UNRESOLVED_RULE,
    AllOf,
    Always,
    AnyOf,
    Literal,
    ModelError,
    Not,
    Opaque,
    Scope,
    ScopedAssertion,
    canonical,
)

ENTAILED = "ENTAILED"
REFUTED = "REFUTED"
UNDETERMINED = "UNDETERMINED"
INCONSISTENT = "INCONSISTENT"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"
RESULTS = (ENTAILED, REFUTED, UNDETERMINED, INCONSISTENT, OUT_OF_SCOPE, UNSUPPORTED_QUERY)

# The declared resource bound: the most assignments one enumeration may visit (design Decision 8). Beyond it
# the decision is UNDETERMINED with the blocker "resource_bound", never a guess.
MAX_ASSIGNMENTS = 1 << 16
# Weakest first: a conclusion's status is the weakest of its premises (design Decision 9).
STATUS_RANK = {"proposed": 0, "interpolated": 1, "known": 2}
COMPARE = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
}
# The member an open enumerated domain always keeps: a value no assertion names.
UNLISTED = "\u0000unlisted"
TRUE = ("const", True)
FALSE = ("const", False)
QUERY = ""  # the query's label among the components (assertion ids are never empty)


@dataclasses.dataclass(frozen=True)
class Context:
    """The entry context a query is asked in: a named cohort, phase or arm, or None where it is not fixed (an
    open population: a named scope may or may not apply). A participant enters through one of each."""

    cohort: str | None = None
    phase: str | None = None
    arm: str | None = None


EVERYONE = Context()


@dataclasses.dataclass(frozen=True)
class Decision:
    """A query's result, the query as canonically written, the conclusion's status (for ENTAILED, REFUTED and
    INCONSISTENT; None otherwise), the proof (assertion ids, sorted) and the blockers (named codes, sorted).
    """

    result: str
    query: str
    status: str | None
    proof: tuple[str, ...]
    blockers: tuple[str, ...]


def weakest_status(statuses: tuple[str, ...]) -> str:
    """The status of a conclusion from premises of these statuses (pure — pinned).

    The weakest of them (proposed < interpolated < known); no premises is a conclusion that needs none, known.
    Deterministic processing never promotes: one interpolated premise makes the conclusion interpolated. A
    word outside the status vocabulary is refused (`ModelError`)."""
    if not set(statuses) <= STATUSES:
        raise ModelError("status_outside_vocabulary")
    return min(statuses, key=STATUS_RANK.__getitem__, default="known")


def proposition_formula(item: object) -> tuple[tuple, tuple[str, ...]]:
    """A proposition or condition as a formula, with the blockers its content raises (pure — pinned).

    `AllOf`, `AnyOf` and `Not` keep their structure; `Always` is true. A literal is a variable keyed by its
    subject, predicate and time: its orientation, anchor, bounds, unit and inclusivity, never its certainty or
    its evidence (epistemic metadata: one predicate cited at two spans, or once explicit and once entailed, is
    one variable). A boolean value is one Boolean variable; a reference names one Boolean per member; a
    member-set value names one membership Boolean per member, `in` S holding every member of S and `not_in` S
    none of them (so `in` {a} and `not_in` {a} are one variable, and {a, b} implies {a} either way); an
    enumerated value is a member of an open domain; a quantity or interval is a typed comparison on a
    measurement keyed by its unit as written (another unit, or a missing one, is another measurement). An
    interval whose boundary inclusivity is unspecified leaves each boundary point undecided (a free variable;
    blocker "unspecified_boundary"). A qualified literal is the conjunction of its base and its qualifiers,
    and negative polarity negates that conjunction: NOT (base AND qualifiers), never (NOT base) AND
    qualifiers. A literal with an unresolved subject, predicate, polarity or value, and an `Opaque`, is a free
    variable (unresolved, never false), blocked as "unresolved_literal" or "opaque"."""
    if isinstance(item, Always):
        return TRUE, ()
    if isinstance(item, Opaque):
        return ("bool", json.dumps(["opaque", item.ref])), (f"opaque:{item.ref}",)
    if isinstance(item, Not):
        inner, blockers = proposition_formula(item.part)
        return _negate(inner), blockers
    if isinstance(item, AllOf | AnyOf):
        compiled = [proposition_formula(part) for part in item.parts]
        parts = tuple(formula for formula, _ in compiled)
        blockers = tuple(b for _, found in compiled for b in found)
        return _fold("and" if isinstance(item, AllOf) else "or", parts), blockers
    if isinstance(item, Literal):
        return _literal_formula(item)
    raise ModelError("not_a_proposition")


def _measured(number: float | None) -> float:
    """A validated quantity's bound, preserving an integer's exact value."""
    if number is None:
        raise TypeError("float() argument must be a string or a real number, not 'NoneType'")
    return number


def _literal_formula(item: Literal) -> tuple[tuple, tuple[str, ...]]:
    value = item.value
    time = canonical(dataclasses.replace(item.time, certainty="unresolved", evidence=())) if item.time else ""
    head = [canonical(item.subject), canonical(item.predicate), time]
    name = item.predicate.key or item.predicate.kind
    if "unresolved" in (item.subject.kind, item.predicate.kind, item.polarity, value.kind):
        return ("bool", json.dumps(["unresolved", *head, canonical(value)])), (f"unresolved_literal:{name}",)
    blockers: tuple[str, ...] = ()
    if value.kind in ("quantity", "interval"):
        key = json.dumps(["measure", *head, value.unit])
        if value.kind == "quantity":
            base = ("cmp", key, value.comparison, _measured(value.number))
        else:
            low, high = _measured(value.number), _measured(value.upper)
            if value.inclusivity == "inclusive":
                base = ("and", (("cmp", key, "ge", low), ("cmp", key, "le", high)))
            else:
                base = ("and", (("cmp", key, "gt", low), ("cmp", key, "lt", high)))
            if value.inclusivity == "unspecified":
                at_low = ("and", (("cmp", key, "eq", low), ("bool", json.dumps([key, "lower", low]))))
                at_high = ("and", (("cmp", key, "eq", high), ("bool", json.dumps([key, "upper", high]))))
                base = ("or", (base, at_low, at_high))
                blockers = (f"unspecified_boundary:{name}",)
            if value.comparison == "not_in":
                base = _negate(base)
    elif value.kind == "enum":
        base = ("enum", json.dumps(["enum", *head]), tuple(sorted(value.members)))
        if value.comparison in ("ne", "not_in"):
            base = _negate(base)
    else:
        held = tuple(("bool", json.dumps(["member", *head, value.kind, m])) for m in sorted(value.members))
        held = held or (("bool", json.dumps(["member", *head, value.kind, ""])),)
        if value.comparison == "not_in":
            held = tuple(_negate(member) for member in held)
        base = _fold("and", held)
    if not isinstance(item.qualifiers, Always):
        qualifier, more = proposition_formula(item.qualifiers)
        base, blockers = _fold("and", (base, qualifier)), blockers + more
    return (_negate(base) if item.polarity == "negative" else base), blockers


def _negate(formula: tuple) -> tuple:
    if formula[0] == "const":
        return ("const", not formula[1])
    return ("not", formula)


def _fold(op: str, parts: tuple) -> tuple:
    """A conjunction or disjunction with its constant parts folded away."""
    absorbing = op == "or"
    if ("const", absorbing) in parts:
        return ("const", absorbing)
    kept = tuple(part for part in parts if part != ("const", not absorbing))
    if not kept:
        return ("const", not absorbing)
    return kept[0] if len(kept) == 1 else (op, kept)


def _scope_formula(scope: Scope, context: Context) -> tuple[tuple, tuple[str, ...]]:
    if scope.kind == "all_participants":
        return TRUE, ()
    if scope.kind == "unresolved":
        return ("bool", json.dumps(["scope", "unresolved", scope.ref])), (f"unresolved_scope:{scope.ref}",)
    if scope.kind in ("all_of", "any_of"):
        compiled = [_scope_formula(part, context) for part in scope.parts]
        blockers = tuple(b for _, found in compiled for b in found)
        return _fold("and" if scope.kind == "all_of" else "or", tuple(f for f, _ in compiled)), blockers
    fixed = {"cohort_ref": context.cohort, "phase_ref": context.phase, "arm_ref": context.arm}[scope.kind]
    if fixed is None:
        return ("bool", json.dumps(["scope", scope.kind, scope.ref])), (
            f"open_scope:{scope.kind}:{scope.ref}",
        )
    return ("const", fixed == scope.ref), ()


def assertion_formula(item: ScopedAssertion, context: Context) -> tuple[str, tuple, tuple[str, ...]]:
    """What one assertion contributes to the eligibility formula in a context, as a code, its formula and the
    blockers it raises (pure — pinned).

    "refused_proposed": a proposed assertion is never a premise. "unresolved_rule": nor is one whose rule is
    explicitly unresolved (no provenance, never a premise). "conflicting" (founder decision A6: neither
    fires) and "unresolved" (its resolution or its modality unresolved) contribute nothing and say so.
    "no_constraint": permitted, definitional and descriptive assertions impose nothing by themselves (a
    permission never establishes presence nor erases an exclusion; a definition only through a resolved
    reference, a later task). "scoped_out": the cohort scope is false in this context; the formula returned is
    its effect, so a query it speaks of can be named out of scope. "constraint": `scope ∧ applicability →
    body` for required, `→ ¬body` for excluded; the applicability antecedent is never implied."""
    if item.status == "proposed":
        return "refused_proposed", TRUE, (f"proposed_refused:{item.id}",)
    if item.rule == UNRESOLVED_RULE:
        return "unresolved_rule", TRUE, (f"unresolved_rule:{item.id}",)
    if item.resolution == "conflicting":
        return "conflicting", TRUE, (f"conflicting:{item.id}",)
    if item.resolution == "unresolved" or item.modality == "unresolved":
        return "unresolved", TRUE, (f"unresolved_assertion:{item.id}",)
    if item.modality not in ("required", "excluded"):
        return "no_constraint", TRUE, ()
    body, found_body = proposition_formula(item.body)
    antecedent, found_antecedent = proposition_formula(item.applicability)
    scope, found_scope = _scope_formula(item.cohort, context)
    effect = body if item.modality == "required" else _negate(body)
    blockers = found_scope + found_antecedent + found_body
    if scope == FALSE:
        return "scoped_out", effect, ()
    return "constraint", _fold("or", (_negate(_fold("and", (scope, antecedent))), effect)), blockers


def _atoms(formula: tuple) -> list[tuple]:
    """Every variable occurrence of a formula: (family, key, payload)."""
    tag = formula[0]
    if tag == "const":
        return []
    if tag == "bool":
        return [("bool", formula[1], None)]
    if tag == "cmp":
        return [("measure", formula[1], formula[3])]
    if tag == "enum":
        return [("enum", formula[1], formula[2])]
    if tag == "not":
        return _atoms(formula[1])
    return [atom for part in formula[1] for atom in _atoms(part)]


def _holds(formula: tuple, assignment: dict) -> bool:
    tag = formula[0]
    if tag == "const":
        return formula[1]
    if tag == "bool":
        return assignment[formula[1]]
    if tag == "cmp":
        return COMPARE[formula[2]](assignment[formula[1]], formula[3])
    if tag == "enum":
        return assignment[formula[1]] in formula[2]
    if tag == "and":
        return all(_holds(part, assignment) for part in formula[1])
    if tag == "or":
        return any(_holds(part, assignment) for part in formula[1])
    return not _holds(formula[1], assignment)


def _satisfiable(formulas: list[tuple], bound: int) -> bool | None:
    """Whether some assignment satisfies every formula; None when the domains exceed the bound.

    Each Boolean takes both values; each measurement every threshold named, every midpoint between two and one
    beyond each end (a comparison with a named threshold is constant between them, so this is exact); each
    enumerated variable every member named and one unlisted member (the domain is open). Variables and values
    in sorted order, so the enumeration is deterministic."""
    domains: dict[str, set] = {}
    for family, key, payload in (atom for f in formulas for atom in _atoms(f)):
        values = domains.setdefault(key, {False, True} if family == "bool" else set())
        if family == "measure":
            values.add(payload)
        elif family == "enum":
            values.update(payload)
    keys = sorted(domains)
    ranges = []
    for key in keys:
        values = sorted(domains[key])
        if key.startswith('["measure"'):
            # Exact rational representatives preserve every comparison cell. Float +/-1 can
            # equal its operand, and a float midpoint can overflow or equal an endpoint.
            values = sorted(Fraction(value) for value in values)
            between = [(low + high) / 2 for low, high in itertools.pairwise(values)]
            values = sorted({values[0] - 1, *values, *between, values[-1] + 1})
        elif key.startswith('["enum"'):
            values = [*values, UNLISTED]
        ranges.append(values)
    if math.prod(len(values) for values in ranges) > bound:
        return None
    for chosen in itertools.product(*ranges):
        assignment = dict(zip(keys, chosen, strict=True))
        if all(_holds(f, assignment) for f in formulas):
            return True
    return False


def _components(items: list[tuple[str, set]]) -> list[tuple[str, ...]]:
    """The labels grouped by shared variables (transitively), each group sorted, the groups sorted."""
    groups: list[tuple[set, list[str]]] = []
    for label, variables in items:
        joined, labels, rest = set(variables), [label], []
        for group_variables, group_labels in groups:
            if group_variables & joined:
                joined |= group_variables
                labels += group_labels
            else:
                rest.append((group_variables, group_labels))
        groups = [*rest, (joined, labels)]
    return sorted(tuple(sorted(labels)) for _, labels in groups)


def _proof(premises: list[tuple], extra: tuple, bound: int) -> tuple[tuple[str, ...], str]:
    """A minimal set of premises whose formulas with `extra` are unsatisfiable, from the known premises alone
    when they suffice; premises are dropped weakest first, then by id, so the proof is deterministic."""
    known = [p for p in premises if p[0] == STATUS_RANK["known"]]
    base = known if known and _satisfiable([p[3] for p in known] + [extra], bound) is False else premises
    kept = sorted(base)
    for premise in sorted(base):
        trial = [p for p in kept if p is not premise]
        if _satisfiable([p[3] for p in trial] + [extra], bound) is False:
            kept = trial
    return tuple(sorted(p[1] for p in kept)), weakest_status(tuple(p[2] for p in kept))


def decide(
    assertions: tuple[ScopedAssertion, ...],
    query: object,
    context: Context = EVERYONE,
    bound: int = MAX_ASSIGNMENTS,
) -> Decision:
    """Whether a trial's assertions entail a query in a context, with proof and blockers (pure — pinned).

    UNSUPPORTED_QUERY: the query is no proposition, or holds unresolved or opaque content. INCONSISTENT: some
    component of the formula is unsatisfiable (anywhere: nothing is entailed from a contradiction); its proof
    a minimal unsatisfiable set. UNDETERMINED with "resource_bound": a component exceeds the bound, so the
    formula is not shown satisfiable. OUT_OF_SCOPE: no constraint in this context speaks of the query, but an
    assertion scoped to another context does. UNDETERMINED with "no_constraint_mentions_query": nothing speaks
    of it (missing support is never evidence of absence). ENTAILED or REFUTED: the query, or its negation,
    holds in every assignment of its component that satisfies the formula, with a minimal proof and the
    weakest status of its premises. Otherwise UNDETERMINED, "undecided_by_constraints", the proof every
    premise considered. Duplicate assertion ids are refused (`ModelError`): a proof names its premises by id.
    """
    ids = [item.id for item in assertions]
    if len(set(ids)) != len(ids):
        raise ModelError("duplicate_assertion_id")
    if not isinstance(query, PROPOSITIONS):
        return Decision(UNSUPPORTED_QUERY, "", None, (), ("query_not_proposition",))
    asked, found = proposition_formula(query)
    written = canonical(query)
    if found:
        return Decision(UNSUPPORTED_QUERY, written, None, (), tuple(sorted(set(found))))
    by_id = {item.id: item for item in assertions}
    premises: dict[str, tuple] = {}
    scoped_out: list[tuple[str, set]] = []
    blockers: set[str] = set()
    for item_id in sorted(by_id):
        item = by_id[item_id]
        code, formula, raised = assertion_formula(item, context)
        blockers.update(raised)
        variables = {key for _, key, _ in _atoms(formula)}
        if code == "constraint":
            premises[item_id] = (STATUS_RANK[item.status], item_id, item.status, formula, variables)
        elif code == "scoped_out":
            scoped_out.append((item_id, variables))
    asked_variables = {key for _, key, _ in _atoms(asked)}
    groups = _components([(QUERY, asked_variables)] + [(i, p[4]) for i, p in premises.items()])
    exhausted = False
    for group in groups:
        members = [premises[label][:4] for label in group if label != QUERY]
        state = _satisfiable([p[3] for p in members], bound) if members else True
        if state is False:
            proof, status = _proof(members, TRUE, bound)
            return Decision(INCONSISTENT, written, status, proof, tuple(sorted(blockers)))
        exhausted = exhausted or state is None
    if exhausted:
        return Decision(UNDETERMINED, written, None, (), tuple(sorted(blockers | {"resource_bound"})))
    group = next(g for g in groups if QUERY in g)
    members = [premises[label][:4] for label in group if label != QUERY]
    if not members:
        speaking = tuple(sorted(i for i, variables in scoped_out if variables & asked_variables))
        if speaking:
            return Decision(OUT_OF_SCOPE, written, None, speaking, tuple(sorted(blockers)))
        return Decision(
            UNDETERMINED, written, None, (), tuple(sorted(blockers | {"no_constraint_mentions_query"}))
        )
    formulas = [p[3] for p in members]
    against = _satisfiable([*formulas, _negate(asked)], bound)
    towards = _satisfiable([*formulas, asked], bound)
    if against is None or towards is None:
        return Decision(UNDETERMINED, written, None, (), tuple(sorted(blockers | {"resource_bound"})))
    if against is False or towards is False:
        result, extra = (ENTAILED, _negate(asked)) if against is False else (REFUTED, asked)
        proof, status = _proof(members, extra, bound)
        return Decision(result, written, status, proof, tuple(sorted(blockers)))
    considered = tuple(sorted(p[1] for p in members))
    return Decision(
        UNDETERMINED, written, None, considered, tuple(sorted(blockers | {"undecided_by_constraints"}))
    )


def rejected_outcome(eligible: bool | None, ineligible: bool | None) -> str:
    """Classify the two feasible completions of a rejected profile (pure — pinned).

    A resource limit is never refutation. No completion at all means an impossible profile, not a bad
    candidate. No rejected completion refutes the reported rejected witness; no eligible completion means
    the profile must fail the candidate. When both are feasible its unspecified attributes matter.
    """
    if eligible is None or ineligible is None:
        return UNDETERMINED
    if eligible is False and ineligible is False:
        return UNSUPPORTED_QUERY
    if ineligible is False:
        return REFUTED
    if eligible is False:
        return ENTAILED
    return UNDETERMINED


def eligibility_witness(
    assertions: tuple[ScopedAssertion, ...],
    profile: object,
    context: Context = EVERYONE,
    direction: str = "accepted",
    bound: int = MAX_ASSIGNMENTS,
) -> Decision:
    """Whether a candidate admits an observed accepted or rejected participant profile.

    A reported profile must itself be feasible: impossible profiles are translation/source problems,
    never evidence against a design. Feasible accepted witnesses preserve ``decide``. A rejected witness
    instead requires a completion of
    P AND NOT E, where E is the conjunction of this candidate's accepted scoped constraints. REFUTED says
    no such rejected completion exists; ENTAILED says every P completion is rejected; UNDETERMINED says
    unspecified attributes can change the decision. This never turns P into a universal exclusion.

    The candidate is checked independently for inconsistency first. Its full eligibility definition is
    used for the negative direction, including constraints disconnected from P: one of those can explain
    rejection. Ignored/proposed/unresolved premises remain blockers. A claim that every P is eligible
    depends on the whole declared candidate, so its proof retains every accepted constraint, rather than
    dropping constraints toward the vacuous all-eligible definition. Bridges and exception allowances are
    the caller's separate premises; this function does not establish them or interpret screening text.
    """
    if direction not in ("accepted", "rejected"):
        raise ModelError("witness_direction_outside_vocabulary")
    if type(bound) is not int or not 1 <= bound <= MAX_ASSIGNMENTS:
        raise ModelError("invalid_resource_bound")
    baseline = decide(assertions, profile, context, bound)
    if baseline.result in (INCONSISTENT, UNSUPPORTED_QUERY):
        return baseline
    written = baseline.query
    asked, _ = proposition_formula(profile)
    intrinsic = _satisfiable([asked], bound)
    if intrinsic is False:
        return Decision(UNSUPPORTED_QUERY, written, None, (), ("profile_inconsistent",))
    if intrinsic is None:
        return Decision(UNDETERMINED, written, None, (), ("resource_bound",))
    if direction == "accepted" or baseline.result == OUT_OF_SCOPE:
        return baseline
    blocked = set(baseline.blockers) - {"undecided_by_constraints", "no_constraint_mentions_query"}
    if blocked:
        return Decision(UNDETERMINED, written, None, baseline.proof, tuple(sorted(blocked)))
    premises = []
    for item in sorted(assertions, key=lambda item: item.id):
        code, formula, _ = assertion_formula(item, context)
        if code == "constraint":
            premises.append((STATUS_RANK[item.status], item.id, item.status, formula))
    eligibility = _fold("and", tuple(p[3] for p in premises))
    eligible = _satisfiable([asked, eligibility], bound)
    ineligible = _satisfiable([asked, _negate(eligibility)], bound)
    result = rejected_outcome(eligible, ineligible)
    if result == UNSUPPORTED_QUERY:
        return Decision(result, written, None, (), ("profile_inconsistent",))
    if eligible is None or ineligible is None:
        return Decision(UNDETERMINED, written, None, (), ("resource_bound",))
    if result == ENTAILED:
        proof, status = _proof(premises, asked, bound)
        return Decision(result, written, status, proof, ())
    proof = tuple(p[1] for p in premises)
    if result == REFUTED:
        status = weakest_status(tuple(p[2] for p in premises))
        return Decision(result, written, status, proof, ())
    return Decision(UNDETERMINED, written, None, proof, ("undecided_by_constraints",))
