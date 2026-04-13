## ADDED Requirements

### Requirement: Markdown-it parser implementation
The system SHALL provide a `MarkdownitParser` that uses pandoc to convert DOCX to markdown, then parses the markdown using markdown-it-py to produce an `IntermediateResult`. The parser SHALL map markdown-it tokens to `IntermediateBlock` items with accurate style hints derived from token types (e.g., `heading_open` → `HeadingN`, `fence` → `CodeBlock`, `image` → attachment). The parser SHALL extract image references from both pandoc's media output and markdown-it image tokens.

#### Scenario: Markdownit parses DOCX via pandoc + markdown-it
- **WHEN** `MarkdownitParser.parse()` is called with a valid DOCX file
- **THEN** the output SHALL be an `IntermediateResult` with blocks classified by markdown-it token types and image attachments collected

#### Scenario: Style hints from markdown-it token types
- **WHEN** a markdown heading `# Title` is parsed by markdown-it
- **THEN** the resulting block SHALL have `style_hint` set to `Heading1` based on the `heading_open` token's `tag` attribute

#### Scenario: Code block detection
- **WHEN** a markdown fenced code block is encountered
- **THEN** the parser SHALL produce a block with `style_hint` set to `CodeBlock`

### Requirement: Pandoc dependency for markdownit parser
The `MarkdownitParser` SHALL require pandoc to be installed for DOCX → markdown conversion. If pandoc is not available, the parser SHALL raise a `ParserDependencyError` with installation instructions.

#### Scenario: Pandoc not installed
- **WHEN** pandoc is not available on the system PATH
- **THEN** `MarkdownitParser.parse()` SHALL raise `ParserDependencyError` with a message explaining pandoc is required

### Requirement: markdown-it-py dependency
The `MarkdownitParser` SHALL require `markdown-it-py` to be installed for markdown AST parsing. The parser SHALL use the GFM preset for full CommonMark + GitHub Flavored Markdown support.

#### Scenario: markdown-it-py not installed
- **WHEN** `markdown-it-py` is not available as a Python package
- **THEN** importing or using `MarkdownitParser` SHALL raise a clear error with installation instructions (`pip install markdown-it-py`)

### Requirement: Markdown-it parser auto-registration
The `MarkdownitParser` SHALL auto-register itself in the `ParserRegistry` under the name `"markdownit"`.

#### Scenario: Registry lookup
- **WHEN** the pipeline requests parser `"markdownit"` from the registry
- **THEN** the registry SHALL return the `MarkdownitParser` implementation

### Requirement: Image attachment extraction
The `MarkdownitParser` SHALL extract image attachments from pandoc's media directory and track them with unique identifiers. Each attachment SHALL include the file path and inferred MIME type from the file extension.

#### Scenario: Image attachments from DOCX
- **WHEN** a DOCX file contains embedded images
- **THEN** the `IntermediateResult` SHALL include attachment entries for each image with file path and MIME type
