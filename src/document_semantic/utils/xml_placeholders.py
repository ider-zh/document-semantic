"""XML placeholder utilities for Markdown output.

Generates XML-style placeholders for special elements (formulas, code, images)
in Markdown output. Block-level elements use self-closing tags, while inline
elements preserve the original content within the tags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ResourceType(str, Enum):
    """Supported resource types for XML placeholders."""

    FORMULA = "formula"
    CODE = "code"
    IMAGE = "image"


class PositionType(str, Enum):
    """Whether a placeholder is block-level or inline."""

    BLOCK = "block"
    INLINE = "inline"


@dataclass
class PlaceholderIdCounter:
    """Manages sequential IDs per resource type.

    IDs start at 1 and increment per resource type within a document.
    """

    _counters: dict[ResourceType, int] = field(default_factory=dict)

    def next_id(self, resource_type: ResourceType) -> int:
        """Get the next sequential ID for the given resource type."""
        current = self._counters.get(resource_type, 0) + 1
        self._counters[resource_type] = current
        return current

    def get_count(self, resource_type: ResourceType) -> int:
        """Get the current count for a resource type (0 if none used yet)."""
        return self._counters.get(resource_type, 0)


def block_placeholder(resource_type: ResourceType, resource_id: int) -> str:
    """Generate a block-level self-closing XML placeholder.

    Examples:
        <formula id="1"/>
        <code id="1"/>
        <image id="1"/>
    """
    return f"<{resource_type.value} id=\"{resource_id}\"/>"


def inline_placeholder(
    resource_type: ResourceType, resource_id: int, content: str
) -> str:
    """Generate an inline XML placeholder with preserved original content.

    Examples:
        <formula id="1">E = mc^2</formula>
        <code id="1">print("hello")</code>
    """
    return f"<{resource_type.value} id=\"{resource_id}\">{content}</{resource_type.value}>"


def format_block_placeholder(
    resource_type: ResourceType, resource_id: int, newline: bool = True
) -> str:
    """Format a block placeholder, optionally with surrounding newlines.

    When newline=True, the placeholder occupies its own line with blank lines
    around it for proper Markdown paragraph separation.
    """
    placeholder = block_placeholder(resource_type, resource_id)
    if newline:
        return f"\n{placeholder}\n"
    return placeholder
