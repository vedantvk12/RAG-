import fitz
from app.services.ingestion.parsers import DocumentParser, ParsedDocument
from app.services.ingestion.chunking import chunk_text, DocumentChunkMetadata, ExtractedChunk

class PDFParser(DocumentParser):
    def parse(self, file_path: str, original_filename: str) -> ParsedDocument:
        chunks = []
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            if not text.strip():
                continue
                
            metadata = DocumentChunkMetadata(
                page_number=page_num + 1,
                section=None,
                source_type="text"
            )
            
            # Use structure-aware chunker per page
            page_chunks = chunk_text(text, metadata)
            chunks.extend(page_chunks)
            
            # Best-effort table extraction
            tables = page.find_tables()
            if tables:
                for table in tables:
                    # Convert to string (CSV-like)
                    table_df = table.to_pandas()
                    if not table_df.empty:
                        table_text = table_df.to_csv(index=False)
                        table_metadata = DocumentChunkMetadata(
                            page_number=page_num + 1,
                            section="Table",
                            source_type="table"
                        )
                        chunks.append(ExtractedChunk(text=table_text, metadata=table_metadata))
                        
        page_count = len(doc)
        metadata = {
            "page_count": page_count,
            "total_pages": page_count,
            "format": "PDF",
            "title": doc.metadata.get("title") or None,
            "author": doc.metadata.get("author") or None
        }
        doc.close()
        return ParsedDocument(chunks=chunks, metadata=metadata)
