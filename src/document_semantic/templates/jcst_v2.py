from .schema import SemanticTemplate, SemanticTag, DocxStyleConfig, PageConfig, PageMargins, ColumnConfig

jcst_v2_template = SemanticTemplate(
    id="jcst-v2",
    name="Journal of Computer Science and Technology (V2)",
    description="JCST official layout with 10pt text and double columns",
    tags=[
        SemanticTag(name="paper_title", display_name="Paper Title", description="Main title in English", is_required=True),
        SemanticTag(name="author_info", display_name="Authors", description="Author names and affiliations"),
        SemanticTag(name="abstract_head", display_name="Abstract Heading", description="The 'Abstract' title"),
        SemanticTag(name="abstract_text", display_name="Abstract Body", description="Abstract content"),
        SemanticTag(name="index_terms", display_name="Keywords", description="Keywords/Index terms"),
        SemanticTag(name="section_head", display_name="Section Heading", description="Numbered level 1 headings"),
        SemanticTag(name="subsection_head", display_name="Subsection Heading", description="Numbered level 2 headings"),
        SemanticTag(name="body_text", display_name="Body Text", description="Standard paragraphs with indent"),
        SemanticTag(name="figure_caption", display_name="Figure Caption", description="Captions for images"),
        SemanticTag(name="table_caption", display_name="Table Caption", description="Captions for tables"),
        SemanticTag(name="reference_item", display_name="Reference", description="Citations in reference list"),
    ],
    page=PageConfig(
        width="210mm",
        height="297mm",
        margins=PageMargins(top="26mm", bottom="13.5mm", left="14.8mm", right="14.8mm"),
        columns=ColumnConfig(title_page=1, abstract_page=1, body=2, column_spacing="8mm")
    ),
    styles={
        "paper_title": DocxStyleConfig(font="Times New Roman", size=16, bold=True, align="center", space_before=18, space_after=12, text_transform="uppercase"),
        "author_info": DocxStyleConfig(font="Times New Roman", size=11, align="center", space_before=6, space_after=12),
        "abstract_head": DocxStyleConfig(font="Times New Roman", size=10, bold=True, align="left", space_before=6, space_after=3, text_transform="uppercase"),
        "abstract_text": DocxStyleConfig(font="Times New Roman", size=9, align="left", space_after=12, line_spacing=1.15),
        "section_head": DocxStyleConfig(font="Times New Roman", size=12, bold=True, align="left", space_before=18, space_after=6),
        "body_text": DocxStyleConfig(font="Times New Roman", size=10, align="justified", indent_first=21, line_spacing=1.15),
        "reference_item": DocxStyleConfig(font="Times New Roman", size=9, align="left", space_after=3),
        "figure_caption": DocxStyleConfig(font="Times New Roman", size=9, italic=True, align="center", space_before=3, space_after=12),
        "table_caption": DocxStyleConfig(font="Times New Roman", size=9, italic=True, align="center", space_after=3),
    }
)
