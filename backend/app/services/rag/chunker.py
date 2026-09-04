import re
from typing import List, Dict, Any


class TextChunker:
    """
    Splits unstructured documents into semantic paragraphs / sliding-window chunks.
    """

    @classmethod
    def chunk_text(
        cls, 
        text: str, 
        chunk_size: int = 500, 
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Chunks text on paragraph or sentence boundaries.
        """
        text = text.strip()
        if not text:
            return []

        # Split by double newlines or headers
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)
            if current_len + para_len > chunk_size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # Retain overlap if desired
                if chunk_overlap > 0 and len(current_chunk) > 1:
                    current_chunk = [current_chunk[-1], para]
                    current_len = len(current_chunk[0]) + para_len
                else:
                    current_chunk = [para]
                    current_len = para_len
            else:
                current_chunk.append(para)
                current_len += para_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks
