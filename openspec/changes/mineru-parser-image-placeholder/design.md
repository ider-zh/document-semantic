## Context

The `MinerUParser` currently uploads DOCX files to the MinerU API, which extracts images and runs OCR on them. This OCR extraction introduces unwanted text content into the parsed output when images should be preserved as-is. The current cache stores a single `result.zip` file keyed by the MD5 hash of the original DOCX file.

## Goals / Non-Goals

**Goals:**
- Prevent MinerU from OCR-ing images by replacing them with uniform placeholders before upload
- Restore original images in the final output ZIP after processing
- Store two ZIP files in cache: the raw MinerU output (with placeholders) and the restored output (with original images)
- Keep the feature opt-in via a configuration flag to maintain backward compatibility

**Non-Goals:**
- Changing the MinerU API interaction protocol
- Modifying how text/content is extracted (only image handling is affected)
- Adding image format conversion or resizing of original images

## Decisions

### 1. Placeholder Image Strategy
**Decision**: Generate a single uniform PNG (e.g., 800x600 solid gray) and use it to replace all images in the DOCX before processing.

**Rationale**: A uniform image prevents OCR from extracting any meaningful text while maintaining the structural position of images in the document. Using a single generated PNG avoids dependencies on external placeholder libraries.

**Alternatives considered**:
- Using blank white images: Could be confused with page backgrounds
- Removing images entirely: Would change document structure and page count
- Using text labels: Would still be extracted by OCR

### 2. DOCX Manipulation Library
**Decision**: Use `python-docx` for reading/modifying DOCX files and `zipfile` for ZIP manipulation.

**Rationale**: `python-docx` is already a common dependency for DOCX processing in Python. For ZIP manipulation, the built-in `zipfile` module is sufficient.

**Alternatives considered**:
- Direct ZIP manipulation of DOCX (DOCX is a ZIP): Would require manual XML parsing of `document.xml` to find image relationships
- Using `docx2python`: Less common, adds unnecessary dependency

### 3. Image Replacement in DOCX
**Decision**: Replace all image parts in the DOCX package with the placeholder PNG data while preserving the original image file entries (same path, same relationship IDs).

**Rationale**: This approach maintains the DOCX structure and ensures MinerU sees the same number of images at the same positions. The placeholder PNG should match the dimensions of a typical image to avoid layout shifts.

**Implementation approach**:
1. Open DOCX as a ZIP (since DOCX is a ZIP of XMLs)
2. Extract all image files (typically in `word/media/`)
3. Store original images in memory
4. Replace each image with a generated placeholder PNG of consistent size (e.g., 800x600)
5. Write modified DOCX to a temporary file for upload

### 4. Post-Processing Image Restoration
**Decision**: After MinerU returns the result ZIP, replace placeholder images in the ZIP with the original images before saving to cache.

**Rationale**: The final output should contain the original images. Since we know the mapping between original image paths and their positions, we can restore them in the result ZIP.

**Implementation approach**:
1. Keep a mapping of original image paths → placeholder positions
2. Open the result ZIP
3. For each placeholder image location in the result, replace with the corresponding original image
4. Write the restored ZIP as the final cache output

### 5. Cache Structure
**Decision**: Store two files in the cache directory:
- `result_placeholders.zip` - The raw MinerU output with placeholder images
- `result_restored.zip` - The final output with original images restored

**Rationale**: Keeping both allows inspection/debugging of what MinerU actually processed vs. the final output. The existing `result.zip` name will point to the restored version for backward compatibility.

### 6. Opt-In Configuration
**Decision**: Add a `skip_image_ocr` flag (default: `False`) to enable this behavior.

**Rationale**: Existing workflows may depend on the current OCR behavior. Making it opt-in ensures no breaking changes.

## Risks / Trade-offs

**[Risk]**: Placeholder images may not match original image dimensions, causing layout differences in MinerU's output.  
**Mitigation**: Use a reasonable default size (800x600) that works for most document images. Consider analyzing original image dimensions and generating per-image placeholders if needed.

**[Risk]**: DOCX manipulation may corrupt the file if relationship IDs are not properly preserved.  
**Mitigation**: Use ZIP-level replacement (replace bytes in `word/media/*` entries) rather than XML-level changes to minimize structural impact.

**[Risk]**: Large DOCX files with many images will consume significant memory when storing originals.  
**Mitigation**: Write originals to a temporary directory instead of keeping all in memory. Clean up temp files after upload.

**[Risk]**: MinerU result ZIP may have different image paths/names than the original DOCX.  
**Mitigation**: Map images by order/index rather than by path. The first image in DOCX → first image in result ZIP, etc.

## Migration Plan

1. **Implementation**: Add `skip_image_ocr` flag to `MinerUParser` config
2. **Testing**: Verify with sample DOCX files that:
   - Placeholders prevent OCR extraction
   - Original images are correctly restored in final output
   - Cache contains both ZIPs for inspection
3. **Rollout**: Enable flag on a per-document basis; monitor output quality
4. **Rollback**: Set `skip_image_ocr=False` to revert to original behavior

## Open Questions

- Should placeholder images be generated per-image with matching dimensions, or use a single uniform size?
- How should we handle embedded images vs. linked images in DOCX?
- Should the two ZIP files be named differently in the cache to make inspection easier?
