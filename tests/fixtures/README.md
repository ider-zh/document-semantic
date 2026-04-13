# Test Fixtures

This directory contains sample DOCX files and expected JSON outputs for testing.

## DOCX Fixtures

DOCX files are generated programmatically in `conftest.py` fixtures, so they don't need to be committed.
The expected JSON output files (`*_expected.json`) ARE committed.

### Expected fixture files:
- `simple_document_expected.json` - title + headings + text
- `academic_document_expected.json` - abstract, headings, references
