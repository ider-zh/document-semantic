## MODIFIED Requirements

### Requirement: Semantic recognition is optional
The semantic recognition module (recognizers) SHALL be an optional post-processing step, not a mandatory stage in the default pipeline.

**Reason**: The original pipeline required every parse to go through a recognizer (regex/LLM/router) to produce a `SemanticDocument`. This change decouples recognition from the core parsing/processing flow, making parsers directly produce structured Markdown output. Recognizers can still be applied afterward for enrichment (e.g., classifying block types, extracting semantic tags).

**Migration**: Existing code that uses `Pipeline` with a recognizer SHALL continue to work but with a warning that the `recognizer` parameter is deprecated in favor of the new `processor` approach. The `recognizer` parameter SHALL be removed in a future version.

#### Scenario: Pipeline runs without recognizer
- **WHEN** a `Pipeline` is constructed with only a parser (no recognizer specified)
- **THEN** the pipeline produces an `IntermediateResult` which is passed to the parser's processor to produce Markdown, resource directory, and JSON mapping outputs

#### Scenario: Pipeline runs with optional recognizer for enrichment
- **WHEN** a `Pipeline` is constructed with a parser and an optional recognizer specified as `post_processor`
- **THEN** the pipeline first produces processor output (Markdown + resources), then optionally runs the recognizer on the `IntermediateResult` for semantic enrichment

### Requirement: Recognizer interface remains available for optional use
The `SemanticRecognizer` ABC and its implementations (`RegexRecognizer`, `LLMRecognizer`) SHALL remain available in the codebase but SHALL NOT be part of the default pipeline output path.

#### Scenario: RegexRecognizer used as post-processor
- **WHEN** a user explicitly configures a recognizer as a post-processor
- **THEN** the recognizer processes the `IntermediateResult` and produces a `SemanticDocument` alongside the processor's Markdown output
