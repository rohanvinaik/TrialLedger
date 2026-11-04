# Clinical design decision list

Session: hfref-persona
Revision: final-walkthrough-v2

Only the represented restrictions are checked. Caller origin labels record declarations, not authenticated confirmation.

## Should a patient without AF, EF 38%, no recent HF hospitalization and NT-proBNP 800 pg/mL be able to enrol (EMPEROR-Reduced would not have, under either reading)?

Current result: Open design choice (design_choice). Selected option: Open.

- Admitted (flat 600 pg/mL threshold): The represented proposition is allowed but not required under these restrictions (UNDETERMINED). Feasibility: Compatible with the represented restrictions (feasible). Deciding premises: ["lvef", "ntprobnp_af", "ntprobnp_no_af"]. Open items: Both sides remain possible under the represented restrictions (undecided_by_constraints).
- Excluded (EF-banded thresholds): The represented proposition is allowed but not required under these restrictions (UNDETERMINED). Feasibility: Compatible with the represented restrictions (feasible). Deciding premises: ["lvef", "ntprobnp_af", "ntprobnp_no_af"]. Open items: Both sides remain possible under the represented restrictions (undecided_by_constraints).

Origin: Computed from declared premises: user:draft-v1 (simulated exchange 1)
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/c7242e9f2b61233a5cb715877cc642f0303c22332c1760d54dd4c29a2fa24615.json#/response/result/decisions/0`

## Should NYHA class IV patients be able to enrol?

Current result: Recorded clinical choice (chosen_by_person). Selected option: NYHA IV can enrol.

- NYHA IV can enrol: The represented proposition is allowed but not required under these restrictions (UNDETERMINED). Feasibility: Compatible with the represented restrictions (feasible). Deciding premises: ["nyha"]. Open items: Both sides remain possible under the represented restrictions (undecided_by_constraints).
- Everyone must be NYHA I-III: The represented proposition is allowed but not required under these restrictions (UNDETERMINED). Feasibility: Compatible with the represented restrictions (feasible). Deciding premises: ["nyha"]. Open items: Both sides remain possible under the represented restrictions (undecided_by_constraints).

Origin: Caller-declared clinical choice: simulated-clinician:final-walkthrough-nyha-widening
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/c7242e9f2b61233a5cb715877cc642f0303c22332c1760d54dd4c29a2fa24615.json#/response/result/decisions/1`

## Changes from the previous revision

- af-ntp900: Inputs changed; clinical answer, support and origin stayed the same (input_only). Answer: unchanged. Support: unchanged. Origin: unchanged.
- current-sglt2i: Inputs changed; clinical answer, support and origin stayed the same (input_only). Answer: unchanged. Support: unchanged. Origin: unchanged.
- ef38-no-hfh-ntp800: Inputs changed; clinical answer, support and origin stayed the same (input_only). Answer: unchanged. Support: unchanged. Origin: unchanged.
- ef38-no-hfh-ntp800-excluded: Inputs changed; clinical answer, support and origin stayed the same (input_only). Answer: unchanged. Support: unchanged. Origin: unchanged.
- egfr-25: Inputs changed; clinical answer, support and origin stayed the same (input_only). Answer: unchanged. Support: unchanged. Origin: unchanged.
- non-iv-required: Clinical answer changed (answer_changed). Answer: changed. Support: changed. Origin: changed.
- nyha-iv-patient: Clinical answer changed (answer_changed). Answer: changed. Support: changed. Origin: changed.
- ntprobnp-banding: Inputs changed; clinical answer, support and origin stayed the same (input_only). Answer: unchanged. Support: unchanged. Origin: unchanged.
- nyha-iv: Clinical answer changed (answer_changed). Answer: changed. Support: changed. Origin: changed.
