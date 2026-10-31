"""Synthetic study records in the registry's real shapes (spec/ctg-oas-v2.yaml), with made-up values.

`results_study()` has posted results in every results module; `ongoing_study()` has none and only a
registry-added reference. Each call returns a fresh dict.
"""

ELIGIBILITY = (
    "Inclusion Criteria:\n\n* Age 18 to 65\n* Stage II disease\n\n"
    "Exclusion Criteria:\n\n* Pregnancy\n* Prior therapy with \\>2 lines"
)


def results_study():
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT01234567",
                "orgStudyIdInfo": {"id": "ORG-1"},
                "briefTitle": "A Study of Testamab in Example Disease",
                "officialTitle": "A Randomized Study of Testamab Versus Placebo",
                "acronym": "TEST",
                "organization": {"fullName": "Example Pharma", "class": "INDUSTRY"},
            },
            "statusModule": {
                "statusVerifiedDate": "2020-06",
                "overallStatus": "COMPLETED",
                "startDateStruct": {"date": "2018-01-15", "type": "ACTUAL"},
                "primaryCompletionDateStruct": {"date": "2019-06-30", "type": "ACTUAL"},
                "completionDateStruct": {"date": "2019-12", "type": "ACTUAL"},
                "resultsFirstSubmitDate": "2020-05-01",
                "resultsFirstPostDateStruct": {"date": "2020-06-01", "type": "ACTUAL"},
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Example Pharma", "class": "INDUSTRY"},
                "collaborators": [{"name": "Example University", "class": "OTHER"}],
            },
            "oversightModule": {"oversightHasDmc": True, "isFdaRegulatedDrug": True},
            "descriptionModule": {"briefSummary": "=Testamab is compared with placebo."},
            "conditionsModule": {"conditions": ["Example Disease"], "keywords": ["example"]},
            "designModule": {
                "studyType": "INTERVENTIONAL",
                "phases": ["PHASE2"],
                "designInfo": {
                    "allocation": "RANDOMIZED",
                    "interventionModel": "PARALLEL",
                    "primaryPurpose": "TREATMENT",
                    "maskingInfo": {"masking": "DOUBLE", "whoMasked": ["PARTICIPANT", "INVESTIGATOR"]},
                },
                "enrollmentInfo": {"count": 120, "type": "ACTUAL"},
            },
            "armsInterventionsModule": {
                "armGroups": [
                    {
                        "label": "Testamab",
                        "type": "EXPERIMENTAL",
                        "description": "Testamab 10 mg/kg every 3 weeks",
                        "interventionNames": ["Drug: Testamab"],
                    },
                    {
                        "label": "Placebo",
                        "type": "PLACEBO_COMPARATOR",
                        "interventionNames": ["Drug: Placebo"],
                    },
                ],
                "interventions": [
                    {
                        "type": "DRUG",
                        "name": "Testamab",
                        "description": "Intravenous infusion",
                        "armGroupLabels": ["Testamab"],
                        "otherNames": ["TM-1"],
                    },
                    {"type": "DRUG", "name": "Placebo", "armGroupLabels": ["Placebo"]},
                ],
            },
            "outcomesModule": {
                "primaryOutcomes": [
                    {
                        "measure": "Objective response rate",
                        "description": "Per RECIST 1.1",
                        "timeFrame": "Week 24",
                    }
                ],
                "secondaryOutcomes": [{"measure": "Progression-free survival", "timeFrame": "Up to 2 years"}],
                "otherOutcomes": [{"measure": "Biomarker X level", "timeFrame": "Baseline, Week 12"}],
            },
            "eligibilityModule": {
                "eligibilityCriteria": ELIGIBILITY,
                "healthyVolunteers": False,
                "sex": "ALL",
                "minimumAge": "18 Years",
                "maximumAge": "65 Years",
                "stdAges": ["ADULT"],
            },
            "contactsLocationsModule": {
                "overallOfficials": [{"name": "A. Investigator", "role": "PRINCIPAL_INVESTIGATOR"}],
                "locations": [
                    {
                        "facility": "Site One",
                        "status": "COMPLETED",
                        "city": "Boston",
                        "country": "United States",
                    },
                    {"facility": "Site Two", "city": "Paris", "country": "France"},
                ],
            },
            "referencesModule": {
                "references": [
                    {
                        "pmid": "31589554",
                        "type": "RESULT",
                        "citation": "Author A. Results paper. J Ex. 2020.",
                    },
                    {
                        "pmid": "27105315",
                        "type": "DERIVED",
                        "citation": "Author B. Indexed paper. J Ex. 2021.",
                    },
                    {"type": "BACKGROUND", "citation": "Author C. Background. J Ex. 2015."},
                ]
            },
            "ipdSharingStatementModule": {"ipdSharing": "NO"},
        },
        "resultsSection": {
            "participantFlowModule": {
                "groups": [{"id": "FG000", "title": "Testamab"}, {"id": "FG001", "title": "Placebo"}],
                "periods": [
                    {
                        "title": "Overall Study",
                        "milestones": [
                            {
                                "type": "STARTED",
                                "achievements": [
                                    {"groupId": "FG000", "numSubjects": "60"},
                                    {"groupId": "FG001", "numSubjects": "60"},
                                ],
                            },
                            {
                                "type": "COMPLETED",
                                "achievements": [
                                    {"groupId": "FG000", "numSubjects": "55"},
                                    {"groupId": "FG001", "numSubjects": "57"},
                                ],
                            },
                            {
                                "type": "NOT COMPLETED",
                                "achievements": [
                                    {"groupId": "FG000", "numSubjects": "5"},
                                    {"groupId": "FG001", "numSubjects": "3"},
                                ],
                            },
                        ],
                        "dropWithdraws": [
                            {
                                "type": "Adverse Event",
                                "reasons": [
                                    {"groupId": "FG000", "numSubjects": "3"},
                                    {"groupId": "FG001", "numSubjects": "1"},
                                ],
                            },
                            {
                                "type": "Withdrawal by Subject",
                                "reasons": [
                                    {"groupId": "FG000", "numSubjects": "2"},
                                    {"groupId": "FG001", "numSubjects": "2"},
                                ],
                            },
                        ],
                    }
                ],
            },
            "baselineCharacteristicsModule": {
                "groups": [{"id": "BG000", "title": "Testamab"}, {"id": "BG001", "title": "Placebo"}],
                "denoms": [
                    {"units": "Participants", "counts": [{"groupId": "BG000", "value": "60"}]},
                ],
                "measures": [
                    {
                        "title": "Age, Continuous",
                        "paramType": "MEAN",
                        "dispersionType": "STANDARD_DEVIATION",
                        "unitOfMeasure": "years",
                        "classes": [
                            {
                                "categories": [
                                    {"measurements": [{"groupId": "BG000", "value": "54.1", "spread": "9.2"}]}
                                ]
                            }
                        ],
                    }
                ],
            },
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {
                        "type": "PRIMARY",
                        "title": "Objective response rate",
                        "timeFrame": "Week 24",
                        "paramType": "COUNT_OF_PARTICIPANTS",
                        "unitOfMeasure": "Participants",
                        "reportingStatus": "POSTED",
                        "groups": [{"id": "OG000", "title": "Testamab"}, {"id": "OG001", "title": "Placebo"}],
                        "denoms": [
                            {
                                "units": "Participants",
                                "counts": [
                                    {"groupId": "OG000", "value": "60"},
                                    {"groupId": "OG001", "value": "60"},
                                ],
                            }
                        ],
                        "classes": [
                            {
                                "categories": [
                                    {
                                        "measurements": [
                                            {"groupId": "OG000", "value": "21"},
                                            {"groupId": "OG001", "value": "6"},
                                        ]
                                    }
                                ]
                            }
                        ],
                        "analyses": [
                            {
                                "groupIds": ["OG000", "OG001"],
                                "pValue": "<0.001",
                                "statisticalMethod": "Fisher Exact",
                                "paramType": "Risk Ratio (RR)",
                                "paramValue": "3.5",
                                "ciPctValue": "95",
                                "ciNumSides": "TWO_SIDED",
                                "ciLowerLimit": "1.5",
                                "ciUpperLimit": "8.1",
                            }
                        ],
                    }
                ]
            },
            "adverseEventsModule": {
                "frequencyThreshold": "5",
                "timeFrame": "Up to 30 days after last dose",
                "eventGroups": [
                    {
                        "id": "EG000",
                        "title": "Testamab",
                        "deathsNumAffected": 1,
                        "deathsNumAtRisk": 60,
                        "seriousNumAffected": 6,
                        "seriousNumAtRisk": 60,
                        "otherNumAffected": 30,
                        "otherNumAtRisk": 60,
                    },
                    {
                        "id": "EG001",
                        "title": "Placebo",
                        "deathsNumAffected": 0,
                        "deathsNumAtRisk": 60,
                        "seriousNumAffected": 2,
                        "seriousNumAtRisk": 60,
                        "otherNumAffected": 20,
                        "otherNumAtRisk": 60,
                    },
                ],
                "seriousEvents": [
                    {
                        "term": "Pneumonitis",
                        "organSystem": "Respiratory, thoracic and mediastinal disorders",
                        "sourceVocabulary": "MedDRA 21.0",
                        "assessmentType": "SYSTEMATIC_ASSESSMENT",
                        "stats": [
                            {"groupId": "EG000", "numEvents": 4, "numAffected": 3, "numAtRisk": 60},
                            {"groupId": "EG001", "numAffected": 0, "numAtRisk": 60},
                        ],
                    }
                ],
                "otherEvents": [
                    {
                        "term": "Fatigue",
                        "organSystem": "General disorders",
                        "stats": [
                            {"groupId": "EG000", "numEvents": 25, "numAffected": 18, "numAtRisk": 60},
                            {"groupId": "EG001", "numEvents": 12, "numAffected": 10},
                        ],
                    }
                ],
            },
            "moreInfoModule": {
                "pointOfContact": {"title": "Medical Director", "organization": "Example Pharma"}
            },
        },
        "documentSection": {
            "largeDocumentModule": {
                "largeDocs": [
                    {
                        "typeAbbrev": "Prot_SAP",
                        "hasProtocol": True,
                        "hasSap": True,
                        "hasIcf": False,
                        "label": "Study Protocol and Statistical Analysis Plan",
                        "date": "2019-01-07",
                        "uploadDate": "2020-05-01T09:08",
                        "filename": "Prot_SAP_000.pdf",
                        "size": 3510125,
                    }
                ]
            }
        },
        "derivedSection": {
            "miscInfoModule": {"versionHolder": "2026-10-30"},
            "conditionBrowseModule": {
                "meshes": [{"id": "D000001", "term": "Example Disease"}],
                "ancestors": [{"id": "D000002", "term": "Example Disease Class"}],
            },
            "interventionBrowseModule": {"meshes": [{"id": "D000003", "term": "Testamab"}]},
        },
        "hasResults": True,
    }


def ongoing_study():
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT07654321", "briefTitle": "An Observational Registry"},
            "statusModule": {
                "overallStatus": "RECRUITING",
                "startDateStruct": {"date": "2025-03", "type": "ACTUAL"},
                "primaryCompletionDateStruct": {"date": "2027-12", "type": "ESTIMATED"},
                "completionDateStruct": {"date": "2028-06", "type": "ESTIMATED"},
            },
            "conditionsModule": {"conditions": ["Example Disease"]},
            "designModule": {
                "studyType": "OBSERVATIONAL",
                "designInfo": {"observationalModel": "COHORT", "timePerspective": "PROSPECTIVE"},
                "enrollmentInfo": {"count": 500, "type": "ESTIMATED"},
            },
            "eligibilityModule": {
                "eligibilityCriteria": "Adults with example disease seen at the clinic.",
                "sex": "ALL",
                "minimumAge": "18 Years",
                "studyPopulation": "Clinic patients",
                "samplingMethod": "NON_PROBABILITY_SAMPLE",
            },
            "referencesModule": {
                "references": [
                    {"pmid": "35273311", "type": "DERIVED", "citation": "Author D. Protocol. 2025."}
                ]
            },
        },
        "derivedSection": {
            "miscInfoModule": {
                "versionHolder": "2026-10-30",
                "submissionTracking": {"estimatedResultsFirstSubmitDate": "2026-09-01"},
            }
        },
        "hasResults": False,
    }


def leaves(value, path=()):
    """Every leaf of a JSON value with its path, in document order (an empty object or list is a leaf): an
    independent walk the tests hold the ledger's entries and the Record sheet to."""
    if isinstance(value, dict) and value:
        out = []
        for key, item in value.items():
            out.extend(leaves(item, (*path, key)))
        return out
    if isinstance(value, list) and value:
        out = []
        for index, item in enumerate(value):
            out.extend(leaves(item, (*path, index)))
        return out
    return [(path, value)]
