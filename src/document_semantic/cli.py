import json
from pathlib import Path
from typing import Optional

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
    refine: bool = typer.Option(False, "--refine", help="Refine content using Agent"),
    translate: Optional[str] = typer.Option(None, "--translate", help="Target language for translation (e.g., 'English')"),
    template: Optional[str] = typer.Option(None, "--template", help="Template ID for rendering (e.g., 'jcst-v2')"),
):
    """Run the processor output workflow with optional Agent-based enhancements."""
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
                title="Document Semantic Workflow",
            )
        )

        # 1. Base Parsing
        result = proc_parser.process(docx_path, output_dir, config=processor_config, skip_image_ocr=skip_image_ocr)
        
        # We need content_list for further processing
        if not result.content_list_json_path:
            rprint("[yellow]Warning:[/yellow] No content_list.json produced. Skipping Agent steps.")
            _print_result_table(result)
            return

        with open(result.content_list_json_path, "r", encoding="utf-8") as f:
            from document_semantic.models.mineru_content import MinerUContentList
            content = MinerUContentList.model_validate(json.load(f))

        # 2. Refinement
        if refine:
            rprint("[bold blue]Starting Content Refinement Agent...[/bold blue]")
            from document_semantic.agents.refinement_agent import LLMRefinementAgent
            from document_semantic.workflows.content_refinement import ContentRefinementWorkflow
            
            refine_agent = LLMRefinementAgent()
            refine_workflow = ContentRefinementWorkflow(refine_agent)
            content = refine_workflow.process_document(content)
            
            # Update file
            with open(result.content_list_json_path, "w", encoding="utf-8") as f:
                f.write(content.model_dump_json(indent=2))

        # 3. Translation
        if translate:
            rprint(f"[bold blue]Starting Translation Agent (to {translate})...[/bold blue]")
            from document_semantic.agents.judger import LLMJudgerAgent
            from document_semantic.agents.translator import LLMTranslationAgent
            from document_semantic.workflows.translation import TranslationWorkflow
            
            trans_agent = LLMTranslationAgent()
            judger_agent = LLMJudgerAgent()
            trans_workflow = TranslationWorkflow(translators=[trans_agent], judger=judger_agent)
            
            content = trans_workflow.translate_document(content, tgt_lang=translate)
            
            # Update file
            with open(result.content_list_json_path, "w", encoding="utf-8") as f:
                f.write(content.model_dump_json(indent=2))

        # 4. Rendering with Template
        if template:
            rprint(f"[bold blue]Applying Semantic Template: {template}...[/bold blue]")
            from document_semantic.agents.semantic_annotator import SemanticAnnotatorAgent
            from document_semantic.renderers.advanced_docx_renderer import AdvancedDocxRenderer
            from document_semantic.templates.registry import TemplateRegistry
            
            tpl = TemplateRegistry.get(template)
            if not tpl:
                rprint(f"[red]Error:[/red] Template '{template}' not found.")
            else:
                annotator = SemanticAnnotatorAgent()
                annotated_content = annotator.annotate(content.root, tpl)
                
                renderer = AdvancedDocxRenderer(resources_dir=result.resources_dir)
                final_docx = output_dir / f"output_{template}.docx"
                renderer.render(annotated_content, tpl, final_docx)
                
                # Add to result (hacky but works for display)
                result.metadata["final_docx"] = final_docx

        _print_result_table(result)

    except Exception as e:
        rprint(f"[bold red]Error:[/bold red] {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise typer.Exit(code=1)


def _print_result_table(result):
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
    if result.content_list_json_path:
        table.add_row("Content JSON", str(result.content_list_json_path))
    
    final_docx = result.metadata.get("final_docx")
    if final_docx:
        table.add_row("Final Document", str(final_docx))

    console.print(table)


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
