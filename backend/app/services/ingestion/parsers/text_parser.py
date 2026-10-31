from app.services.ingestion.parsers import DocumentParser, ParsedDocument
from app.services.ingestion.chunking import chunk_text, DocumentChunkMetadata

class TextParser(DocumentParser):
    def parse(self, file_path: str, original_filename: str) -> ParsedDocument:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            
        metadata = DocumentChunkMetadata(
            page_number=None,
            section=None,
            source_type="text"
        )
        chunks = chunk_text(text, metadata)
        
        return ParsedDocument(chunks=chunks)
