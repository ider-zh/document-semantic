from __future__ import annotations

from typing import List, Optional

from langfuse.decorators import observe
from langfuse.openai import openai
from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger
from document_semantic.models.mineru_content import MinerUContentList, MinerUElement
from document_semantic.models.annotated_content import AnnotatedMinerUElement, AnnotatedMinerUContentList
from document_semantic.templates.schema import SemanticTemplate

logger = get_logger(__name__)


class Annotation(BaseModel):
    """A single annotation result."""
    element_index: int = Field(description="The index of the element in the provided list")
    semantic_tag: str = Field(description="The semantic tag from the template")


class AnnotationResult(BaseModel):
    """Structured output for semantic annotation."""
    annotations: List[Annotation]


class SemanticAnnotatorAgent:
    """Agent that labels MinerU elements with semantic tags defined in a template."""

    def __init__(self, model_id: Optional[str] = None):
        self.model_id = model_id or settings.recognizer_model_id
        self.agent = Agent(
            model=OpenAIModel(
                client_args={
                    "api_key": settings.recognizer_model_api_key,
                    "base_url": settings.recognizer_model_provider_url,
                    "timeout": settings.recognizer_modelizer_model_timeout,
                },
                model_id=self.model_id,
            )
        )

    @observe(name="semantic_annotator_agent")
    def annotate(self, elements: List[MinerUElement], template: SemanticTemplate) -> AnnotatedMinerUContentList:
        """Annotates a list of elements using the provided template."""
        if not elements:
            return AnnotatedMinerUContentList(root=[])

        # Prepare prompt
        template_info = template.get_prompt_fragment()
        valid_tags = ", ".join(template.get_tag_names())
        
        # Build element list for prompt
        # We need to provide enough text for the LLM to identify the semantics
        element_previews = []
        for i, elem in enumerate(elements):
            text = self._extract_preview_text(elem)
            element_previews.append(f"[{i}] ({elem.type}): {text}")

        prompt = (
            f"You are a document structuring expert. Your task is to assign a semantic tag to each document element "
            f"based on the following template: '{template.name}'.\n\n"
            f"Available Semantic Tags:\n{template_info}\n\n"
            f"Elements to annotate (format: [Index] (Type): Preview):\n"
            + "\n".join(element_previews) +
            f"\n\nFor each element index from 0 to {len(elements)-1}, choose the MOST appropriate tag from: {valid_tags}.\n"
            f"If no specific tag fits, use the most generic one (e.g., 'body_text' or 'paragraph')."
        )

        try:
            logger.info(f"[agent:annotator] Annotating {len(elements)} elements using {self.model_id}")
            result = self.agent(
                prompt,
                structured_output_model=AnnotationResult
            )
            
            # Map back to models
            annotations_map = {ann.element_index: ann.semantic_tag for ann in result.structured_output.annotations}
            
            annotated_list = []
            for i, elem in enumerate(elements):
                tag = annotations_map.get(i, "body_text") # Default fallback
                annotated_list.append(AnnotatedMinerUElement(
                    semantic_tag=tag,
                    element=elem
                ))
            
            return AnnotatedMinerUContentList(root=annotated_list)
            
        except Exception as e:
            logger.error(f"[agent:annotator] Annotation failed: {e}")
            raise

    def _extract_preview_text(self, elem: MinerUElement, max_len: int = 200) -> str:
        """Extracts a short text preview of the element for the prompt."""
        parts = []

        def _collect(obj):
            if isinstance(obj, str):
                parts.append(obj)
            elif hasattr(obj, "model_dump"):
                _collect(obj.model_dump())
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    # In MinerU models, text is often in 'content' field of inline items
                    # or in '*_content' lists.
                    if k == "content" and isinstance(v, str):
                        parts.append(v)
                    elif isinstance(v, (str, dict, list)) or hasattr(v, "model_dump"):
                        _collect(v)
            elif isinstance(obj, list):
                for x in obj:
                    _collect(x)

        _collect(elem.content)
        full_text = " ".join(p for p in parts if p.strip()).strip()
        if len(full_text) <= max_len:
            return full_text
        return full_text[:max_len] + "..."
