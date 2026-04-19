## Context

The current document semantic processing tool follows a rigid pipeline: DOCX files are parsed by one of several parsers (python-docx, pandoc, markdownit, mineru) to produce an `IntermediateResult`, which is then passed to a recognizer (regex, LLM, router) to produce a `SemanticDocument` for JSON output.

This architecture has several limitations:
- The recognizer step is mandatory even when not needed, adding unnecessary complexity
- Parsers produce a generic `IntermediateResult` that loses parser-specific information
- There is no support for producing markdown output with XML placeholders for special elements
- Images and resources are not extracted or tracked

The refactoring aims to simplify the pipeline by removing the mandatory recognizer step and enabling each parser to directly produce a dedicated processor output format.

## Goals / Non-Goals

**Goals:**
- Remove the mandatory recognizer step from the processing pipeline
- Enable each parser to produce a dedicated processor output with structured content
- Add markdown output format with XML placeholders for code, formula, and image blocks
- Add resource directory structure with extracted images and a JSON mapping file
- Maintain backward compatibility for the existing `parse()` method

**Non-Goals:**
- Implementing the LLM recognizer (remains a placeholder)
- Adding new parser implementations (existing parsers only)
- Supporting output formats other than JSON and markdown
- Modifying the input file format support (DOCX and markdown only)

## Decisions

### 1. Parser vs Processor Separation

**Decision:** Extend existing parsers with a `process()` method rather than creating separate processor classes.

**Rationale:**
- Each parser already has the context needed to identify and categorize elements during parsing
- Creating separate processor classes would require duplicating parsing logic or sharing internal state
- The `parse()` method remains available for backward compatibility, returning `IntermediateResult`
- The new `process()` method returns a dedicated `ProcessorOutput` type with richer structure

**Implementation:**
```python
class BaseParser:
    def parse(self, input: Path) -> IntermediateResult:
        """Existing method - returns generic intermediate result."""

    def process(self, input: Path, output_dir: Path) -> ProcessorOutput:
        """New method - returns structured output with resources."""
```

The `ProcessorOutput` type contains:
- `content`: The processed document content (JSON or markdown)
- `resources`: A mapping of resource IDs to their metadata and file paths
- `metadata`: Document-level metadata

### 2. XML Placeholder Format

**Decision:** Use a simple XML-style placeholder format for special elements in markdown output.

**Block-level placeholders:**
```xml
<code id="1"/>
<formula id="1"/>
<image id="1"/>
```

**Inline placeholders:**
```xml
<code id="1">content</code>
<formula id="1">content</formula>
```

**Rationale:**
- Simple and parseable by downstream tools
- Clear distinction between block (self-closing) and inline (with content) elements
- IDs are sequential integers scoped per resource type within a document
- Placeholders reference entries in the resources mapping file

**Rules:**
- Block placeholders occupy their own line in the markdown
- Inline placeholders appear within text content
- IDs start at 1 and increment per resource type
- The same ID always refers to the same resource within a document

### 3. Resource Directory Structure

**Decision:** Store resources in a `{output_dir}/resources/` subdirectory.

**Structure:**
```
{output_dir}/
  output.json          # or output.md
  resources/
    resources.json     # Mapping file
    images/
      image_1.png
      image_2.png
    ...
```

**Rationale:**
- Keeps resources co-located with the output file
- Separate `images/` subdirectory for organized storage
- Single `resources.json` mapping file at the resources root
- Easy to archive or transfer as a single directory

### 4. JSON Mapping File Format

**Decision:** Use a structured JSON format that maps resource IDs to their metadata.

**Format:**
```json
{
  "version": "1.0",
  "resources": {
    "image": {
      "1": {
        "type": "image",
        "file": "images/image_1.png",
        "metadata": {
          "width": 800,
          "height": 600,
          "format": "png"
        }
      }
    },
    "code": {
      "1": {
        "type": "code",
        "language": "python",
        "content": "print('hello')",
        "metadata": {}
      }
    },
    "formula": {
      "1": {
        "type": "formula",
        "content": "E = mc^2",
        "metadata": {}
      }
    }
  }
}
```

**Rationale:**
- Grouped by resource type for easy lookup
- Each entry includes type, file path (for binary resources), and metadata
- Inline resources (code, formula) store content directly
- Version field allows future format changes
- Empty metadata object ensures consistent structure

### 5. Pipeline Simplification

**Decision:** The new pipeline is: `DOCX -> Parser.process() -> ProcessorOutput -> File Output`

The recognizer step becomes optional and can be applied as a post-processing step if needed:
```
DOCX -> Parser.process() -> ProcessorOutput -> [Recognizer] -> Enhanced ProcessorOutput
```

**Rationale:**
- Most use cases only need parsing, not semantic recognition
- Recognizers can still be applied when needed without modifying the core pipeline
- Simplifies the default path and reduces processing time

## Risks / Trade-offs

### Risk: Breaking changes for existing users

**Mitigation:** Keep the `parse()` method unchanged. The `process()` method is additive. Existing code continues to work without modification.

### Trade-off: Parser complexity increases

Parsers now have additional responsibility for processing. However, this is acceptable because:
- Parsers already perform element identification during parsing
- The alternative (separate processors) would require re-parsing or complex state sharing
- The `process()` method can delegate to `parse()` internally and then transform the result

### Risk: XML placeholder conflicts with user content

If document content contains literal strings like `<code id="1"/>`, it could be confused with a placeholder.

**Mitigation:** 
- Use a reserved XML namespace: `<doc:id="1" xmlns:doc="..."/>`
- Or document that placeholders use a specific ID range and format
- Consider using a non-XML format like `[[CODE:1]]` if conflicts become an issue

### Trade-off: Resource ID scoping

IDs are scoped per-document, which means merging documents requires ID reconciliation.

**Mitigation:** Document this limitation. Provide a utility function for merging processor outputs with ID remapping if needed in the future.

### Risk: Markdown output loses structural information

Converting to markdown with placeholders may lose some structural details present in the original DOCX.

**Mitigation:**
- JSON output remains available for full structural fidelity
- Markdown output is explicitly a "rendered" view, not a lossless format
- Document which elements are preserved and which are simplified
