import json
import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID
import uuid

from app.schemas.rag import RAGQueryResponse, CitationValidation
from app.schemas.agent import AgentState, AgentStepPayload
from app.services.retrieval.retriever import HybridRetriever
from app.services.retrieval.reranker import reranker_service
from app.services.rag.context import build_context, GROUNDING_SYSTEM_PROMPT
from app.services.rag.generator import rag_generator, get_org_document_registry
from app.llm.provider import ChatMessage
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.db.models import AgentRun, AgentStep

logger = logging.getLogger(__name__)

# Configurable Limits
MAX_AGENT_ITERATIONS = 3
MAX_AGENT_RETRIEVAL_QUERIES = 5
MAX_AGENT_LLM_CALLS = 5
MAX_AGENT_LATENCY_SECONDS = 30.0

class AgenticRAGOrchestrator:
    def __init__(self):
        self.llm_provider = rag_generator.llm_provider

    def _check_limits(self, state: AgentState, start_time: float, check_type: str) -> Tuple[bool, str]:
        elapsed = time.monotonic() - start_time
        if elapsed >= MAX_AGENT_LATENCY_SECONDS:
            return False, f"Timeout reached ({elapsed:.2f}s)"
        if check_type == "llm" and state.llm_call_count >= MAX_AGENT_LLM_CALLS:
            return False, "Max LLM calls reached"
        if check_type == "retrieval" and state.retrieval_query_count >= MAX_AGENT_RETRIEVAL_QUERIES:
            return False, "Max retrieval queries reached"
        if check_type == "iteration" and state.current_iteration >= state.max_iterations:
            return False, "Max iterations reached"
        return True, ""

    async def _safe_llm_call(self, messages: List[ChatMessage], state: AgentState, start_time: float) -> str:
        ok, reason = self._check_limits(state, start_time, "llm")
        if not ok:
            raise TimeoutError(reason)
        state.llm_call_count += 1
        res = await self.llm_provider.generate_response(messages)
        return str(res or "")

    async def run(
        self,
        query: str,
        org_id: UUID,
        user_id: UUID,
        top_k: int = 5,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> RAGQueryResponse:
        start_time = time.monotonic()
        
        run_id = uuid.uuid4()
        
        # 1. Initialize DB Run
        async with AsyncSessionLocal() as db:
            run = AgentRun(
                id=run_id,
                org_id=org_id,
                user_id=user_id,
                original_query=query,
                status="processing",
                iterations=0
            )
            db.add(run)
            await db.commit()

        # 2. Initialize State
        state = AgentState(
            run_id=run_id,
            org_id=org_id,
            user_id=user_id,
            original_query=query,
            max_iterations=MAX_AGENT_ITERATIONS
        )

        try:
            # 3. Fetch Organization Document Registry
            doc_registry = await get_org_document_registry(org_id)

            # 4. Coordinator: Classify & Plan
            try:
                classification, initial_plan = await self._classify_and_plan(query, state, start_time)
            except TimeoutError as e:
                state.status = "abstained"
                await self._log_step(run_id, "limit_reached", AgentStepPayload(reason=str(e)), state)
                classification, initial_plan = "simple", [query]
                
            state.classification = classification
            state.retrieval_plan = initial_plan
            
            if state.status != "abstained":
                await self._log_step(run_id, "plan", AgentStepPayload(decision=classification, sub_query=str(initial_plan)), state)

            # 5. Agentic Loop
            while state.status != "abstained" and state.current_iteration < state.max_iterations:
                ok, reason = self._check_limits(state, start_time, "iteration")
                if not ok:
                    state.status = "abstained"
                    await self._log_step(run_id, "limit_reached", AgentStepPayload(reason=reason), state)
                    break
                    
                state.current_iteration += 1
                
                # Retrieve
                current_queries = state.retrieval_plan if state.current_iteration == 1 else [state.original_query]
                if state.status == "refining" and state.retrieval_plan:
                    current_queries = state.retrieval_plan
                    
                new_evidence = []
                for q in current_queries:
                    ok, reason = self._check_limits(state, start_time, "retrieval")
                    if not ok:
                        await self._log_step(run_id, "limit_reached", AgentStepPayload(reason=reason), state)
                        break
                        
                    state.retrieval_query_count += 1
                    
                    # Call Retrieval Agent
                    results = await self._retrieve(q, org_id, top_k, conversation_history)
                    new_evidence.extend(results)
                    
                # Deduplicate and sort evidence
                state.accumulated_evidence = self._merge_evidence(state.accumulated_evidence, new_evidence)
                
                await self._log_step(run_id, "retrieve", AgentStepPayload(retrieved_chunk_ids=[str(c.chunk_id) for c in new_evidence]), state)

                # Synthesis Agent: Evaluate
                if not state.accumulated_evidence:
                    if doc_registry:
                        # Metadata evidence is available even without text chunks
                        state.is_sufficient = True
                        reason = "Document registry metadata available."
                    else:
                        state.is_sufficient = False
                        reason = "No documents found."
                elif state.classification == "simple":
                    state.is_sufficient = True
                    reason = "Simple query optimization bypasses evaluation."
                else:
                    try:
                        state.is_sufficient, reason = await self._evaluate_evidence(state.original_query, state.accumulated_evidence, doc_registry, state, start_time)
                    except TimeoutError as e:
                        state.status = "abstained"
                        await self._log_step(run_id, "limit_reached", AgentStepPayload(reason=str(e)), state)
                        break
                
                await self._log_step(run_id, "evaluate", AgentStepPayload(decision=str(state.is_sufficient), reason=reason), state)

                if state.is_sufficient:
                    break
                else:
                    # Refine
                    if state.current_iteration < state.max_iterations:
                        try:
                            refined = await self._refine_query(state.original_query, reason, state, start_time)
                            state.retrieval_plan = [refined]
                            state.status = "refining"
                            await self._log_step(run_id, "refine", AgentStepPayload(refined_query=refined, reason=reason), state)
                        except TimeoutError as e:
                            state.status = "abstained"
                            await self._log_step(run_id, "limit_reached", AgentStepPayload(reason=str(e)), state)
                            break

            # 6. Synthesize or Abstain
            if state.status == "abstained" or (not state.is_sufficient and not state.accumulated_evidence and not doc_registry):
                final_answer = "The available documents do not contain enough information to answer this question."
                state.status = "abstained"
                final_sources = []
                cv = CitationValidation(valid_citations=[], invalid_citations=[])
            else:
                try:
                    final_answer, final_sources, cv = await self._synthesize(
                        state.original_query,
                        state.accumulated_evidence,
                        doc_registry,
                        state,
                        start_time,
                        conversation_history=conversation_history
                    )
                    state.status = "completed"
                except TimeoutError as e:
                    final_answer = "The available documents do not contain enough information to answer this question."
                    state.status = "abstained"
                    final_sources = []
                    cv = CitationValidation(valid_citations=[], invalid_citations=[])
                    await self._log_step(run_id, "limit_reached", AgentStepPayload(reason=str(e)), state)
                
            state.final_answer = final_answer
            
            # Update DB Run
            total_latency = (time.monotonic() - start_time) * 1000
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                if run:
                    run.status = state.status
                    run.classification = state.classification
                    run.iterations = state.current_iteration
                    run.total_latency_ms = total_latency
                    await db.commit()

            return RAGQueryResponse(
                query=query,
                answer=final_answer,
                sources=final_sources,
                retrieval_metadata={
                    "hybrid_candidates": len(state.accumulated_evidence),
                    "reranked_results": len(state.accumulated_evidence),
                    "context_sources_provided": len(final_sources),
                    "documents_in_registry": len(doc_registry),
                    "agentic_iterations": state.current_iteration,
                    "agentic_classification": state.classification,
                    "agentic_retrieval_queries": state.retrieval_query_count,
                    "agentic_llm_calls": state.llm_call_count,
                    "run_id": str(run_id)
                },
                citation_validation=cv
            )

        except TimeoutError as e:
            logger.warning(f"Agentic RAG timeout: {e}")
            final_answer = "The available documents do not contain enough information to answer this question."
            total_latency = (time.monotonic() - start_time) * 1000
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                if run:
                    run.status = "abstained"
                    run.iterations = state.current_iteration
                    run.total_latency_ms = total_latency
                    await db.commit()
            return RAGQueryResponse(
                query=query,
                answer=final_answer,
                sources=[],
                retrieval_metadata={
                    "hybrid_candidates": 0,
                    "reranked_results": 0,
                    "context_sources_provided": 0,
                    "documents_in_registry": len(doc_registry) if 'doc_registry' in locals() else 0,
                    "agentic_iterations": state.current_iteration,
                    "agentic_classification": state.classification,
                    "agentic_retrieval_queries": state.retrieval_query_count,
                    "agentic_llm_calls": state.llm_call_count,
                    "run_id": str(run_id)
                },
                citation_validation=CitationValidation(valid_citations=[], invalid_citations=[])
            )
        except Exception as e:
            logger.error(f"Agentic RAG Error: {e}")
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                if run:
                    run.status = "failed"
                    run.total_latency_ms = (time.monotonic() - start_time) * 1000
                    await db.commit()
            raise e

    async def _classify_and_plan(self, query: str, state: AgentState, start_time: float) -> Tuple[str, List[str]]:
        prompt = f"""Analyze the user's query and classify it into one of: 'simple', 'comparison', 'multi-hop', 'metadata', 'ambiguous'.
If it requires breaking down, provide sub-queries.
Return ONLY valid JSON: {{"classification": "...", "sub_queries": ["..."]}}
Query: {query}"""
        
        try:
            res = await self._safe_llm_call([ChatMessage(role="user", content=prompt)], state, start_time)
            import re
            if res and isinstance(res, str):
                match = re.search(r'\{.*\}', res, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    c = data.get("classification", "simple")
                    sq = data.get("sub_queries", [])
                    if not sq: sq = [query]
                    return c, [str(q) for q in sq if q]
        except TimeoutError:
            raise
        except Exception as e:
            logger.warning(f"Classification failed, defaulting to simple: {e}")
        return "simple", [query]

    async def _retrieve(self, query: str, org_id: UUID, top_k: int, conversation_history: Optional[List[Dict[str, str]]] = None):
        hybrid_cands = await HybridRetriever.search(
            query=query, 
            org_id=org_id, 
            top_k=settings.FINAL_TOP_K,
            conversation_history=conversation_history
        )
        reranked = await reranker_service.rerank_results(query, hybrid_cands, org_id, top_k)
        
        # STRICT TENANT ISOLATION
        for r in reranked:
            if str(r.org_id) != str(org_id):
                logger.error(f"CRITICAL: Cross-tenant leakage detected! Chunk {r.chunk_id} != {org_id}.")
                raise Exception("Security Error: Cross-tenant data detected in RAG pipeline.")
        return reranked

    def _merge_evidence(self, existing, new_evidence):
        seen = {str(e.chunk_id) for e in existing}
        merged = list(existing)
        for e in new_evidence:
            if str(e.chunk_id) not in seen:
                merged.append(e)
                seen.add(str(e.chunk_id))
        # Keep top N
        return sorted(merged, key=lambda x: x.final_rank or 999)[:settings.FINAL_TOP_K]

    async def _evaluate_evidence(self, query: str, evidence: List[Any], doc_registry: List[Dict[str, Any]], state: AgentState, start_time: float) -> Tuple[bool, str]:
        # 1. Deterministic signals
        if not evidence:
            if doc_registry:
                return True, "Document registry metadata available."
            return False, "No evidence chunks retrieved."
        
        highly_relevant = [e for e in evidence if getattr(e, 'rerank_score', 0) and e.rerank_score > 0.1]
        
        if len(highly_relevant) >= 2:
            return True, "Found multiple highly relevant chunks."
            
        if len(evidence) >= 5:
            return True, "Max evidence chunks reached."
            
        # 2. LLM Fallback for ambiguous cases
        context_text, _ = build_context(evidence, doc_registry)
        prompt = f"""Determine if the following evidence is sufficient to answer the query.
Return ONLY valid JSON: {{"is_sufficient": true/false, "reason": "why or what is missing"}}
Evidence:
{context_text}

Query: {query}"""
        try:
            res = await self._safe_llm_call([ChatMessage(role="user", content=prompt)], state, start_time)
            import re
            if res and isinstance(res, str):
                match = re.search(r'\{.*\}', res, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return bool(data.get("is_sufficient", False)), str(data.get("reason", "Unknown"))
        except TimeoutError:
            raise
        except Exception as e:
            logger.warning(f"Evaluation failed: {e}")
            
        return True, "Default sufficient due to error"

    async def _refine_query(self, query: str, reason: str, state: AgentState, start_time: float) -> str:
        prompt = f"""The previous retrieval was insufficient. Reason: {reason}.
Original query: {query}
Generate a refined search query to find the missing information. Return ONLY the new query string, nothing else."""
        try:
            res = await self._safe_llm_call([ChatMessage(role="user", content=prompt)], state, start_time)
            refined = str(res or "").strip()
            return refined if refined else query
        except Exception as e:
            logger.warning(f"Query refinement failed, defaulting to original query: {e}")
            return query

    async def _synthesize(
        self,
        query: str,
        evidence: List[Any],
        doc_registry: List[Dict[str, Any]],
        state: AgentState,
        start_time: float,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ):
        context_text, cited_sources = build_context(evidence, doc_registry)
        messages = [
            ChatMessage(role="system", content=GROUNDING_SYSTEM_PROMPT)
        ]

        if conversation_history:
            for turn in conversation_history[-6:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if content and role in ["user", "assistant"]:
                    messages.append(ChatMessage(role=role, content=content))

        messages.append(
            ChatMessage(role="user", content=f"Evidence Context:\n{context_text}\n\nQuestion: {query}")
        )
        
        answer = await self._safe_llm_call(messages, state, start_time)
        if not answer or not str(answer).strip():
            answer = "The available documents do not contain enough information to answer this question."
        
        # Citation Validation
        import re
        cited_ids_in_answer = set(re.findall(r"\[Source\s+(\d+)\]", answer))
        valid_ids = set([s.source_id for s in cited_sources])
        
        valid_citations = []
        invalid_citations = []
        for cid in cited_ids_in_answer:
            if cid in valid_ids:
                valid_citations.append(f"[Source {cid}]")
            else:
                invalid_citations.append(f"[Source {cid}]")
                
        final_sources = [s for s in cited_sources if s.source_id in cited_ids_in_answer]
        cv = CitationValidation(valid_citations=valid_citations, invalid_citations=invalid_citations)
        return answer, final_sources, cv

    async def _log_step(self, run_id: UUID, step_type: str, payload: AgentStepPayload, state: AgentState):
        start = time.monotonic()
        async with AsyncSessionLocal() as db:
            p_dump = payload.model_dump(exclude_unset=True)
            p_dump.update({
                "iteration": state.current_iteration,
                "status": state.status,
                "retrieval_query_count": state.retrieval_query_count,
                "llm_call_count": state.llm_call_count,
                "latency_ms": (time.monotonic() - start) * 1000
            })
            step = AgentStep(
                run_id=run_id,
                step_type=step_type,
                latency_ms=(time.monotonic() - start) * 1000,
                payload=p_dump
            )
            db.add(step)
            await db.commit()

agentic_orchestrator = AgenticRAGOrchestrator()
