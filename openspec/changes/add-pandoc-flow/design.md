## Context

The document-semantic project has a pandoc parser (`PandocParser`) already implemented and registered in `ParserRegistry`. It converts DOCX files to markdown using the pandoc binary, producing an `IntermediateResult` with blocks and image attachments. However, pandoc is not currently tested as a standalone processor in the DOCX test flow — it only appears indirectly as a dependency of `markdownit`.

The test routing system (`tests/docx/test_routes.yaml`) drives parameterized tests (`test_docx_flow.py`) that run each processor combination against DOCX fixtures and compare output against expected YAML snapshots.

**Constraints:**
- Pandoc must be installed on the system for these tests to run
- The existing `skip_if_no_pandoc` flag already handles this gracefully in the test harness
- `PandocParser.parse()` returns markdown-based blocks (not semantic blocks), so the recognizer processes them the same way as other parsers

## Goals / Non-Goals

**Goals:**
- Add pandoc as a testable processor in the DOCX test routing flow
- Generate expected output fixtures for pandoc parser results
- Ensure tests run conditionally (skip if pandoc unavailable)
- Maintain parity with existing parser test patterns

**Non-Goals:**
- No changes to `PandocParser` implementation itself
- No changes to the pipeline or recognition logic
- No new pandoc configuration options or command-line arguments

## Decisions

### Decision 1: Use existing `skip_if_no_pandoc` flag
The test harness already supports `skip_if_no_pandoc: true` in processor config (used by `markdownit` entries). We reuse this mechanism rather than introducing a new flag. This keeps the change additive and consistent.

**Alternatives considered:**
- Create a new `skip_if_binary_missing` generic flag — more flexible but unnecessary complexity for this scope.

### Decision 2: Pandoc expected output uses `_pandoc` suffix naming convention
Expected output files follow the existing pattern: `test_<N>_pandoc.yaml`. This mirrors `test_<N>_python-docx.yaml` and `test_<N>_markdownit.yaml`, maintaining consistency.

### Decision 3: Recognizer choice — `regex` for all pandoc entries
The `regex` recognizer is the baseline recognizer used across all parser flows. Pandoc output is markdown text, which the regex recognizer can classify. We use `recognizer: regex` for pandoc entries, matching the pattern of other parsers.

**Alternatives considered:**
- Using `router` recognizer — adds complexity without clear benefit for initial pandoc flow integration.

## Risks / Trade-offs

- **[Risk]** Pandoc not installed in CI environment → **Mitigation:** `skip_if_no_pandoc: true` ensures tests are skipped gracefully, not failed.
- **[Risk]** Pandoc output format differs significantly from other parsers, causing assertion mismatches → **Mitigation:** Expected output fixtures are generated from actual pandoc output and reviewed manually before committing.
- **[Trade-off]** Pandoc produces markdown-based blocks (not structural blocks like `python-docx`), so semantic recognition quality may differ — this is acceptable as it tests the pandoc→regex pipeline specifically.
