from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from document_semantic.models.annotated_content import AnnotatedMinerUContentList, AnnotatedMinerUElement
from document_semantic.models.mineru_content import (
    MinerUParagraphContent,
    MinerUTitleContent,
    MinerUImageContent,
    MinerUInlineContent
)
from document_semantic.templates.schema import SemanticTemplate

logger = logging.getLogger(__name__)


class LatexRenderer:
    """Renders annotated MinerU content to a LaTeX file using template mappings."""

    def __init__(self, preamble_path: Optional[Path] = None, resources_dir: Optional[Path] = None):
        self.preamble_path = preamble_path
        self.resources_dir = resources_dir

    def render(
        self, 
        annotated_content: AnnotatedMinerUContentList, 
        template: SemanticTemplate, 
        output_path: Path
    ) -> Path:
        """Renders the content to a LaTeX file."""
        lines = []
        
        # 1. Preamble
        if self.preamble_path and self.preamble_path.exists():
            lines.append(self.preamble_path.read_text(encoding="utf-8"))
        else:
            lines.append(r"\documentclass{article}")
            lines.append(r"\usepackage[utf8]{inputenc}")
            lines.append(r"\usepackage{amsmath}")
            lines.append(r"\usepackage{graphicx}")
            lines.append(r"\usepackage{hyperref}")
            lines.append(r"\begin{document}")

        # 2. Content
        for ann_elem in annotated_content:
            tag = ann_elem.semantic_tag
            elem = ann_elem.element
            
            try:
                if tag == "paper_title":
                    text = self._extract_text(elem)
                    lines.append(f"\\title{{{self._escape_latex(text)}}}")
                    lines.append(r"\maketitle")
                elif tag == "author_info":
                    text = self._extract_text(elem)
                    lines.append(f"\\author{{{self._escape_latex(text)}}}")
                elif tag == "abstract_text":
                    text = self._extract_text(elem)
                    lines.append(r"\begin{abstract}")
                    lines.append(text)
                    lines.append(r"\end{abstract}")
                elif tag == "section_head":
                    text = self._extract_text(elem)
                    lines.append(f"\\section{{{self._escape_latex(text)}}}")
                elif tag == "subsection_head":
                    text = self._extract_text(elem)
                    lines.append(f"\\subsection{{{self._escape_latex(text)}}}")
                elif elem.type == "equation_interline":
                    lines.append(r"\begin{equation}")
                    lines.append(elem.content.math_content)
                    lines.append(r"\end{equation}")
                elif elem.type == "image":
                    self._render_latex_image(elem, lines)
                elif elem.type == "paragraph":
                    text = self._extract_text_with_inline_math(elem)
                    lines.append(text + "\n")
                else:
                    text = self._extract_text(elem)
                    if text:
                        lines.append(self._escape_latex(text) + "\n")
            except Exception as e:
                logger.error(f"[renderer:latex] Failed to render {tag}: {e}")

        # 3. Footer
        lines.append(r"\end{document}")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"[renderer:latex] Saved LaTeX to {output_path}")
        return output_path

    def _render_latex_image(self, elem, lines: list):
        # We need relative path to image from tex file
        img_path = elem.content.image_source.path if hasattr(elem.content, "image_source") else None
        caption = ""
        if hasattr(elem.content, "image_caption") and elem.content.image_caption:
            caption = self._extract_text_fallback(elem.content.image_caption)
            
        lines.append(r"\begin{figure}[htbp]")
        lines.append(r"\centering")
        if img_path:
            # We assume images are in 'images/' subdir relative to tex
            lines.append(f"\\includegraphics[width=0.8\\textwidth]{{{img_path}}}")
        if caption:
            lines.append(f"\\caption{{{self._escape_latex(caption)}}}")
        lines.append(r"\end{figure}")

    def _extract_text_fallback(self, obj) -> str:
        parts = []
        def _collect(o):
            if isinstance(o, str): parts.append(o)
            elif isinstance(o, list):
                for i in o: _collect(i)
            elif hasattr(o, "content"):
                parts.append(str(o.content))
        _collect(obj)
        return "".join(parts).strip()

    def _extract_text(self, elem) -> str:
        parts = []
        def _collect(obj):
            if isinstance(obj, str): parts.append(obj)
            elif hasattr(obj, "model_dump"): _collect(obj.model_dump())
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "content" and isinstance(v, str): parts.append(v)
                    elif isinstance(v, (str, dict, list)): _collect(v)
            elif isinstance(obj, list):
                for x in obj: _collect(x)
        _collect(elem.content)
        return " ".join(p for p in parts if p.strip()).strip()

    def _extract_text_with_inline_math(self, elem) -> str:
        if elem.type != "paragraph":
            return self._extract_text(elem)
        
        parts = []
        inlines = elem.content.paragraph_content or []
        for inline in inlines:
            if inline.type == "text":
                parts.append(self._escape_latex(inline.content))
            elif inline.type == "equation_inline":
                # Ensure it has $ separators
                content = inline.content.strip()
                if not content.startswith("$"): content = "$" + content
                if not content.endswith("$"): content = content + "$"
                parts.append(content)
        return "".join(parts)

    def _escape_latex(self, text: str) -> str:
        # Very basic escaping
        chars = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
        }
        return "".join(chars.get(c, c) for c in text)
