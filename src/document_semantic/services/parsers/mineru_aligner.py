import difflib
import re

import docx


class DocxAligner:
    """Aligns MinerU parsed elements with raw DOCX text to fix OCR errors and word wraps."""

    def __init__(self, docx_path: str):
        self.doc = docx.Document(docx_path)
        self.docx_paras = []
        for i, p in enumerate(self.doc.paragraphs):
            text = p.text.strip()
            if text:
                self.docx_paras.append({"id": len(self.docx_paras), "text": text, "norm": self._normalize_text(text)})

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove all whitespace
        text = re.sub(r"\s+", "", text)
        # Unify punctuation to English (halfwidth)
        text = text.translate(
            str.maketrans(
                "，。！？【】（）％＃＠＆１２３４５６７８９０ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ‘’“”",
                ",.!?[]()%#@&1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ''\"\"",
            )
        )
        return text.lower()

    def _extract_text(self, item: dict) -> str:
        parts = []

        def _collect(obj):
            if isinstance(obj, str):
                parts.append(obj)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "content":
                        _collect(v)
                    elif k in ("type", "bbox", "level", "math_type"):
                        pass
                    elif isinstance(v, (str, dict, list)):
                        _collect(v)
            elif isinstance(obj, list):
                for x in obj:
                    _collect(x)

        _collect(item)
        return " ".join(p for p in parts if p.strip()).strip()

    def align(self, items: list[dict]) -> list[dict]:
        if not self.docx_paras:
            return items

        # 1. Assign docx_id to each paragraph/title
        docx_idx = 0
        for item in items:
            t = item.get("type")
            if t not in ("paragraph", "title"):
                continue

            mineru_text = self._extract_text(item)
            norm_m = self._normalize_text(mineru_text)
            if not norm_m:
                continue

            best_id = -1
            best_score = 0

            # Search forward
            for i in range(docx_idx, min(docx_idx + 20, len(self.docx_paras))):
                norm_d = self.docx_paras[i]["norm"]
                if not norm_d:
                    continue
                if norm_m in norm_d or norm_d in norm_m:
                    best_id = i
                    break
                s = difflib.SequenceMatcher(None, norm_m, norm_d).ratio()
                if s > best_score:
                    best_score = s
                    best_id = i

            if best_id != -1 and (
                best_score > 0.5 or best_id == docx_idx or (norm_m in self.docx_paras[best_id]["norm"])
            ):
                item["_docx_id"] = best_id
                docx_idx = best_id

        # 2. Group by docx_id
        out_items = []
        current_group = []
        current_docx_id = None

        for item in items:
            did = item.get("_docx_id")
            if did is not None:
                if current_docx_id == did:
                    current_group.append(item)
                else:
                    if current_group:
                        out_items.append(self._merge_and_restore(current_group, current_docx_id))
                    current_group = [item]
                    current_docx_id = did
            else:
                if current_group:
                    out_items.append(self._merge_and_restore(current_group, current_docx_id))
                    current_group = []
                    current_docx_id = None
                out_items.append(item)

        if current_group:
            out_items.append(self._merge_and_restore(current_group, current_docx_id))

        # Clean up _docx_id
        for item in out_items:
            if "_docx_id" in item:
                del item["_docx_id"]

        return out_items

    def _merge_and_restore(self, group: list[dict], docx_id: int) -> dict:
        # Merge contents
        merged_elements = []
        base_item = group[0].copy()
        new_content = base_item.get("content", {}).copy()

        for item in group:
            c = item.get("content", {})
            if "paragraph_content" in c:
                merged_elements.extend(c["paragraph_content"])
            elif "title_content" in c:
                merged_elements.extend(c["title_content"])
            else:
                merged_elements.append({"type": "text", "content": self._extract_text(item)})

        # Restore with docx text
        docx_text = self.docx_paras[docx_id]["text"]
        restored_elements = self._restore_elements(merged_elements, docx_text)

        if "paragraph_content" in new_content:
            new_content["paragraph_content"] = restored_elements
        elif "title_content" in new_content:
            new_content["title_content"] = restored_elements

        base_item["content"] = new_content
        return base_item

    def _restore_elements(self, mineru_elements: list[dict], docx_text: str) -> list[dict]:
        s_m = ""
        boundaries = []
        for elem in mineru_elements:
            start = len(s_m)
            s_m += str(elem.get("content", ""))
            end = len(s_m)
            boundaries.append((start, end, elem))

        matcher = difflib.SequenceMatcher(None, s_m, docx_text)
        M = [0] * (len(s_m) + 1)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1 + 1):
                    if i1 + k < len(M):
                        M[i1 + k] = j1 + k
            elif tag == "replace":
                for k in range(i2 - i1 + 1):
                    if i1 + k < len(M):
                        M[i1 + k] = j1 + int((k / max(1, i2 - i1)) * (j2 - j1))
            elif tag == "delete":
                for k in range(i2 - i1 + 1):
                    if i1 + k < len(M):
                        M[i1 + k] = j1
            elif tag == "insert":
                if i1 < len(M):
                    M[i1] = j1

        M[0] = 0
        M[-1] = len(docx_text)
        for i in range(1, len(M)):
            if M[i] < M[i - 1]:
                M[i] = M[i - 1]

        restored = []
        for start, end, elem in boundaries:
            d_start = M[start]
            d_end = M[end]
            if elem.get("type") == "text":
                text = docx_text[d_start:d_end]
                if text:
                    restored.append({"type": "text", "content": text})
            else:
                restored.append(elem)

        # Merge consecutive text elements
        final_restored = []
        for elem in restored:
            if elem.get("type") == "text" and final_restored and final_restored[-1].get("type") == "text":
                final_restored[-1]["content"] += elem["content"]
            else:
                final_restored.append(elem)

        return final_restored
