---
name: document-semantic
description: Expertise in transforming raw documents into high-fidelity, academically formatted artifacts using an Agent-driven pipeline. This skill specializes in the lifecycle of structured document processing: from deep parsing and OCR correction to intelligent translation, semantic annotation, and professional rendering (DOCX/LaTeX).
---

# Skill: Document Semantic Processing & Layout Engine

Expertise in transforming raw documents into high-fidelity, academically formatted artifacts using an Agent-driven pipeline. This skill specializes in the lifecycle of structured document processing: from deep parsing and OCR correction to intelligent translation, semantic annotation, and professional rendering (DOCX/LaTeX).

## Core Capabilities

### 1. High-Fidelity Parsing & Alignment
- **MinerU Integration**: Extract structured content (JSON/Markdown) with rich metadata (equations, tables, images).
- **Docx Alignment**: Use raw DOCX text as ground truth to fix OCR errors, page-break splits, and word-wrap issues.
- **Resource Management**: Automatic extraction and synchronization of image and formula assets.

### 2. Intelligent Content Transformation
- **Semantic Chunking**: Split long documents by logical headers (H1, H2) with graceful degradation to paragraph-level chunks based on token limits.
- **Format Protection**: Safeguard non-translatable elements (LaTeX equations, tables, code) using unique XML-like placeholders (e.g., `<P:EQ_1/>`).
- **Workflow Orchestration**:
    - **Global Glossary**: Document-wide terminology extraction and per-chunk recall.
    - **Refinement**: Automated academic editing (citation formatting, spelling, flow) with structured auditing.
    - **Translation**: Multi-agent translation with LLM-based judging and placeholder integrity verification.

### 3. Semantic Template Engine
- **Annotation**: Use LLM agents to assign business semantics (e.g., `paper_title`, `abstract_text`, `reference_item`) to raw document blocks.
- **Style Decoupling**: Separate content from presentation using YAML-defined templates (supports JCST, IEEE, etc.).
- **Advanced Rendering**:
    - **DOCX**: Dynamic generation of styles, multi-column layout control, and academic "Three-line Table" rendering via OXML.
    - **LaTeX**: Structural source generation with automatic environment mapping and character escaping.

## Operational Procedures

### Documentation & Design
- Always refer to `docs/llm.txt` when designing or modifying `SemanticTemplate` YAML configurations.
- Maintain the `AnnotatedMinerUContentList` interface for all downstream rendering tasks.

### Processing Pipeline
1. **Parse**: Execute MinerU parser to get `content_list.json`.
2. **Protect**: Wrap complex elements in placeholders.
3. **Transform**: Apply `Refine` or `Translate` agents via `Workflow`.
4. **Annotate**: Label elements using `SemanticAnnotatorAgent` against a specific template.
5. **Render**: Produce the final artifact using `AdvancedDocxRenderer` or `LatexRenderer`.

### Debugging & Quality Control
- **Langfuse Observation**: Use the `@observe` decorator and `langfuse.openai` for tracing agent logic and token usage.
- **Placeholder Integrity**: Check for `ProtectionVerificationError` during agent processing to catch hallucinated or deleted placeholders.
- **Token Management**: Adjust `--chunk-size` (recommended 1500-2000) for large documents to prevent 20k token overflows.

## Detailed Execution Example

The following command demonstrates the full power of the pipeline, combining parsing, multiple agent workflows, and professional rendering:

```bash
cd /home/ider/workspace/document-semantic
uv run document-semantic process tests/docx/test_1.docx tests/docx/output/cli_test \
  -p mineru \
  --refine \
  --translate English \
  --template jcst-v2 \
  --chunk-size 1500
```

### Internal Workflow Breakdown:
1.  **MinerU Parsing & Alignment**:
    - The document is sent to MinerU API.
    - Resulting JSON is flattened and **aligned** with raw text from `test_1.docx` to fix OCR artifacts.
    - All image and formula assets are extracted to `output/cli_test/resources`.
2.  **Academic Refinement (`--refine`)**:
    - `LLMRefinementAgent` scans the text.
    - Automatically reformats citations (e.g., `[3,1,2]` -> `[1-3]`) and polishes academic flow while protecting formula placeholders.
3.  **Intelligent Translation (`--translate English`)**:
    - `LLMGlossaryExtractor` extracts global terminology.
    - Document is split into ~1500 character chunks.
    - `LLMTranslationAgent` translates Chinese to English, ensuring `<P:EQ_1/>` etc. remain untouched.
    - `LLMJudgerAgent` selects the highest quality translation for each chunk.
4.  **Semantic Annotation & Rendering (`--template jcst-v2`)**:
    - `SemanticAnnotatorAgent` labels blocks as `paper_title`, `abstract_text`, etc.
    - `AdvancedDocxRenderer` applies the **JCST V2** YAML style:
        - Creates a **double-column** layout for the body.
        - Generates **Three-line Tables** from HTML data.
        - Inserts high-res formula images with automatic right-aligned numbering.

## Integrated Commands
- `uv run document-semantic process <input.docx> <output_dir> -p mineru --refine --translate <lang> --template <id>`
