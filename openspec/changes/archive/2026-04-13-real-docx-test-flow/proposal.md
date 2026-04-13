## Why

The current test suite only validates the pipeline against programmatically generated DOCX files with predictable structure. Real-world DOCX documents contain complex formatting, embedded objects, varied styling, and edge cases that synthetic fixtures cannot reproduce. We need a testing flow that runs the full pipeline against real DOCX files (like `tests/docx/test_1.docx`) with configurable routing, multiple processors, and semantic validation to ensure the pipeline handles production documents correctly.

## What Changes

- Add a test routing system that maps each DOCX file to a configurable test flow (processor selection, recognizer selection, semantic tools)
- Add expected output assertions that validate parser and recognizer outputs against user-defined expectations
- Add semantic recognition tool selection per test case, with output validation
- Extend `tests/docx/` as the home for real DOCX test files, each with an associated test route configuration
- Add parameterized pytest tests that iterate over DOCX files, execute their routing config, and assert results
- Update Makefile with convenience targets for running docx test flows

## Capabilities

### New Capabilities
- `docx-test-routing`: Per-document routing configuration that selects parsers, recognizers, and semantic tools for each test file
- `docx-test-assertions`: Expected output validation framework for parser and recognizer results against configurable expectations
- `docx-test-suite`: Real DOCX test file management and parameterized test execution

### Modified Capabilities
- `pipeline-testing`: Extend the existing testing capability to support real DOCX files and routing-based test flows (existing spec at `openspec/specs/pipeline-testing/spec.md`)

## Impact

- **New files**: `src/document_semantic/testing/routing.py`, `src/document_semantic/testing/assertions.py`, `tests/docx/test_routes.yaml`, `tests/docx/conftest.py`, `tests/test_docx_flow.py`
- **Modified files**: `tests/conftest.py` (add real-docx fixtures), `Makefile` (add test targets)
- **No breaking changes**: Existing test infrastructure and pipeline API remain unchanged
