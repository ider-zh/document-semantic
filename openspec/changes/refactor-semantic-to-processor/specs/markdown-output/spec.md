## ADDED Requirements

### Requirement: Markdown output with XML placeholders
The processor SHALL produce a Markdown file where block-level and inline elements are replaced with XML placeholders:

- **Block-level elements** (formulas, code blocks, images) SHALL use self-closing tags: `<formula id="N"/>`, `<code id="N"/>`, `<image id="N"/>`
- **Inline elements** (formulas, code spans) SHALL use tags with original content preserved: `<formula id="N">original content</formula>`, `<code id="N">original content</code>`

The IDs SHALL be sequential integers starting from 1, scoped within each document.

#### Scenario: Block formula replaced with placeholder
- **WHEN** the processor encounters a block-level formula element
- **THEN** the Markdown output contains `<formula id="1"/>` at that position and the formula content is stored in the JSON mapping

#### Scenario: Inline code span preserved with content
- **WHEN** the processor encounters an inline code span like `print("hello")`
- **THEN** the Markdown output contains `<code id="2">print("hello")</code>`

### Requirement: Markdown formatting rules
The generated Markdown SHALL follow these formatting conventions:
- Headers use ATX syntax (`#`, `##`, etc.)
- Tables use GFM syntax with header separators
- Lists use `-` for unordered and `1.` for ordered
- Paragraphs separated by blank lines
- XML placeholders appear on their own line for block-level elements

#### Scenario: Table formatted as GFM
- **WHEN** the processor encounters a table element
- **THEN** the output is valid GFM table syntax with `|` separators and header row

### Requirement: Output configuration
The processor SHALL accept a `ProcessorConfig` that controls:
- Whether to produce Markdown output (default: true)
- Whether to use XML placeholders (default: true)
- Whether to generate the resource directory (default: true)

#### Scenario: XML placeholders disabled
- **WHEN** config has `use_xml_placeholders=false`
- **THEN** the Markdown output contains the original content directly without XML placeholder substitution
