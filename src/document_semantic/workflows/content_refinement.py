from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from document_semantic.agents.refinement_agent import LLMRefinementAgent
from document_semantic.models.mineru_content import MinerUContentList, MinerUElement
from document_semantic.transform.chunker import Chunker
from document_semantic.transform.protector import Protector, ProtectionVerificationError

logger = logging.getLogger(__name__)


class ContentRefinementWorkflow:
    """Workflow for refining document content (citations, flow, etc.) using Agents."""

    def __init__(
        self,
        refinement_agent: LLMRefinementAgent,
        chunk_size: int = 4000,
        max_retries: int = 3
    ):
        self.agent = refinement_agent
        self.chunker = Chunker(max_chars=chunk_size)
        self.max_retries = max_retries

    def process_document(self, content: MinerUContentList) -> MinerUContentList:
        """Main entry point for document refinement."""
        elements = content.root
        
        # 1. Chunking
        chunks = self.chunker.chunk(elements)
        logger.info(f"[workflow:refinement] Document split into {len(chunks)} chunks")
        
        processed_elements = []
        for i, chunk_elements in enumerate(chunks):
            logger.info(f"[workflow:refinement] Processing chunk {i+1}/{len(chunks)}")
            refined_chunk = self._process_chunk(chunk_elements)
            processed_elements.extend(refined_chunk)
            
        return MinerUContentList(root=processed_elements)

    def _process_chunk(self, elements: List[MinerUElement]) -> List[MinerUElement]:
        """Processes a single chunk: protect -> refine -> verify -> restore."""
        protector = Protector()
        protected_text, mapping = protector.protect(elements)
        
        best_text = protected_text
        
        for attempt in range(self.max_retries):
            try:
                # Refine
                result = self.agent.refine(protected_text, {})
                
                # Verify protection
                protector.verify(result.refined_text, mapping)
                best_text = result.refined_text
                break 
            except ProtectionVerificationError as e:
                logger.warning(f"[workflow:refinement] Protection failed (attempt {attempt+1}): {e}")
                if attempt == self.max_retries - 1:
                    logger.error("[workflow:refinement] Max retries reached. Using original text.")
            except Exception as e:
                logger.error(f"[workflow:refinement] Agent error: {e}")
                break
            
        # Restore
        return protector.restore(best_text, mapping)
