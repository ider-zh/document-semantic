from __future__ import annotations

from typing import Any

from langfuse import observe
from langfuse.openai import openai
from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger

logger = get_logger(__name__)


class TranslationResult(BaseModel):
    """Structured output for translation."""

    translated_text: str = Field(description="The translated text with placeholders preserved.")


class LLMTranslationAgent:
    """Translation agent using Strands and LLM."""

    def __init__(self, model_id: str | None = None, prompt_template: str | None = None):
        self.model_id = model_id or settings.recognizer_model_id
        self.prompt_template = prompt_template or (
            "You are a professional academic translator. Your goal is to translate the provided text into {tgt_lang}.\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. TARGET LANGUAGE: Everything MUST be in {tgt_lang}. Do NOT return any {src_lang} text unless it's a proper noun or a placeholder.\n"
            "2. PRESERVE all placeholders like <P:EQ_1/>, <P:IMG_2/>, etc. EXACTLY as they are. Do not translate, wrap in Markdown, or modify them.\n"
            "3. Structure: Maintain headings (#) and list items (-).\n"
            "4. Glossary: Use the provided terms consistently.\n\n"
            "Glossary:\n{glossary}\n\n"
            "Text to translate ({src_lang} -> {tgt_lang}):\n{text}"
        )

    def _create_agent(self) -> Agent:
        """Creates a fresh Agent instance for a thread-safe invocation."""
        return Agent(
            model=OpenAIModel(
                client_args={
                    "api_key": settings.recognizer_model_api_key,
                    "base_url": settings.provider_base_url,
                    "timeout": settings.recognizer_modelizer_model_timeout,
                },
                model_id=self.model_id,
            )
        )

    @observe(name="translator_agent")
    def translate(self, text: str, context: dict[str, Any]) -> str:
        """Translates text using the LLM."""
        glossary_items = context.get("glossary", {})
        glossary_str = "\n".join([f"- {k}: {v}" for k, v in glossary_items.items()])

        prompt = self.prompt_template.format(
            src_lang=context.get("src_lang", "Auto"),
            tgt_lang=context.get("tgt_lang", "Chinese"),
            glossary=glossary_str or "None",
            text=text,
        )

        try:
            logger.info(f"[agent:translator] Translating {len(text)} chars using {self.model_id}")
            agent = self._create_agent()
            result = agent(prompt, structured_output_model=TranslationResult)
            return result.structured_output.translated_text
        except Exception as e:
            logger.error(f"[agent:translator] Translation failed: {e}")
            raise
