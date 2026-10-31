"""node_role — the one role a record node's place and own identifier give everything beneath it.

Positive: a registered outcome takes its section's type; an adverse event its table; a reference, arm,
intervention or posted measure the string in its own identifier field; a results node its string groupId;
an entry of a groups list its string id, at any depth.
Negative: the structure is never stretched: a near place (another section, module or listing, a string
index, another depth), an identifier that is absent or not a string, a node that is not a dict, and a
groupId outside the results section all give no role.
"""

import pytest

from TrialLedger.ledger import node_role

P = "protocolSection"
R = "resultsSection"


@pytest.mark.parametrize(
    "path, node, expected",
    [
        ((P, "outcomesModule", "primaryOutcomes", 0), {"measure": "x"}, ("outcome_type", "PRIMARY")),
        ((P, "outcomesModule", "secondaryOutcomes", 2), {}, ("outcome_type", "SECONDARY")),
        (
            (P, "outcomesModule", "otherOutcomes", 0),
            "not even a dict",
            ("outcome_type", "OTHER_PRE_SPECIFIED"),
        ),
        ((R, "adverseEventsModule", "seriousEvents", 0), {}, ("event_table", "serious")),
        ((R, "adverseEventsModule", "otherEvents", 3), {}, ("event_table", "other")),
        ((P, "referencesModule", "references", 1), {"type": "DERIVED"}, ("reference_type", "DERIVED")),
        ((P, "armsInterventionsModule", "armGroups", 0), {"label": "Arm A"}, ("arm", "Arm A")),
        (
            (P, "armsInterventionsModule", "interventions", 0),
            {"name": "Testamab"},
            ("intervention", "Testamab"),
        ),
        (
            (R, "outcomeMeasuresModule", "outcomeMeasures", 0),
            {"type": "POST_HOC"},
            ("outcome_type", "POST_HOC"),
        ),
        (
            (R, "adverseEventsModule", "seriousEvents", 0, "stats", 1),
            {"groupId": "EG001"},
            ("group", "EG001"),
        ),
        ((R, "adverseEventsModule", "eventGroups", 0), {"id": "EG000"}, ("group", "EG000")),
        ((R, "participantFlowModule", "groups", 1), {"id": "FG001"}, ("group", "FG001")),
        (
            (R, "outcomeMeasuresModule", "outcomeMeasures", 0, "groups", 1),
            {"id": "OG001"},
            ("group", "OG001"),
        ),
        ((R,), {"groupId": "G"}, ("group", "G")),
    ],
)
def test_the_structure_states_a_role(path, node, expected):
    assert node_role(path, node) == expected


@pytest.mark.parametrize(
    "path, node",
    [
        ((R, "outcomesModule", "primaryOutcomes", 0), {}),
        ((P, "designModule", "primaryOutcomes", 0), {}),
        ((P, "outcomesModule", "tertiaryOutcomes", 0), {}),
        ((P, "outcomesModule", "primaryOutcomes", "0"), {}),
        ((P, "outcomesModule", "primaryOutcomes"), [{}]),
        ((P, "outcomesModule", "primaryOutcomes", 0, "measure"), "x"),
        ((P, "adverseEventsModule", "seriousEvents", 0), {}),
        ((R, "outcomesModule", "seriousEvents", 0), {}),
        ((P, "referencesModule", "references", 1), {"citation": "c"}),
        ((P, "referencesModule", "references", 1), {"type": 5}),
        ((P, "referencesModule", "references", 1), {"type": None}),
        ((P, "referencesModule", "references", 1), "typewriter"),
        ((P, "referencesModule", "references", 1), ["type"]),
        ((P, "referencesModule", "citations", 1), {"type": "RESULT"}),
        ((R, "referencesModule", "references", 1), {"type": "RESULT"}),
        ((P, "armsInterventionsModule", "armGroups", 0), {"type": "EXPERIMENTAL"}),
        ((P, "armsInterventionsModule", "armGroups", 0), {"label": 3}),
        ((P, "armsInterventionsModule", "interventions", "0"), {"name": "N"}),
        ((R, "outcomeMeasuresModule", "outcomeMeasures", 0), {"title": "t"}),
        ((P, "statusModule"), {"groupId": "EG000"}),
        ((P, "outcomesModule", "groups", 0), {"id": "X"}),
        ((R, "participantFlowModule", "groups", 1), {"title": "t"}),
        ((R, "participantFlowModule", "groups", 1), {"id": 1}),
        ((R, "participantFlowModule", "groups", "1"), {"id": "FG001"}),
        ((R, "participantFlowModule", "periods", 0), {"id": "P0"}),
        ((R, "participantFlowModule", "groups", 1), "FG001"),
        ((R, "adverseEventsModule", "seriousEvents", 0, "stats", 1), {"groupId": 7}),
        ((R, "adverseEventsModule", "eventGroups"), [{"id": "EG000"}]),
        ((R,), {}),
        ((), {"groupId": "G"}),
        ((P, "eligibilityModule", "eligibilityCriteria"), "Inclusion Criteria: ..."),
    ],
)
def test_no_role_the_structure_does_not_state(path, node):
    assert node_role(path, node) is None


def test_a_role_is_a_name_then_a_value():
    name, value = node_role((P, "armsInterventionsModule", "armGroups", 0), {"label": "Placebo"})
    assert (name, value) == ("arm", "Placebo")
