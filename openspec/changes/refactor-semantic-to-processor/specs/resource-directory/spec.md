## ADDED Requirements

### Requirement: Resource directory structure
The processor SHALL create a resource directory at `{output_dir}/resources/` containing:
- An `images/` subdirectory with all extracted images
- A `resources.json` mapping file at `{output_dir}/resources.json`

The resource directory SHALL be created alongside the Markdown output file.

#### Scenario: Resource directory created with images
- **WHEN** the processor encounters image elements in the document
- **THEN** images are saved to `{output_dir}/resources/images/` and referenced in the Markdown as `![caption](resources/images/<filename>)`

### Requirement: JSON mapping file format
The `resources.json` file SHALL contain a JSON object with the following structure:
```json
{
  "version": "1.0",
  "resources": {
    "formula": { "1": { "content": "...", "type": "block|inline" } },
    "code": { "1": { "content": "...", "type": "block|inline" } },
    "image": { "1": { "content": "...", "type": "block|inline", "path": "resources/images/..." } }
  },
  "metadata": {
    "source_path": "...",
    "parser": "...",
    "processed_at": "..."
  }
}
```

The mapping SHALL group resources by type (formula, code, image) and then by ID.

#### Scenario: JSON mapping contains all placeholder content
- **WHEN** the processor generates Markdown with 3 formula placeholders and 2 image placeholders
- **THEN** `resources.json` contains entries under `resources.formula` for IDs 1-3 and `resources.image` for IDs 1-2, each with content and type fields

### Requirement: Image attachment handling
Images extracted from the document SHALL be:
- Saved to `resources/images/` with sequential naming: `image_1.png`, `image_2.png`, etc.
- Referenced in Markdown as `![alt_text](resources/images/image_N.ext)`
- The XML placeholder `<image id="N"/>` SHALL be replaced with the Markdown image reference, not left as a bare placeholder

#### Scenario: Image extracted and referenced
- **WHEN** the processor encounters an image element with binary data
- **THEN** the image is saved to `resources/images/image_1.png` and the Markdown contains `![caption](resources/images/image_1.png)` and `resources.json` records the path and metadata
