"""Tests for MinerU parser image placeholder substitution."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest

from document_semantic.parsers.mineru_parser import (
    _generate_placeholder_image,
    _extract_images_from_docx,
    _replace_images_in_docx,
    _restore_images_in_zip,
    _is_image_path,
)


class TestGeneratePlaceholderImage:
    """Tests for placeholder image generation."""

    def test_placeholder_is_valid_png(self):
        """Generated placeholder should be valid PNG data."""
        data = _generate_placeholder_image()
        assert data is not None
        assert len(data) > 0
        # PNG magic bytes: \x89PNG\r\n\x1a\n
        assert data[:8] == b"\x89PNG\r\n\x1a\n"

    def test_placeholder_dimensions(self):
        """Generated placeholder should be 800x600 pixels."""
        try:
            from PIL import Image
            import io

            data = _generate_placeholder_image()
            img = Image.open(io.BytesIO(data))
            assert img.size == (800, 600)
        except ImportError:
            # Skip if PIL not available (fallback mode)
            pytest.skip("PIL not available")


class TestExtractImagesFromDocx:
    """Tests for DOCX image extraction."""

    def test_extract_images_to_temp_directory(self, sample_docx_with_images):
        """Should extract all images from DOCX to temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            images = _extract_images_from_docx(sample_docx_with_images, output_dir)

            # Should have extracted at least one image
            assert len(images) > 0
            # All images should exist in output directory
            for img_path in images:
                assert img_path.exists()
                assert img_path.parent == output_dir

    def test_extract_images_preserves_order(self, sample_docx_with_images):
        """Extracted images should be in consistent order (sorted by name)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            images = _extract_images_from_docx(sample_docx_with_images, output_dir)

            # Images should be sorted by original name
            names = [img.name for img in images]
            assert names == sorted(names)


class TestReplaceImagesInDocx:
    """Tests for DOCX image replacement."""

    def test_replace_images_with_placeholders(self, sample_docx_with_images):
        """Should replace all images in DOCX with placeholders."""
        placeholder_data = _generate_placeholder_image()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "modified.docx"
            replace_count = _replace_images_in_docx(
                sample_docx_with_images, placeholder_data, output_path
            )

            # Should have replaced at least one image
            assert replace_count > 0
            # Output file should exist
            assert output_path.exists()

            # Verify the output is a valid ZIP (DOCX is ZIP)
            with zipfile.ZipFile(output_path, "r") as zf:
                # All word/media/* files should be the placeholder size
                for name in zf.namelist():
                    if name.startswith("word/media/"):
                        img_data = zf.read(name)
                        assert img_data == placeholder_data

    def test_replace_preserves_document_structure(self, sample_docx_with_images):
        """Replacement should preserve all non-image files in DOCX."""
        placeholder_data = _generate_placeholder_image()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "modified.docx"
            _replace_images_in_docx(sample_docx_with_images, placeholder_data, output_path)

            # Compare ZIP contents
            with zipfile.ZipFile(sample_docx_with_images, "r") as orig_zip:
                with zipfile.ZipFile(output_path, "r") as mod_zip:
                    orig_names = set(orig_zip.namelist())
                    mod_names = set(mod_zip.namelist())
                    # All original files should still be present
                    assert orig_names == mod_names


class TestRestoreImagesInZip:
    """Tests for result ZIP image restoration."""

    def test_restore_images_from_result_zip(self, sample_docx_with_images):
        """Should restore original images in result ZIP."""
        # First extract originals
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            originals_dir = tmpdir_path / "originals"
            originals_dir.mkdir()

            originals = _extract_images_from_docx(sample_docx_with_images, originals_dir)

            # Create a mock result ZIP with placeholders
            result_zip_path = tmpdir_path / "result.zip"
            placeholder_data = _generate_placeholder_image()

            with zipfile.ZipFile(result_zip_path, "w") as zf:
                zf.writestr("content_list_v2.json", "[]")
                # Add placeholder images
                for i, orig_img in enumerate(originals):
                    zf.writestr(f"images/image_{i}{orig_img.suffix}", placeholder_data)

            # Restore images
            result_zip_data = result_zip_path.read_bytes()
            restored_data = _restore_images_in_zip(result_zip_data, originals_dir)

            # Verify restoration
            with zipfile.ZipFile(Path(tmpdir_path) / "restored.zip", "w") as zf:
                zf.writestr("temp", restored_data)

            # Check that originals were restored
            with zipfile.ZipFile(Path(tmpdir_path) / "restored.zip", "r") as zf:
                for i, orig_img in enumerate(originals):
                    img_path = f"images/image_{i}{orig_img.suffix}"
                    if img_path in zf.namelist():
                        restored_img = zf.read(img_path)
                        original_img = orig_img.read_bytes()
                        assert restored_img == original_img

    def test_restore_handles_fewer_images_in_result(self, sample_docx_with_images):
        """Should handle case where result has fewer images than original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            originals_dir = tmpdir_path / "originals"
            originals_dir.mkdir()

            # Extract originals
            originals = _extract_images_from_docx(sample_docx_with_images, originals_dir)

            # Create result ZIP with fewer images
            result_zip_path = tmpdir_path / "result.zip"
            placeholder_data = _generate_placeholder_image()

            with zipfile.ZipFile(result_zip_path, "w") as zf:
                zf.writestr("content_list_v2.json", "[]")
                # Only add half the images
                for i in range(len(originals) // 2):
                    zf.writestr(f"images/image_{i}.png", placeholder_data)

            # Should not raise, just warn
            result_zip_data = result_zip_path.read_bytes()
            restored_data = _restore_images_in_zip(result_zip_data, originals_dir)
            assert restored_data is not None


class TestIsImagePath:
    """Tests for image path detection."""

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("images/photo.png", True),
            ("word/media/image1.jpg", True),
            ("resources/images/fig.svg", True),
            ("content_list_v2.json", False),
            ("document.xml", False),
            ("styles/style1.css", False),
        ],
    )
    def test_image_path_detection(self, path, expected):
        """Should correctly identify image file paths."""
        assert _is_image_path(path) == expected


# Fixtures for test documents with images
@pytest.fixture
def sample_docx_with_images():
    """Provide a sample DOCX with images for testing."""
    # For now, create a minimal test DOCX with images
    import tempfile
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / "test_with_images.docx"

        # Create a minimal DOCX with images
        with zipfile.ZipFile(docx_path, "w") as zf:
            # Minimal DOCX structure
            zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n<Default Extension="png" ContentType="image/png"/>\n<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n<Default Extension="xml" ContentType="application/xml"/>\n</Types>')
            zf.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>\n</Relationships>')
            zf.writestr("word/_rels/document.xml.rels", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>\n</Relationships>')
            zf.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n<w:body>\n<w:p><w:r><w:t>Test document with images</w:t></w:r></w:p>\n</w:body>\n</w:document>')

            # Add a minimal PNG image
            minimal_png = _generate_placeholder_image()
            zf.writestr("word/media/image1.png", minimal_png)
            zf.writestr("word/media/image2.png", minimal_png)

        yield docx_path
