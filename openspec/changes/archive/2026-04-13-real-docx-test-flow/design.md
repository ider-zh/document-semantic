## Context

The project has a fully functional document parsing pipeline (Parser → Recognizer → SemanticDocument) with synthetic test fixtures generated programmatically. A real DOCX file (`tests/docx/test_1.docx`, 131KB) exists but is not exercised by any test. The current test suite validates structure but lacks: (1) a mechanism to route each DOCX file through different processor combinations, (2) a way to define and assert expected outputs per file, and (3) a flow to test semantic recognition tools and validate their output.

The existing architecture provides: `Parser` ABC + `ParserRegistry`, `SemanticRecognizer` ABC + `RouterRecognizer`, and `Pipeline` that wires them together. The `testing/` module is an empty placeholder.

## Goals / Non-Goals

**Goals:**
- Provide a per-DOCX routing configuration that selects which parser(s), recognizer(s), and semantic tools to run
- Enable expected-output assertions: compare actual pipeline output against user-defined expectations
- Support a test flow where a single DOCX file can be processed by multiple processors, each with its own assertions
- Allow adding new DOCX files by simply placing them in `tests/docx/` and adding a routing entry
- Integrate with pytest as parameterized tests for easy `pytest` execution

**Non-Goals:**
- Not a production feature — this is purely a testing infrastructure addition
- Not modifying the core Pipeline API — routing and assertions wrap the existing pipeline, not replace it
- Not auto-generating expected outputs — users define expectations manually (snapshot update can assist but is not automatic)
- Not a benchmarking tool — focus is correctness, not performance

## Decisions

### Decision 1: YAML-based test route configuration

**Choice:** Use a single `tests/docx/test_routes.yaml` file to define per-document test flows.

**Rationale:** YAML is already used for pipeline configuration in this project. It's readable, supports complex nested structures (processor lists, assertions), and is easy to edit.

**Alternatives considered:**
- Python conftest fixtures: more programmatic but less declarative and harder to scan
- JSON: less readable, no comments
- Per-file sidecar YAMLs: too scattered; a single file is easier to maintain for small-to-medium test suites

### Decision 2: TestFlow dataclass over separate classes

**Choice:** Create a single `TestFlow` dataclass in `src/document_semantic/testing/routing.py` that encapsulates: docx filename, list of processor configs (each with parser name + recognizer name), list of semantic tool configs, and expected assertions.

**Rationale:** Keeps the routing model simple and serializable. A dataclass is easy to load from YAML via `pyyaml` and provides clear structure.

**Alternatives considered:**
- Separate classes for ProcessorConfig, AssertionConfig, etc.: more modular but adds indirection for a testing-only feature
- Pydantic models: consistent with project models but adds validation overhead unnecessary for test config

### Decision 3: Assertion framework using dict comparison

**Choice:** Assertions compare deserialized dict representations of `SemanticDocument` (via `model.model_dump()`) against expected dicts loaded from YAML. Field-level assertions (e.g., "block count", "block types in order") are implemented as helper functions.

**Rationale:** Pydantic models have `model_dump()` built-in. Dict comparison is straightforward and produces readable diff output on failure. Field-level helpers give concise assertions for common checks (block count, types).

**Alternatives considered:**
- Full JSON fixture comparison: too rigid for real documents where minor ordering/formatting differences are acceptable
- Pytest snapshot: useful for regression but not for explicit expected-output validation
- Custom assertion DSL: overkill for this scope

### Decision 4: Parameterized pytest test iterates over test routes

**Choice:** A single `test_docx_flow.py` with `@pytest.mark.parametrize` reads all routes from `test_routes.yaml` and executes each flow. Each route produces sub-results for each processor.

**Rationale:** One test file is simple to discover and run. Parametrization gives one line per route in pytest output. Sub-results are reported via pytest's nested test names.

**Alternatives considered:**
- One test function per DOCX: too much boilerplate, hard to scale
- Dynamic test generation via pytest_generate_tests: more complex, less transparent

### Decision 5: Semantic tool selection as recognizer extension

**Choice:** "Semantic tools" in the routing config map to recognizer instances. The router recognizer already supports dispatching to sub-recognizers. The test flow configures which recognizers to invoke per processor output.

**Rationale:** The existing `RouterRecognizer` already handles multi-recognizer dispatch. Reusing it avoids building a parallel mechanism. Test flows can configure the router's sub-recognizers and rules per test case.

## Risks / Trade-offs

- **[Risk]** Real DOCX files may have non-deterministic elements (timestamps, image extraction paths) causing flaky assertions → **Mitigation:** Assertions focus on stable properties (block count, types, key content) rather than exact dict equality. Provide "contains" and "count" assertion modes.

- **[Risk]** Test routes YAML grows unmanageably as more DOCX files are added → **Mitigation:** Support glob patterns in route keys (e.g., `test_*.docx`) to apply shared config to multiple files. Keep per-file overrides minimal.

- **[Risk]** Multiple processors per file multiplies test execution time → **Mitigation:** Processors run sequentially in a single test. Future optimization can parallelize, but correctness is the priority. Individual processors can be selected via pytest markers.

- **[Trade-off]** Dict comparison over exact JSON fixtures sacrifices some precision for flexibility → **Acceptable** because real DOCX output may have minor variations (e.g., whitespace) that shouldn't cause failures.

## Migration Plan

No migration needed — this is additive test infrastructure. Existing tests continue to run unchanged. To adopt:
1. Add DOCX files to `tests/docx/`
2. Add routing entries to `tests/docx/test_routes.yaml`
3. Run `pytest tests/test_docx_flow.py`

## Open Questions

- Should the test flow support LLM-based recognizers when they are implemented? → **Deferred:** The routing config is extensible; LLM recognizer support can be added when the recognizer itself is implemented.
- Should there be a CLI command to scaffold a new test route? → **Deferred:** Can be added later; initial users can edit YAML directly.
