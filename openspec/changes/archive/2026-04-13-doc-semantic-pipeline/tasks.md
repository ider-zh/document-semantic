## 1. Project Setup

- [x] 1.1 Configure `pyproject.toml` with dependencies: `pydantic`, `python-docx`, `loguru`, `pytest`, `pyyaml`
- [x] 1.2 Create package directory structure: `src/document_semantic/` with subpackages `parsers/`, `recognizers/`, `models/`, `pipeline/`, `observability/`
- [x] 1.3 Create `tests/` directory structure with `fixtures/` subdirectory and `conftest.py`
- [x] 1.4 Configure `loguru` logger in `src/document_semantic/observability/logger.py` with configurable level and sink

## 2. Semantic Data Models

- [x] 2.1 Define inline element models: `Bold`, `Italic`, `Strikethrough`, `Formula`, `CodeSpan`, `Link` with `type`, `text`, `start_offset`, `end_offset` fields
- [x] 2.2 Define block-level models: `TitleBlock`, `HeadingBlock` (1-6), `TextBlock`, `AbstractBlock`, `ReferenceBlock`, `ListItemBlock`, `TableBlock`, `CodeBlock` with discriminator `type` field
- [x] 2.3 Define `SemanticDocument` container with `schema_version`, `metadata`, `blocks`, `attachments` fields
- [x] 2.4 Implement JSON serialization with Pydantic, verify discriminator round-trips
- [x] 2.5 Implement `SchemaUpgrader` base class and registry for version migrations

## 3. Document Parsing

- [x] 3.1 Define `Parser` protocol/ABC with `parse(docx_path) -> IntermediateResult` method
- [x] 3.2 Define `IntermediateResult` model with `blocks`, `metadata`, `attachments` fields
- [x] 3.3 Implement `ParserRegistry` for name-to-parser resolution
- [x] 3.4 Implement `PythonDocxParser` extracting paragraphs, tables, and style hints
- [x] 3.5 Implement `PandocParser` invoking pandoc subprocess for DOCX-to-MD conversion
- [x] 3.6 Implement custom exceptions: `ParserNotFoundError`, `ParserDependencyError`
- [x] 3.7 Write parser configuration loader (config file + env variable support, default to python-docx)

## 4. Semantic Recognition

- [x] 4.1 Define `SemanticRecognizer` protocol/ABC with `recognize(intermediate) -> SemanticDocument` method
- [x] 4.2 Implement `RegexRecognizer` for block-level classification using markdown syntax and metadata
- [x] 4.3 Implement `RegexRecognizer` for inline-level element extraction (bold, italic, code, formula, link)
- [x] 4.4 Implement `RouterRecognizer` with configurable routing rules and default fallback
- [x] 4.5 Implement `LLMRecognizer` placeholder that raises `RecognizerNotConfiguredError` without a client
- [x] 4.6 Implement recognizer configuration and selection from config

## 5. Pipeline Orchestration

- [x] 5.1 Implement `Pipeline` class that wires parser → recognizer → output from configuration
- [x] 5.2 Implement `PipelineTrace` to record stage inputs, outputs, duration, and warnings
- [x] 5.3 Implement `get_trace()` method for post-execution inspection
- [x] 5.4 Implement configurable result verbosity: `summary`, `preview`, `full` output modes
- [x] 5.5 Implement warning system with `warning_code` strings and configurable suppression

## 6. Observability & Logging

- [x] 6.1 Add entry/exit logging to all pipeline stages with duration tracking
- [x] 6.2 Add warning emissions for: unrecognized blocks, missing attachments, unknown schema versions, parser fallback
- [x] 6.3 Add error logging with full context (file path, exception, stage name) and debug-level stack traces
- [x] 6.4 Implement non-fatal error continuation (skip failed block, continue processing)

## 7. Test Infrastructure

- [x] 7.1 Create sample DOCX fixtures: simple document, academic document, table document, rich inline formatting
- [x] 7.2 Create expected output JSON fixtures for each sample document
- [x] 7.3 Implement fixture loader utilities in `conftest.py` with path resolution
- [x] 7.4 Implement per-stage test validation utilities (test parsing only, test recognition only)
- [x] 7.5 Set up snapshot testing infrastructure with `--snapshot-update` support

## 8. Tests - Parsing

- [x] 8.1 Write tests for `PythonDocxParser` against all fixtures
- [x] 8.2 Write tests for `PandocParser` with skip decorator when pandoc unavailable
- [x] 8.3 Write tests for `ParserRegistry` lookup and error handling
- [x] 8.4 Write tests for parser configuration loading and default fallback

## 9. Tests - Recognition

- [x] 9.1 Write tests for `RegexRecognizer` block classification against fixtures
- [x] 9.2 Write tests for inline element extraction (bold, italic, code, formula, links)
- [x] 9.3 Write tests for `RouterRecognizer` routing rules and default fallback
- [x] 9.4 Write tests for `LLMRecognizer` not-configured error

## 10. Tests - Data Models & Pipeline

- [x] 10.1 Write tests for all block and inline model creation and serialization
- [x] 10.2 Write tests for `SchemaUpgrader` version migration
- [x] 10.3 Write full pipeline integration tests with round-trip serialization
- [x] 10.4 Write tests for `PipelineTrace` capture and inspection
- [x] 10.5 Write tests for observability: log output, warning codes, verbosity modes

## 11. Documentation

- [x] 11.1 Write `README.md` with project overview, installation, and quick start
- [x] 11.2 Write usage examples: config file format, pipeline invocation, trace inspection
- [x] 11.3 Document how to add a new parser and a new recognizer
