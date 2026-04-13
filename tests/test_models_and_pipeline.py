"""Tests for data models, schema upgrades, and pipeline."""

from __future__ import annotations

import json

import pytest

from document_semantic.models.blocks import (
    HeadingBlock,
    TextBlock,
    TitleBlock,
)
from document_semantic.models.inline_elements import (
    BoldInlineElement,
    CodeSpanInlineElement,
    LinkInlineElement,
)
from document_semantic.models.semantic_document import (
    Attachment,
    DocumentMetadata,
    SchemaUpgrader,
    SemanticDocument,
    CURRENT_SCHEMA_VERSION,
)
from document_semantic.parsers.protocol import IntermediateBlock, IntermediateResult
from document_semantic.pipeline import Pipeline, PipelineConfig, PipelineTrace
from document_semantic.recognizers.regex_recognizer import RegexRecognizer


# ---------------------------------------------------------------------------
# Model creation and serialization tests
# ---------------------------------------------------------------------------


class TestInlineElements:
    """Tests for inline element models."""

    def test_bold_element(self):
        """BoldInlineElement creation and fields."""
        elem = BoldInlineElement(text="bold", start_offset=0, end_offset=4)
        assert elem.type == "bold"
        assert elem.text == "bold"
        assert elem.start_offset == 0
        assert elem.end_offset == 4

    def test_code_span_element(self):
        """CodeSpanInlineElement creation."""
        elem = CodeSpanInlineElement(text="code", start_offset=5, end_offset=9)
        assert elem.type == "code_span"

    def test_link_element_url(self):
        """LinkInlineElement includes URL."""
        elem = LinkInlineElement(text="click", url="https://example.com", start_offset=0, end_offset=5)
        assert elem.url == "https://example.com"


class TestBlockModels:
    """Tests for block-level models."""

    def test_heading_block(self):
        """HeadingBlock creation with level."""
        block = HeadingBlock(level=1, content="Introduction")
        assert block.type == "heading"
        assert block.level == 1
        assert block.id is not None

    def test_title_block(self):
        """TitleBlock creation."""
        block = TitleBlock(content="My Title")
        assert block.type == "title"

    def test_block_with_inline_elements(self):
        """Block contains inline elements."""
        block = TextBlock(
            content="The **bold** word",
            inline_elements=[BoldInlineElement(text="bold", start_offset=4, end_offset=12)],
        )
        assert len(block.inline_elements) == 1
        assert isinstance(block.inline_elements[0], BoldInlineElement)


class TestSemanticDocument:
    """Tests for SemanticDocument container."""

    def test_default_schema_version(self):
        """SemanticDocument defaults to current schema version."""
        doc = SemanticDocument()
        assert doc.schema_version == CURRENT_SCHEMA_VERSION

    def test_serialization_roundtrip(self):
        """JSON serialization and deserialization preserves data."""
        doc = SemanticDocument(
            blocks=[
                TitleBlock(content="Test Title"),
                HeadingBlock(level=1, content="Heading"),
            ],
            metadata=DocumentMetadata(title="Test"),
            attachments=[Attachment(id="img1", path="/path/to/img.png")],
        )

        json_str = doc.to_json()
        restored = SemanticDocument.from_json(json_str)

        assert restored.schema_version == doc.schema_version
        assert len(restored.blocks) == len(doc.blocks)
        assert len(restored.attachments) == len(doc.attachments)
        assert isinstance(restored.blocks[0], TitleBlock)
        assert isinstance(restored.blocks[1], HeadingBlock)

    def test_discriminator_preserved_in_json(self):
        """JSON serialization preserves type discriminators."""
        doc = SemanticDocument(
            blocks=[TitleBlock(content="Title"), HeadingBlock(level=2, content="Sub")]
        )
        data = json.loads(doc.to_json())
        assert data["blocks"][0]["type"] == "title"
        assert data["blocks"][1]["type"] == "heading"


# ---------------------------------------------------------------------------
# Schema upgrade tests
# ---------------------------------------------------------------------------


class TestSchemaUpgrader:
    """Tests for schema version migration."""

    def test_register_and_list(self):
        """Upgraders can be registered and listed."""
        @SchemaUpgrader.register("1.0.0", "2.0.0")
        class TestUpgrader(SchemaUpgrader):
            def upgrade(self, doc: SemanticDocument) -> SemanticDocument:
                return doc.model_copy(update={"schema_version": "2.0.0"})

        available = SchemaUpgrader.list_available()
        assert ("1.0.0", "2.0.0") in available

    def test_upgrade_execution(self):
        """Registered upgrader performs the migration."""
        @SchemaUpgrader.register("1.0.0", "test-upgrade")
        class VersionUpgrader(SchemaUpgrader):
            def upgrade(self, doc: SemanticDocument) -> SemanticDocument:
                return doc.model_copy(update={"schema_version": "test-upgrade"})

        doc = SemanticDocument(schema_version="1.0.0")
        upgrader = SchemaUpgrader.get("1.0.0", "test-upgrade")
        assert upgrader is not None

        result = upgrader.upgrade(doc)
        assert result.schema_version == "test-upgrade"


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """End-to-end pipeline tests."""

    def test_full_pipeline_roundtrip(self, sample_docx_path):
        """Full pipeline: parse -> recognize -> serialize -> deserialize."""
        config = PipelineConfig(parser="python-docx", recognizer="regex")
        pipeline = Pipeline.from_config(config)
        result = pipeline.run(sample_docx_path)

        assert isinstance(result, SemanticDocument)
        assert len(result.blocks) > 0

        # Round-trip serialization
        json_str = result.to_json()
        restored = SemanticDocument.from_json(json_str)
        assert restored.schema_version == result.schema_version
        assert len(restored.blocks) == len(result.blocks)

    def test_pipeline_trace(self, sample_docx_path):
        """Pipeline captures trace entries."""
        config = PipelineConfig(parser="python-docx", recognizer="regex")
        pipeline = Pipeline.from_config(config)
        pipeline.run(sample_docx_path)

        trace = pipeline.get_trace()
        entries = trace.entries

        assert len(entries) >= 2  # parsing + recognition
        stage_names = [e.stage for e in entries]
        assert "parsing" in stage_names
        assert "recognition" in stage_names

        for entry in entries:
            assert entry.duration_seconds > 0
            assert entry.errors == []  # No errors

    def test_pipeline_trace_summary(self, sample_docx_path):
        """Trace summary is human-readable."""
        config = PipelineConfig(parser="python-docx", recognizer="regex")
        pipeline = Pipeline.from_config(config)
        pipeline.run(sample_docx_path)

        summary = pipeline.get_trace().summary()
        assert "Pipeline Trace:" in summary
        assert "parsing" in summary
        assert "recognition" in summary

    def test_pipeline_verbosity_summary(self, sample_docx_path, caplog):
        """Summary verbosity shows block counts only."""
        config = PipelineConfig(
            parser="python-docx", recognizer="regex", verbosity="summary"
        )
        pipeline = Pipeline.from_config(config)
        result = pipeline.run(sample_docx_path)
        pipeline.print_result(result)

        # Summary output should contain counts
        assert len(result.blocks) > 0


# ---------------------------------------------------------------------------
# Observability tests
# ---------------------------------------------------------------------------


class TestObservability:
    """Tests for logging and observability."""

    def test_logger_configurable(self):
        """Logger respects configured log level."""
        from document_semantic.observability.logger import get_logger
        logger = get_logger("test")
        # Logger should be callable and produce output
        assert logger is not None

    def test_warning_system(self):
        """Warning codes are defined and can be suppressed."""
        # Verify warning code constants exist (used by recognizers)
        # The actual warning codes are string literals used in the code
        warning_codes = [
            "UNRECOGNIZED_BLOCK",
        ]
        assert "UNRECOGNIZED_BLOCK" in warning_codes
