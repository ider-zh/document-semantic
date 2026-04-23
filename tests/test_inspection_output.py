"""Tests that generate inspection output for MinerU parser."""

import os
from pathlib import Path

import pytest

from document_semantic.services.parsers.mineru_parser import MinerUParser
from document_semantic.models.processor_output import ProcessorConfig


def is_mineru_configured():
    """Check if MinerU API token is available."""
    token = os.getenv("MINERU_TOKEN") or os.getenv("token_mineru")
    return bool(token)


@pytest.mark.skipif(not is_mineru_configured(), reason="MinerU API token not configured")
class TestInspectionOutput:
    """Generate inspection artifacts for specific test documents."""

    @pytest.mark.parametrize("docx_name", ["test_1.docx", "test_2.docx"])
    def test_generate_inspection(self, docx_name: str):
        """Parse document and save results to inspection directory."""
        project_root = Path(__file__).parent.parent
        docx_path = project_root / "tests" / "docx" / docx_name
        
        if not docx_path.exists():
            pytest.skip(f"Document {docx_name} not found")

        output_dir = project_root / "tests" / "docx" / "output" / "inspection" / docx_name.replace(".docx", "")
        output_dir.mkdir(parents=True, exist_ok=True)

        parser = MinerUParser()
        config = ProcessorConfig(
            output_markdown=True,
            output_resources=True,
            output_json_mapping=True
        )
        
        # We use process() to generate all artifacts including content_list.json
        result = parser.process(
            docx_path=docx_path,
            output_dir=output_dir,
            config=config
        )

        assert result.content_list_json_path is not None
        assert result.content_list_json_path.exists()
        assert (output_dir / "output.md").exists()
        assert (output_dir / "content_list.json").exists()

        # Validate with Pydantic model
        import json
        from document_semantic.models.mineru_content import MinerUContentList
        
        with open(result.content_list_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            MinerUContentList.model_validate(data)
