# Staging Directory

This directory holds **staged file envelopes** — JSON files written by the
`StagingService` that await human approval before being written to their
final destinations.

## Workflow

1. An LLM generates a file payload.
2. The Inspection Pipeline validates the payload.
3. `StagingService.stage_file()` writes a JSON envelope here.
4. A Domain Authority or root user reviews the staged file.
5. On **approve** → the file is written to its final path via `write_from_template`.
6. On **reject** → the envelope is marked rejected and stays here for audit.

## File naming

Each envelope is named `{staged_id}.json` where `staged_id` is a UUID.

## Cleanup

Approved and rejected envelopes are kept for audit.  Periodic cleanup can
be done by archiving or removing resolved envelopes older than a
configured retention period.
