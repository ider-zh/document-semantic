## Why

The current semantic recognition module (regex/LLM) mixes two concerns: parsing output normalization and semantic classification. Parsers produce intermediate results that then require semantic recognition to become structured documents. This architecture creates unnecessary coupling and makes it difficult to add new parsers or change output formats. Additionally, the current pipeline only outputs JSON, but users need human-readable Markdown output with structured resource directories for manual quality inspection.

## What Changes

- **Remove the semantic recognition abstraction** (`recognizers/`) from the main pipeline output path. Semantic classification (regex/LLM) becomes optional, not mandatory.
- **Transform each parser's output into a dedicated processor** that handles parser-specific output normalization instead of a shared recognizer step.
- **Add Markdown export** as the primary output format, alongside existing JSON.
- **Introduce XML placeholder substitution** for formulas, code blocks, and images in the Markdown output, using ID-based references for lossless round-trip recovery.
- **Add a resource directory output** containing extracted images and a JSON mapping file linking placeholder IDs to original content and attachments.
- **Update `test_docx_flow`** to default to producing all three output artifacts (Markdown, resource directory, JSON mapping) for manual quality inspection.

## Capabilities

### New Capabilities

- `parser-processor`: Each parser gets a dedicated processor that converts its intermediate output into standardized Markdown with XML placeholders, a resource directory with images, and a JSON mapping file for ID-based content recovery.
- `markdown-output`: Pipeline produces human-readable Markdown as the primary output format, with configurable XML placeholder substitution for blocks (formulas, code, images) and inline elements (formulas, code spans).
- `resource-directory`: Output includes a directory containing extracted images and a JSON mapping file (`resources.json`) linking placeholder IDs to original content, file paths, and metadata.
- `flow-test-outputs`: Test flow (`test_docx_flow`) produces Markdown, resource directory, and JSON mapping files by default for manual quality inspection.

### Modified Capabilities

- `semantic-recognition`: The semantic recognition module is no longer part of the default pipeline. Recognizers become optional post-processors that can enrich processor output with semantic tags. The requirement for mandatory recognition is removed.

## Impact

- **`src/document_semantic/recognizers/`**: Moved from mandatory pipeline stage to optional enrichment step. `RegexRecognizer` and `LLMRecognizer` become post-processing tools.
- **`src/document_semantic/parsers/`**: Each parser gains a corresponding processor (e.g., `python_docx_processor.py`, `mineru_processor.py`) or the parser itself is extended to produce the new output format.
- **`src/document_semantic/pipeline/`**: Pipeline configuration changes to support processor-based output instead of recognizer-based output. New config options for Markdown export, XML placeholder substitution, and resource directory output.
- **`src/document_semantic/models/`**: May need new models for the JSON mapping file format (placeholder ID → content/resource).
- **`tests/test_docx_flow.py`**: Updated to produce three output files per processor: `.md`, `resources/` directory, and `resources.json`.
- **`tests/docx/expected/`**: Expected output fixtures may need updates to match new output format.
