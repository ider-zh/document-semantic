"""Parser registry for name-to-parser resolution."""

from __future__ import annotations

from typing import TypeVar

from .protocol import Parser, ParserNotFoundError

T = TypeVar("T", bound=Parser)


class ParserRegistry:
    """Registry that maps string identifiers to parser classes/instances.

    Parsers register themselves (or are registered) by name. The pipeline
    resolves the active parser from this registry at runtime.
    """

    _registry: dict[str, type[Parser]] = {}

    @classmethod
    def register(cls, name: str, parser_cls: type[Parser]) -> None:
        """Register a parser class under the given name.

        Args:
            name: The identifier for this parser (e.g., 'pandoc', 'python-docx').
            parser_cls: A class that implements the Parser interface.
        """
        cls._registry[name] = parser_cls

    @classmethod
    def get(cls, name: str) -> Parser:
        """Resolve and instantiate a parser by name.

        Args:
            name: The registered parser identifier.

        Returns:
            An instance of the requested parser.

        Raises:
            ParserNotFoundError: If no parser is registered under the given name.
        """
        parser_cls = cls._registry.get(name)
        if parser_cls is None:
            raise ParserNotFoundError(name, list(cls._registry.keys()))
        return parser_cls()

    @classmethod
    def available(cls) -> list[str]:
        """Return list of registered parser names."""
        return list(cls._registry.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a parser is registered under the given name."""
        return name in cls._registry
