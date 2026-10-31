import os
import shutil
import hashlib
from uuid import UUID
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User, Organization, Membership, Document
from app.schemas.document import DocumentResponse, DocumentWithChunksResponse, DocumentStatusResponse
from app.api.deps import get_current_user, get_current_org_member
from app.services.ingestion.processor import process_document_background

router = APIRouter()

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx"}

def validate_file(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
        )
    return ext

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    org_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Upload a document for ingestion.
    """
    ext = validate_file(file.filename)
    
    # Read file to check size and compute hash
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 2GB allowed.")
        
    content_hash = hashlib.sha256(content).hexdigest()
    
    # Check for duplicates in the same org
    dup_result = await db.execute(
        select(Document).where(Document.org_id == org_id, Document.content_hash == content_hash)
    )
    duplicate = dup_result.scalars().first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Document with same content already exists in this organization.")

    # Create safe storage directory
    org_dir = os.path.join(settings.UPLOAD_DIR, str(org_id))
    os.makedirs(org_dir, exist_ok=True)
    
    # Pre-create Document DB record
    doc = Document(
        org_id=org_id,
        uploaded_by=membership.user_id,
        filename=file.filename,
        content_hash=content_hash,
        status="processing"
    )
    db.add(doc)
    await db.flush()  # To get doc.id

    # Safe filename using doc.id UUID
    safe_filename = f"{doc.id}{ext}"
    file_path = os.path.join(org_dir, safe_filename)
    
    with open(file_path, "wb") as f:
        f.write(content)
        
    await db.commit()
    await db.refresh(doc)
    
    # Queue background task
    background_tasks.add_task(process_document_background, doc.id, file_path, file.filename)
    
    return doc

@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    org_id: UUID,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all documents in the organization.
    """
    result = await db.execute(select(Document).where(Document.org_id == org_id))
    return result.scalars().all()

@router.get("/{doc_id}", response_model=DocumentWithChunksResponse)
async def get_document(
    org_id: UUID,
    doc_id: UUID,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a specific document by ID.
    """
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Document)
        .where(Document.id == doc_id, Document.org_id == org_id)
        .options(selectinload(Document.chunks))
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in this organization")
    return doc

@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    org_id: UUID,
    doc_id: UUID,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get just the processing status.
    """
    result = await db.execute(
        select(Document.status, Document.error_message)
        .where(Document.id == doc_id, Document.org_id == org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found in this organization")
    return {"status": row.status, "error_message": row.error_message}

@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    org_id: UUID,
    doc_id: UUID,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a document and its chunks.
    """
    # Requires admin OR uploader? The prompt says "delete authorized documents".
    # For now, let's allow uploader or admin.
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.org_id == org_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in this organization")

    if doc.uploaded_by != membership.user_id and membership.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")

    # DB Delete (cascade will remove chunks)
    await db.delete(doc)
    await db.commit()

    # Invalidate BM25 Cache
    from app.services.retrieval.bm25 import BM25Manager
    BM25Manager.invalidate_cache(org_id)

    # Filesystem delete
    ext = validate_file(doc.filename)
    safe_filename = f"{doc.id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, str(org_id), safe_filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return None

from app.services.indexing.indexer import index_document_background

@router.post("/{doc_id}/index", status_code=status.HTTP_202_ACCEPTED)
async def index_document(
    org_id: UUID,
    doc_id: UUID,
    background_tasks: BackgroundTasks,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Trigger indexing for a ready document.
    """
    # Verify document ownership/authorization
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.org_id == org_id)
    )
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found in this organization")

    if doc.status not in ["ready", "failed", "indexed"]:
        raise HTTPException(status_code=400, detail=f"Document cannot be indexed from state: {doc.status}")

    # Start indexing
    background_tasks.add_task(index_document_background, doc.id)
    return {"status": "indexing_started"}

@router.get("/{doc_id}/index-status", response_model=DocumentStatusResponse)
async def get_index_status(
    org_id: UUID,
    doc_id: UUID,
    membership: Membership = Depends(get_current_org_member),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get the indexing status. Reuse the document status endpoint for now as it contains 'status' and 'error_message'.
    """
    result = await db.execute(
        select(Document.status, Document.error_message)
        .where(Document.id == doc_id, Document.org_id == org_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found in this organization")
    return {"status": row.status, "error_message": row.error_message}
