"""Semantic recognizer abstraction and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from document_semantic.models.semantic_document import SemanticDocument
from document_semantic.observability.logger import get_logger
from document_semantic.parsers.protocol import IntermediateResult

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


class RecognizerError(Exception):
    """Base exception for recognizer-related errors."""


class RecognizerNotConfiguredError(RecognizerError):
    """Raised when a recognizer requires configuration that is missing."""


class RecognizerNotFoundError(RecognizerError):
    """Raised when a requested recognizer is not found."""

    def __init__(self, recognizer_name: str, available_recognizers: list[str]):
        self.recognizer_name = recognizer_name
        self.available_recognizers = available_recognizers
        super().__init__(
            f"Recognizer '{recognizer_name}' not found. "
            f"Available recognizers: {', '.join(available_recognizers)}"
        )
