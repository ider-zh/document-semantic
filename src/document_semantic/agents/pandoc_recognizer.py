"""Pandoc-specific semantic recognizer using Strands Agent."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger
from document_semantic.models.blocks import (
    AbstractBlock,
    AbstractHeadBlock,
    Block,
    CodeBlock,
    ConclusionBlock,
    ConclusionHeadBlock,
    HeadingBlock,
    ImageBlock,
    ImageDescriptionBlock,
    ListItemBlock,
    ReferenceBlock,
    ReferenceHeadBlock,
    TableBlock,
    TableDescriptionBlock,
    TextBlock,
    TitleBlock,
)
from document_semantic.models.semantic_document import (
    Attachment,
    DocumentMetadata,
    SemanticDocument,
)
from document_semantic.services.parsers.protocol import IntermediateBlock, IntermediateResult

from .protocol import SemanticRecognizer

logger = get_logger(__name__)


class SemanticType(str, Enum):
    """Semantic types for document blocks."""

    TITLE = "title"
    AUTHOR = "author"
    KEYWORD = "keyword"
    HEAD1 = "head1"
    HEAD2 = "head2"
    HEAD3 = "head3"
    TEXT = "text"
    ABSTRACT_HEAD = "abstract_head"
    ABSTRACT = "abstract"
    CONCLUSION_HEAD = "conclusion_head"
    CONCLUSION = "conclusion"
    REFERENCE_HEAD = "reference_head"
    REFERENCE = "reference"
    FORMULA = "formula"
    CODE = "code"
    IMAGE = "image"
    TABLE = "table"
    LIST = "list"
    IMAGE_DESCRIPTION = "image_description"
    TABLE_DESCRIPTION = "table_description"


class BlockAnnotation(BaseModel):
    """Annotation for a single block."""

    block_id: int = Field(description="The integer ID of the block")
    semantic_type: SemanticType = Field(description="The recognized semantic type of the block")


class DocumentSemantics(BaseModel):
    """Collection of block annotations."""

    annotations: list[BlockAnnotation] = Field(description="List of annotations for the provided blocks")


class PandocRecognizer(SemanticRecognizer):
    """Recognizer specialized for Pandoc markdown output using Strands Agent."""

    def __init__(
        self,
    ):
        # The agent can be customized if needed, currently using default Strands agent
        self.agent = Agent(
            model=OpenAIModel(
                client_args={
                    "api_key": settings.recognizer_model_api_key,
                    "base_url": settings.recognizer_model_provider_url,
                    "timeout": settings.recognizer_modelizer_model_timeout,
                },
                model_id=settings.recognizer_model_id,
            )
        )

    @property
    def name(self) -> str:
        return "pandoc_agent"

    def _clean_markdown_text(self, text: str) -> str:
        """Remove markdown styling to check if text is empty."""
        cleaned = re.sub(r"[*_>]+", "", text)
        return cleaned.strip()

    def _preprocess_blocks(self, blocks: list[IntermediateBlock]) -> list[IntermediateBlock]:
        """Preprocess blocks: handle Pandoc blockquote issue and empty blocks."""
        if not blocks:
            return []

        # Count blockquote prefixed blocks
        blockquote_count = sum(1 for b in blocks if b.content.startswith("> ") or b.content.startswith(">"))
        total_blocks = len(blocks)

        strip_quotes = False
        if total_blocks > 0 and (blockquote_count / total_blocks) >= 0.1:
            logger.info(
                f"[pandoc_agent] Detected high ratio of blockquotes ({blockquote_count}/{total_blocks}). Stripping '> '."
            )
            strip_quotes = True

        processed: list[IntermediateBlock] = []
        for b in blocks:
            content = b.content
            if strip_quotes:
                # Remove leading '> ' or '>' from each line
                lines = content.split("\n")
                cleaned_lines = []
                for line in lines:
                    if line.startswith("> "):
                        cleaned_lines.append(line[2:])
                    elif line.startswith(">"):
                        cleaned_lines.append(line[1:])
                    else:
                        cleaned_lines.append(line)
                content = "\n".join(cleaned_lines)

            # Re-split by \n\n because stripping blockquotes might expose internal block separators
            for sub_content in content.split("\n\n"):
                sub_content = sub_content.strip()
                if not self._clean_markdown_text(sub_content):
                    continue

                # Strip pandoc image dimensions like {width="..." height="..."}
                if sub_content.startswith("![") and re.search(r"\]\(.*\)", sub_content):
                    sub_content = re.sub(r"\{[^\}]+\}$", "", sub_content)

                processed.append(
                    IntermediateBlock(
                        content=sub_content,
                        style_hint=b.style_hint,
                        inline_elements=b.inline_elements,
                    )
                )

        return processed

    def _truncate_for_agent(self, text: str, max_len: int = 300) -> str:
        """Truncate long text to save context, preserving start and end."""
        if len(text) <= max_len:
            return text
        half = max_len // 2
        return f"{text[:half]} ... {text[-half:]}"

    def _pre_tag_blocks(self, blocks: list[IntermediateBlock]) -> dict[int, SemanticType]:
        """Apply heuristic rules to pre-tag obvious blocks."""
        tags: dict[int, SemanticType] = {}
        for i, b in enumerate(blocks):
            content = b.content.strip()
            # Image
            if content.startswith("![") and re.search(r"\]\(.*\)", content):
                tags[i] = SemanticType.IMAGE
                continue
            # Table (has | and newline)
            if "|" in content and "\n" in content and "-|-" in content:
                tags[i] = SemanticType.TABLE
                continue
            # Code
            if content.startswith("```"):
                tags[i] = SemanticType.CODE
                continue
            # Formula (block formula or single line formula)
            if (content.startswith("$$") and content.endswith("$$")) or (
                content.startswith("\\[") and content.endswith("\\]")
            ):
                tags[i] = SemanticType.FORMULA
                continue

            # Common Headings using keywords
            cleaned = self._clean_markdown_text(content).strip()
            if len(cleaned) < 50:
                lower_cleaned = cleaned.lower()
                # Remove common numbering patterns (e.g., "1. ", "1.", "I.", "(1)", "一、")
                text_no_num = re.sub(
                    r"^(?:\d+[\.、]\s*|[ivxIVX]+[\.、]\s*|[\(（]\d+[\)）]\s*|[一二三四五六七八九十]+[\.、]\s*)",
                    "",
                    lower_cleaned,
                ).strip()

                if text_no_num in ("摘要", "abstract"):
                    tags[i] = SemanticType.ABSTRACT_HEAD
                    continue
                if text_no_num in ("引文", "参考文献", "参考", "references", "reference"):
                    tags[i] = SemanticType.REFERENCE_HEAD
                    continue
                if text_no_num in ("结论", "结语", "总结", "conclusion", "conclusions"):
                    tags[i] = SemanticType.CONCLUSION_HEAD
                    continue

        return tags

    def recognize(self, intermediate: IntermediateResult) -> SemanticDocument:
        logger.info(f"[pandoc_agent] Starting recognition on {len(intermediate.blocks)} blocks")

        # 1. Pre-process blocks
        processed_blocks = self._preprocess_blocks(intermediate.blocks)
        if not processed_blocks:
            return SemanticDocument(blocks=[], attachments=[], metadata=DocumentMetadata())

        # 2. Rule-based pre-tagging
        pre_tags = self._pre_tag_blocks(processed_blocks)

        # 3. Agent recognition for remaining blocks
        blocks_to_infer = []
        for i, b in enumerate(processed_blocks):
            if i not in pre_tags:
                blocks_to_infer.append((i, b.content))

        inferred_tags: dict[int, SemanticType] = {}

        if blocks_to_infer:
            # Construct prompt
            prompt_lines = [
                "Analyze the following document blocks and identify their semantic type.",
                "Choose from: title, author, keyword, head1, head2, head3, text, abstract_head, abstract, "
                "conclusion_head, conclusion, reference_head, reference, formula, code, image, table, list, "
                "image_description, table_description.",
                "CRITICAL INSTRUCTIONS:",
                "- Numbered headings (e.g. '1. **Background**', '2.  **History**') must be classified as 'head1'.",
                "- '摘要' or 'Abstract' heading must be 'abstract_head', and the text paragraph following it is 'abstract'.",
                "- Text immediately below an image that describes the image must be 'image_description'.",
                "- Text immediately below a table that describes the table must be 'table_description'.",
                "Blocks are provided in '[ID] (type): Content' format. Long blocks may be truncated with '...'.",
                "Some blocks are already pre-tagged (e.g. image, table). You must infer the type for blocks marked as (unknown).\n",
            ]
            for i, b in enumerate(processed_blocks):
                truncated = self._truncate_for_agent(b.content)
                status = pre_tags.get(i, "unknown")
                if isinstance(status, SemanticType):
                    status = status.value
                prompt_lines.append(f"[{i}] ({status}): {truncated}")

            prompt = "\n".join(prompt_lines)

            try:
                logger.info(f"[pandoc_agent] Calling Strands Agent for {len(blocks_to_infer)} blocks")
                result = self.agent(
                    prompt,
                    structured_output_model=DocumentSemantics,
                    # We might need to pass model kwargs if supported, but agent default is fine
                )
                doc_semantics: DocumentSemantics = result.structured_output
                for ann in doc_semantics.annotations:
                    inferred_tags[ann.block_id] = ann.semantic_type
            except Exception as e:
                logger.error(f"[pandoc_agent] Agent inference failed: {e}")
                # Fallback to TEXT for failed ones
                for block_id, _ in blocks_to_infer:
                    inferred_tags[block_id] = SemanticType.TEXT

        # 4. Merge tags
        final_tags: dict[int, SemanticType] = {}
        for i in range(len(processed_blocks)):
            if i in pre_tags:
                final_tags[i] = pre_tags[i]
            elif i in inferred_tags:
                final_tags[i] = inferred_tags[i]
            else:
                final_tags[i] = SemanticType.TEXT

        # First block is always TITLE if not already set (or override)
        if 0 in final_tags and final_tags[0] not in (SemanticType.IMAGE, SemanticType.TABLE):
            final_tags[0] = SemanticType.TITLE

        # 5. Merge contiguous blocks of same type for specific types
        # Mergable types: FORMULA, CODE, LIST, TABLE
        mergeable_types = {SemanticType.FORMULA, SemanticType.CODE, SemanticType.LIST, SemanticType.TABLE}

        merged_blocks: list[tuple[SemanticType, str, IntermediateBlock]] = []

        current_type = None
        current_contents = []
        current_first_block = None

        for i, b in enumerate(processed_blocks):
            sem_type = final_tags[i]
            if sem_type in mergeable_types:
                if current_type == sem_type:
                    current_contents.append(b.content)
                else:
                    if current_type is not None:
                        merged_blocks.append((current_type, "\n\n".join(current_contents), current_first_block))
                    current_type = sem_type
                    current_contents = [b.content]
                    current_first_block = b
            else:
                if current_type is not None:
                    merged_blocks.append((current_type, "\n\n".join(current_contents), current_first_block))
                    current_type = None
                    current_contents = []
                    current_first_block = None
                merged_blocks.append((sem_type, b.content, b))

        if current_type is not None:
            merged_blocks.append((current_type, "\n\n".join(current_contents), current_first_block))

        # 6. Map to standard Block models
        final_standard_blocks: list[Block] = []
        for sem_type, content, orig_block in merged_blocks:
            standard_block = self._map_to_standard_block(sem_type, content, orig_block)
            final_standard_blocks.append(standard_block)

        # Attachments and metadata
        attachments = [Attachment(id=a.id, path=a.path, mime_type=a.mime_type) for a in intermediate.attachments]
        metadata = DocumentMetadata(
            title=intermediate.metadata.get("title"),
            author=intermediate.metadata.get("author"),
            doc_type=intermediate.metadata.get("doc_type"),
            source_path=intermediate.metadata.get("source_path"),
        )

        logger.info(f"[pandoc_agent] Complete: produced {len(final_standard_blocks)} blocks")
        sem_doc = SemanticDocument(blocks=final_standard_blocks, attachments=attachments, metadata=metadata)

        # Dump to pandoc_agent_output.json
        try:
            from pathlib import Path

            out_file = Path("pandoc_agent_output.json")
            source_path = intermediate.metadata.get("source_path", "")
            if source_path:
                sp = Path(source_path)
                if sp.parent.name == "docx" and sp.parent.parent.name == "tests":
                    out_dir = sp.parent / "output" / f"{sp.name}_pandoc_pandoc_agent"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    out_file = out_dir / "pandoc_agent_output.json"

            with open(out_file, "w", encoding="utf-8") as f:
                f.write(sem_doc.model_dump_json(indent=2))
            logger.info(f"Saved recognition result JSON to {out_file}")
        except Exception as e:
            logger.error(f"Failed to dump JSON: {e}")

        return sem_doc

    def _map_to_standard_block(self, sem_type: SemanticType, content: str, orig_block: IntermediateBlock) -> Block:
        """Map our internal semantic type to the standard Block models."""
        inlines = orig_block.inline_elements

        if sem_type == SemanticType.TITLE:
            return TitleBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.HEAD1:
            return HeadingBlock(level=1, content=content.lstrip("# "), inline_elements=inlines)
        elif sem_type == SemanticType.HEAD2:
            return HeadingBlock(level=2, content=content.lstrip("# "), inline_elements=inlines)
        elif sem_type == SemanticType.HEAD3:
            return HeadingBlock(level=3, content=content.lstrip("# "), inline_elements=inlines)
        elif sem_type == SemanticType.ABSTRACT_HEAD:
            return AbstractHeadBlock(level=1, content=content.lstrip("# "), inline_elements=inlines)
        elif sem_type == SemanticType.ABSTRACT:
            return AbstractBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.CONCLUSION_HEAD:
            return ConclusionHeadBlock(level=1, content=content.lstrip("# "), inline_elements=inlines)
        elif sem_type == SemanticType.CONCLUSION:
            return ConclusionBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.REFERENCE_HEAD:
            return ReferenceHeadBlock(level=1, content=content.lstrip("# "), inline_elements=inlines)
        elif sem_type == SemanticType.REFERENCE:
            return ReferenceBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.LIST:
            # We don't do full list parsing here, just map it as unordered for now
            return ListItemBlock(content=content, list_type="unordered", inline_elements=inlines)
        elif sem_type == SemanticType.TABLE:
            return TableBlock(content=content)
        elif sem_type == SemanticType.CODE:
            return CodeBlock(content=content)
        elif sem_type == SemanticType.FORMULA:
            # Just mapped as a TextBlock containing the formula since we don't have a FormulaBlock
            return TextBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.IMAGE:
            return ImageBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.IMAGE_DESCRIPTION:
            return ImageDescriptionBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.TABLE_DESCRIPTION:
            return TableDescriptionBlock(content=content, inline_elements=inlines)
        elif sem_type == SemanticType.AUTHOR or sem_type == SemanticType.KEYWORD:
            return TextBlock(content=content, inline_elements=inlines)
        else:
            return TextBlock(content=content, inline_elements=inlines)


from .router_and_llm import register_recognizer

# Auto-register
register_recognizer("pandoc_agent", PandocRecognizer)
