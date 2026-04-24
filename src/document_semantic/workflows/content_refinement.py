from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from document_semantic.agents.refinement_agent import LLMRefinementAgent
from document_semantic.core.config import settings
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
        max_retries: int = 3,
        parallel_chunks: int | None = None,
    ):
        self.agent = refinement_agent
        self.chunker = Chunker(max_chars=chunk_size)
        self.max_retries = max_retries
        self.parallel_chunks = parallel_chunks or settings.parallel_chunks

    def process_document(self, content: MinerUContentList) -> MinerUContentList:
        """Main entry point for document refinement."""
        elements = content.root

        # 1. Chunking
        chunks = self.chunker.chunk(elements)
        logger.info(f"[workflow:refinement] Document split into {len(chunks)} chunks")

        # 2. Parallel processing of chunks
        def process_single_chunk(i_chunk):
            i, chunk_elements = i_chunk
            logger.info(f"[workflow:refinement] Processing chunk {i + 1}/{len(chunks)}")
            return self._process_chunk(chunk_elements)

        with ThreadPoolExecutor(max_workers=self.parallel_chunks) as executor:
            results = list(executor.map(process_single_chunk, enumerate(chunks)))

        processed_elements = []
        for chunk_result in results:
            processed_elements.extend(chunk_result)

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
