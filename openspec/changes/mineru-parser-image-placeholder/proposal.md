## Why

When processing DOCX files with MinerU parser, images are sent through OCR processing, which extracts unwanted text content from images. This introduces noise into the parsed output when images should be preserved as-is without OCR extraction. We need a way to bypass image OCR while maintaining the document structure and ensuring the final output contains the original images.

## What Changes

- **Before MinerU processing**: Replace images in the DOCX with uniformly-sized placeholder images to prevent OCR extraction
- **After MinerU processing**: Swap placeholder images back with original images in the output ZIP
- **Cache output**: Generate two ZIP files - one with placeholders (MinerU's output) and one with restored original images (final cache)
- Maintain backward compatibility with existing parsing workflows

## Capabilities

### New Capabilities
- `image-placeholder-substitution`: Substitution of images with placeholders before MinerU processing and restoration after processing to prevent unwanted OCR extraction

### Modified Capabilities
- `mineru-parser`: The MinerU parser's preprocessing and caching workflow will be extended to support image placeholder substitution

## Impact

- **Affected code**: `src/document_semantic/parsers/mineru_parser.py` - preprocessing and postprocessing logic
- **Dependencies**: May require a library for DOCX manipulation (e.g., `python-docx`) and image handling
- **Cache structure**: Cache will now store two ZIP files instead of one
- **API**: No breaking changes to public API; new behavior can be optional via config flag