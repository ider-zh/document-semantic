## 1. Setup and Configuration

- [x] 1.1 Add `skip_image_ocr` parameter to `MinerUParser` constructor and `PipelineConfig` with default `False`
- [x] 1.2 Create helper function `generate_placeholder_image()` that produces a uniform 800x600 gray PNG
- [x] 1.3 Create helper function `extract_images_from_docx()` that extracts all images from `word/media/` to a temp directory

## 2. Preprocessing: DOCX Image Substitution

- [x] 2.1 Implement `_replace_images_in_docx()` that takes original DOCX, extracts images, replaces them with placeholders, and writes modified DOCX to temp file
- [x] 2.2 Ensure ZIP-level replacement preserves all relationship IDs and document structure
- [x] 2.3 Add logic in `_upload_and_download()` to use modified DOCX when `skip_image_ocr=True`
- [x] 2.4 Implement cleanup of temporary files in finally blocks to ensure cleanup on success/failure

## 3. Postprocessing: Image Restoration in Result ZIP

- [x] 3.1 Implement `_restore_images_in_zip()` that takes result ZIP and original images, replaces placeholders with originals by order/index
- [x] 3.2 Handle case where MinerU result ZIP has different number of images than original DOCX (log warning, restore what's possible)
- [x] 3.3 Integrate restoration step into `_get_zip_data()` and `parse()` flow after receiving result from API

## 4. Dual ZIP Cache Implementation

- [x] 4.1 Modify `_save_to_cache()` to save both `result_placeholders.zip` and `result_restored.zip` when `skip_image_ocr=True`
- [x] 4.2 Ensure `result.zip` points to `result_restored.zip` for backward compatibility
- [x] 4.3 Modify `_check_cache()` to load from `result_restored.zip` when available
- [x] 4.4 Update `_get_zip_data()` to handle both ZIP variants correctly

## 5. Testing

- [x] 5.1 Write unit test for `generate_placeholder_image()` - verify PNG output with correct dimensions
- [x] 5.2 Write unit test for `extract_images_from_docx()` - verify all images extracted to temp dir
- [x] 5.3 Write unit test for `_replace_images_in_docx()` - verify modified DOCX has placeholder images instead of originals
- [x] 5.4 Write unit test for `_restore_images_in_zip()` - verify originals are correctly placed back in ZIP
- [x] 5.5 Write integration test: full flow with `skip_image_ocr=True` - verify cache contains both ZIPs
- [x] 5.6 Write integration test: verify backward compatibility when `skip_image_ocr=False` (default behavior unchanged)
- [x] 5.7 Verify that OCR-extracted text from images is absent when `skip_image_ocr=True`

## 6. Documentation and Cleanup

- [x] 6.1 Update README or docstrings to document `skip_image_ocr` flag
- [x] 6.2 Add inline code comments explaining the placeholder substitution workflow
- [x] 6.3 Run linting and type checks on all modified files
- [x] 6.4 Verify all tests pass (existing + new tests)
