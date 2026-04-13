# Document Semantic Pipeline

A pluggable document semantic processing pipeline that converts DOCX files into structured, machine-readable semantic data.

## Overview

This pipeline processes DOCX documents through three stages:

1. **Document Parsing** → Intermediate markdown representation (with attachments)
2. **Semantic Recognition** → Typed semantic structures (blocks + inline elements)
3. **Semantic Data Output** → Versioned JSON data for downstream consumption

### Key Features

- **Pluggable parsers**: Swap between `python-docx` and `pandoc` backends
- **Swappable recognizers**: Regex-based (default) or LLM-based (future) analysis
- **Configurable routing**: Route documents to different recognizers based on type
- **Full observability**: Structured logging, pipeline traces, configurable verbosity
- **Test-driven**: Sample fixtures, snapshot testing, per-stage validation

## Installation

```bash
# Install with uv (recommended)
uv sync

# Install dev dependencies
uv sync --all-extras
```

### Requirements

- Python 3.13+
- `pandoc` (optional, for the pandoc parser backend)

## Quick Start

```python
from pathlib import Path
from document_semantic.pipeline import Pipeline, PipelineConfig

# Use defaults (python-docx parser + regex recognizer)
config = PipelineConfig.load()
pipeline = Pipeline.from_config(config)

# Process a document
result = pipeline.run(Path("my_document.docx"))

# Inspect results
pipeline.print_result(result)

# View pipeline trace
print(pipeline.get_trace().summary())
```

## Configuration

Create a `doc_semantic.yaml` file:

```yaml
parser: python-docx          # or 'pandoc'
recognizer: regex             # or 'llm', 'router'
verbosity: preview            # summary, preview, full
log_level: INFO               # DEBUG, INFO, WARNING, ERROR

# Recognizer-specific config
recognizer_config: {}

# Suppress specific warnings
suppress_warnings:
  - UNRECOGNIZED_BLOCK
```

Or use environment variables:

```bash
export DOC_SEMANTIC_PARSER=pandoc
export DOC_SEMANTIC_RECOGNIZER=regex
export DOC_SEMANTIC_VERBOSITY=full
export DOC_SEMANTIC_LOG_LEVEL=DEBUG
```

## Adding a New Parser

1. Create a class that implements the `Parser` ABC:

```python
from document_semantic.parsers.protocol import Parser, IntermediateResult

class MyCustomParser(Parser):
    @property
    def name(self) -> str:
        return "my-custom"

    def parse(self, docx_path: Path) -> IntermediateResult:
        # Return IntermediateResult with blocks, metadata, attachments
        ...
```

2. Register it:

```python
from document_semantic.parsers.registry import ParserRegistry
ParserRegistry.register("my-custom", MyCustomParser)
```

3. Use it via config: `parser: my-custom`

## Adding a New Recognizer

1. Create a class that implements the `SemanticRecognizer` ABC:

```python
from document_semantic.recognizers.protocol import SemanticRecognizer
from document_semantic.models.semantic_document import SemanticDocument

class MyCustomRecognizer(SemanticRecognizer):
    @property
    def name(self) -> str:
        return "my-custom"

    def recognize(self, intermediate) -> SemanticDocument:
        # Return a SemanticDocument with typed blocks
        ...
```

2. Register it:

```python
from document_semantic.recognizers.router_and_llm import register_recognizer
register_recognizer("my-custom", MyCustomRecognizer)
```

3. Use it via config: `recognizer: my-custom`

## Running Tests

```bash
uv run pytest tests/ -v          # All tests
uv run pytest tests/ -v -k parser  # Parser tests only
uv run pytest tests/ --snapshot-update  # Update snapshots
```

## Architecture

```
src/document_semantic/
├── models/            # Pydantic data models (blocks, inline elements, SemanticDocument)
├── parsers/           # Parser protocol, registry, implementations
├── recognizers/       # Recognizer protocol, regex/llm/router implementations
├── pipeline/          # Pipeline orchestration, configuration
├── observability/     # loguru logger configuration
└── testing/           # Test utilities

tests/
├── fixtures/          # Expected output JSON fixtures
├── conftest.py        # Shared fixtures (DOCX generators, parsers, recognizers)
├── test_parsers.py    # Parser tests
├── test_recognizers.py  # Recognizer tests
└── test_models_and_pipeline.py  # Model, pipeline, and observability tests
```
