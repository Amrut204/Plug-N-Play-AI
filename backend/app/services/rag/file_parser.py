import io
import csv
import json
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class FileParserService:
    """
    Parses various document file formats into clean text representation for RAG chunking.
    Supports: PDF (.pdf), CSV (.csv), Markdown (.md), Plain Text (.txt), JSON (.json).
    """

    @classmethod
    async def extract_text_from_file(cls, filename: str, content_bytes: bytes) -> Tuple[str, str]:
        """
        Returns (extracted_title, clean_text_content)
        """
        name_lower = filename.lower()
        title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

        if name_lower.endswith(".pdf"):
            return title, cls._parse_pdf(content_bytes)
        elif name_lower.endswith(".csv"):
            return title, cls._parse_csv(content_bytes)
        elif name_lower.endswith(".json"):
            return title, cls._parse_json(content_bytes)
        else:
            # Default text / markdown decoding
            try:
                text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = content_bytes.decode("latin-1", errors="ignore")
            return title, text

    @classmethod
    def _parse_pdf(cls, content_bytes: bytes) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt and txt.strip():
                    pages_text.append(f"[Page {i+1}]\n{txt.strip()}")
            return "\n\n".join(pages_text)
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            raise ValueError(f"Could not extract text from PDF: {str(e)}")

    @classmethod
    def _parse_csv(cls, content_bytes: bytes) -> str:
        try:
            text = content_bytes.decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            rows_formatted = []
            for i, row in enumerate(reader):
                if i >= 500:  # Cap at 500 rows for RAG document chunking
                    break
                row_str = ", ".join([f"{k}: {v}" for k, v in row.items() if v and v.strip()])
                rows_formatted.append(f"Row {i+1}: {row_str}")
            return "\n".join(rows_formatted)
        except Exception as e:
            logger.error(f"Failed to parse CSV: {e}")
            raise ValueError(f"Could not extract text from CSV: {str(e)}")

    @classmethod
    def _parse_json(cls, content_bytes: bytes) -> str:
        try:
            text = content_bytes.decode("utf-8", errors="ignore")
            data = json.loads(text)
            if isinstance(data, list):
                return "\n\n".join([json.dumps(item, indent=2) for item in data[:200]])
            elif isinstance(data, dict):
                return json.dumps(data, indent=2)
            return str(data)
        except Exception as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Could not extract text from JSON: {str(e)}")
