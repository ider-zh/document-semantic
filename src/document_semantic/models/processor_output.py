"""Processor output models for the new processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ProcessorConfig:
    """Configuration for processor output generation."""

    output_markdown: bool = True
    """Whether to produce Markdown output."""

    output_resources: bool = True
    """Whether to produce resource directory with images."""

    output_json_mapping: bool = True
    """Whether to produce resources.json mapping file."""

    use_xml_placeholders: bool = True
    """Whether to use XML placeholders in Markdown output."""


@dataclass
class ResourceEntry:
    """A single resource entry in the mapping file."""

    entry_type: str  # "formula", "code", "image"
    content: str | None = None  # For inline resources (formula, code)
    file_path: str | None = None  # For binary resources (images)
    position_type: str = "block"  # "block" or "inline"
    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata (language for code, dimensions for images, etc.)."""


@dataclass
class ProcessResult:
    """Result returned by a parser's process() method."""

    rich_markdown_path: Path | None = None
    """Path to the rich Markdown file with full content (formulas, code, images in markdown format)."""

    placeholder_markdown_path: Path | None = None
    """Path to the placeholder Markdown file with XML tags replacing special elements."""

    resources_dir: Path | None = None
    """Path to the resources directory."""

    resources_json_path: Path | None = None
    """Path to the resources.json mapping file."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Document-level metadata and processing info."""

    @property
    def markdown_path(self) -> Path | None:
        """Alias for placeholder_markdown_path for backward compatibility."""
        return self.placeholder_markdown_path

    @property
    def output_dir(self) -> Path | None:
        """Return the output directory containing all artifacts."""
        if self.placeholder_markdown_path:
            return self.placeholder_markdown_path.parent
        if self.rich_markdown_path:
            return self.rich_markdown_path.parent
        if self.resources_dir:
            return self.resources_dir.parent
        if self.resources_json_path:
            return self.resources_json_path.parent
        return None
