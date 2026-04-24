import yaml
from pathlib import Path
from typing import Dict, Any
from .schema import SemanticTemplate, DocxStyleConfig, PageConfig, PageMargins, ColumnConfig, SemanticTag

class YAMLTemplateLoader:
    """Helper to load SemanticTemplate from docx_build_cli style YAML files."""

    @staticmethod
    def load(path: Path) -> SemanticTemplate:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        # 1. Page Config
        p = data.get("page", {})
        m = p.get("margins", {})
        c = p.get("columns", {})
        page_config = PageConfig(
            width=p.get("width", "210mm"),
            height=p.get("height", "297mm"),
            orientation=p.get("orientation", "portrait"),
            margins=PageMargins(
                top=m.get("top", "25.4mm"),
                bottom=m.get("bottom", "25.4mm"),
                left=m.get("left", "31.7mm"),
                right=m.get("right", "31.7mm")
            ),
            columns=ColumnConfig(
                title_page=c.get("title_page", 1),
                abstract_page=c.get("abstract_page", 1),
                body=c.get("body", 1),
                column_spacing=c.get("column_spacing", "12.7mm")
            )
        )
        
        # 2. Styles
        styles = {}
        for s_name, s_data in data.get("styles", {}).items():
            styles[s_name] = DocxStyleConfig(**s_data)
            
        # 3. Tags (Simplified conversion for now)
        # In a real scenario, we might need a mapping in the YAML for tag descriptions
        tags = []
        for s_name in styles.keys():
            tags.append(SemanticTag(
                name=s_name,
                display_name=s_name.replace("_", " ").title(),
                description=f"Auto-generated tag for {s_name} style"
            ))
            
        return SemanticTemplate(
            id=data.get("journal", "custom").lower(),
            name=data.get("full_name", "Custom Template"),
            description=data.get("description", ""),
            tags=tags,
            page=page_config,
            styles=styles
        )
