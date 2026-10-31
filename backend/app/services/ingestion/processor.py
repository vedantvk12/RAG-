import hashlib
from uuid import UUID
import traceback

from app.db.session import AsyncSessionLocal
from app.db.models import Document, DocumentChunk
from app.services.ingestion.parsers.pdf_parser import PDFParser
from app.services.ingestion.parsers.docx_parser import DOCXParser
from app.services.ingestion.parsers.text_parser import TextParser
from app.services.ingestion.parsers.spreadsheet_parser import SpreadsheetParser

def get_parser_for_filename(filename: str):
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        return PDFParser()
    elif ext == 'docx':
        return DOCXParser()
    elif ext in ['txt', 'md']:
        return TextParser()
    elif ext in ['csv', 'xlsx']:
        return SpreadsheetParser()
    raise ValueError(f"Unsupported file extension: {ext}")

async def process_document_background(doc_id: UUID, file_path: str, original_filename: str):
    """
    Background task to parse a document and store chunks.
    Uses its own DB session so it doesn't conflict with the original request.
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch document
            doc = await db.get(Document, doc_id)
            if not doc:
                return  # If document was deleted before processing started

            # 2. Parse
            parser = get_parser_for_filename(original_filename)
            parsed_doc = parser.parse(file_path, original_filename)

            # 3. Create Chunks
            if not parsed_doc.chunks:
                raise ValueError("No text could be extracted from this document. It may be a scanned image or an empty file.")

            for idx, chunk in enumerate(parsed_doc.chunks):
                # Hash content
                content_hash = hashlib.sha256(chunk.text.encode('utf-8')).hexdigest()
                
                db_chunk = DocumentChunk(
                    doc_id=doc.id,
                    org_id=doc.org_id,
                    chunk_index=idx,
                    text=chunk.text,
                    content_hash=content_hash,
                    page_number=chunk.metadata.page_number,
                    section=chunk.metadata.section,
                    source_type=chunk.metadata.source_type
                )
                db.add(db_chunk)

            # 4. Update metadata and status
            import os
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
            meta = {
                **(doc.metadata_json or {}),
                **(parsed_doc.metadata or {}),
                "file_size_bytes": file_size,
                "chunk_count": len(parsed_doc.chunks)
            }
            doc.metadata_json = meta
            doc.status = "ready"
            db.add(doc)
            await db.commit()

            # 5. Automatically index into Qdrant & BM25
            from app.services.indexing.indexer import index_document_background
            await index_document_background(doc.id)

        except Exception as e:
            await db.rollback()
            # Try to update document status to failed
            try:
                doc = await db.get(Document, doc_id)
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(e)
                    db.add(doc)
                    await db.commit()
            except Exception as inner_e:
                await db.rollback()
                # Log this somewhere if possible
                pass
