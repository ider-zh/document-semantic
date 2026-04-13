## 1. Dependency Setup

- [x] 1.1 Add `httpx>=0.27` and `python-dotenv>=1.0` to dependencies in `pyproject.toml`
- [x] 1.2 Run `uv sync` to install new dependencies

## 2. MinerUParser Implementation

- [x] 2.1 Create `src/document_semantic/parsers/mineru_parser.py` with `MinerUParser` class implementing the `Parser` interface
- [x] 2.2 Implement token loading from `MINERU_TOKEN` env var with `.env` fallback via `python-dotenv`
- [x] 2.3 Implement httpx-based upload: POST to `/api/v4/file-urls/batch` then PUT to presigned URL
- [x] 2.4 Implement polling loop: GET `/api/v4/extract-results/batch/{batch_id}` every 3s until `state: done` or timeout
- [x] 2.5 Implement result download: GET the `full_zip_url` and save as ZIP to cache directory
- [x] 2.6 Implement md5 file-hash-based caching: check cache before upload, store result ZIP and serialized `IntermediateResult`
- [x] 2.7 Implement `content_list_v2.json` parser: map JSON elements to `IntermediateBlock` items with style hints
- [x] 2.8 Implement markdown fallback: if `content_list_v2.json` absent, parse markdown file (same approach as PandocParser)
- [x] 2.9 Implement image attachment extraction from result ZIP
- [x] 2.10 Implement error handling: 401 token expiry, timeout, API errors with clear `ParserDependencyError` messages
- [x] 2.11 Auto-register `MinerUParser` as `"mineru"` in `ParserRegistry`

## 3. Configuration and Integration

- [x] 3.1 Update `src/document_semantic/pipeline/config.py` to add `mineru_token` and `mineru_cache_dir` fields with env var loading
- [x] 3.2 Update `src/document_semantic/parsers/__init__.py` to import and export `MinerUParser`
- [x] 3.3 Add `load_dotenv()` call to `src/document_semantic/__init__.py` or `pipeline/config.py`

## 4. Test Integration

- [x] 4.1 Update `tests/docx/test_routes.yaml`: add `parser: mineru` processor with `skip_if_no_token` flag
- [x] 4.2 Update `src/document_semantic/testing/routing.py`: add `skip_if_no_token` field to `ProcessorConfig`
- [x] 4.3 Update `tests/test_docx_flow.py`: add token availability check and graceful skip for mineru processor
- [x] 4.4 Run `pytest tests/test_docx_flow.py` and verify mineru route is skipped when token is not configured
- [x] 4.5 Verify `make test-docx-single FILE=mineru` filters to mineru test instances only
