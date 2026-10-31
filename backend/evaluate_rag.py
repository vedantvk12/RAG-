import asyncio
import os
import sys
import time

# Ensure correct import paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from evaluate_retrieval import setup_evaluation, EVAL_DATASET
from app.services.rag.generator import rag_generator
from app.services.rag.orchestrator import agentic_orchestrator
from app.services.decisions.engine import decision_engine
from app.core.config import settings
import traceback

async def evaluate():
    print("Checking Qdrant availability...")
    try:
        import httpx
        httpx.get(settings.QDRANT_URL, timeout=1.0)
        qdrant_status = "A. Real Docker Qdrant"
    except Exception:
        settings.QDRANT_URL = ":memory:"
        qdrant_status = "B. In-memory evaluation fallback"
        
    print(f"EVALUATION QDRANT STATUS: {qdrant_status}")
    print("NOTE: In-memory fallback is for evaluation only and does NOT represent production-Qdrant verification.")
    
    print("Setting up RAG evaluation database...")
    org_id, chunks_map = await setup_evaluation()
    print("Setup complete. Running RAG evaluation...\n")
    
    if not settings.LLM_API_KEY:
        print("REAL PROVIDER VERIFICATION BLOCKED")
        print("Reason: LLM_API_KEY is not configured.")
        return

    EVAL_DECISION_DATASET = [
        "Compare the backend framework to the database used.",
        "Recommend the best component to update for performance.",
        "What are the risks of using this database?",
        "Create a decision matrix evaluating the backend framework and the database.",
        "What is the cafeteria's famous cookie recipe?" # Should abstain
    ]
    
    queries = []
    for item in EVAL_DATASET:
        queries.append(item["expected_queries"][0]) # Just take the first one to save time/cost
        
    # queries.extend(complex_queries)
    # limit for speed during eval test
    queries = queries[:1]
            
    results_deterministic = {"success": 0, "abstain": 0, "total_latency": 0, "llm_calls": len(queries)}
    results_agentic = {"success": 0, "abstain": 0, "total_latency": 0, "llm_calls": 0, "retrieval_queries": 0, "total_iterations": 0}
    results_decision = {"success": 0, "abstain": 0, "total_latency": 0, "llm_calls": 0, "retrieval_queries": 0}
    
    # Needs a valid user_id for Agentic RAG DB logging
    from app.db.session import AsyncSessionLocal
    from app.db.models import User
    from sqlalchemy.future import select
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User))).scalars().first()
        user_id = user.id
    
    for idx, query in enumerate(queries, start=1):
        print(f"\n==================================================")
        print(f"Query {idx}: '{query}'")
        print(f"==================================================")
        
        # --- DETERMINISTIC RAG ---
        print("\n[Mode: DETERMINISTIC]")
        t0 = time.time()
        try:
            res_det = await rag_generator.generate_grounded_response(query, org_id, top_k=3)
            lat_det = time.time() - t0
            results_deterministic["total_latency"] += lat_det
            
            print(f"Answer: {res_det.answer}")
            print(f"Sources: {[s.filename for s in res_det.sources]}")
            print(f"Latency: {lat_det:.2f}s")
            
            if "do not contain enough information" in res_det.answer:
                results_deterministic["abstain"] += 1
            else:
                results_deterministic["success"] += 1
        except Exception as e:
            print(f"Deterministic failed: {e}")
            traceback.print_exc()

        # --- AGENTIC RAG ---
        print("\n[Mode: AGENTIC]")
        t1 = time.time()
        try:
            res_agt = await agentic_orchestrator.run(query, org_id, user_id, top_k=3)
            lat_agt = time.time() - t1
            results_agentic["total_latency"] += lat_agt
            
            meta = res_agt.retrieval_metadata
            iters = meta.get("agentic_iterations", 1)
            results_agentic["total_iterations"] += iters
            results_agentic["llm_calls"] += meta.get("agentic_llm_calls", 0)
            results_agentic["retrieval_queries"] += meta.get("agentic_retrieval_queries", 0)
            
            print(f"Classification: {meta.get('agentic_classification')}")
            print(f"Iterations: {iters}")
            print(f"Answer: {res_agt.answer}")
            print(f"Sources: {[s.filename for s in res_agt.sources]}")
            print(f"Latency: {lat_agt:.2f}s")
            
            if "do not contain enough information" in res_agt.answer:
                results_agentic["abstain"] += 1
            else:
                results_agentic["success"] += 1
        except Exception as e:
            print(f"Agentic failed: {e}")
            traceback.print_exc()

    print("\n--- DECISION INTELLIGENCE EVALUATION ---")
    for idx, query in enumerate(EVAL_DECISION_DATASET, start=1):
        print(f"\n==================================================")
        print(f"Decision Query {idx}: '{query}'")
        print(f"==================================================")
        
        t2 = time.time()
        try:
            res_dec = await decision_engine.analyze(query, org_id, user_id)
            lat_dec = time.time() - t2
            results_decision["total_latency"] += lat_dec
            
            trace = res_dec.decision_trace
            results_decision["llm_calls"] += trace.llm_calls
            results_decision["retrieval_queries"] += trace.retrieval_queries
            
            print(f"Decision Type: {res_dec.decision_type}")
            print(f"Confidence: {res_dec.confidence}")
            if res_dec.decision_type == "abstained":
                print(f"Reason: {res_dec.reason}")
                results_decision["abstain"] += 1
            else:
                results_decision["success"] += 1
                
            print(f"Latency: {lat_dec:.2f}s")
            
        except Exception as e:
            print(f"Decision engine failed: {e}")
            traceback.print_exc()

    print("\n==================================================")
    print("FINAL EVALUATION COMPARISON")
    print("==================================================")
    print(f"Total Queries: {len(queries)}")
    print(f"Qdrant Backend Used: {qdrant_status}")
    
    print("\n--- Deterministic RAG ---")
    print(f"Successful Answers: {results_deterministic['success']}")
    print(f"Abstentions: {results_deterministic['abstain']}")
    print(f"Avg Latency: {(results_deterministic['total_latency'] / len(queries)):.2f}s")
    print(f"Estimated LLM Calls: {results_deterministic['llm_calls']}")
    
    print("\n--- Agentic RAG ---")
    print(f"Successful Answers: {results_agentic['success']}")
    print(f"Abstentions: {results_agentic['abstain']}")
    print(f"Avg Latency: {(results_agentic['total_latency'] / max(1, len(queries))):.2f}s")
    print(f"Actual LLM Calls: {results_agentic['llm_calls']}")
    print(f"Actual Retrieval Queries: {results_agentic['retrieval_queries']}")
    print(f"Total Iterations: {results_agentic['total_iterations']}")
    
    print("\n--- Decision Intelligence ---")
    print(f"Successful Answers: {results_decision['success']}")
    print(f"Abstentions: {results_decision['abstain']}")
    print(f"Avg Latency: {(results_decision['total_latency'] / max(1, len(EVAL_DECISION_DATASET))):.2f}s")
    print(f"Actual LLM Calls: {results_decision['llm_calls']}")
    print(f"Actual Retrieval Queries: {results_decision['retrieval_queries']}")

if __name__ == "__main__":
    asyncio.run(evaluate())
