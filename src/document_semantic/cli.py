from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from document_semantic.core.config import Settings
from document_semantic.core.logger import get_logger
from document_semantic.models.processor_output import ProcessorConfig
from document_semantic.pipelines.pipeline import Pipeline
from document_semantic.services.parsers.registry import ParserRegistry

app = typer.Typer(
    help="Document Semantic Processing Pipeline CLI",
    add_completion=False,
)
console = Console()
logger = get_logger(__name__)


def get_pipeline(
    parser: str | None = None,
    recognizer: str | None = None,
    log_level: str | None = None,
    verbosity: str | None = None,
    config_path: Path | None = None,
) -> Pipeline:
    """Initialize a pipeline with optional overrides."""
    # Load base config
    config = Settings.load(config_path)

    # Apply overrides from CLI
    if parser:
        config.parser = parser
    if recognizer:
        config.recognizer = recognizer
    if log_level:
        config.log_level = log_level
    if verbosity:
        config.verbosity = verbosity

    return Pipeline.from_config(config)


@app.command(name="run")
def run_pipeline(
    docx_path: Path = typer.Argument(..., help="Path to the DOCX file to process", exists=True, dir_okay=False),
    parser: str | None = typer.Option(None, "--parser", "-p", help="Parser backend to use"),
    recognizer: str | None = typer.Option(None, "--recognizer", "-r", help="Recognizer backend to use"),
    log_level: str | None = typer.Option(None, "--log-level", "-l", help="Log level (DEBUG, INFO, etc.)"),
    verbosity: str = typer.Option("preview", "--verbosity", "-v", help="Output verbosity (summary, preview, full)"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to a custom config.yaml"),
):
    """Run the semantic recognition workflow on a DOCX file."""
    try:
        pipeline = get_pipeline(parser, recognizer, log_level, verbosity, config)
        rprint(
            Panel(
                f"Processing [bold cyan]{docx_path}[/bold cyan]\nParser: [green]{pipeline.parser.name}[/green]",
                title="Document Semantic Pipeline",
            )
        )

        result = pipeline.run(docx_path)

        # Use existing pipeline printing logic
        pipeline.print_result(result)

        # Show trace summary
        rprint("\n[bold]Pipeline Trace Summary:[/bold]")
        rprint(pipeline.get_trace().summary())

    except Exception as e:
        rprint(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="process")
def process_pipeline(
    docx_path: Path = typer.Argument(..., help="Path to the DOCX file to process", exists=True, dir_okay=False),
    output_dir: Path = typer.Argument(..., help="Directory to save output artifacts"),
    parser: str | None = typer.Option(None, "--parser", "-p", help="Parser backend to use"),
    log_level: str | None = typer.Option(None, "--log-level", "-l", help="Log level"),
    config: Path | None = typer.Option(None, "--config", "-c", help="Path to a custom config.yaml"),
    skip_image_ocr: bool = typer.Option(False, "--skip-image-ocr", help="Skip OCR on images (MinerU only)"),
    no_markdown: bool = typer.Option(False, "--no-markdown", help="Do not generate markdown file"),
    no_resources: bool = typer.Option(False, "--no-resources", help="Do not generate resources directory"),
    no_json: bool = typer.Option(False, "--no-json", help="Do not generate JSON mapping file"),
):
    """Run the processor output workflow (Markdown + Resources + JSON)."""
    try:
        # Load config for parser selection
        base_config = Settings.load(config)
        parser_name = parser or base_config.parser

        proc_parser = ParserRegistry.get(parser_name)

        processor_config = ProcessorConfig(
            output_markdown=not no_markdown,
            output_resources=not no_resources,
            output_json_mapping=not no_json,
            use_xml_placeholders=True,
        )

        rprint(
            Panel(
                f"Processing [bold cyan]{docx_path}[/bold cyan]\n"
                f"Parser: [green]{parser_name}[/green]\n"
                f"Output: [yellow]{output_dir}[/yellow]",
                title="Processor Workflow",
            )
        )

        result = proc_parser.process(docx_path, output_dir, config=processor_config, skip_image_ocr=skip_image_ocr)

        # Print results
        table = Table(title="Generated Artifacts")
        table.add_column("Type", style="cyan")
        table.add_column("Path", style="green")

        if result.rich_markdown_path:
            table.add_row("Markdown (Rich)", str(result.rich_markdown_path))
        if result.placeholder_markdown_path:
            table.add_row("Markdown (XML)", str(result.placeholder_markdown_path))
        if result.resources_dir:
            table.add_row("Resources", str(result.resources_dir))
        if result.resources_json_path:
            table.add_row("JSON Mapping", str(result.resources_json_path))

        console.print(table)

    except Exception as e:
        rprint(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command(name="config")
def show_config(
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Path to a custom config.yaml"),
):
    """Show the current configuration (resolved from file, env, and defaults)."""
    config = Settings.load(config_path)

    rprint(Panel("Current Configuration", style="bold blue"))

    table = Table(box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    # Core settings
    table.add_row("[bold]Core Settings[/bold]", "")
    table.add_row("  Parser", config.parser)
    table.add_row("  Recognizer", config.recognizer)
    table.add_row("  Log Level", config.log_level)
    table.add_row("  Verbosity", config.verbosity)

    # MinerU settings
    table.add_row("", "")
    table.add_row("[bold]MinerU Settings[/bold]", "")
    token_display = f"{config.mineru_token[:10]}..." if config.mineru_token else "None"
    table.add_row("  Token", token_display)
    table.add_row("  Cache Dir", config.mineru_cache_dir or "Default")
    table.add_row("  PDF Cache Dir", config.mineru_pdf_cache_dir or "Default")
    table.add_row("  Skip Image OCR", str(config.mineru_skip_image_ocr))

    # Output settings
    table.add_row("", "")
    table.add_row("[bold]Output Settings[/bold]", "")
    table.add_row("  Markdown", str(config.output_markdown))
    table.add_row("  Resources", str(config.output_resources))
    table.add_row("  JSON Mapping", str(config.output_json_mapping))

    console.print(table)


if __name__ == "__main__":
    app()
