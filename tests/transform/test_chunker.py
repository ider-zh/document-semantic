from document_semantic.models.mineru_content import (
    MinerUElement,
    MinerUInlineContent,
    MinerUParagraphContent,
    MinerUTitleContent,
)
from document_semantic.transform.chunker import Chunker


def test_chunker_basic():
    # Large number of elements
    elements = [
        MinerUElement(
            type="title",
            content=MinerUTitleContent(title_content=[MinerUInlineContent(type="text", content="Chapter 1")], level=1),
        )
    ]
    for i in range(20):
        elements.append(
            MinerUElement(
                type="paragraph",
                content=MinerUParagraphContent(
                    paragraph_content=[MinerUInlineContent(type="text", content="Sentence " + str(i))]
                ),
            )
        )

    # Each paragraph is ~10 chars
    # chapter is ~10 chars
    # Total is ~210 chars

    # If we set max_chars to 100, we expect ~3 chunks
    chunker = Chunker(max_chars=100, min_chars=10)
    chunks = chunker.chunk(elements)

    assert len(chunks) > 1
    # Check if first chunk contains the title
    assert chunks[0][0].type == "title"

    # Total element count should match
    total_elements = sum(len(c) for c in chunks)
    assert total_elements == 21


def test_chunker_split_at_heading():
    elements = [
        MinerUElement(
            type="paragraph",
            content=MinerUParagraphContent(
                paragraph_content=[MinerUInlineContent(type="text", content="Some preamble text.")]
            ),
        ),
        MinerUElement(
            type="title",
            content=MinerUTitleContent(title_content=[MinerUInlineContent(type="text", content="Chapter 1")], level=1),
        ),
        MinerUElement(
            type="paragraph",
            content=MinerUParagraphContent(
                paragraph_content=[MinerUInlineContent(type="text", content="Sentence text inside chapter.")]
            ),
        ),
    ]

    # Split even if small if it's a heading and we reached min_chars
    chunker = Chunker(max_chars=1000, min_chars=5)
    chunks = chunker.chunk(elements)

    assert len(chunks) == 2
    assert chunks[0][0].type == "paragraph"
    assert chunks[1][0].type == "title"
