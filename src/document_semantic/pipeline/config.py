"""Configuration loading for parser and recognizer selection."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

from document_semantic.observability.logger import get_logger

# Load .env at module import time
load_dotenv()

logger = get_logger(__name__)

DEFAULT_CONFIG_PATHS = [
    "doc_semantic.yaml",
    "doc_semantic.yml",
    ".doc_semantic.yaml",
    ".doc_semantic.yml",
]

DEFAULT_PARSER = "python-docx"
DEFAULT_RECOGNIZER = "regex"
DEFAULT_VERBOSITY = "preview"
DEFAULT_LOG_LEVEL = "INFO"


class PipelineConfig:
    """Pipeline configuration from config file and environment variables.

    Resolution order:
    1. Explicit config file path
    2. Default config file locations (first found)
    3. Environment variables
    4. Defaults
    """

    def __init__(
        self,
        parser: Optional[str] = None,
        recognizer: Optional[str] = None,
        recognizer_config: Optional[dict[str, Any]] = None,
        verbosity: Optional[str] = None,
        suppress_warnings: Optional[list[str]] = None,
        log_level: Optional[str] = None,
        mineru_token: Optional[str] = None,
        mineru_cache_dir: Optional[str] = None,
        mineru_skip_image_ocr: Optional[bool] = None,
        # Processor output settings
        output_markdown: Optional[bool] = None,
        output_resources: Optional[bool] = None,
        output_json_mapping: Optional[bool] = None,
        use_xml_placeholders: Optional[bool] = None,
    ):
        self.parser = parser or DEFAULT_PARSER
        self.recognizer = recognizer or DEFAULT_RECOGNIZER
        self.recognizer_config = recognizer_config or {}
        self.verbosity = verbosity or DEFAULT_VERBOSITY
        self.suppress_warnings = suppress_warnings or []
        self.log_level = log_level or DEFAULT_LOG_LEVEL
        # MinerU-specific settings: token from env, cache dir from env
        self.mineru_token = mineru_token or os.getenv("MINERU_TOKEN") or os.getenv("token_mineru")
        self.mineru_cache_dir = mineru_cache_dir or os.getenv("MINERU_CACHE_DIR") or ""
        self.mineru_skip_image_ocr = mineru_skip_image_ocr or False
        # Processor output settings (default to True)
        self.output_markdown = output_markdown if output_markdown is not None else True
        self.output_resources = output_resources if output_resources is not None else True
        self.output_json_mapping = output_json_mapping if output_json_mapping is not None else True
        self.use_xml_placeholders = use_xml_placeholders if use_xml_placeholders is not None else True

    @classmethod
    def load(cls, config_path: Optional[str | Path] = None) -> PipelineConfig:
        """Load configuration from file, environment, or defaults.

        Args:
            config_path: Optional explicit path to config file.

        Returns:
            A PipelineConfig instance.
        """
        raw: dict[str, Any] = {}

        # Try config file
        file_config = _find_config_file(config_path)
        if file_config:
            logger.debug(f"[config] Loaded config from {file_config}")
            raw = _read_yaml(file_config)
        else:
            logger.debug("[config] No config file found, using defaults + env vars")

        # Environment variables override config file
        env_parser = os.getenv("DOC_SEMANTIC_PARSER")
        env_recognizer = os.getenv("DOC_SEMANTIC_RECOGNIZER")
        env_verbosity = os.getenv("DOC_SEMANTIC_VERBOSITY")
        env_log_level = os.getenv("DOC_SEMANTIC_LOG_LEVEL")
        env_mineru_token = os.getenv("MINERU_TOKEN") or os.getenv("token_mineru")
        env_mineru_cache = os.getenv("MINERU_CACHE_DIR")
        env_mineru_skip_image_ocr = os.getenv("MINERU_SKIP_IMAGE_OCR")

        return cls(
            parser=env_parser or raw.get("parser"),
            recognizer=env_recognizer or raw.get("recognizer"),
            recognizer_config=raw.get("recognizer_config", {}),
            verbosity=env_verbosity or raw.get("verbosity"),
            suppress_warnings=raw.get("suppress_warnings", []),
            log_level=env_log_level or raw.get("log_level"),
            mineru_token=env_mineru_token or raw.get("mineru_token"),
            mineru_cache_dir=env_mineru_cache or raw.get("mineru_cache_dir"),
            mineru_skip_image_ocr=_parse_bool(env_mineru_skip_image_ocr or raw.get("mineru_skip_image_ocr")),
            output_markdown=raw.get("output_markdown"),
            output_resources=raw.get("output_resources"),
            output_json_mapping=raw.get("output_json_mapping"),
            use_xml_placeholders=raw.get("use_xml_placeholders"),
        )


def _find_config_file(explicit_path: Optional[str | Path] = None) -> Optional[Path]:
    """Find a config file, checking explicit path then default locations."""
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return p
        logger.warning(f"[config] Explicit config path {p} does not exist")
        return None

    # Check current working directory and home directory
    search_dirs = [Path.cwd(), Path.home()]
    for d in search_dirs:
        for filename in DEFAULT_CONFIG_PATHS:
            candidate = d / filename
            if candidate.exists():
                return candidate
    return None


def _read_yaml(path: Path) -> dict[str, Any]:
    """Read and parse a YAML file."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _parse_bool(value: Any) -> bool | None:
    """Parse a boolean value from string or config."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)
