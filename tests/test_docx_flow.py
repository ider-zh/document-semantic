"""Parameterized tests for real DOCX test flows.

Iterates over (docx_file, processor) pairs defined in test_routes.yaml,
executes the pipeline, runs semantic tools, and asserts against expected output.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest

from document_semantic.models.semantic_document import SemanticDocument
from document_semantic.parsers.protocol import (
    IntermediateResult,
    ParserDependencyError,
)
from document_semantic.pipeline import Pipeline, PipelineConfig
from document_semantic.pipeline.pipeline import PipelineTrace
from document_semantic.recognizers.protocol import SemanticRecognizer
from document_semantic.recognizers.router_and_llm import create_recognizer
from document_semantic.testing.assertions import (
    assert_document_partial,
    load_expected_output,
)
from document_semantic.testing.routing import (
    ProcessorConfig,
    TestFlow,
    load_routes,
    resolve_route,
    validate_route,
)

DOCX_DIR = Path(__file__).parent / "docx"
ROUTES_FILE = DOCX_DIR / "test_routes.yaml"


def _collect_test_params():
    """Collect all (docx_path, processor_config, expected_output_path, assertion_mode) tuples."""
    routes = load_routes(ROUTES_FILE)
    if not routes:
        return []

    params = []
    for route_key, flow in routes.items():
        # Validation errors
        errors = validate_route(flow)
        if errors:
            # Still add but mark for skip
            for proc in flow.processors:
                params.append((flow, proc, None, True))
            continue

        # Discover docx files matching the route key
        import fnmatch

        docx_files = []
        if "*" in route_key or "?" in route_key:
            docx_files = [
                p for p in DOCX_DIR.glob("*.docx")
                if fnmatch.fnmatch(p.name, route_key)
            ]
        else:
            docx_path = DOCX_DIR / route_key
            if docx_path.exists():
                docx_files = [docx_path]

        for docx_path in docx_files:
            for proc in flow.processors:
                # Per-processor expected output path, fallback to flow-level
                proc_expected = proc.expected_output_path or flow.expected_output_path
                expected_path = None
                has_assertions = False
                if proc_expected:
                    expected_path = DOCX_DIR / proc_expected
                    if expected_path.exists():
                        has_assertions = True
                    else:
                        expected_path = None

                params.append((
                    flow,
                    proc,
                    expected_path,
                    has_assertions,
                    docx_path,
                ))

    return params


def _build_pipeline(proc: ProcessorConfig) -> Pipeline:
    """Build a Pipeline from a processor config."""
    config = PipelineConfig(
        parser=proc.parser,
        recognizer=proc.recognizer,
        verbosity="summary",
    )
    return Pipeline.from_config(config)


def _run_semantic_tools(
    intermediate: IntermediateResult,
    tools: list,
) -> list[SemanticDocument]:
    """Run semantic tools from the processor config and collect results."""
    from document_semantic.testing.routing import SemanticToolConfig

    results = []
    for tool_config in tools:
        if isinstance(tool_config, SemanticToolConfig):
            if tool_config.tool_type == "recognizer":
                recognizer = create_recognizer(
                    tool_config.recognizer_name, tool_config.params
                )
                result = recognizer.recognize(intermediate)
                results.append(result)
    return results


def _run_processor(
    docx_path: Path, proc: ProcessorConfig
) -> dict[str, Any]:
    """Run a single processor configuration against a DOCX file.

    Returns a dict with: output (SemanticDocument), trace (PipelineTrace),
    tool_results (list), and errors (list).
    """
    errors = []
    tool_results = []

    try:
        pipeline = _build_pipeline(proc)
        semantic_doc = pipeline.run(docx_path)
        trace = pipeline.get_trace()

        # Run semantic tools on the intermediate result
        # We need to re-parse to get intermediate for tools
        from document_semantic.parsers.registry import ParserRegistry

        parser = ParserRegistry.get(proc.parser)
        intermediate = parser.parse(docx_path)
        tool_results = _run_semantic_tools(intermediate, proc.semantic_tools)

        return {
            "output": semantic_doc,
            "trace": trace,
            "tool_results": tool_results,
            "errors": errors,
        }
    except Exception as e:
        errors.append(str(e))
        return {
            "output": None,
            "trace": None,
            "tool_results": [],
            "errors": errors,
        }


# Build test parameters
_TEST_PARAMS = _collect_test_params()


def _make_test_id(param):
    """Create a readable test ID from a test parameter tuple."""
    flow, proc, expected_path, has_assertions, docx_path = param
    proc_label = f"{proc.parser}_{proc.recognizer}"
    return f"{docx_path.name}-{proc_label}"


def _pandoc_available() -> bool:
    """Check if pandoc binary is on PATH."""
    return shutil.which("pandoc") is not None


def _mineru_token_available() -> bool:
    """Check if MinerU API token is configured."""
    import os
    return bool(os.getenv("MINERU_TOKEN") or os.getenv("token_mineru"))


@pytest.mark.parametrize(
    "flow,proc,expected_path,has_assertions,docx_path",
    _TEST_PARAMS,
    ids=[_make_test_id(p) for p in _TEST_PARAMS],
)
def test_docx_flow(flow, proc, expected_path, has_assertions, docx_path):
    """Run a single (docx_file, processor) test flow.

    Executes the pipeline, collects results, and asserts against expected output
    if available.
    """
    # Skip if processor requires pandoc but it's not available
    if proc.skip_if_no_pandoc and not _pandoc_available():
        pytest.skip("pandoc is not installed; skipping processor")

    # Skip if processor requires MinerU token but it's not available
    if proc.skip_if_no_token and not _mineru_token_available():
        pytest.skip("MINERU_TOKEN is not configured; skipping processor")

    # Run the processor
    result = _run_processor(docx_path, proc)

    # Handle dependency errors gracefully
    if result["errors"]:
        # Check if it's a dependency error (skip) or real failure
        if any(
            "pandoc" in e.lower() or "markdown-it-py" in e.lower() or "mineru" in e.lower() or "token" in e.lower()
            for e in result["errors"]
        ):
            pytest.skip(f"Dependency not available: {'; '.join(result['errors'])}")
        error_msg = (
            f"Processor failed for {docx_path.name} with "
            f"parser={proc.parser}, recognizer={proc.recognizer}:\n"
            + "\n".join(result["errors"])
        )
        pytest.fail(error_msg)

    # Assert output is valid
    semantic_doc = result["output"]
    assert semantic_doc is not None, "Pipeline returned no output"
    assert isinstance(semantic_doc, SemanticDocument)

    # Run assertions if expected output is available
    if has_assertions and expected_path and expected_path.exists():
        expected = load_expected_output(expected_path)
        failures = assert_document_partial(semantic_doc, expected)

        if failures:
            failure_details = "\n".join(f"- {f}" for f in failures)
            pytest.fail(
                f"Assertion failures for {docx_path.name} "
                f"(parser={proc.parser}, recognizer={proc.recognizer}):\n"
                f"{failure_details}"
            )


def test_routes_load():
    """Verify that test_routes.yaml loads without errors."""
    routes = load_routes(ROUTES_FILE)
    assert len(routes) > 0, "No routes loaded from test_routes.yaml"


def test_routes_validation():
    """Verify that all routes pass validation."""
    routes = load_routes(ROUTES_FILE)
    all_errors = []
    for key, flow in routes.items():
        errors = validate_route(flow)
        if errors:
            all_errors.extend([f"[{key}] {e}" for e in errors])
    assert not all_errors, f"Route validation errors:\n" + "\n".join(all_errors)
