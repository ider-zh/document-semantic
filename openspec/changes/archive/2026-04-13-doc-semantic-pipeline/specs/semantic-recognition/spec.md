## ADDED Requirements

### Requirement: Semantic recognizer abstraction interface
The system SHALL define a `SemanticRecognizer` protocol or abstract base class that specifies a `recognize(intermediate: IntermediateResult) -> SemanticDocument` method. All concrete recognizer implementations MUST conform to this interface.

#### Scenario: Recognizer interface conformance
- **WHEN** a new recognizer class is implemented against the `SemanticRecognizer` interface
- **THEN** it MUST accept an `IntermediateResult` and produce a valid `SemanticDocument`

#### Scenario: Recognizer preserves block order
- **WHEN** a recognizer processes an `IntermediateResult` with 10 blocks in sequence
- **THEN** the resulting `SemanticDocument` SHALL contain the same 10 blocks in their original order

### Requirement: Regex-based block recognizer
The system SHALL provide a `RegexRecognizer` that uses pattern matching to classify block-level elements into semantic types: `title`, `heading1` through `heading6`, `text`, `abstract`, `reference`, `list_item`, `table`, and `code_block`. The recognizer SHALL also identify inline-level semantics: `bold`, `italic`, `strikethrough`, `formula`, `code_span`, and `link`.

#### Scenario: Recognize heading blocks
- **WHEN** a block starts with `# ` (markdown heading syntax) or has heading style metadata
- **THEN** the recognizer SHALL classify it as the corresponding `heading1` through `heading6` block type

#### Scenario: Recognize inline bold and italic
- **WHEN** a block contains `**bold**` or `*italic*` markdown syntax
- **THEN** the recognizer SHALL mark those spans as `bold` or `italic` inline elements with the enclosed text

#### Scenario: Recognize inline formula
- **WHEN** a block contains `$...$` or `$$...$$` syntax
- **THEN** the recognizer SHALL mark those spans as `formula` inline or block elements with the LaTeX content

### Requirement: LLM-based recognizer placeholder
The system SHALL define an `LLMRecognizer` class with a `recognize()` method that is a placeholder for future LLM integration. The recognizer SHALL accept an `LLMClient` dependency for making inference calls.

#### Scenario: LLM recognizer raises not-implemented
- **WHEN** `LLMRecognizer.recognize()` is called without a configured `LLMClient`
- **THEN** it SHALL raise a `RecognizerNotConfiguredError` indicating LLM client is required

### Requirement: Router recognizer for conditional dispatch
The system SHALL provide a `RouterRecognizer` that dispatches to sub-recognizers based on configurable routing rules. Rules SHALL be evaluated in order and the first matching recognizer SHALL be used.

#### Scenario: Route by document type
- **WHEN** the router is configured with rule `doc_type: academic` → `AcademicRecognizer`
- **AND** the document metadata indicates academic type
- **THEN** the router SHALL dispatch to `AcademicRecognizer`

#### Scenario: Default recognizer fallback
- **WHEN** no routing rule matches the document
- **THEN** the router SHALL use the configured default recognizer

### Requirement: Recognizer configuration and selection
The system SHALL allow the active recognizer to be selected via configuration. The recognizer config SHALL support specifying the recognizer type and any recognizer-specific parameters.

#### Scenario: Config selects regex recognizer
- **WHEN** config specifies `recognizer: regex`
- **THEN** the pipeline SHALL use `RegexRecognizer` for semantic recognition

#### Scenario: Config selects router recognizer
- **WHEN** config specifies `recognizer: router` with routing rules
- **THEN** the pipeline SHALL use `RouterRecognizer` with the provided rules
