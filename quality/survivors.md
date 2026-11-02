# Surviving mutants at 5598ea6

Each row is a planted bug the selected tests did not catch. Some are equivalent (they cannot change behavior) and some are real gaps; none has been classified here.

| Function | Kind | Original | Mutant |
|---|---|---|---|
| `TrialLedger/request.py::resolve_scope` | str | `code, candidates, candidate_code = "pending", [], "pending"` | `code, candidates, candidate_code = "pending", [], ('pending_x')` |
| `TrialLedger/request.py::resolve_scope` | int | `listed = [member[0] for member in searched]` | `listed = [member[(1)] for member in searched]` |
| `TrialLedger/request.py::resolve_scope` | str | `drugs.append((slot, member[1], "rxclass_member", urls, parts, (member, listed)))` | `drugs.append((slot, member[1], ('rxclass_member_x'), urls, parts, (member, listed)))` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `return "value_kind_outside_vocabulary"` | `return ('value_kind_outside_vocabulary_x')` |
| `TrialLedger/layer2/assertions.py::_value_problem` | boolop | `if not isinstance(value.members, tuple) or not all(isinstance(m, str) and m for m in value.members):` | `if (not isinstance(value.members, tuple) and (not all((isinstance(m, str) and m for m in value.members)))):` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `return "members_not_tuple_of_text"` | `return ('members_not_tuple_of_text_x')` |
| `TrialLedger/layer2/assertions.py::_value_problem` | boolop | `if not isinstance(value.members, tuple) or not all(isinstance(m, str) and m for m in value.members):` | `if not isinstance(value.members, tuple) or not all((isinstance(m, str) or m) for m in value.members):` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `return "unit_not_text"` | `return ('unit_not_text_x')` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `single = value.comparison in ("eq", "ne")` | `single = value.comparison in ("eq", ('ne_x'))` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `if value.kind in ("enum", "enum_set", "entity_ref", "definition_ref"):` | `if value.kind in ("enum", "enum_set", "entity_ref", ('definition_ref_x')):` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `return "ok" if not numbers else "number_on_unnumbered_kind"` | `return "ok" if not numbers else ('number_on_unnumbered_kind_x')` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `return "members_on_numbered_kind"` | `return ('members_on_numbered_kind_x')` |
| `TrialLedger/layer2/assertions.py::_value_problem` | boolop | `if value.number is None or value.upper is None:` | `if (value.number is None and value.upper is None):` |
| `TrialLedger/layer2/assertions.py::_value_problem` | str | `return "interval_needs_two_numbers"` | `return ('interval_needs_two_numbers_x')` |
| `TrialLedger/layer2/profile.py::frequency_rows` | int | `if element.split(":", 1)[0] not in ELIGIBILITY_SECTIONS:` | `if element.split(":", (2))[0] not in ELIGIBILITY_SECTIONS:` |
| `TrialLedger/layer2/profile.py::frequency_rows` | int | `round((s + u) / n, 4),` | `round((s + u) / n, (5)),` |
| `TrialLedger/layer2/profile.py::frequency_rows` | int | `typed = any(e.split(":", 1)[0] in ELIGIBILITY_SECTIONS for e in elements)` | `typed = any(e.split(":", (2))[0] in ELIGIBILITY_SECTIONS for e in elements)` |
| `TrialLedger/layer2/profile.py::frequency_rows` | int | `return sorted(rows, key=lambda row: (row[0], -row[2], row[1]))` | `return sorted(rows, key=lambda row: (row[(1)], -row[2], row[1]))` |
| `TrialLedger/layer2/profile.py::frequency_rows` | int | `return sorted(rows, key=lambda row: (row[0], -row[2], row[1]))` | `return sorted(rows, key=lambda row: (row[0], -row[2], row[(2)]))` |
| `TrialLedger/layer2/evaluation.py::threshold_verdict` | compare | `if measure.denominator < minimum["items"] or measure.trials < minimum["trials"]:` | `if measure.denominator < minimum["items"] or (measure.trials <= minimum['trials']):` |
| `TrialLedger/layer2/evaluation.py::threshold_verdict` | compare | `return "meets" if lower >= values[group] else "below"` | `return "meets" if (lower > values[group]) else "below"` |
| `TrialLedger/warrants.py::_imported_modules` | boolop | `if (node.level == 0 and source == PACKAGE_NAME) or (node.level == 1 and not source):` | `if (node.level == 0 and source == PACKAGE_NAME) or ((node.level == 1 or not source)):` |
| `TrialLedger/warrants.py::_imported_modules` | compare | `elif node.level == 1:` | `elif (node.level != 1):` |
| `TrialLedger/warrants.py::_imported_modules` | int | `elif node.level == 1:` | `elif node.level == (2):` |
| `TrialLedger/warrants.py::_imported_modules` | int | `names.add(source.split(".")[0])` | `names.add(source.split(".")[(1)])` |
| `TrialLedger/warrants.py::_imported_modules` | str | `names.add(source.split(".")[0])` | `names.add(source.split(('._x'))[0])` |
| `TrialLedger/layer2/expectations.py::conditional_rarity` | compare | `elif len(known) >= support:` | `elif (len(known) > support):` |
| `TrialLedger/layer2/expectations.py::conditional_rarity` | compare | `present_bits = round(-math.log2(share), 3) if share > 0 else None` | `present_bits = round(-math.log2(share), 3) if (share >= 0) else None` |
| `TrialLedger/layer2/expectations.py::conditional_rarity` | int | `present_bits = round(-math.log2(share), 3) if share > 0 else None` | `present_bits = round(-math.log2(share), (4)) if share > 0 else None` |
| `TrialLedger/layer2/evaluation.py::clustered_lower_bound` | int | `return sorted(rates)[lower_rank - 1]` | `return sorted(rates)[lower_rank - (2)]` |
| `TrialLedger/request.py::_iso_date` | compare | `return date.fromisoformat(value).isoformat() == value` | `return (date.fromisoformat(value).isoformat() != value)` |
| `TrialLedger/request.py::_iso_date` | bool | `return False` | `return (True)` |
| `TrialLedger/workbook.py::write_workbook` | int | `problems = certify(record, path, book=book, contexts=contexts, limit=1)` | `problems = certify(record, path, book=book, contexts=contexts, limit=(2))` |
| `TrialLedger/warrants.py::review` | str | `return digest("review", reason, *sources)` | `return digest(('review_x'), reason, *sources)` |
| `TrialLedger/classes.py::class_evidence` | str | `"classes": [],` | `('classes_x'): [],` |
| `TrialLedger/classes.py::class_evidence` | str | `"identities": [],` | `('identities_x'): [],` |
| `TrialLedger/classes.py::class_evidence` | boolop | `if not isinstance(aliases, list) or any(not isinstance(name, str) or not name for name in aliases):` | `if not isinstance(aliases, list) or any((not isinstance(name, str) and (not name)) for name in aliases):` |
| `TrialLedger/classes.py::class_evidence` | str | `"own"` | `('own_x')` |
| `TrialLedger/classes.py::class_evidence` | str | `"relation": relation,` | `('relation_x'): relation,` |
| `TrialLedger/classes.py::class_evidence` | str | `"code": "not_recorded" if isinstance(answer, dict) else "not_looked_up",` | `"code": ('not_recorded_x') if isinstance(answer, dict) else "not_looked_up",` |
| `TrialLedger/classes.py::class_evidence` | str | `"code": "not_recorded" if isinstance(answer, dict) else "not_looked_up",` | `"code": "not_recorded" if isinstance(answer, dict) else ('not_looked_up_x'),` |
| `TrialLedger/classes.py::class_evidence` | str | `query["code"] = "malformed"` | `query["code"] = ('malformed_x')` |
| `TrialLedger/classes.py::class_evidence` | str | `standing = "identity_conflict"` | `standing = ('identity_conflict_x')` |
| `TrialLedger/classes.py::class_evidence` | str | `query["code"] = "malformed"` | `query[('code_x')] = "malformed"` |
| `TrialLedger/classes.py::class_evidence` | str | `"malformed",` | `('malformed_x'),` |
| `TrialLedger/classes.py::class_evidence` | str | `"not_in_rxnorm",` | `('not_in_rxnorm_x'),` |
| `TrialLedger/classes.py::class_evidence` | str | `"ambiguous_in_rxnorm",` | `('ambiguous_in_rxnorm_x'),` |
| `TrialLedger/classes.py::class_evidence` | str | `"queried_name": name,` | `('queried_name_x'): name,` |
| `TrialLedger/classes.py::class_evidence` | str | `"class_type": kind,` | `('class_type_x'): kind,` |
| `TrialLedger/classes.py::class_evidence` | str | `"subject_type": tty,` | `('subject_type_x'): tty,` |
| `TrialLedger/classes.py::class_evidence` | int | `or not all(row[index] for index in (0, 1, 5, 6, 7))` | `or not all(row[index] for index in ((1), 1, 5, 6, 7))` |
| `TrialLedger/classes.py::class_evidence` | int | `or not all(row[index] for index in (0, 1, 5, 6, 7))` | `or not all(row[index] for index in (0, (2), 5, 6, 7))` |
| `TrialLedger/classes.py::class_evidence` | int | `or not all(row[index] for index in (0, 1, 5, 6, 7))` | `or not all(row[index] for index in (0, 1, (6), 6, 7))` |
| `TrialLedger/classes.py::class_evidence` | int | `or not all(row[index] for index in (0, 1, 5, 6, 7))` | `or not all(row[index] for index in (0, 1, 5, (7), 7))` |
| `TrialLedger/classes.py::class_evidence` | str | `out.update(state="not_looked_up", reason="own_identity_not_looked_up")` | `out.update(state="not_looked_up", reason=('own_identity_not_looked_up_x'))` |
| `TrialLedger/classes.py::class_evidence` | str | `out.update(state="lookup_failed", reason="class_lookup_failed")` | `out.update(state="lookup_failed", reason=('class_lookup_failed_x'))` |
| `TrialLedger/request.py::slot_value_ok` | compare | `if not isinstance(value, dict) or not set(value) <= {"name", "id", "source", "subclasses"}:` | `if not isinstance(value, dict) or not (set(value) < {'name', 'id', 'source', 'subclasses'}):` |
| `TrialLedger/classes.py::name_identity` | compare | `return ("ambiguous" if ids_code == "found" and len(id_list) > 1 else "unresolved"), "", []` | `return ("ambiguous" if ids_code == "found" and (len(id_list) >= 1) else "unresolved"), "", []` |
| `TrialLedger/layer2/review.py::flags_for` | str | `["excludes", "admits", "differs by cohort", "not stated"],` | `[('excludes_x'), "admits", "differs by cohort", "not stated"],` |
| `TrialLedger/layer2/review.py::flags_for` | str | `["excludes", "admits", "differs by cohort", "not stated"],` | `["excludes", ('admits_x'), "differs by cohort", "not stated"],` |
| `TrialLedger/layer2/review.py::flags_for` | str | `["excludes", "admits", "differs by cohort", "not stated"],` | `["excludes", "admits", ('differs by cohort_x'), "not stated"],` |
| `TrialLedger/layer2/review.py::flags_for` | str | `["excludes", "admits", "differs by cohort", "not stated"],` | `["excludes", "admits", "differs by cohort", ('not stated_x')],` |
| `TrialLedger/cli.py::_landscape` | str | `words = "Give the request either as --request FILE or as flags (--drug, --ids, ...), not both."` | `words = ('Give the request either as --request FILE or as flags (--drug, --ids, ...), not both._x')` |
| `TrialLedger/cli.py::_landscape` | str | `outcome = Outcome("request_refused", "request_and_flags", words)` | `outcome = Outcome(('request_refused_x'), "request_and_flags", words)` |
| `TrialLedger/cli.py::_landscape` | str | `outcome = Outcome("request_refused", "request_and_flags", words)` | `outcome = Outcome("request_refused", ('request_and_flags_x'), words)` |
| `TrialLedger/cli.py::_landscape` | str | `words = "The request file cannot be read as JSON: write the request as one JSON object of slots."` | `words = ('The request file cannot be read as JSON: write the request as one JSON object of slots._x')` |
| `TrialLedger/cli.py::_landscape` | str | `outcome = Outcome("request_refused", f"{code}: {' '.join(offending)}", words)` | `outcome = Outcome(('request_refused_x'), f"{code}: {' '.join(offending)}", words)` |
| `TrialLedger/cli.py::_landscape` | str | `outcome = Outcome("request_refused", f"request_unreadable: {args.request}", words)` | `outcome = Outcome(('request_refused_x'), f"request_unreadable: {args.request}", words)` |
| `TrialLedger/cli.py::_landscape` | str | `if mode not in ("direct", "relay"):` | `if mode not in (('direct_x'), "relay"):` |
| `TrialLedger/cli.py::_landscape` | boolop | `outcome = preview(args.run, request, mode, get=rxclass_get or rx.http_get, sleep=sleep, progress=say)` | `outcome = preview(args.run, request, mode, get=(rxclass_get and rx.http_get), sleep=sleep, progress=say)` |
| `TrialLedger/record.py::write_record` | str | `staging = out_dir.with_name(out_dir.name + ".partial")` | `staging = out_dir.with_name(out_dir.name + ('.partial_x'))` |
| `TrialLedger/record.py::write_record` | bool | `staging.mkdir(parents=True)` | `staging.mkdir(parents=(False))` |
| `TrialLedger/record.py::write_record` | str | `"retrieved_at": pull.retrieved_at,` | `('retrieved_at_x'): pull.retrieved_at,` |
| `TrialLedger/record.py::write_record` | str | `"workbook": f"{WORKBOOK_NAME}: the review workbook, the design questions study by study, every "` | `('workbook_x'): f"{WORKBOOK_NAME}: the review workbook, the design questions study by study, every "` |
| `TrialLedger/record.py::write_record` | str | `"record_workbook": f"{RECORD_NAME}: every value of every study in the registry's own categories, "` | `('record_workbook_x'): f"{RECORD_NAME}: every value of every study in the registry's own categories, "` |
| `TrialLedger/record.py::write_record` | str | `"tool": f"TrialLedger {__version__}",` | `('tool_x'): f"TrialLedger {__version__}",` |
| `TrialLedger/record.py::write_record` | bool | `shutil.rmtree(staging, ignore_errors=True)` | `shutil.rmtree(staging, ignore_errors=(False))` |
| `TrialLedger/record.py::write_record` | bool | `json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"` | `json.dumps(record, ensure_ascii=(True), indent=2) + "\n", encoding="utf-8"` |
| `TrialLedger/record.py::write_record` | int | `json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"` | `json.dumps(record, ensure_ascii=False, indent=(3)) + "\n", encoding="utf-8"` |
| `TrialLedger/classes.py::alias_role` | compare | `if own_code in RESOLVED and len(own_parts) > 1 and set(parts) <= set(own_parts):` | `if own_code in RESOLVED and (len(own_parts) >= 1) and set(parts) <= set(own_parts):` |
| `TrialLedger/classes.py::alias_role` | compare | `if own_code in RESOLVED and len(own_parts) > 1 and set(parts) <= set(own_parts):` | `if own_code in RESOLVED and len(own_parts) > 1 and (set(parts) < set(own_parts)):` |
| `TrialLedger/classes.py::class_route` | compare | `if ids_code == "found" and count > 1:` | `if ids_code == "found" and (count >= 1):` |
| `TrialLedger/layer2/nearmiss.py::near_misses` | int | `return sorted(pairs, key=lambda pair: (order[pair[0]], order[pair[1]]))` | `return sorted(pairs, key=lambda pair: (order[pair[(1)]], order[pair[1]]))` |
| `TrialLedger/layer2/nearmiss.py::near_misses` | int | `return sorted(pairs, key=lambda pair: (order[pair[0]], order[pair[1]]))` | `return sorted(pairs, key=lambda pair: (order[pair[0]], order[pair[(2)]]))` |
| `TrialLedger/layer2/assertions.py::_build` | str | `raise ModelError("not_a_model_object")` | `raise ModelError(('not_a_model_object_x'))` |
| `TrialLedger/layer2/assertions.py::_build` | boolop | `if cls is Branch and isinstance(fields.get("path"), tuple):` | `if (cls is Branch or isinstance(fields.get('path'), tuple)):` |
| `TrialLedger/layer2/assertions.py::_build` | boolop | `fields["path"] = tuple(int(i) if isinstance(i, float) and i.is_integer() else i for i in path)` | `fields["path"] = tuple(int(i) if (isinstance(i, float) or i.is_integer()) else i for i in path)` |
| `TrialLedger/layer2/assertions.py::_build` | compare | `if not set(fields) <= names:` | `if not (set(fields) < names):` |
| `TrialLedger/layer2/assertions.py::_build` | str | `raise ModelError("fields_do_not_fit_class")` | `raise ModelError(('fields_do_not_fit_class_x'))` |
| `TrialLedger/layer2/coherence.py::close` | bool | `changed = False` | `changed = (True)` |
| `TrialLedger/layer2/coherence.py::close` | int | `for _ in range(sum(len(values) for values in current.values()) + 1):` | `for _ in range(sum(len(values) for values in current.values()) + (2)):` |
| `TrialLedger/checks.py::_not_completed` | boolop | `return started - completed if started is not None and completed is not None else None` | `return started - completed if (started is not None or completed is not None) else None` |
| `TrialLedger/layer2/evaluation.py::agreement_kind` | compare | `0 <= read.start < read.end <= len(text) and text[read.start : read.end] == read.quote` | `(0 < read.start < read.end <= len(text)) and text[read.start : read.end] == read.quote` |
| `TrialLedger/layer2/evaluation.py::agreement_kind` | int | `0 <= read.start < read.end <= len(text) and text[read.start : read.end] == read.quote` | `(1) <= read.start < read.end <= len(text) and text[read.start : read.end] == read.quote` |
| `TrialLedger/layer2/assertions.py::_plain` | boolop | `if isinstance(item, bool) or item is None or isinstance(item, str):` | `if (isinstance(item, bool) and item is None and isinstance(item, str)):` |
| `TrialLedger/layer2/assertions.py::_plain` | compare | `if isinstance(item, bool) or item is None or isinstance(item, str):` | `if isinstance(item, bool) or (item is not None) or isinstance(item, str):` |
| `TrialLedger/layer2/assertions.py::_plain` | compare | `return number if number == item else item` | `return number if (number != item) else item` |
| `TrialLedger/layer2/assertions.py::_plain` | boolop | `if type(item).__name__ in CLASSES and dataclasses.is_dataclass(item):` | `if (type(item).__name__ in CLASSES or dataclasses.is_dataclass(item)):` |
| `TrialLedger/layer2/assertions.py::_plain` | compare | `if type(item).__name__ in CLASSES and dataclasses.is_dataclass(item):` | `if (type(item).__name__ not in CLASSES) and dataclasses.is_dataclass(item):` |
| `TrialLedger/layer2/assertions.py::_plain` | str | `return {"class": type(item).__name__, **fields}` | `return {('class_x'): type(item).__name__, **fields}` |
| `TrialLedger/layer2/assertions.py::_plain` | str | `raise ModelError("not_a_model_object")` | `raise ModelError(('not_a_model_object_x'))` |
| `TrialLedger/layer2/semantics/contracts.py::atom_digest` | str | `canonical = json.dumps(content, ensure_ascii=False, separators=(",", ":"))` | `canonical = json.dumps(content, ensure_ascii=False, separators=(",", (':_x')))` |
| `TrialLedger/workbook.py::_group_titles` | str | `return {get(group, "id"): get(group, "title") for group in as_list(get(module, "groups"))}` | `return {get(group, ('id_x')): get(group, "title") for group in as_list(get(module, "groups"))}` |
| `TrialLedger/workbook.py::_group_titles` | str | `return {get(group, "id"): get(group, "title") for group in as_list(get(module, "groups"))}` | `return {get(group, "id"): get(group, ('title_x')) for group in as_list(get(module, "groups"))}` |
| `TrialLedger/workbook.py::_group_titles` | str | `return {get(group, "id"): get(group, "title") for group in as_list(get(module, "groups"))}` | `return {get(group, "id"): get(group, "title") for group in as_list(get(module, ('groups_x')))}` |
| `TrialLedger/layer2/service.py::_corpus` | str | `_input(request, "corpus", "request")` | `_input(request, ('corpus_x'), "request")` |
| `TrialLedger/layer2/service.py::_corpus` | str | `_input(request, "corpus", "request")` | `_input(request, "corpus", ('request_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `given = _list(request["trials"], "trials")` | `given = _list(request["trials"], ('trials_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `given = _list(request["trials"], "trials")` | `given = _list(request[('trials_x')], "trials")` |
| `TrialLedger/layer2/service.py::_corpus` | str | `ids = [item["id"] for item in trials]` | `ids = [item[('id_x')] for item in trials]` |
| `TrialLedger/layer2/service.py::_corpus` | compare | `if len(set(ids)) != len(ids):` | `if (len(set(ids)) == len(ids)):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `raise RequestError("duplicate_trial_id")` | `raise RequestError(('duplicate_trial_id_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["id"],` | `t[('id_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["sponsor"],` | `t[('sponsor_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["stratum"],` | `t[('stratum_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["typed"],` | `t[('typed_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["elements"],` | `t[('elements_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["classes"],` | `t[('classes_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["class_unresolved"],` | `t[('class_unresolved_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `t["eligibility_content"],` | `t[('eligibility_content_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `tuple(t["coverage"].items()),` | `tuple(t[('coverage_x')].items()),` |
| `TrialLedger/layer2/service.py::_corpus` | str | `pairs = [(t["id"], t["representation"], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]` | `pairs = [(t[('id_x')], t["representation"], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]` |
| `TrialLedger/layer2/service.py::_corpus` | str | `pairs = [(t["id"], t["representation"], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]` | `pairs = [(t["id"], t[('representation_x')], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]` |
| `TrialLedger/layer2/service.py::_corpus` | str | `pairs = [(t["id"], t["representation"], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]` | `pairs = [(t["id"], t["representation"], t[('predicates_x')], t["sponsor"], t["start_year"]) for t in trials]` |
| `TrialLedger/layer2/service.py::_corpus` | str | `pairs = [(t["id"], t["representation"], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]` | `pairs = [(t["id"], t["representation"], t["predicates"], t[('sponsor_x')], t["start_year"]) for t in trials]` |
| `TrialLedger/layer2/service.py::_corpus` | str | `pairs = [(t["id"], t["representation"], t["predicates"], t["sponsor"], t["start_year"]) for t in trials]` | `pairs = [(t["id"], t["representation"], t["predicates"], t["sponsor"], t[('start_year_x')]) for t in trials]` |
| `TrialLedger/layer2/service.py::_corpus` | str | `for raw in _list(request.get("cells", []), "cells"):` | `for raw in _list(request.get("cells", []), ('cells_x')):` |
| `TrialLedger/layer2/service.py::_corpus` | compare | `if len(held) != 2:` | `if (len(held) == 2):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `for raw in _list(request.get("cells", []), "cells"):` | `for raw in _list(request.get(('cells_x'), []), "cells"):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `held = _texts(raw, "cell")` | `held = _texts(raw, ('cell_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | int | `if len(held) != 2:` | `if len(held) != (3):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `raise RequestError("cell_needs_setting_and_class")` | `raise RequestError(('cell_needs_setting_and_class_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | int | `cells.append((held[0], held[1]))` | `cells.append((held[(1)], held[1]))` |
| `TrialLedger/layer2/service.py::_corpus` | int | `cells.append((held[0], held[1]))` | `cells.append((held[0], held[(2)]))` |
| `TrialLedger/layer2/service.py::_corpus` | boolop | `if cells and any(not t["setting_domain"] for t in trials):` | `if (cells or any((not t['setting_domain'] for t in trials))):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `raise RequestError("occupancy_requires_nonempty_setting_domains")` | `raise RequestError(('occupancy_requires_nonempty_setting_domains_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `if cells and any(not t["setting_domain"] for t in trials):` | `if cells and any(not t[('setting_domain_x')] for t in trials):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `(t["id"], tuple(t["setting_domain"]), () if t["class_unresolved"] else tuple(t["classes"]))` | `(t[('id_x')], tuple(t["setting_domain"]), () if t["class_unresolved"] else tuple(t["classes"]))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `(t["id"], tuple(t["setting_domain"]), () if t["class_unresolved"] else tuple(t["classes"]))` | `(t["id"], tuple(t[('setting_domain_x')]), () if t["class_unresolved"] else tuple(t["classes"]))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `(t["id"], tuple(t["setting_domain"]), () if t["class_unresolved"] else tuple(t["classes"]))` | `(t["id"], tuple(t["setting_domain"]), () if t[('class_unresolved_x')] else tuple(t["classes"]))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `(t["id"], tuple(t["setting_domain"]), () if t["class_unresolved"] else tuple(t["classes"]))` | `(t["id"], tuple(t["setting_domain"]), () if t["class_unresolved"] else tuple(t[('classes_x')]))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `for raw in _list(request.get("expectations", []), "expectations"):` | `for raw in _list(request.get("expectations", []), ('expectations_x')):` |
| `TrialLedger/layer2/service.py::_corpus` | boolop | `if type(item["support"]) is not int or item["support"] < 1:` | `if (type(item['support']) is not int and item['support'] < 1):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `for raw in _list(request.get("expectations", []), "expectations"):` | `for raw in _list(request.get(('expectations_x'), []), "expectations"):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `item = _input(raw, "expectation", "expectation")` | `item = _input(raw, ('expectation_x'), "expectation")` |
| `TrialLedger/layer2/service.py::_corpus` | str | `item = _input(raw, "expectation", "expectation")` | `item = _input(raw, "expectation", ('expectation_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `_text(item["id"], "expectation:id")` | `_text(item["id"], ('expectation:id_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `_text(item["cell"], "expectation:cell")` | `_text(item["cell"], ('expectation:cell_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | compare | `if type(item["support"]) is not int or item["support"] < 1:` | `if (type(item['support']) is int) or item["support"] < 1:` |
| `TrialLedger/layer2/service.py::_corpus` | compare | `if type(item["support"]) is not int or item["support"] < 1:` | `if type(item["support"]) is not int or (item['support'] <= 1):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `for row in _list(item["observations"], "observations"):` | `for row in _list(item["observations"], ('observations_x')):` |
| `TrialLedger/layer2/service.py::_corpus` | boolop | `if len(pair) != 2 or pair[1] not in expectations.STATUSES:` | `if (len(pair) != 2 and pair[1] not in expectations.STATUSES):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `_text(item["id"], "expectation:id")` | `_text(item[('id_x')], "expectation:id")` |
| `TrialLedger/layer2/service.py::_corpus` | str | `_text(item["cell"], "expectation:cell")` | `_text(item[('cell_x')], "expectation:cell")` |
| `TrialLedger/layer2/service.py::_corpus` | str | `if not _texts(item["basis"], "expectation:basis"):` | `if not _texts(item["basis"], ('expectation:basis_x')):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `raise RequestError("missing_expectation_basis")` | `raise RequestError(('missing_expectation_basis_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | int | `if type(item["support"]) is not int or item["support"] < 1:` | `if type(item["support"]) is not int or item["support"] < (2):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `raise RequestError("invalid_expectation_support")` | `raise RequestError(('invalid_expectation_support_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `for row in _list(item["observations"], "observations"):` | `for row in _list(item[('observations_x')], "observations"):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `pair = _texts(row, "observation")` | `pair = _texts(row, ('observation_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | compare | `if len(pair) != 2 or pair[1] not in expectations.STATUSES:` | `if (len(pair) == 2) or pair[1] not in expectations.STATUSES:` |
| `TrialLedger/layer2/service.py::_corpus` | compare | `if len(pair) != 2 or pair[1] not in expectations.STATUSES:` | `if len(pair) != 2 or (pair[1] in expectations.STATUSES):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"id": item["id"],` | `('id_x'): item["id"],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"basis": item["basis"],` | `('basis_x'): item["basis"],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"rarity": expectations.conditional_rarity(rows, item["cell"], item["support"]),` | `('rarity_x'): expectations.conditional_rarity(rows, item["cell"], item["support"]),` |
| `TrialLedger/layer2/service.py::_corpus` | str | `if not _texts(item["basis"], "expectation:basis"):` | `if not _texts(item[('basis_x')], "expectation:basis"):` |
| `TrialLedger/layer2/service.py::_corpus` | str | `if type(item["support"]) is not int or item["support"] < 1:` | `if type(item["support"]) is not int or item[('support_x')] < 1:` |
| `TrialLedger/layer2/service.py::_corpus` | int | `if len(pair) != 2 or pair[1] not in expectations.STATUSES:` | `if len(pair) != (3) or pair[1] not in expectations.STATUSES:` |
| `TrialLedger/layer2/service.py::_corpus` | str | `raise RequestError("invalid_observation")` | `raise RequestError(('invalid_observation_x'))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"id": item["id"],` | `"id": item[('id_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"basis": item["basis"],` | `"basis": item[('basis_x')],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `if type(item["support"]) is not int or item["support"] < 1:` | `if type(item[('support_x')]) is not int or item["support"] < 1:` |
| `TrialLedger/layer2/service.py::_corpus` | int | `if len(pair) != 2 or pair[1] not in expectations.STATUSES:` | `if len(pair) != 2 or pair[(2)] not in expectations.STATUSES:` |
| `TrialLedger/layer2/service.py::_corpus` | int | `rows.append((pair[0], pair[1]))` | `rows.append((pair[(1)], pair[1]))` |
| `TrialLedger/layer2/service.py::_corpus` | int | `rows.append((pair[0], pair[1]))` | `rows.append((pair[0], pair[(2)]))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"rarity": expectations.conditional_rarity(rows, item["cell"], item["support"]),` | `"rarity": expectations.conditional_rarity(rows, item[('cell_x')], item["support"]),` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"rarity": expectations.conditional_rarity(rows, item["cell"], item["support"]),` | `"rarity": expectations.conditional_rarity(rows, item["cell"], item[('support_x')]),` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"basis": BASIS,` | `('basis_x'): BASIS,` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"premises": given,` | `('premises_x'): given,` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"frequency": [dict(zip(FREQUENCY_FIELDS, row, strict=True)) for row in profile.frequency_rows(typed)],` | `('frequency_x'): [dict(zip(FREQUENCY_FIELDS, row, strict=True)) for row in profile.frequency_rows(typed)],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"associations": [` | `('associations_x'): [` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"near_misses": [dict(zip(PAIR_FIELDS, row, strict=True)) for row in nearmiss.near_misses(pairs)],` | `('near_misses_x'): [dict(zip(PAIR_FIELDS, row, strict=True)) for row in nearmiss.near_misses(pairs)],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"occupancy": [` | `('occupancy_x'): [` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"expectations": observations,` | `('expectations_x'): observations,` |
| `TrialLedger/layer2/service.py::_corpus` | str | `"limits": (` | `('limits_x'): (` |
| `TrialLedger/layer2/service.py::_corpus` | bool | `"frequency": [dict(zip(FREQUENCY_FIELDS, row, strict=True)) for row in profile.frequency_rows(typed)],` | `"frequency": [dict(zip(FREQUENCY_FIELDS, row, strict=(False))) for row in profile.frequency_rows(typed)],` |
| `TrialLedger/layer2/service.py::_corpus` | bool | `dict(zip(ASSOCIATION_FIELDS, row, strict=True)) for row in profile.mechanism_rows(typed)` | `dict(zip(ASSOCIATION_FIELDS, row, strict=(False))) for row in profile.mechanism_rows(typed)` |
| `TrialLedger/layer2/service.py::_corpus` | bool | `"near_misses": [dict(zip(PAIR_FIELDS, row, strict=True)) for row in nearmiss.near_misses(pairs)],` | `"near_misses": [dict(zip(PAIR_FIELDS, row, strict=(False))) for row in nearmiss.near_misses(pairs)],` |
| `TrialLedger/layer2/service.py::_corpus` | str | `dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=True))` | `dict(zip((('setting_x'), "class", "occupants", "possible", "state"), row, strict=True))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=True))` | `dict(zip(("setting", ('class_x'), "occupants", "possible", "state"), row, strict=True))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=True))` | `dict(zip(("setting", "class", ('occupants_x'), "possible", "state"), row, strict=True))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=True))` | `dict(zip(("setting", "class", "occupants", ('possible_x'), "state"), row, strict=True))` |
| `TrialLedger/layer2/service.py::_corpus` | str | `dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=True))` | `dict(zip(("setting", "class", "occupants", "possible", ('state_x')), row, strict=True))` |
| `TrialLedger/layer2/service.py::_corpus` | bool | `dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=True))` | `dict(zip(("setting", "class", "occupants", "possible", "state"), row, strict=(False)))` |
| `TrialLedger/classes.py::drug_axes` | int | `assertions = [(*a[:5], "identity_conflict" if a[5] == "known" else a[5], *a[6:]) for a in assertions]` | `assertions = [(*a[:5], "identity_conflict" if a[5] == "known" else a[5], *a[(7):]) for a in assertions]` |
| `TrialLedger/readout.py::_column_hidden` | bool | `return False` | `return (True)` |
| `TrialLedger/readout.py::_column_hidden` | bool | `return False` | `return (True)` |
| `TrialLedger/readout.py::_column_hidden` | str | `target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))` | `target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(('xl_x'), target))` |
| `TrialLedger/readout.py::_column_hidden` | str | `if node.tag.rsplit("}", 1)[-1] == "sheetData":` | `if node.tag.rsplit("}", 1)[-1] == ('sheetData_x'):` |
| `TrialLedger/readout.py::_column_hidden` | str | `if node.tag.rsplit("}", 1)[-1] == "sheetData":` | `if node.tag.rsplit(('}_x'), 1)[-1] == "sheetData":` |
| `TrialLedger/readout.py::_column_hidden` | int | `if node.tag.rsplit("}", 1)[-1] == "sheetData":` | `if node.tag.rsplit("}", (2))[-1] == "sheetData":` |
| `TrialLedger/readout.py::_column_hidden` | int | `if node.tag.rsplit("}", 1)[-1] == "sheetData":` | `if node.tag.rsplit("}", 1)[-(2)] == "sheetData":` |
| `TrialLedger/readout.py::_column_hidden` | int | `if node.tag.rsplit("}", 1)[-1] != "col":` | `if node.tag.rsplit("}", (2))[-1] != "col":` |
| `TrialLedger/readout.py::_column_hidden` | str | `start, end = int(node.get("min", "0")), int(node.get("max", "0"))` | `start, end = int(node.get(('min_x'), "0")), int(node.get("max", "0"))` |
| `TrialLedger/readout.py::_column_hidden` | str | `start, end = int(node.get("min", "0")), int(node.get("max", "0"))` | `start, end = int(node.get("min", ('0_x'))), int(node.get("max", "0"))` |
| `TrialLedger/readout.py::_column_hidden` | str | `start, end = int(node.get("min", "0")), int(node.get("max", "0"))` | `start, end = int(node.get("min", "0")), int(node.get("max", ('0_x')))` |
| `TrialLedger/readout.py::_column_hidden` | str | `return node.get("hidden") in {"1", "true", "True"}` | `return node.get("hidden") in {"1", ('true_x'), "True"}` |
| `TrialLedger/readout.py::_column_hidden` | str | `return node.get("hidden") in {"1", "true", "True"}` | `return node.get("hidden") in {"1", "true", ('True_x')}` |
| `TrialLedger/readout.py::_column_hidden` | int | `if node.tag.rsplit("}", 1)[-1] == "sheet" and node.get("name") == sheet` | `if node.tag.rsplit("}", (2))[-1] == "sheet" and node.get("name") == sheet` |
| `TrialLedger/readout.py::_column_hidden` | bool | `return False` | `return (True)` |
| `TrialLedger/layer2/typematrix.py::study_coordinates` | boolop | `if isinstance(item, dict) and isinstance(item.get("term"), str)` | `if (isinstance(item, dict) or isinstance(item.get('term'), str))` |
| `TrialLedger/layer2/typematrix.py::study_coordinates` | boolop | `"allocation": [allocation if isinstance(allocation, str) and allocation else NONE],` | `"allocation": [allocation if (isinstance(allocation, str) or allocation) else NONE],` |
| `TrialLedger/layer2/typematrix.py::study_coordinates` | boolop | `"intervention_model": [model if isinstance(model, str) and model else NONE],` | `"intervention_model": [model if (isinstance(model, str) or model) else NONE],` |
| `TrialLedger/layer2/typematrix.py::study_coordinates` | boolop | `"children": [("yes" if "CHILD" in ages else "no") if isinstance(ages, list) and ages else NONE],` | `"children": [("yes" if "CHILD" in ages else "no") if (isinstance(ages, list) or ages) else NONE],` |
| `TrialLedger/classes.py::rxnorm_concepts` | boolop | `if not isinstance(groups, list) or not all(isinstance(g, dict) for g in groups):` | `if (not isinstance(groups, list) and (not all((isinstance(g, dict) for g in groups)))):` |
| `TrialLedger/classes.py::rxnorm_concepts` | str | `if not all(isinstance(g.get("conceptProperties") or [], list) for g in groups):` | `if not all(isinstance(g.get(('conceptProperties_x')) or [], list) for g in groups):` |
| `TrialLedger/classes.py::rxnorm_concepts` | str | `return "malformed", []` | `return ('malformed_x'), []` |
| `TrialLedger/classes.py::rxnorm_concepts` | str | `concepts.add((concept["rxcui"], concept["name"], concept["tty"]))` | `concepts.add((concept[('rxcui_x')], concept["name"], concept["tty"]))` |
| `TrialLedger/ingest.py::reconcile_ids` | str | `canonical = "NCT" + token[3:].lstrip("0").zfill(8)` | `canonical = "NCT" + token[3:].lstrip(('0_x')).zfill(8)` |
| `TrialLedger/layer2/profile.py::occupancy_rows` | compare | `and (len(domain) > 1 or not classes)` | `and ((len(domain) >= 1) or not classes)` |
| `TrialLedger/workbook.py::_site_rows` | str | `where = (P, "contactsLocationsModule", "locations", index)` | `where = (P, ('contactsLocationsModule_x'), "locations", index)` |
| `TrialLedger/workbook.py::_site_rows` | str | `where = (P, "contactsLocationsModule", "locations", index)` | `where = (P, "contactsLocationsModule", ('locations_x'), index)` |
| `TrialLedger/workbook.py::_site_rows` | str | `ctx.field(*where, "facility"),` | `ctx.field(*where, ('facility_x')),` |
| `TrialLedger/workbook.py::_site_rows` | str | `ctx.field(*where, "status"),` | `ctx.field(*where, ('status_x')),` |
| `TrialLedger/workbook.py::_site_rows` | str | `ctx.field(*where, "city"),` | `ctx.field(*where, ('city_x')),` |
| `TrialLedger/workbook.py::_site_rows` | str | `ctx.field(*where, "state"),` | `ctx.field(*where, ('state_x')),` |
| `TrialLedger/workbook.py::_site_rows` | str | `ctx.field(*where, "zip"),` | `ctx.field(*where, ('zip_x')),` |
| `TrialLedger/workbook.py::_site_rows` | str | `ctx.field(*where, "country"),` | `ctx.field(*where, ('country_x')),` |
| `TrialLedger/ingest.py::fetch_version` | str | `payload = _decode_json(response, "version")` | `payload = _decode_json(response, ('version_x'))` |
| `TrialLedger/ingest.py::fetch_version` | int | `raise PullError(f"version.{code}", f"{response.request.url}: {payload!r}"[:500])` | `raise PullError(f"version.{code}", f"{response.request.url}: {payload!r}"[:(501)])` |
| `TrialLedger/layer2/evaluation.py::_single_level` | compare | `if len(levels) > 1:` | `if (len(levels) >= 1):` |
| `TrialLedger/layer2/evaluation.py::_single_level` | int | `if len(levels) > 1:` | `if len(levels) > (2):` |
| `TrialLedger/mcp_server.py::record_view` | boolop | `if type(budget) is not int or not MIN_BYTES <= budget <= MAX_BYTES:` | `if (type(budget) is not int and (not MIN_BYTES <= budget <= MAX_BYTES)):` |
| `TrialLedger/mcp_server.py::record_view` | compare | `if response_bytes({"held": held}) > budget:` | `if (response_bytes({'held': held}) >= budget):` |
| `TrialLedger/mcp_server.py::record_view` | str | `if response_bytes({"held": held}) > budget:` | `if response_bytes({('held_x'): held}) > budget:` |
| `TrialLedger/mcp_server.py::record_view` | str | `address = "/studies"` | `address = ('/studies_x')` |
| `TrialLedger/mcp_server.py::record_view` | str | `address = "/fields"` | `address = ('/fields_x')` |
| `TrialLedger/mcp_server.py::record_view` | boolop | `if "text_offset" in arguments or "text_limit" in arguments:` | `if ('text_offset' in arguments and 'text_limit' in arguments):` |
| `TrialLedger/mcp_server.py::record_view` | str | `if "text_offset" in arguments or "text_limit" in arguments:` | `if ('text_offset_x') in arguments or "text_limit" in arguments:` |
| `TrialLedger/mcp_server.py::record_view` | str | `if "text_offset" in arguments or "text_limit" in arguments:` | `if "text_offset" in arguments or ('text_limit_x') in arguments:` |
| `TrialLedger/mcp_server.py::record_view` | str | `return "not_text", {}` | `return ('not_text_x'), {}` |
| `TrialLedger/mcp_server.py::record_view` | str | `and "navigation" not in view` | `and ('navigation_x') not in view` |
| `TrialLedger/layer2/typematrix.py::universe_status` | boolop | `if not isinstance(study_type, str) or not study_type:` | `if (not isinstance(study_type, str) and (not study_type)):` |
| `TrialLedger/layer2/typematrix.py::universe_status` | int | `if date[:7] < UNIVERSE["start_from"]:` | `if date[:(8)] < UNIVERSE["start_from"]:` |
| `TrialLedger/layer2/semantics/parsers.py::read_number` | int | `if _IN_A_NAME.search(text, 0, pos):` | `if _IN_A_NAME.search(text, (1), pos):` |
| `TrialLedger/layer2/semantics/parsers.py::read_number` | int | `if sign and _DIGIT_BEFORE.search(text, 0, pos):` | `if sign and _DIGIT_BEFORE.search(text, (1), pos):` |
| `TrialLedger/layer2/entail.py::assertion_formula` | str | `if item.resolution == "unresolved" or item.modality == "unresolved":` | `if item.resolution == ('unresolved_x') or item.modality == "unresolved":` |
| `TrialLedger/layer2/entail.py::assertion_formula` | str | `if item.resolution == "unresolved" or item.modality == "unresolved":` | `if item.resolution == "unresolved" or item.modality == ('unresolved_x'):` |
| `TrialLedger/layer2/evaluation.py::complete_representation` | str | `gold_judged, emitted_judged = judge(gold, emitted) if gold else ([], ["unresolved"] * len(emitted))` | `gold_judged, emitted_judged = judge(gold, emitted) if gold else ([], [('unresolved_x')] * len(emitted))` |
| `TrialLedger/layer2/evaluation.py::complete_representation` | bool | `for record, judgement in zip(gold, gold_judged, strict=True):` | `for record, judgement in zip(gold, gold_judged, strict=(False)):` |
| `TrialLedger/layer2/evaluation.py::complete_representation` | bool | `for claim, judgement in zip(emitted, emitted_judged, strict=True):` | `for claim, judgement in zip(emitted, emitted_judged, strict=(False)):` |
| `TrialLedger/workbook.py::_outcome_rows` | bool | `found = False` | `found = (True)` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `("primaryOutcomes", "PRIMARY"),` | `(('primaryOutcomes_x'), "PRIMARY"),` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `("primaryOutcomes", "PRIMARY"),` | `("primaryOutcomes", ('PRIMARY_x')),` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `("secondaryOutcomes", "SECONDARY"),` | `(('secondaryOutcomes_x'), "SECONDARY"),` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `("secondaryOutcomes", "SECONDARY"),` | `("secondaryOutcomes", ('SECONDARY_x')),` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `("otherOutcomes", "OTHER_PRE_SPECIFIED"),` | `(('otherOutcomes_x'), "OTHER_PRE_SPECIFIED"),` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `("otherOutcomes", "OTHER_PRE_SPECIFIED"),` | `("otherOutcomes", ('OTHER_PRE_SPECIFIED_x')),` |
| `TrialLedger/workbook.py::_outcome_rows` | bool | `found = True` | `found = (False)` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `absent = ctx.field(P, "outcomesModule")` | `absent = ctx.field(P, ('outcomesModule_x'))` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `where = (P, "outcomesModule", section, index)` | `where = (P, ('outcomesModule_x'), section, index)` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `measure = ctx.field(*where, "measure")` | `measure = ctx.field(*where, ('measure_x'))` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `for index, _ in enumerate(as_list(get(ctx.study, P, "outcomesModule", section))):` | `for index, _ in enumerate(as_list(get(ctx.study, P, ('outcomesModule_x'), section))):` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `ctx.field(*where, "description"),` | `ctx.field(*where, ('description_x')),` |
| `TrialLedger/workbook.py::_outcome_rows` | str | `ctx.field(*where, "timeFrame"),` | `ctx.field(*where, ('timeFrame_x')),` |
| `TrialLedger/workbook.py::_outcome_rows` | int | `literal(index + 1),` | `literal(index + (2)),` |
| `TrialLedger/checks.py::_tally` | str | `counts = {name: outcomes.count(name) for name in ("consistent", "conflict", "not_checkable")}` | `counts = {name: outcomes.count(name) for name in (('consistent_x'), "conflict", "not_checkable")}` |
| `TrialLedger/checks.py::_tally` | str | `counts = {name: outcomes.count(name) for name in ("consistent", "conflict", "not_checkable")}` | `counts = {name: outcomes.count(name) for name in ("consistent", ('conflict_x'), "not_checkable")}` |
| `TrialLedger/checks.py::_tally` | str | `counts = {name: outcomes.count(name) for name in ("consistent", "conflict", "not_checkable")}` | `counts = {name: outcomes.count(name) for name in ("consistent", "conflict", ('not_checkable_x'))}` |
| `TrialLedger/checks.py::_tally` | str | `summary = ", ".join(f"{n} {name.replace('_', ' ')}" for name, n in counts.items() if n)` | `summary = (', _x').join(f"{n} {name.replace('_', ' ')}" for name, n in counts.items() if n)` |
| `TrialLedger/checks.py::_tally` | compare | `f"; and {len(offenders) - 20} more" if len(offenders) > 20 else ""` | `f"; and {len(offenders) - 20} more" if (len(offenders) >= 20) else ""` |
| `TrialLedger/checks.py::_tally` | str | `shown = "; ".join(offenders[:20]) + (` | `shown = ('; _x').join(offenders[:20]) + (` |
| `TrialLedger/checks.py::_tally` | int | `f"; and {len(offenders) - 20} more" if len(offenders) > 20 else ""` | `f"; and {len(offenders) - 20} more" if len(offenders) > (21) else ""` |
| `TrialLedger/checks.py::_tally` | int | `shown = "; ".join(offenders[:20]) + (` | `shown = "; ".join(offenders[:(21)]) + (` |
| `TrialLedger/checks.py::_tally` | str | `return summary or "no entries"` | `return summary or ('no entries_x')` |
| `TrialLedger/readout.py::footer_parts` | str | `left = "Search: " + search.replace("&", "&&")` | `left = ('Search: _x') + search.replace("&", "&&")` |
| `TrialLedger/readout.py::footer_parts` | str | `left = "Search: " + search.replace("&", "&&")` | `left = "Search: " + search.replace(('&_x'), "&&")` |
| `TrialLedger/readout.py::footer_parts` | str | `left = "Search: " + search.replace("&", "&&")` | `left = "Search: " + search.replace("&", ('&&_x'))` |
| `TrialLedger/readout.py::footer_parts` | str | `centre = "&A, page &P of &N"` | `centre = ('&A, page &P of &N_x')` |
| `TrialLedger/readout.py::footer_parts` | str | `right = "Retrieved " + retrieved.replace("&", "&&")` | `right = ('Retrieved _x') + retrieved.replace("&", "&&")` |
| `TrialLedger/readout.py::footer_parts` | str | `right = "Retrieved " + retrieved.replace("&", "&&")` | `right = "Retrieved " + retrieved.replace(('&_x'), "&&")` |
| `TrialLedger/readout.py::footer_parts` | str | `right = "Retrieved " + retrieved.replace("&", "&&")` | `right = "Retrieved " + retrieved.replace("&", ('&&_x'))` |
| `TrialLedger/readout.py::footer_parts` | compare | `if len(f"&L{left}&C{centre}&R{right}") > FOOTER_LIMIT:` | `if (len(f'&L{left}&C{centre}&R{right}') >= FOOTER_LIMIT):` |
| `TrialLedger/readout.py::footer_parts` | str | `left = "Search: see the Read me sheet"` | `left = ('Search: see the Read me sheet_x')` |
| `TrialLedger/request.py::any_of` | compare | `return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"` | `return terms[0] if (len(terms) != 1) else "(" + " OR ".join(terms) + ")"` |
| `TrialLedger/request.py::any_of` | int | `return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"` | `return terms[0] if len(terms) == (2) else "(" + " OR ".join(terms) + ")"` |
| `TrialLedger/request.py::any_of` | int | `return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"` | `return terms[(1)] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"` |
| `TrialLedger/request.py::any_of` | str | `return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"` | `return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + (')_x')` |
| `TrialLedger/request.py::any_of` | str | `return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"` | `return terms[0] if len(terms) == 1 else ('(_x') + " OR ".join(terms) + ")"` |
| `TrialLedger/request.py::any_of` | str | `return terms[0] if len(terms) == 1 else "(" + " OR ".join(terms) + ")"` | `return terms[0] if len(terms) == 1 else "(" + (' OR _x').join(terms) + ")"` |
| `TrialLedger/layer2/semantics/parsers.py::read_window` | compare | `if anchor_end > anchor_start:` | `if (anchor_end >= anchor_start):` |
| `TrialLedger/layer2/semantics/parsers.py::read_window` | str | `if orient and orient.group(0).lower() != "ago":` | `if orient and orient.group(0).lower() != ('ago_x'):` |
| `TrialLedger/layer2/semantics/parsers.py::read_window` | bool | `(name, value if bound == "N" else bound) for name, bound in zip(_BOUND_NAMES, bounds, strict=True)` | `(name, value if bound == "N" else bound) for name, bound in zip(_BOUND_NAMES, bounds, strict=(False))` |
| `TrialLedger/mcp_server.py::call_tool` | str | `return code, {"tool": name} if name else None` | `return code, {('tool_x'): name} if name else None` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": verdict, "arguments": concerned, "why": ARGUMENT_WORDS[verdict]}` | `refusal = {('tool_x'): name, "refused": verdict, "arguments": concerned, "why": ARGUMENT_WORDS[verdict]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": verdict, "arguments": concerned, "why": ARGUMENT_WORDS[verdict]}` | `refusal = {"tool": name, ('refused_x'): verdict, "arguments": concerned, "why": ARGUMENT_WORDS[verdict]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": verdict, "arguments": concerned, "why": ARGUMENT_WORDS[verdict]}` | `refusal = {"tool": name, "refused": verdict, ('arguments_x'): concerned, "why": ARGUMENT_WORDS[verdict]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": verdict, "arguments": concerned, "why": ARGUMENT_WORDS[verdict]}` | `refusal = {"tool": name, "refused": verdict, "arguments": concerned, ('why_x'): ARGUMENT_WORDS[verdict]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `return "ok", _text(refusal, True)` | `return ('ok_x'), _text(refusal, True)` |
| `TrialLedger/mcp_server.py::call_tool` | bool | `return "ok", _text(refusal, True)` | `return "ok", _text(refusal, (False))` |
| `TrialLedger/mcp_server.py::call_tool` | str | `folder = context.root if name == "reason" else context.root / arguments["run"]` | `folder = context.root if name == ('reason_x') else context.root / arguments["run"]` |
| `TrialLedger/mcp_server.py::call_tool` | compare | `if name != "reason" and folder.resolve().parent != context.root.resolve():` | `if (name == 'reason') and folder.resolve().parent != context.root.resolve():` |
| `TrialLedger/mcp_server.py::call_tool` | str | `if name != "reason" and folder.resolve().parent != context.root.resolve():` | `if name != ('reason_x') and folder.resolve().parent != context.root.resolve():` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}` | `refusal = {('tool_x'): name, "refused": "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}` | `refusal = {"tool": name, ('refused_x'): "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}` | `refusal = {"tool": name, "refused": "run_outside_root", ('why_x'): SAVE_REFUSALS["run_outside_root"]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}` | `refusal = {"tool": name, "refused": ('run_outside_root_x'), "why": SAVE_REFUSALS["run_outside_root"]}` |
| `TrialLedger/mcp_server.py::call_tool` | str | `return "ok", _text(refusal, True)` | `return ('ok_x'), _text(refusal, True)` |
| `TrialLedger/mcp_server.py::call_tool` | str | `refusal = {"tool": name, "refused": "run_outside_root", "why": SAVE_REFUSALS["run_outside_root"]}` | `refusal = {"tool": name, "refused": "run_outside_root", "why": SAVE_REFUSALS[('run_outside_root_x')]}` |
| `TrialLedger/mcp_server.py::call_tool` | bool | `return "ok", _text(refusal, True)` | `return "ok", _text(refusal, (False))` |
| `TrialLedger/mcp_server.py::call_tool` | str | `result = {"tool": name, **reply}` | `result = {('tool_x'): name, **reply}` |
| `TrialLedger/mcp_server.py::call_tool` | compare | `if name != "reason":` | `if (name == 'reason'):` |
| `TrialLedger/mcp_server.py::call_tool` | str | `if name != "reason":` | `if name != ('reason_x'):` |
| `TrialLedger/mcp_server.py::call_tool` | str | `result["run_folder"] = str(folder.resolve())` | `result[('run_folder_x')] = str(folder.resolve())` |
| `TrialLedger/ingest.py::fetch_json_pages` | int | `total = 0` | `total = (1)` |
| `TrialLedger/ingest.py::fetch_json_pages` | int | `empty_streak = 0` | `empty_streak = (1)` |
| `TrialLedger/ingest.py::fetch_json_pages` | int | `page_number = 0` | `page_number = (1)` |
| `TrialLedger/ingest.py::fetch_json_pages` | int | `page_number += 1` | `page_number += (2)` |
| `TrialLedger/ingest.py::fetch_json_pages` | int | `empty_streak = 0 if page else empty_streak + 1` | `empty_streak = (1) if page else empty_streak + 1` |
| `TrialLedger/ingest.py::fetch_json_pages` | int | `empty_streak = 0 if page else empty_streak + 1` | `empty_streak = 0 if page else empty_streak + (2)` |
| `TrialLedger/layer2/semantics/contracts.py::result_problems` | str | `said = {(f.owner_bank, f.concept_id) for f in result.findings if f.code in ("IDENTIFIED", "AMBIGUOUS")}` | `said = {(f.owner_bank, f.concept_id) for f in result.findings if f.code in ("IDENTIFIED", ('AMBIGUOUS_x'))}` |
| `TrialLedger/readout.py::dictionary_rows` | compare | `sheet.name == contract.INDEX` | `(sheet.name != contract.INDEX)` |
| `TrialLedger/readout.py::dictionary_rows` | compare | `and record is not None` | `and (record is None)` |
| `TrialLedger/readout.py::dictionary_rows` | str | `source = "A JSON pointer into landscape.json"` | `source = ('A JSON pointer into landscape.json_x')` |
| `TrialLedger/readout.py::dictionary_rows` | str | `definition = "Where the row's value is in the record: ask the assistant about the row by it"` | `definition = ("Where the row's value is in the record: ask the assistant about the row by it_x")` |
| `TrialLedger/readout.py::dictionary_rows` | compare | `column.header.format(n="1 ... G" + str(n)) if column.shows == "per group" else column.header` | `column.header.format(n="1 ... G" + str(n)) if (column.shows != 'per group') else column.header` |
| `TrialLedger/readout.py::dictionary_rows` | str | `column.header.format(n="1 ... G" + str(n)) if column.shows == "per group" else column.header` | `column.header.format(n="1 ... G" + str(n)) if column.shows == ('per group_x') else column.header` |
| `TrialLedger/readout.py::dictionary_rows` | str | `source = "\n".join(` | `source = ('\n_x').join(` |
| `TrialLedger/readout.py::dictionary_rows` | str | `definition = "\n".join(dict.fromkeys(field.label for field in fields))` | `definition = ('\n_x').join(dict.fromkeys(field.label for field in fields))` |
| `TrialLedger/readout.py::dictionary_rows` | str | `column.header.format(n="1 ... G" + str(n)) if column.shows == "per group" else column.header` | `column.header.format(n=('1 ... G_x') + str(n)) if column.shows == "per group" else column.header` |
| `TrialLedger/layer2/semantics/contracts.py::from_legacy` | str | `kind = LEGACY_MENTION_KIND.get(concept.split(":")[0], "named")` | `kind = LEGACY_MENTION_KIND.get(concept.split((':_x'))[0], "named")` |
| `TrialLedger/operate.py::_fetch` | int | `for done, entry in enumerate(entries, 1):` | `for done, entry in enumerate(entries, (2)):` |
| `TrialLedger/operate.py::_fetch` | str | `status, body = get(entry["url"], entry["params"])` | `status, body = get(entry[('url_x')], entry["params"])` |
| `TrialLedger/operate.py::_fetch` | str | `status, body = get(entry["url"], entry["params"])` | `status, body = get(entry["url"], entry[('params_x')])` |
| `TrialLedger/operate.py::_fetch` | str | `_write(folder / LOOKUPS / entry["file"], answer_bytes(status, body))` | `_write(folder / LOOKUPS / entry[('file_x')], answer_bytes(status, body))` |
| `TrialLedger/record.py::record_root` | str | `return warrants.digest("record", warrants.canonical(committed))` | `return warrants.digest(('record_x'), warrants.canonical(committed))` |
| `TrialLedger/layer2/predicates.py::atom_literal` | int | `own = atom.concept_id.rsplit(".", 1)[-1]` | `own = atom.concept_id.rsplit(".", (2))[-1]` |
| `TrialLedger/layer2/predicates.py::atom_literal` | int | `own = atom.concept_id.rsplit(".", 1)[-1]` | `own = atom.concept_id.rsplit(".", 1)[-(2)]` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `subject = str(data.get("name", "?")) if isinstance(data, dict) else "?"` | `subject = str(data.get("name", "?")) if isinstance(data, dict) else ('?_x')` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `subject = str(data.get("name", "?")) if isinstance(data, dict) else "?"` | `subject = str(data.get(('name_x'), "?")) if isinstance(data, dict) else "?"` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `subject = str(data.get("name", "?")) if isinstance(data, dict) else "?"` | `subject = str(data.get("name", ('?_x'))) if isinstance(data, dict) else "?"` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `allowed = {"name", "version", "exposure", "requires", "concepts", "references", "universes"}` | `allowed = {('name_x'), "version", "exposure", "requires", "concepts", "references", "universes"}` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `"code",` | `('code_x'),` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `"definition",` | `('definition_x'),` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `Reference(str(r["concept_id"]), str(r["family"]), _pairs(r["arguments"]))` | `Reference(str(r["concept_id"]), str(r[('family_x')]), _pairs(r["arguments"]))` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `Reference(str(r["concept_id"]), str(r["family"]), _pairs(r["arguments"]))` | `Reference(str(r["concept_id"]), str(r["family"]), _pairs(r[('arguments_x')]))` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `None if entry.get("code") is None else str(entry["code"]),` | `None if entry.get(('code_x')) is None else str(entry["code"]),` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `None if entry.get("code") is None else str(entry["code"]),` | `None if entry.get("code") is None else str(entry[('code_x')]),` |
| `TrialLedger/layer2/semantics/loader.py::fragment_from_data` | str | `tuple(str(d) for d in entry.get("depends_on", ())),` | `tuple(str(d) for d in entry.get(('depends_on_x'), ())),` |
| `TrialLedger/readout.py::book_plan` | boolop | `if heading == "Publications and documents" and publications is None:` | `if (heading == 'Publications and documents' or publications is None):` |
| `TrialLedger/readout.py::book_plan` | boolop | `sheet_p, row_p = place(publications or starts[-1], CAPACITY, contract.REVIEW)` | `sheet_p, row_p = place((publications and starts[-1]), CAPACITY, contract.REVIEW)` |
| `TrialLedger/readout.py::book_plan` | compare | `if heading != shown_band and listing:` | `if (heading == shown_band) and listing:` |
| `TrialLedger/readout.py::book_plan` | compare | `if heading == "Publications and documents" and publications is None:` | `if (heading != 'Publications and documents') and publications is None:` |
| `TrialLedger/readout.py::book_plan` | compare | `if heading == "Publications and documents" and publications is None:` | `if heading == "Publications and documents" and (publications is not None):` |
| `TrialLedger/readout.py::book_plan` | str | `if heading == "Publications and documents" and publications is None:` | `if heading == ('Publications and documents_x') and publications is None:` |
| `TrialLedger/readout.py::book_plan` | int | `count = sum(1 for row in rows[listing] if row[0][0] == study["nct"])` | `count = sum((2) for row in rows[listing] if row[0][0] == study["nct"])` |
| `TrialLedger/readout.py::book_plan` | int | `if len(parts) > 1` | `if len(parts) > (2)` |
| `TrialLedger/readout.py::book_plan` | int | `sheet_p, row_p = place(publications or starts[-1], CAPACITY, contract.REVIEW)` | `sheet_p, row_p = place(publications or starts[-(2)], CAPACITY, contract.REVIEW)` |
| `TrialLedger/readout.py::book_plan` | compare | `count = sum(1 for row in rows[listing] if row[0][0] == study["nct"])` | `count = sum(1 for row in rows[listing] if (row[0][0] != study['nct']))` |
| `TrialLedger/readout.py::book_plan` | str | `label("Detail"),` | `label(('Detail_x')),` |
| `TrialLedger/readout.py::book_plan` | str | `cell(part_value, "known", link=source_links.get(fact, "")),` | `cell(part_value, ('known_x'), link=source_links.get(fact, "")),` |
| `TrialLedger/readout.py::book_plan` | int | `count = sum(1 for row in rows[listing] if row[0][0] == study["nct"])` | `count = sum(1 for row in rows[listing] if row[0][(1)] == study["nct"])` |
| `TrialLedger/readout.py::book_plan` | int | `count = sum(1 for row in rows[listing] if row[0][0] == study["nct"])` | `count = sum(1 for row in rows[listing] if row[(1)][0] == study["nct"])` |
| `TrialLedger/readout.py::book_plan` | bool | `rows[contract.INDEX] = [index_cells(study, *held) for study, held in zip(studies, links_, strict=True)]` | `rows[contract.INDEX] = [index_cells(study, *held) for study, held in zip(studies, links_, strict=(False))]` |
| `TrialLedger/readout.py::book_plan` | compare | `plan.append((name, headers, written_safely(projected), starts[1:] if name == contract.REVIEW else []))` | `plan.append((name, headers, written_safely(projected), starts[1:] if (name != contract.REVIEW) else []))` |
| `TrialLedger/readout.py::book_plan` | int | `plan.append((name, headers, written_safely(projected), starts[1:] if name == contract.REVIEW else []))` | `plan.append((name, headers, written_safely(projected), starts[(2):] if name == contract.REVIEW else []))` |
| `TrialLedger/request.py::request_problems` | str | `if not malformed and request.get("start_from", "") > request.get("start_to", "9999-12-31"):` | `if not malformed and request.get("start_from", "") > request.get("start_to", ('9999-12-31_x')):` |
| `TrialLedger/readout.py::dossier_value_parts` | compare | `if end < len(value):` | `if (end <= len(value)):` |
| `TrialLedger/readout.py::dossier_value_parts` | int | `low, high = 1, min(len(value) - start, width * contract.DOSSIER_LINES_PER_ROW)` | `low, high = (2), min(len(value) - start, width * contract.DOSSIER_LINES_PER_ROW)` |
| `TrialLedger/readout.py::dossier_value_parts` | int | `end = (low + high + 1) // 2` | `end = (low + high + (2)) // 2` |
| `TrialLedger/readout.py::dossier_value_parts` | int | `high = end - 1` | `high = end - (2)` |
| `TrialLedger/readout.py::dossier_value_parts` | int | `(i + 1 for i in range(end - 1, start + low // 2 - 1, -1) if value[i].isspace()),` | `(i + 1 for i in range(end - (2), start + low // 2 - 1, -1) if value[i].isspace()),` |
| `TrialLedger/readout.py::dossier_value_parts` | int | `(i + 1 for i in range(end - 1, start + low // 2 - 1, -1) if value[i].isspace()),` | `(i + 1 for i in range(end - 1, start + low // 2 - (2), -1) if value[i].isspace()),` |
| `TrialLedger/readout.py::dossier_value_parts` | int | `(i + 1 for i in range(end - 1, start + low // 2 - 1, -1) if value[i].isspace()),` | `(i + 1 for i in range(end - 1, start + low // 2 - 1, -(2)) if value[i].isspace()),` |
| `TrialLedger/readout.py::dossier_value_parts` | int | `(i + 1 for i in range(end - 1, start + low // 2 - 1, -1) if value[i].isspace()),` | `(i + 1 for i in range(end - 1, start + low // (3) - 1, -1) if value[i].isspace()),` |
| `TrialLedger/layer2/typematrix.py::trial_cells` | boolop | `phases = [p for p in (listed if isinstance(listed, list) else []) if isinstance(p, str) and p]` | `phases = [p for p in (listed if isinstance(listed, list) else []) if (isinstance(p, str) or p)]` |
| `TrialLedger/layer2/typematrix.py::trial_cells` | boolop | `if isinstance(item, dict) and isinstance(item.get("type"), str) and item["type"]` | `if (isinstance(item, dict) or isinstance(item.get('type'), str) or item['type'])` |
| `TrialLedger/layer2/typematrix.py::trial_cells` | boolop | `"primary_purpose": [purpose if isinstance(purpose, str) and purpose else NONE],` | `"primary_purpose": [purpose if (isinstance(purpose, str) or purpose) else NONE],` |
| `TrialLedger/layer2/typematrix.py::trial_cells` | str | `"phase": ["|".join(phases) if phases else NONE],` | `"phase": [('|_x').join(phases) if phases else NONE],` |
| `TrialLedger/layer2/semantics/loader.py::load_fragments` | str | `if path.suffix != ".json" and (path.suffix != ".py" or path.name == "__init__.py"):` | `if path.suffix != ".json" and (path.suffix != ".py" or path.name == ('__init__.py_x')):` |
| `TrialLedger/layer2/semantics/loader.py::load_fragments` | str | `raise RegistryError((("malformed_fragment", path.name, "no FRAGMENT dict"),))` | `raise RegistryError(((('malformed_fragment_x'), path.name, "no FRAGMENT dict"),))` |
| `TrialLedger/layer2/semantics/loader.py::load_fragments` | str | `raise RegistryError((("malformed_fragment", path.name, "no FRAGMENT dict"),))` | `raise RegistryError((("malformed_fragment", path.name, ('no FRAGMENT dict_x')),))` |
| `TrialLedger/readout.py::resolve_address` | compare | `if isinstance(node, list) and part.isdigit() and int(part) < len(node):` | `if isinstance(node, list) and part.isdigit() and (int(part) <= len(node)):` |
| `TrialLedger/readout.py::resolve_address` | str | `template[-1] += "[]"` | `template[-1] += ('[]_x')` |
| `TrialLedger/readout.py::resolve_address` | boolop | `elif isinstance(node, dict) and part in node:` | `elif (isinstance(node, dict) or part in node):` |
| `TrialLedger/readout.py::resolve_address` | bool | `return False, None, "", []` | `return (True), None, "", []` |
| `TrialLedger/readout.py::resolve_address` | str | `return True, node, ".".join(template), indices` | `return True, node, ('._x').join(template), indices` |
| `TrialLedger/readout.py::registered_rows` | str | `contract.WHICH_LIST_WORDS.get(str(outcome.get("category")), value_words(outcome.get("category"))),` | `contract.WHICH_LIST_WORDS.get(str(outcome.get("category")), value_words(outcome.get(('category_x')))),` |
| `TrialLedger/readout.py::registered_rows` | str | `rows.append(tuple(cell(value, "known", address) for value in values))` | `rows.append(tuple(cell(value, ('known_x'), address) for value in values))` |
| `TrialLedger/record.py::_unique` | str | `raise DuplicateKey(", ".join(repeated))` | `raise DuplicateKey((', _x').join(repeated))` |
| `TrialLedger/readout.py::retrieval_mode_words` | str | `mode = retrieval.get("mode") if isinstance(retrieval, dict) else None` | `mode = retrieval.get(('mode_x')) if isinstance(retrieval, dict) else None` |
| `TrialLedger/classes.py::_ask_rxnav` | bool | `return dict(zip(keys, answered, strict=True))` | `return dict(zip(keys, answered, strict=(False)))` |
| `TrialLedger/classes.py::_ask_rxnav` | boolop | `if code == "found" and len(held) == 1 and held[0][2] != "IN"` | `if (code == 'found' or len(held) == 1 or held[0][2] != 'IN')` |
| `TrialLedger/classes.py::_ask_rxnav` | str | `if code == "found" and len(held) == 1 and held[0][2] != "IN"` | `if code == "found" and len(held) == 1 and held[0][2] != ('IN_x')` |
| `TrialLedger/classes.py::_ask_rxnav` | str | `"ingredients asked of RxNav",` | `('ingredients asked of RxNav_x'),` |
| `TrialLedger/classes.py::_ask_rxnav` | str | `"concepts",` | `('concepts_x'),` |
| `TrialLedger/classes.py::_ask_rxnav` | str | `[(RXNORM_RELATED.format(rxcui=rxcui), {"tty": "IN"}) for rxcui in combined],` | `[(RXNORM_RELATED.format(rxcui=rxcui), {('tty_x'): "IN"}) for rxcui in combined],` |
| `TrialLedger/classes.py::_ask_rxnav` | str | `[(RXNORM_RELATED.format(rxcui=rxcui), {"tty": "IN"}) for rxcui in combined],` | `[(RXNORM_RELATED.format(rxcui=rxcui), {"tty": ('IN_x')}) for rxcui in combined],` |
| `TrialLedger/classes.py::_ask_rxnav` | int | `class_warrant, status, body = classes[rxcui] if rxcui else (identity_warrant, 0, None)` | `class_warrant, status, body = classes[rxcui] if rxcui else (identity_warrant, (1), None)` |
| `TrialLedger/classes.py::_ask_rxnav` | str | `concept = concepts.get(rxcui, (None, ("not_asked", [])))` | `concept = concepts.get(rxcui, (None, (('not_asked_x'), [])))` |
| `TrialLedger/classes.py::_ask_rxnav` | str | `ingredients = parts.get(rxcui, (None, ("not_asked", [])))` | `ingredients = parts.get(rxcui, (None, (('not_asked_x'), [])))` |
| `TrialLedger/layer2/entail.py::decide` | str | `raise ModelError("duplicate_assertion_id")` | `raise ModelError(('duplicate_assertion_id_x'))` |
| `TrialLedger/layer2/entail.py::decide` | str | `return Decision(UNSUPPORTED_QUERY, "", None, (), ("query_not_proposition",))` | `return Decision(UNSUPPORTED_QUERY, "", None, (), (('query_not_proposition_x'),))` |
| `TrialLedger/layer2/entail.py::decide` | int | `members = [premises[label][:4] for label in group if label != QUERY]` | `members = [premises[label][:(5)] for label in group if label != QUERY]` |
| `TrialLedger/layer2/entail.py::decide` | int | `members = [premises[label][:4] for label in group if label != QUERY]` | `members = [premises[label][:(5)] for label in group if label != QUERY]` |
| `TrialLedger/layer2/entail.py::decide` | str | `UNDETERMINED, written, None, (), tuple(sorted(blockers | {"no_constraint_mentions_query"}))` | `UNDETERMINED, written, None, (), tuple(sorted(blockers | {('no_constraint_mentions_query_x')}))` |
| `TrialLedger/layer2/entail.py::decide` | boolop | `if against is None or towards is None:` | `if (against is None and towards is None):` |
| `TrialLedger/landscape.py::value_problem` | boolop | `if not isinstance(item, dict) or tuple(item) != READING_KEYS:` | `if (not isinstance(item, dict) and tuple(item) != READING_KEYS):` |
| `TrialLedger/layer2/semantics/loader.py::unit_problems` | str | `elif parse.status == "abstained" or parse.spans != (Span("unit", 0, len(unit)),):` | `elif parse.status == ('abstained_x') or parse.spans != (Span("unit", 0, len(unit)),):` |
| `TrialLedger/layer2/semantics/loader.py::unit_problems` | str | `reason = parse.note or "not one unit, whole"` | `reason = parse.note or ('not one unit, whole_x')` |
| `TrialLedger/workbook.py::_record_rows` | str | `shown = "(null in the record)"` | `shown = ('(null in the record)_x')` |
| `TrialLedger/workbook.py::_record_rows` | str | `shown = "(empty list)"` | `shown = ('(empty list)_x')` |
| `TrialLedger/workbook.py::_record_rows` | str | `shown = "(empty object)"` | `shown = ('(empty object)_x')` |
| `TrialLedger/workbook.py::_record_rows` | str | `part for part in entry.location.replace("[", ".[").split(".") if not part.startswith("[")` | `part for part in entry.location.replace("[", ('.[_x')).split(".") if not part.startswith("[")` |
| `TrialLedger/layer2/evaluation.py::recall` | bool | `judged = [(record.claim.nct_id, j) for record, j in zip(gold, gold_judged, strict=True)]` | `judged = [(record.claim.nct_id, j) for record, j in zip(gold, gold_judged, strict=(False))]` |
| `TrialLedger/layer2/semantics/contracts.py::slug` | str | `elif out and out[-1] != "_":` | `elif out and out[-1] != ('__x'):` |
| `TrialLedger/layer2/semantics/contracts.py::slug` | str | `out.append("_")` | `out.append(('__x'))` |
| `TrialLedger/layer2/semantics/contracts.py::slug` | int | `elif out and out[-1] != "_":` | `elif out and out[-(2)] != "_":` |
| `TrialLedger/layer2/semantics/contracts.py::slug` | str | `return "".join(out).strip("_")` | `return "".join(out).strip(('__x'))` |
| `TrialLedger/layer2/evaluation.py::precision` | bool | `for claim, verdict in zip(emitted, verdicts, strict=True)` | `for claim, verdict in zip(emitted, verdicts, strict=(False))` |
| `TrialLedger/layer2/evaluation.py::precision` | str | `return rate("precision", level, judged, ("correct",), ("wrong", "spurious"))` | `return rate("precision", level, judged, ("correct",), ("wrong", ('spurious_x')))` |
| `TrialLedger/workbook.py::_document_count` | str | `return len(as_list(get(study, "documentSection", "largeDocumentModule", "largeDocs")))` | `return len(as_list(get(study, ('documentSection_x'), "largeDocumentModule", "largeDocs")))` |
| `TrialLedger/workbook.py::_document_count` | str | `return len(as_list(get(study, "documentSection", "largeDocumentModule", "largeDocs")))` | `return len(as_list(get(study, "documentSection", ('largeDocumentModule_x'), "largeDocs")))` |
| `TrialLedger/workbook.py::_document_count` | str | `return len(as_list(get(study, "documentSection", "largeDocumentModule", "largeDocs")))` | `return len(as_list(get(study, "documentSection", "largeDocumentModule", ('largeDocs_x'))))` |
| `TrialLedger/readout.py::_write_book` | int | `written = 0` | `written = (1)` |
| `TrialLedger/readout.py::_write_book` | str | `sheet.print_title_rows = "1:1"` | `sheet.print_title_rows = ('1:1_x')` |
| `TrialLedger/readout.py::_write_book` | bool | `sheet.sheet_properties.pageSetUpPr.fitToPage = True` | `sheet.sheet_properties.pageSetUpPr.fitToPage = (False)` |
| `TrialLedger/readout.py::_write_book` | int | `sheet.page_setup.fitToWidth = 1` | `sheet.page_setup.fitToWidth = (2)` |
| `TrialLedger/readout.py::_write_book` | int | `sheet.page_setup.fitToHeight = 0` | `sheet.page_setup.fitToHeight = (1)` |
| `TrialLedger/readout.py::_write_book` | int | `for start in range(0, max(len(rows), 1), CAPACITY):` | `for start in range(0, max(len(rows), (2)), CAPACITY):` |
| `TrialLedger/readout.py::_write_book` | compare | `if start <= begin < start + len(part):` | `if (start < begin < start + len(part)):` |
| `TrialLedger/readout.py::_write_book` | boolop | `if name == contract.POSTED and address_index is not None:` | `if (name == contract.POSTED or address_index is not None):` |
| `TrialLedger/readout.py::_write_book` | compare | `summary = len(row) > 1 and all(held[0] is None for held in row[1:])` | `summary = (len(row) >= 1) and all(held[0] is None for held in row[1:])` |
| `TrialLedger/readout.py::_write_book` | int | `lines = row_lines(row_for_height, row_widths) if wrap else 1` | `lines = row_lines(row_for_height, row_widths) if wrap else (2)` |
| `TrialLedger/readout.py::_write_book` | compare | `if header != contract.ADDRESS` | `if (header == contract.ADDRESS)` |
| `TrialLedger/readout.py::_write_book` | int | `contract.MAX_ROW_HEIGHT_POINTS, round(header_lines * LINE_POINTS, 2)` | `contract.MAX_ROW_HEIGHT_POINTS, round(header_lines * LINE_POINTS, (3))` |
| `TrialLedger/readout.py::_write_book` | int | `written += len(headers) * (len(part) + 1)` | `written += len(headers) * (len(part) + (2))` |
| `TrialLedger/readout.py::_write_book` | int | `summary = len(row) > 1 and all(held[0] is None for held in row[1:])` | `summary = len(row) > (2) and all(held[0] is None for held in row[1:])` |
| `TrialLedger/readout.py::_write_book` | int | `contract.MAX_ROW_HEIGHT_POINTS, round(lines * LINE_POINTS, 2)` | `contract.MAX_ROW_HEIGHT_POINTS, round(lines * LINE_POINTS, (3))` |
| `TrialLedger/readout.py::_write_book` | bool | `sheet.append([_book_cell(sheet, label(header), True, True, styles) for header in headers])` | `sheet.append([_book_cell(sheet, label(header), (False), True, styles) for header in headers])` |
| `TrialLedger/readout.py::_write_book` | bool | `sheet.append([_book_cell(sheet, label(header), True, True, styles) for header in headers])` | `sheet.append([_book_cell(sheet, label(header), True, (False), styles) for header in headers])` |
| `TrialLedger/readout.py::_write_book` | bool | `written_row = [_book_cell(sheet, held, False, wrap, styles) for held in row]` | `written_row = [_book_cell(sheet, held, (True), wrap, styles) for held in row]` |
| `TrialLedger/readout.py::_write_book` | int | `row_for_height = (row[0],)` | `row_for_height = (row[(1)],)` |
| `TrialLedger/readout.py::_write_book` | bool | `for header, width in zip(headers, width_of, strict=True)` | `for header, width in zip(headers, width_of, strict=(False))` |
| `TrialLedger/readout.py::_write_book` | compare | `if len(parts) >= 4` | `if (len(parts) > 4)` |
| `TrialLedger/readout.py::_write_book` | int | `if len(parts) >= 4` | `if len(parts) >= (5)` |
| `TrialLedger/readout.py::_write_book` | int | `sheet.row_breaks.append(Break(id=begin - start + 1))` | `sheet.row_breaks.append(Break(id=begin - start + (2)))` |
| `TrialLedger/readout.py::_write_book` | int | `summary = len(row) > 1 and all(held[0] is None for held in row[1:])` | `summary = len(row) > 1 and all(held[(1)] is None for held in row[1:])` |
| `TrialLedger/readout.py::_write_book` | compare | `if header != contract.ADDRESS` | `if (header == contract.ADDRESS)` |
| `TrialLedger/readout.py::_write_book` | bool | `for header, held, width in zip(headers, row, width_of, strict=True)` | `for header, held, width in zip(headers, row, width_of, strict=(False))` |
| `TrialLedger/readout.py::_write_book` | str | `parts = address.strip("/").split("/") if isinstance(address, str) else []` | `parts = address.strip(('/_x')).split("/") if isinstance(address, str) else []` |
| `TrialLedger/readout.py::_write_book` | int | `tuple(parts[:4])` | `tuple(parts[:(5)])` |
| `TrialLedger/readout.py::_write_book` | bool | `for header, width in zip(headers, width_of, strict=True)` | `for header, width in zip(headers, width_of, strict=(False))` |
| `TrialLedger/readout.py::_write_book` | str | `book.properties.creator = "TrialLedger"` | `book.properties.creator = ('TrialLedger_x')` |
| `TrialLedger/request.py::_subclass_expansions` | int | `waiting = "pending" in (tree_code, members[0])` | `waiting = "pending" in (tree_code, members[(1)])` |
| `TrialLedger/steps.py::follow_ids` | int | `total = 0` | `total = (1)` |
| `TrialLedger/steps.py::follow_ids` | int | `empty_streak = 0 if page else empty_streak + 1` | `empty_streak = (1) if page else empty_streak + 1` |
| `TrialLedger/layer2/evaluation.py::gold_problems` | compare | `inside = 0 <= claim.start < claim.end <= len(text)` | `inside = (0 < claim.start < claim.end <= len(text))` |
| `TrialLedger/layer2/evaluation.py::gold_problems` | int | `inside = 0 <= claim.start < claim.end <= len(text)` | `inside = (1) <= claim.start < claim.end <= len(text)` |
| `TrialLedger/readout.py::registry_number` | str | `whole, _point, places = text.lstrip("-").partition(".")` | `whole, _point, places = text.lstrip(('-_x')).partition(".")` |
| `TrialLedger/readout.py::registry_number` | str | `digits = (whole + places).lstrip("0")` | `digits = (whole + places).lstrip(('0_x'))` |
| `TrialLedger/readout.py::registry_number` | boolop | `if shown != text or (text.startswith("-") and value == 0):` | `if (shown != text and (text.startswith('-') and value == 0)):` |
| `TrialLedger/readout.py::registry_number` | str | `if shown != text or (text.startswith("-") and value == 0):` | `if shown != text or (text.startswith(('-_x')) and value == 0):` |
| `TrialLedger/readout.py::registry_number` | int | `if shown != text or (text.startswith("-") and value == 0):` | `if shown != text or (text.startswith("-") and value == (1)):` |
| `TrialLedger/classes.py::rxclass_classes` | boolop | `if not isinstance(class_id, str) or not isinstance(name, str):` | `if (not isinstance(class_id, str) and (not isinstance(name, str))):` |
| `TrialLedger/layer2/profile.py::element_silence` | int | `section = element.split(":", 1)[0]` | `section = element.split(":", (2))[0]` |
| `TrialLedger/readout.py::date_text` | compare | `if found is None:` | `if (found is not None):` |
| `TrialLedger/readout.py::date_text` | compare | `if month is None:` | `if (month is not None):` |
| `TrialLedger/readout.py::date_text` | compare | `if not 1 <= int(month) <= 12:` | `if not (1 < int(month) <= 12):` |
| `TrialLedger/readout.py::date_text` | int | `if not 1 <= int(month) <= 12:` | `if not (2) <= int(month) <= 12:` |
| `TrialLedger/readout.py::date_text` | int | `if not 1 <= int(month) <= 12:` | `if not 1 <= int(month) <= (13):` |
| `TrialLedger/readout.py::date_text` | compare | `written = f"{MONTHS[int(month) - 1]}-{year}" if day is None else f"{day}-{MONTHS[int(month) - 1]}-{year}"` | `written = f"{MONTHS[int(month) - 1]}-{year}" if (day is not None) else f"{day}-{MONTHS[int(month) - 1]}-{year}"` |
| `TrialLedger/readout.py::date_text` | compare | `return written if time is None else f"{written} {time}"` | `return written if (time is not None) else f"{written} {time}"` |
| `TrialLedger/layer2/evaluation.py::miss_rate` | bool | `judged = [(record.claim.nct_id, j) for record, j in zip(gold, gold_judged, strict=True)]` | `judged = [(record.claim.nct_id, j) for record, j in zip(gold, gold_judged, strict=(False))]` |
| `TrialLedger/checks.py::approval` | compare | `return "approved" if self.id in APPROVED else "proposed"` | `return "approved" if (self.id not in APPROVED) else "proposed"` |
| `TrialLedger/checks.py::approval` | str | `return "approved" if self.id in APPROVED else "proposed"` | `return ('approved_x') if self.id in APPROVED else "proposed"` |
| `TrialLedger/checks.py::approval` | str | `return "approved" if self.id in APPROVED else "proposed"` | `return "approved" if self.id in APPROVED else ('proposed_x')` |
| `TrialLedger/readout.py::index_cells` | str | `acronym = study.get("acronym")` | `acronym = study.get(('acronym_x'))` |
| `TrialLedger/readout.py::index_cells` | compare | `short = acronym if held_kind(acronym) == "plain" else study.get("brief_title")` | `short = acronym if (held_kind(acronym) != 'plain') else study.get("brief_title")` |
| `TrialLedger/readout.py::index_cells` | str | `short = acronym if held_kind(acronym) == "plain" else study.get("brief_title")` | `short = acronym if held_kind(acronym) == ('plain_x') else study.get("brief_title")` |
| `TrialLedger/readout.py::index_cells` | str | `short = acronym if held_kind(acronym) == "plain" else study.get("brief_title")` | `short = acronym if held_kind(acronym) == "plain" else study.get(('brief_title_x'))` |
| `TrialLedger/readout.py::index_cells` | str | `status = value_words(study.get("overall_status"), "Status")` | `status = value_words(study.get("overall_status"), ('Status_x'))` |
| `TrialLedger/readout.py::index_cells` | str | `status = value_words(study.get("overall_status"), "Status")` | `status = value_words(study.get(('overall_status_x')), "Status")` |
| `TrialLedger/readout.py::index_cells` | boolop | `if held_kind(study.get("last_known_status")) == "plain" and applies("studies[].last_known_status", study):` | `if (held_kind(study.get('last_known_status')) == 'plain' or applies('studies[].last_known_status', study)):` |
| `TrialLedger/readout.py::index_cells` | compare | `if held_kind(study.get("last_known_status")) == "plain" and applies("studies[].last_known_status", study):` | `if (held_kind(study.get('last_known_status')) != 'plain') and applies("studies[].last_known_status", study):` |
| `TrialLedger/readout.py::index_cells` | str | `if held_kind(study.get("last_known_status")) == "plain" and applies("studies[].last_known_status", study):` | `if held_kind(study.get("last_known_status")) == ('plain_x') and applies("studies[].last_known_status", study):` |
| `TrialLedger/readout.py::index_cells` | str | `if held_kind(study.get("last_known_status")) == "plain" and applies("studies[].last_known_status", study):` | `if held_kind(study.get("last_known_status")) == "plain" and applies(('studies[].last_known_status_x'), study):` |
| `TrialLedger/readout.py::index_cells` | str | `if held_kind(study.get("last_known_status")) == "plain" and applies("studies[].last_known_status", study):` | `if held_kind(study.get(('last_known_status_x'))) == "plain" and applies("studies[].last_known_status", study):` |
| `TrialLedger/readout.py::index_cells` | str | `held = study.get("registered_outcomes")` | `held = study.get(('registered_outcomes_x'))` |
| `TrialLedger/readout.py::index_cells` | compare | `primary = [o for o in (held if isinstance(held, list) else []) if o.get("category") == "primary"]` | `primary = [o for o in (held if isinstance(held, list) else []) if (o.get('category') != 'primary')]` |
| `TrialLedger/readout.py::index_cells` | str | `primary = [o for o in (held if isinstance(held, list) else []) if o.get("category") == "primary"]` | `primary = [o for o in (held if isinstance(held, list) else []) if o.get("category") == ('primary_x')]` |
| `TrialLedger/readout.py::index_cells` | str | `primary = [o for o in (held if isinstance(held, list) else []) if o.get("category") == "primary"]` | `primary = [o for o in (held if isinstance(held, list) else []) if o.get(('category_x')) == "primary"]` |
| `TrialLedger/readout.py::index_cells` | str | `endpoint = value_words(primary[0].get("measure")) if primary else NOT_STATED` | `endpoint = value_words(primary[0].get(('measure_x'))) if primary else NOT_STATED` |
| `TrialLedger/readout.py::index_cells` | int | `endpoint = value_words(primary[0].get("measure")) if primary else NOT_STATED` | `endpoint = value_words(primary[(1)].get("measure")) if primary else NOT_STATED` |
| `TrialLedger/readout.py::index_cells` | compare | `endpoint = f"{endpoint} (+{len(primary) - 1} more)" if len(primary) > 1 else endpoint` | `endpoint = f"{endpoint} (+{len(primary) - 1} more)" if (len(primary) >= 1) else endpoint` |
| `TrialLedger/readout.py::index_cells` | int | `endpoint = f"{endpoint} (+{len(primary) - 1} more)" if len(primary) > 1 else endpoint` | `endpoint = f"{endpoint} (+{len(primary) - 1} more)" if len(primary) > (2) else endpoint` |
| `TrialLedger/readout.py::index_cells` | str | `first = study.get("results_first_posted")` | `first = study.get(('results_first_posted_x'))` |
| `TrialLedger/readout.py::index_cells` | boolop | `date_text(first) if results_posted(study) and held_kind(first) == "plain" else results_words(study)[0]` | `date_text(first) if (results_posted(study) or held_kind(first) == 'plain') else results_words(study)[0]` |
| `TrialLedger/readout.py::index_cells` | compare | `date_text(first) if results_posted(study) and held_kind(first) == "plain" else results_words(study)[0]` | `date_text(first) if results_posted(study) and (held_kind(first) != 'plain') else results_words(study)[0]` |
| `TrialLedger/readout.py::index_cells` | int | `date_text(first) if results_posted(study) and held_kind(first) == "plain" else results_words(study)[0]` | `date_text(first) if results_posted(study) and held_kind(first) == "plain" else results_words(study)[(1)]` |
| `TrialLedger/readout.py::index_cells` | str | `date_text(first) if results_posted(study) and held_kind(first) == "plain" else results_words(study)[0]` | `date_text(first) if results_posted(study) and held_kind(first) == ('plain_x') else results_words(study)[0]` |
| `TrialLedger/readout.py::index_cells` | str | `held = study.get("references")` | `held = study.get(('references_x'))` |
| `TrialLedger/readout.py::index_cells` | int | `marked = sum(1 for reference in references if reference.get("type") == "RESULT")` | `marked = sum((2) for reference in references if reference.get("type") == "RESULT")` |
| `TrialLedger/readout.py::index_cells` | compare | `marked = sum(1 for reference in references if reference.get("type") == "RESULT")` | `marked = sum(1 for reference in references if (reference.get('type') != 'RESULT'))` |
| `TrialLedger/readout.py::index_cells` | str | `marked = sum(1 for reference in references if reference.get("type") == "RESULT")` | `marked = sum(1 for reference in references if reference.get("type") == ('RESULT_x'))` |
| `TrialLedger/readout.py::index_cells` | str | `marked = sum(1 for reference in references if reference.get("type") == "RESULT")` | `marked = sum(1 for reference in references if reference.get(('type_x')) == "RESULT")` |
| `TrialLedger/readout.py::index_cells` | str | `update = study.get("last_update_posted")` | `update = study.get(('last_update_posted_x'))` |
| `TrialLedger/readout.py::index_cells` | str | `cell(study["nct"], "known", "studies[].nct", "", "", study.get("link") or ""),` | `cell(study["nct"], ('known_x'), "studies[].nct", "", "", study.get("link") or ""),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(study["nct"], "known", "studies[].nct", "", "", study.get("link") or ""),` | `cell(study["nct"], "known", ('studies[].nct_x'), "", "", study.get("link") or ""),` |
| `TrialLedger/readout.py::index_cells` | boolop | `cell(study["nct"], "known", "studies[].nct", "", "", study.get("link") or ""),` | `cell(study["nct"], "known", "studies[].nct", "", "", (study.get('link') and '')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(short), "known"),` | `cell(value_words(short), ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(sponsor, "known"),` | `cell(sponsor, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("phases"), "Phase", " / "), "known"),` | `cell(value_words(study.get("phases"), "Phase", " / "), ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(status, "known"),` | `cell(status, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("conditions")), "known"),` | `cell(value_words(study.get("conditions")), ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(design, "known"),` | `cell(design, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(enrollment, "known"),` | `cell(enrollment, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(enrollment_type, "known"),` | `cell(enrollment_type, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(start, "known"),` | `cell(start, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(endpoint, "known"),` | `cell(endpoint, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(results, "known"),` | `cell(results, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(cited, "known", "", "", "", publications if references else ""),` | `cell(cited, ('known_x'), "", "", "", publications if references else ""),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("countries")), "known"),` | `cell(value_words(study.get("countries")), ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(date_text(update) if held_kind(update) == "plain" else NOT_STATED, "known"),` | `cell(date_text(update) if held_kind(update) == "plain" else NOT_STATED, ('known_x')),` |
| `TrialLedger/readout.py::index_cells` | str | `cell("Dossier", LABEL, "", "", "", dossier),` | `cell(('Dossier_x'), LABEL, "", "", "", dossier),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("phases"), "Phase", " / "), "known"),` | `cell(value_words(study.get("phases"), ('Phase_x'), " / "), "known"),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("phases"), "Phase", " / "), "known"),` | `cell(value_words(study.get("phases"), "Phase", (' / _x')), "known"),` |
| `TrialLedger/readout.py::index_cells` | compare | `cell(date_text(update) if held_kind(update) == "plain" else NOT_STATED, "known"),` | `cell(date_text(update) if (held_kind(update) != 'plain') else NOT_STATED, "known"),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(study["nct"], "known", "studies[].nct", "", "", study.get("link") or ""),` | `cell(study["nct"], "known", "studies[].nct", "", "", study.get(('link_x')) or ""),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("phases"), "Phase", " / "), "known"),` | `cell(value_words(study.get(('phases_x')), "Phase", " / "), "known"),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("conditions")), "known"),` | `cell(value_words(study.get(('conditions_x'))), "known"),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(value_words(study.get("countries")), "known"),` | `cell(value_words(study.get(('countries_x'))), "known"),` |
| `TrialLedger/readout.py::index_cells` | str | `cell(date_text(update) if held_kind(update) == "plain" else NOT_STATED, "known"),` | `cell(date_text(update) if held_kind(update) == ('plain_x') else NOT_STATED, "known"),` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `round(a / b, 4),` | `round(a / b, (5)),` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `round(c / d, 4),` | `round(c / d, (5)),` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `if element not in t[4] and element_silence(element, t[7], t[3], t[8]) == "abbreviated"` | `if element not in t[(5)] and element_silence(element, t[7], t[3], t[8]) == "abbreviated"` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `if element not in t[4] and element_silence(element, t[7], t[3], t[8]) == "abbreviated"` | `if element not in t[4] and element_silence(element, t[(8)], t[3], t[8]) == "abbreviated"` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | compare | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[2]))` | `return sorted(rows, key=lambda row: (row[0], (row[15] == 'proposed'), -row[9], row[1], row[2]))` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[2]))` | `return sorted(rows, key=lambda row: (row[(1)], row[15] != "proposed", -row[9], row[1], row[2]))` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | str | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[2]))` | `return sorted(rows, key=lambda row: (row[0], row[15] != ('proposed_x'), -row[9], row[1], row[2]))` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[2]))` | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[(2)], row[2]))` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[2]))` | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[(3)]))` |
| `TrialLedger/layer2/profile.py::mechanism_rows` | int | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[2]))` | `return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[(10)], row[1], row[2]))` |
| `TrialLedger/mcp_server.py::argument_problems` | str | `and re.fullmatch(described[name]["pattern"].removeprefix("^").removesuffix("$"), value) is None` | `and re.fullmatch(described[name]["pattern"].removeprefix("^").removesuffix(('$_x')), value) is None` |
| `TrialLedger/mcp_server.py::argument_problems` | str | `and re.fullmatch(described[name]["pattern"].removeprefix("^").removesuffix("$"), value) is None` | `and re.fullmatch(described[name]["pattern"].removeprefix(('^_x')).removesuffix("$"), value) is None` |
| `TrialLedger/request.py::class_candidate_selection` | str | `if code in ("malformed", "not_found"):` | `if code in (('malformed_x'), "not_found"):` |
| `TrialLedger/request.py::class_candidate_selection` | str | `if code in ("malformed", "not_found"):` | `if code in ("malformed", ('not_found_x')):` |
| `TrialLedger/request.py::class_candidate_selection` | str | `return "catalog_malformed", []` | `return ('catalog_malformed_x'), []` |
| `TrialLedger/readout.py::shown_field` | compare | `if name in DATES and held_kind(value) == "plain":` | `if name in DATES and (held_kind(value) != 'plain'):` |
| `TrialLedger/readout.py::shown_field` | str | `if name in DATES and held_kind(value) == "plain":` | `if name in DATES and held_kind(value) == ('plain_x'):` |
| `TrialLedger/readout.py::shown_field` | str | `held = at(study, beside.removeprefix("studies[]."))` | `held = at(study, beside.removeprefix(('studies[]._x')))` |
| `TrialLedger/readout.py::shown_field` | compare | `if main == name and (held_kind(held) == "plain" or beside == "studies[].enrollment.type"):` | `if main == name and ((held_kind(held) != 'plain') or beside == "studies[].enrollment.type"):` |
| `TrialLedger/readout.py::shown_field` | str | `if main == name and (held_kind(held) == "plain" or beside == "studies[].enrollment.type"):` | `if main == name and (held_kind(held) == ('plain_x') or beside == "studies[].enrollment.type"):` |
| `TrialLedger/readout.py::shown_field` | str | `if words == extra and held_kind(value) != "plain" and held_kind(held) != "plain":` | `if words == extra and held_kind(value) != ('plain_x') and held_kind(held) != "plain":` |
| `TrialLedger/readout.py::shown_field` | str | `if words == extra and held_kind(value) != "plain" and held_kind(held) != "plain":` | `if words == extra and held_kind(value) != "plain" and held_kind(held) != ('plain_x'):` |
| `TrialLedger/eligibility.py::split_eligibility` | str | `content = line.strip(" \t")` | `content = line.strip((' \t_x'))` |
| `TrialLedger/eligibility.py::split_eligibility` | compare | `if end < start:` | `if (end <= start):` |
| `TrialLedger/record.py::verify_folder` | str | `return "not_certified", problems[:limit]` | `return ('not_certified_x'), problems[:limit]` |
| `TrialLedger/record.py::verify_folder` | str | `if any(problem.startswith("record.no_digests") for problem in problems):` | `if any(problem.startswith(('record.no_digests_x')) for problem in problems):` |
| `TrialLedger/readout.py::result_words` | str | `return " or ".join(result_words(item) for item in result) or "nothing"` | `return " or ".join(result_words(item) for item in result) or ('nothing_x')` |
| `TrialLedger/readout.py::result_words` | str | `or "nothing"` | `or ('nothing_x')` |
| `TrialLedger/readout.py::result_words` | str | `"; ".join(f"{str(key).replace('_', ' ')}: {result_words(item)}" for key, item in result.items())` | `('; _x').join(f"{str(key).replace('_', ' ')}: {result_words(item)}" for key, item in result.items())` |
| `TrialLedger/readout.py::least_settled` | str | `if held & {"Unresolved", "Proposed", "Interpolated"}:` | `if held & {('Unresolved_x'), "Proposed", "Interpolated"}:` |
| `TrialLedger/readout.py::least_settled` | str | `if held & {"Unresolved", "Proposed", "Interpolated"}:` | `if held & {"Unresolved", ('Proposed_x'), "Interpolated"}:` |
| `TrialLedger/readout.py::place` | compare | `return (sheet if part == 0 else f"{sheet} {part + 1}"), offset + 2` | `return (sheet if (part != 0) else f"{sheet} {part + 1}"), offset + 2` |
| `TrialLedger/readout.py::place` | int | `return (sheet if part == 0 else f"{sheet} {part + 1}"), offset + 2` | `return (sheet if part == 0 else f"{sheet} {part + 1}"), offset + (3)` |
| `TrialLedger/readout.py::place` | int | `return (sheet if part == 0 else f"{sheet} {part + 1}"), offset + 2` | `return (sheet if part == (1) else f"{sheet} {part + 1}"), offset + 2` |
| `TrialLedger/readout.py::as_reading` | boolop | `return value if held_kind(value) == "reading" and isinstance(value, dict) else None` | `return value if (held_kind(value) == 'reading' or isinstance(value, dict)) else None` |
