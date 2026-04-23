"""Pipeline orchestration: wires parser -> recognizer -> output."""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from document_semantic.agents.protocol import SemanticRecognizer
from document_semantic.agents.router_and_llm import create_recognizer
from document_semantic.core.config import Settings
from document_semantic.core.logger import get_logger
from document_semantic.models.processor_output import ProcessorConfig, ProcessResult
from document_semantic.models.semantic_document import SemanticDocument
from document_semantic.services.parsers.protocol import IntermediateResult, Parser
from document_semantic.services.parsers.registry import ParserRegistry

logger = get_logger(__name__)


@dataclass(frozen=True)
class StageTrace:
    """Trace entry for a single pipeline stage."""

    stage: str
    duration_seconds: float
    input_summary: str
    output_summary: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class PipelineTrace:
    """Collects trace entries for all pipeline stages."""

    def __init__(self):
        self._entries: list[StageTrace] = []

    def add(self, entry: StageTrace) -> None:
        """Add a stage trace entry."""
        self._entries.append(entry)

    @property
    def entries(self) -> list[StageTrace]:
        """Return all trace entries in order."""
        return list(self._entries)

    def summary(self) -> str:
        """Return a human-readable summary of the trace."""
        lines = ["Pipeline Trace:"]
        for entry in self._entries:
            status = "OK" if not entry.errors else "ERRORS"
            line = (
                f"  [{entry.stage}] {entry.duration_seconds:.3f}s - {status}\n"
                f"    Input:  {entry.input_summary}\n"
                f"    Output: {entry.output_summary}"
            )
            if entry.warnings:
                line += f"\n    Warnings: {', '.join(entry.warnings)}"
            if entry.errors:
                line += f"\n    Errors: {', '.join(entry.errors)}"
            lines.append(line)
        return "\n".join(lines)


class Pipeline:
    """Main pipeline that wires parser and recognizer together.

    Usage:
        config = Settings.load()
        pipeline = Pipeline.from_config(config)
        result = pipeline.run(Path("document.docx"))
        trace = pipeline.get_trace()
    """

    def __init__(
        self,
        parser: Parser,
        recognizer: SemanticRecognizer | None = None,
        config: Settings | None = None,
        post_processor: SemanticRecognizer | None = None,
    ):
        self._parser = parser
        self._recognizer = recognizer  # Deprecated, kept for backward compatibility
        self._config = config or Settings()
        self._trace = PipelineTrace()
        self._post_processor = post_processor  # Optional recognizer for post-processing

        if recognizer is not None:
            warnings.warn(
                "The 'recognizer' parameter is deprecated and will be removed in a future version. "
                "Use 'post_processor' instead for optional semantic enrichment.",
                DeprecationWarning,
                stacklevel=2,
            )

    @classmethod
    def from_config(cls, config: Settings) -> Pipeline:
        """Build a pipeline from configuration.

        Args:
            config: Pipeline configuration specifying parser and recognizer.

        Returns:
            A configured Pipeline instance.
        """
        parser = ParserRegistry.get(config.parser)
        recognizer = create_recognizer(config.recognizer, config.recognizer_config)
        logger.info(f"[pipeline] Created pipeline: parser={config.parser}, recognizer={config.recognizer}")
        return cls(parser=parser, recognizer=recognizer, config=config)

    def run(self, docx_path: Path) -> SemanticDocument:
        """Execute the full pipeline: parse -> recognize -> output.

        Args:
            docx_path: Path to the DOCX file.

        Returns:
            A SemanticDocument with full semantic annotation.
        """
        logger.info(f"[pipeline] Starting pipeline for {docx_path}")
        self._trace = PipelineTrace()  # Reset trace

        # Stage 1: Parse
        intermediate = self._parse(docx_path)

        # Stage 2: Recognize
        semantic_doc = self._recognize(intermediate)

        logger.info(f"[pipeline] Pipeline complete: {len(semantic_doc.blocks)} blocks")
        return semantic_doc

    def run_with_processor(
        self,
        docx_path: Path,
        output_dir: Path,
        config: ProcessorConfig | None = None,
    ) -> ProcessResult:
        """Execute the processor workflow: parse -> process -> file output.

        This is the new primary workflow that produces Markdown output with
        XML placeholders, resource directory, and JSON mapping file.

        Args:
            docx_path: Path to the DOCX file.
            output_dir: Directory to write output files to.
            config: Processor configuration options.

        Returns:
            ProcessResult with paths to the generated files.
        """
        logger.info(f"[pipeline] Starting processor workflow for {docx_path}")
        self._trace = PipelineTrace()  # Reset trace

        # Stage 1: Parse
        intermediate = self._parse(docx_path)

        # Stage 2: Optional post-processing recognizer
        if self._post_processor is not None:
            logger.info("[pipeline] Running post-processor for semantic enrichment")
            self._recognize(intermediate)

        # Stage 3: Process to Markdown + resources
        result = self._process_output(intermediate, docx_path, output_dir, config)

        logger.info(
            f"[pipeline] Processor workflow complete: md={result.markdown_path}, resources={result.resources_dir}"
        )
        return result

    def _process_output(
        self,
        intermediate: IntermediateResult,
        docx_path: Path,
        output_dir: Path,
        config: ProcessorConfig | None = None,
    ) -> ProcessResult:
        """Execute the processor output generation stage."""
        from document_semantic.utils.markdown_generator import MarkdownGenerator

        if config is None:
            config = ProcessorConfig()

        logger.info("[pipeline:processor] stage started")
        start = time.monotonic()
        warnings_list: list[str] = []
        errors: list[str] = []

        try:
            gen = MarkdownGenerator(
                intermediate,
                output_resources=config.output_resources,
            )

            rich_md_path, placeholder_md_path, resources_dir, json_path = gen.generate_both(
                output_dir,
                source_path=str(docx_path),
                parser_name=self._parser.name,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            error_msg = f"Processor output generation failed: {e}"
            logger.error(f"[pipeline:processor] {error_msg}")
            errors.append(error_msg)
            self._trace.add(
                StageTrace(
                    stage="processor",
                    duration_seconds=elapsed,
                    input_summary=str(docx_path),
                    output_summary="FAILED",
                    warnings=warnings_list,
                    errors=errors,
                )
            )
            raise

        elapsed = time.monotonic() - start
        summary = (
            f"rich_md={rich_md_path}, placeholder_md={placeholder_md_path}, resources={resources_dir}, json={json_path}"
        )
        logger.info(f"[pipeline:processor] stage completed ({elapsed:.3f}s): {summary}")

        self._trace.add(
            StageTrace(
                stage="processor",
                duration_seconds=elapsed,
                input_summary=str(docx_path),
                output_summary=summary,
                warnings=warnings_list,
                errors=errors,
            )
        )

        return ProcessResult(
            rich_markdown_path=rich_md_path if config.output_markdown else None,
            placeholder_markdown_path=placeholder_md_path if config.output_markdown else None,
            resources_dir=resources_dir,
            resources_json_path=json_path,
            metadata=dict(intermediate.metadata),
        )

    def _parse(self, docx_path: Path) -> IntermediateResult:
        """Execute the parsing stage."""
        logger.info("[pipeline:parsing] stage started")
        start = time.monotonic()
        warnings: list[str] = []
        errors: list[str] = []

        try:
            skip_image_ocr = getattr(self._config, "mineru_skip_image_ocr", False)
            result = self._parser.parse(docx_path, skip_image_ocr=skip_image_ocr)
        except Exception as e:
            elapsed = time.monotonic() - start
            error_msg = f"Parser {self._parser.name} failed: {e}"
            logger.error(f"[pipeline:parsing] {error_msg}")
            errors.append(error_msg)
            self._trace.add(
                StageTrace(
                    stage="parsing",
                    duration_seconds=elapsed,
                    input_summary=str(docx_path),
                    output_summary="FAILED",
                    warnings=warnings,
                    errors=errors,
                )
            )
            raise

        elapsed = time.monotonic() - start
        summary = f"{len(result.blocks)} blocks, {len(result.attachments)} attachments"
        logger.info(f"[pipeline:parsing] stage completed ({elapsed:.3f}s): {summary}")

        self._trace.add(
            StageTrace(
                stage="parsing",
                duration_seconds=elapsed,
                input_summary=str(docx_path),
                output_summary=summary,
                warnings=warnings,
                errors=errors,
            )
        )
        return result

    def _recognize(self, intermediate: IntermediateResult) -> SemanticDocument:
        """Execute the recognition stage."""
        logger.info("[pipeline:recognition] stage started")
        start = time.monotonic()
        warnings: list[str] = []
        errors: list[str] = []

        try:
            result = self._recognizer.recognize(intermediate)
        except Exception as e:
            elapsed = time.monotonic() - start
            error_msg = f"Recognizer {self._recognizer.name} failed: {e}"
            logger.error(f"[pipeline:recognition] {error_msg}")
            errors.append(error_msg)
            self._trace.add(
                StageTrace(
                    stage="recognition",
                    duration_seconds=elapsed,
                    input_summary=f"{len(intermediate.blocks)} blocks",
                    output_summary="FAILED",
                    warnings=warnings,
                    errors=errors,
                )
            )
            raise

        elapsed = time.monotonic() - start
        summary = f"{len(result.blocks)} semantic blocks, version={result.schema_version}"
        logger.info(f"[pipeline:recognition] stage completed ({elapsed:.3f}s): {summary}")

        self._trace.add(
            StageTrace(
                stage="recognition",
                duration_seconds=elapsed,
                input_summary=f"{len(intermediate.blocks)} blocks",
                output_summary=summary,
                warnings=warnings,
                errors=errors,
            )
        )
        return result

    def get_trace(self) -> PipelineTrace:
        """Return the trace from the most recent pipeline run.

        Returns:
            PipelineTrace with entries for all completed stages.
        """
        return self._trace

    def print_result(self, semantic_doc: SemanticDocument) -> None:
        """Print the semantic document according to configured verbosity."""
        verbosity = self._config.verbosity
        if verbosity == "summary":
            self._print_summary(semantic_doc)
        elif verbosity == "preview":
            self._print_preview(semantic_doc)
        else:  # full
            self._print_full(semantic_doc)

    def _print_summary(self, doc: SemanticDocument) -> None:
        """Print block type counts only."""
        from collections import Counter

        counts = Counter(block.type for block in doc.blocks)
        parts = [f"{t}: {c}" for t, c in counts.items()]
        logger.info(f"[output:summary] {', '.join(parts)}")

    def _print_preview(self, doc: SemanticDocument) -> None:
        """Print block type and first 100 chars of content."""
        for block in doc.blocks:
            preview = block.content[:100] + ("..." if len(block.content) > 100 else "")
            logger.info(f"[output:preview] [{block.type}] {preview}")

    def _print_full(self, doc: SemanticDocument) -> None:
        """Print full semantic document."""
        for block in doc.blocks:
            inline_count = len(block.inline_elements)
            logger.info(f"[output:full] [{block.type}] id={block.id} (inlines={inline_count})\n{block.content}")
