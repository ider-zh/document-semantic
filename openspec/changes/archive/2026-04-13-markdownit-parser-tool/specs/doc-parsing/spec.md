## MODIFIED Requirements

### Requirement: Pluggable parser registry
The system SHALL provide a `ParserRegistry` that maps string identifiers (e.g., `"pandoc"`, `"python-docx"`, `"markdownit"`) to parser classes. The pipeline SHALL resolve the active parser from configuration at runtime.

#### Scenario: Registry lookup by name
- **WHEN** the pipeline requests parser `"pandoc"` from the registry
- **THEN** the registry SHALL return the `PandocParser` implementation

#### Scenario: Registry lookup markdownit
- **WHEN** the pipeline requests parser `"markdownit"` from the registry
- **THEN** the registry SHALL return the `MarkdownitParser` implementation

#### Scenario: Unknown parser name
- **WHEN** the pipeline requests a parser name not registered
- **THEN** the system SHALL raise a `ParserNotFoundError` with a message listing available parsers