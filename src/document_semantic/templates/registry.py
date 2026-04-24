from __future__ import annotations

from typing import Dict, List, Optional
from .schema import SemanticTemplate, SemanticTag

class TemplateRegistry:
    _templates: Dict[str, SemanticTemplate] = {}

    @classmethod
    def register(cls, template: SemanticTemplate):
        cls._templates[template.id] = template

    @classmethod
    def get(cls, template_id: str) -> Optional[SemanticTemplate]:
        return cls._templates.get(template_id)

    @classmethod
    def list_available(cls) -> List[str]:
        return list(cls._templates.keys())


# Define IEEE Template
ieee_template = SemanticTemplate(
    id="ieee",
    name="IEEE Conference Style",
    description="Standard IEEE conference paper template semantics",
    tags=[
        SemanticTag(name="paper_title", display_name="Paper Title", description="The main title of the paper", is_required=True),
        SemanticTag(name="author_info", display_name="Author Information", description="Names, affiliations, and emails of authors"),
        SemanticTag(name="abstract_head", display_name="Abstract Heading", description="The 'Abstract' keyword heading"),
        SemanticTag(name="abstract_text", display_name="Abstract Body", description="The content of the abstract"),
        SemanticTag(name="index_terms", display_name="Index Terms", description="Keywords or index terms"),
        SemanticTag(name="section_head", display_name="Section Heading", description="Level 1 headings (I, II, III...)"),
        SemanticTag(name="subsection_head", display_name="Subsection Heading", description="Level 2 headings (A, B, C...)"),
        SemanticTag(name="body_text", display_name="Body Text", description="Standard paragraphs of text"),
        SemanticTag(name="equation", display_name="Display Equation", description="Numbered block-level equations"),
        SemanticTag(name="figure_caption", display_name="Figure Caption", description="Captions starting with 'Fig. X.'"),
        SemanticTag(name="table_caption", display_name="Table Caption", description="Captions starting with 'TABLE X.'"),
        SemanticTag(name="reference_item", display_name="Reference", description="A single entry in the reference list"),
        SemanticTag(name="acknowledgment", display_name="Acknowledgment", description="Acknowledgment section text"),
    ],
    docx_style_map={
        "paper_title": "Title",
        "author_info": "Author",
        "abstract_head": "Abstract Heading",
        "abstract_text": "Abstract",
        "section_head": "Heading 1",
        "subsection_head": "Heading 2",
        "body_text": "Normal",
        "reference_item": "Reference",
    }
)

# Define JCST Template (Placeholder, adjust based on actual JCST style)
jcst_template = SemanticTemplate(
    id="jcst",
    name="Journal of Computer Science and Technology",
    description="JCST journal submission semantics",
    tags=[
        SemanticTag(name="title_en", display_name="English Title", description="Main title in English", is_required=True),
        SemanticTag(name="author_en", display_name="English Authors", description="Author names in English"),
        SemanticTag(name="abstract_en", display_name="English Abstract", description="Abstract text in English"),
        SemanticTag(name="keywords_en", display_name="English Keywords", description="Keywords in English"),
        SemanticTag(name="section_head", display_name="Section Heading", description="Numbered headings"),
        SemanticTag(name="body_text", display_name="Body Text", description="Normal paragraphs"),
        SemanticTag(name="reference_head", display_name="Reference Heading", description="The 'References' section title"),
        SemanticTag(name="reference_item", display_name="Reference Item", description="Individual citations"),
    ]
)

from .jcst_v2 import jcst_v2_template

# ... existing code ...
TemplateRegistry.register(ieee_template)
TemplateRegistry.register(jcst_template)
TemplateRegistry.register(jcst_v2_template)
