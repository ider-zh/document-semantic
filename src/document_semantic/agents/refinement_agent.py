from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger

logger = get_logger(__name__)


class RefinementResult(BaseModel):
    """Structured output for content refinement."""
    refined_text: str = Field(description="The refined/rewritten text with placeholders preserved.")
    changes_made: List[str] = Field(description="Summary of changes made for auditing.")


class LLMRefinementAgent:
    """Agent that performs content refinement (rewriting citations, improving flow, etc.)."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        task_description: str = "Reformat citations in text to be consistent (e.g., [1, 2, 3] instead of [1,3,2]) and improve academic flow."
    ):
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
        self.task_description = task_description

    def refine(self, text: str, context: Dict[str, Any]) -> RefinementResult:
        """Refines text based on the configured task."""
        prompt = (
            f"You are a professional academic editor. Task: {self.task_description}\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. PRESERVE all placeholders like <P:EQ_1/>, <P:IMG_2/>, etc. EXACTLY as they are.\n"
            "2. Maintain the original Markdown structure.\n"
            "3. Only modify the text content to fulfill the task.\n\n"
            f"Text to refine:\n{text}"
        )

        try:
            logger.info(f"[agent:refinement] Refining {len(text)} chars using {self.model_id}")
            result = self.agent(
                prompt,
                structured_output_model=RefinementResult
            )
            return result.structured_output
        except Exception as e:
            logger.error(f"[agent:refinement] Refinement failed: {e}")
            raise
