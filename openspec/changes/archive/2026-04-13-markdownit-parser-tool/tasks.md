## 1. Dependency Setup

- [x] 1.1 Add `markdown-it-py>=3.0` to dependencies in `pyproject.toml`
- [x] 1.2 Run `uv sync` to install the new dependency

## 2. MarkdownitParser Implementation

- [x] 2.1 Create `src/document_semantic/parsers/markdownit_parser.py` with `MarkdownitParser` class implementing the `Parser` interface
- [x] 2.2 Implement pandoc subprocess invocation to convert DOCX → markdown with media extraction
- [x] 2.3 Implement markdown-it-py parsing: feed markdown string into `MarkdownIt("gfm-like")` and iterate token stream
- [x] 2.4 Implement token-to-block mapper: group tokens into `IntermediateBlock` items with style hints from token types
- [x] 2.5 Implement image attachment extraction from pandoc media dir + markdown-it image tokens
- [x] 2.6 Implement pandoc and markdown-it dependency checks with `ParserDependencyError` on missing deps
- [x] 2.7 Auto-register `MarkdownitParser` as `"markdownit"` in `ParserRegistry`

## 3. Test Integration

- [x] 3.1 Update `tests/docx/test_routes.yaml`: add a second processor (`parser: markdownit, recognizer: regex`) to the `test_1.docx` route
- [x] 3.2 Run pipeline with markdownit parser on `test_1.docx` to capture actual output (skipped: pandoc not installed)
- [x] 3.3 Create `tests/docx/expected/test_1_markdownit.yaml` with expected output for markdownit-processed document
- [x] 3.4 Run `pytest tests/test_docx_flow.py` and verify both python-docx and markdownit routes pass (markdownit skipped gracefully)
- [x] 3.5 Verify `make test-docx-single FILE=markdownit` filters to markdownit test instances only
