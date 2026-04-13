## ADDED Requirements

### Requirement: .env file loading for API tokens
The system SHALL support loading API tokens from a `.env` file at the project root. The `python-dotenv` library SHALL be used to load environment variables from `.env` into the process environment. Variables loaded from `.env` SHALL be overridden by explicitly set environment variables (standard dotenv behavior).

#### Scenario: Token loaded from .env
- **WHEN** the `.env` file contains `token_mineru=...` or `MINERU_TOKEN=...`
- **THEN** the value SHALL be available via `os.getenv("MINERU_TOKEN")` after dotenv loading

#### Scenario: Environment variable overrides .env
- **WHEN** both `.env` and the system environment set `MINERU_TOKEN`
- **THEN** the system environment value SHALL take precedence

### Requirement: Token configuration in pipeline config
The `PipelineConfig` SHALL support a `mineru_token` field that can be set explicitly, loaded from environment, or loaded from `.env`. The token SHALL NOT be logged or included in trace output (security requirement).

#### Scenario: Token from environment
- **WHEN** `MINERU_TOKEN` environment variable is set
- **THEN** `PipelineConfig.load()` SHALL set `mineru_token` to its value

#### Scenario: Token not configured
- **WHEN** no token is available via any source
- **THEN** `mineru_token` SHALL be `None` and the MinerU parser SHALL raise `ParserDependencyError` on use
