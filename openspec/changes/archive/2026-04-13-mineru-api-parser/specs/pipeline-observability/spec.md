## MODIFIED Requirements

### Requirement: Configurable output verbosity for results
The system SHALL support configurable verbosity levels for printed intermediate results: `summary` (block counts and types only), `preview` (first 100 chars of each block), and `full` (complete content). The verbosity SHALL be controlled via configuration. The `PipelineConfig` SHALL additionally support parser-specific settings including `mineru_token` for API authentication and `mineru_cache_dir` for cache directory configuration.

#### Scenario: Summary verbosity
- **WHEN** verbosity is set to `summary`
- **THEN** printed results SHALL show only block type counts (e.g., `heading1: 3, text: 12, reference: 5`)

#### Scenario: Preview verbosity
- **WHEN** verbosity is set to `preview`
- **THEN** printed results SHALL show block type and first 100 characters of content for each block

#### Scenario: MinerU token configuration
- **WHEN** the pipeline config includes `mineru_token` or `MINERU_TOKEN` env var is set
- **THEN** the MinerU parser SHALL use the token for API authentication