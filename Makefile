.PHONY: help test test-verbose test-cov test-update-snapshots clean install sync \
        lint format check run-example \
        test-docx test-docx-single

# ─────────────────────────────────────────────────────
# Variables
# ─────────────────────────────────────────────────────
PYTHON  := uv run python
PYTEST  := uv run pytest
SRC     := src/document_semantic
TESTS   := tests

# ─────────────────────────────────────────────────────
# Default target
# ─────────────────────────────────────────────────────
help:
	@echo "Available targets:"
	@echo "  install              Sync all dependencies (uv sync)"
	@echo "  test                 Run tests (short output)"
	@echo "  test-verbose         Run tests with full output and coverage report"
	@echo "  test-cov             Run tests with HTML coverage report"
	@echo "  test-update          Update snapshot test fixtures"
	@echo "  test-parser FILE     Run pipeline on a specific DOCX file"
	@echo "  test-docx            Run real DOCX test flow on all files in tests/docx/"
	@echo "  test-docx-single FILE= Run real DOCX test flow for a single file"
	@echo "  lint                 Run ruff linter on source and tests"
	@echo "  format               Auto-format source and tests with ruff"
	@echo "  check                Run lint + type check + tests"
	@echo "  run-example          Run a quick pipeline example on tests/fixtures/test_1.docx"
	@echo "  clean                Remove build artifacts, caches, and debug files"

# ─────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────
install:
	uv sync --all-extras

sync: install

# ─────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────
test:
	$(PYTEST) $(TESTS) -v --tb=short

test-verbose:
	$(PYTEST) $(TESTS) -v --tb=long -s

test-cov:
	$(PYTEST) $(TESTS) -v --tb=short \
		--cov=$(SRC) --cov-report=term-missing --cov-report=html:htmlcov

test-update:
	$(PYTEST) $(TESTS) -v --tb=short --snapshot-update

# Run real DOCX test flow on all files in tests/docx/
test-docx:
	$(PYTEST) tests/test_docx_flow.py -v

# Run real DOCX test flow for a single file
# Usage: make test-docx-single FILE=test_1.docx
test-docx-single:
	$(PYTEST) tests/test_docx_flow.py -v -k "$(FILE)"

# Run pipeline on a specific DOCX file
# Usage: make test-parser FILE=tests/fixtures/test_1.docx
test-parser:
	$(PYTHON) -c " \
	import sys; sys.stdout.reconfigure(encoding='utf-8'); \
	from pathlib import Path; \
	from document_semantic.pipeline import Pipeline, PipelineConfig; \
	config = PipelineConfig.load(); \
	pipeline = Pipeline.from_config(config); \
	doc = Path('$(FILE)'); \
	result = pipeline.run(doc); \
	print(f'Blocks: {len(result.blocks)}'); \
	[pipeline.print_result(result) for _ in [None]]; \
	print(pipeline.get_trace().summary()) \
	"

# ─────────────────────────────────────────────────────
# Code quality
# ─────────────────────────────────────────────────────
lint:
	$(PYTHON) -m ruff check $(SRC) $(TESTS)

format:
	$(PYTHON) -m ruff format $(SRC) $(TESTS)

check: lint test

# ─────────────────────────────────────────────────────
# Examples
# ─────────────────────────────────────────────────────
run-example:
	$(PYTHON) -c " \
	import sys; sys.stdout.reconfigure(encoding='utf-8'); \
	from pathlib import Path; \
	from document_semantic.pipeline import Pipeline, PipelineConfig; \
	config = PipelineConfig(parser='python-docx', recognizer='regex', verbosity='preview'); \
	pipeline = Pipeline.from_config(config); \
	result = pipeline.run(Path('tests/fixtures/test_1.docx')); \
	pipeline.print_result(result); \
	print(); \
	print(pipeline.get_trace().summary()) \
	"

# ─────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────
clean:
	@# Python cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@# Test/build artifacts
	rm -rf .pytest_cache 2>/dev/null || true
	rm -rf htmlcov 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	rm -rf .ruff_cache 2>/dev/null || true
	@# Debug/temp files
	rm -f _debug_*.py _debug_*.txt _test_*.py _test_*.txt 2>/dev/null || true
	@echo "Cleaned."
