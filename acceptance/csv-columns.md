# The registry's CSV columns, as its documentation states them

Source: ClinicalTrials.gov, "CSV Download" (https://clinicaltrials.gov/data-api/about-api/csv-download, "Last
updated on August 14, 2026"), retrieved 2026-11-01. The API's description of `format=csv`
(spec/ctg-oas-v2.yaml, `/studies`) points to this page for the columns. The page lists, for each column, the
data pieces it includes (piece names as in `/studies/metadata`); it does not state how the pieces of a column
are joined. `acceptance/compare.py` (`csv_expected`) builds each column from the JSON record by these pieces.
Where a column is one field or one list (Conditions, Phases, Collaborators, Interventions), the join was read
from the CSV itself (list items joined by "|"; an intervention written "type: name") and the column is then
compared exactly. Where a column joins several pieces (Age, Study Design, Other IDs, Locations, Study
Documents, the three outcome columns), it is compared as components: each piece's value must appear somewhere
in the cell. That check cannot see the pieces' order or which item a piece belongs to, so a swap between two
sites or two outcomes inside one cell would agree.

| Column Name | Included data fields (pieces) |
| --- | --- |
| NCT Number | NCTId |
| Study Title | BriefTitle |
| Study URL | NCTId |
| Acronym | Acronym |
| Study Status | OverallStatus |
| Brief Summary | BriefSummary |
| Study Results | HasResults |
| Conditions | Condition |
| Interventions | InterventionType, InterventionName |
| Primary Outcome Measures | PrimaryOutcomeMeasure, PrimaryOutcomeDescription, PrimaryOutcomeTimeFrame |
| Secondary Outcome Measures | SecondaryOutcomeMeasure, SecondaryOutcomeDescription, SecondaryOutcomeTimeFrame |
| Other Outcome Measures | OtherOutcomeMeasure, OtherOutcomeDescription, OtherOutcomeTimeFrame |
| Sponsor | LeadSponsorName |
| Collaborators | CollaboratorName |
| Sex | Sex |
| Age | MinimumAge, MaximumAge, StdAge |
| Phases | Phase |
| Enrollment | EnrollmentCount |
| Funder Type | LeadSponsorClass |
| Study Type | StudyType |
| Study Design | Interventional: DesignAllocation, DesignInterventionModel, DesignMasking, DesignWhoMasked, DesignPrimaryPurpose; Observational: DesignObservationalModel, DesignTimePerspective |
| Other IDs | OrgStudyId, SecondaryId |
| Start Date | StartDate |
| Primary Completion Date | PrimaryCompletionDate |
| Completion Date | CompletionDate |
| First Posted | StudyFirstPostDate |
| Results First Posted | ResultsFirstPostDate |
| Last Update Posted | LastUpdatePostDate |
| Locations | LocationFacility, LocationCity, LocationState, LocationZip, LocationCountry |
| Study Documents | NCTId, LargeDocLabel, LargeDocFilename |

"Markup fields are encoded in markdown format."
