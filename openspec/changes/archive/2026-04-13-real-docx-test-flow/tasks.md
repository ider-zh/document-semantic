## 1. Routing Infrastructure

- [x] 1.1 Create `src/document_semantic/testing/__init__.py` with public exports
- [x] 1.2 Create `src/document_semantic/testing/routing.py` with `TestFlow`, `ProcessorConfig`, and `SemanticToolConfig` dataclasses
- [x] 1.3 Implement `load_routes(routes_path: Path) -> dict[str, TestFlow]` that parses the YAML route file and resolves glob patterns
- [x] 1.4 Implement `resolve_route(docx_filename: str, routes: dict) -> TestFlow` with exact-match precedence over glob patterns
- [x] 1.5 Implement route validation: verify all parser names exist in `ParserRegistry` and recognizer names are valid
- [x] 1.6 Create `tests/docx/test_routes.yaml` with an initial route for `test_1.docx` (python-docx parser + regex recognizer)

## 2. Assertion Framework

- [x] 2.1 Create `src/document_semantic/testing/assertions.py` with block-level assertion helpers: `assert_block_count`, `assert_block_types`, `assert_block_content_contains`
- [x] 2.2 Implement inline element assertion helpers: `assert_inline_element_count`, `assert_inline_element_text`
- [x] 2.3 Implement `load_expected_output(yaml_path: Path) -> dict` for loading expected output from YAML fixtures
- [x] 2.4 Implement partial assertion mode: `assert_document_partial(actual: SemanticDocument, expected: dict)` that validates only specified fields
- [x] 2.5 Create `tests/docx/expected/test_1_python-docx.yaml` with expected output for `test_1.docx` processed by python-docx parser + regex recognizer

## 3. Test Suite Implementation

- [x] 3.1 Create `tests/docx/conftest.py` with fixtures: `docx_dir`, `routes`, `expected_output_loader`
- [x] 3.2 Create `tests/test_docx_flow.py` with parameterized test that iterates over (docx_file, processor) pairs
- [x] 3.3 Implement test body: instantiate pipeline from route config, run parser + recognizer, run semantic tools, run assertions
- [x] 3.4 Implement result collection: gather SemanticDocument output, trace info, assertion results per processor
- [x] 3.5 Add clear failure messages showing file name, processor, and expected vs actual diffs

## 4. Makefile and Integration

- [x] 4.1 Add `test-docx` target to Makefile running `pytest tests/test_docx_flow.py`
- [x] 4.2 Add `test-docx-single` target accepting `FILE` variable for single-file test execution
- [x] 4.3 Run `make test-docx` and verify `test_1.docx` processes correctly with the initial route
- [x] 4.4 Verify that adding a new DOCX file + route entry causes it to appear in the next test run
