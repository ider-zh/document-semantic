## Why

The pandoc parser exists in the codebase but is not integrated into the test routing flow. Currently, `test_docx_flow.py` tests `python-docx`, `markdownit`, and `mineru` parsers, but pandoc is only used indirectly as a dependency of `markdownit`. Adding pandoc as a first-class flow enables:

1. Direct testing of the pandoc parser's intermediate result (blocks + attachments)
2. Validation of pandoc's output quality against expected semantics
3. Coverage parity with other parsers in the test suite

## What Changes

- Add pandoc as a processor entry in `tests/docx/test_routes.yaml` for each test document
- Create expected output YAML files for pandoc results (`expected/test_*_pandoc.yaml`)
- Update the test flow to include pandoc in `pytest tests/test_docx_flow.py -v`
- Add a skip flag (`skip_if_no_pandoc`) for environments without pandoc installed

## Capabilities

### New Capabilities
- `pandoc-test-flow`: Pandoc parser integration in the DOCX test routing suite, including route configuration and expected output fixtures

### Modified Capabilities
- `docx-test-routing`: Extended to support pandoc as a processor option in existing test routes (no breaking changes; pandoc entries are additive)

## Impact

- **Tests**: `tests/docx/test_routes.yaml` gains pandoc processor entries per document
- **Fixtures**: New expected output YAML files under `tests/docx/expected/`
- **Dependencies**: Requires pandoc binary installed for test execution (already a dependency for `markdownit` parser)
- **No API changes**: Existing parser, pipeline, and test infrastructure remains unchanged
