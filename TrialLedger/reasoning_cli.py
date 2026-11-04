"""Clinical reasoning delivery commands; computation and artifacts have shared owners."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from TrialLedger import clinical_delivery, reasoning_artifacts, reasoning_delivery
from TrialLedger.landscape_verify import strict_json

COMMANDS = ("reason-result", "reason-revise", "reason-export")


def configure(commands: argparse._SubParsersAction, reason: argparse.ArgumentParser) -> None:
    """Declare the CLI part of the same artifact/revision/export contract MCP serves."""
    reason.add_argument("--store", type=Path, help="retain complete canonical reasoning in this folder")
    reason.add_argument("--compact", action="store_true", help="bounded view; requires --store")
    budget_help = (
        f"compact reply budget: {clinical_delivery.MIN_BYTES}–{clinical_delivery.MAX_BYTES} bytes; "
        f"default {clinical_delivery.DEFAULT_BYTES}; full mode stays full"
    )
    reason.add_argument("--max-bytes", type=int, default=clinical_delivery.DEFAULT_BYTES, help=budget_help)
    reason.add_argument("--intent", choices=clinical_delivery.INTENTS, default="unspecified")
    reason.add_argument("--question", default="", help="the person's question, retained as supplied")
    read = commands.add_parser(
        "reason-result",
        help="read a retained reasoning result in bounded parts",
        description="Read exact parts of a saved reasoning result. Follow page and text continuation.\n\n"
        "example: trialledger reason-result --store reasoning --id ID --part decisions\n\n"
        "exit status: 0 read; 2 named refusal",
    )
    read.add_argument("--store", type=Path, required=True)
    read.add_argument("--id", required=True, help="the complete artifact fingerprint returned by reason")
    read.add_argument(
        "--part", choices=("manifest", *reasoning_artifacts.PARTS, "address"), default="summary"
    )
    read.add_argument("--address")
    for flag in ("offset", "limit", "max-bytes", "text-offset", "text-limit"):
        help_text = None
        if flag == "max-bytes":
            help_text = (
                f"reply budget: {reasoning_artifacts.MIN_BYTES}–{reasoning_artifacts.MAX_BYTES} bytes; "
                f"default {reasoning_artifacts.DEFAULT_BYTES}"
            )
        read.add_argument("--" + flag, type=int, help=help_text)
    revise = commands.add_parser(
        "reason-revise",
        help="revise retained premises and recompute both snapshots",
        description="Change a draft with explicitly attributed premises and recompute both versions.\n\n"
        "example: trialledger reason-revise --store reasoning --id ID --edits edits.json --revision two\n\n"
        "exit status: 0 evaluated or prepared; 2 named refusal",
    )
    revise.add_argument("--store", type=Path, required=True)
    revise.add_argument("--id", required=True)
    choice = revise.add_mutually_exclusive_group(required=True)
    choice.add_argument("--session", type=Path, help="complete next session with explicit clinical origins")
    choice.add_argument(
        "--edits", type=Path, help="bounded explicit replacement edits, with origins for changed premises"
    )
    revise.add_argument("--revision", help="new revision label when applying edits")
    revise.add_argument(
        "--full", action="store_true", help="return full canonical result instead of compact view"
    )
    revise.add_argument(
        "--prepare-only", action="store_true", help="return the valid request without executing it"
    )
    revise.add_argument("--intent", choices=clinical_delivery.INTENTS, default="unspecified")
    revise.add_argument("--question", default="")
    revise.add_argument("--max-bytes", type=int, default=clinical_delivery.DEFAULT_BYTES, help=budget_help)
    export = commands.add_parser(
        "reason-export",
        help="write a traceable clinical review workbook and decision list",
        description="Give colleagues a decision list and workbook with evidence, choices "
        "and consequences. OUT must not already exist; publication is OUT/review.\n\n"
        "example: trialledger reason-export --store reasoning --id ID --out review\n\n"
        "exit status: 0 exported; 2 named refusal",
    )
    export.add_argument("--store", type=Path, required=True)
    export.add_argument("--id", required=True)
    export.add_argument("--out", type=Path, required=True, help="parent folder; publishes into OUT/review")
    export.add_argument("--source-record", type=Path, help="matching retained landscape.json; never modified")
    export.add_argument(
        "--include", action="append", default=[], help="another retained analysis artifact to include"
    )


def handle(args: argparse.Namespace) -> int:
    """Execute one public delivery command; named refusals are never clinical answers."""
    try:
        if args.command == "reason-result":
            fields = ("part", "address", "offset", "limit", "max_bytes", "text_offset", "text_limit")
            reply = reasoning_artifacts.read(
                args.store,
                args.id,
                {key: getattr(args, key) for key in fields if getattr(args, key) is not None},
            )
        elif args.command == "reason-revise":
            reply = reasoning_delivery.revise(
                args.store,
                args.id,
                session=strict_json(args.session.read_text()) if args.session else None,
                revision=args.revision,
                edits=strict_json(args.edits.read_text()) if args.edits else None,
                response_view="full" if args.full else "compact",
                intent=args.intent,
                question=args.question,
                max_bytes=args.max_bytes,
                prepare_only=args.prepare_only,
            )
        else:
            from TrialLedger.clinical_export import export_review

            reply = export_review(
                args.store, args.id, args.out, source_record=args.source_record, include=args.include
            )
    except (OSError, ValueError, TypeError, KeyError) as error:
        reply = {"code": "refused", "problems": [str(error)]}
    print(json.dumps(reply, ensure_ascii=False, indent=1, allow_nan=False))
    return 0 if reply["code"] in ("complete", "prepared") else 2
