"""Semantic recognizer implementations."""

from document_semantic.core.exceptions import (
    RecognizerError,
    RecognizerNotConfiguredError,
    RecognizerNotFoundError,
)

from .pandoc_recognizer import PandocRecognizer
from .protocol import SemanticRecognizer
from .regex_recognizer import RegexRecognizer
from .router_and_llm import (
    LLMClient,
    LLMRecognizer,
    RouterRecognizer,
    RoutingRule,
    create_recognizer,
    register_recognizer,
)

__all__ = [
    "SemanticRecognizer",
    "RecognizerError",
    "RecognizerNotFoundError",
    "RecognizerNotConfiguredError",
    "PandocRecognizer",
    "RegexRecognizer",
    "LLMClient",
    "LLMRecognizer",
    "RoutingRule",
    "RouterRecognizer",
    "create_recognizer",
    "register_recognizer",
]
