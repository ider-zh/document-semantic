## Context

The project has four DOCX parsers: `PythonDocxParser` (local, python-docx library), `PandocParser` (pandoc binary, DOCX→markdown), `MarkdownitParser` (pandoc + markdown-it-py for AST parsing). All produce `IntermediateResult` with flat `IntermediateBlock` items. None produce rich semantic data — formulas, tables with cell structure, and content classifications are left to the recognizer stage.

Mineru (mineru.net) is a cloud API using VLM models to extract structured content from documents. It returns a ZIP with: markdown, images, and crucially `content_list_v2.json` — a structured JSON with element-level metadata including formulas (LaTeX), table structures, heading levels, list types, and text classifications. This provides a fundamentally richer input format than any existing parser.

The `.env` file already contains a `token_mineru` JWT token. No dotenv loading exists in the codebase currently.

## Goals / Non-Goals

**Goals:**
- Implement `MinerUParser` that uploads DOCX to mineru.net API, polls for results, downloads the ZIP, and produces a rich `IntermediateResult`
- Use `httpx` (async-capable HTTP client) for all API calls, replacing `requests` from the reference code
- Load API token from `.env` via `python-dotenv`, with env var `MINERU_TOKEN` override
- Implement file-hash-based caching: md5 hash of DOCX content maps to a local cache directory containing the result ZIP and a serialized `IntermediateResult`
- Cache the downloaded ZIP so repeated parsing of the same document reuses it without re-downloading
- Parse `content_list_v2.json` from the result ZIP and use it to produce richer `IntermediateBlock` items with accurate style hints and inline elements
- Maintain the existing `Parser` interface — no changes to the abstract contract

**Non-Goals:**
- Not modifying the `Parser` ABC or `IntermediateResult` schema — the output is still the same types
- Not implementing a new recognizer — this is a parser-only change
- Not changing the recognizer stage input format — `IntermediateResult` is still the input
- Not auto-uploading to MinerU on every parse — caching is the default behavior

## Decisions

### Decision 1: httpx over requests

**Choice:** Use `httpx` for all HTTP interactions instead of `requests`.

**Rationale:** httpx supports both sync and async APIs with the same interface. The project may want async parsing in the future. httpx also has better connection pooling and HTTP/2 support. The user explicitly requested httpx.

**Alternatives considered:**
- `requests`: simpler but sync-only, already replaced by httpx in modern Python projects
- `aiohttp`: async-only, more complex for this use case

### Decision 2: md5 file hash for cache key

**Choice:** Cache results keyed by md5 hash of the DOCX file content.

**Rationale:** File hash is content-addressable — same document always produces the same key regardless of filename or location. md5 is fast enough for typical DOCX sizes (KB-MB range).

**Alternatives considered:**
- `(path, mtime)` tuple: fragile if file is moved or touched
- Full path as key: same document in different locations would be re-parsed

### Decision 3: Cache directory structure

**Choice:** Cache stored at `~/.cache/document-semantic/mineru/<hash>/` containing:
- `result.zip` — the full result ZIP from MinerU (not extracted)
- `intermediate_result.json` — serialized `IntermediateResult` for instant deserialization

**Rationale:** Storing the ZIP avoids re-downloading. Storing the serialized `IntermediateResult` avoids both re-downloading and re-parsing the JSON. The cache directory is self-contained and easy to clean.

### Decision 4: Polling strategy for extraction results

**Choice:** After uploading, poll the result endpoint every 3 seconds with a 5-minute timeout. Return the result ZIP URL when `state: "done"`.

**Rationale:** The MinerU API is async — upload returns a `batch_id`, results become available later. Polling with reasonable interval and timeout balances latency and API load.

**Alternatives considered:**
- Webhook callback: MinerU API doesn't appear to support webhooks
- Single blocking request: could hang indefinitely if extraction is slow

### Decision 5: content_list_v2.json as primary block source

**Choice:** Parse `content_list_v2.json` from the result ZIP and map its structured elements to `IntermediateBlock` items. Fall back to the markdown file if `content_list_v2.json` is absent or malformed.

**Rationale:** The JSON provides element-level type, content, and metadata — far more precise than markdown block splitting. The recognizer can then work from higher-quality input.

**Fallback:** If the JSON is missing, use the markdown file (same approach as PandocParser).

### Decision 6: Token loading from .env

**Choice:** Use `python-dotenv` to load `.env` at project root. Token read from `MINERU_TOKEN` environment variable (consistent with existing `DOC_SEMANTIC_*` naming). The `.env` file's `token_mineru` key is loaded by dotenv.

**Rationale:** `.env` is a standard pattern. `MINERU_TOKEN` is consistent with the project's env var naming convention. Users can set the token via env var directly (for CI/CD) or via `.env` file (for local dev).

### Decision 7: Keep ZIP compressed in cache

**Choice:** Store the result ZIP as-is in the cache. Do not extract and store individual files. When needed, read from the ZIP using Python's `zipfile` module.

**Rationale:** ZIP is a single file, easy to cache and clean. Python's `zipfile` can read specific entries without full extraction. Avoids cache bloat from extracted directory trees.

## Risks / Trade-offs

- **[Risk]** MinerU API rate limits or downtime → **Mitigation:** Cache eliminates repeat calls. Graceful `ParserDependencyError` on API failure with clear message.
- **[Risk]** Token expires (JWT has expiry) → **Mitigation:** Detect 401 response, log clear error with token refresh instructions. Don't retry automatically.
- **[Risk]** Large DOCX files cause slow uploads → **Mitigation:** Log upload progress. User can set timeout via config. Cache means slow only happens once per document.
- **[Risk]** content_list_v2.json schema changes → **Mitigation:** Parse defensively with fallback to markdown. Log warnings for unrecognized element types.
- **[Trade-off]** Cloud dependency vs local parsers → **Acceptable** for a testing/validation tool; MinerU provides superior quality that local parsers cannot match.
