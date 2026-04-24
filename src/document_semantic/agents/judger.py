from __future__ import annotations

from langfuse import observe
from langfuse.openai import openai
from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger

logger = get_logger(__name__)


class JudgerResult(BaseModel):
    """Structured output for judging translations."""

    best_candidate_index: int = Field(
        description="The index of the best candidate starting from 0, or -1 if all are unacceptable."
    )
    justification: str = Field(description="A brief explanation of why this candidate was chosen.")


class LLMJudgerAgent:
    """Judger agent using Strands and LLM to choose the best translation."""

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
            "You are a professional quality editor. You are provided with the original text (protected with placeholders) and several translation candidates.\n"
            "Evaluate each candidate based on accuracy, fluency, terminology consistency, and protection integrity (placeholders should be preserved exactly).\n\n"
            "Original Text:\n{original}\n\n"
            "Translation Candidates:\n{candidates}\n\n"
            "Choose the best candidate index (0 to {max_idx}), or -1 if none are acceptable.\n"
        )

    @observe(name="judger_agent")
    def judge(self, original: str, candidates: list[str]) -> int:
        """Returns the index of the best candidate."""
        if not candidates:
            return -1

        candidates_str = "\n".join([f"Candidate {i}:\n{c}\n" for i, c in enumerate(candidates)])
        prompt = self.prompt_template.format(original=original, candidates=candidates_str, max_idx=len(candidates) - 1)

        try:
            logger.info(f"[agent:judger] Judging {len(candidates)} candidates using {self.model_id}")
            result = self.agent(prompt, structured_output_model=JudgerResult)
            idx = result.structured_output.best_candidate_index
            if -1 <= idx < len(candidates):
                return idx
            return -1
        except Exception as e:
            logger.error(f"[agent:judger] Judging failed: {e}")
            return -1
