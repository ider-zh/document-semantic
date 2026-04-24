from __future__ import annotations

import re
from typing import Any

from document_semantic.models.mineru_content import (
    MinerUElement,
    MinerUGenericContent,
    MinerUInlineContent,
    MinerUListContent,
    MinerUParagraphContent,
    MinerUTitleContent,
)


class ProtectionVerificationError(Exception):
    """Raised when placeholders are missing in the processed text."""

    pass


class Protector:
    """Protects complex structures in MinerUElement lists during processing.

    Replaces non-translatable elements with XML-like placeholders and
    restores them back to the original objects after processing.
    """

    def __init__(self, prefix: str = "P"):
        self.prefix = prefix
        self._placeholder_pattern = re.compile(rf"<{self.prefix}:([A-Z_]+)_(\d+)/>")

    def protect(self, elements: list[MinerUElement]) -> tuple[str, dict[str, Any]]:
        """Converts a list of elements to a protected string.

        Returns:
            A tuple of (protected_string, mapping_dict).
        """
        mapping = {}
        lines = []

        # We need unique IDs within this protection session
        counters = {"EQ": 0, "IMG": 0, "TBL": 0, "CODE": 0, "REF": 0, "INLINE_EQ": 0}

        def _get_id(tag: str) -> str:
            counters[tag] += 1
            return f"{self.prefix}:{tag}_{counters[tag]}"

        for elem in elements:
            e_type = elem.type
            content = elem.content

            if e_type == "title":
                assert isinstance(content, MinerUTitleContent)
                level = content.level
                text = self._protect_inline_list(content.title_content or [], mapping, _get_id)
                lines.append("#" * level + " " + text)

            elif e_type == "paragraph":
                assert isinstance(content, MinerUParagraphContent)
                text = self._protect_inline_list(content.paragraph_content or [], mapping, _get_id)
                lines.append(text)

            elif e_type == "list":
                assert isinstance(content, MinerUListContent)
                # We protect the whole list structure as a block if it's too complex,
                # but usually we want to translate list items.
                # Let's keep the markdown list structure.
                list_lines = []
                for item in content.list_items:
                    item_text = self._protect_inline_list(item.item_content, mapping, _get_id)
                    list_lines.append(f"- {item_text}")
                lines.append("\n".join(list_lines))

            elif e_type == "equation_interline":
                p_id = _get_id("EQ")
                mapping[p_id] = elem
                lines.append(f"<{p_id}/>")

            elif e_type in ("image", "figure", "img"):
                p_id = _get_id("IMG")
                mapping[p_id] = elem
                lines.append(f"<{p_id}/>")

            elif e_type in ("table", "table_body"):
                p_id = _get_id("TBL")
                mapping[p_id] = elem
                lines.append(f"<{p_id}/>")

            elif e_type in ("code", "algorithm"):
                p_id = _get_id("CODE")
                mapping[p_id] = elem
                lines.append(f"<{p_id}/>")

            elif isinstance(content, MinerUGenericContent):
                if isinstance(content.content, str):
                    lines.append(content.content)
                elif isinstance(content.content, list):
                    text = self._protect_inline_list(content.content, mapping, _get_id)
                    lines.append(text)
            else:
                # Fallback for unknown types - protect as block
                p_id = _get_id("GEN")
                mapping[p_id] = elem
                lines.append(f"<{p_id}/>")

        return "\n\n".join(lines), mapping

    def _protect_inline_list(self, inlines: list[MinerUInlineContent], mapping: dict[str, Any], get_id_func) -> str:
        parts = []
        for inline in inlines:
            if inline.type == "text":
                parts.append(inline.content)
            elif inline.type == "equation_inline":
                p_id = get_id_func("INLINE_EQ")
                mapping[p_id] = inline
                parts.append(f"<{p_id}/>")
            else:
                # Other inlines (like bold, italic if represented as separate types)
                # MinerU usually just has text and equation_inline
                p_id = get_id_func("INLINE")
                mapping[p_id] = inline
                parts.append(f"<{p_id}/>")
        return "".join(parts)

    def verify(self, text: str, mapping: dict[str, Any]) -> None:
        """Verifies that all placeholders in mapping exist in text."""
        missing = []
        for p_id in mapping:
            if f"<{p_id}/>" not in text:
                missing.append(p_id)

        if missing:
            raise ProtectionVerificationError(f"Missing placeholders in output: {', '.join(missing)}")

    def restore(self, text: str, mapping: dict[str, Any]) -> list[MinerUElement]:
        """Restores a protected string back to a list of elements.

        This is tricky because the LLM might have merged or split lines.
        We rely on the placeholders being block-level or inline.
        """
        # First, we split the text into logical blocks (double newlines)
        # But wait, restoring is hard if the LLM changed the structure.
        # Actually, if we want to restore back to MinerUElement list,
        # we should parse the text line by line or block by block.

        # A simpler approach:
        # 1. Split text into segments based on placeholders.
        # 2. Re-construct elements.

        # Let's use re.split to keep the placeholders
        tokens = re.split(rf"(<{self.prefix}:[A-Z_]+_\d+/>)", text)

        restored_elements = []
        current_paragraph_inlines = []

        def flush_paragraph():
            if current_paragraph_inlines:
                # Check if it's actually a title (starts with #)
                first_content = current_paragraph_inlines[0].content
                if first_content.startswith("#"):
                    level = 0
                    while level < len(first_content) and first_content[level] == "#":
                        level += 1

                    # Strip leading # and space
                    current_paragraph_inlines[0].content = first_content[level:].lstrip()

                    restored_elements.append(
                        MinerUElement(
                            type="title",
                            content=MinerUTitleContent(title_content=list(current_paragraph_inlines), level=level),
                        )
                    )
                else:
                    restored_elements.append(
                        MinerUElement(
                            type="paragraph",
                            content=MinerUParagraphContent(paragraph_content=list(current_paragraph_inlines)),
                        )
                    )
                current_paragraph_inlines.clear()

        for token in tokens:
            if not token:
                continue

            match = self._placeholder_pattern.match(token)
            if match:
                p_id = f"{self.prefix}:{match.group(1)}_{match.group(2)}"
                original = mapping.get(p_id)

                if isinstance(original, MinerUElement):
                    # Block level element
                    flush_paragraph()
                    restored_elements.append(original)
                elif isinstance(original, MinerUInlineContent):
                    # Inline element
                    current_paragraph_inlines.append(original)
            else:
                # Plain text. Might contain multiple paragraphs.
                lines = token.split("\n\n")
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        if i < len(lines) - 1:
                            flush_paragraph()
                        continue

                    # Handle lists (very basic for now)
                    if line.startswith("- "):
                        # If we have a pending paragraph that isn't a list, flush it?
                        # This is getting complex. For now, let's treat everything as text.
                        pass

                    current_paragraph_inlines.append(MinerUInlineContent(type="text", content=line))

                    if i < len(lines) - 1:
                        flush_paragraph()

        flush_paragraph()
        return restored_elements
