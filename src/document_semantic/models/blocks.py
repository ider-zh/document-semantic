"""Block-level semantic data models."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from .inline_elements import InlineElement


class BaseBlock(BaseModel):
    """Base class for all block-level semantic elements."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique block identifier")
    type: str = Field(..., description="Block type discriminator")
    content: str = Field(..., description="The text content of this block")
    inline_elements: list[InlineElement] = Field(
        default_factory=list, description="Recognized inline elements within this block"
    )


class TitleBlock(BaseBlock):
    """Document title block."""

    type: Literal["title"] = "title"


class HeadingBlock(BaseBlock):
    """Heading block with level 1-6."""

    type: Literal["heading"] = "heading"
    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")


class TextBlock(BaseBlock):
    """Standard paragraph text."""

    type: Literal["text"] = "text"


class AbstractBlock(BaseBlock):
    """Document abstract/summary section."""

    type: Literal["abstract"] = "abstract"


class AbstractHeadBlock(BaseBlock):
    """Heading for the abstract section."""

    type: Literal["abstract_head"] = "abstract_head"
    level: int = Field(default=1, ge=1, le=6, description="Heading level")


class ConclusionBlock(BaseBlock):
    """Document conclusion section."""

    type: Literal["conclusion"] = "conclusion"


class ConclusionHeadBlock(BaseBlock):
    """Heading for the conclusion section."""

    type: Literal["conclusion_head"] = "conclusion_head"
    level: int = Field(default=1, ge=1, le=6, description="Heading level")


class ReferenceBlock(BaseBlock):
    """Reference/bibliography entry."""

    type: Literal["reference"] = "reference"


class ReferenceHeadBlock(BaseBlock):
    """Heading for the references section."""

    type: Literal["reference_head"] = "reference_head"
    level: int = Field(default=1, ge=1, le=6, description="Heading level")


class ListItemBlock(BaseBlock):
    """List item (ordered or unordered)."""

    type: Literal["list_item"] = "list_item"
    list_type: Literal["ordered", "unordered"] = Field(
        default="unordered", description="Whether this is from an ordered or unordered list"
    )
    indent_level: int = Field(default=0, ge=0, description="Nesting depth of the list item")


class TableBlock(BaseBlock):
    """Table with rows and columns."""

    type: Literal["table"] = "table"
    headers: list[str] = Field(default_factory=list, description="Column header labels")
    rows: list[list[str]] = Field(default_factory=list, description="Table cell content as 2D array")


class CodeBlock(BaseBlock):
    """Code block (multi-line code)."""

    type: Literal["code_block"] = "code_block"
    language: str | None = Field(default=None, description="Programming language hint")


class ImageBlock(BaseBlock):
    """Image block."""

    type: Literal["image"] = "image"


class ImageDescriptionBlock(BaseBlock):
    """Text describing an image."""

    type: Literal["image_description"] = "image_description"


class TableDescriptionBlock(BaseBlock):
    """Text describing a table."""

    type: Literal["table_description"] = "table_description"


# Discriminated union of all block types
Block = Annotated[
    TitleBlock
    | HeadingBlock
    | TextBlock
    | AbstractBlock
    | AbstractHeadBlock
    | ConclusionBlock
    | ConclusionHeadBlock
    | ReferenceBlock
    | ReferenceHeadBlock
    | ListItemBlock
    | TableBlock
    | CodeBlock
    | ImageBlock
    | ImageDescriptionBlock
    | TableDescriptionBlock,
    Field(discriminator="type"),
]

__all__ = [
    "BaseBlock",
    "TitleBlock",
    "HeadingBlock",
    "TextBlock",
    "AbstractBlock",
    "AbstractHeadBlock",
    "ConclusionBlock",
    "ConclusionHeadBlock",
    "ReferenceBlock",
    "ReferenceHeadBlock",
    "ListItemBlock",
    "TableBlock",
    "CodeBlock",
    "ImageBlock",
    "ImageDescriptionBlock",
    "TableDescriptionBlock",
    "Block",
]
