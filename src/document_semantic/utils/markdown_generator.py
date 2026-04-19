"""Markdown generator with XML placeholder support.

Converts IntermediateResult blocks into formatted Markdown output,
replacing special elements (formulas, code blocks, images) with XML
placeholders and collecting resources for the mapping file.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional

from document_semantic.parsers.protocol import Attachment, IntermediateBlock, IntermediateResult

from .resource_mapping import ResourceCollector
from .xml_placeholders import (
    PositionType,
    ResourceType,
    block_placeholder,
    inline_placeholder,
)


class MarkdownGenerator:
    """Generates Markdown output with XML placeholders and resource extraction.

    Usage:
        gen = MarkdownGenerator(intermediate_result, config)
        rich_path, placeholder_path, resources_dir, json_path = gen.generate_both(output_dir, source_path, parser_name)
    """

    def __init__(
        self,
        intermediate: IntermediateResult,
        output_resources: bool = True,
    ) -> None:
        self._intermediate = intermediate
        self._output_resources = output_resources
        self._image_counter = 0

    def generate_both(
        self,
        output_dir: Path,
        source_path: Optional[str] = None,
        parser_name: Optional[str] = None,
    ) -> tuple[Path, Path, Optional[Path], Optional[Path]]:
        """Generate both rich and placeholder Markdown files, resource directory, and resources.json.

        Args:
            output_dir: Directory to write outputs to.
            source_path: Original document path (for metadata).
            parser_name: Name of the parser used (for metadata).

        Returns:
            Tuple of (rich_markdown_path, placeholder_markdown_path, resources_dir, resources_json_path).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        resources_dir = output_dir / "resources" if self._output_resources else None
        images_dir = resources_dir / "images" if resources_dir else None

        # Generate rich markdown (no XML placeholders, full content)
        rich_collector = ResourceCollector()
        rich_lines = self._build_markdown(images_dir, rich_collector, use_placeholders=False)
        rich_path = output_dir / "output_rich.md"
        rich_path.write_text("\n".join(rich_lines), encoding="utf-8")

        # Generate placeholder markdown (with XML placeholders)
        placeholder_collector = ResourceCollector()
        placeholder_lines = self._build_markdown(images_dir, placeholder_collector, use_placeholders=True)
        placeholder_path = output_dir / "output.md"
        placeholder_path.write_text("\n".join(placeholder_lines), encoding="utf-8")

        # Write resources.json (from placeholder collector)
        json_path = None
        if self._output_resources and resources_dir:
            json_path = placeholder_collector.write_json(
                output_dir, source_path=source_path, parser_name=parser_name
            )

        return rich_path, placeholder_path, resources_dir, json_path

    def generate(
        self,
        output_dir: Path,
        source_path: Optional[str] = None,
        parser_name: Optional[str] = None,
    ) -> tuple[Path, Optional[Path], Optional[Path]]:
        """Generate Markdown file, resource directory, and resources.json (legacy method).

        Args:
            output_dir: Directory to write outputs to.
            source_path: Original document path (for metadata).
            parser_name: Name of the parser used (for metadata).

        Returns:
            Tuple of (markdown_path, resources_dir_or_None, resources_json_path_or_None).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        resources_dir = output_dir / "resources" if self._output_resources else None
        images_dir = resources_dir / "images" if resources_dir else None

        md_path = output_dir / "output.md"
        lines = self._build_markdown(images_dir, self._collector, self._use_xml_placeholders)
        md_path.write_text("\n".join(lines), encoding="utf-8")

        json_path = None
        if self._output_resources and resources_dir:
            json_path = self._collector.write_json(
                output_dir, source_path=source_path, parser_name=parser_name
            )

        return md_path, resources_dir, json_path

    def _build_markdown(
        self,
        images_dir: Optional[Path],
        collector: ResourceCollector,
        use_placeholders: bool = True,
    ) -> list[str]:
        """Convert all blocks to Markdown lines."""
        lines: list[str] = []
        for block in self._intermediate.blocks:
            block_lines = self._process_block(block, images_dir, collector, use_placeholders)
            lines.extend(block_lines)
            lines.append("")  # Blank line between blocks
        return lines

    def _process_block(
        self, block: IntermediateBlock, images_dir: Optional[Path], collector: ResourceCollector, use_placeholders: bool = True
    ) -> list[str]:
        """Process a single IntermediateBlock into Markdown lines."""
        style_hint = block.style_hint or ""
        content = block.content

        # Handle block-level special elements
        if use_placeholders:
            # Block-level formulas
            if style_hint == "Formula" or self._is_block_formula(content):
                res_id = collector.add_formula(content, PositionType.BLOCK)
                return [block_placeholder(ResourceType.FORMULA, res_id)]

            # Block-level code
            if style_hint == "CodeBlock" or self._is_block_code(content):
                res_id = collector.add_code(content, PositionType.BLOCK)
                return [block_placeholder(ResourceType.CODE, res_id)]

            # Block-level images (by style hint or markdown image syntax)
            if style_hint == "Image" or self._is_block_image(content):
                return self._handle_block_image(content, images_dir, collector, use_placeholders=True)

        # For non-placeholder mode, still handle images but with markdown references
        if style_hint == "Image" or self._is_block_image(content):
            return self._handle_block_image(content, images_dir, collector, use_placeholders=False)

        # Handle tables
        if style_hint == "Table" or self._is_table(content):
            return self._format_table(content)

        # Handle headings
        heading = self._detect_heading(content, style_hint)
        if heading:
            level, text_content = heading
            prefix = "#" * level + " "
            processed_text = self._process_inline(text_content, images_dir, collector, use_placeholders)
            return [prefix + processed_text]

        # Handle list items
        if style_hint in ("ListBullet", "ListNumbered"):
            return self._format_list_item(content, style_hint, images_dir, collector, use_placeholders)

        # Handle MinerU list types - keep original content without conversion
        if style_hint in ("text_list", "reference_list", "list_item"):
            return self._format_mineru_list_item(content, style_hint)

        # Handle block quotes
        if style_hint == "BlockQuote":
            processed = self._process_inline(content, images_dir, collector, use_placeholders)
            return [f"> {line}" for line in processed.split("\n")]

        # Handle thematic breaks
        if style_hint == "ThematicBreak":
            return ["---"]

        # Default: plain paragraph
        processed = self._process_inline(content, images_dir, collector, use_placeholders)
        if processed.strip():
            return [processed]
        return []

    def _process_inline(
        self, text: str, images_dir: Optional[Path], collector: ResourceCollector, use_placeholders: bool = True
    ) -> str:
        """Process inline elements within text content."""
        if not use_placeholders:
            return text

        # Replace inline formulas: $...$ or $$...$$
        text = re.sub(
            r'\$([^$\n]+?)\$',
            lambda m: self._inline_formula_replacer(m, collector),
            text,
        )

        # Replace inline code spans: `...`
        text = re.sub(
            r'`([^`\n]+?)`',
            lambda m: self._inline_code_replacer(m, collector),
            text,
        )

        # Replace inline LaTeX formulas: \mathsf{...}, \sum, etc.
        # Match LaTeX commands with optional spaces before braces
        latex_formula_pattern = re.compile(
            r'((?:\\(?:mathsf|mathbf|mathrm|sum|int|frac|prod|sqrt|infty|alpha|beta|gamma|delta|epsilon|lambda|mu|pi|sigma|omega|partial|nabla|left|right|langle|rangle|lvert|rvert|overline|underline|hat|bar|tilde|vec|dot|ddot|text|limits|displaystyle|scriptstyle)\s*\{[^}]*\}|\\(?:sum|int|infty|ldots|cdots|dots|forall|exists|equiv|approx|neq|leq|geq|subset|supset|subseteq|supseteq|in|notin))+)',
            re.MULTILINE
        )
        text = latex_formula_pattern.sub(
            lambda m: self._inline_latex_formula_replacer(m, collector),
            text,
        )

        # Handle inline image references like ![alt](attachment:<id>)
        text = re.sub(
            r'!\[([^\]]*)\]\(attachment:([^)]+)\)',
            lambda m: self._inline_image_replacer(m, images_dir, collector),
            text,
        )

        return text

    def _inline_latex_formula_replacer(self, match: re.Match, collector: ResourceCollector) -> str:
        content = match.group(1)
        res_id = collector.add_formula(content, PositionType.INLINE)
        return inline_placeholder(ResourceType.FORMULA, res_id, content)

    def _inline_formula_replacer(self, match: re.Match, collector: ResourceCollector) -> str:
        content = match.group(1)
        res_id = collector.add_formula(content, PositionType.INLINE)
        return inline_placeholder(ResourceType.FORMULA, res_id, content)

    def _inline_code_replacer(self, match: re.Match, collector: ResourceCollector) -> str:
        content = match.group(1)
        res_id = collector.add_code(content, PositionType.INLINE)
        return inline_placeholder(ResourceType.CODE, res_id, content)

    def _inline_image_replacer(self, match: re.Match, images_dir: Optional[Path], collector: ResourceCollector) -> str:
        alt = match.group(1)
        attachment_id = match.group(2)
        # Find the attachment in intermediate result
        for att in self._intermediate.attachments:
            if att.id == attachment_id or att.id == f"attachment:{attachment_id}":
                return self._format_image_reference(att, images_dir, alt, collector)
        # If not found, keep original reference
        return match.group(0)

    def _handle_block_image(
        self, content: str, images_dir: Optional[Path], collector: ResourceCollector, use_placeholders: bool = True
    ) -> list[str]:
        """Handle a block-level image."""
        # Parse markdown image syntax: ![caption](attachment:<id>) or ![caption](path)
        m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', content)
        if m:
            alt = m.group(1)
            ref = m.group(2)
            # Check if it's an attachment reference
            if ref.startswith("attachment:"):
                att_id = ref[len("attachment:"):]
                for att in self._intermediate.attachments:
                    if att.id == att_id:
                        if use_placeholders:
                            res_id = collector.add_image(
                                att.path, content=alt, position_type=PositionType.BLOCK
                            )
                            return [block_placeholder(ResourceType.IMAGE, res_id)]
                        return [self._format_image_reference(att, images_dir, alt, collector)]
            elif images_dir:
                # It's a file path reference (e.g., resources/images/image_N)
                src_path = Path(ref)
                if src_path.exists():
                    self._image_counter += 1
                    dest_name = f"image_{self._image_counter}{src_path.suffix}"
                    dest_path = images_dir / dest_name
                    images_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    rel_path = f"resources/images/{dest_name}"
                    res_id = collector.add_image(
                        rel_path, content=alt, position_type=PositionType.BLOCK
                    )
                    if use_placeholders:
                        return [block_placeholder(ResourceType.IMAGE, res_id)]
                    return [f"![{alt}]({rel_path})"]
        # Fallback: record as image
        res_id = collector.add_image(
            content, content=content, position_type=PositionType.BLOCK
        )
        if use_placeholders:
            return [block_placeholder(ResourceType.IMAGE, res_id)]
        return [content]

    def _format_image_reference(
        self, att: Attachment, images_dir: Optional[Path], alt: str = "", collector: Optional[ResourceCollector] = None
    ) -> str:
        """Copy an image to the resources directory and return a Markdown image reference."""
        if collector is None:
            collector = self._collector

        self._image_counter += 1
        src_path = Path(att.path)

        # Strip zip:// or other protocol prefixes
        if src_path.parts[0].startswith("zip:"):
            # Can't copy from virtual paths; keep reference
            res_id = collector.add_image(
                att.path, content=alt, position_type=PositionType.BLOCK
            )
            return f"![{alt}](resources/images/image_{self._image_counter})"

        if not src_path.exists():
            # Source doesn't exist on filesystem; record reference
            res_id = collector.add_image(
                att.path, content=alt, position_type=PositionType.BLOCK
            )
            return f"![{alt}](resources/images/{att.id})"

        # Determine file extension
        suffix = src_path.suffix or ".png"
        dest_name = f"image_{self._image_counter}{suffix}"

        if images_dir:
            images_dir.mkdir(parents=True, exist_ok=True)
            dest_path = images_dir / dest_name
            shutil.copy2(src_path, dest_path)

        rel_path = f"resources/images/{dest_name}"
        collector.add_image(
            rel_path, content=alt, position_type=PositionType.BLOCK
        )
        return f"![{alt}]({rel_path})"

    def _format_table(self, content: str) -> list[str]:
        """Format table content as GFM table syntax."""
        # If content is already in table format, pass through
        if "|" in content:
            lines = content.strip().split("\n")
            if not lines:
                return []
            # First line is header
            result = [lines[0]]
            # Add separator line
            header_cells = lines[0].split("|")
            separator = "|".join(["---" for _ in header_cells])
            if separator.startswith("|"):
                separator = separator[1:]
            result.append(f"|{separator}|")
            # Add data rows
            result.extend(lines[1:])
            return result

        # If content is a description like "[Table: 3 rows x 2 cols]"
        return [content]

    def _format_list_item(
        self, content: str, style_hint: str, images_dir: Optional[Path], collector: ResourceCollector, use_placeholders: bool = True
    ) -> list[str]:
        """Format a list item with appropriate prefix."""
        processed = self._process_inline(content, images_dir, collector, use_placeholders)
        if style_hint == "ListNumbered":
            return [f"1. {processed}"]
        return [f"- {processed}"]

    def _format_mineru_list_item(self, content: str, style_hint: str) -> list[str]:
        """Format a MinerU list item - keep original content without XML conversion."""
        # For MinerU list types, return content as-is to preserve original structure
        return [content]

    # --- Detection helpers ---

    def _detect_heading(
        self, content: str, style_hint: str
    ) -> Optional[tuple[int, str]]:
        """Detect if content is a heading and return (level, text)."""
        # Check markdown syntax: # Heading
        m = re.match(r'^(#{1,6})\s+(.+)$', content)
        if m:
            return len(m.group(1)), m.group(2)

        # Check style hint
        if style_hint.startswith("Heading"):
            try:
                level = int(style_hint[-1])
                return level, content
            except (ValueError, IndexError):
                pass

        return None

    def _is_block_formula(self, content: str) -> bool:
        """Check if content is a block-level formula."""
        # Block formulas starting with $$
        if re.match(r'^\$\$', content):
            return True
        # Standalone $...$ formulas
        if re.match(r'^\s*\$[^$]+\$\s*$', content):
            return True
        # MinerU LaTeX formulas: entire content is a LaTeX formula ending with "latex"
        # e.g., "P _ {M} (x) = \sum_ {i = 0} ^ {\infty} 2 ^ {- | S _ {i} (x) |} latex"
        # Must end with "latex" and not contain regular text
        stripped = content.strip()
        if stripped.endswith(' latex') and re.search(r'\\', stripped):
            # Check it's not a list item or regular paragraph
            if not stripped.startswith('- ') and not stripped.startswith('1. '):
                # Ensure it's primarily mathematical content (has multiple LaTeX commands)
                latex_cmds = len(re.findall(r'\\[a-zA-Z]+', stripped))
                if latex_cmds >= 2:
                    return True
        return False

    def _is_block_code(self, content: str) -> bool:
        """Check if content is a block-level code block."""
        return content.startswith("```") or content.startswith("~~~")

    def _is_block_image(self, content: str) -> bool:
        """Check if content is a block-level image."""
        return bool(re.match(r'^!\[', content))

    def _is_table(self, content: str) -> bool:
        """Check if content represents a table."""
        lines = content.strip().split("\n")
        if len(lines) < 2:
            return False
        return all("|" in line for line in lines[:2])
