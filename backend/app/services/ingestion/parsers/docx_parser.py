import docx
from app.services.ingestion.parsers import DocumentParser, ParsedDocument
from app.services.ingestion.chunking import chunk_text, DocumentChunkMetadata, ExtractedChunk

class DOCXParser(DocumentParser):
    def parse(self, file_path: str, original_filename: str) -> ParsedDocument:
        doc = docx.Document(file_path)
        chunks = []
        
        full_text = []
        current_section = None
        
        for para in doc.paragraphs:
            if para.style.name.startswith('Heading'):
                current_section = para.text.strip()
            
            text = para.text.strip()
            if text:
                full_text.append(text)
                
        # To preserve document structure better, we can chunk everything as one large text
        # for a simple DOCX parsing, or chunk per section if we split by sections.
        # For this version, we will chunk the full document text, but if we wanted to be more precise,
        # we would chunk on sections. Let's just chunk the full text for simplicity while preserving basic boundaries.
        text_content = "\n\n".join(full_text)
        metadata = DocumentChunkMetadata(
            page_number=None,
            section=current_section,
            source_type="text"
        )
        chunks.extend(chunk_text(text_content, metadata))
        
        # Tables
        for table in doc.tables:
            table_data = []
            for row in table.rows:
                row_data = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
                table_data.append(" | ".join(row_data))
                
            table_text = "\n".join(table_data)
            table_metadata = DocumentChunkMetadata(
                page_number=None,
                section="Table",
                source_type="table"
            )
            chunks.append(ExtractedChunk(text=table_text, metadata=table_metadata))
            
        return ParsedDocument(chunks=chunks)
