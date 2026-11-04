# Bounded selector migration receipt

Comparison specimen: committed b8a635d TrialLedger/mcp_server.py definitions versus current TrialLedger/evidence_access.py. This is a mechanical migration check, not an automatic transfer of the old module's Detective certificate.

`ast-equality.json` reports whole-function AST equality for `_served`, `page_window`, `pointer_value`, `study_line` and `record_view`, including docstrings/defaults/annotations; only source locations and AST-absent comments/formatting are excluded. Complete old/new function units are retained.

`old-bindings.json` and `new-bindings.json` capture every executable LOAD_GLOBAL reference, including nested code objects, and recursively fingerprint the called Python helpers. All four public helpers' reachable contexts match after explicitly naming the module move. Imported `bounded_view`, `response_bytes` and `text_window` ASTs and consumed globals match. Native bindings use their nominal module/name with the same interpreter binary; they have no Python AST. No unresolved binding remains in the final captures.

All ten separately checked selection/budget/error constants match, including STUDY_LINE, MANIFEST_KEYS, STATUS_KEYS, limits and RECORD_WORDS. The live MCP aliases for the four public helpers are the identical function objects exported by evidence_access.

The private `_served` initializer's full FIELDS binding is different. Four new criteria.source_context definitions are retained completely in `complete-changed-fields.json`; they include source heading/kind and source start/end offsets. Field's whole NamedTuple class AST is unchanged. The full name/consumer projection is not claimed equal. The three actual import-time `_served` outputs used to build STUDY_LINE/MANIFEST_KEYS/STATUS_KEYS are exactly equal. Those resulting constants, rather than the entire FIELDS object, are what the public selectors consume at runtime. This receipt does not equate `_served` on every possible part or equate the old/new generated reports; new report content remains source data for unchanged selectors.

Evidence: 276 existing/direct MCP/CLI/UX and generated paging tests passed in the fresh copy, with no authored tests removed. The separate fresh clinical packet retained 41 executable CLI/fresh stdio MCP pairs and complete text continuation checks: /Users/rohanvinaik/trialledger-runs/repair-handoff-walkthroughs-20261104/ . Its receipts name their exact runtime windows.

Limits: module/global-dictionary identity, __module__, source filename and traceback/introspection locations changed. Monkeypatching helpers through the old module namespace is not asserted equivalent. Custom non-JSON objects, altered builtins and alternate interpreter/library versions are outside this bounded clinical-interface check. There is no new mutation certificate claimed for pointer_value, study_line or record_view. No such mutation walk was started after scope refinement.

The external receipt generator initially lacked a native-class representation and then assumed a dataclass field shape. Those helper errors were corrected using the complete native/class and Field definitions before final comparison. Initial incomplete captures remain outside this export under migration/iteration-1 and migration/iteration-2; final captures contain no unresolved binding. No source or test was changed to make a comparison pass.
