## ADDED Requirements

### Requirement: Test fixture infrastructure
The system SHALL maintain a `tests/fixtures/` directory containing sample DOCX files that cover common document patterns. Each fixture SHALL have a corresponding expected output file (JSON) defining the anticipated `SemanticDocument` structure. Fixtures SHALL include: a simple document (title + headings + text), an academic document (with abstract and references), a document with tables, and a document with rich inline formatting.

#### Scenario: Simple document fixture
- **WHEN** the simple document fixture is processed through the full pipeline
- **THEN** the output SHALL match the expected `SemanticDocument` with 1 title block, N heading blocks, and M text blocks

#### Scenario: Academic document fixture
- **WHEN** the academic document fixture is processed
- **THEN** the output SHALL include recognized `abstract` and `reference` blocks with correct content

### Requirement: Per-stage test validation
The system SHALL provide test utilities that validate each pipeline stage independently. Tests SHALL be able to assert the `IntermediateResult` from parsing and the `SemanticDocument` from recognition separately. Each stage test SHALL accept a fixture DOCX file and an expected output file.

#### Scenario: Test parsing stage only
- **WHEN** a test runs only the parsing stage against a fixture
- **THEN** it SHALL assert the `IntermediateResult` block count, types, and attachment count match expectations

#### Scenario: Test recognition stage only
- **WHEN** a test runs only the recognition stage against a pre-built `IntermediateResult` fixture
- **THEN** it SHALL assert the `SemanticDocument` block classifications are correct

### Requirement: Parameterized parser tests
The test suite SHALL run parsing tests against all registered parsers (where available). Tests SHALL be skipped gracefully if a parser's external dependency (e.g., pandoc) is not installed, rather than failing.

#### Scenario: Skip pandoc tests when unavailable
- **WHEN** pandoc is not on the system PATH
- **THEN** tests requiring `PandocParser` SHALL be skipped with a clear skip reason

#### Scenario: Run python-docx tests always
- **WHEN** tests are executed
- **THEN** tests using `PythonDocxParser` SHALL always run since it has no external dependencies

### Requirement: Snapshot testing for intermediate results
The system SHALL use snapshot testing to capture and verify intermediate pipeline outputs. Snapshots SHALL cover: the markdown output from parsing, the block-level classifications from recognition, and the final serialized `SemanticDocument` JSON. Snapshot updates SHALL be performed via a pytest flag (`--snapshot-update`).

#### Scenario: Markdown output snapshot
- **WHEN** the parsing stage output is compared against its snapshot
- **THEN** the markdown text structure SHALL match the stored snapshot (within whitespace tolerance)

#### Scenario: Update snapshots
- **WHEN** a developer runs `pytest --snapshot-update`
- **THEN** failing snapshot assertions SHALL be overwritten with current output

### Requirement: Full pipeline integration tests
The system SHALL include end-to-end tests that run a complete DOCX → `SemanticDocument` pipeline with all components wired together. Integration tests SHALL verify: correct block ordering, inline element extraction, attachment references, and JSON serialization round-trip.

#### Scenario: Full pipeline round-trip
- **WHEN** a DOCX fixture goes through the full pipeline and is serialized to JSON, then deserialized
- **THEN** the round-tripped `SemanticDocument` SHALL be equal to the original

#### Scenario: Inline element extraction validation
- **WHEN** a fixture with bold, italic, and code spans is processed
- **THEN** the final `SemanticDocument` blocks SHALL contain the correct inline elements with accurate offsets

### Requirement: Test configuration and fixtures management
The test suite SHALL provide a `conftest.py` with shared fixtures: sample DOCX paths, expected output loaders, parser instances, and pipeline builders. Test fixtures SHALL be loaded via helper functions that handle path resolution relative to the test directory.

#### Scenario: Fixture path resolution
- **WHEN** a test requests fixture `"simple_document.docx"`
- **THEN** the fixture loader SHALL resolve the path relative to `tests/fixtures/`

#### Scenario: Expected output loading
- **WHEN** a test loads expected output for `"simple_document"`
- **THEN** it SHALL return a `SemanticDocument` instance parsed from the corresponding JSON fixture
