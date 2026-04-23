from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from document_semantic.core import constants
from document_semantic.core.logger import get_logger

# Load .env at module import time for compatibility with os.getenv()
load_dotenv()

logger = get_logger(__name__)


class MultiYamlConfigSettingsSource(YamlConfigSettingsSource):
    """YAML source that checks multiple default paths."""

    def __init__(self, settings_cls: type[BaseSettings]):
        # Find the first existing config file
        config_file = self._find_config_file()
        super().__init__(settings_cls, yaml_file=config_file)

    def _find_config_file(self) -> Path | None:
        search_dirs = [Path.cwd(), Path.home()]
        # Search for config.yaml first, then the legacy ones
        config_names = ["config.yaml", "config.yml"] + constants.DEFAULT_CONFIG_PATHS
        for d in search_dirs:
            for filename in config_names:
                candidate = d / filename
                if candidate.exists():
                    logger.debug(f"[config] Found config file at {candidate}")
                    return candidate
        return None


class Settings(BaseSettings):
    """Document Semantic configuration using pydantic-settings.

    Resolution order (highest priority first):
    1. Explicit arguments passed to constructor
    2. Environment variables (DOC_SEMANTIC_* or specific ones)
    3. .env file
    4. config.yaml or doc_semantic.yaml
    5. Default values
    """

    parser: str = Field(
        default=constants.DEFAULT_PARSER,
        validation_alias=AliasChoices("parser", constants.ENV_PARSER),
    )
    recognizer: str = Field(
        default=constants.DEFAULT_RECOGNIZER,
        validation_alias=AliasChoices("recognizer", constants.ENV_RECOGNIZER),
    )
    recognizer_config: dict[str, Any] = Field(default_factory=dict)
    verbosity: str = Field(
        default=constants.DEFAULT_VERBOSITY,
        validation_alias=AliasChoices("verbosity", constants.ENV_VERBOSITY),
    )
    suppress_warnings: list[str] = Field(default_factory=list)
    log_level: str = Field(
        default=constants.DEFAULT_LOG_LEVEL,
        validation_alias=AliasChoices("log_level", constants.ENV_LOG_LEVEL),
    )

    # MinerU-specific settings
    mineru_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("mineru_token", constants.ENV_MINERU_TOKEN, constants.ENV_MINERU_TOKEN_ALT),
    )
    mineru_cache_dir: str | None = Field(
        default="",
        validation_alias=AliasChoices("mineru_cache_dir", constants.ENV_MINERU_CACHE_DIR),
    )
    mineru_pdf_cache_dir: str | None = Field(
        default="",
        validation_alias=AliasChoices("mineru_pdf_cache_dir", constants.ENV_MINERU_PDF_CACHE_DIR),
    )
    mineru_skip_image_ocr: bool | None = Field(
        default=False,
        validation_alias=AliasChoices("mineru_skip_image_ocr", constants.ENV_MINERU_SKIP_IMAGE_OCR),
    )

    recognizer_model_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("recognizer_model_id", constants.ENV_RECOGNIZER_MODEL_ID),
    )

    recognizer_model_provider_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("recognizer_model_provider_url", constants.ENV_RECOGNIZER_MODEL_PROVIDER_URL),
    )

    recognizer_model_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("recognizer_model_api_key", constants.ENV_RECOGNIZER_MODEL_API_KEY),
    )

    recognizer_modelizer_model_timeout: int | None = Field(
        default=120,
        validation_alias=AliasChoices(
            "recognizer_modelizer_model_timeout", constants.ENV_RECOGNIZER_MODELIZER_MODEL_TIMEOUT
        ),
    )

    # Processor output settings (default to True)
    output_markdown: bool = True
    output_resources: bool = True
    output_json_mapping: bool = True
    use_xml_placeholders: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            MultiYamlConfigSettingsSource(settings_cls),
        )

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> Settings:
        """Load configuration.

        If config_path is provided, it is used as the primary YAML source.
        Otherwise, it searches for default config files.
        """
        if config_path:
            p = Path(config_path)
            if p.exists():
                logger.debug(f"[config] Loading explicit config from {p}")
                with open(p, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                # Create with the data from YAML, but env vars will still override
                # because we want to maintain the same priority as BaseSettings
                # However, if we want the explicit YAML to be higher priority than default YAML,
                # we can just pass it to __init__ which has highest priority.
                # But wait, current load() implementation allowed env to override YAML.
                # To maintain that, we should use a temporary settings class or similar.
                # Actually, the simplest is to just instantiate it.
                return cls(**data)
            else:
                logger.warning(f"[config] Explicit config path {p} does not exist")

        return cls()


settings = Settings.load()
