## ADDED Requirements

### Requirement: File-hash-based result caching
The `MinerUParser` SHALL cache parse results locally keyed by the MD5 hash of the DOCX file content. When a document is parsed, the parser SHALL first check the cache for an existing result. If found, the cached result SHALL be returned without making API calls. The cache key SHALL be deterministic — the same document always produces the same hash regardless of filename or location.

#### Scenario: Cache hit returns cached result
- **WHEN** a DOCX file is parsed that has been parsed before
- **THEN** the cached `IntermediateResult` SHALL be returned without uploading to the API

#### Scenario: Cache miss triggers API call
- **WHEN** a DOCX file is parsed for the first time
- **THEN** the parser SHALL upload to the API, cache the result, and return it

#### Scenario: Cache key is content-based
- **WHEN** the same DOCX file is copied to a different path and parsed
- **THEN** the cache SHALL recognize it as the same document and return the cached result

### Requirement: Cache storage format
The cache SHALL store results at `~/.cache/document-semantic/mineru/<hash>/` containing:
- `result.zip` — the full result ZIP from the MinerU API (not extracted)
- `intermediate_result.json` — serialized `IntermediateResult` for instant deserialization

The cache SHALL read from the ZIP using Python's `zipfile` module without full extraction.

#### Scenario: Cache stores ZIP and JSON
- **WHEN** a result is cached
- **THEN** the cache directory SHALL contain both `result.zip` and `intermediate_result.json`

#### Scenario: Cache reads from ZIP
- **WHEN** a cached result is needed for block extraction
- **THEN** the parser SHALL read specific files from `result.zip` using `zipfile` without extracting the entire archive

### Requirement: Cache directory configuration
The cache directory SHALL be configurable via environment variable `MINERU_CACHE_DIR` (default: `~/.cache/document-semantic/mineru/`). The parser SHALL create the cache directory if it does not exist.

#### Scenario: Default cache location
- **WHEN** `MINERU_CACHE_DIR` is not set
- **THEN** the cache SHALL be stored at `~/.cache/document-semantic/mineru/`

#### Scenario: Custom cache location
- **WHEN** `MINERU_CACHE_DIR=/tmp/my-cache` is set
- **THEN** the cache SHALL be stored at the specified path
