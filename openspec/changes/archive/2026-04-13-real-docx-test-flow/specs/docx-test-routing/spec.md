## ADDED Requirements

### Requirement: Test route configuration file
The system SHALL load test route definitions from a YAML file at `tests/docx/test_routes.yaml`. Each entry in the file SHALL map a DOCX filename (or glob pattern) to a test flow configuration containing: a list of processor configurations, and optional semantic tool selections.

#### Scenario: Load route for a single DOCX file
- **WHEN** the route configuration file contains an entry for `test_1.docx`
- **THEN** the system SHALL return the associated test flow configuration when queried for that file

#### Scenario: Glob pattern matches multiple files
- **WHEN** the route configuration contains a glob pattern `test_*.docx`
- **THEN** the route SHALL apply to all DOCX files in `tests/docx/` matching the pattern

### Requirement: Processor configuration per test flow
Each test flow SHALL specify one or more processor configurations. A processor configuration SHALL include: a parser name (registered in `ParserRegistry`), and a recognizer name or router configuration. The system SHALL instantiate the specified parser and recognizer for each processor in the flow.

#### Scenario: Single processor configuration
- **WHEN** a test flow specifies one processor with `parser: python-docx` and `recognizer: regex`
- **THEN** the system SHALL create a pipeline with `PythonDocxParser` and `RegexRecognizer`

#### Scenario: Multiple processors in one flow
- **WHEN** a test flow specifies two processors: `parser: python-docx, recognizer: regex` and `parser: pandoc, recognizer: regex`
- **THEN** the system SHALL run both processor combinations sequentially and collect both outputs

### Requirement: Route resolution and validation
The system SHALL validate that all parser and recognizer names referenced in route configurations are registered in their respective registries. Invalid references SHALL produce a clear error message listing available options. Routes SHALL be resolved in order: exact filename match takes precedence over glob patterns.

#### Scenario: Exact match takes precedence over glob
- **WHEN** both an exact entry `test_1.docx` and a glob `test_*.docx` exist
- **THEN** the exact entry SHALL be used for `test_1.docx`

#### Scenario: Unknown parser name error
- **WHEN** a route specifies a parser not in `ParserRegistry`
- **THEN** the system SHALL raise an error listing the unknown name and available parsers

### Requirement: Semantic tool selection per processor output
A test flow MAY specify semantic tools to run against each processor's output. Semantic tools SHALL be identified by name and mapped to recognizer instances or future semantic analysis tools. The system SHALL run each configured tool against the processor output and collect results.

#### Scenario: Run router recognizer as semantic tool
- **WHEN** a processor output is passed to a semantic tool configured as `recognizer: router` with sub-recognizers
- **THEN** the system SHALL dispatch to the appropriate sub-recognizer based on routing rules and return the result

#### Scenario: No semantic tools specified
- **WHEN** a test flow has no semantic tools configured for a processor
- **THEN** the system SHALL only run the primary processor (parser + recognizer) without additional semantic analysis
