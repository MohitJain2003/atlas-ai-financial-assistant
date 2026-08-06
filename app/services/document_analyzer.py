"""
Document & Voice Analyzers — PDF, DOCX, XLSX extraction and AI analysis.
Voice transcription via Groq Whisper.
"""
import os
import logging
from typing import Dict, Any
from PyPDF2 import PdfReader
import docx

from app.ai.models import model_chain

logger = logging.getLogger(__name__)


class DocumentAnalyzerService:
    """Service to extract text and analyze financial documents."""

    @staticmethod
    async def extract_text(file_path: str, file_type: str) -> str:
        """Extract plain text from PDF, DOCX, XLSX, or TXT files."""
        try:
            if file_type == "pdf":
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                return text.strip()

            elif file_type in ("docx", "doc"):
                doc = docx.Document(file_path)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                # Also extract tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                        if row_text:
                            paragraphs.append(row_text)
                return "\n".join(paragraphs).strip()

            elif file_type in ("xlsx", "xls"):
                return DocumentAnalyzerService._extract_xlsx(file_path)

            elif file_type == "txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read().strip()

        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")

        return ""

    @staticmethod
    def _extract_xlsx(file_path: str) -> str:
        """Extract data from Excel spreadsheet as structured text."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            all_text = []

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                all_text.append(f"=== Sheet: {sheet_name} ===")
                rows_extracted = 0
                for row in ws.iter_rows(max_row=100, values_only=True):
                    if any(cell is not None for cell in row):
                        row_text = " | ".join(str(c) if c is not None else "" for c in row)
                        all_text.append(row_text)
                        rows_extracted += 1
                        if rows_extracted >= 100:
                            all_text.append("... [truncated to first 100 rows per sheet]")
                            break

            wb.close()
            return "\n".join(all_text)
        except Exception as e:
            logger.error(f"XLSX extraction error: {e}")
            return ""

    @staticmethod
    async def analyze_document(user_prompt: str, document_text: str,
                                filename: str = "document") -> str:
        """Analyze financial document text using AI with context-aware prompting."""
        if not document_text:
            return "Could not extract readable text from the uploaded document. It may be scanned/image-based or password protected."

        # Determine document type for better prompting
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        doc_type_hint = {
            "pdf": "financial PDF",
            "docx": "Word document",
            "doc": "Word document",
            "xlsx": "Excel spreadsheet",
            "xls": "Excel spreadsheet",
            "txt": "text file",
        }.get(ext, "financial document")

        # Truncate if too long
        truncated_text = document_text[:15000]
        if len(document_text) > 15000:
            truncated_text += "\n\n[... Document truncated — showing first 15,000 characters ...]"

        system_instruction = (
            f"You are Atlas, an expert financial analyst. The user has uploaded a {doc_type_hint}. "
            "Analyze it and answer their question concisely. Focus on: key financial KPIs, risks, "
            "revenue trends, profitability, strategic highlights, and actionable takeaways. "
            "Use bullet points. Bold key numbers. If it's a spreadsheet, identify trends and anomalies."
        )

        user_message = f"User Request: {user_prompt}\n\nDocument Content:\n{truncated_text}"

        return await model_chain.generate(system_instruction, user_message)

    @staticmethod
    async def compare_documents(prompt: str, doc1_text: str, doc2_text: str,
                                 doc1_name: str = "Document 1",
                                 doc2_name: str = "Document 2") -> str:
        """Compare two financial documents — e.g. two annual reports."""
        system_instruction = (
            "You are Atlas, an expert financial analyst. Compare the two documents below and answer "
            "the user's question. Focus on key differences in revenue, profitability, risk factors, "
            "strategy, and outlook. Format as a structured comparison."
        )

        combined = (
            f"=== {doc1_name} ===\n{doc1_text[:7000]}\n\n"
            f"=== {doc2_name} ===\n{doc2_text[:7000]}"
        )
        user_message = f"User Request: {prompt}\n\nDocuments:\n{combined}"

        return await model_chain.generate(system_instruction, user_message)


class VoiceService:
    """Service for voice message transcription."""

    @staticmethod
    async def process_voice_message(file_path: str) -> str:
        """Transcribe voice message audio to text via Groq Whisper."""
        transcription = await model_chain.transcribe_voice(file_path)
        if not transcription:
            return "Sorry, I couldn't transcribe your voice message. Please try again or type your question."
        return transcription
