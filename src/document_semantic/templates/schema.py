from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class PageMargins(BaseModel):
    top: str = "25.4mm"
    bottom: str = "25.4mm"
    left: str = "31.7mm"
    right: str = "31.7mm"


class ColumnConfig(BaseModel):
    title_page: int = 1
    abstract_page: int = 1
    body: int = 1
    column_spacing: str = "12.7mm"


class PageConfig(BaseModel):
    width: str = "210mm"
    height: str = "297mm"
    orientation: str = "portrait"
    margins: PageMargins = Field(default_factory=PageMargins)
    columns: ColumnConfig = Field(default_factory=ColumnConfig)


class DocxStyleConfig(BaseModel):
    font: Optional[str] = None
    chinese_font: Optional[str] = None
    size: Optional[float] = None  # in pt
    bold: bool = False
    italic: bool = False
    align: str = "left"  # left, center, right, justified
    space_before: float = 0
    space_after: float = 0
    line_spacing: float = 1.0
    indent_first: float = 0  # in pt
    indent_left: float = 0
    text_transform: Optional[str] = None  # uppercase, lowercase
    model_config = {"extra": "allow"}


class SemanticTag(BaseModel):
    """Represents a valid semantic tag within a template."""
    name: str = Field(description="The machine-readable name of the tag (e.g., 'main_title')")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="Guidance for the Agent on when to apply this tag")
    is_required: bool = False


class SemanticTemplate(BaseModel):
    """Definition of a semantic style template (e.g., JCST, IEEE)."""
    id: str = Field(description="Template ID (e.g., 'jcst', 'ieee')")
    name: str
    description: str
    tags: List[SemanticTag]
    
    # Layout and Style Configuration (inspired by docx_build_cli)
    page: PageConfig = Field(default_factory=PageConfig)
    styles: Dict[str, DocxStyleConfig] = Field(default_factory=dict)
    
    # Metadata for other renderers
    latex_cmd_map: Dict[str, str] = Field(default_factory=dict)
    
    # Legacy mapping for simple templates
    docx_style_map: Dict[str, str] = Field(default_factory=dict)

    def get_tag_names(self) -> List[str]:
        return [tag.name for tag in self.tags]

    def get_prompt_fragment(self) -> str:
        """Generates a text description of the tags for LLM prompts."""
        lines = []
        for tag in self.tags:
            req = "(Required)" if tag.is_required else ""
            lines.append(f"- {tag.name}: {tag.description} {req}")
        return "\n".join(lines)
