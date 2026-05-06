import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field

from document_semantic.core.config import settings
from document_semantic.core.logger import get_logger

logger = get_logger(__name__)

class VisualTestResult(BaseModel):
    is_format_correct: bool = Field(description="Whether the document formatting (columns, tables, images, margins) looks correct and uncorrupted.")
    issues_found: list[str] = Field(description="List of formatting issues or corruption artifacts found, if any.")
    confidence_score: int = Field(description="Confidence score from 0 to 100.")
    analysis_summary: str = Field(description="A brief summary of the visual analysis.")

class VisualTesterAgent:
    """Agent that visually inspects a generated DOCX by rendering it via LibreOffice."""
    
    def __init__(self, model_id: str | None = None):
        # We default to a vision-capable model if one isn't specified
        self.model_id = model_id or "qwen-vl-max"
        self.client = OpenAI(
            api_key=settings.recognizer_model_api_key,
            base_url=settings.provider_base_url,
            timeout=settings.recognizer_modelizer_model_timeout or 120.0
        )
        
    def test_docx(self, docx_path: Path, max_pages: int = 3) -> VisualTestResult:
        """Converts DOCX to PDF/Images using LibreOffice, then runs Vision QA."""
        if not docx_path.exists():
            raise FileNotFoundError(f"DOCX not found: {docx_path}")
            
        # Use a local temp directory to avoid Snap sandbox issues with /tmp
        local_tmp_base = Path.cwd() / ".visual_tmp"
        local_tmp_base.mkdir(exist_ok=True)
        
        with tempfile.TemporaryDirectory(dir=local_tmp_base) as tmpdir:
            # 1. Convert to PDF using LibreOffice
            logger.info(f"[agent:visual] Converting {docx_path.name} to PDF using LibreOffice...")
            try:
                # Use absolute paths for LibreOffice reliability
                abs_docx = docx_path.resolve()
                abs_tmp = Path(tmpdir).resolve()
                process = subprocess.run([
                    "libreoffice", "--headless", "--nologo", "--convert-to", "pdf", 
                    str(abs_docx), "--outdir", str(abs_tmp)
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                logger.error(f"LibreOffice conversion failed: {e.stderr.decode()}")
                raise RuntimeError("Failed to render DOCX with LibreOffice.")
            
            pdf_path = abs_tmp / f"{docx_path.stem}.pdf"
            if not pdf_path.exists():
                logger.error(f"LibreOffice stdout: {process.stdout.decode()}")
                logger.error(f"LibreOffice stderr: {process.stderr.decode()}")
                logger.error(f"Contents of tmpdir: {list(abs_tmp.iterdir())}")
                # Try to find any PDF in the directory
                pdfs = list(abs_tmp.glob("*.pdf"))
                if pdfs:
                    pdf_path = pdfs[0]
                    logger.info(f"Using found PDF: {pdf_path}")
                else:
                    raise FileNotFoundError(f"Failed to generate PDF: {pdf_path}")
                
            # 2. Convert PDF to Images using pdftoppm
            logger.info(f"[agent:visual] Converting PDF to images...")
            try:
                subprocess.run([
                    "pdftoppm", "-jpeg", "-r", "150", str(pdf_path), f"{abs_tmp}/page"
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                logger.error(f"pdftoppm failed: {e.stderr.decode()}")
                raise RuntimeError("Failed to extract images from PDF.")
            
            # 3. Gather images and prompt Vision LLM
            image_paths = sorted(abs_tmp.glob("page-*.jpg"))
            if not image_paths:
                raise FileNotFoundError("Failed to generate images from PDF.")
                
            prompt = (
                "Please act as a QA engineer. Review the following pages of a generated academic DOCX document. "
                "Check if the layout is correct (e.g., margins, columns, three-line tables, image rendering, headings, references). "
                "Identify any 'unreadable content' placeholders, corrupted layouts, overlapping text, or missing assets.\n\n"
                "Respond ONLY with a valid JSON object matching this schema:\n"
                + json.dumps(VisualTestResult.model_json_schema(), indent=2)
            )
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
            
            pages_to_analyze = image_paths[:max_pages]
            for img_path in pages_to_analyze:
                with open(img_path, "rb") as img_file:
                    b64_img = base64.b64encode(img_file.read()).decode('utf-8')
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_img}"
                        }
                    })
                    
            logger.info(f"[agent:visual] Analyzing {len(pages_to_analyze)} pages with vision model {self.model_id}...")
            
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            logger.info(f"[agent:visual] Vision LLM response: {result_text}")
            
            try:
                # Basic cleanup in case model wrapped JSON in markdown blocks
                if result_text.startswith("```json"):
                    result_text = result_text[7:-3].strip()
                elif result_text.startswith("```"):
                    result_text = result_text[3:-3].strip()
                    
                result_data = json.loads(result_text)
                return VisualTestResult.model_validate(result_data)
            except Exception as e:
                logger.error(f"[agent:visual] Failed to parse structured output: {e}\nRaw output: {result_text}")
                # Fallback return
                return VisualTestResult(
                    is_format_correct=False, 
                    issues_found=["Failed to parse LLM QA output."], 
                    confidence_score=0,
                    analysis_summary="Parsing error."
                )
