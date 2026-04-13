## ADDED Requirements

### Requirement: Parser abstraction interface
The system SHALL define a `Parser` protocol or abstract base class that specifies a `parse(docx_path: Path) -> IntermediateResult` method. All concrete parser implementations MUST conform to this interface. The `IntermediateResult` SHALL contain: a list of block-level elements, document metadata, and a collection of attachments (images, embedded objects).

#### Scenario: Parser interface conformance
- **WHEN** a new parser class is implemented against the `Parser` interface
- **THEN** it MUST produce a valid `IntermediateResult` with all required fields populated

#### Scenario: Parser returns attachments
- **WHEN** a DOCX file contains embedded images
- **THEN** the `IntermediateResult` SHALL include file references to extracted attachments with unique identifiers

### Requirement: Pluggable parser registry
The system SHALL provide a `ParserRegistry` that maps string identifiers (e.g., `"pandoc"`, `"python-docx"`) to parser classes. The pipeline SHALL resolve the active parser from configuration at runtime.

#### Scenario: Registry lookup by name
- **WHEN** the pipeline requests parser `"pandoc"` from the registry
- **THEN** the registry SHALL return the `PandocParser` implementation

#### Scenario: Unknown parser name
- **WHEN** the pipeline requests a parser name not registered
- **THEN** the system SHALL raise a `ParserNotFoundError` with a message listing available parsers

### Requirement: Pandoc parser implementation
The system SHALL provide a `PandocParser` that invokes pandoc as a subprocess to convert DOCX to an intermediate markdown representation. The parser SHALL extract image references and track them as attachments.

#### Scenario: Pandoc converts DOCX to MD
- **WHEN** `PandocParser.parse()` is called with a valid DOCX file
- **THEN** the output SHALL be an `IntermediateResult` with markdown-formatted blocks and image attachment references

#### Scenario: Pandoc not installed
- **WHEN** pandoc is not available on the system PATH
- **THEN** the parser SHALL raise a `ParserDependencyError` with installation instructions

### Requirement: Python-docx parser implementation
The system SHALL provide a `PythonDocxParser` that uses the `python-docx` library to read DOCX structure and produce an `IntermediateResult`. This parser SHALL extract paragraphs, tables, and inline formatting information.

#### Scenario: Python-docx extracts paragraphs
- **WHEN** `PythonDocxParser.parse()` is called with a DOCX containing styled paragraphs
- **THEN** the output SHALL include block elements with style hints (e.g., heading level, normal text)

#### Scenario: Python-docx extracts tables
- **WHEN** a DOCX file contains tables
- **THEN** the parser SHALL produce table block elements with cell content preserved

### Requirement: Parser configuration via config file
The system SHALL allow the active parser to be selected via a configuration file (YAML or TOML) or environment variable. The default parser SHALL be `python-docx`.

#### Scenario: Config file selects parser
- **WHEN** the config file specifies `parser: pandoc`
- **THEN** the pipeline SHALL use `PandocParser` for document parsing

#### Scenario: Default parser fallback
- **WHEN** no parser is specified in configuration
- **THEN** the system SHALL default to `python-docx` parser
