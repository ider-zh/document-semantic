"""Tests for document parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from document_semantic.core.exceptions import (
    ParserDependencyError,
    ParserNotFoundError,
)
from document_semantic.services.parsers.pandoc_parser import PandocParser
from document_semantic.services.parsers.protocol import IntermediateResult
from document_semantic.services.parsers.python_docx_parser import PythonDocxParser
from document_semantic.services.parsers.registry import ParserRegistry

# ---------------------------------------------------------------------------
# PythonDocxParser tests
# ---------------------------------------------------------------------------


class TestPythonDocxParser:
    """Tests for the python-docx parser."""

    def test_parse_simple_document(self, sample_docx_path: Path):
        """PythonDocxParser parses a simple document with blocks."""
        parser = PythonDocxParser()
        result = parser.parse(sample_docx_path)

        assert isinstance(result, IntermediateResult)
        assert len(result.blocks) > 0
        # Should have at least title and heading blocks
        block_contents = [b.content for b in result.blocks]
        assert any("Sample Document" in c for c in block_contents)
        assert any("Introduction" in c for c in block_contents)

    def test_parse_academic_document(self, academic_docx_path: Path):
        """PythonDocxParser extracts abstract and references."""
        parser = PythonDocxParser()
        result = parser.parse(academic_docx_path)

        assert len(result.blocks) > 0
        block_contents = [b.content for b in result.blocks]
        assert any("Abstract" in c for c in block_contents)
        assert any("References" in c for c in block_contents)

    def test_parse_table_document(self, table_docx_path: Path):
        """PythonDocxParser detects tables."""
        parser = PythonDocxParser()
        result = parser.parse(table_docx_path)

        # Should have table-related blocks
        table_blocks = [b for b in result.blocks if b.style_hint and "Table" in b.style_hint]
        assert len(table_blocks) > 0

    def test_parse_metadata(self, sample_docx_path: Path):
        """PythonDocxParser extracts document metadata."""
        parser = PythonDocxParser()
        result = parser.parse(sample_docx_path)

        assert isinstance(result.metadata, dict)
        assert "source_path" in result.metadata

    def test_parser_name(self):
        """PythonDocxParser returns correct name."""
        parser = PythonDocxParser()
        assert parser.name == "python-docx"


# ---------------------------------------------------------------------------
# PandocParser tests
# ---------------------------------------------------------------------------


class TestPandocParser:
    """Tests for the pandoc parser."""

    @pytest.mark.skipif(
        not __import__("shutil").which("pandoc"),
        reason="pandoc is not installed",
    )
    def test_parse_with_pandoc(self, sample_docx_path: Path):
        """PandocParser converts DOCX to markdown blocks."""
        parser = PandocParser()
        result = parser.parse(sample_docx_path)

        assert isinstance(result, IntermediateResult)
        assert len(result.blocks) > 0

    def test_pandoc_not_available_raises(self, monkeypatch):
        """PandocParser raises ParserDependencyError when pandoc missing."""
        monkeypatch.setattr("document_semantic.services.parsers.pandoc_parser._pandoc_available", lambda: False)
        parser = PandocParser()

        with pytest.raises(ParserDependencyError) as exc_info:
            parser.parse(Path("/fake/path.docx"))

        assert "pandoc" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# ParserRegistry tests
# ---------------------------------------------------------------------------


class TestParserRegistry:
    """Tests for the parser registry."""

    def test_get_registered_parser(self):
        """Registry returns python-docx parser by default."""
        assert ParserRegistry.has("python-docx")
        parser = ParserRegistry.get("python-docx")
        assert isinstance(parser, PythonDocxParser)

    def test_unknown_parser_raises(self):
        """Registry raises ParserNotFoundError for unknown name."""
        with pytest.raises(ParserNotFoundError) as exc_info:
            ParserRegistry.get("nonexistent-parser")

        assert "nonexistent-parser" in str(exc_info.value)
        assert "python-docx" in str(exc_info.value)  # Should list available

    def test_available_parsers(self):
        """Registry lists available parsers."""
        available = ParserRegistry.available()
        assert "python-docx" in available
