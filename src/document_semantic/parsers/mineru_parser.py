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
import tempfile
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from document_semantic.observability.logger import get_logger
from document_semantic.models.processor_output import ProcessorConfig, ProcessResult
from document_semantic.parsers.protocol import (
    Attachment,
    IntermediateBlock,
    IntermediateResult,
    Parser,
    ParserDependencyError,
    ParserError,
)
from document_semantic.parsers.registry import ParserRegistry
from document_semantic.utils.markdown_generator import MarkdownGenerator

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


def _check_cache(docx_path: Path, skip_image_ocr: bool = False) -> Optional[IntermediateResult]:
    """Check if a cached result exists for the given DOCX file.

    Returns the deserialized IntermediateResult if found, None otherwise.
    """
    file_hash = _compute_file_hash(docx_path)
    cache_dir = _get_cache_dir() / file_hash
    result_json = cache_dir / "intermediate_result.json"

    if result_json.exists():
        zip_name = "result_restored.zip" if skip_image_ocr else "result.zip"
        zip_path = cache_dir / zip_name
        if zip_path.exists():
            logger.info(f"[parsing:mineru] Cache hit for hash {file_hash}")
            with open(result_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            return _deserialize_intermediate_result(data)

    return None


def _save_to_cache(
    docx_path: Path,
    result: IntermediateResult,
    zip_data: bytes,
    skip_image_ocr: bool = False,
    placeholder_zip_data: Optional[bytes] = None,
) -> None:
    """Save parse result and ZIP to cache directory."""
    file_hash = _compute_file_hash(docx_path)
    cache_dir = _get_cache_dir() / file_hash
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Save ZIP(s)
    if skip_image_ocr:
        # Save placeholder ZIP
        if placeholder_zip_data:
            with open(cache_dir / "result_placeholders.zip", "wb") as f:
                f.write(placeholder_zip_data)
        # Save restored ZIP as result_restored.zip
        with open(cache_dir / "result_restored.zip", "wb") as f:
            f.write(zip_data)
        # result.zip points to result_restored for backward compatibility
        with open(cache_dir / "result.zip", "wb") as f:
            f.write(zip_data)
    else:
        with open(cache_dir / "result.zip", "wb") as f:
            f.write(zip_data)

    # Save serialized IntermediateResult
    with open(cache_dir / "intermediate_result.json", "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)

    logger.info(f"[parsing:mineru] Cached result for hash {file_hash}")


def _deserialize_intermediate_result(data: dict[str, Any]) -> IntermediateResult:
    """Deserialize a dict into an IntermediateResult."""
    return IntermediateResult.model_validate(data)


# Image placeholder substitution helpers

# Standard placeholder PNG: 800x600 solid gray (#808080)
_PLACEHOLDER_WIDTH = 800
_PLACEHOLDER_HEIGHT = 600
_PLACEHOLDER_GRAYAY = 128  # 0-255, 128 = middle gray


def _generate_placeholder_image() -> bytes:
    """Generate a uniform gray placeholder PNG image.

    Returns:
        PNG image data as bytes, 800x600 pixels, gray color.
    """
    try:
        from PIL import Image
        import io

        img = Image.new("RGB", (_PLACEHOLDER_WIDTH, _PLACEHOLDER_HEIGHT), (_PLACEHOLDER_GRAYAY, _PLACEHOLDER_GRAYAY, _PLACEHOLDER_GRAYAY))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback: generate a minimal valid PNG manually
        # This is a minimal 1x1 gray PNG that can be used as fallback
        import base64
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )


def _extract_images_from_docx(docx_path: Path, output_dir: Path) -> list[Path]:
    """Extract all images from a DOCX file's word/media/ directory.

    Args:
        docx_path: Path to the DOCX file.
        output_dir: Directory to write extracted images to.

    Returns:
        List of paths to extracted images, in order found in the DOCX.
    """
    import zipfile as zf
    from pathlib import PurePosixPath

    output_dir.mkdir(parents=True, exist_ok=True)
    extracted_images: list[Path] = []

    with zf.ZipFile(docx_path, "r") as z:
        # Find all image files in word/media/
        image_names = [n for n in z.namelist() if n.startswith("word/media/")]
        image_names.sort()  # Ensure consistent order

        for name in image_names:
            # Extract the file
            data = z.read(name)
            dest = output_dir / PurePosixPath(name).name
            dest.write_bytes(data)
            extracted_images.append(dest)
            logger.debug(f"[parsing:mineru] Extracted image {name} -> {dest}")

    return extracted_images


def _replace_images_in_docx(
    docx_path: Path,
    placeholder_data: bytes,
    output_path: Path,
) -> int:
    """Replace all images in a DOCX with placeholder images at ZIP level.

    This preserves the DOCX structure by only replacing the image file contents
    in word/media/ while keeping all XML relationships intact.

    Args:
        docx_path: Path to the original DOCX file.
        placeholder_data: PNG data to use as placeholder for all images.
        output_path: Path to write the modified DOCX to.

    Returns:
        Number of images replaced.
    """
    import zipfile as zf
    from pathlib import PurePosixPath

    replaced_count = 0

    with zf.ZipFile(docx_path, "r") as src_zip:
        with zf.ZipFile(output_path, "w", zf.ZIP_DEFLATED) as dest_zip:
            for name in src_zip.namelist():
                if name.startswith("word/media/"):
                    # Replace this image with placeholder
                    dest_zip.writestr(name, placeholder_data)
                    replaced_count += 1
                    logger.debug(f"[parsing:mineru] Replaced image {name} with placeholder")
                else:
                    # Copy original file
                    dest_zip.writestr(name, src_zip.read(name))

    return replaced_count


def _build_image_mapping(zip_data: bytes) -> dict[str, int]:
    """Build mapping from ZIP image paths to DOCX image indices.

    Uses content_list_v2.json to determine which images in the ZIP correspond
    to DOCX images (in document order). Only images referenced in
    content_list_v2.json are DOCX-sourced; others are MinerU-generated artifacts.

    Returns:
        Dict mapping ZIP image path -> 0-based DOCX image index.
    """
    zf = zipfile.ZipFile(BytesIO(zip_data))
    if "content_list_v2.json" not in zf.namelist():
        return {}

    with zf.open("content_list_v2.json") as f:
        raw = json.loads(f.read().decode("utf-8"))

    # Flatten pages
    items: list[dict] = []
    if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
        for page in raw:
            items.extend(page)
    elif isinstance(raw, list):
        items = raw

    mapping: dict[str, int] = {}
    img_idx = 0
    for item in items:
        if item.get("type") in ("image", "figure", "img"):
            img_source = item.get("content", {}).get("image_source", {})
            img_path = img_source.get("path", "") if isinstance(img_source, dict) else ""
            if img_path and img_path not in mapping:
                mapping[img_path] = img_idx
                img_idx += 1

    return mapping


def _restore_images_in_zip(
    zip_data: bytes,
    original_images_dir: Path,
) -> bytes:
    """Replace placeholder images in result ZIP with original images.

    Uses content_list_v2.json to build the correct mapping between DOCX images
    and ZIP images, avoiding incorrect matches with MinerU-generated artifacts.

    Args:
        zip_data: Content of the result ZIP from MinerU API.
        original_images_dir: Directory containing original images extracted from DOCX.

    Returns:
        Modified ZIP data with original images restored.
    """
    from io import BytesIO

    # Get list of original images (sorted by name for consistent order)
    original_images = sorted(original_images_dir.glob("*"))
    if not original_images:
        logger.warning("[parsing:mineru] No original images found for restoration")
        return zip_data

    # Read original image data in order
    original_data: list[bytes] = []
    for img_path in original_images:
        original_data.append(img_path.read_bytes())

    # Build correct mapping from content_list_v2.json
    image_mapping = _build_image_mapping(zip_data)

    logger.info(
        f"[parsing:mineru] Restoring {len(original_data)} original images in result ZIP "
        f"(found {len(image_mapping)} DOCX-sourced images via content_list_v2.json)"
    )

    # Modify the result ZIP
    zf_in = zipfile.ZipFile(BytesIO(zip_data))
    out_buf = BytesIO()
    restored_count = 0

    with zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as zf_out:
        for name in zf_in.namelist():
            if name in image_mapping:
                docx_idx = image_mapping[name]
                if docx_idx < len(original_data):
                    zf_out.writestr(name, original_data[docx_idx])
                    restored_count += 1
                    logger.debug(f"[parsing:mineru] Restored image {name} with original #{docx_idx}")
                else:
                    zf_out.writestr(name, zf_in.read(name))
                    logger.warning(f"[parsing:mineru] No original for image #{docx_idx} ({name}), keeping placeholder")
            else:
                # Copy non-DOCX files as-is (including MinerU-generated images)
                zf_out.writestr(name, zf_in.read(name))

    if restored_count < len(original_data):
        logger.warning(
            f"[parsing:mineru] Restored {restored_count}/{len(original_data)} original images; "
            f"{len(original_data) - restored_count} originals had no matching ZIP image"
        )

    return out_buf.getvalue()


def _is_image_path(path: str) -> bool:
    """Check if a path in the ZIP refers to an image file."""
    image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp"}
    return Path(path).suffix.lower() in image_extensions


class MinerUParser(Parser):
    """Parser that uses the mineru.net API for rich document extraction.

    Uploads DOCX to the API, polls for results, downloads the ZIP,
    and parses content_list_v2.json into structured IntermediateBlock items.
    Results are cached locally by MD5 file hash.
    """

    @property
    def name(self) -> str:
        return "mineru"

    def parse(
        self,
        docx_path: Path,
        skip_image_ocr: bool = False,
    ) -> IntermediateResult:
        """Parse a DOCX file using the mineru.net API.

        Args:
            docx_path: Absolute path to the DOCX file.
            skip_image_ocr: If True, replace images with placeholders before
                processing and restore them after. Prevents OCR extraction.

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
        cached = _check_cache(docx_path, skip_image_ocr)
        if cached is not None:
            return cached

        logger.info(f"[parsing:mineru] Processing {docx_path} via MinerU API")
        if skip_image_ocr:
            logger.info("[parsing:mineru] Image placeholder substitution enabled")

        # Upload and get result
        zip_data, original_images_dir, modified_docx_path = self._upload_and_download(
            docx_path, token, skip_image_ocr
        )

        try:
            # Save placeholder ZIP before restoration if skip_image_ocr was enabled
            placeholder_zip_data = zip_data
            if skip_image_ocr and original_images_dir:
                zip_data = _restore_images_in_zip(zip_data, original_images_dir)

            # Parse the ZIP into IntermediateResult
            result = self._parse_zip(zip_data, docx_path)

            # Save to cache - both placeholder and restored ZIPs
            _save_to_cache(docx_path, result, zip_data, skip_image_ocr, placeholder_zip_data)
        finally:
            # Cleanup temporary files
            if modified_docx_path and modified_docx_path.exists():
                modified_docx_path.unlink()
            if original_images_dir and original_images_dir.exists():
                import shutil
                shutil.rmtree(original_images_dir, ignore_errors=True)

        return result

    def process(
        self,
        docx_path: Path,
        output_dir: Path,
        config: ProcessorConfig | None = None,
        skip_image_ocr: bool = False,
    ) -> ProcessResult:
        """Parse and process a DOCX file into rich Markdown + placeholder Markdown + resources.

        Reads content_list_v2.json directly from the MinerU result ZIP (cache or API)
        to preserve the full structured output, instead of going through IntermediateResult.

        Args:
            docx_path: Absolute path to the DOCX file.
            output_dir: Directory to write output files to.
            config: Processor configuration options.
            skip_image_ocr: If True, replace images with placeholders before
                processing and restore them after. Prevents OCR extraction.

        Returns:
            ProcessResult with paths to the generated files.
        """
        if config is None:
            config = ProcessorConfig()

        # Get the MinerU result ZIP (from cache or API)
        zip_data = self._get_zip_data(docx_path, skip_image_ocr)

        # Parse content_list_v2.json directly from the ZIP
        output_dir.mkdir(parents=True, exist_ok=True)
        resources_dir = output_dir / "resources" if config.output_resources else None
        images_dir = resources_dir / "images" if resources_dir else None

        converter = _MinerUContentConverter(docx_path, self.name, config.output_resources)
        rich_md_path, placeholder_md_path, resources_dir, json_path = converter.convert(
            zip_data, output_dir, images_dir
        )

        return ProcessResult(
            rich_markdown_path=rich_md_path if config.output_markdown else None,
            placeholder_markdown_path=placeholder_md_path if config.output_markdown else None,
            resources_dir=resources_dir,
            resources_json_path=json_path,
            metadata={"source_path": str(docx_path), "parser": "mineru"},
        )

    def _get_zip_data(self, docx_path: Path, skip_image_ocr: bool = False) -> bytes:
        """Get the MinerU result ZIP data, from cache or API."""
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
        cached = _check_cache(docx_path, skip_image_ocr)
        if cached is not None:
            # Re-read ZIP from cache
            cache_dir = _get_cache_dir() / _compute_file_hash(docx_path)
            zip_name = "result_restored.zip" if skip_image_ocr else "result.zip"
            zip_path = cache_dir / zip_name
            if zip_path.exists():
                return zip_path.read_bytes()

        # Fetch from API
        zip_data, _, _ = self._upload_and_download(docx_path, token, skip_image_ocr)
        return zip_data

    def _upload_and_download(
        self,
        docx_path: Path,
        token: str,
        skip_image_ocr: bool = False,
    ) -> tuple[bytes, Optional[Path], Optional[Path]]:
        """Upload DOCX to MinerU, poll for result, download ZIP.

        Args:
            docx_path: Path to the DOCX file.
            token: MinerU API token.
            skip_image_ocr: If True, replace images with placeholders before upload.

        Returns:
            Tuple of (zip_data, original_images_dir, modified_docx_path).
            original_images_dir and modified_docx_path are only set when skip_image_ocr=True.
        """
        modified_docx_path: Optional[Path] = None
        original_images_dir: Optional[Path] = None
        upload_path = docx_path

        if skip_image_ocr:
            # Generate placeholder image
            placeholder_data = _generate_placeholder_image()

            # Create temp directory for working files
            original_images_dir = Path(tempfile.mkdtemp(prefix="mineru_orig_images_"))
            modified_docx_path = Path(tempfile.mktemp(prefix="mineru_modified_", suffix=".docx"))

            # Extract original images for later restoration
            _extract_images_from_docx(docx_path, original_images_dir)

            # Replace images in DOCX
            replace_count = _replace_images_in_docx(docx_path, placeholder_data, modified_docx_path)
            logger.info(f"[parsing:mineru] Replaced {replace_count} images with placeholders")

            upload_path = modified_docx_path

        with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
            headers = {
                "Authorization": f"Bearer {token}",
            }

            # Step 1: Get upload URLs
            file_name = docx_path.name
            data_id = _compute_file_hash(docx_path)
            upload_payload = {
                "files": [{"name": file_name, "data_id": data_id, "is_ocr": False}],
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

            batch_id = result.get("data", {}).get("batch_id")
            urls = result.get("data", {}).get("file_urls", [])
            if not batch_id or not urls:
                raise ParserError(
                    f"Unexpected API response structure: {result}"
                )

            if not urls:
                raise ParserError("No upload URLs returned from API")

            upload_url = urls[0]

            # Step 2: Upload DOCX to presigned URL
            logger.info(f"[parsing:mineru] Uploading {upload_path.name}")
            with open(upload_path, "rb") as f:
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

            return zip_resp.content, original_images_dir, modified_docx_path

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


# ---------------------------------------------------------------------------
# MinerU content_list_v2.json direct converter
# ---------------------------------------------------------------------------


class _MinerUContentConverter:
    """Converts content_list_v2.json directly to rich + placeholder Markdown.

    Bypasses the IntermediateResult flattening to preserve all structured content
    from MinerU's output.
    """

    def __init__(self, docx_path: Path, parser_name: str, output_resources: bool = True):
        self._source_path = str(docx_path)
        self._parser_name = parser_name
        self._output_resources = output_resources
        self._image_counter = 0
        self._formula_counter = 0
        self._code_counter = 0
        self._resources: dict[str, dict[str, dict]] = {
            "formula": {},
            "code": {},
            "image": {},
        }

    def convert(
        self,
        zip_data: bytes,
        output_dir: Path,
        images_dir: Optional[Path],
    ) -> tuple[Path, Path, Optional[Path], Optional[Path]]:
        """Convert content_list_v2.json from ZIP to both Markdown outputs."""
        import zipfile as zf_module

        zf = zf_module.ZipFile(BytesIO(zip_data))
        file_names = zf.namelist()

        if "content_list_v2.json" not in file_names:
            raise ParserError("content_list_v2.json not found in MinerU result ZIP")

        with zf.open("content_list_v2.json") as f:
            raw = json.loads(f.read().decode("utf-8"))

        # Unwrap: content_list_v2.json is [[page_items], [page_items], ...]
        # Flatten all pages into a single item list
        items = []
        if isinstance(raw, list) and len(raw) > 0 and isinstance(raw[0], list):
            for page in raw:
                items.extend(page)
        elif isinstance(raw, list):
            items = raw

        # Generate both markdowns
        rich_lines = self._generate_markdown(items, zf, images_dir, use_placeholders=False)
        placeholder_lines = self._generate_markdown(items, zf, images_dir, use_placeholders=True)

        # Write files
        output_dir.mkdir(parents=True, exist_ok=True)
        rich_path = output_dir / "output_rich.md"
        rich_path.write_text("\n".join(rich_lines), encoding="utf-8")

        placeholder_path = output_dir / "output.md"
        placeholder_path.write_text("\n".join(placeholder_lines), encoding="utf-8")

        # Write resources.json
        json_path = None
        resources_dir = output_dir / "resources" if self._output_resources else None
        if self._output_resources and resources_dir:
            json_path = self._write_resources_json(output_dir)

        return rich_path, placeholder_path, resources_dir, json_path

    def _generate_markdown(
        self,
        items: list[dict],
        zf: zipfile.ZipFile,
        images_dir: Optional[Path],
        use_placeholders: bool,
    ) -> list[str]:
        """Generate Markdown lines from content_list_v2 items."""
        lines: list[str] = []
        for item in items:
            item_lines = self._process_item(item, zf, images_dir, use_placeholders)
            lines.extend(item_lines)
            lines.append("")  # Blank line between blocks
        return lines

    def _process_item(
        self,
        item: dict,
        zf: zipfile.ZipFile,
        images_dir: Optional[Path],
        use_placeholders: bool,
    ) -> list[str]:
        """Process a single content_list_v2 item."""
        elem_type = item.get("type", "text")
        content = item.get("content", {})

        if elem_type == "title":
            return self._title_to_markdown(content, use_placeholders)
        elif elem_type == "paragraph":
            return self._paragraph_to_markdown(content, use_placeholders)
        elif elem_type == "equation_interline":
            return self._equation_to_markdown(content, use_placeholders)
        elif elem_type in ("image", "figure", "img"):
            return self._image_to_markdown(content, zf, images_dir, use_placeholders)
        elif elem_type in ("table", "table_body"):
            return self._table_to_markdown(content, use_placeholders)
        elif elem_type in ("code", "code_block", "algorithm"):
            return self._code_to_markdown(content, use_placeholders)
        elif elem_type in ("list", "unordered_list", "ordered_list", "list_item"):
            return self._list_to_markdown(content, elem_type, use_placeholders)
        else:
            # Fallback: extract text
            text = self._extract_text(item)
            if text:
                return [text]
        return []

    def _title_to_markdown(self, content: dict, use_placeholders: bool) -> list[str]:
        """Convert title element to Markdown."""
        tc = content.get("title_content", [])
        if isinstance(tc, list):
            parts: list[str] = []
            for sub in tc:
                sub_type = sub.get("type", "text")
                if sub_type == "text":
                    parts.append(sub.get("content", ""))
                elif sub_type == "equation_inline":
                    eq_content = sub.get("content", "")
                    if use_placeholders:
                        self._formula_counter += 1
                        res_id = self._formula_counter
                        self._resources["formula"][str(res_id)] = {
                            "type": "inline",
                            "content": eq_content,
                            "metadata": {},
                        }
                        parts.append(f'<formula id="{res_id}">{eq_content}</formula>')
                    else:
                        parts.append(eq_content)
                else:
                    parts.append(self._extract_text(sub))
            text = "".join(parts)
        else:
            text = self._extract_text(content)
        level = content.get("level", 1)
        prefix = "#" * level + " "
        return [prefix + text]

    def _paragraph_to_markdown(self, content: dict, use_placeholders: bool) -> list[str]:
        """Convert paragraph element to Markdown."""
        pc = content.get("paragraph_content", [])
        if not pc:
            # Fallback: extract text from content dict
            text = self._extract_text(content)
            if use_placeholders:
                text = self._apply_inline_placeholders(text)
            return [text] if text else []

        parts: list[str] = []
        has_equations = False
        for sub in pc:
            sub_type = sub.get("type", "text")
            if sub_type == "text":
                parts.append(sub.get("content", ""))
            elif sub_type == "equation_inline":
                has_equations = True
                eq_content = sub.get("content", "")
                if use_placeholders:
                    self._formula_counter += 1
                    res_id = self._formula_counter
                    self._resources["formula"][str(res_id)] = {
                        "type": "inline",
                        "content": eq_content,
                        "metadata": {},
                    }
                    parts.append(f'<formula id="{res_id}">{eq_content}</formula>')
                else:
                    parts.append(eq_content)
            else:
                # Other sub-types: just extract text
                parts.append(self._extract_text(sub))

        text = "".join(parts)
        # Only apply regex placeholders if no equation_inline was found
        # (to avoid double-processing)
        if use_placeholders and not has_equations:
            text = self._apply_inline_placeholders(text)
        return [text]

    def _equation_to_markdown(self, content: dict, use_placeholders: bool) -> list[str]:
        """Convert equation_interline element to Markdown."""
        math_content = content.get("math_content", "")
        if not math_content:
            return []
        if use_placeholders:
            self._formula_counter += 1
            res_id = self._formula_counter
            self._resources["formula"][str(res_id)] = {
                "type": "block",
                "content": math_content,
                "metadata": {"math_type": content.get("math_type", "")},
            }
            return [f'<formula id="{res_id}">{math_content}</formula>']
        return [math_content]

    def _image_to_markdown(
        self,
        content: dict,
        zf: zipfile.ZipFile,
        images_dir: Optional[Path],
        use_placeholders: bool,
    ) -> list[str]:
        """Convert image element to Markdown."""
        img_source = content.get("image_source", {})
        if isinstance(img_source, dict):
            img_path = img_source.get("path", "")
        elif isinstance(img_source, str):
            img_path = img_source
        else:
            img_path = ""

        caption_parts = []
        raw_caption = content.get("image_caption", [])
        if isinstance(raw_caption, list):
            for cap_item in raw_caption:
                caption_parts.append(self._extract_text(cap_item))
        elif isinstance(raw_caption, str):
            caption_parts.append(raw_caption)

        # MinerU often puts image description in image_footnote, not image_caption
        raw_footnote = content.get("image_footnote", [])
        if isinstance(raw_footnote, list):
            for fn_item in raw_footnote:
                caption_parts.append(self._extract_text(fn_item))
        elif isinstance(raw_footnote, str):
            caption_parts.append(raw_footnote)

        caption = " ".join(p for p in caption_parts if p).strip()

        if not img_path:
            return []

        # Extract image from ZIP to resources
        self._image_counter += 1
        img_name = f"image_{self._image_counter}{Path(img_path).suffix or '.png'}"
        rel_path = f"resources/images/{img_name}"

        if images_dir:
            images_dir.mkdir(parents=True, exist_ok=True)
            try:
                img_data = zf.read(img_path)
                (images_dir / img_name).write_bytes(img_data)
            except KeyError:
                pass  # Image not in ZIP

        if use_placeholders:
            self._resources["image"][str(self._image_counter)] = {
                "type": "block",
                "content": caption,
                "file": rel_path,
                "metadata": {},
            }
            # Embed caption inside the image tag for semantic completeness
            if caption:
                lines = [f'<image id="{self._image_counter}">{caption}</image>']
            else:
                lines = [f'<image id="{self._image_counter}"/>']
            return lines

        return [f"![{caption}]({rel_path})"]

    def _table_to_markdown(self, content: dict, use_placeholders: bool) -> list[str]:
        """Convert table element to Markdown."""
        # Extract table text as-is
        text = self._extract_text(content)
        return [text]

    def _code_to_markdown(self, content: dict, use_placeholders: bool) -> list[str]:
        """Convert code element to Markdown."""
        text = self._extract_text(content)
        if use_placeholders:
            self._code_counter += 1
            res_id = self._code_counter
            self._resources["code"][str(res_id)] = {
                "type": "block",
                "content": text,
                "metadata": {},
            }
            return [f"<code id=\"{res_id}\"/>"]
        return [f"```\n{text}\n```"]

    def _list_to_markdown(
        self, content: dict, elem_type: str, use_placeholders: bool
    ) -> list[str]:
        """Convert list element to Markdown. Extracts text from list_items."""
        list_items = content.get("list_items", [])
        if not list_items:
            text = self._extract_text(content)
            if text:
                return [text]
            return []
        
        lines = []
        for i, li in enumerate(list_items):
            item_text = self._extract_text(li)
            if item_text:
                lines.append(item_text)
        return ["\n".join(lines)] if lines else []

    def _extract_text(self, content_or_item: dict) -> str:
        """Extract all text from a content dict or item dict recursively."""
        parts: list[str] = []

        def _collect(obj):
            if isinstance(obj, str):
                parts.append(obj)
            elif isinstance(obj, dict):
                for key, val in obj.items():
                    if key == "content":
                        _collect(val)
                    elif key in ("type", "bbox", "level", "math_type", "image_footnote",
                                 "item_type", "image_source", "image_caption", "math_content",
                                 "list_type", "list_items"):
                        pass  # Skip metadata keys
                    elif isinstance(val, (str, dict, list)):
                        _collect(val)
            elif isinstance(obj, list):
                for item in obj:
                    _collect(item)

        _collect(content_or_item)
        return " ".join(p for p in parts if p.strip()).strip()

    def _apply_inline_placeholders(self, text: str) -> str:
        """Apply XML placeholders to inline LaTeX formulas in text."""
        import re

        def _replacer(m):
            content = m.group(1)
            self._formula_counter += 1
            res_id = self._formula_counter
            self._resources["formula"][str(res_id)] = {
                "type": "inline",
                "content": content,
                "metadata": {},
            }
            return f'<formula id="{res_id}">{content}</formula>'

        # Match LaTeX commands: \mathsf{...}, \sum, \infty, etc.
        text = re.sub(
            r'((?:\\(?:mathsf|mathbf|mathrm|sum|int|frac|prod|sqrt|infty|alpha|beta|gamma|delta|epsilon|lambda|mu|pi|sigma|omega|partial|nabla|left|right|langle|rangle|lvert|rvert|overline|underline|hat|bar|tilde|vec|dot|ddot|text|limits|displaystyle|scriptstyle)\s*\{[^}]*\}|\\(?:sum|int|infty|ldots|cdots|dots|forall|exists|equiv|approx|neq|leq|geq|subset|supset|subseteq|supseteq|in|notin))+)',
            _replacer,
            text,
        )
        return text

    def _write_resources_json(self, output_dir: Path) -> Path:
        """Write resources.json mapping file."""
        import datetime

        mapping = {
            "version": "1.0",
            "resources": self._resources,
            "metadata": {
                "source_path": self._source_path,
                "parser": self._parser_name,
                "processed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        }
        json_path = output_dir / "resources.json"
        json_path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
        return json_path


# Auto-register
ParserRegistry.register("mineru", MinerUParser)
