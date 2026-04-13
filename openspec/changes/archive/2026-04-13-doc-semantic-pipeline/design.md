## Context

This is a greenfield project. The codebase currently has only a `pyproject.toml` scaffold with no dependencies. We are building a document semantic processing pipeline from scratch, using Python with `uv` as the package manager.

The pipeline processes DOCX files through three main stages:
1. **Document Parsing** → Intermediate MD representation (with attachments like images)
2. **Semantic Recognition** → Typed semantic structures (block-level and inline-level)
3. **Semantic Data Output** → Versioned, structured data ready for downstream consumption

During development, engineers need full visibility into each stage's output to iterate quickly and debug issues.

## Goals / Non-Goals

**Goals:**
- Extensible pipeline architecture where parsers and recognizers are swappable via configuration
- Clear separation between block-level semantics (headings, paragraphs, lists, tables) and inline-level semantics (bold, italic, code, formulas)
- Every pipeline stage produces observable, inspectable intermediate results
- Test-driven development with sample DOCX fixtures and expected outputs at each stage
- Semantic data model versioning to support future schema evolution

**Non-Goals:**
- PDF or other document format support (out of scope for now, but architecture should not preclude it)
- LLM integration implementation (framework supports it, but initial implementation uses regex/rule-based recognizers)
- Production deployment infrastructure (pipeline is a library, not a service)
- Real-time processing or streaming (batch processing only for now)

## Decisions

### 1. Package Layout: `src/` Layout
- Use `src/document_semantic/` as the package root for clean separation between source code and project configuration
- Subpackages: `parsers/`, `recognizers/`, `models/`, `pipeline/`, `observability/`, `testing/`

**Alternatives considered:** Flat layout (`document_semantic/` at root). Rejected because `src/` layout prevents accidental import of uninstalled code and matches Python packaging best practices.

### 2. Data Models: Pydantic v2
- Use Pydantic v2 for all semantic data structures with `ConfigDict` for validation, serialization, and versioning support
- Block models use a discriminated union pattern (`Literal` type field as discriminator)
- Inline models are nested within block models

**Alternatives considered:** `dataclasses` + manual validation. Rejected due to boilerplate and lack of built-in serialization. Pydantic provides validation error messages useful for debugging.

### 3. Parser Abstraction: Strategy Pattern with Registry
- Define a `Parser` protocol/ABC with `parse(docx_path) -> IntermediateResult`
- Concrete implementations: `PandocParser`, `PythonDocxParser`
- A `ParserRegistry` maps string names to parser classes, resolved from config
- `IntermediateResult` contains: list of blocks, metadata, attachments (images as base64 or file refs)

### 4. Semantic Recognition: Chain of Responsibility with Routing
- Define a `SemanticRecognizer` protocol/ABC
- Recognizers can be chained; each processes blocks it understands
- A `RouterRecognizer` dispatches to sub-recognizers based on document type or block characteristics
- Concrete recognizers: `RegexRecognizer` (rule-based), `LLMRecognizer` (placeholder for future)
- Output: `SemanticDocument` with typed blocks and inline elements

### 5. Intermediate Representation: Markdown AST + Attachments
- The intermediate format between parsing and recognition is a simplified markdown AST
- Blocks: raw text with type hints from parser (if available), plus extracted images
- This format is human-readable, making debugging and observability straightforward

### 6. Observability: loguru + Structured Logging
- Use `loguru` throughout with configurable sinks
- Pipeline stages emit `logger.info()` for normal flow, `logger.warning()` for recoverable issues, `logger.error()` for failures
- A `PipelineTrace` object collects intermediate results at each stage, available for inspection
- Log level and verbosity controlled via environment variable or config file

### 7. Pipeline Orchestration: Composition over Framework
- The pipeline is a simple composition: `Parser → Recognizer → Output`
- No heavy framework machinery — just a `Pipeline` class that wires components together from config
- Each stage is independently testable

### 8. Testing: pytest + Snapshot Testing
- `pytest` as the test framework
- Sample DOCX files in `tests/fixtures/`
- Snapshot testing for intermediate MD output and final semantic data
- Parameterized tests for different parser/recognizer combinations

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| pandoc not installed on developer machine | Graceful degradation: skip pandoc tests, use python-docx as default; document setup in README |
| Regex-based recognition insufficient for complex documents | Design supports LLM recognizer swap; provide clear extension point for future |
| Pydantic v2 serialization overhead for large documents | Acceptable for MVP; profile and optimize if needed (e.g., orjson backend) |
| Intermediate MD format loses information from original DOCX | Document limitations; provide parser-specific extraction hooks for edge cases |
| Snapshot tests become brittle | Keep snapshots focused on structure, not exact whitespace; use tolerance where appropriate |

## Migration Plan

Not applicable — this is a new project with no existing data or deployments.

## Open Questions

1. **Attachment handling strategy**: Should images be embedded as base64 in the intermediate format, or stored as file references with a separate output directory? → *Decision: File references during processing, with an optional "bundle" step for export.*
2. **LLM recognizer contract**: What is the minimal prompt/response schema for an LLM-based recognizer? → *Decision: Deferred to a future change; placeholder interface defined.*
3. **Semantic data versioning granularity**: Should each document carry its schema version, or should we maintain a global migration log? → *Decision: Each `SemanticDocument` carries a `schema_version` field; migration utilities provided separately.*
