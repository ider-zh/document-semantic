"""Centralized exceptions for the document-semantic project."""


class DocumentSemanticError(Exception):
    """Base exception for all document-semantic errors."""


# --- Parser Exceptions ---


class ParserError(DocumentSemanticError):
    """Base exception for parser-related errors."""


class ParserNotFoundError(ParserError):
    """Raised when a requested parser is not found in the registry."""

    def __init__(self, parser_name: str, available_parsers: list[str]):
        self.parser_name = parser_name
        self.available_parsers = available_parsers
        super().__init__(f"Parser '{parser_name}' not found. Available parsers: {', '.join(available_parsers)}")


class ParserDependencyError(ParserError):
    """Raised when a parser's external dependency is missing."""

    def __init__(self, parser_name: str, dependency: str, message: str = ""):
        self.parser_name = parser_name
        self.dependency = dependency
        detail = message or f"Required dependency '{dependency}' is not available for parser '{parser_name}'"
        super().__init__(detail)


# --- Recognizer / Agent Exceptions ---


class RecognizerError(DocumentSemanticError):
    """Base exception for recognizer-related errors."""


class RecognizerNotConfiguredError(RecognizerError):
    """Raised when a recognizer requires configuration that is missing."""


class RecognizerNotFoundError(RecognizerError):
    """Raised when a requested recognizer is not found."""

    def __init__(self, recognizer_name: str, available_recognizers: list[str]):
        self.recognizer_name = recognizer_name
        self.available_recognizers = available_recognizers
        super().__init__(
            f"Recognizer '{recognizer_name}' not found. Available recognizers: {', '.join(available_recognizers)}"
        )


# --- Pipeline Exceptions ---


class PipelineError(DocumentSemanticError):
    """Base exception for pipeline-related errors."""


class PipelineConfigurationError(PipelineError):
    """Raised when the pipeline configuration is invalid."""
