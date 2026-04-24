from __future__ import annotations

from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger

logger = get_logger(__name__)


class GlossaryItem(BaseModel):
    """A single glossary term."""

    term: str = Field(description="The source language term")
    translation: str = Field(description="The target language translation")


class GlossaryExtraction(BaseModel):
    """Collection of glossary items extracted from text."""

    items: list[GlossaryItem]


class LLMGlossaryExtractor:
    """Agent to extract key terms and their translations from text."""

    def __init__(self, model_id: str | None = None, prompt_template: str | None = None):
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
        self.prompt_template = prompt_template or (
            "You are a professional terminologist. Extract key technical terms, named entities, "
            "and domain-specific jargon from the following text and provide their standard translations "
            "from {src_lang} to {tgt_lang}.\n\n"
            "Text:\n{text}"
        )

    def extract(self, text: str, src_lang: str = "Auto", tgt_lang: str = "Chinese") -> dict[str, str]:
        """Extracts terminology and returns a dict mapping source to target terms."""
        prompt = self.prompt_template.format(src_lang=src_lang, tgt_lang=tgt_lang, text=text)

        try:
            logger.info(f"[agent:glossary] Extracting terminology from {len(text)} chars using {self.model_id}")
            result = self.agent(prompt, structured_output_model=GlossaryExtraction)
            return {item.term: item.translation for item in result.structured_output.items}
        except Exception as e:
            logger.error(f"[agent:glossary] Glossary extraction failed: {e}")
            return {}
