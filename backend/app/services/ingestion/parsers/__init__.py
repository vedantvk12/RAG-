from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, BinaryIO
from app.services.ingestion.chunking import ExtractedChunk

class ParsedDocument:
    def __init__(self, chunks: List[ExtractedChunk], metadata: Optional[Dict[str, Any]] = None):
        self.chunks = chunks
        self.metadata = metadata or {}

class DocumentParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, original_filename: str) -> ParsedDocument:
        """
        Parse the given file and return a ParsedDocument containing chunks.
        """
        pass
