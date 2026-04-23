"""Regex-based semantic recognizer for block and inline element extraction."""

from __future__ import annotations

import re

from document_semantic.core.logger import get_logger
from document_semantic.models.blocks import (
    Block,
    CodeBlock,
    HeadingBlock,
    ListItemBlock,
    TableBlock,
    TextBlock,
    TitleBlock,
)
from document_semantic.models.inline_elements import (
    BoldInlineElement,
    CodeSpanInlineElement,
    FormulaInlineElement,
    InlineElement,
    ItalicInlineElement,
    LinkInlineElement,
    StrikethroughInlineElement,
)
from document_semantic.models.semantic_document import (
    Attachment,
    DocumentMetadata,
    SemanticDocument,
)
from document_semantic.services.parsers.protocol import IntermediateBlock, IntermediateResult

from .protocol import SemanticRecognizer

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Block-level patterns
# ---------------------------------------------------------------------------

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)")
_TITLE_HEADING_PATTERN = re.compile(r"^#{1}\s+(.*)")  # Single # at top could be title


def _classify_block(block: IntermediateBlock) -> Block:
    """Classify a raw intermediate block into a typed semantic block."""
    content = block.content
    style_hint = block.style_hint or ""
    pre_existing_inlines = list(block.inline_elements)  # Elements already from parser

    # Try markdown heading syntax first
    heading_match = _HEADING_PATTERN.match(content)
    if heading_match:
        level = len(heading_match.group(1))
        # For markdown headings, strip the leading #s for display content
        display_content = heading_match.group(2).strip()
        return HeadingBlock(
            level=level,
            content=display_content,
            inline_elements=_extract_or_merge_inline_elements(heading_match.group(2).strip(), pre_existing_inlines),
        )

    # Try style hint from parser
    style_upper = style_hint.upper() if style_hint else ""
    if "TITLE" in style_upper:
        return TitleBlock(
            content=content,
            inline_elements=_extract_or_merge_inline_elements(content, pre_existing_inlines),
        )
    if "HEADING" in style_upper:
        # Extract level number from style hint like "Heading1", "HEADING2"
        level_match = re.search(r"(\d)", style_hint)
        level = int(level_match.group(1)) if level_match else 1
        level = max(1, min(6, level))
        return HeadingBlock(
            level=level,
            content=content,
            inline_elements=_extract_or_merge_inline_elements(content, pre_existing_inlines),
        )
    if "LIST" in style_upper or content.startswith(("- ", "* ", "+ ")):
        return ListItemBlock(
            content=content.lstrip("-*+ ").strip(),
            inline_elements=_extract_or_merge_inline_elements(content, pre_existing_inlines),
            list_type="unordered",
        )
    if "TABLE" in style_upper:
        return TableBlock(content=content)
    if "CODE" in style_upper or content.startswith("```"):
        lang_match = re.match(r"```(\w+)?", content)
        language = lang_match.group(1) if lang_match else None
        return CodeBlock(content=content, language=language)

    # Heuristic: short text at start could be title
    # Heuristic: "abstract" / "summary" heading
    if content.lower() in ("abstract", "summary"):
        return HeadingBlock(level=1, content=content)

    # Default: text block
    return TextBlock(
        content=content,
        inline_elements=_extract_or_merge_inline_elements(content, pre_existing_inlines),
    )


# ---------------------------------------------------------------------------
# Inline element patterns
# ---------------------------------------------------------------------------

_INLINE_PATTERNS = [
    # Inline formula: $...$
    (r"\$([^$]+)\$", FormulaInlineElement),
    # Code span: `...`
    (r"`([^`]+)`", CodeSpanInlineElement),
    # Bold: **...** or __...__
    (r"\*\*([^*]+)\*\*", BoldInlineElement),
    (r"__([^_]+)__", BoldInlineElement),
    # Italic: *...* or _..._
    (r"\*([^*]+)\*", ItalicInlineElement),
    (r"(?<!\w)_([^_]+)_(?!\w)", ItalicInlineElement),
    # Strikethrough: ~~...~~
    (r"~~([^~]+)~~", StrikethroughInlineElement),
    # Link: [text](url)
    (r"\[([^\]]+)\]\(([^)]+)\)", LinkInlineElement),
]


def _extract_or_merge_inline_elements(text: str, pre_existing: list[InlineElement]) -> list[InlineElement]:
    """Extract inline elements, preferring pre-existing ones from the parser.

    If the parser already extracted inline elements (from run formatting),
    we use those directly and adjust offsets for the new text.
    Otherwise, we extract from markdown patterns in the text.

    Args:
        text: The text content (may be stripped of markdown markers or not).
        pre_existing: Inline elements already extracted by the parser.

    Returns:
        List of inline elements.
    """
    if pre_existing:
        # The parser already extracted elements.
        # If the text has markdown markers (e.g., **摘要**), we need to
        # adjust offsets from the marker-wrapped version to the clean version.
        # Simple approach: find the raw text within the content.
        adjusted = []
        for elem in pre_existing:
            pos = text.find(elem.text)
            if pos >= 0:
                adjusted.append(
                    elem.model_copy(
                        update={
                            "start_offset": pos,
                            "end_offset": pos + len(elem.text),
                        }
                    )
                )
            else:
                # Text not found in cleaned content, skip
                pass
        return adjusted

    # No pre-existing elements, extract from markdown patterns
    return _extract_inline_elements(text)


def _extract_inline_elements(text: str) -> list[InlineElement]:
    """Extract inline semantic elements from a text string.

    Scans for markdown-like patterns and produces typed inline elements
    with position offsets.
    """
    elements: list[InlineElement] = []
    seen_spans: set[tuple[int, int]] = set()

    for pattern, element_cls in _INLINE_PATTERNS:
        for match in re.finditer(pattern, text):
            start = match.start()
            end = match.end()

            if (start, end) in seen_spans:
                continue

            if element_cls == LinkInlineElement:
                elem = LinkInlineElement(
                    text=match.group(1),
                    url=match.group(2),
                    start_offset=start,
                    end_offset=end,
                )
            else:
                elem = element_cls(
                    text=match.group(1),
                    start_offset=start,
                    end_offset=end,
                )
            elements.append(elem)
            seen_spans.add((start, end))

    # Sort by position
    elements.sort(key=lambda e: e.start_offset)
    return elements


class RegexRecognizer(SemanticRecognizer):
    """Regex-based semantic recognizer using pattern matching.

    Classifies blocks based on markdown syntax and style hints,
    and extracts inline elements from text content.
    """

    @property
    def name(self) -> str:
        return "regex"

    def recognize(self, intermediate: IntermediateResult) -> SemanticDocument:
        """Recognize semantic structure from intermediate result.

        Args:
            intermediate: The parsed document intermediate representation.

        Returns:
            A SemanticDocument with classified blocks and inline elements.
        """
        logger.info(f"[recognition:regex] Processing {len(intermediate.blocks)} blocks")

        blocks: list[Block] = []
        for i, raw_block in enumerate(intermediate.blocks):
            try:
                typed_block = _classify_block(raw_block)
                blocks.append(typed_block)
                logger.debug(f"[recognition:regex] Block {i}: {typed_block.type}")
            except Exception:
                logger.warning(
                    f"[recognition:regex] Failed to classify block {i}: content_preview='{raw_block.content[:50]}...'"
                )
                # Fallback to text block
                blocks.append(
                    TextBlock(
                        content=raw_block.content,
                        inline_elements=_extract_or_merge_inline_elements(raw_block.content, raw_block.inline_elements),
                    )
                )

        # Convert parser attachments to document attachments
        attachments = [Attachment(id=a.id, path=a.path, mime_type=a.mime_type) for a in intermediate.attachments]

        metadata = DocumentMetadata(
            title=intermediate.metadata.get("title"),
            author=intermediate.metadata.get("author"),
            doc_type=intermediate.metadata.get("doc_type"),
            source_path=intermediate.metadata.get("source_path"),
        )

        doc = SemanticDocument(
            blocks=blocks,
            attachments=attachments,
            metadata=metadata,
        )

        logger.info(f"[recognition:regex] Complete: {len(blocks)} blocks classified")
        return doc
