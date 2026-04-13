## ADDED Requirements

### Requirement: Real DOCX test file management
The system SHALL use `tests/docx/` as the directory for real DOCX test files. Any `.docx` file placed in this directory SHALL be discoverable by the test framework. The directory SHALL also contain the test route configuration file and expected output subdirectory.

#### Scenario: Discover DOCX files in tests/docx/
- **WHEN** the test framework scans `tests/docx/` for test files
- **THEN** it SHALL return all `.docx` files found, including `test_1.docx` and any newly added files

#### Scenario: Add new test file
- **WHEN** a developer places `new_document.docx` in `tests/docx/` and adds a route entry
- **THEN** the next test run SHALL include the new document in the parameterized test matrix

### Requirement: Parameterized pytest test execution
The system SHALL provide a pytest test function parameterized over all defined test routes. Each parameterization SHALL include: the DOCX file path, the processor configuration, and the expected output path. Test execution SHALL run each processor in the flow sequentially and collect results.

#### Scenario: Run all defined test routes
- **WHEN** `pytest tests/test_docx_flow.py` is executed
- **THEN** pytest SHALL run one test instance per (docx_file, processor) pair defined in the route configuration

#### Scenario: Test failure reports processor and file
- **WHEN** a test instance fails for `test_1.docx` with `parser: python-docx`
- **THEN** the pytest output SHALL clearly identify the file and processor that failed

### Requirement: Test result collection and reporting
Each test flow execution SHALL collect results for every processor in the flow. Results SHALL include: the `SemanticDocument` output, pipeline trace information, assertion results (pass/fail per assertion), and any warnings. Results SHALL be available for downstream analysis or reporting.

#### Scenario: Collect processor results
- **WHEN** a test flow runs 2 processors on `test_1.docx`
- **THEN** the test result SHALL include 2 result entries, each with output, trace, and assertion status

#### Scenario: Report assertion failures with diff
- **WHEN** an assertion fails comparing expected vs actual block content
- **THEN** the test output SHALL show the expected value, actual value, and their difference

### Requirement: Makefile convenience targets
The Makefile SHALL provide targets for running the real DOCX test flow. The `test-docx` target SHALL run `pytest tests/test_docx_flow.py`. The `test-docx-single` target SHALL accept a `FILE` variable to run tests for a specific DOCX file only.

#### Scenario: Run all DOCX tests
- **WHEN** `make test-docx` is executed
- **THEN** all parameterized DOCX test routes SHALL be executed via pytest

#### Scenario: Run single DOCX test
- **WHEN** `make test-docx-single FILE=test_1.docx` is executed
- **THEN** only the test route for `test_1.docx` SHALL be executed
