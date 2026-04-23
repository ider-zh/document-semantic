"""Test route configuration and routing for real DOCX test flows.

Provides dataclasses and functions to load per-document test route
configurations from YAML, resolve routes by filename (with glob support),
and validate that referenced parsers and recognizers are registered.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from document_semantic.agents.router_and_llm import (
    _RECOGNIZER_REGISTRY,
)
from document_semantic.core.logger import get_logger
from document_semantic.services.parsers.registry import ParserRegistry

logger = get_logger(__name__)


@dataclass
class SemanticToolConfig:
    """Configuration for a semantic tool (recognizer) to run on processor output."""

    tool_type: str = "recognizer"
    recognizer_name: str = "regex"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessorConfig:
    """Configuration for a single processor in a test flow."""

    parser: str = "python-docx"
    recognizer: str = "regex"
    semantic_tools: list[SemanticToolConfig] = field(default_factory=list)
    skip_if_no_pandoc: bool = False
    skip_if_no_token: bool = False
    skip_image_ocr: bool = False
    expected_output_path: str | None = None
    # Output generation settings (default to True for manual inspection)
    output_markdown: bool = True
    output_resources: bool = True
    output_json_mapping: bool = True


@dataclass
class DocxTestFlow:
    """Complete test flow configuration for a DOCX file.

    A test flow defines which processors to run against a document,
    what assertions to apply, and what expected output to compare against.
    """

    docx_filename: str
    processors: list[ProcessorConfig]
    expected_output_path: str | None = None
    assertion_mode: str = "partial"  # "partial" or "full"


# Alias for backwards compatibility and cleaner import name
TestFlow = DocxTestFlow


def load_routes(routes_path: Path) -> dict[str, TestFlow]:
    """Load test route definitions from a YAML file.

    Parses the YAML and creates TestFlow instances keyed by their
    docx_filename. Glob patterns in keys are preserved for later resolution.

    Args:
        routes_path: Path to the test_routes.yaml file.

    Returns:
        Dictionary mapping docx filename (or glob pattern) to TestFlow.
    """
    if not routes_path.exists():
        logger.warning(f"Route file not found: {routes_path}, returning empty routes")
        return {}

    with open(routes_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f) or {}

    routes: dict[str, TestFlow] = {}
    for key, value in raw.items():
        processors = _parse_processors(value.get("processors", []))
        expected_output_path = value.get("expected_output_path")
        assertion_mode = value.get("assertion_mode", "partial")

        flow = TestFlow(
            docx_filename=key,
            processors=processors,
            expected_output_path=expected_output_path,
            assertion_mode=assertion_mode,
        )
        routes[key] = flow
        logger.info(f"Loaded route: {key} ({len(processors)} processor(s))")

    return routes


def resolve_route(docx_filename: str, routes: dict[str, TestFlow]) -> TestFlow:
    """Resolve the test route for a given DOCX filename.

    Exact filename matches take precedence over glob patterns.
    Among glob matches, the first defined glob is used.

    Args:
        docx_filename: The DOCX filename to resolve (e.g., "test_1.docx").
        routes: Dictionary of routes keyed by filename or glob pattern.

    Returns:
        The matched TestFlow.

    Raises:
        ValueError: If no route matches the filename.
    """
    # Exact match first
    if docx_filename in routes:
        return routes[docx_filename]

    # Glob pattern match
    for pattern, flow in routes.items():
        if fnmatch.fnmatch(docx_filename, pattern):
            logger.info(f"Route for '{docx_filename}' matched glob pattern '{pattern}'")
            return flow

    raise ValueError(f"No route found for '{docx_filename}'. Available routes: {', '.join(routes.keys())}")


def validate_route(route: TestFlow) -> list[str]:
    """Validate that all parser and recognizer names in a route are registered.

    Args:
        route: The TestFlow to validate.

    Returns:
        List of error messages (empty if valid).
    """
    errors: list[str] = []
    available_parsers = ParserRegistry.available()
    available_recognizers = list(_RECOGNIZER_REGISTRY.keys())

    for i, proc in enumerate(route.processors):
        if not ParserRegistry.has(proc.parser):
            errors.append(f"Processor {i}: unknown parser '{proc.parser}'. Available: {', '.join(available_parsers)}")
        if proc.recognizer not in available_recognizers:
            errors.append(
                f"Processor {i}: unknown recognizer '{proc.recognizer}'. Available: {', '.join(available_recognizers)}"
            )
        for j, tool in enumerate(proc.semantic_tools):
            if tool.tool_type == "recognizer" and tool.recognizer_name not in available_recognizers:
                errors.append(
                    f"Processor {i}, semantic tool {j}: unknown recognizer "
                    f"'{tool.recognizer_name}'. Available: "
                    f"{', '.join(available_recognizers)}"
                )

    if not errors:
        logger.info(f"Route '{route.docx_filename}' validated OK")
    return errors


def _parse_processors(raw: list[Any]) -> list[ProcessorConfig]:
    """Parse processor definitions from raw YAML data."""
    processors = []
    for item in raw:
        if isinstance(item, str):
            # Shorthand: just a parser name
            processors.append(ProcessorConfig(parser=item))
        elif isinstance(item, dict):
            tools = []
            for tool_def in item.get("semantic_tools", []):
                if isinstance(tool_def, str):
                    tools.append(SemanticToolConfig(recognizer_name=tool_def))
                elif isinstance(tool_def, dict):
                    tools.append(
                        SemanticToolConfig(
                            tool_type=tool_def.get("tool_type", "recognizer"),
                            recognizer_name=tool_def.get("recognizer_name", "regex"),
                            params=tool_def.get("params", {}),
                        )
                    )
            processors.append(
                ProcessorConfig(
                    parser=item.get("parser", "python-docx"),
                    recognizer=item.get("recognizer", "regex"),
                    semantic_tools=tools,
                    skip_if_no_pandoc=item.get("skip_if_no_pandoc", False),
                    skip_if_no_token=item.get("skip_if_no_token", False),
                    skip_image_ocr=item.get("skip_image_ocr", False),
                    expected_output_path=item.get("expected_output_path"),
                    output_markdown=item.get("output_markdown", True),
                    output_resources=item.get("output_resources", True),
                    output_json_mapping=item.get("output_json_mapping", True),
                )
            )
    return processors
