## Why

The existing parsers (`python-docx`, `pandoc`, `markdownit`) produce flat block-level output with limited semantic understanding. MinerU (mineru.net) is a cloud API that uses VLM models to extract rich structured content from DOCX documents — including markdown, images, formulas, tables with cell-level content, and a `content_list_v2.json` with preliminary semantic annotations. This provides significantly richer parsing output than any local parser can achieve, enabling downstream recognizers to work from high-quality semantic data rather than raw text.

## What Changes

- Add `httpx` and `python-dotenv` as new dependencies
- Implement `MinerUParser` that uploads DOCX to mineru.net API, polls for extraction results, downloads the result ZIP, and produces a rich `IntermediateResult` with blocks, attachments, and parsed `content_list_v2.json` semantic data
- Add token-based authentication loaded from `.env` (via `python-dotenv`)
- Implement file-level caching: hash the DOCX content, cache the result ZIP and parsed `IntermediateResult` locally, skip API calls for repeated documents
- Extend `PipelineConfig` to support MinerU-specific settings (token, cache directory, API base URL)
- Add a `mineru` route in `tests/docx/test_routes.yaml` with test coverage (skipped when token is not configured)
- **Architectural note**: The `content_list_v2.json` output from MinerU contains structured semantic data (formulas, tables, headings, lists with metadata) that could serve as a richer input to the recognizer stage. This change lays the groundwork for a future "structured recognizer" that consumes MinerU's semantic JSON directly.

## Capabilities

### New Capabilities
- `mineru-api-parser`: Cloud API parser using mineru.net with token auth, result caching by file hash, and rich semantic output including `content_list_v2.json`
- `parser-token-auth`: Token-based API authentication via `.env` configuration for cloud-based parsers
- `parser-result-cache`: Local caching of parser results by file hash to avoid redundant API calls

### Modified Capabilities
- `doc-parsing`: Add a new parser implementation (`MinerUParser`) and extend the parser interface to support cached/remote results (existing spec at `openspec/specs/doc-parsing/spec.md`)
- `pipeline-observability`: Extend pipeline config to support parser-specific settings like API tokens and cache directories (existing spec at `openspec/specs/pipeline-observability/spec.md`)

## Impact

- **New files**: `src/document_semantic/parsers/mineru_parser.py`, `src/document_semantic/testing/test_utils.py` (pandoc/mineru skip helpers)
- **Modified files**: `src/document_semantic/parsers/__init__.py`, `src/document_semantic/pipeline/config.py`, `tests/docx/test_routes.yaml`
- **New dependencies**: `httpx>=0.27`, `python-dotenv>=1.0`
- **No breaking changes**: Existing parsers and pipeline API unchanged; mineru is opt-in via config
