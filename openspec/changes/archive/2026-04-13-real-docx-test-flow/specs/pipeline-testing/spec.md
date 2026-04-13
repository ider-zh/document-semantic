## MODIFIED Requirements

### Requirement: Full pipeline integration tests
The system SHALL include end-to-end tests that run a complete DOCX → `SemanticDocument` pipeline with all components wired together. Integration tests SHALL verify: correct block ordering, inline element extraction, attachment references, and JSON serialization round-trip.

**Modified to add:** Integration tests SHALL additionally support real DOCX files from `tests/docx/` via the test routing system. When running against a real DOCX file, the test SHALL use the processor configuration and assertions defined in the test route for that file.

#### Scenario: Full pipeline round-trip
- **WHEN** a DOCX fixture goes through the full pipeline and is serialized to JSON, then deserialized
- **THEN** the round-tripped `SemanticDocument` SHALL be equal to the original

#### Scenario: Inline element extraction validation
- **WHEN** a fixture with bold, italic, and code spans is processed
- **THEN** the final `SemanticDocument` blocks SHALL contain the correct inline elements with accurate offsets

#### Scenario: Real DOCX file via test route
- **WHEN** a real DOCX file from `tests/docx/` is processed via its test route configuration
- **THEN** the pipeline SHALL execute with the configured parser and recognizer, and assertions SHALL validate against the expected output
