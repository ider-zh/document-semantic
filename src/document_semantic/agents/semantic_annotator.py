from __future__ import annotations

from langfuse import observe
from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger
from document_semantic.models.annotated_content import AnnotatedMinerUContentList, AnnotatedMinerUElement
from document_semantic.models.mineru_content import MinerUElement
from document_semantic.templates.schema import SemanticTemplate

logger = get_logger(__name__)


class AnnotationResult(BaseModel):
    """Structured output for semantic annotation — ordered tag list."""
    tags: list[str] = Field(description="Ordered list of semantic tags, one per element, matching input order")


class SemanticAnnotatorAgent:
    """Agent that labels MinerU elements with semantic tags defined in a template."""

    def __init__(self, model_id: str | None = None):
        self.model_id = model_id or settings.recognizer_model_id
        self.agent = Agent(
            model=OpenAIModel(
                client_args={
                    "api_key": settings.recognizer_model_api_key,
                    "base_url": settings.provider_base_url,
                    "timeout": settings.recognizer_modelizer_model_timeout,
                },
                model_id=self.model_id,
            ),
            callback_handler=None,
        )

    @observe(name="semantic_annotator_agent")
    def annotate(self, elements: list[MinerUElement], template: SemanticTemplate) -> AnnotatedMinerUContentList:
        """Annotates a list of elements using the provided template."""
        if not elements:
            return AnnotatedMinerUContentList(root=[])

        template_info = template.get_prompt_fragment()
        valid_tags = ", ".join(template.get_tag_names())

        element_previews = []
        for i, elem in enumerate(elements):
            text = self._extract_preview_text(elem)
            element_previews.append(f"[{i}] {elem.type}: {text}")

        prompt = (
            f"Assign a semantic tag to each document element using template '{template.name}'.\n\n"
            f"Tags: {template_info}\n\n"
            f"Elements:\n"
            + "\n".join(element_previews) +
            f"\n\nReturn exactly {len(elements)} tags in order, one per element. Valid tags: {valid_tags}."
        )

        try:
            logger.info(f"[agent:annotator] Annotating {len(elements)} elements using {self.model_id}")
            result = self.agent(
                prompt,
                structured_output_model=AnnotationResult
            )

            tags = result.structured_output.tags
            valid_tag_set = set(template.get_tag_names())

            if len(tags) != len(elements):
                logger.warning(
                    f"[agent:annotator] Tag count mismatch: got {len(tags)}, expected {len(elements)}"
                )

            annotated_list = []
            for i, elem in enumerate(elements):
                raw_tag = tags[i] if i < len(tags) else "body_text"
                tag = raw_tag if raw_tag in valid_tag_set else "body_text"
                annotated_list.append(AnnotatedMinerUElement(
                    semantic_tag=tag,
                    element=elem
                ))

            return AnnotatedMinerUContentList(root=annotated_list)
        except Exception as e:
            logger.error(f"[agent:annotator] Annotation failed: {e}")
            raise

    def _extract_preview_text(self, elem: MinerUElement, max_len: int = 80) -> str:
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
