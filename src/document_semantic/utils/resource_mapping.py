"""Resource mapping utilities for building resources.json files."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .xml_placeholders import PositionType, ResourceType


def build_resources_json(
    resources: dict[str, dict[str, dict[str, Any]]],
    source_path: Optional[str] = None,
    parser_name: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Build and write the resources.json mapping file.

    Args:
        resources: Nested dict grouped by resource type, then by ID.
            Example: {
                "formula": {"1": {"content": "E=mc^2", "type": "block"}},
                "code": {"1": {"content": "print('hi')", "type": "inline"}},
                "image": {"1": {"file": "images/image_1.png", "type": "block"}},
            }
        source_path: Original document path.
        parser_name: Name of the parser used.
        output_dir: Directory to write resources.json to.

    Returns:
        Path to the written resources.json file.
    """
    mapping: dict[str, Any] = {
        "version": "1.0",
        "resources": resources,
        "metadata": {
            "source_path": source_path or "",
            "parser": parser_name or "",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    if output_dir is None:
        output_dir = Path(".")

    output_path = output_dir / "resources.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


class ResourceCollector:
    """Collects resources during processing and outputs the JSON mapping.

    Usage:
        collector = ResourceCollector()
        id1 = collector.add_formula("E = mc^2", position_type="block")
        id2 = collector.add_image("images/image_1.png", content="caption", position_type="block")
        path = collector.write_json(output_dir, source_path, parser_name)
    """

    def __init__(self) -> None:
        self._resources: dict[str, dict[str, dict[str, Any]]] = {
            "formula": {},
            "code": {},
            "image": {},
        }

    def add(
        self,
        resource_type: ResourceType,
        content: Optional[str] = None,
        file_path: Optional[str] = None,
        position_type: PositionType = PositionType.BLOCK,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Add a resource entry and return its assigned ID.

        Args:
            resource_type: Type of resource (formula, code, image).
            content: Original content (for inline resources like formulas, code).
            file_path: Relative file path (for binary resources like images).
            position_type: Whether block or inline.
            metadata: Additional metadata (language, dimensions, etc.).

        Returns:
            The assigned sequential ID (1-based).
        """
        entries = self._resources[resource_type.value]
        new_id = len(entries) + 1

        entry: dict[str, Any] = {
            "type": position_type.value,
        }
        if content is not None:
            entry["content"] = content
        if file_path is not None:
            entry["file"] = file_path
        if metadata:
            entry["metadata"] = metadata
        else:
            entry["metadata"] = {}

        entries[str(new_id)] = entry
        return new_id

    def add_formula(
        self, content: str, position_type: PositionType = PositionType.BLOCK
    ) -> int:
        """Add a formula resource."""
        return self.add(ResourceType.FORMULA, content=content, position_type=position_type)

    def add_code(
        self,
        content: str,
        position_type: PositionType = PositionType.BLOCK,
        language: Optional[str] = None,
    ) -> int:
        """Add a code resource."""
        meta: dict[str, Any] = {}
        if language:
            meta["language"] = language
        return self.add(
            ResourceType.CODE, content=content, position_type=position_type, metadata=meta
        )

    def add_image(
        self,
        file_path: str,
        content: Optional[str] = None,
        position_type: PositionType = PositionType.BLOCK,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Add an image resource."""
        return self.add(
            ResourceType.IMAGE,
            content=content,
            file_path=file_path,
            position_type=position_type,
            metadata=metadata,
        )

    def get_resources(self) -> dict[str, dict[str, dict[str, Any]]]:
        """Return the collected resources dict."""
        return self._resources

    def write_json(
        self,
        output_dir: Path,
        source_path: Optional[str] = None,
        parser_name: Optional[str] = None,
    ) -> Path:
        """Write the collected resources to resources.json."""
        return build_resources_json(
            resources=self._resources,
            source_path=source_path,
            parser_name=parser_name,
            output_dir=output_dir,
        )
