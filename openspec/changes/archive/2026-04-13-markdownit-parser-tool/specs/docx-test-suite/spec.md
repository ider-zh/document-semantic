## MODIFIED Requirements

### Requirement: Parameterized pytest test execution
The system SHALL provide a pytest test function parameterized over all defined test routes. Each parameterization SHALL include: the DOCX file path, the processor configuration, and the expected output path. Test execution SHALL run each processor in the flow sequentially and collect results.

#### Scenario: Run all defined test routes
- **WHEN** `pytest tests/test_docx_flow.py` is executed
- **THEN** pytest SHALL run one test instance per (docx_file, processor) pair defined in the route configuration

#### Scenario: Test failure reports processor and file
- **WHEN** a test instance fails for `test_1.docx` with `parser: python-docx`
- **THEN** the pytest output SHALL clearly identify the file and processor that failed

#### Scenario: Test markdownit parser workflow
- **WHEN** a test route specifies `parser: markdownit` with `recognizer: regex`
- **THEN** the test SHALL run the `MarkdownitParser` pipeline and assert against expected output

### Requirement: Makefile convenience targets
The Makefile SHALL provide targets for running the real DOCX test flow. The `test-docx` target SHALL run `pytest tests/test_docx_flow.py`. The `test-docx-single` target SHALL accept a `FILE` variable to run tests for a specific DOCX file only.

#### Scenario: Run all DOCX tests
- **WHEN** `make test-docx` is executed
- **THEN** all parameterized DOCX test routes SHALL be executed via pytest

#### Scenario: Run single DOCX test
- **WHEN** `make test-docx-single FILE=test_1.docx` is executed
- **THEN** only the test route for `test_1.docx` SHALL be executed

#### Scenario: Run markdownit parser test only
- **WHEN** `make test-docx-single FILE=markdownit` is executed
- **THEN** only the test instances using the markdownit parser SHALL be executed