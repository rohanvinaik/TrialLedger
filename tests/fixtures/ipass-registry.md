# IPASS development fixture

`ipass-registry.json` is the complete, unchanged response body fetched on 2026-11-03 from
https://clinicaltrials.gov/api/v2/studies/NCT00322452.

SHA-256: `dc5b4cb1f416420d38c93c444f5a7b5f93d35d1676dc9c1cfa0379a58fe53354`.

It is a retained development example, not independent validation of a rule authored against it. The tests
bind exact baseline addresses to WHO PS 2 and the BG002 total. No label matcher, cross-module group-title
join or WHO-to-ECOG mapping is used. A count's `NUMBER` representation and `Participants` unit are inspected
together; its interpretation is an explicit test premise. The baseline population description is not stated.

The participation-to-eligibility bridge and its zero/125/126 exception allowances are declared test premises,
not registry facts, independent consent or a recovered protocol. The source's smoking categories and abbreviated
eligibility text illustrate why blanket compliance is not established merely by observing enrollment.
