"""Semantic recognizer abstraction and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from document_semantic.core.logger import get_logger
from document_semantic.models.semantic_document import SemanticDocument
from document_semantic.services.parsers.protocol import IntermediateResult

logger = get_logger(__name__)


class SemanticRecognizer(ABC):
    """Abstract base class for semantic recognizers.

    Concrete implementations analyze an :class:`IntermediateResult` and
    produce a typed :class:`SemanticDocument`.
    """

    @abstractmethod
    def recognize(self, intermediate: IntermediateResult) -> SemanticDocument:
        """Analyze intermediate result and produce a SemanticDocument.

        Args:
            intermediate: The parsed document intermediate representation.

        Returns:
            A SemanticDocument with typed block and inline elements.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the canonical name of this recognizer."""
        ...
