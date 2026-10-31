from typing import List, Optional
from pydantic import BaseModel
import re

from app.core.config import settings

class DocumentChunkMetadata(BaseModel):
    page_number: Optional[int] = None
    section: Optional[str] = None
    source_type: str = "text"

class ExtractedChunk(BaseModel):
    text: str
    metadata: DocumentChunkMetadata

def chunk_text(
    text: str,
    metadata: DocumentChunkMetadata,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP
) -> List[ExtractedChunk]:
    """
    Structure-aware chunking. Splits on paragraphs first, then tries to pack them up to chunk_size.
    Preserves overlap.
    """
    if not text or not isinstance(text, str) or not text.strip():
        return []

    # Split by paragraphs (double newline)
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk_text = ""
    
    for p in paragraphs:
        # If a single paragraph is longer than chunk_size, split by sentences or chunks
        if len(p) > chunk_size:
            if current_chunk_text:
                chunks.append(ExtractedChunk(text=current_chunk_text, metadata=metadata))
                current_chunk_text = ""
            # Split long paragraph
            for i in range(0, len(p), chunk_size - chunk_overlap):
                slice_text = p[i:i + chunk_size].strip()
                if slice_text:
                    chunks.append(ExtractedChunk(text=slice_text, metadata=metadata))
            continue

        if not current_chunk_text:
            current_chunk_text = p
        elif len(current_chunk_text) + len(p) + 2 <= chunk_size:
            current_chunk_text += "\n\n" + p
        else:
            chunks.append(ExtractedChunk(text=current_chunk_text, metadata=metadata))
            current_chunk_text = p
            
    if current_chunk_text:
        chunks.append(ExtractedChunk(text=current_chunk_text, metadata=metadata))
        
    return chunks
