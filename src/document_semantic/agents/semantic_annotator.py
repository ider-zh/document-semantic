from __future__ import annotations

from collections import Counter
from typing import Literal

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


class TagModification(BaseModel):
    """需要修改标签的元素"""
    index: int = Field(description="元素索引 (0-based)")
    from_type: str = Field(description="原始 MinerU 类型")
    to_tag: str = Field(description="目标模板标签")
    reason: str = Field(description="修改理由", max_length=40)


class AnnotationResult(BaseModel):
    """增量式语义标注 - 基于 MinerU 类型，只输出需要修改的"""

    modifications: list[TagModification] = Field(
        default_factory=list,
        description="需要覆盖默认映射的修改项"
    )

    element_count: int = Field(description="输入元素总数（校验用）")

    invalid_tags_detected: list[str] = Field(
        default_factory=list,
        description="如发现模板外的标签，请列明"
    )


class SemanticAnnotatorAgent:
    """Agent that labels MinerU elements with semantic tags defined in a template.

    基于 MinerU 类型进行增量标注：
    - MinerU 已提供基础语义（title, paragraph, equation_interline 等）
    - 只需输出需要覆盖默认映射的修改项
    """

    # MinerU type -> 默认 template tag 映射
    DEFAULT_TYPE_MAP = {
        "title": "section_head",
        "paragraph": "body_text",
        "image": "figure_caption",
        "table": "table_caption",
        "list": "body_text",
        "equation_interline": "equation_interline",
        "equation_inline": "equation_inline",
        "algorithm": "body_text",
    }

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
    def annotate(
        self,
        elements: list[MinerUElement],
        template: SemanticTemplate,
        max_retries: int = 2
    ) -> AnnotatedMinerUContentList:
        """Annotates a list of elements using the provided template.

        Args:
            elements: MinerU 解析的元素列表
            template: 语义模板定义
            max_retries: 最大重试次数

        Returns:
            标注后的内容列表
        """
        if not elements:
            return AnnotatedMinerUContentList(root=[])

        valid_tags = set(template.get_tag_names())
        mineru_types = [elem.type for elem in elements]

        for attempt in range(max_retries + 1):
            try:
                result = self._try_annotate(elements, template, mineru_types, valid_tags)
                return result
            except ValueError as e:
                if attempt < max_retries:
                    logger.warning(f"[agent:annotator] Validation failed, retrying ({attempt + 1}/{max_retries}): {e}")
                else:
                    logger.error(f"[agent:annotator] Max retries exceeded, using fallback: {e}")
                    return self._fallback_annotation(elements, mineru_types, valid_tags)

    def _try_annotate(
        self,
        elements: list[MinerUElement],
        template: SemanticTemplate,
        mineru_types: list[str],
        valid_tags: set[str]
    ) -> AnnotatedMinerUContentList:
        """尝试一次标注"""
        prompt = self._build_prompt(elements, template)

        logger.info(f"[agent:annotator] Annotating {len(elements)} elements using {self.model_id}")
        result = self.agent(
            prompt,
            structured_output_model=AnnotationResult
        )

        output = result.structured_output

        # 验证和展开
        tags = self._validate_and_expand(output, mineru_types, valid_tags)

        # 日志统计
        mod_count = len(output.modifications)
        logger.info(
            f"[agent:annotator] MinerU types: {dict(Counter(mineru_types))}, "
            f"LLM modifications: {mod_count}/{len(elements)} ({mod_count/len(elements)*100:.1f}%)"
        )

        return AnnotatedMinerUContentList(root=[
            AnnotatedMinerUElement(semantic_tag=tag, element=elem)
            for tag, elem in zip(tags, elements)
        ])

    def _validate_and_expand(
        self,
        output: AnnotationResult,
        mineru_types: list[str],
        valid_tags: set[str]
    ) -> list[str]:
        """验证输出并展开为完整标签列表

        Args:
            output: LLM 返回的标注结果
            mineru_types: MinerU 元素类型列表
            valid_tags: 有效的模板标签集合

        Returns:
            完整的标签列表

        Raises:
            ValueError: 验证失败时抛出
        """
        n = len(mineru_types)

        # 1. 数量校验
        if output.element_count != n:
            raise ValueError(f"element_count mismatch: {output.element_count} vs {n}")

        # 2. 构建修改查找表并校验每个修改项
        mods = {}
        for mod in output.modifications:
            # 索引范围检查
            if not (0 <= mod.index < n):
                logger.warning(f"[agent:annotator] Invalid index {mod.index}, skipping")
                continue

            # from_type 校验
            actual_type = mineru_types[mod.index]
            if mod.from_type != actual_type:
                logger.warning(
                    f"[agent:annotator] Type mismatch at [{mod.index}]: "
                    f"claimed {mod.from_type}, actual {actual_type}"
                )
                # 继续处理，使用实际类型

            # to_tag 有效性检查
            if mod.to_tag not in valid_tags:
                logger.warning(
                    f"[agent:annotator] Invalid tag '{mod.to_tag}' at [{mod.index}], "
                    f"using default mapping for {actual_type}"
                )
                continue

            mods[mod.index] = mod.to_tag

        # 3. 展开为完整标签列表
        tags = []
        for i, mtype in enumerate(mineru_types):
            if i in mods:
                tag = mods[i]
            else:
                # 使用默认映射
                tag = self.DEFAULT_TYPE_MAP.get(mtype, "body_text")

            # 最终防御：无效标签回退
            if tag not in valid_tags:
                tag = self.DEFAULT_TYPE_MAP.get(mtype, "body_text")

            tags.append(tag)

        return tags

    def _fallback_annotation(
        self,
        elements: list[MinerUElement],
        mineru_types: list[str],
        valid_tags: set[str]
    ) -> AnnotatedMinerUContentList:
        """失败时的回退标注：仅使用默认映射"""
        logger.warning("[agent:annotator] Using fallback annotation (default mappings only)")

        tags = []
        for mtype in mineru_types:
            tag = self.DEFAULT_TYPE_MAP.get(mtype, "body_text")
            if tag not in valid_tags:
                tag = "body_text"
            tags.append(tag)

        return AnnotatedMinerUContentList(root=[
            AnnotatedMinerUElement(semantic_tag=tag, element=elem)
            for tag, elem in zip(tags, elements)
        ])

    def _build_prompt(self, elements: list[MinerUElement], template: SemanticTemplate) -> str:
        """构建标注提示词"""
        valid_tags = template.get_tag_names()
        n = len(elements)

        # 提取元素信息
        element_info = []
        for i, elem in enumerate(elements):
            preview = self._extract_preview_text(elem, max_len=35)
            element_info.append(f"{i}: {elem.type} | {preview}")

        # 默认映射说明
        default_map_desc = "\n".join(
            f"- {mtype} → {tag}"
            for mtype, tag in self.DEFAULT_TYPE_MAP.items()
        )

        return f"""对 {n} 个文档元素进行语义标注。

可用标签: {', '.join(valid_tags)}

## 默认映射规则（MinerU type → 模板标签）
{default_map_desc}

## 常见需修改场景
- 索引 0: title → paper_title (论文主标题)
- 索引 1-2: title → author_info/abstract_head (作者/摘要标题)
- 索引 ~5: title → section_head (1. 引言)
- 参考文献区域: paragraph/list → reference_item

## 输入元素
{chr(10).join(element_info)}

## 输出要求
1. 只输出需要**修改**的元素，默认映射已覆盖大部分情况
2. 不确定时宁可不输出（保持默认）
3. 必须验证: index 在 [0, {n-1}] 范围内，from_type 与输入一致
4. element_count 必须等于 {n}

## 输出格式
{{"modifications": [{{"index": 0, "from_type": "title", "to_tag": "paper_title", "reason": "主标题"}}], "element_count": {n}, "invalid_tags_detected": []}}
"""

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
