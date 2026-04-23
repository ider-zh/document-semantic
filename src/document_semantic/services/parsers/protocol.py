"""Parser abstraction: protocol, intermediate result, and exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from document_semantic.models.inline_elements import InlineElement


class IntermediateBlock(BaseModel):
    """A raw block from the parsing stage (before semantic recognition).

    This is the intermediate representation between parsing and recognition.
    """

    model_config = ConfigDict(frozen=True)

    content: str = Field(..., description="Raw text content")
    style_hint: str | None = Field(
        default=None,
        description="Parser-provided style hint (e.g., 'Heading1', 'Normal', 'Table')",
    )
    inline_elements: list[InlineElement] = Field(
        default_factory=list,
        description="Inline elements detected during parsing (if available)",
    )


class Attachment(BaseModel):
    """Reference to an extracted attachment (e.g., image from DOCX)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique attachment identifier")
    path: str = Field(..., description="File path or reference to the attachment")
    mime_type: str | None = Field(default=None, description="MIME type if known")


class IntermediateResult(BaseModel):
    """Output of the document parsing stage.

    Contains raw blocks, document metadata, and extracted attachments.
    This is the intermediate format between parsing and semantic recognition.
    """

    model_config = ConfigDict(frozen=True)

    blocks: list[IntermediateBlock] = Field(default_factory=list, description="Raw blocks extracted from the document")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata (title, author, etc.)")
    attachments: list[Attachment] = Field(
        default_factory=list, description="Extracted attachments (images, embedded objects)"
    )


class Parser(ABC):
    """Abstract base class for document parsers.

    Concrete implementations (e.g., PandocParser, PythonDocxParser) must
    implement the ``parse`` method to convert a DOCX file into an
    :class:`IntermediateResult`.
    """

    @abstractmethod
    def parse(self, docx_path: Path, skip_image_ocr: bool = False) -> IntermediateResult:
        """Parse a DOCX file and produce an IntermediateResult.

        Args:
            docx_path: Absolute path to the DOCX file.
            skip_image_ocr: If True, replace images with placeholders before
                processing to prevent OCR extraction. Only supported by mineru parser;
                other parsers ignore this flag.

        Returns:
            An IntermediateResult with blocks, metadata, and attachments.

        Raises:
            ParserDependencyError: If a required external dependency is missing.
            ParserError: If parsing fails for any other reason.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the canonical name of this parser (e.g., 'pandoc', 'python-docx')."""
        ...
