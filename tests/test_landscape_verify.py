"""Law-12 offline landscape replay and authored failure cases.

Runs are created through operate.run with saved registry bodies and direct RxNav answers.
The verifier replays retained inputs without network access or treating output as its oracle. Source, code,
record, workbook and missing-data failures remain separate named outcomes; no clinical inference is certified.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from openpyxl import load_workbook
from records import results_study
from test_landscape_run import Registry, RxNav, direct, drug_free

from TrialLedger import landscape, operate
from TrialLedger.landscape_verify import strict_json, verify_landscape


def document(path):
    return strict_json(path.read_bytes())


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def change_manifest(folder, mutate):
    record = document(folder / "landscape.json")
    mutate(record["manifest"])
    save(folder / "landscape.json", record)
    save(folder / "manifest.json", record["manifest"])


def completed_run(folder, *, with_drug=False):
    study = results_study()
    if not with_drug:
        drug_free(study)
    nct = study["protocolSection"]["identificationModule"]["nctId"]
    outcome = direct(folder, {"params": {"filter.ids": nct}}, Registry([study]), RxNav())
    assert outcome.status == "complete", outcome
    return folder


@pytest.fixture
def run_folder(tmp_path):
    return completed_run(tmp_path / "run")


def test_actual_production_run_replays_without_network(run_folder, monkeypatch):
    import httpx

    def forbidden(*_args, **_kwargs):
        pytest.fail("offline verifier attempted a network lookup")

    monkeypatch.setattr(httpx.Client, "request", forbidden)
    monkeypatch.setattr(operate.rx, "http_get", forbidden)
    assert verify_landscape(run_folder) == ("verified", [])


@pytest.mark.parametrize("kind", ["value", "status", "group"])
def test_output_value_status_or_group_change_cannot_be_used_as_replay_oracle(run_folder, kind):
    record = document(run_folder / "landscape.json")
    study = record["studies"][0]
    if kind == "value":
        study["enrollment"]["count"] += 1
    elif kind == "status":
        study["results_posted"]["status"] = "unresolved"
    else:
        study["posted_outcomes"][0]["groups"][0]["title"] = "Wrong treatment group"
    save(run_folder / "landscape.json", record)
    assert verify_landscape(run_folder)[0] == "changed"


@pytest.mark.parametrize("kind", ["format", "link", "value"])
def test_workbook_parts_format_and_links_are_compared_even_if_cell_values_agree(run_folder, kind):
    path = run_folder / "landscape.xlsx"
    book = load_workbook(path)
    cell = book["Trial index"]["A2"]
    if kind == "format":
        cell.number_format = "0.0000"
    elif kind == "link":
        cell.hyperlink = "https://example.invalid/wrong-trial"
    else:
        cell.value = "NCT99999999"
    book.save(path)
    book.close()
    assert verify_landscape(run_folder)[0] == "changed"


def test_standalone_manifest_must_agree(run_folder):
    manifest = document(run_folder / "manifest.json")
    manifest["retrieval"]["read"] += 1
    save(run_folder / "manifest.json", manifest)
    code, details = verify_landscape(run_folder)
    assert code == "changed" and details[0].startswith("manifest_mismatch")


def test_wrong_code_is_distinct_and_copied_rule_versions_cannot_bypass_source_root(run_folder, monkeypatch):
    change_manifest(
        run_folder, lambda manifest: manifest["rule_versions"].update(derivation_code_root="wrong")
    )
    claimed = document(run_folder / "manifest.json")["rule_versions"]
    monkeypatch.setattr(landscape, "RULE_VERSIONS", claimed)
    code, details = verify_landscape(run_folder)
    assert code == "wrong_code" and details[0].startswith("code_root")


@pytest.mark.parametrize(
    "name",
    [
        "manifest.json",
        "fetches.json",
        "request.json",
        "resolution.json",
        "scope.json",
        "landscape.xlsx",
        "bodies/studies-001.json",
    ],
)
def test_missing_source_or_output_is_never_a_pass(run_folder, name):
    (run_folder / name).unlink()
    assert verify_landscape(run_folder)[0] == "missing_source"


def test_present_input_without_digest_is_not_silently_trusted(run_folder):
    change_manifest(run_folder, lambda manifest: manifest["input_digests"].pop("request.json"))
    assert verify_landscape(run_folder)[0] == "missing_source"


def test_registry_raw_body_change_fails_its_recorded_digest(run_folder):
    path = run_folder / "bodies" / "studies-001.json"
    body = document(path)
    body["studies"][0]["protocolSection"]["identificationModule"]["briefTitle"] = "Changed source title"
    save(path, body)
    code, details = verify_landscape(run_folder)
    assert code == "invalid_source" and details[0].startswith("registry_digest")


def test_direct_classes_cache_is_a_bound_input_and_missing_is_not_no_class(tmp_path):
    folder = completed_run(tmp_path / "with-drug", with_drug=True)
    assert verify_landscape(folder) == ("verified", [])
    path = folder / "classes.json"
    cache = document(path)
    first = next(iter(cache["answers"]))
    cache["answers"][first]["state"] = "altered answer"
    save(path, cache)
    assert verify_landscape(folder)[0] == "invalid_source"
    path.unlink()
    assert verify_landscape(folder)[0] == "missing_source"


def test_duplicate_json_keys_are_rejected_in_record_and_saved_inputs(run_folder):
    (run_folder / "landscape.json").write_bytes(b'{"manifest":{},"manifest":{}}')
    assert verify_landscape(run_folder)[0] == "unreadable"


def test_record_source_warrants_do_not_claim_registry_truth(run_folder):
    record = document(run_folder / "landscape.json")
    assert record["manifest"]["study_digests"]
    assert record["manifest"]["input_digests"]
    assert record["schema_version"] == 4
    assert verify_landscape(run_folder) == ("verified", [])


def test_real_cli_verifies_a_cold_run_then_refuses_changed_record(run_folder, capsys):
    from TrialLedger import cli

    assert cli.main(["verify", str(run_folder)]) == 0
    assert "verified" in capsys.readouterr().out
    record = document(run_folder / "landscape.json")
    record["studies"][0]["enrollment"]["count"] += 1
    save(run_folder / "landscape.json", record)
    assert cli.main(["verify", str(run_folder)]) == 1
    assert "changed" in capsys.readouterr().err


def test_fetch_history_cannot_claim_another_request_for_the_same_saved_bodies(run_folder):
    path = run_folder / "fetches.json"
    fetches = document(path)
    fetches[0]["url"] = "https://example.invalid/not-the-registry"
    save(path, fetches)
    code, details = verify_landscape(run_folder)
    assert code == "invalid_source" and details[0].startswith("fetch_history")


def test_duplicate_keys_in_a_bound_persisted_input_are_refused_even_with_updated_digest(run_folder):
    path = run_folder / "request.json"
    path.write_bytes(b'{"params":{},"params":{}}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    change_manifest(run_folder, lambda manifest: manifest["input_digests"].update({"request.json": digest}))
    code, details = verify_landscape(run_folder)
    assert code == "unreadable" and "duplicate_key" in details[0]


def test_saved_real_three_trial_bodies_replay_in_documented_relay_mode(tmp_path):
    from test_landscape_run import relay_to_the_end

    from tests.schema3_records import BODIES, SAMPLE

    folder = tmp_path / "real-three"
    request = {"params": {"filter.ids": ",".join(SAMPLE)}}
    statuses, outcome = relay_to_the_end(folder, request, Registry([BODIES[nct] for nct in SAMPLE]), RxNav())
    assert statuses[-1] == "complete", outcome
    assert not (folder / "classes.json").exists()
    assert document(folder / "manifest.json")["retrieval"]["mode"] == "relay"
    assert verify_landscape(folder) == ("verified", [])


def test_recommitted_malformed_class_cache_is_not_an_empty_answer(tmp_path):
    folder = completed_run(tmp_path / "malformed-class", with_drug=True)
    path = folder / "classes.json"
    cache = document(path)
    answer = next(iter(cache["answers"].values()))
    answer["classes"] = None
    save(path, cache)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    change_manifest(folder, lambda manifest: manifest["input_digests"].update({"classes.json": digest}))
    code, details = verify_landscape(folder)
    assert code == "invalid_source" and "class rows" in details[0]


def test_absent_query_codes_cannot_document_an_empty_class_answer(tmp_path):
    folder = completed_run(tmp_path / "missing-class-codes", with_drug=True)
    path = folder / "classes.json"
    cache = document(path)
    next(iter(cache["answers"].values()))["codes"] = {}
    save(path, cache)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    change_manifest(folder, lambda manifest: manifest["input_digests"].update({"classes.json": digest}))
    code, details = verify_landscape(folder)
    assert code == "invalid_source" and "per-query codes" in details[0]


@pytest.mark.parametrize(
    "name",
    [
        "landscape.py",
        "readout.py",
        "classes.py",
        "eligibility.py",
        "registry/source_rules.py",
    ],
)
def test_landscape_root_binds_python_modules_including_nested_source_modules(tmp_path, name):
    from TrialLedger.landscape_warrants import derivation_root

    package = tmp_path / "package"
    module = package / name
    module.parent.mkdir(parents=True)
    module.write_text('"""Documentation."""\nVALUE = 1\n', encoding="utf-8")
    before = derivation_root(package)
    module.write_text('"""Documentation."""\nVALUE = 2\n', encoding="utf-8")
    assert derivation_root(package) != before


@pytest.mark.parametrize(
    "name",
    [
        "registry/ctg-metadata.json",
        "registry/ctg-enums.json",
        "registry/retained-source.json",
        "registry/runtime.bin",
    ],
)
def test_landscape_root_binds_runtime_resource_bytes(tmp_path, name):
    from TrialLedger.landscape_warrants import derivation_root

    package = tmp_path / "package"
    resource = package / name
    resource.parent.mkdir(parents=True)
    resource.write_bytes(b"first runtime resource")
    before = derivation_root(package)
    resource.write_bytes(b"changed runtime resource")
    assert derivation_root(package) != before


def test_landscape_root_ignores_comments_and_docstrings_but_binds_new_modules_and_paths(tmp_path):
    from TrialLedger.landscape_warrants import derivation_root

    package = tmp_path / "package"
    package.mkdir()
    module = package / "landscape.py"
    module.write_text(
        '"""First documentation."""\n# comment\ndef read():\n    """First detail."""\n    return 1\n'
    )
    before = derivation_root(package)
    module.write_text(
        '"""Changed documentation."""\n# changed comment\n'
        'def read():\n    """Other detail."""\n    return 1\n'
    )
    assert derivation_root(package) == before
    new_module = package / "new_runtime_rule.py"
    new_module.write_text("VALUE = 1\n")
    assert derivation_root(package) != before
    with_new_module = derivation_root(package)
    new_module.rename(package / "renamed_runtime_rule.py")
    assert derivation_root(package) != with_new_module


def test_development_inventory_and_caches_do_not_enter_landscape_root(tmp_path):
    from TrialLedger.landscape_warrants import derivation_files, derivation_root

    package = tmp_path / "package"
    package.mkdir()
    (package / "landscape.py").write_text("VALUE = 1\n")
    before = derivation_root(package)
    for relative in (
        "semantics/conformance-inventory.json",
        "semantics/__pycache__/rules.pyc",
        "semantics/cache/old-response.json",
        "registry/.DS_Store",
        "registry/pull.tmp",
    ):
        path = package / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"development or cache artifact")
    assert derivation_root(package) == before
    assert [path.relative_to(package).as_posix() for path in derivation_files(package)] == ["landscape.py"]


def test_actual_landscape_source_inventory_includes_the_verifier_and_root_implementation():
    from pathlib import Path

    from TrialLedger.landscape_warrants import derivation_files

    package = Path(landscape.__file__).parent
    names = {path.relative_to(package).as_posix() for path in derivation_files(package)}
    assert {
        "landscape.py",
        "readout.py",
        "classes.py",
        "eligibility.py",
        "links.py",
        "landscape_verify.py",
        "landscape_warrants.py",
        "registry/ctg-metadata.json",
        "registry/ctg-enums.json",
    } <= names
    assert "semantics/conformance-inventory.json" not in names


@pytest.mark.parametrize("name", ["request.json", "resolution.json", "scope.json"])
def test_changed_persisted_input_is_rejected_by_its_committed_bytes(run_folder, name):
    path = run_folder / name
    data = document(path)
    data["unexpected_source_change"] = True
    save(path, data)
    code, details = verify_landscape(run_folder)
    assert code == "invalid_source"
    assert details == [f"input_digest: changed {name}"]


def test_stale_rule_version_is_wrong_code_even_with_the_current_source_root(run_folder):
    change_manifest(run_folder, lambda manifest: manifest["rule_versions"].update(landscape_schema=-1))
    code, details = verify_landscape(run_folder)
    assert code == "wrong_code" and details[0].startswith("rule_versions")


@pytest.mark.parametrize("raw", [b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}'])
def test_non_json_numbers_in_retained_evidence_are_rejected(raw):
    with pytest.raises(ValueError, match="unreadable.*non-finite JSON"):
        strict_json(raw)


def test_non_finite_bound_input_is_refused_even_with_its_updated_digest(run_folder):
    path = run_folder / "request.json"
    path.write_bytes(b'{"params":{},"extra":NaN}')
    changed = hashlib.sha256(path.read_bytes()).hexdigest()
    change_manifest(run_folder, lambda manifest: manifest["input_digests"].update({"request.json": changed}))
    code, details = verify_landscape(run_folder)
    assert code == "unreadable" and "non-finite JSON" in details[0]
