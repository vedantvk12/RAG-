import os
import re
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.future import select
from sqlalchemy import func

from app.schemas.rag import RAGQueryResponse, CitationValidation
from app.services.retrieval.retriever import HybridRetriever
from app.services.retrieval.reranker import reranker_service
from app.services.rag.context import build_context, GROUNDING_SYSTEM_PROMPT
from app.llm.openai_provider import OpenAILLMProvider
from app.llm.provider import ChatMessage
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import Document, DocumentChunk

logger = logging.getLogger(__name__)

def _format_size(size_bytes: Optional[int]) -> Optional[str]:
    if size_bytes is None:
        return None
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

async def get_org_document_registry(org_id: UUID) -> List[Dict[str, Any]]:
    """
    Fetches the organization's document registry with accurate metadata.
    If page_count or file size is missing, performs safe on-demand inspection from disk/chunks.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document)
            .where(Document.org_id == org_id)
            .order_by(Document.created_at.desc())
        )
        docs = result.scalars().all()
        registry = []
        needs_commit = False

        for d in docs:
            meta = dict(d.metadata_json or {})
            ext = os.path.splitext(d.filename)[1].lower()
            file_path = os.path.join(settings.UPLOAD_DIR, str(org_id), f"{d.id}{ext}")
            
            # Safe on-demand PDF inspection if page_count is missing
            if "page_count" not in meta:
                if ext == ".pdf" and os.path.exists(file_path):
                    try:
                        import fitz
                        with fitz.open(file_path) as pdf_doc:
                            meta["page_count"] = len(pdf_doc)
                            meta["total_pages"] = len(pdf_doc)
                    except Exception as e:
                        logger.warning(f"Could not read PDF {file_path}: {e}")
                else:
                    # Query max chunk page_number from DB
                    max_p_res = await db.execute(
                        select(func.max(DocumentChunk.page_number)).where(DocumentChunk.doc_id == d.id)
                    )
                    max_p = max_p_res.scalar()
                    if max_p is not None:
                        meta["page_count"] = max_p

            # Safe on-demand file size inspection
            if "file_size_bytes" not in meta and os.path.exists(file_path):
                meta["file_size_bytes"] = os.path.getsize(file_path)

            if meta != (d.metadata_json or {}):
                d.metadata_json = meta
                db.add(d)
                needs_commit = True

            size_bytes = meta.get("file_size_bytes")
            registry.append({
                "id": str(d.id),
                "filename": d.filename,
                "status": d.status,
                "page_count": meta.get("page_count"),
                "file_size_bytes": size_bytes,
                "file_size_formatted": _format_size(size_bytes),
                "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if d.created_at else "Unknown",
                "error_message": d.error_message
            })

        if needs_commit:
            try:
                await db.commit()
            except Exception:
                await db.rollback()

        return registry

class RAGGenerator:
    def __init__(self):
        self.llm_provider = OpenAILLMProvider(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS
        )

    async def generate_grounded_response(
        self, 
        query: str, 
        org_id: UUID, 
        top_k: int,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> RAGQueryResponse:
        # 1. Fetch organization document registry
        doc_registry = await get_org_document_registry(org_id)
        
        # 2. Retrieval
        hybrid_candidates = await HybridRetriever.search(
            query=query, 
            org_id=org_id, 
            top_k=settings.FINAL_TOP_K,
            conversation_history=conversation_history
        )
        
        # 3. Reranking (includes tenant isolation inside the reranker service)
        reranked_results = await reranker_service.rerank_results(
            query=query, 
            candidates=hybrid_candidates, 
            org_id=org_id, 
            top_k=top_k
        )
        
        # 4. Defensive Tenant Isolation Check
        for r in reranked_results:
            if r.org_id != org_id:
                logger.error(f"CRITICAL: Cross-tenant leakage detected! Chunk {r.chunk_id} does not belong to {org_id}.")
                raise Exception("Security Error: Cross-tenant data detected in RAG pipeline.")

        # 5. Abstention Check if neither documents nor chunks exist
        if not reranked_results and not doc_registry:
            return RAGQueryResponse(
                query=query,
                answer="The available documents do not contain enough information to answer this question.",
                sources=[],
                retrieval_metadata={
                    "hybrid_candidates": 0,
                    "reranked_results": 0,
                    "documents_in_registry": 0
                },
                citation_validation=CitationValidation(valid_citations=[], invalid_citations=[])
            )
            
        # 6. Build Context
        context_text, cited_sources = build_context(reranked_results, doc_registry)
        
        # 7. Build Prompt & LLM Generation (incorporating conversation history for pronoun resolution)
        messages = [
            ChatMessage(role="system", content=GROUNDING_SYSTEM_PROMPT)
        ]
        
        if conversation_history:
            for turn in conversation_history[-4:]: # include recent turns
                role = turn.get("role", "user")
                if role in ["user", "assistant"]:
                    messages.append(ChatMessage(role=role, content=turn.get("content", "")))
                    
        messages.append(ChatMessage(role="user", content=f"Evidence Context:\n{context_text}\n\nQuestion: {query}"))
        
        try:
            answer = await self.llm_provider.generate_response(messages)
            if not answer or not answer.strip():
                answer = "The available documents do not contain enough information to answer this question."
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            raise Exception("LLM Generation failed safely.") from e
            
        # 8. Citation Validation
        cited_ids_in_answer = set(re.findall(r"\[Source\s+(\d+)\]", answer))
        valid_ids = set([s.source_id for s in cited_sources])
        
        valid_citations = []
        invalid_citations = []
        for cid in cited_ids_in_answer:
            if cid in valid_ids:
                valid_citations.append(f"[Source {cid}]")
            else:
                invalid_citations.append(f"[Source {cid}]")
                
        # Only return sources that were ACTUALLY cited (and are valid)
        final_sources = [s for s in cited_sources if s.source_id in cited_ids_in_answer]
        
        return RAGQueryResponse(
            query=query,
            answer=answer,
            sources=final_sources,
            retrieval_metadata={
                "hybrid_candidates": len(hybrid_candidates),
                "reranked_results": len(reranked_results),
                "context_sources_provided": len(cited_sources),
                "documents_in_registry": len(doc_registry)
            },
            citation_validation=CitationValidation(
                valid_citations=valid_citations,
                invalid_citations=invalid_citations
            )
        )

rag_generator = RAGGenerator()
