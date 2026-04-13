## ADDED Requirements

### Requirement: MinerU API parser implementation
The system SHALL provide a `MinerUParser` that uploads DOCX files to the mineru.net API, polls for extraction results, downloads the result ZIP, and produces an `IntermediateResult`. The parser SHALL use `content_list_v2.json` from the result ZIP as the primary source for block generation, falling back to the markdown file if the JSON is absent or malformed. Each block SHALL include accurate style hints derived from the JSON element types (e.g., `formula`, `table`, `heading`, `text`, `list`, `image`).

#### Scenario: MinerU parses DOCX via API
- **WHEN** `MinerUParser.parse()` is called with a valid DOCX file and configured token
- **THEN** the output SHALL be an `IntermediateResult` with blocks derived from `content_list_v2.json` element types and image attachments from the result ZIP

#### Scenario: Fallback to markdown when JSON absent
- **WHEN** the result ZIP does not contain `content_list_v2.json`
- **THEN** the parser SHALL fall back to parsing the markdown file with style hint inference (same approach as PandocParser)

#### Scenario: Upload and poll for results
- **WHEN** a DOCX is uploaded to the mineru.net API
- **THEN** the parser SHALL poll the result endpoint until `state: "done"` or timeout, then download the result ZIP

### Requirement: MinerU API token authentication
The `MinerUParser` SHALL authenticate all API requests using a Bearer token loaded from the `MINERU_TOKEN` environment variable. The token SHALL be read at parse time and included in the `Authorization` header of every request. If no token is configured, the parser SHALL raise a `ParserDependencyError` with instructions to set the token.

#### Scenario: Token loaded from environment
- **WHEN** `MINERU_TOKEN` is set in the environment
- **THEN** the parser SHALL include `Authorization: Bearer <token>` in all API requests

#### Scenario: No token configured
- **WHEN** `MINERU_TOKEN` is not set
- **THEN** `MinerUParser.parse()` SHALL raise `ParserDependencyError` with instructions to set `MINERU_TOKEN` in `.env` or environment

### Requirement: httpx for HTTP communication
The `MinerUParser` SHALL use the `httpx` library for all HTTP requests (upload, poll, download). The parser SHALL use synchronous httpx client for compatibility with the existing synchronous `Parser` interface.

#### Scenario: HTTP upload
- **WHEN** a DOCX file is uploaded to the mineru.net API
- **THEN** the request SHALL be made using `httpx` with the correct headers and multipart form data

#### Scenario: HTTP timeout handling
- **WHEN** the API request takes longer than the configured timeout
- **THEN** the parser SHALL raise a `ParserError` with a timeout message

### Requirement: MinerU parser auto-registration
The `MinerUParser` SHALL auto-register itself in the `ParserRegistry` under the name `"mineru"`.

#### Scenario: Registry lookup
- **WHEN** the pipeline requests parser `"mineru"` from the registry
- **THEN** the registry SHALL return the `MinerUParser` implementation
