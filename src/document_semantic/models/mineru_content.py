from __future__ import annotations

from typing import Any, List, Optional, Union, Dict
from pydantic import BaseModel, Field, RootModel


class MinerUInlineContent(BaseModel):
    """Represents inline elements like text or inline equations."""
    type: str
    content: str
    model_config = {"extra": "allow"}


class MinerUImageSource(BaseModel):
    """Source information for images or formulas."""
    path: str
    model_config = {"extra": "allow"}


class MinerUTitleContent(BaseModel):
    """Content for title/heading elements."""
    title_content: Optional[List[MinerUInlineContent]] = None
    level: int = 1
    model_config = {"extra": "allow"}


class MinerUParagraphContent(BaseModel):
    """Content for standard paragraphs."""
    paragraph_content: Optional[List[MinerUInlineContent]] = None
    model_config = {"extra": "allow"}


class MinerUImageContent(BaseModel):
    """Content for images and figures."""
    image_source: Optional[MinerUImageSource] = None
    image_caption: Optional[List[MinerUInlineContent]] = Field(default_factory=list)
    image_footnote: Optional[List[MinerUInlineContent]] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class MinerUListItem(BaseModel):
    """A single item within a list."""
    item_type: str
    item_content: List[MinerUInlineContent]
    model_config = {"extra": "allow"}


class MinerUListContent(BaseModel):
    """Content for lists (bulleted, numbered, references)."""
    list_type: str
    list_items: List[MinerUListItem]
    model_config = {"extra": "allow"}


class MinerUEquationInterlineContent(BaseModel):
    """Content for block-level equations."""
    math_content: str
    math_type: str = "latex"
    image_source: Optional[MinerUImageSource] = None
    model_config = {"extra": "allow"}


class MinerUAlgorithmContent(BaseModel):
    """Content for algorithms and code blocks."""
    algorithm_caption: List[MinerUInlineContent] = Field(default_factory=list)
    algorithm_content: List[MinerUInlineContent] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class MinerUTableContent(BaseModel):
    """Content for tables (can be complex, often contains list of rows or HTML)."""

    # Table structure can vary significantly in MinerU,
    # using a flexible dict to allow extensions.
    table_content: Optional[Union[str, List[Any], Dict[str, Any]]] = None
    html: Optional[str] = None
    model_config = {"extra": "allow"}


class MinerUGenericContent(BaseModel):
    """Generic content container for simple elements."""
    content: Union[str, List[MinerUInlineContent], Dict[str, Any]]
    model_config = {"extra": "allow"}


class MinerUElement(BaseModel):
    """A top-level element in the content_list.json."""

    type: str
    content: Union[
        MinerUTitleContent,
        MinerUParagraphContent,
        MinerUImageContent,
        MinerUListContent,
        MinerUEquationInterlineContent,
        MinerUAlgorithmContent,
        MinerUTableContent,
        MinerUGenericContent,
        Dict[str, Any],  # Final fallback
    ]
    model_config = {"extra": "allow"}


class MinerUContentList(RootModel):
    """The root structure of content_list.json."""
    root: List[MinerUElement]

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def __len__(self):
        return len(self.root)
