## ADDED Requirements

### Requirement: Test flow produces three output files
The `test_docx_flow` test SHALL, by default, produce three output artifacts for each processor configuration:
1. A Markdown file (`.md`)
2. A resource directory (`resources/`) with images
3. A JSON mapping file (`resources.json`)

These outputs SHALL be written to a test output directory (e.g., `tests/docx/output/<docx_name>_<processor>/`) for manual quality inspection.

#### Scenario: Test run produces all outputs
- **WHEN** `test_docx_flow` is executed with a DOCX file and processor configuration
- **THEN** the output directory contains `.md`, `resources/`, and `resources.json` files

### Requirement: Test flow output directory cleanup
Before each test run, the output directory for that test case SHALL be cleared to ensure fresh outputs. The output directory SHALL be `.gitignore`d.

#### Scenario: Output directory cleared before test
- **WHEN** `test_docx_flow` runs for `test_1.docx` with `python-docx` processor
- **THEN** any previous outputs in `tests/docx/output/test_1_python-docx/` are removed before new outputs are written

### Requirement: Test flow configuration
The test flow SHALL be configurable via route YAML to control output generation:
- `output_markdown`: Whether to produce Markdown (default: true)
- `output_resources`: Whether to produce resource directory (default: true)
- `output_json_mapping`: Whether to produce JSON mapping (default: true)

#### Scenario: Route YAML disables resource output
- **WHEN** a route has `output_resources: false`
- **THEN** the test does not create a `resources/` directory for that processor
