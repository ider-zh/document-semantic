import pytest

from document_semantic.models.mineru_content import (
    MinerUElement,
    MinerUEquationInterlineContent,
    MinerUInlineContent,
    MinerUParagraphContent,
    MinerUTitleContent,
)
from document_semantic.transform.protector import ProtectionVerificationError, Protector


def test_protector_basic():
    elements = [
        MinerUElement(
            type="title",
            content=MinerUTitleContent(title_content=[MinerUInlineContent(type="text", content="Chapter 1")], level=1),
        ),
        MinerUElement(
            type="paragraph",
            content=MinerUParagraphContent(
                paragraph_content=[
                    MinerUInlineContent(type="text", content="The equation is "),
                    MinerUInlineContent(type="equation_inline", content="E=mc^2"),
                    MinerUInlineContent(type="text", content=" and it's famous."),
                ]
            ),
        ),
        MinerUElement(
            type="equation_interline",
            content=MinerUEquationInterlineContent(math_content="E = mc^2", math_type="latex"),
        ),
    ]

    protector = Protector()
    text, mapping = protector.protect(elements)

    # Check if placeholders are correct
    assert "# Chapter 1" in text
    assert "The equation is <P:INLINE_EQ_1/> and it's famous." in text
    assert "<P:EQ_1/>" in text
    assert len(mapping) == 2  # one inline eq, one block eq

    # Restore
    restored = protector.restore(text, mapping)
    assert len(restored) == 3
    assert restored[0].type == "title"
    assert restored[0].content.title_content[0].content == "Chapter 1"
    assert restored[1].content.paragraph_content[1].type == "equation_inline"
    assert restored[2].type == "equation_interline"
    assert restored[2].content.math_content == "E = mc^2"


def test_protector_verification_error():
    elements = [
        MinerUElement(type="equation_interline", content=MinerUEquationInterlineContent(math_content="E = mc^2"))
    ]
    protector = Protector()
    text, mapping = protector.protect(elements)

    # Simulate LLM missing a placeholder
    corrupted_text = "The equation is missing."
    with pytest.raises(ProtectionVerificationError):
        protector.verify(corrupted_text, mapping)
