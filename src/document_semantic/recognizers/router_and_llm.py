"""Router recognizer and LLM recognizer placeholder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from document_semantic.models.semantic_document import SemanticDocument
from document_semantic.observability.logger import get_logger
from document_semantic.parsers.protocol import IntermediateResult

from .protocol import (
    SemanticRecognizer,
    RecognizerError,
    RecognizerNotConfiguredError,
    RecognizerNotFoundError,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# LLM Recognizer (placeholder)
# ---------------------------------------------------------------------------


class LLMClient(ABC):
    """Abstract interface for LLM inference clients."""

    @abstractmethod
    def infer(self, prompt: str) -> str:
        """Send a prompt and return the text response."""
        ...


class LLMRecognizer(SemanticRecognizer):
    """LLM-based semantic recognizer (placeholder for future integration).

    Requires an LLMClient to be provided. Without a client, calls to
    recognize() will raise RecognizerNotConfiguredError.
    """

    def __init__(self, client: Optional[LLMClient] = None):
        self._client = client

    @property
    def name(self) -> str:
        return "llm"

    def recognize(self, intermediate: IntermediateResult) -> SemanticDocument:
        """Recognize semantics using an LLM.

        Raises:
            RecognizerNotConfiguredError: If no LLMClient is configured.
        """
        if self._client is None:
            raise RecognizerNotConfiguredError(
                "LLMRecognizer requires an LLMClient to be configured. "
                "Provide a client when constructing this recognizer."
            )

        # Placeholder: future implementation sends document content to LLM
        raise NotImplementedError(
            "LLMRecognizer is not yet fully implemented. "
            "This is a placeholder for future LLM integration."
        )


# ---------------------------------------------------------------------------
# Router Recognizer
# ---------------------------------------------------------------------------


class RoutingRule:
    """A rule that determines which recognizer to use for a document."""

    def __init__(self, condition: dict[str, Any], recognizer: SemanticRecognizer):
        """
        Args:
            condition: Dict of metadata key-value pairs that must all match.
                       e.g., {"doc_type": "academic"}
            recognizer: The recognizer to use when this rule matches.
        """
        self.condition = condition
        self.recognizer = recognizer

    def matches(self, metadata: dict[str, Any]) -> bool:
        """Check if the given document metadata satisfies this rule."""
        for key, value in self.condition.items():
            if metadata.get(key) != value:
                return False
        return True


class RouterRecognizer(SemanticRecognizer):
    """Recognizer that dispatches to sub-recognizers based on routing rules.

    Rules are evaluated in order; the first matching recognizer is used.
    If no rule matches, the default recognizer is used.
    """

    def __init__(
        self,
        rules: list[RoutingRule],
        default_recognizer: SemanticRecognizer,
    ):
        self._rules = rules
        self._default = default_recognizer

    @property
    def name(self) -> str:
        return "router"

    def recognize(self, intermediate: IntermediateResult) -> SemanticDocument:
        """Route to the appropriate recognizer based on document metadata.

        Args:
            intermediate: The parsed document intermediate representation.

        Returns:
            A SemanticDocument from the matched recognizer.
        """
        metadata = intermediate.metadata
        doc_type = metadata.get("doc_type", "unknown")
        logger.info(f"[recognition:router] Routing document with doc_type='{doc_type}'")

        for rule in self._rules:
            if rule.matches(metadata):
                logger.info(
                    f"[recognition:router] Matched rule -> {rule.recognizer.name}"
                )
                return rule.recognizer.recognize(intermediate)

        logger.info(f"[recognition:router] No rule matched, using default: {self._default.name}")
        return self._default.recognize(intermediate)


# ---------------------------------------------------------------------------
# Recognizer Registry and Factory
# ---------------------------------------------------------------------------

_RECOGNIZER_REGISTRY: dict[str, Any] = {}


def register_recognizer(name: str, cls: type[SemanticRecognizer]) -> None:
    """Register a recognizer class by name."""
    _RECOGNIZER_REGISTRY[name] = cls


def create_recognizer(
    recognizer_type: str,
    config: Optional[dict[str, Any]] = None,
) -> SemanticRecognizer:
    """Create a recognizer instance from configuration.

    Args:
        recognizer_type: Recognizer name (e.g., 'regex', 'llm', 'router').
        config: Optional recognizer-specific configuration.

    Returns:
        A configured SemanticRecognizer instance.

    Raises:
        RecognizerNotFoundError: If the recognizer type is not registered.
    """
    config = config or {}
    cls = _RECOGNIZER_REGISTRY.get(recognizer_type)
    if cls is None:
        raise RecognizerNotFoundError(
            recognizer_type, list(_RECOGNIZER_REGISTRY.keys())
        )
    return cls(**config)


# Auto-register built-in recognizers
from .regex_recognizer import RegexRecognizer  # noqa: E402

register_recognizer("regex", RegexRecognizer)

__all__ = [
    "LLMClient",
    "LLMRecognizer",
    "RoutingRule",
    "RouterRecognizer",
    "register_recognizer",
    "create_recognizer",
]
