"""Common readable delivery over canonical reasoning; no new clinical premises."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy

INTENTS = ("unspecified", "compatibility", "necessity", "consistency", "description", "decision")


def augment(response: dict) -> dict:
    """Add one shared clinical projection and summary, retaining every original result field."""
    from TrialLedger.layer2 import clinical_answers
    from TrialLedger.layer2.session_state import digest

    operation = response["operation"]
    if operation == "describe":
        return {
            "summary": {"kind": "discovery", "code": response["code"], "operation": operation},
            **response,
        }
    clinical = clinical_answers.project(operation, response["result"], response["problems"])
    dispositions = Counter(row["disposition"] for row in clinical["findings"])
    summary = {
        "kind": "reasoning" if response["code"] == "complete" else "refusal",
        "code": response["code"],
        "operation": operation,
        "findings": len(clinical["findings"]),
        "dispositions": dict(sorted(dispositions.items())),
        "problems": deepcopy(response["problems"]),
    }
    if "answer_diff" in response:
        changes = response["answer_diff"]
        summary["changes"] = (
            {
                kind: dict(Counter(row["code"] for row in changes.get(kind, [])))
                for kind in ("analyses", "decisions")
            }
            if isinstance(changes, dict)
            else None
        )
    reply = {"summary": summary, "clinical": clinical, **response}
    if response["code"] == "complete":
        reply["result_digest"] = digest(response["result"])
        reply["result_digest_scope"] = "result only; excludes summary, presentation and artifact metadata"
    return reply


def present(response: dict, *, intent: str = "unspecified", question: str = "") -> dict:
    """A declared clinical question guides wording; it never changes a logical outcome."""
    if not isinstance(intent, str) or intent not in INTENTS:
        raise ValueError("unsupported_question_intent")
    if not isinstance(question, str) or len(question) > 4096:
        raise ValueError("invalid_clinical_question")
    if intent == "unspecified" and not question:
        return dict(response)
    return {
        **response,
        "presentation": {
            "intent": intent,
            "question": question,
            "origin": "caller_declared_question; not authenticated confirmation",
        },
    }


def compact(response: dict, artifact: dict) -> dict:
    """A compact view requires an actual retained canonical artifact; nothing is truncated."""
    from TrialLedger.layer2.session_state import digest
    from TrialLedger.reasoning_artifacts import artifact_id_code

    if type(artifact) is not dict or artifact_id_code(artifact.get("id")) != "valid_artifact_id":
        raise ValueError("compact_requires_canonical_artifact")
    fields = (
        "summary",
        "clinical",
        "code",
        "operation",
        "problems",
        "result_digest",
        "result_digest_scope",
        "presentation",
        "answer_diff",
        "diagnostics",
    )
    reply = {
        **{key: deepcopy(response[key]) for key in fields if key in response},
        "artifact": deepcopy(artifact),
        "view": "compact",
        "canonical_result": "Full request/response retained; retrieve by artifact id and exact address.",
    }
    if "delivery" in response:
        delivery = response["delivery"]
        reply["delivery"] = {
            "previous_artifact": delivery["previous_artifact"],
            "edits": [
                {
                    "path": row["path"],
                    "before_digest": digest(row["before"]),
                    "after_digest": digest(row["after"]),
                    "canonical_ref": f"/response/delivery/edits/{index}",
                }
                for index, row in enumerate(delivery["edits"])
            ],
        }
    return reply
