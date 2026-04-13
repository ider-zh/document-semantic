"""Testing utilities and fixtures for real DOCX test flows."""

from document_semantic.testing.assertions import (
    assert_block_content_contains,
    assert_block_count,
    assert_block_types,
    assert_document_partial,
    assert_inline_element_count,
    assert_inline_element_text,
    load_expected_output,
)
from document_semantic.testing.routing import (
    DocxTestFlow,
    ProcessorConfig,
    SemanticToolConfig,
    TestFlow,
    load_routes,
    resolve_route,
    validate_route,
)

__all__ = [
    "TestFlow",
    "DocxTestFlow",
    "ProcessorConfig",
    "SemanticToolConfig",
    "load_routes",
    "resolve_route",
    "validate_route",
    "assert_block_count",
    "assert_block_types",
    "assert_block_content_contains",
    "assert_inline_element_count",
    "assert_inline_element_text",
    "load_expected_output",
    "assert_document_partial",
]
