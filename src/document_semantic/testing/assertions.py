"""Assertion helpers for validating SemanticDocument output against expectations.

Provides block-level and inline element assertion helpers, expected output
loading from YAML fixtures, and partial assertion mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from document_semantic.models.semantic_document import SemanticDocument
from document_semantic.observability.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Block-level assertions
# ---------------------------------------------------------------------------


def assert_block_count(doc: SemanticDocument, expected: int) -> None:
    """Assert that the document has exactly *expected* blocks.

    Raises:
        AssertionError: If block count does not match.
    """
    actual = len(doc.blocks)
    if actual != expected:
        raise AssertionError(f"Expected {expected} blocks, got {actual}")


def assert_block_types(
    doc: SemanticDocument, expected_types: list[str]
) -> None:
    """Assert that block types match *expected_types* in order.

    For partial matching (fewer expected types than actual blocks), only the
    first N blocks are checked.

    Raises:
        AssertionError: If types do not match at the first mismatched position.
    """
    actual_types = [b.type for b in doc.blocks]
    check_len = min(len(expected_types), len(actual_types))

    for i in range(check_len):
        if actual_types[i] != expected_types[i]:
            raise AssertionError(
                f"Block type mismatch at index {i}: "
                f"expected '{expected_types[i]}', got '{actual_types[i]}'. "
                f"Full actual types: {actual_types}"
            )

    if len(expected_types) > len(actual_types):
        raise AssertionError(
            f"Expected {len(expected_types)} block types, "
            f"but document only has {len(actual_types)} blocks. "
            f"Missing types starting at index {len(actual_types)}."
        )


def assert_block_content_contains(
    doc: SemanticDocument, index: int, substring: str
) -> None:
    """Assert that the block at *index* contains *substring*.

    Raises:
        AssertionError: If the index is out of range or substring not found.
    """
    if index < 0 or index >= len(doc.blocks):
        raise AssertionError(
            f"Block index {index} out of range (document has {len(doc.blocks)} blocks)"
        )
    content = doc.blocks[index].content
    if substring not in content:
        raise AssertionError(
            f"Block {index} does not contain '{substring}'. "
            f"Actual content: {content!r}"
        )


# ---------------------------------------------------------------------------
# Inline element assertions
# ---------------------------------------------------------------------------


def assert_inline_element_count(
    doc: SemanticDocument, block_index: int, element_type: str, expected: int
) -> None:
    """Assert that the block at *block_index* has *expected* inline elements of *element_type*.

    Raises:
        AssertionError: If block index is out of range or count does not match.
    """
    if block_index < 0 or block_index >= len(doc.blocks):
        raise AssertionError(
            f"Block index {block_index} out of range (document has {len(doc.blocks)} blocks)"
        )
    block = doc.blocks[block_index]
    actual_count = sum(
        1 for el in block.inline_elements if el.type == element_type
    )
    if actual_count != expected:
        raise AssertionError(
            f"Block {block_index}: expected {expected} '{element_type}' inline elements, "
            f"got {actual_count}"
        )


def assert_inline_element_text(
    doc: SemanticDocument,
    block_index: int,
    element_type: str,
    element_index: int,
    expected_text: str,
) -> None:
    """Assert that the inline element at (*block_index*, *element_index*) of *element_type* has *expected_text*.

    Raises:
        AssertionError: If the element is not found or text does not match.
    """
    if block_index < 0 or block_index >= len(doc.blocks):
        raise AssertionError(
            f"Block index {block_index} out of range (document has {len(doc.blocks)} blocks)"
        )
    block = doc.blocks[block_index]
    typed_elements = [
        el for el in block.inline_elements if el.type == element_type
    ]
    if element_index < 0 or element_index >= len(typed_elements):
        raise AssertionError(
            f"Block {block_index}: expected '{element_type}' element at index "
            f"{element_index}, but only {len(typed_elements)} '{element_type}' "
            f"elements exist"
        )
    actual_text = typed_elements[element_index].text
    if actual_text != expected_text:
        raise AssertionError(
            f"Block {block_index}, '{element_type}' element {element_index}: "
            f"expected text '{expected_text}', got '{actual_text}'"
        )


# ---------------------------------------------------------------------------
# Expected output loading
# ---------------------------------------------------------------------------


def load_expected_output(yaml_path: Path) -> dict[str, Any]:
    """Load expected output definition from a YAML fixture.

    Args:
        yaml_path: Path to the expected output YAML file.

    Returns:
        Dictionary matching the structure of SemanticDocument.model_dump().

    Raises:
        FileNotFoundError: If the YAML file does not exist.
    """
    if not yaml_path.exists():
        raise FileNotFoundError(f"Expected output file not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}
    return data


# ---------------------------------------------------------------------------
# Partial assertion mode
# ---------------------------------------------------------------------------


def assert_document_partial(
    actual: SemanticDocument, expected: dict[str, Any]
) -> list[str]:
    """Assert that *actual* matches the specified fields in *expected*.

    Only fields present in *expected* are checked; unspecified fields are
    ignored. Supports checking:
    - ``block_count``: exact block count
    - ``block_types``: list of expected block types (checked in order, up to
      the length of ``block_types``)
    - ``blocks``: dict keyed by block index, each with optional ``type``,
      ``content_contains`` (list of substrings), and ``inline_elements`` checks.

    Returns:
        List of failure messages (empty if all assertions pass).
    """
    failures: list[str] = []

    # Block count
    if "block_count" in expected:
        try:
            assert_block_count(actual, expected["block_count"])
        except AssertionError as e:
            failures.append(str(e))

    # Block types
    if "block_types" in expected:
        try:
            assert_block_types(actual, expected["block_types"])
        except AssertionError as e:
            failures.append(str(e))

    # Per-block checks
    if "blocks" in expected:
        for idx_str, block_expect in expected["blocks"].items():
            block_idx = int(idx_str)
            block = actual.blocks[block_idx] if block_idx < len(actual.blocks) else None

            if block is None:
                failures.append(
                    f"Block {block_idx}: does not exist (document has {len(actual.blocks)} blocks)"
                )
                continue

            # Type check
            if "type" in block_expect and block.type != block_expect["type"]:
                failures.append(
                    f"Block {block_idx}: expected type '{block_expect['type']}', got '{block.type}'"
                )

            # Content substring checks
            if "content_contains" in block_expect:
                for substring in block_expect["content_contains"]:
                    if substring not in block.content:
                        failures.append(
                            f"Block {block_idx}: does not contain '{substring}'. "
                            f"Content: {block.content!r}"
                        )

            # Inline element checks
            if "inline_elements" in block_expect:
                for el_expect in block_expect["inline_elements"]:
                    el_type = el_expect.get("type")
                    el_idx = el_expect.get("index", 0)
                    typed = [
                        el for el in block.inline_elements if el.type == el_type
                    ]
                    if el_idx < len(typed):
                        actual_el = typed[el_idx]
                        if "text" in el_expect and actual_el.text != el_expect["text"]:
                            failures.append(
                                f"Block {block_idx}, '{el_type}' element {el_idx}: "
                                f"expected text '{el_expect['text']}', got '{actual_el.text}'"
                            )
                    else:
                        failures.append(
                            f"Block {block_idx}: expected '{el_type}' element at index "
                            f"{el_idx}, but only {len(typed)} exist"
                        )

    return failures
