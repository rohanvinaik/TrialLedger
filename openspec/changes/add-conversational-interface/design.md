# Design — add-conversational-interface

## Context

Proposed 2026-11-01. The founder will supply the MCP and skill systems he means to use; this design fixes only
the contract that keeps the founding rule, and is completed against those systems.

## Decisions

1. **The shell contract.** The chatbot calls tools and presents their results; it never reads a trial's text to
   answer a question, never fills a value a tool did not return, never upgrades a value's status, and always
   shows a value's status and source. A question the tools cannot answer becomes a review-queue item with its
   closed options, never a free answer.
2. **Tools return warranted, typed results.** Every tool's output carries the values with their spans or
   fields, statuses, warrants and links, the abstentions and blocked claims with their causes, and the data
   timestamp and code commit of the reading; nothing a tool returns is prose a model wrote.
3. **The ten-point extract and extras** are one tool over a resolved study, its fields fixed by the review
   workbook's sheets and the coherence engine's coordinates; extras are added only as typed fields with their
   own provenance.
4. **Pending the founder's systems**: the transport (MCP server shape), skill format and deployment follow his
   existing systems.

## Risks / Trade-offs

- [A chatbot paraphrasing a value into something else] → the skills instruct verbatim presentation with status;
  the tools return display strings the chatbot is told to quote, not reword.
