## ADDED Requirements

### Requirement: Structured logging with loguru
The system SHALL use `loguru` as its logging framework throughout all pipeline stages. Each pipeline stage (parsing, recognition, output) SHALL log an `info`-level message upon entry and exit, including the stage name and processing duration. The default log level SHALL be `INFO` and SHALL be configurable via environment variable `DOC_SEMANTIC_LOG_LEVEL` or configuration file.

#### Scenario: Stage entry and exit logs
- **WHEN** the parsing stage begins and completes
- **THEN** log output SHALL contain messages like `[parsing] stage started` and `[parsing] stage completed (0.5s)`

#### Scenario: Log level configuration
- **WHEN** environment variable `DOC_SEMANTIC_LOG_LEVEL=DEBUG` is set
- **THEN** debug-level messages SHALL be emitted including block-by-block processing details

### Requirement: Warning system for recoverable issues
The system SHALL emit `warning`-level log messages for recoverable conditions including: unrecognized block types, missing attachments, unrecognized schema versions, parser fallback events, and recognizer rule misses. Each warning SHALL include a `warning_code` string for programmatic filtering.

#### Scenario: Unrecognized block type warning
- **WHEN** the recognizer encounters a block it cannot classify
- **THEN** it SHALL log a warning with `warning_code: "UNRECOGNIZED_BLOCK"` and include the block content preview

#### Scenario: Suppress specific warnings
- **WHEN** the configuration sets `suppress_warnings: ["UNRECOGNIZED_BLOCK"]`
- **THEN** warnings with that code SHALL NOT be emitted

### Requirement: Pipeline trace for intermediate inspection
The system SHALL maintain a `PipelineTrace` object that records the input and output of each pipeline stage. The trace SHALL be accessible after pipeline execution for debugging. Each trace entry SHALL include: stage name, input summary, output summary, duration, and any warnings or errors.

#### Scenario: Trace captures parsing output
- **WHEN** the pipeline completes the parsing stage
- **THEN** the trace SHALL include the number of blocks produced, number of attachments, and stage duration

#### Scenario: Trace inspection after pipeline run
- **WHEN** a developer calls `pipeline.get_trace()` after execution
- **THEN** it SHALL return a list of trace entries for all completed stages

### Requirement: Configurable output verbosity for results
The system SHALL support configurable verbosity levels for printed intermediate results: `summary` (block counts and types only), `preview` (first 100 chars of each block), and `full` (complete content). The verbosity SHALL be controlled via configuration.

#### Scenario: Summary verbosity
- **WHEN** verbosity is set to `summary`
- **THEN** printed results SHALL show only block type counts (e.g., `heading1: 3, text: 12, reference: 5`)

#### Scenario: Preview verbosity
- **WHEN** verbosity is set to `preview`
- **THEN** printed results SHALL show block type and first 100 characters of content for each block

### Requirement: Error logging with context
The system SHALL log errors with full context including the stage name, input file path, exception type and message, and a stack trace (at DEBUG level). Fatal errors SHALL raise exceptions; non-fatal errors SHALL be logged and the pipeline SHALL continue with best-effort behavior.

#### Scenario: Parsing error with context
- **WHEN** the parser fails to open a corrupted DOCX file
- **THEN** the error log SHALL include the file path, exception type, and message

#### Scenario: Non-fatal error continuation
- **WHEN** a single block fails to parse but the rest succeed
- **THEN** the pipeline SHALL log the error and continue processing remaining blocks
