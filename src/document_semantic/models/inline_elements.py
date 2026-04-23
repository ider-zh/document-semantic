"""Inline-level semantic element models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseInlineElement(BaseModel):
    """Base class for all inline semantic elements."""

    model_config = ConfigDict(frozen=True)

    type: str = Field(..., description="Element type discriminator")
    text: str = Field(..., description="The raw text content of this element")
    start_offset: int = Field(..., ge=0, description="Character offset where this element starts in the parent block")
    end_offset: int = Field(..., ge=0, description="Character offset where this element ends in the parent block")


class BoldInlineElement(BaseInlineElement):
    """Bold formatted text span."""

    type: Literal["bold"] = "bold"


class ItalicInlineElement(BaseInlineElement):
    """Italic formatted text span."""

    type: Literal["italic"] = "italic"


class StrikethroughInlineElement(BaseInlineElement):
    """Strikethrough formatted text span."""

    type: Literal["strikethrough"] = "strikethrough"


class FormulaInlineElement(BaseInlineElement):
    """Inline mathematical formula (e.g., $E=mc^2$)."""

    type: Literal["formula"] = "formula"


class CodeSpanInlineElement(BaseInlineElement):
    """Inline code span (e.g., `code`)."""

    type: Literal["code_span"] = "code_span"


class LinkInlineElement(BaseInlineElement):
    """Hyperlink with display text and URL."""

    type: Literal["link"] = "link"
    url: str = Field(..., description="The target URL of the link")


# Discriminated union of all inline element types
InlineElement = (
    BoldInlineElement
    | ItalicInlineElement
    | StrikethroughInlineElement
    | FormulaInlineElement
    | CodeSpanInlineElement
    | LinkInlineElement
)

__all__ = [
    "BaseInlineElement",
    "BoldInlineElement",
    "ItalicInlineElement",
    "StrikethroughInlineElement",
    "FormulaInlineElement",
    "CodeSpanInlineElement",
    "LinkInlineElement",
    "InlineElement",
]
