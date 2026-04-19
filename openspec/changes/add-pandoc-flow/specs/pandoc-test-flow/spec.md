## ADDED Requirements

### Requirement: Pandoc processor entry in test routes
The test route configuration file (`tests/docx/test_routes.yaml`) SHALL include a processor entry for the pandoc parser on each test document. The entry SHALL specify `parser: pandoc` and `recognizer: regex`, and SHALL include `skip_if_no_pandoc: true` to gracefully skip when pandoc is not installed.

#### Scenario: Pandoc processor added for test_1.docx
- **WHEN** the test routes file is loaded for `test_1.docx`
- **THEN** a processor entry with `parser: pandoc` and `recognizer: regex` SHALL be present alongside existing `python-docx` and `markdownit` entries

#### Scenario: Pandoc processor skips when binary is unavailable
- **WHEN** pandoc is not installed on the system PATH
- **THEN** any test flow processor with `skip_if_no_pandoc: true` SHALL be skipped with a pytest skip marker instead of failing

### Requirement: Pandoc expected output fixtures
Each pandoc processor entry SHALL reference an expected output YAML file at `tests/docx/expected/test_<N>_pandoc.yaml`. The expected output file SHALL contain the semantic recognition results (block types, inline elements) produced by running the pandoc parser + regex recognizer against the corresponding DOCX fixture.

#### Scenario: Expected output file exists for pandoc
- **WHEN** a pandoc processor entry references `expected_output_path: expected/test_1_pandoc.yaml`
- **THEN** that file SHALL exist and contain valid expected output data for assertion comparison

#### Scenario: Assertion matches pandoc output
- **WHEN** `test_docx_flow.py` runs the pandoc processor against `test_1.docx`
- **THEN** the actual output SHALL be compared against `test_1_pandoc.yaml` using `assert_document_partial()` and all specified fields SHALL match

### Requirement: Pandoc flow appears in test output
When `pytest tests/test_docx_flow.py -v` is executed with pandoc installed, the test output SHALL include test cases for pandoc processor entries. Each test case SHALL be identified by the document name and processor parser name.

#### Scenario: Pandoc tests appear in verbose pytest output
- **WHEN** `pytest tests/test_docx_flow.py -v` is run with pandoc installed
- **THEN** the output SHALL include lines such as `test_docx_flow[test_1.docx-pandoc-regex] PASSED`

#### Scenario: Pandoc tests are skipped in output when pandoc is missing
- **WHEN** `pytest tests/test_docx_flow.py -v` is run without pandoc installed
- **THEN** the output SHALL include `SKIPPED` markers for pandoc processor entries with the reason "pandoc not installed"
