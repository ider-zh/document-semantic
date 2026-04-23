"""Tests for semantic recognizers."""

from __future__ import annotations

import pytest

from document_semantic.agents.regex_recognizer import RegexRecognizer
from document_semantic.agents.router_and_llm import (
    LLMRecognizer,
    RouterRecognizer,
    RoutingRule,
)
from document_semantic.core.exceptions import RecognizerNotConfiguredError
from document_semantic.models.blocks import (
    HeadingBlock,
    TextBlock,
    TitleBlock,
)
from document_semantic.models.inline_elements import (
    BoldInlineElement,
    CodeSpanInlineElement,
)
from document_semantic.models.semantic_document import SemanticDocument
from document_semantic.services.parsers.protocol import IntermediateBlock, IntermediateResult

# ---------------------------------------------------------------------------
# RegexRecognizer tests
# ---------------------------------------------------------------------------


class TestRegexRecognizer:
    """Tests for the regex-based recognizer."""

    def test_block_classification_heading(self, regex_recognizer: RegexRecognizer):
        """RegexRecognizer classifies markdown headings."""
        intermediate = IntermediateResult(
            blocks=[
                IntermediateBlock(content="# Main Title", style_hint=None),
                IntermediateBlock(content="## Sub Heading", style_hint=None),
                IntermediateBlock(content="###### Deep Heading", style_hint=None),
            ],
            metadata={},
            attachments=[],
        )

        result = regex_recognizer.recognize(intermediate)

        assert isinstance(result, SemanticDocument)
        assert len(result.blocks) == 3
        assert isinstance(result.blocks[0], HeadingBlock)
        assert result.blocks[0].level == 1
        assert isinstance(result.blocks[1], HeadingBlock)
        assert result.blocks[1].level == 2
        assert isinstance(result.blocks[2], HeadingBlock)
        assert result.blocks[2].level == 6

    def test_block_classification_style_hint(self, regex_recognizer: RegexRecognizer):
        """RegexRecognizer uses style hints for classification."""
        intermediate = IntermediateResult(
            blocks=[
                IntermediateBlock(content="Document Title", style_hint="Title"),
                IntermediateBlock(content="Section One", style_hint="Heading1"),
                IntermediateBlock(content="Regular text here.", style_hint="Normal"),
            ],
            metadata={},
            attachments=[],
        )

        result = regex_recognizer.recognize(intermediate)

        assert isinstance(result.blocks[0], TitleBlock)
        assert isinstance(result.blocks[1], HeadingBlock)
        assert result.blocks[1].level == 1
        assert isinstance(result.blocks[2], TextBlock)

    def test_inline_bold_extraction(self, regex_recognizer: RegexRecognizer):
        """RegexRecognizer extracts bold inline elements."""
        intermediate = IntermediateResult(
            blocks=[
                IntermediateBlock(content="This has **bold text** inside.", style_hint="Normal"),
            ],
            metadata={},
            attachments=[],
        )

        result = regex_recognizer.recognize(intermediate)

        block = result.blocks[0]
        bold_elements = [e for e in block.inline_elements if isinstance(e, BoldInlineElement)]
        assert len(bold_elements) == 1
        assert bold_elements[0].text == "bold text"

    def test_inline_code_extraction(self, regex_recognizer: RegexRecognizer):
        """RegexRecognizer extracts code spans."""
        intermediate = IntermediateResult(
            blocks=[
                IntermediateBlock(content="Use `print()` to output.", style_hint="Normal"),
            ],
            metadata={},
            attachments=[],
        )

        result = regex_recognizer.recognize(intermediate)

        block = result.blocks[0]
        code_elements = [e for e in block.inline_elements if isinstance(e, CodeSpanInlineElement)]
        assert len(code_elements) == 1
        assert code_elements[0].text == "print()"

    def test_inline_formula_extraction(self, regex_recognizer: RegexRecognizer):
        """RegexRecognizer extracts inline formulas."""
        intermediate = IntermediateResult(
            blocks=[
                IntermediateBlock(content="The formula is $E = mc^2$ as known.", style_hint="Normal"),
            ],
            metadata={},
            attachments=[],
        )

        result = regex_recognizer.recognize(intermediate)

        from document_semantic.models.inline_elements import FormulaInlineElement

        block = result.blocks[0]
        formulas = [e for e in block.inline_elements if isinstance(e, FormulaInlineElement)]
        assert len(formulas) == 1
        assert formulas[0].text == "E = mc^2"

    def test_preserves_block_order(self, regex_recognizer: RegexRecognizer):
        """Recognizer preserves original block order."""
        blocks = [IntermediateBlock(content=f"Block {i}", style_hint="Normal") for i in range(10)]
        intermediate = IntermediateResult(blocks=blocks, metadata={}, attachments=[])

        result = regex_recognizer.recognize(intermediate)

        assert len(result.blocks) == 10
        for i, block in enumerate(result.blocks):
            assert block.content == f"Block {i}"


# ---------------------------------------------------------------------------
# RouterRecognizer tests
# ---------------------------------------------------------------------------


class TestRouterRecognizer:
    """Tests for the router recognizer."""

    def test_route_by_doc_type(self, regex_recognizer: RegexRecognizer):
        """Router dispatches based on doc_type metadata."""
        # Create a rule that uses a custom recognizer (we'll just use regex as target)
        rule = RoutingRule(
            condition={"doc_type": "academic"},
            recognizer=regex_recognizer,
        )
        router = RouterRecognizer(rules=[rule], default_recognizer=regex_recognizer)

        intermediate = IntermediateResult(
            blocks=[IntermediateBlock(content="# Title", style_hint=None)],
            metadata={"doc_type": "academic"},
            attachments=[],
        )

        result = router.recognize(intermediate)
        assert isinstance(result, SemanticDocument)

    def test_default_fallback(self, regex_recognizer: RegexRecognizer):
        """Router falls back to default recognizer when no rule matches."""
        rule = RoutingRule(
            condition={"doc_type": "nonexistent_type"},
            recognizer=regex_recognizer,
        )
        router = RouterRecognizer(rules=[rule], default_recognizer=regex_recognizer)

        intermediate = IntermediateResult(
            blocks=[IntermediateBlock(content="Some text", style_hint="Normal")],
            metadata={"doc_type": "regular"},
            attachments=[],
        )

        result = router.recognize(intermediate)
        assert isinstance(result, SemanticDocument)
        assert len(result.blocks) == 1


# ---------------------------------------------------------------------------
# LLMRecognizer tests
# ---------------------------------------------------------------------------


class TestLLMRecognizer:
    """Tests for the LLM recognizer placeholder."""

    def test_raises_without_client(self):
        """LLMRecognizer raises RecognizerNotConfiguredError without client."""
        recognizer = LLMRecognizer(client=None)
        intermediate = IntermediateResult(blocks=[], metadata={}, attachments=[])

        with pytest.raises(RecognizerNotConfiguredError):
            recognizer.recognize(intermediate)
