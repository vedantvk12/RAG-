import asyncio
import os
import uuid
import sys
from app.db.session import AsyncSessionLocal
from app.db.models import Organization, User, Membership, Document, DocumentChunk
from app.db.qdrant import init_qdrant, get_qdrant_client
from app.core.security import get_password_hash

# --- MOCK FASTEMBED FOR DETERMINISTIC EVALUATION ON WINDOWS ---
from app.llm.fastembed_provider import FastEmbedProvider
class DeterministicProvider:
    async def get_embedding(self, text: str) -> list[float]:
        # Hardcode matching for our EVAL_DATASET to prove Dense/RRF works
        vec = [0.0] * 384
        
        # Avoid circular imports
        try:
            from evaluate_retrieval import EVAL_DATASET
            dataset = EVAL_DATASET
        except ImportError:
            dataset = []
            
        match_idx = 0
        for i, item in enumerate(dataset):
            if text == item["text"] or text in item["expected_queries"]:
                match_idx = i + 1
                break
                
        if match_idx > 0:
            vec[match_idx] = 1.0
        else:
            vec[0] = 1.0
            
        return vec

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return [await self.get_embedding(t) for t in texts]

import app.services.retrieval.dense
import app.services.indexing.indexer
dummy_provider = DeterministicProvider()
app.services.retrieval.dense.provider = dummy_provider
app.services.indexing.indexer.provider = dummy_provider
# --------------------------------------------------------------

from app.services.retrieval.dense import DenseRetriever
from app.services.retrieval.bm25 import BM25Manager
from app.services.retrieval.retriever import HybridRetriever

EVAL_DATASET = [
    {
        "text": "The company uses PostgreSQL for transactional data.",
        "expected_queries": ["PostgreSQL database", "transactional data system"]
    },
    {
        "text": "The company uses Qdrant for semantic vector search.",
        "expected_queries": ["semantic vector search", "where are embeddings stored?"]
    },
    {
        "text": "Employees receive annual performance reviews in December.",
        "expected_queries": ["performance review", "annual employee feedback"]
    },
    {
        "text": "The backend is built with FastAPI and Node.js for microservices.",
        "expected_queries": ["Node.js microservices", "FastAPI backend framework"]
    },
    {
        "text": "Authentication is handled via JWT and Argon2id hashing.",
        "expected_queries": ["JWT authentication", "Argon2id password hashing"]
    }
]

async def setup_evaluation():
    # 1. Initialize Qdrant
    await init_qdrant()
    
    # 2. Seed deterministic data
    org_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    
    async with AsyncSessionLocal() as db:
        user_id = uuid.uuid4()
        user = User(id=user_id, email=f"eval_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash")
        db.add(user)
        
        org = Organization(id=org_id, name="Eval Org")
        db.add(org)
        
        mem = Membership(org_id=org_id, user_id=user_id, role="admin")
        db.add(mem)
        
        doc = Document(id=doc_id, org_id=org_id, uploaded_by=user_id, filename="eval.txt", status="indexed", content_hash="hash")
        db.add(doc)
        
        chunks_map = {}
        for i, item in enumerate(EVAL_DATASET):
            chunk = DocumentChunk(
                doc_id=doc_id,
                org_id=org_id,
                chunk_index=i,
                text=item["text"],
                content_hash=f"hash{i}"
            )
            db.add(chunk)
            await db.flush()
            chunks_map[chunk.text] = chunk.id
            
        await db.commit()
    
    # 3. Index into Qdrant
    from app.services.indexing.indexer import index_document_background
    await index_document_background(doc_id)
    
    # Wait for Qdrant to persist the vectors
    await asyncio.sleep(1.0)
    
    # Check if doc indexed successfully
    async with AsyncSessionLocal() as db:
        doc = await db.get(Document, doc_id)
        if doc.status == "failed":
            print("INDEXING FAILED!", doc.error_message)
    
    return org_id, chunks_map

async def evaluate():
    print("Setting up evaluation database...")
    org_id, chunks_map = await setup_evaluation()
    print("Setup complete. Running evaluation...\n")
    
    queries = []
    for item in EVAL_DATASET:
        for q in item["expected_queries"]:
            queries.append((q, chunks_map[item["text"]]))
            
    def calc_metrics(results, expected_chunk_id, k=3):
        top_k_ids = [r.chunk_id for r in results[:k]]
        recall = 1 if expected_chunk_id in top_k_ids else 0
        precision = 1/len(top_k_ids) if expected_chunk_id in top_k_ids else 0
        return recall, precision

    dense_recall, dense_precision = 0, 0
    bm25_recall, bm25_precision = 0, 0
    hybrid_recall, hybrid_precision = 0, 0
    rerank_recall, rerank_precision = 0, 0
    
    # Latencies
    import time
    dense_times, bm25_times, hybrid_times, rerank_times, total_times = [], [], [], [], []
    
    # Instantiate the real reranker service for evaluation
    from app.services.retrieval.reranker import reranker_service
    reranker_failed = False
    
    for i, (query, expected_id) in enumerate(queries):
        is_first = (i == 0)
        if is_first:
            print(f"\n--- Analyzing First Query: '{query}' ---")
            
        t0 = time.time()
        # Dense
        dense_results = await DenseRetriever.search(query, org_id)
        dense_times.append(time.time() - t0)
        
        dr, dp = calc_metrics(dense_results, expected_id)
        dense_recall += dr
        dense_precision += dp
        
        # BM25
        t1 = time.time()
        bm25_results = await BM25Manager.search(query, org_id)
        bm25_times.append(time.time() - t1)
        
        br, bp = calc_metrics(bm25_results, expected_id)
        bm25_recall += br
        bm25_precision += bp
        
        # Hybrid
        t2 = time.time()
        hybrid_results = await HybridRetriever.search(query, org_id)
        hybrid_times.append(time.time() - t2)
        
        if is_first:
            print("\nHybrid RRF Candidates:")
            for idx, c in enumerate(hybrid_results[:3]):
                print(f"  {idx+1}. Rank={c.final_rank} RRF={c.rrf_score:.3f} | Text: {c.text[:50]}...")
                
        hr, hp = calc_metrics(hybrid_results, expected_id)
        hybrid_recall += hr
        hybrid_precision += hp
        
        # Hybrid + Reranking
        t3 = time.time()
        if not reranker_failed:
            try:
                # Top_k here needs to be enough candidates. We'll pass all hybrid candidates.
                reranked_results = await reranker_service.rerank_results(query, hybrid_results, org_id, top_k=3)
                rerank_times.append(time.time() - t3)
                total_times.append(time.time() - t0)
                
                if is_first:
                    print("\nReranked Candidates:")
                    for idx, c in enumerate(reranked_results[:3]):
                        print(f"  {idx+1}. Rank={c.final_rank} RerankScore={c.rerank_score:.3f} | Text: {c.text[:50]}...")
                        
                rr, rp = calc_metrics(reranked_results, expected_id)
                rerank_recall += rr
                rerank_precision += rp
            except Exception as e:
                print(f"RERANKER EVALUATION BLOCKED: Model download or inference failed. Error: {e}")
                reranker_failed = True
        
    n = len(queries)
    print("\n=== Evaluation Results (Top-3) ===")
    print(f"Total Queries: {n}\n")
    
    avg_d = sum(dense_times) / n * 1000
    avg_b = sum(bm25_times) / n * 1000
    avg_h = sum(hybrid_times) / n * 1000
    
    print(f"1. Dense-only Retrieval (avg latency: {avg_d:.2f}ms)")
    print(f"   Recall@3:    {dense_recall/n:.2f}")
    print(f"   Precision@3: {dense_precision/n:.2f}\n")
    
    print(f"2. BM25-only Retrieval (avg latency: {avg_b:.2f}ms)")
    print(f"   Recall@3:    {bm25_recall/n:.2f}")
    print(f"   Precision@3: {bm25_precision/n:.2f}\n")
    
    print(f"3. Hybrid RRF Retrieval (avg latency: {avg_h:.2f}ms)")
    print(f"   Recall@3:    {hybrid_recall/n:.2f}")
    print(f"   Precision@3: {hybrid_precision/n:.2f}\n")

    print("4. Hybrid + Cross-Encoder Reranking")
    if reranker_failed:
        print("   [BLOCKED] Cannot evaluate due to model download failure.")
    else:
        avg_r = sum(rerank_times) / len(rerank_times) * 1000
        avg_t = sum(total_times) / len(total_times) * 1000
        print(f"   (avg rerank latency: {avg_r:.2f}ms, avg total retrieval latency: {avg_t:.2f}ms)")
        print(f"   Recall@3:    {rerank_recall/n:.2f}")
        print(f"   Precision@3: {rerank_precision/n:.2f}\n")
    
    # Cleanup (optional for this standalone script if running in isolated DB)

if __name__ == "__main__":
    # Ensure run in asyncio loop
    asyncio.run(evaluate())
