"""Pandoc parser implementation."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from document_semantic.observability.logger import get_logger

from .protocol import (
    Attachment,
    IntermediateBlock,
    IntermediateResult,
    Parser,
    ParserDependencyError,
    ParserError,
)
from .registry import ParserRegistry

logger = get_logger(__name__)

PANDOC_BINARY = "pandoc"


def _pandoc_available() -> bool:
    """Check if pandoc is available on the system PATH."""
    return shutil.which(PANDOC_BINARY) is not None


class PandocParser(Parser):
    """Parser that invokes pandoc to convert DOCX to intermediate markdown.

    Uses pandoc's native DOCX reader to produce markdown output, extracting
    images as separate files.
    """

    @property
    def name(self) -> str:
        return "pandoc"

    def parse(self, docx_path: Path) -> IntermediateResult:
        """Parse a DOCX file using pandoc.

        Args:
            docx_path: Absolute path to the DOCX file.

        Returns:
            IntermediateResult with markdown blocks and image attachments.

        Raises:
            ParserDependencyError: If pandoc is not installed.
        """
        if not _pandoc_available():
            raise ParserDependencyError(
                parser_name="pandoc",
                dependency=PANDOC_BINARY,
                message=(
                    "pandoc is not installed. Install it from https://pandoc.org/installing.html "
                    "or use the 'python-docx' parser instead."
                ),
            )

        logger.info(f"[parsing:pandoc] Converting {docx_path} with pandoc")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            media_dir = tmpdir_path / "media"
            media_dir.mkdir()
            output_md = tmpdir_path / "output.md"

            # Run pandoc: extract markdown and media
            result = subprocess.run(
                [
                    PANDOC_BINARY,
                    str(docx_path),
                    "-t", "markdown",
                    "--extract-media", str(media_dir),
                    "-o", str(output_md),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(f"[parsing:pandoc] pandoc failed: {result.stderr}")
                raise ParserError(f"pandoc conversion failed: {result.stderr}")

            # Read the markdown output
            md_content = output_md.read_text(encoding="utf-8")

            # Collect image attachments
            attachments: list[Attachment] = []
            if media_dir.exists():
                for img_path in media_dir.rglob("*"):
                    if img_path.is_file():
                        att_id = f"image_{len(attachments)}"
                        attachments.append(
                            Attachment(
                                id=att_id,
                                path=str(img_path),
                                mime_type=None,  # Could be inferred from extension
                            )
                        )
                        logger.debug(f"[parsing:pandoc] Attachment: {att_id} -> {img_path.name}")

            # Split markdown into blocks (separated by blank lines)
            raw_blocks = md_content.strip().split("\n\n")
            blocks: list[IntermediateBlock] = []
            for block_text in raw_blocks:
                block_text = block_text.strip()
                if not block_text:
                    continue
                # Infer style hint from markdown syntax
                style_hint = _infer_style_hint(block_text)
                logger.debug(f"[parsing:pandoc] Block: style={style_hint}, len={len(block_text)}")
                blocks.append(
                    IntermediateBlock(content=block_text, style_hint=style_hint)
                )

            logger.info(
                f"[parsing:pandoc] Complete: {len(blocks)} blocks, {len(attachments)} attachments"
            )
            return IntermediateResult(
                blocks=blocks,
                metadata={"source_path": str(docx_path)},
                attachments=attachments,
            )


def _infer_style_hint(text: str) -> str | None:
    """Infer a style hint from markdown syntax patterns."""
    if text.startswith("# "):
        return "Heading1"
    elif text.startswith("## "):
        return "Heading2"
    elif text.startswith("### "):
        return "Heading3"
    elif text.startswith("#### "):
        return "Heading4"
    elif text.startswith("##### "):
        return "Heading5"
    elif text.startswith("###### "):
        return "Heading6"
    elif text.startswith("- ") or text.startswith("* "):
        return "ListBullet"
    elif text.startswith("|"):
        return "Table"
    elif text.startswith("```"):
        return "CodeBlock"
    elif text.startswith("$") and text.endswith("$"):
        return "Formula"
    return "Normal"


# Auto-register
ParserRegistry.register("pandoc", PandocParser)
