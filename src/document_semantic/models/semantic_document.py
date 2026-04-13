"""SemanticDocument container model and schema versioning."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field

from .blocks import Block
from .inline_elements import InlineElement

CURRENT_SCHEMA_VERSION = "1.0.0"


class Attachment(BaseModel):
    """Reference to an extracted attachment (e.g., image from DOCX)."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique attachment identifier")
    path: str = Field(..., description="File path or reference to the attachment")
    mime_type: Optional[str] = Field(default=None, description="MIME type if known")


class DocumentMetadata(BaseModel):
    """Document-level metadata."""

    model_config = ConfigDict(frozen=True)

    title: Optional[str] = Field(default=None, description="Document title")
    author: Optional[str] = Field(default=None, description="Document author")
    doc_type: Optional[str] = Field(
        default=None, description="Document type hint (e.g., 'academic', 'report')"
    )
    source_path: Optional[str] = Field(default=None, description="Original file path")
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata fields"
    )


class SemanticDocument(BaseModel):
    """Top-level container for a semantically processed document."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(
        default=CURRENT_SCHEMA_VERSION,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Schema version in semver format",
    )
    metadata: DocumentMetadata = Field(
        default_factory=DocumentMetadata, description="Document-level metadata"
    )
    blocks: list[Block] = Field(
        default_factory=list, description="Ordered list of semantic blocks"
    )
    attachments: list[Attachment] = Field(
        default_factory=list, description="Referenced attachments (images, etc.)"
    )

    def to_json(self, **kwargs: Any) -> str:
        """Serialize to JSON string with type discriminators preserved."""
        return self.model_dump_json(indent=2, **kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> SemanticDocument:
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)


# ---------------------------------------------------------------------------
# Schema Upgrader
# ---------------------------------------------------------------------------


class SchemaUpgrader(ABC):
    """Base class for schema version migrations.

    Subclass and register specific version transitions (e.g., 1.0.0 -> 2.0.0).
    """

    _registry: ClassVar[dict[tuple[str, str], SchemaUpgrader]] = {}

    @classmethod
    def register(cls, from_version: str, to_version: str) -> Callable:
        """Decorator to register an upgrader for a version transition."""

        def decorator(upgrader_class: type[SchemaUpgrader]) -> type[SchemaUpgrader]:
            instance = upgrader_class()
            cls._registry[(from_version, to_version)] = instance
            return upgrader_class

        return decorator

    @classmethod
    def get(cls, from_version: str, to_version: str) -> SchemaUpgrader | None:
        """Look up a registered upgrader for the given version transition."""
        return cls._registry.get((from_version, to_version))

    @classmethod
    def list_available(cls) -> list[tuple[str, str]]:
        """Return all registered version transitions."""
        return list(cls._registry.keys())

    @abstractmethod
    def upgrade(self, doc: SemanticDocument) -> SemanticDocument:
        """Perform the schema upgrade. Must return a new SemanticDocument."""
        ...
