## 1. Update test routes configuration

- [x] 1.1 Add pandoc processor entry for `test_1.docx` in `tests/docx/test_routes.yaml` with `parser: pandoc`, `recognizer: regex`, `skip_if_no_pandoc: true`, and `expected_output_path: expected/test_1_pandoc.yaml`
- [x] 1.2 Add pandoc processor entry for `test_2.docx` in `tests/docx/test_routes.yaml` with `parser: pandoc`, `recognizer: regex`, `skip_if_no_pandoc: true`, and `expected_output_path: expected/test_2_pandoc.yaml`

## 2. Generate expected output fixtures

- [x] 2.1 Run pandoc parser against `test_1.docx` to produce intermediate result and regex recognition output
- [x] 2.2 Create `tests/docx/expected/test_1_pandoc.yaml` with the expected semantic document output (block types, inline elements, metadata)
- [x] 2.3 Run pandoc parser against `test_2.docx` to produce intermediate result and regex recognition output
- [x] 2.4 Create `tests/docx/expected/test_2_pandoc.yaml` with the expected semantic document output

## 3. Verify test execution

- [x] 3.1 Run `pytest tests/test_docx_flow.py -v` and verify pandoc test cases appear (PASSED or SKIPPED)
- [x] 3.2 Verify test output includes readable test IDs like `test_1.docx-pandoc_regex`
- [x] 3.3 Verify pandoc tests are skipped gracefully when pandoc binary is unavailable (confirm `skip_if_no_pandoc` behavior)
- [x] 3.4 Fix any assertion mismatches between expected YAML and actual pandoc output

## 4. Clean up and lint

- [x] 4.1 Run `make lint` to check code style
- [x] 4.2 Run `make test-docx` to confirm full DOCX test suite passes
