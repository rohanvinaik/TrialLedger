## ADDED Requirements

### Requirement: Retained source objects have bounded exact access
Record access SHALL expose complete retained NIH study objects through bounded pages or exact text chunks with snapshot identity and digest. It SHALL distinguish these source objects from the selected clinical projection and SHALL NOT alter the reference report.

#### Scenario: A long eligibility passage is read from its raw source
- **WHEN** the operator follows all returned continuation offsets
- **THEN** the concatenated passage equals the retained source text and keeps its study identity and digest
