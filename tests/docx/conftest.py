"""Fixtures for real DOCX test flow tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from document_semantic.utils.testing.routing import TestFlow, load_routes, resolve_route

DOCX_DIR = Path(__file__).parent
ROUTES_FILE = DOCX_DIR / "test_routes.yaml"


@pytest.fixture
def docx_dir() -> Path:
    """Return the tests/docx/ directory path."""
    return DOCX_DIR


@pytest.fixture
def routes() -> dict[str, TestFlow]:
    """Load and return all test routes from test_routes.yaml."""
    return load_routes(ROUTES_FILE)


@pytest.fixture
def expected_output_loader():
    """Return a callable that loads expected output from a YAML path."""

    def _load(yaml_path: Path) -> dict[str, Any]:
        if not yaml_path.exists():
            return {}
        with open(yaml_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    return _load


@pytest.fixture
def route_resolver(routes: dict[str, TestFlow]):
    """Return a callable that resolves a filename to its TestFlow."""

    def _resolve(docx_filename: str) -> TestFlow:
        return resolve_route(docx_filename, routes)

    return _resolve
