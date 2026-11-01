# Proposal

## Why

The founder, 2026-11-01: he has MCP- and skill-based systems to let someone use TrialLedger with an LLM chatbot
rather than the terminal, for the metadata pull-out (the original ten-point list plus sensible extras) and for
clinical study design. The project's founding rule is that no model reads a trial; a chatbot front end must keep
it.

## What Changes

- TrialLedger's operations exposed as MCP tools (resolve a query; the ten-point extract and its extras for a
  study; the profile, mechanism signals, occupancy and near misses for a population; the review queue and its
  closed questions; design questions over a population), each returning warranted values with their sources,
  statuses (known, interpolated, proposed) and links.
- Skills that guide the chatbot through the founder's workflows (pull the metadata for a study or a population;
  answer a design question; resolve review items) by calling those tools.
- The chatbot is the shell, never the reader: it presents what the tools return, with each value's status and
  source; it routes anything unresolved to the review queue's closed questions; it never reads raw trial text to
  answer, never fills a value, never states a proposed or interpolated value as known.

## Capabilities

### New Capabilities

- `conversational-interface`: the MCP tools, the skills and the shell contract.

## Impact

A new package (the MCP server and the skills), built on the library's public functions; no change to any reading.
The design waits for the founder's existing MCP and skill systems, whose shape it will follow.
