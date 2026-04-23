# Document Semantic Pipeline

A pluggable document semantic processing pipeline that converts DOCX files into structured, machine-readable semantic data.

## Overview

This pipeline processes DOCX documents through two primary workflows:

### Workflow 1: Semantic Recognition (original)

1. **Document Parsing** → Intermediate markdown representation (with attachments)
2. **Semantic Recognition** → Typed semantic structures (blocks + inline elements)
3. **Semantic Data Output** → Versioned JSON data for downstream consumption

### Workflow 2: Processor Output (new)

1. **Document Parsing** → Intermediate markdown representation
2. **Processor Processing** → Markdown output with XML placeholders, resource directory, JSON mapping file
3. **File Output** → Three output artifacts for manual inspection and downstream use

### Key Features

- **Pluggable parsers**: Swap between `python-docx`, `pandoc`, `markdownit`, and `mineru` backends
- **Swappable recognizers**: Regex-based (default) or LLM-based (future) analysis
- **Configurable routing**: Route document to different recognizers based on type
- **Processor output**: Markdown with XML placeholders, resource directory with images, JSON mapping file
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

### Semantic Recognition Workflow (original)

```python
from pathlib import Path
from document_semantic.pipelines.pipeline import Pipeline
from document_semantic.core.config import PipelineConfig

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

### Processor Output Workflow (new)

```python
from pathlib import Path
from document_semantic.pipelines.pipeline import Pipeline
from document_semantic.core.config import PipelineConfig
from document_semantic.services.parsers.registry import ParserRegistry

# Create pipeline with python-docx parser (recognizer optional)
config = PipelineConfig(parser="python-docx")
pipeline = Pipeline(parser=ParserRegistry.get("python-docx"))

# Process with processor output workflow
result = pipeline.run_with_processor(
    Path("my_document.docx"),
    output_dir=Path("output/"),
    config=ProcessorConfig(
        output_markdown=True,
        output_resources=True,
        output_json_mapping=True,
        use_xml_placeholders=True,
    ),
)

# Access output files
print(f"Markdown: {result.markdown_path}")
print(f"Resources: {result.resources_dir}")
print(f"JSON mapping: {result.resources_json_path}")
```

Or use the parser's `process()` method directly:

```python
from document_semantic.services.parsers.registry import ParserRegistry
from document_semantic.models.processor_output import ProcessorConfig

parser = ParserRegistry.get("python-docx")
result = parser.process(
    Path("my_document.docx"),
    output_dir=Path("output/"),
    config=ProcessorConfig(),
)
```

## Processor Output Format

The processor workflow produces three output artifacts:

### 1. Markdown File (`output.md`)

Markdown representation with XML placeholders for special elements:

```markdown
# Document Title

Some paragraph text with <formula id="1">E = mc^2</formula> inline.

<formula id="1"/>

<code id="1"/>

![Figure 1](resources/images/image_1.png)
```

### 2. Resource Directory (`resources/`)

Directory containing extracted images and attachments:

```
resources/
└── images/
    ├── image_1.png
    └── image_2.jpg
```

### 3. JSON Mapping File (`resources.json`)

Maps placeholder IDs to original content and file paths:

```json
{
  "version": "1.0",
  "resources": {
    "formula": {
      "1": { "type": "block", "content": "E = mc^2", "metadata": {} }
    },
    "code": {
      "1": { "type": "block", "content": "print('hello')", "metadata": {"language": "python"} }
    },
    "image": {
      "1": { "type": "block", "file": "resources/images/image_1.png", "metadata": {} }
    }
  },
  "metadata": {
    "source_path": "my_document.docx",
    "parser": "python-docx",
    "processed_at": "2025-04-14T10:30:00Z"
  }
}
```

## Configuration

Create a `doc_semantic.yaml` file:

```yaml
parser: python-docx          # or 'pandoc', 'markdownit', 'mineru'
recognizer: regex             # or 'llm', 'router' (deprecated, use post_processor)
verbosity: preview            # summary, preview, full
log_level: INFO               # DEBUG, INFO, WARNING, ERROR

# Processor output settings
output_markdown: true
output_resources: true
output_json_mapping: true
use_xml_placeholders: true

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

### MinerU Parser Configuration

The `mineru` parser uses the MinerU cloud API for advanced document extraction. It requires:

- **API Token**: Set via `MINERU_TOKEN` environment variable or config file
- **Cache Directory**: Set via `MINERU_CACHE_DIR` (default: `~/.cache/document-semantic/mineru/`)

#### Image Placeholder Substitution

By default, MinerU performs OCR on images, which may extract unwanted text content. To prevent this:

```yaml
# doc_semantic.yaml
parser: mineru
mineru_skip_image_ocr: true  # Replace images with placeholders before API processing
```

Or via environment variable:

```bash
export MINERU_SKIP_IMAGE_OCR=true
```

When enabled:
1. Original images are extracted to a temporary directory
2. Images in the DOCX are replaced with uniform gray placeholders (800x600)
3. Modified DOCX is uploaded to MinerU API (prevents OCR extraction)
4. After download, placeholders are replaced with original images
5. Cache stores both ZIPs: `result_placeholders.zip` (MinerU output) and `result_restored.zip` (final output)
6. Temporary files are automatically cleaned up

This allows you to inspect what MinerU processed vs. the final restored output.

## Adding a New Parser

1. Create a class that implements the `Parser` ABC:

```python
from document_semantic.services.parsers.protocol import Parser, IntermediateResult
from document_semantic.models.processor_output import ProcessorConfig, ProcessResult

class MyCustomParser(Parser):
    @property
    def name(self) -> str:
        return "my-custom"

    def parse(self, docx_path: Path) -> IntermediateResult:
        # Return IntermediateResult with blocks, metadata, attachments
        ...

    def process(self, docx_path: Path, output_dir: Path, config: ProcessorConfig = None) -> ProcessResult:
        # Return ProcessResult with markdown, resources, and JSON mapping paths
        # Can call parse() internally and use MarkdownGenerator
        ...
```

2. Register it:

```python
from document_semantic.services.parsers.registry import ParserRegistry
ParserRegistry.register("my-custom", MyCustomParser)
```

3. Use it via config: `parser: my-custom`

## Adding a New Recognizer

1. Create a class that implements the `SemanticRecognizer` ABC:

```python
from document_semantic.agents.protocol import SemanticRecognizer
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
from document_semantic.agents.router_and_llm import register_recognizer
register_recognizer("my-custom", MyCustomRecognizer)
```

3. Use it via config: `recognizer: my-custom`

## Running Tests

```bash
uv run pytest tests/ -v          # All tests
uv run pytest tests/ -k parser  # Parser tests only
uv run pytest tests/ --snapshot-update  # Update snapshots
```

Test output files are written to `tests/docx/output/` for manual inspection (gitignored).

## Architecture

```
src/document_semantic/
├── models/            # Pydantic data models (blocks, inline elements, SemanticDocument, ProcessorOutput)
├── parsers/           # Parser protocol, registry, implementations
├── recognizers/       # Recognizer protocol, regex/llm/router implementations
├── pipeline/          # Pipeline orchestration, configuration
├── utils/             # Utility modules (MarkdownGenerator, XML placeholders, resource mapping)
├── observability/     # loguru logger configuration
└── testing/           # Test utilities

tests/
├── fixtures/          # Expected output JSON fixtures
├── conftest.py        # Shared fixtures (DOCX generators, parsers, recognizers)
├── test_parsers.py    # Parser tests
├── test_recognizers.py  # Recognizer tests
├── test_models_and_pipeline.py  # Model, pipeline, and observability tests
└── docx/
    ├── output/        # Test output files (gitignored)
    └── test_routes.yaml  # Test route configuration
```
