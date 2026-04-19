## ADDED Requirements

### Requirement: Image placeholder substitution before processing
The `MinerUParser` SHALL support replacing all images in a DOCX file with uniformly-sized placeholder images before uploading to the MinerU API. This behavior SHALL be controlled by a `skip_image_ocr` configuration flag (default: `False`). When enabled, the parser SHALL create a modified DOCX with placeholder images, upload that for processing, and retain the original images for later restoration.

#### Scenario: Placeholder substitution enabled
- **WHEN** `skip_image_ocr=True` is configured and `MinerUParser.parse()` is called
- **THEN** the parser SHALL replace all images in the DOCX with placeholder images before uploading to the MinerU API

#### Scenario: Placeholder substitution disabled
- **WHEN** `skip_image_ocr=False` (default)
- **THEN** the parser SHALL upload the original DOCX without any image modifications

### Requirement: Original image restoration in result ZIP
After receiving the result ZIP from the MinerU API, the parser SHALL replace placeholder images in the result ZIP with the original images from the source DOCX. The restoration SHALL preserve the order of images (first original image → first image position in result).

#### Scenario: Image restoration after processing
- **WHEN** the result ZIP is received from MinerU API with `skip_image_ocr=True`
- **THEN** the parser SHALL replace all placeholder images in the result ZIP with the corresponding original images

#### Scenario: Image order preservation
- **WHEN** restoring images from DOCX to result ZIP
- **THEN** images SHALL be mapped by their sequential order (1st image in DOCX → 1st image position in result ZIP)

### Requirement: Dual ZIP cache output
When `skip_image_ocr=True`, the cache SHALL store two ZIP files: `result_placeholders.zip` (raw MinerU output with placeholders) and `result_restored.zip` (final output with original images). The existing `result.zip` filename SHALL point to `result_restored.zip` for backward compatibility.

#### Scenario: Cache stores both ZIPs
- **WHEN** processing completes with `skip_image_ocr=True`
- **THEN** the cache directory SHALL contain both `result_placeholders.zip` and `result_restored.zip`

#### Scenario: Backward compatibility with result.zip
- **WHEN** accessing `result.zip` from cache
- **THEN** it SHALL refer to `result_restored.zip` (the output with original images)

### Requirement: Temporary original image storage
The parser SHALL store original images extracted from the DOCX in a temporary location during processing. These originals SHALL be used for restoration in the result ZIP and SHALL be cleaned up after processing completes or fails.

#### Scenario: Temporary storage of originals
- **WHEN** images are extracted from DOCX for placeholder substitution
- **THEN** the original images SHALL be written to a temporary directory

#### Scenario: Cleanup after processing
- **WHEN** processing completes (success or failure)
- **THEN** the temporary directory containing original images SHALL be deleted
