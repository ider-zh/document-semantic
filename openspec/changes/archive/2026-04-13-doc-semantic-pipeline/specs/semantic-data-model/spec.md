## ADDED Requirements

### Requirement: Block-level semantic data model
The system SHALL define a discriminated union of block types: `title`, `heading1` through `heading6`, `text`, `abstract`, `reference`, `list_item`, `table`, and `code_block`. Each block type SHALL have a `type` field (used as discriminator), a `content` field containing the block's text, and an `inline_elements` field containing a list of recognized inline semantic elements. Each block SHALL carry a unique `id` field for tracing.

#### Scenario: Create a heading block
- **WHEN** a heading block is created with `type: heading1` and `content: "Introduction"`
- **THEN** the block SHALL be a valid Pydantic model with all required fields populated

#### Scenario: Block contains inline elements
- **WHEN** a text block contains the sentence "The **bold** word and `code` span"
- **THEN** the block's `inline_elements` SHALL contain a `bold` element for "bold" and a `code_span` element for "code"

### Requirement: Inline-level semantic data model
The system SHALL define inline element types: `bold`, `italic`, `strikethrough`, `formula`, `code_span`, and `link`. Each inline element SHALL have a `type` field, a `text` field with the raw content, and for `link` types, a `url` field. Inline elements SHALL carry `start_offset` and `end_offset` fields indicating their position within the parent block's content.

#### Scenario: Create an inline formula
- **WHEN** an inline formula element is created with `type: formula`, `text: "E=mc^2"`, `start_offset: 5`, `end_offset: 14`
- **THEN** the element SHALL be a valid Pydantic model with position metadata

#### Scenario: Link element includes URL
- **WHEN** a link inline element is created
- **THEN** it SHALL include both `text` (display text) and `url` (target URL) fields

### Requirement: Semantic document container
The system SHALL define a `SemanticDocument` model that contains: a `schema_version` field (string, semver format), a `metadata` field with document-level metadata, a `blocks` field as an ordered list of block-level elements, and an `attachments` field listing referenced attachments.

#### Scenario: SemanticDocument carries schema version
- **WHEN** a `SemanticDocument` is created
- **THEN** its `schema_version` SHALL default to `"1.0.0"`

#### Scenario: SemanticDocument serialization
- **WHEN** a `SemanticDocument` is serialized to JSON
- **THEN** all fields including nested inline elements SHALL be correctly serialized with type discriminators preserved

### Requirement: Schema versioning and upgrade
The system SHALL provide a `SchemaUpgrader` that can migrate a `SemanticDocument` from one schema version to another. The upgrader SHALL be registered to handle specific version transitions (e.g., `1.0.0` → `2.0.0`). When a document's schema version does not match the current version, the pipeline SHALL log a warning and attempt automatic upgrade.

#### Scenario: Upgrade from v1 to v2
- **WHEN** a `SemanticDocument` with `schema_version: "1.0.0"` is passed through the upgrader registered for `1.0.0 → 2.0.0`
- **THEN** the output SHALL be a `SemanticDocument` with `schema_version: "2.0.0"` and migrated fields

#### Scenario: Unknown schema version warning
- **WHEN** a `SemanticDocument` has `schema_version: "0.1.0"` and no upgrader is registered for that version
- **THEN** the system SHALL log a warning and pass the document through unchanged

### Requirement: Document-type-based routing for data model
The system SHALL support routing `SemanticDocument` instances through different post-processing pipelines based on document type metadata. A `DocumentRouter` SHALL evaluate type rules and apply type-specific transformations or validations.

#### Scenario: Route academic document for reference extraction
- **WHEN** a `SemanticDocument` has metadata `doc_type: academic`
- **AND** the router is configured to extract references for academic documents
- **THEN** the `reference` blocks SHALL be collected into a structured bibliography

#### Scenario: Unknown document type passthrough
- **WHEN** no routing rule matches the document type
- **THEN** the document SHALL pass through without transformation
