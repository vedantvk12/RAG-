import asyncio
import re
import logging
from typing import List, Optional, Any, Dict
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy import func

from app.schemas.retrieval import RetrievalResult
from app.services.retrieval.dense import DenseRetriever
from app.services.retrieval.bm25 import BM25Manager
from app.services.retrieval.fusion import ReciprocalRankFusion
from app.db.session import AsyncSessionLocal
from app.db.models import Document, DocumentChunk

logger = logging.getLogger(__name__)

class HybridRetriever:
    @classmethod
    async def _resolve_target_document(
        cls, 
        query: str, 
        org_id: UUID, 
        db: Any,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Document]:
        """
        Resolves the intended document from the query text, conversation history, or defaults to the latest PDF/document.
        Supports:
        - Exact filename or stem match
        - Multi-word keyword matching against filename stems (>= 4 chars)
        - Ordinal references ("first PDF", "second file", "1st document", etc.)
        - Conversational context / history resolution
        - Fallback to latest uploaded PDF / document
        """
        all_docs = (await db.execute(
            select(Document).where(Document.org_id == org_id, Document.status == "indexed").order_by(Document.created_at.desc())
        )).scalars().all()
        
        if not all_docs:
            return None

        query_lower = query.lower()
        
        # 1. Check for exact filename or stem match in query
        for doc in all_docs:
            if not doc.filename:
                continue
            fname_lower = doc.filename.lower()
            stem = fname_lower.rsplit('.', 1)[0]
            if fname_lower in query_lower or stem in query_lower:
                return doc
                
        # 2. Check for ordinal references (e.g. "first pdf", "second document", "1st pdf", "2nd file")
        # In chronological order:
        chronological_docs = list(reversed(all_docs))
        ordinal_map = {
            "first": 0, "1st": 0, "one": 0,
            "second": 1, "2nd": 1, "two": 1,
            "third": 2, "3rd": 2, "three": 2,
            "fourth": 3, "4th": 3, "four": 3,
            "fifth": 4, "5th": 4, "five": 4
        }
        for ord_word, idx in ordinal_map.items():
            if re.search(rf'\b{ord_word}\s+(pdf|file|document|paper)\b', query_lower):
                pdf_docs = [d for d in chronological_docs if d.filename and d.filename.lower().endswith('.pdf')]
                target_list = pdf_docs if pdf_docs else chronological_docs
                if idx < len(target_list):
                    return target_list[idx]

        # 3. Check for keyword stem matches (tokens >= 4 chars, excluding generic stopwords)
        stopwords = {"what", "when", "where", "which", "about", "from", "with", "this", "that", "these", "those", "have", "been", "file", "document", "paper", "pages", "page", "give", "tell", "explain", "summarize", "points", "main", "does", "could", "would", "should"}
        query_words = set(re.findall(r'[a-zA-Z0-9]+', query_lower)) - stopwords
        
        best_match = None
        max_overlap = 0
        for doc in all_docs:
            if not doc.filename:
                continue
            doc_tokens = set(re.findall(r'[a-zA-Z0-9]+', doc.filename.lower())) - stopwords
            overlap = len(query_words.intersection(doc_tokens))
            if overlap > max_overlap and overlap >= 2:
                max_overlap = overlap
                best_match = doc
                
        if best_match:
            return best_match

        # 4. Check conversation history for prior document references
        if conversation_history:
            for turn in reversed(conversation_history):
                content = str(turn.get("content", "")).lower()
                for doc in all_docs:
                    if doc.filename and (doc.filename.lower() in content or doc.filename.lower().rsplit('.', 1)[0] in content):
                        return doc

        # 5. Fallback: If user mentions PDF/document or generic "this/the", default to latest PDF
        is_pdf_ref = bool(re.search(r'\b(pdf|paper|article|manuscript|document|file|this|it)\b', query_lower))
        if is_pdf_ref:
            for doc in all_docs:
                if doc.filename and doc.filename.lower().endswith('.pdf'):
                    return doc
                    
        return all_docs[0]

    @classmethod
    async def _get_targeted_page_chunks(
        cls, 
        query: str, 
        org_id: UUID,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[RetrievalResult]:
        """
        If the query explicitly asks for a specific page (e.g., 'page 3', 'page 5', 'last page'),
        fetch chunks from that exact page directly.
        """
        match = re.search(r'\bpage\s*(\d+)\b', query, re.IGNORECASE)
        is_last_page = bool(re.search(r'\b(last|final|ending)\s+page\b', query, re.IGNORECASE))
        
        if not match and not is_last_page:
            return []
            
        async with AsyncSessionLocal() as db:
            target_doc = await cls._resolve_target_document(query, org_id, db, conversation_history)
            if not target_doc:
                return []
                
            if match:
                target_page = int(match.group(1))
                chunk_query = select(DocumentChunk).where(
                    DocumentChunk.org_id == org_id,
                    DocumentChunk.doc_id == target_doc.id,
                    DocumentChunk.page_number == target_page
                ).order_by(DocumentChunk.chunk_index)
            else:
                max_p_res = await db.execute(
                    select(func.max(DocumentChunk.page_number)).where(
                        DocumentChunk.org_id == org_id,
                        DocumentChunk.doc_id == target_doc.id
                    )
                )
                max_page = max_p_res.scalar()
                if not max_page:
                    return []
                chunk_query = select(DocumentChunk).where(
                    DocumentChunk.org_id == org_id,
                    DocumentChunk.doc_id == target_doc.id,
                    DocumentChunk.page_number == max_page
                ).order_by(DocumentChunk.chunk_index)
                
            chunks = (await db.execute(chunk_query)).scalars().all()
            results = []
            for i, c in enumerate(chunks, start=1):
                results.append(
                    RetrievalResult(
                        chunk_id=c.id,
                        document_id=c.doc_id,
                        org_id=c.org_id,
                        text=c.text,
                        filename=target_doc.filename,
                        page_number=c.page_number,
                        section=c.section,
                        source_type=c.source_type,
                        chunk_index=c.chunk_index,
                        dense_score=1.0,
                        bm25_score=1.0,
                        rerank_score=1.0,
                        final_rank=i
                    )
                )
            return results

    @classmethod
    async def _get_document_overview_chunks(
        cls, 
        query: str, 
        org_id: UUID,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[RetrievalResult]:
        """
        If the user asks to summarize a PDF or ask for methodology, findings, or conclusion,
        retrieve introductory, middle, and concluding chunks across the document.
        """
        if not re.search(r'\b(summarize|summary|overview|findings|methodology|conclusion|abstract|main points|key points|important points|limitations|gaps)\b', query, re.IGNORECASE):
            return []
            
        async with AsyncSessionLocal() as db:
            target_doc = await cls._resolve_target_document(query, org_id, db, conversation_history)
            if not target_doc:
                return []
                
            all_chunks = (await db.execute(
                select(DocumentChunk).where(
                    DocumentChunk.org_id == org_id,
                    DocumentChunk.doc_id == target_doc.id
                ).order_by(DocumentChunk.chunk_index.asc())
            )).scalars().all()
            
            if not all_chunks:
                return []
                
            # Pick representative chunks across beginning, middle, and end
            selected = []
            if len(all_chunks) <= 6:
                selected = all_chunks
            else:
                first_2 = all_chunks[:2]
                middle_idx = len(all_chunks) // 2
                mid_2 = all_chunks[middle_idx:middle_idx+2]
                last_2 = all_chunks[-2:]
                seen = set()
                for c in first_2 + mid_2 + last_2:
                    if c.id not in seen:
                        seen.add(c.id)
                        selected.append(c)
                    
            results = []
            for i, c in enumerate(selected, start=1):
                results.append(
                    RetrievalResult(
                        chunk_id=c.id,
                        document_id=c.doc_id,
                        org_id=c.org_id,
                        text=c.text,
                        filename=target_doc.filename,
                        page_number=c.page_number,
                        section=c.section,
                        source_type=c.source_type,
                        chunk_index=c.chunk_index,
                        dense_score=0.95,
                        bm25_score=0.95,
                        rerank_score=0.95,
                        final_rank=i
                    )
                )
            return results

    @classmethod
    async def search(
        cls, 
        query: str, 
        org_id: UUID, 
        top_k: int = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[RetrievalResult]:
        """
        Executes a hybrid search combining Dense and BM25 using RRF, with page-targeted awareness.
        Strictly enforces tenant isolation via org_id.
        """
        if not query or not isinstance(query, str) or not query.strip():
            return []
            
        # Execute searches concurrently
        dense_task = asyncio.create_task(DenseRetriever.search(query, org_id))
        bm25_task = asyncio.create_task(BM25Manager.search(query, org_id))
        page_task = asyncio.create_task(cls._get_targeted_page_chunks(query, org_id, conversation_history))
        overview_task = asyncio.create_task(cls._get_document_overview_chunks(query, org_id, conversation_history))
        
        dense_results, bm25_results, page_results, overview_results = await asyncio.gather(
            dense_task, bm25_task, page_task, overview_task
        )
        
        # Fuse dense and bm25 results
        fused = ReciprocalRankFusion.fuse(dense_results, bm25_results, top_k=top_k)
        
        # Prepend any targeted page results or overview results while avoiding duplicates
        seen_chunks = {r.chunk_id for r in fused}
        injected = []
        for r in page_results + overview_results:
            if r.chunk_id not in seen_chunks:
                seen_chunks.add(r.chunk_id)
                injected.append(r)
                
        # Targeted page results are top priority
        return page_results + [r for r in injected if r not in page_results] + [r for r in fused if r.chunk_id not in {p.chunk_id for p in page_results}]
