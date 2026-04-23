"""Markdown-it parser implementation.

Chains pandoc (DOCX → markdown) with markdown-it-py (markdown → AST)
to produce structured IntermediateResult with accurate style hints
and image attachment extraction.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from markdown_it import MarkdownIt

from document_semantic.core.exceptions import ParserDependencyError, ParserError
from document_semantic.core.logger import get_logger
from document_semantic.models.processor_output import ProcessorConfig, ProcessResult
from document_semantic.services.parsers.protocol import (
    Attachment,
    IntermediateBlock,
    IntermediateResult,
    Parser,
)
from document_semantic.services.parsers.registry import ParserRegistry
from document_semantic.utils.markdown_generator import MarkdownGenerator

logger = get_logger(__name__)

PANDOC_BINARY = "pandoc"

# Mapping from markdown-it token tags to style hints
_TOKEN_TAG_TO_STYLE: dict[str, str] = {
    "h1": "Heading1",
    "h2": "Heading2",
    "h3": "Heading3",
    "h4": "Heading4",
    "h5": "Heading5",
    "h6": "Heading6",
    "bullet_list": "ListBullet",
    "ordered_list": "ListNumbered",
    "table": "Table",
    "fence": "CodeBlock",
    "code_block": "CodeBlock",
    "blockquote": "BlockQuote",
    "hr": "ThematicBreak",
}


def _pandoc_available() -> bool:
    """Check if pandoc is available on the system PATH."""
    return shutil.which(PANDOC_BINARY) is not None


def _markdown_it_available() -> bool:
    """Check if markdown-it-py is available."""
    try:
        from markdown_it import MarkdownIt  # noqa: F401

        return True
    except ImportError:
        return False


class MarkdownitParser(Parser):
    """Parser that chains pandoc → markdown → markdown-it AST → IntermediateResult.

    Uses pandoc to convert DOCX to markdown, then parses the markdown with
    markdown-it-py to produce structured blocks with accurate style hints
    derived from token types.
    """

    @property
    def name(self) -> str:
        return "markdownit"

    def parse(self, docx_path: Path, skip_image_ocr: bool = False) -> IntermediateResult:
        """Parse a DOCX file using pandoc + markdown-it.

        Args:
            docx_path: Absolute path to the DOCX file.

        Returns:
            IntermediateResult with structured blocks and image attachments.

        Raises:
            ParserDependencyError: If pandoc or markdown-it-py is not available.
            ParserError: If pandoc conversion fails.
        """
        if not _pandoc_available():
            raise ParserDependencyError(
                parser_name="markdownit",
                dependency=PANDOC_BINARY,
                message=(
                    "pandoc is not installed. The markdownit parser requires pandoc "
                    "to convert DOCX to markdown. Install from https://pandoc.org/installing.html"
                ),
            )

        if not _markdown_it_available():
            raise ParserDependencyError(
                parser_name="markdownit",
                dependency="markdown-it-py",
                message=("markdown-it-py is not installed. Install with: pip install markdown-it-py"),
            )

        logger.info(f"[parsing:markdownit] Converting {docx_path} with pandoc + markdown-it")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            media_dir = tmpdir_path / "media"
            media_dir.mkdir()
            output_md = tmpdir_path / "output.md"

            # Step 1: pandoc converts DOCX → markdown
            result = subprocess.run(
                [
                    PANDOC_BINARY,
                    str(docx_path),
                    "-t",
                    "markdown",
                    "--extract-media",
                    str(media_dir),
                    "-o",
                    str(output_md),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"[parsing:markdownit] pandoc failed: {result.stderr}")
                raise ParserError(f"pandoc conversion failed: {result.stderr}")

            md_content = output_md.read_text(encoding="utf-8")

            # Step 2: markdown-it parses markdown into token AST
            md = MarkdownIt("gfm-like")
            tokens = md.parse(md_content)

            # Step 3: Map tokens to IntermediateBlock items
            blocks, attachments = self._tokens_to_blocks(tokens, media_dir)

            logger.info(f"[parsing:markdownit] Complete: {len(blocks)} blocks, {len(attachments)} attachments")
            return IntermediateResult(
                blocks=blocks,
                metadata={"source_path": str(docx_path)},
                attachments=attachments,
            )

    def process(
        self,
        docx_path: Path,
        output_dir: Path,
        config: ProcessorConfig | None = None,
        skip_image_ocr: bool = False,
    ) -> ProcessResult:
        """Parse and process a DOCX file into rich Markdown + placeholder Markdown + resources.

        Calls parse() internally, then uses MarkdownGenerator to produce both
        rich Markdown output and placeholder Markdown with XML tags,
        resource directory, and JSON mapping.

        Args:
            docx_path: Absolute path to the DOCX file.
            output_dir: Directory to write output files to.
            config: Processor configuration options.

        Returns:
            ProcessResult with paths to the generated files.
        """
        if config is None:
            config = ProcessorConfig()

        intermediate = self.parse(docx_path)

        gen = MarkdownGenerator(
            intermediate,
            output_resources=config.output_resources,
        )

        rich_md_path, placeholder_md_path, resources_dir, json_path = gen.generate_both(
            output_dir,
            source_path=str(docx_path),
            parser_name=self.name,
        )

        return ProcessResult(
            rich_markdown_path=rich_md_path if config.output_markdown else None,
            placeholder_markdown_path=placeholder_md_path if config.output_markdown else None,
            resources_dir=resources_dir,
            resources_json_path=json_path,
            metadata=dict(intermediate.metadata),
        )

    def _tokens_to_blocks(self, tokens: list, media_dir: Path) -> tuple[list[IntermediateBlock], list[Attachment]]:
        """Convert markdown-it token stream to IntermediateBlock list.

        Walks the token stream sequentially, grouping related tokens
        (open/content/close) into single blocks.
        """
        blocks: list[IntermediateBlock] = []
        attachments: list[Attachment] = []
        i = 0

        while i < len(tokens):
            token = tokens[i]
            block = None

            if token.type in ("heading_open",):
                # Heading: collect inline content until heading_close
                block, i = self._collect_block_content(tokens, i)
            elif token.type == "paragraph_open":
                # Paragraph: collect inline content until paragraph_close
                block, i = self._collect_block_content(tokens, i)
            elif token.type == "fence":
                # Fenced code block
                content = token.content or ""
                style_hint = _TOKEN_TAG_TO_STYLE.get(token.tag, "CodeBlock")
                lang = token.info or ""
                if lang:
                    content = f"```{lang}\n{content}```" if content else f"```{lang}"
                block = IntermediateBlock(
                    content=content.strip(),
                    style_hint=style_hint,
                )
            elif token.type == "code_block":
                content = token.content or ""
                block = IntermediateBlock(
                    content=content.strip(),
                    style_hint="CodeBlock",
                )
            elif token.type == "hr":
                block = IntermediateBlock(
                    content="---",
                    style_hint="ThematicBreak",
                )
            elif token.type == "bullet_list_open" or token.type == "ordered_list_open":
                block, i = self._collect_list_content(tokens, i)
            elif token.type == "table_open" or token.type == "blockquote_open":
                block, i = self._collect_block_content(tokens, i)
            elif token.type == "image":
                # Image token: create attachment
                att = self._create_image_attachment(token, media_dir, len(attachments))
                if att:
                    attachments.append(att)
                # Also create a block for the image reference
                alt = token.attrs.get("alt", "") or token.children[0].content if token.children else ""
                block = IntermediateBlock(
                    content=f"![{alt}]",
                    style_hint="Image",
                )

            if block is not None:
                blocks.append(block)
            i += 1

        return blocks, attachments

    def _collect_block_content(self, tokens: list, start_idx: int) -> tuple[IntermediateBlock, int]:
        """Collect content tokens between open/close token pairs."""
        open_token = tokens[start_idx]
        content_parts = []
        i = start_idx + 1

        # Determine the matching close token type
        close_type = open_token.type.replace("_open", "_close")

        while i < len(tokens) and tokens[i].type != close_type:
            tok = tokens[i]
            if tok.type == "inline":
                # Inline token: extract text content
                content_parts.append(tok.content or "")
            elif tok.type == "text":
                content_parts.append(tok.content or "")
            elif tok.type == "image":
                # Image within block
                alt = tok.attrs.get("alt", "") or ""
                content_parts.append(f"![{alt}]")
            elif tok.type == "code_inline":
                content_parts.append(f"`{tok.content or ''}`")
            elif tok.type in ("strong_open", "em_open"):
                # Handle emphasis markers - will be in inline content
                pass
            i += 1

        content = " ".join(part for part in content_parts if part).strip()

        # Derive style hint from the open token tag
        tag = open_token.tag  # e.g., "h1", "p", "ul", "table"
        style_hint = _TOKEN_TAG_TO_STYLE.get(tag, "Normal")

        # For paragraphs, try to infer more specific style
        if tag == "p" and content:
            style_hint = _infer_paragraph_style(content)

        block = IntermediateBlock(content=content, style_hint=style_hint)
        return block, i

    def _collect_list_content(self, tokens: list, start_idx: int) -> tuple[IntermediateBlock, int]:
        """Collect list items into a single block."""
        open_token = tokens[start_idx]
        items = []
        i = start_idx + 1
        close_type = open_token.type.replace("_open", "_close")
        prefix = "- " if open_token.type == "bullet_list_open" else "1. "

        while i < len(tokens) and tokens[i].type != close_type:
            if tokens[i].type == "list_item_open":
                item_content, i = self._collect_block_content(tokens, i)
                if item_content.content:
                    items.append(f"{prefix}{item_content.content}")
            else:
                i += 1

        content = "\n".join(items)
        style_hint = _TOKEN_TAG_TO_STYLE.get(open_token.tag, "ListBullet")
        return IntermediateBlock(content=content, style_hint=style_hint), i - 1

    def _create_image_attachment(self, token, media_dir: Path, index: int) -> Attachment | None:
        """Create an Attachment from an image token."""
        src = token.attrs.get("src", "")
        if not src:
            return None

        # If src is a relative path from pandoc's media extraction
        if media_dir.exists():
            # Try to find the file in media_dir
            filename = Path(src).name
            for img_path in media_dir.rglob(filename):
                if img_path.is_file():
                    mime_type = _infer_mime_type(img_path.suffix)
                    return Attachment(
                        id=f"image_{index}",
                        path=str(img_path),
                        mime_type=mime_type,
                    )

        # Fallback: use src path as-is
        mime_type = _infer_mime_type(Path(src).suffix)
        return Attachment(
            id=f"image_{index}",
            path=src,
            mime_type=mime_type,
        )


def _infer_paragraph_style(content: str) -> str:
    """Infer a more specific style hint from paragraph content patterns."""
    if content.startswith("$$") and content.endswith("$$"):
        return "Formula"
    if content.startswith("|") and "|" in content:
        return "Table"
    return "Normal"


def _infer_mime_type(suffix: str) -> str | None:
    """Infer MIME type from file extension."""
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }
    return mime_map.get(suffix.lower())


# Auto-register
ParserRegistry.register("markdownit", MarkdownitParser)
