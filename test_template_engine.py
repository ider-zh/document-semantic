import json
import logging
from pathlib import Path

from document_semantic.agents.semantic_annotator import SemanticAnnotatorAgent
from document_semantic.models.mineru_content import MinerUContentList
from document_semantic.templates.registry import TemplateRegistry
from document_semantic.renderers.advanced_docx_renderer import AdvancedDocxRenderer
from document_semantic.renderers.latex_renderer import LatexRenderer

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_template_engine():
    # 1. Load the translated content (or original for testing)
    input_path = Path("tests/docx/output/inspection/test_1/translated_content_list.json")
    if not input_path.exists():
        input_path = Path("tests/docx/output/inspection/test_1/content_list.json")
    
    if not input_path.exists():
        print(f"Input file {input_path} not found.")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    content_list = MinerUContentList.model_validate(data)
    print(f"Loaded {len(content_list)} elements from {input_path}")

    # 2. Choose Template (Using JCST V2)
    template = TemplateRegistry.get("jcst-v2")
    print(f"Using template: {template.name}")

    # 3. Annotate
    annotator = SemanticAnnotatorAgent()
    print("Starting semantic annotation...")
    annotated_content = annotator.annotate(content_list.root, template)
    
    # Save annotated JSON for inspection
    annotated_path = Path("tests/docx/output/inspection/test_1/annotated_content_list_jcst.json")
    with open(annotated_path, "w", encoding="utf-8") as f:
        f.write(annotated_content.model_dump_json(indent=2))
    print(f"Annotated content saved to {annotated_path}")

    # 4. Render to Advanced DOCX
    resources_dir = Path("tests/docx/output/inspection/test_1/resources")
    renderer_docx = AdvancedDocxRenderer(resources_dir=resources_dir)
    output_docx = Path("tests/docx/output/inspection/test_1/output_jcst_v2.docx")
    renderer_docx.render(annotated_content, template, output_docx)
    print(f"Advanced DOCX saved to {output_docx}")

    # 5. Render to LaTeX
    renderer_latex = LatexRenderer(resources_dir=resources_dir)
    output_latex = Path("tests/docx/output/inspection/test_1/output_jcst_v2.tex")
    renderer_latex.render(annotated_content, template, output_latex)
    print(f"Rendered LaTeX saved to {output_latex}")

if __name__ == "__main__":
    test_template_engine()
