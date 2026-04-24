from __future__ import annotations

from document_semantic.models.mineru_content import MinerUElement, MinerUTitleContent


class Chunker:
    """Chunks MinerUElement lists into manageable segments for Agent processing.

    Prioritizes splitting at headings (H1, H2). If a section is too large,
    it degrades to splitting between paragraphs.
    """

    def __init__(self, max_chars: int = 4000, min_chars: int = 500):
        self.max_chars = max_chars
        self.min_chars = min_chars

    def chunk(self, elements: list[MinerUElement]) -> list[list[MinerUElement]]:
        """Splits elements into chunks based on size and heading structure."""
        if not elements:
            return []

        chunks = []
        current_chunk = []
        current_size = 0

        for elem in elements:
            elem_size = self._estimate_size(elem)

            # Potential split point: Heading level 1 or 2
            is_heading = (
                elem.type == "title" and isinstance(elem.content, MinerUTitleContent) and elem.content.level <= 2
            )

            # Split if:
            # 1. We have a heading and current chunk is large enough (min_chars)
            # 2. Current element would push us over max_chars
            if current_chunk:
                should_split = False
                if is_heading and current_size >= self.min_chars or current_size + elem_size > self.max_chars:
                    should_split = True

                if should_split:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_size = 0

            current_chunk.append(elem)
            current_size += elem_size

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _estimate_size(self, elem: MinerUElement) -> int:
        """Estimates the character size of an element."""
        # Simple recursive text extraction for size estimation
        size = 0

        def _collect_size(obj):
            nonlocal size
            if isinstance(obj, str):
                size += len(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _collect_size(v)
            elif isinstance(obj, list):
                for item in obj:
                    _collect_size(item)
            elif hasattr(obj, "model_dump"):
                _collect_size(obj.model_dump())

        _collect_size(elem.content)
        return size
