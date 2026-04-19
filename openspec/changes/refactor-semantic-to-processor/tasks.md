## 1. Core Models and Types

- [x] 1.1 Define `ProcessorOutput` dataclass/model with fields: `markdown_path`, `resources_dir`, `resources_json_path`, `metadata`
- [x] 1.2 Define `ProcessorConfig` dataclass/model with fields: `output_markdown`, `output_resources`, `output_json_mapping`, `use_xml_placeholders`
- [x] 1.3 Define `ProcessResult` dataclass/model returned by `process()` with paths to all three output artifacts
- [x] 1.4 Add new types to `src/document_semantic/models/` module and export from `__init__.py`

## 2. XML Placeholder Utilities

- [x] 2.1 Create `src/document_semantic/utils/xml_placeholders.py` with functions for generating block-level placeholders (`<code id="N"/>`, `<formula id="N"/>`, `<image id="N"/>`)
- [x] 2.2 Create inline placeholder generation (`<code id="N">content</code>`, `<formula id="N">content</formula>`)
- [x] 2.3 Create ID counter class that manages sequential IDs per resource type (formula, code, image)
- [ ] 2.4 Add unit tests for placeholder generation and ID management

## 3. JSON Mapping File Generator

- [x] 3.1 Create `src/document_semantic/utils/resource_mapping.py` with function to build `resources.json` structure
- [x] 3.2 Implement mapping builder that collects all resources during processing and outputs the JSON structure per spec (version, resources grouped by type, metadata)
- [ ] 3.3 Add unit tests for JSON mapping generation with various resource types

## 4. Parser Processor Methods

- [x] 4.1 Add `process()` method to `PythonDocxParser` that calls `parse()` then transforms `IntermediateResult` to Markdown + resources
- [x] 4.2 Add `process()` method to `MinerUParser` that handles MinerU-specific element types (formula, code, image, table) and produces Markdown + resources
- [x] 4.3 Add `process()` method to `PandocParser` that transforms pandoc markdown to the standardized format with XML placeholders
- [x] 4.4 Add `process()` method to `MarkdownitParser` that transforms markdownit output to the standardized format
- [x] 4.5 Extract common Markdown generation logic into a shared helper (e.g., `MarkdownGenerator` class) to avoid duplication across processors

## 5. Markdown Generation with XML Placeholders

- [x] 5.1 Implement `MarkdownGenerator` class in `src/document_semantic/utils/markdown_generator.py`
- [x] 5.2 `MarkdownGenerator` SHALL handle block types: title, heading, text, abstract, reference, list_item, table, code_block
- [x] 5.3 `MarkdownGenerator` SHALL replace block-level formulas, code blocks, and images with XML placeholders
- [x] 5.4 `MarkdownGenerator` SHALL replace inline formulas and code spans with inline XML placeholders preserving original content
- [x] 5.5 `MarkdownGenerator` SHALL write images to `resources/images/` and use relative paths in Markdown output
- [x] 5.6 `MarkdownGenerator` SHALL produce the `resources.json` mapping file alongside the Markdown
- [ ] 5.7 Add unit tests for `MarkdownGenerator` with various block and inline element combinations

## 6. Pipeline Updates

- [x] 6.1 Update `Pipeline` class to support new `processor` workflow with `process()` method
- [x] 6.2 Make `recognizer` parameter optional and deprecated in `Pipeline` constructor, emit deprecation warning when used
- [x] 6.3 Add new pipeline method `run_with_processor()` that produces `ProcessorOutput` with all three artifacts
- [x] 6.4 Add `post_processor` optional parameter for running recognizers after processor output
- [x] 6.5 Update `PipelineConfig` to support new processor configuration options
- [ ] 6.6 Add integration tests for new pipeline workflow

## 7. Test Flow Updates

- [x] 7.1 Update `test_docx_flow.py` to produce three output files by default: `.md`, `resources/`, `resources.json`
- [x] 7.2 Create test output directory structure at `tests/docx/output/<docx_name>_<processor>/`
- [x] 7.3 Add output directory cleanup before each test run
- [x] 7.4 Add route YAML configuration options: `output_markdown`, `output_resources`, `output_json_mapping` with defaults of `true`
- [x] 7.5 Update `tests/docx/test_routes.yaml` to include new output configuration if needed
- [x] 7.6 Add `.gitignore` entry for `tests/docx/output/` directory
- [ ] 7.7 Run test flow manually to verify all three output files are produced correctly

## 8. Backward Compatibility and Cleanup

- [x] 8.1 Verify existing `parse()` method behavior is unchanged across all parsers
- [x] 8.2 Verify existing `Pipeline` with recognizer still works (with deprecation warning)
- [x] 8.3 Run existing tests (`test_parsers.py`, `test_recognizers.py`, `test_models_and_pipeline.py`) to ensure no regressions
- [x] 8.4 Update `README.md` to document new processor workflow and output format
- [x] 8.5 Update `plan.md` if applicable (no changes needed - plan describes original goals)

## 9. Manual Quality Inspection

- [x] 9.1 Run test flow on `test_1.docx` with all three processors (python-docx, markdownit, mineru)
- [x] 9.2 Verify Markdown output is human-readable and well-formatted
- [x] 9.3 Verify `resources.json` contains correct mappings for all placeholder IDs
- [x] 9.4 Verify images are correctly extracted and saved to `resources/images/`
- [x] 9.5 Verify XML placeholders in Markdown can be resolved using `resources.json` for lossless recovery
