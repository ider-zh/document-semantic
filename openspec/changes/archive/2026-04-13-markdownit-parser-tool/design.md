## Context

The project has two DOCX parsers: `PythonDocxParser` (reads DOCX structure directly via python-docx) and `PandocParser` (invokes pandoc subprocess to convert DOCX → markdown). Both produce `IntermediateResult` with flat `IntermediateBlock` items. PandocParser's block splitting is naive (blank-line separation) and it does not use a markdown parser to understand structure — it only does regex-based style hint inference.

markdown-it is a mature markdown parser (with a Python port, `markdown-it-py`) that produces a full token AST with precise position data, proper nesting awareness, and support for all CommonMark + GFM features. Using markdown-it on pandoc's markdown output gives structured block types, accurate inline element positions, and reliable image link detection.

## Goals / Non-Goals

**Goals:**
- Implement `MarkdownitParser` that chains: DOCX → pandoc markdown → markdown-it AST → `IntermediateResult`
- Produce `IntermediateBlock` items with accurate style hints derived from markdown-it token types (not regex)
- Extract image attachments from pandoc's media extraction, plus image references from markdown-it image tokens
- Integrate with the existing `Parser` interface and auto-register as `"markdownit"`
- Add test coverage in `test_docx_flow.py` with a route for the markdownit parser

**Non-Goals:**
- Not replacing pandoc — MarkdownitParser uses pandoc as the DOCX → markdown source, so pandoc is a required dependency
- Not a standalone DOCX parser — the DOCX reading is delegated to pandoc; markdown-it only parses the markdown output
- Not implementing a new recognizer — this is purely a parser-level change

## Decisions

### Decision 1: Pandoc as DOCX → markdown source, markdown-it as structure parser

**Choice:** MarkdownitParser invokes pandoc to produce markdown, then feeds the markdown string into markdown-it-py to parse into tokens, which are then mapped to `IntermediateBlock` items.

**Rationale:** markdown-it-py is a markdown parser, not a DOCX reader. Pandoc is the best available DOCX → markdown converter. Combining them gives pandoc's DOCX extraction quality plus markdown-it's structural understanding.

**Alternatives considered:**
- Use python-docx → markdown → markdown-it: loses pandoc's superior DOCX conversion quality
- Build a DOCX reader from scratch: too much effort, pandoc already does this well

### Decision 2: Token-to-block mapping strategy

**Choice:** Iterate markdown-it tokens sequentially. Each `inline`, `paragraph_open/close`, `heading_open/close`, `fence`, `table`, etc. token group maps to one `IntermediateBlock`. Image tokens produce both a block (if standalone) and an attachment entry.

**Rationale:** markdown-it's token stream is well-structured and predictable. A sequential pass with a small state machine can group open/close token pairs into blocks. This is simpler and more accurate than the current pandoc blank-line splitting.

### Decision 3: Dependency via `markdown-it-py`

**Choice:** Use `markdown-it-py` (the Python port) rather than the JS markdown-it via subprocess.

**Rationale:** markdown-it-py is a pure Python dependency, installable via pip/pypi, consistent with the project's Python ecosystem. No Node.js runtime needed.

### Decision 4: Test via existing test flow infrastructure

**Choice:** Add a `markdownit` route to `tests/docx/test_routes.yaml` and a corresponding expected output YAML. The existing parameterized test in `test_docx_flow.py` will pick it up automatically.

**Rationale:** The real-docx-test-flow infrastructure already supports multiple processors per route. Adding `parser: markdownit` as a second processor to the existing `test_1.docx` route tests both parsers against the same document for comparison.

## Risks / Trade-offs

- **[Risk]** MarkdownitParser adds pandoc as a hard dependency (unlike python-docx parser) → **Mitigation:** Check pandoc availability at parse time and raise `ParserDependencyError` with clear message. Test skips if pandoc unavailable.
- **[Risk]** markdown-it token structure differs from pandoc's output style (e.g., pandoc-specific extensions) → **Mitigation:** Use markdown-it's GFM preset which covers common markdown. Log unmapped token types as warnings.
- **[Trade-off]** Two-step conversion (pandoc + markdown-it) is slower than either parser alone → **Acceptable** for a testing/validation tool; performance is not the primary goal.
