"""MinerU API parser implementation.

Uses the mineru.net cloud API to extract rich structured content from DOCX
documents. Chains: upload → poll → download ZIP → parse content_list_v2.json
→ IntermediateResult with rich semantic blocks.

Results are cached locally by MD5 file hash to avoid redundant API calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from document_semantic.observability.logger import get_logger
from document_semantic.parsers.protocol import (
    Attachment,
    IntermediateBlock,
    IntermediateResult,
    Parser,
    ParserDependencyError,
    ParserError,
)
from document_semantic.parsers.registry import ParserRegistry

logger = get_logger(__name__)

# Load .env at module import time
load_dotenv()

MINERU_API_BASE = "https://mineru.net/api/v4"
POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 300
HTTP_TIMEOUT_SECONDS = 60

# Mapping from MinerU element types to style hints
_MINERU_TYPE_TO_STYLE: dict[str, str] = {
    "title": "Title",
    "heading": "Heading1",  # Level extracted from metadata
    "text": "Normal",
    "paragraph": "Normal",
    "formula": "Formula",
    "table": "Table",
    "list": "ListBullet",
    "ordered_list": "ListNumbered",
    "unordered_list": "ListBullet",
    "image": "Image",
    "code": "CodeBlock",
    "code_block": "CodeBlock",
    "reference": "Reference",
    "abstract": "Abstract",
    "list_item": "ListBullet",
}


def _get_mineru_token() -> Optional[str]:
    """Get the MinerU API token from environment or .env."""
    return os.getenv("MINERU_TOKEN") or os.getenv("token_mineru")


def _get_cache_dir() -> Path:
    """Get the cache directory for MinerU results."""
    cache_dir = os.getenv("MINERU_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir)
    return Path.home() / ".cache" / "document-semantic" / "mineru"


def _compute_file_hash(docx_path: Path) -> str:
    """Compute MD5 hash of DOCX file content for cache key."""
    hasher = hashlib.md5()
    with open(docx_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _check_cache(docx_path: Path) -> Optional[IntermediateResult]:
    """Check if a cached result exists for the given DOCX file.

    Returns the deserialized IntermediateResult if found, None otherwise.
    """
    file_hash = _compute_file_hash(docx_path)
    cache_dir = _get_cache_dir() / file_hash
    result_json = cache_dir / "intermediate_result.json"

    if result_json.exists():
        logger.info(f"[parsing:mineru] Cache hit for hash {file_hash}")
        with open(result_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _deserialize_intermediate_result(data)

    return None


def _save_to_cache(docx_path: Path, result: IntermediateResult, zip_data: bytes) -> None:
    """Save parse result and ZIP to cache directory."""
    file_hash = _compute_file_hash(docx_path)
    cache_dir = _get_cache_dir() / file_hash
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Save ZIP
    with open(cache_dir / "result.zip", "wb") as f:
        f.write(zip_data)

    # Save serialized IntermediateResult
    with open(cache_dir / "intermediate_result.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    logger.info(f"[parsing:mineru] Cached result for hash {file_hash}")


def _deserialize_intermediate_result(data: dict[str, Any]) -> IntermediateResult:
    """Deserialize a dict into an IntermediateResult."""
    return IntermediateResult.model_validate(data)


class MinerUParser(Parser):
    """Parser that uses the mineru.net API for rich document extraction.

    Uploads DOCX to the API, polls for results, downloads the ZIP,
    and parses content_list_v2.json into structured IntermediateBlock items.
    Results are cached locally by MD5 file hash.
    """

    @property
    def name(self) -> str:
        return "mineru"

    def parse(self, docx_path: Path) -> IntermediateResult:
        """Parse a DOCX file using the mineru.net API.

        Args:
            docx_path: Absolute path to the DOCX file.

        Returns:
            IntermediateResult with rich semantic blocks.

        Raises:
            ParserDependencyError: If API token is not configured.
            ParserError: If API calls fail or extraction errors occur.
        """
        token = _get_mineru_token()
        if not token:
            raise ParserDependencyError(
                parser_name="mineru",
                dependency="MINERU_TOKEN",
                message=(
                    "MinerU API token is not configured. Set MINERU_TOKEN in your "
                    ".env file or environment. Get a token from https://mineru.net"
                ),
            )

        # Check cache first
        cached = _check_cache(docx_path)
        if cached is not None:
            return cached

        logger.info(f"[parsing:mineru] Processing {docx_path} via MinerU API")

        # Upload and get result
        zip_data = self._upload_and_download(docx_path, token)

        # Parse the ZIP into IntermediateResult
        result = self._parse_zip(zip_data, docx_path)

        # Save to cache
        _save_to_cache(docx_path, result, zip_data)

        return result

    def _upload_and_download(self, docx_path: Path, token: str) -> bytes:
        """Upload DOCX to MinerU, poll for result, download ZIP.

        Returns the ZIP file content as bytes.
        """
        with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
            headers = {
                "Authorization": f"Bearer {token}",
            }

            # Step 1: Get upload URLs
            file_name = docx_path.name
            data_id = _compute_file_hash(docx_path)
            upload_payload = {
                "files": [{"name": file_name, "data_id": data_id}],
                "model_version": "vlm",
            }

            logger.info(f"[parsing:mineru] Requesting upload URL for {file_name}")
            resp = client.post(
                f"{MINERU_API_BASE}/file-urls/batch",
                headers={**headers, "Content-Type": "application/json"},
                json=upload_payload,
            )

            if resp.status_code == 401:
                raise ParserDependencyError(
                    parser_name="mineru",
                    dependency="MINERU_TOKEN",
                    message="MinerU API token is expired or invalid. Get a new token from https://mineru.net",
                )

            if resp.status_code != 200:
                raise ParserError(
                    f"Failed to get upload URL: HTTP {resp.status_code}: {resp.text}"
                )

            result = resp.json()
            if result.get("code") != 0 and not result.get("success", True):
                msg = result.get("msg", result.get("message", "Unknown error"))
                if "auth" in msg.lower() or "token" in msg.lower():
                    raise ParserDependencyError(
                        parser_name="mineru",
                        dependency="MINERU_TOKEN",
                        message=f"MinerU API authentication failed: {msg}. Get a new token from https://mineru.net",
                    )
                raise ParserError(f"API error: {msg}")

            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]

            if not urls:
                raise ParserError("No upload URLs returned from API")

            upload_url = urls[0]

            # Step 2: Upload DOCX to presigned URL
            logger.info(f"[parsing:mineru] Uploading {file_name}")
            with open(docx_path, "rb") as f:
                upload_resp = httpx.put(upload_url, data=f, timeout=HTTP_TIMEOUT_SECONDS)

            if upload_resp.status_code != 200:
                raise ParserError(
                    f"Upload failed: HTTP {upload_resp.status_code}: {upload_resp.text}"
                )

            logger.info(f"[parsing:mineru] Upload complete, batch_id={batch_id}")

            # Step 3: Poll for results
            zip_url = self._poll_for_result(client, headers, batch_id)

            # Step 4: Download result ZIP
            logger.info(f"[parsing:mineru] Downloading result ZIP")
            zip_resp = client.get(zip_url, timeout=HTTP_TIMEOUT_SECONDS)
            if zip_resp.status_code != 200:
                raise ParserError(
                    f"Download failed: HTTP {zip_resp.status_code}"
                )

            return zip_resp.content

    def _poll_for_result(
        self, client: httpx.Client, headers: dict[str, str], batch_id: str
    ) -> str:
        """Poll the result endpoint until extraction is done or timeout.

        Returns the full_zip_url when ready.
        """
        start = time.monotonic()
        url = f"{MINERU_API_BASE}/extract-results/batch/{batch_id}"

        logger.info(f"[parsing:mineru] Polling for results (timeout={POLL_TIMEOUT_SECONDS}s)")

        while True:
            elapsed = time.monotonic() - start
            if elapsed > POLL_TIMEOUT_SECONDS:
                raise ParserError(
                    f"Polling timeout after {elapsed:.0f}s for batch {batch_id}"
                )

            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                raise ParserError(
                    f"Poll failed: HTTP {resp.status_code}: {resp.text}"
                )

            data = resp.json()
            if data.get("code") != 0:
                raise ParserError(f"Poll error: {data.get('msg', 'Unknown error')}")

            extract_results = data.get("data", {}).get("extract_result", [])
            if not extract_results:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            first_result = extract_results[0]
            state = first_result.get("state", "")

            if state == "done":
                zip_url = first_result.get("full_zip_url")
                if not zip_url:
                    raise ParserError("Result is done but no full_zip_url found")
                logger.info(f"[parsing:mineru] Extraction complete")
                return zip_url
            elif state == "failed":
                err_msg = first_result.get("err_msg", "Unknown error")
                raise ParserError(f"Extraction failed: {err_msg}")
            else:
                logger.debug(f"[parsing:mineru] State: {state}, polling again...")
                time.sleep(POLL_INTERVAL_SECONDS)

    def _parse_zip(self, zip_data: bytes, docx_path: Path) -> IntermediateResult:
        """Parse the result ZIP into an IntermediateResult.

        Tries content_list_v2.json first, falls back to markdown.
        """
        zf = zipfile.ZipFile(BytesIO(zip_data))
        file_names = zf.namelist()

        # Try content_list_v2.json first
        if "content_list_v2.json" in file_names:
            logger.info("[parsing:mineru] Parsing content_list_v2.json")
            with zf.open("content_list_v2.json") as f:
                content_list = json.loads(f.read().decode("utf-8"))
            # Attachments are extracted during content_list parsing
            blocks, attachments = self._parse_content_list(content_list, zf)
        else:
            # Fallback to markdown: extract images by file extension
            logger.info("[parsing:mineru] content_list_v2.json not found, falling back to markdown")
            blocks, attachments = self._parse_markdown_fallback(zf, file_names)
            for att in self._extract_attachments_from_zip(zf, file_names):
                attachments.append(att)

        logger.info(
            f"[parsing:mineru] Extracted {len(blocks)} blocks, "
            f"{len(attachments)} attachments from result ZIP"
        )

        return IntermediateResult(
            blocks=blocks,
            metadata={"source_path": str(docx_path), "parser": "mineru"},
            attachments=attachments,
        )

    def _parse_content_list(
        self, content_list: list[dict[str, Any]], zf: zipfile.ZipFile
    ) -> tuple[list[IntermediateBlock], list[Attachment]]:
        """Parse content_list_v2.json into IntermediateBlock items.

        Each element in the JSON is mapped to a block with appropriate style hint.
        Handles nested lists (items can be dicts or lists of dicts).
        Image elements produce both a block (with caption) and an attachment entry.
        """
        blocks: list[IntermediateBlock] = []
        attachments: list[Attachment] = []

        for item in content_list:
            # Handle nested lists - flatten one level
            if isinstance(item, list):
                for sub_item in item:
                    if isinstance(sub_item, dict):
                        block = self._item_to_block(sub_item, attachments)
                        if block:
                            blocks.append(block)
            elif isinstance(item, dict):
                block = self._item_to_block(item, attachments)
                if block:
                    blocks.append(block)

        return blocks, attachments

    def _item_to_block(
        self, item: dict[str, Any], attachments: list[Attachment]
    ) -> Optional[IntermediateBlock]:
        """Convert a single content_list_v2 element to an IntermediateBlock.

        For image elements, also creates an Attachment entry and sets block
        content to the image reference.
        """
        elem_type = item.get("type", "text")
        content_dict = item.get("content", {})

        # Handle image elements specially
        if elem_type in ("image", "figure", "img"):
            return self._image_item_to_block(item, content_dict, attachments)

        content = self._extract_content_text(item)
        style_hint = self._resolve_style_hint(elem_type, item)
        inline_elements = self._extract_inline_elements(item)

        if not content:
            return None

        return IntermediateBlock(
            content=content,
            style_hint=style_hint,
            inline_elements=inline_elements,
        )

    def _image_item_to_block(
        self,
        item: dict[str, Any],
        content_dict: dict[str, Any],
        attachments: list[Attachment],
    ) -> IntermediateBlock:
        """Create block and attachment for an image element.

        The block content uses markdown image syntax with the attachment ID
        as the URL: ![caption](attachment:<id>). This allows downstream code
        to recover the link between image blocks and their attachments.
        """
        # Extract image path from content.image_source.path
        image_source = content_dict.get("image_source", {})
        image_path = image_source.get("path", "")

        # Extract caption if available
        caption_parts = []
        image_caption = content_dict.get("image_caption", [])
        if isinstance(image_caption, list):
            for cap_item in image_caption:
                if isinstance(cap_item, dict):
                    cap_text = cap_item.get("content", "")
                    if cap_text:
                        caption_parts.append(cap_text)
                elif isinstance(cap_item, str):
                    caption_parts.append(cap_item)
        elif isinstance(image_caption, str):
            caption_parts.append(image_caption)

        caption = " ".join(caption_parts).strip()

        # Create attachment (avoid duplicates by checking path)
        att_id = f"image_{len(attachments)}"
        if image_path:
            existing_paths = {att.path for att in attachments}
            zip_path = f"zip:///{image_path}"
            if zip_path not in existing_paths:
                mime_type = _infer_mime_type(Path(image_path).suffix)
                attachments.append(
                    Attachment(
                        id=att_id,
                        path=zip_path,
                        mime_type=mime_type,
                    )
                )
            # Build content with attachment reference: ![caption](attachment:<id>)
            display = caption if caption else "image"
            content = f"![{display}](attachment:{att_id})"
        else:
            content = "![image]"

        return IntermediateBlock(
            content=content,
            style_hint="Image",
            inline_elements=[],
        )

    def _extract_content_text(self, item: dict[str, Any]) -> str:
        """Extract text content from a content_list_v2 element.

        Handles both simple format (item.text, item.md_content) and
        nested format (item.content.title_content, item.content.paragraph_content, etc.).
        """
        content_dict = item.get("content", {})
        if isinstance(content_dict, dict):
            # Nested structure: content has typed sub-fields
            parts = []
            for key, val in content_dict.items():
                if isinstance(val, list):
                    for sub in val:
                        if isinstance(sub, dict):
                            text = sub.get("content", "")
                            if text and isinstance(text, str):
                                parts.append(text)
                        elif isinstance(sub, str):
                            parts.append(sub)
                elif isinstance(val, str):
                    parts.append(val)
            if parts:
                return " ".join(parts).strip()

        # Simple structure fallback
        if "text" in item:
            return str(item["text"]).strip()
        if isinstance(content_dict, str):
            return content_dict.strip()
        if "content" in item and isinstance(item["content"], str):
            return item["content"].strip()
        if "md_content" in item:
            return str(item["md_content"]).strip()
        if "latex" in item:
            return f"${item['latex']}$"
        return ""

    def _resolve_style_hint(self, elem_type: str, item: dict[str, Any]) -> str:
        """Resolve a style hint from MinerU element type and metadata."""
        content_dict = item.get("content", {})
        if isinstance(content_dict, dict):
            # Check for heading level in title_content
            level = content_dict.get("level")
            if elem_type == "title" and level and 1 <= level <= 6:
                return f"Heading{level}"

        # Check for list types
        if elem_type in ("list", "list_item"):
            list_type = content_dict.get("list_type", item.get("ordered", ""))
            if str(list_type).lower() in ("ordered", "true", "1"):
                return "ListNumbered"
            return "ListBullet"

        # Check for algorithm/code
        if elem_type in ("algorithm", "code", "code_block"):
            return "CodeBlock"

        # Check for formula
        if elem_type in ("formula", "equation", "latex", "equation_inline", "equation_block"):
            return "Formula"

        # Check for table
        if elem_type in ("table",):
            return "Table"

        # Check for image
        if elem_type in ("image", "figure", "img"):
            return "Image"

        # Title without level → Heading1
        if elem_type == "title":
            return "Heading1"

        # Paragraph → Normal
        if elem_type == "paragraph":
            return "Normal"

        # Default mapping
        return _MINERU_TYPE_TO_STYLE.get(elem_type, "Normal")

    def _extract_inline_elements(self, item: dict[str, Any]) -> list:
        """Extract inline elements from a content_list_v2 item.

        For now, returns empty list — inline elements are handled by
        the recognizer stage. Can be enhanced in the future.
        """
        # MinerU's content_list_v2.json may have inline formulas, links, etc.
        # These could be extracted here but are deferred to the recognizer
        # for consistency with other parsers.
        return []

    def _parse_markdown_fallback(
        self, zf: zipfile.ZipFile, file_names: list[str]
    ) -> tuple[list[IntermediateBlock], list[Attachment]]:
        """Parse markdown file from ZIP as fallback.

        Uses the same approach as PandocParser: split on blank lines,
        infer style hints from markdown syntax.
        """
        md_file = None
        for name in file_names:
            if name.endswith(".md"):
                md_file = name
                break

        if not md_file:
            return [], []

        with zf.open(md_file) as f:
            md_content = f.read().decode("utf-8")

        raw_blocks = md_content.strip().split("\n\n")
        blocks: list[IntermediateBlock] = []
        for block_text in raw_blocks:
            block_text = block_text.strip()
            if not block_text:
                continue
            style_hint = _infer_style_hint_markdown(block_text)
            blocks.append(IntermediateBlock(content=block_text, style_hint=style_hint))

        return blocks, []

    def _extract_attachments_from_zip(
        self, zf: zipfile.ZipFile, file_names: list[str]
    ) -> list[Attachment]:
        """Extract image references from the result ZIP."""
        attachments: list[Attachment] = []
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}

        for name in file_names:
            ext = Path(name).suffix.lower()
            if ext in image_extensions:
                mime_type = _infer_mime_type(ext)
                attachments.append(
                    Attachment(
                        id=f"image_{len(attachments)}",
                        path=f"zip:///{name}",
                        mime_type=mime_type,
                    )
                )

        return attachments


def _infer_style_hint_markdown(text: str) -> str:
    """Infer style hint from markdown syntax patterns (fallback)."""
    if text.startswith("# "):
        return "Heading1"
    elif text.startswith("## "):
        return "Heading2"
    elif text.startswith("### "):
        return "Heading3"
    elif text.startswith("#### "):
        return "Heading4"
    elif text.startswith("##### "):
        return "Heading5"
    elif text.startswith("###### "):
        return "Heading6"
    elif text.startswith("- ") or text.startswith("* "):
        return "ListBullet"
    elif text.startswith("|"):
        return "Table"
    elif text.startswith("```"):
        return "CodeBlock"
    elif text.startswith("$") and text.endswith("$"):
        return "Formula"
    return "Normal"


def _infer_mime_type(suffix: str) -> str:
    """Infer MIME type from file extension."""
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    return mime_map.get(suffix.lower(), "application/octet-stream")


# Auto-register
ParserRegistry.register("mineru", MinerUParser)
