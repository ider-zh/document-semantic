from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from document_semantic.agents.glossary_extractor import LLMGlossaryExtractor
from document_semantic.agents.judger import LLMJudgerAgent
from document_semantic.agents.translator import LLMTranslationAgent
from document_semantic.core.config import settings
from document_semantic.models.mineru_content import (
    MinerUContentList,
    MinerUElement,
    MinerUParagraphContent,
    MinerUTitleContent,
)
from document_semantic.transform.chunker import Chunker
from document_semantic.transform.protector import ProtectionVerificationError, Protector

logger = logging.getLogger(__name__)


class TranslationWorkflow:
    """Orchestrates the chunking, protection, translation, and judging of MinerU documents."""

    def __init__(
        self,
        translators: list[LLMTranslationAgent],
        judger: LLMJudgerAgent,
        glossary_extractor: LLMGlossaryExtractor | None = None,
        chunk_size: int = 4000,
        max_retries: int = 3,
        parallel_chunks: int | None = None,
    ):
        self.translators = translators
        self.judger = judger
        self.glossary_extractor = glossary_extractor or LLMGlossaryExtractor()
        self.chunker = Chunker(max_chars=chunk_size)
        self.max_retries = max_retries
        self.parallel_chunks = parallel_chunks or settings.parallel_chunks

    def translate_document(
        self, content: MinerUContentList, src_lang: str = "English", tgt_lang: str = "Chinese"
    ) -> MinerUContentList:
        """Main entry point for document translation."""
        elements = content.root

        # 1. Global glossary extraction from entire document (or sampled)
        sample_text = self._get_sample_text(elements)
        logger.info("[workflow:translation] Extracting global glossary...")
        global_glossary = self.glossary_extractor.extract(sample_text, src_lang, tgt_lang)
        logger.info(f"[workflow:translation] Extracted {len(global_glossary)} global terms")

        # 2. Chunking
        chunks = self.chunker.chunk(elements)
        logger.info(f"[workflow:translation] Document split into {len(chunks)} chunks")

        # 3. Parallel processing of chunks
        def process_single_chunk(i_chunk):
            i, chunk_elements = i_chunk
            logger.info(f"[workflow:translation] Processing chunk {i + 1}/{len(chunks)}")
            chunk_text = self._elements_to_text(chunk_elements)
            local_glossary = self._recall_glossary(chunk_text, global_glossary)
            return self._process_chunk(chunk_elements, local_glossary, src_lang, tgt_lang)

        with ThreadPoolExecutor(max_workers=self.parallel_chunks) as executor:
            # Maintain order by indexing or using map on enumerated chunks
            results = list(executor.map(process_single_chunk, enumerate(chunks)))

        translated_elements = []
        for chunk_result in results:
            translated_elements.extend(chunk_result)

        return MinerUContentList(root=translated_elements)

    def _process_chunk(
        self, elements: list[MinerUElement], glossary: dict[str, str], src_lang: str, tgt_lang: str
    ) -> list[MinerUElement]:
        """Processes a single chunk: protect -> multiple translate -> verify -> judge -> restore."""
        protector = Protector()
        protected_text, mapping = protector.protect(elements)

        candidates = []
        context = {"glossary": glossary, "src_lang": src_lang, "tgt_lang": tgt_lang}

        for translator in self.translators:
            for attempt in range(self.max_retries):
                try:
                    # Translate
                    result_text = translator.translate(protected_text, context)

                    # Verify protection
                    protector.verify(result_text, mapping)
                    candidates.append(result_text)
                    break  # Success
                except (ProtectionVerificationError, Exception) as e:
                    logger.warning(
                        f"[workflow:translation] Translation/Verification failed (attempt {attempt + 1}): {e}"
                    )
                    if attempt == self.max_retries - 1:
                        logger.error("[workflow:translation] Max retries reached for chunk.")

        if not candidates:
            logger.warning("[workflow:translation] All translation candidates failed. Returning original chunk.")
            return elements

        # Judge
        best_idx = self.judger.judge(protected_text, candidates)
        best_text = candidates[0] if best_idx == -1 else candidates[best_idx]

        # Restore
        return protector.restore(best_text, mapping)

    def _get_sample_text(self, elements: list[MinerUElement], max_chars: int = 3000) -> str:
        """Gets a sample text for glossary extraction."""
        text = self._elements_to_text(elements)
        return text[:max_chars]


    def _elements_to_text(self, elements: list[MinerUElement]) -> str:
        """Simple extraction of all text from elements."""
        texts = []
        for e in elements:
            if e.type == "paragraph" and isinstance(e.content, MinerUParagraphContent):
                texts.append(" ".join([i.content for i in e.content.paragraph_content or [] if i.type == "text"]))
            elif e.type == "title" and isinstance(e.content, MinerUTitleContent):
                texts.append(" ".join([i.content for i in e.content.title_content or [] if i.type == "text"]))
        return "\n".join(texts)

    def _recall_glossary(self, text: str, global_glossary: dict[str, str]) -> dict[str, str]:
        """Simple keyword-based recall from global glossary."""
        recalled = {}
        text_lower = text.lower()
        for term, trans in global_glossary.items():
            if term.lower() in text_lower:
                recalled[term] = trans
        return recalled
