## ADDED Requirements

### Requirement: Block-level assertions
The system SHALL provide assertion helpers that validate block-level properties of a `SemanticDocument`. Assertions SHALL include: block count equality, block type sequence verification, and block content substring matching. Each assertion SHALL produce a clear failure message showing expected vs actual values.

#### Scenario: Assert block count
- **WHEN** an assertion checks that a `SemanticDocument` has exactly 5 blocks
- **THEN** the assertion SHALL pass if the block count is 5 and fail with "expected 5 blocks, got N" otherwise

#### Scenario: Assert block type sequence
- **WHEN** an assertion verifies the block type sequence is `[title, heading1, text, heading2, text]`
- **THEN** the assertion SHALL pass if blocks match in order and fail listing the first mismatched position

#### Scenario: Assert block content contains substring
- **WHEN** an assertion checks that block at index 0 contains the text "Introduction"
- **THEN** the assertion SHALL pass if the block's content includes that substring and fail otherwise

### Requirement: Inline element assertions
The system SHALL provide assertion helpers that validate inline element properties within a block. Assertions SHALL include: inline element count per type at a block index, and inline element text content verification.

#### Scenario: Assert bold inline element count
- **WHEN** an assertion checks that block at index 2 has exactly 3 `bold` inline elements
- **THEN** the assertion SHALL pass if the count matches and fail with expected vs actual count

#### Scenario: Assert inline element text content
- **WHEN** an assertion verifies that the first bold inline element in block 2 has text "Key Term"
- **THEN** the assertion SHALL pass if the text matches exactly and fail otherwise

### Requirement: Expected output from YAML fixtures
The system SHALL load expected output definitions from YAML files. Each expected output file SHALL define the anticipated `SemanticDocument` structure using the same field names as `SemanticDocument.model_dump()`. Expected output files SHALL be stored in `tests/docx/expected/` with naming convention `<docx_name>_<processor_name>.yaml`.

#### Scenario: Load expected output for python-docx processor
- **WHEN** the test flow for `test_1.docx` with `parser: python-docx` loads its expected output
- **THEN** the system SHALL load `tests/docx/expected/test_1_python-docx.yaml` and parse it into a dict

#### Scenario: Missing expected output file is a warning, not error
- **WHEN** no expected output file exists for a processor
- **THEN** the system SHALL log a warning and skip assertions for that processor, allowing the test to pass

### Requirement: Partial assertion mode
The assertion framework SHALL support a "partial" mode where only specified fields are validated and unspecified fields are ignored. This allows tests to assert on important properties (block count, key content) without requiring exact structural equality.

#### Scenario: Partial assertion validates only specified blocks
- **WHEN** an expected output specifies only blocks 0 and 1 with their types and content
- **THEN** the assertion SHALL validate those blocks and ignore any additional blocks in the actual output

#### Scenario: Full assertion validates all blocks
- **WHEN** an expected output specifies all blocks
- **THEN** the assertion SHALL validate block count matches and all blocks match in type and content
