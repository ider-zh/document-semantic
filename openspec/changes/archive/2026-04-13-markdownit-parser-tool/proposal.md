## Why

The existing parsers (`python-docx` and `pandoc`) produce flat block-level output with limited structural understanding of markdown syntax. A markdown-it based parser would leverage the full markdown AST — proper heading levels, lists, code fences, tables, blockquotes, and image links with accurate position data. This produces richer `IntermediateResult` blocks with precise inline element positions and better image attachment extraction, enabling downstream recognizers to work from higher-quality parsed content.

## What Changes

- Add `markdown-it-py` as a new dependency for parsing markdown AST from DOCX content
- Implement `MarkdownitParser` that converts DOCX to markdown (via pandoc subprocess), then uses markdown-it to parse into structured blocks with precise inline element positions and image attachment extraction
- Auto-register the parser as `"markdownit"` in the `ParserRegistry`
- Add a test route for `markdownit` in `tests/docx/test_routes.yaml` and expected output assertions in `tests/test_docx_flow.py`

## Capabilities

### New Capabilities
- `markdownit-parser`: markdown-it based parser that converts DOCX → markdown → structured IntermediateResult with precise inline elements and image attachments

### Modified Capabilities
- `doc-parsing`: Add a new parser implementation (`MarkdownitParser`) registered in the parser registry (existing spec at `openspec/specs/doc-parsing/spec.md`)
- `docx-test-suite`: Extend the test suite to cover the markdownit parser workflow (existing spec at `openspec/specs/docx-test-suite/spec.md`)

## Impact

- **New files**: `src/document_semantic/parsers/markdownit_parser.py`
- **Modified files**: `tests/docx/test_routes.yaml` (add markdownit route), `tests/docx/expected/test_1_markdownit.yaml` (expected output)
- **New dependency**: `markdown-it-py>=3.0` (Python port of markdown-it)
- **No breaking changes**: Existing parsers and pipeline API unchanged; markdownit is opt-in via config
