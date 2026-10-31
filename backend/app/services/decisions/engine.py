import json
import logging
import time
import uuid
from uuid import UUID
from typing import List, Dict, Any

from app.schemas.decision import (
    DecisionTrace, DecisionConflict, DecisionResponseBase, ComparisonResponse,
    RecommendationResponse, RiskAnalysisResponse, ImpactAnalysisResponse,
    DecisionMatrixResponse, AbstainDecisionResponse, GeneralInformationResponse
)
from app.schemas.rag import CitationValidation
from app.schemas.agent import AgentState, AgentStepPayload
from app.db.session import AsyncSessionLocal
from app.db.models import AgentRun, AgentStep
from app.llm.provider import ChatMessage
from app.services.rag.orchestrator import agentic_orchestrator
from app.services.rag.context import build_context
from app.services.decisions.analyzers import analyzers

logger = logging.getLogger(__name__)

class DecisionIntelligenceEngine:
    async def analyze(self, query: str, org_id: UUID, user_id: UUID) -> DecisionResponseBase:
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
                iterations=0,
                classification="decision_pending"
            )
            db.add(run)
            await db.commit()

        # 2. Initialize Agent State to reuse limit tracking
        state = AgentState(
            run_id=run_id,
            org_id=org_id,
            user_id=user_id,
            original_query=query,
            max_iterations=3 # max retries if needed
        )

        try:
            # 3. Classify Query
            decision_type = await self._classify_decision_type(query, state, start_time)
            state.classification = decision_type
            await self._log_step(run_id, "decision_classification", AgentStepPayload(decision=decision_type), state, start_time)
            
            # If general_information, fallback to AgenticRAG
            if decision_type == "general_information":
                # A full agentic run might be excessive inside this wrapper, but we can do a simple hybrid retrieval and synthesize
                rag_resp = await agentic_orchestrator.run(query, org_id, user_id)
                
                dt = DecisionTrace(
                    run_id=run_id,
                    iterations=rag_resp.retrieval_metadata.get("agentic_iterations", 0),
                    llm_calls=rag_resp.retrieval_metadata.get("agentic_llm_calls", 1),
                    retrieval_queries=rag_resp.retrieval_metadata.get("agentic_retrieval_queries", 1),
                    latency_ms=(time.monotonic() - start_time) * 1000,
                    evidence_count=len(rag_resp.sources),
                    document_count=len({s.document_id for s in rag_resp.sources})
                )
                
                await self._finalize_run(run_id, decision_type, "completed", state, dt)
                return GeneralInformationResponse(
                    decision_type="general_information",
                    confidence=0.8,
                    answer=rag_resp.answer,
                    sources=rag_resp.sources,
                    decision_trace=dt
                )
                
            # 4. Evidence Collection (Retrieve)
            evidence = await agentic_orchestrator._retrieve(query, org_id, top_k=10)
            state.retrieval_query_count += 1
            await self._log_step(run_id, "retrieve_evidence", AgentStepPayload(retrieved_chunk_ids=[str(e.chunk_id) for e in evidence]), state, start_time)
            
            if not evidence:
                raise TimeoutError("No evidence retrieved to support decision analysis.")
                
            context_text, cited_sources = build_context(evidence)
            
            # 5. Detect Conflicts
            conflicts = await analyzers.detect_conflicts(context_text)
            state.llm_call_count += 1
            await self._log_step(run_id, "conflict_detection", AgentStepPayload(decision=str(len(conflicts)) + " conflicts found"), state, start_time)
            
            # 6. Branch by Decision Type
            confidence = self._calculate_confidence(evidence, conflicts)
            
            dt = DecisionTrace(
                run_id=run_id,
                iterations=1,
                llm_calls=state.llm_call_count + 1,
                retrieval_queries=state.retrieval_query_count,
                latency_ms=0.0, # updated later
                evidence_count=len(evidence),
                document_count=len({e.document_id for e in evidence})
            )

            # Route to correct analyzer
            if decision_type == "comparison":
                sims, diffs, advs, disadvs = await analyzers.analyze_comparison(query, context_text)
                state.llm_call_count += 1
                resp = ComparisonResponse(
                    confidence=confidence,
                    conflicts=conflicts,
                    sources=cited_sources,
                    decision_trace=dt,
                    similarities=sims,
                    differences=diffs,
                    advantages=advs,
                    disadvantages=disadvs
                )
            elif decision_type == "recommendation":
                rec, reasoning, alts = await analyzers.analyze_recommendation(query, context_text)
                state.llm_call_count += 1
                factors = await analyzers.extract_factors(query, context_text)
                state.llm_call_count += 1
                
                resp = RecommendationResponse(
                    confidence=confidence,
                    conflicts=conflicts,
                    sources=cited_sources,
                    decision_trace=dt,
                    recommendation=rec,
                    reasoning=reasoning,
                    factors=factors,
                    alternatives=alts
                )
            elif decision_type == "risk_analysis":
                risks = await analyzers.analyze_risk(query, context_text)
                state.llm_call_count += 1
                resp = RiskAnalysisResponse(
                    confidence=confidence,
                    conflicts=conflicts,
                    sources=cited_sources,
                    decision_trace=dt,
                    risks=risks
                )
            elif decision_type == "impact_analysis":
                impacts, deps = await analyzers.analyze_impact(query, context_text)
                state.llm_call_count += 1
                resp = ImpactAnalysisResponse(
                    confidence=confidence,
                    conflicts=conflicts,
                    sources=cited_sources,
                    decision_trace=dt,
                    impacts=impacts,
                    dependencies=deps
                )
            elif decision_type == "decision_matrix":
                criteria, scores, total_scores = await analyzers.calculate_matrix(query, context_text)
                state.llm_call_count += 1
                resp = DecisionMatrixResponse(
                    confidence=confidence,
                    conflicts=conflicts,
                    sources=cited_sources,
                    decision_trace=dt,
                    criteria=criteria,
                    scores=scores,
                    total_scores=total_scores
                )
            else:
                raise ValueError("Unknown decision type")
                
            # Citation Validation Filter
            resp = self._validate_citations(resp, cited_sources)
            
            # Update trace latency
            resp.decision_trace.llm_calls = state.llm_call_count
            resp.decision_trace.latency_ms = (time.monotonic() - start_time) * 1000
            
            await self._finalize_run(run_id, decision_type, "completed", state, resp.decision_trace)
            return resp

        except TimeoutError as e:
            logger.warning(f"Decision Engine limits reached: {e}")
            dt = DecisionTrace(
                run_id=run_id,
                iterations=state.current_iteration,
                llm_calls=state.llm_call_count,
                retrieval_queries=state.retrieval_query_count,
                latency_ms=(time.monotonic() - start_time) * 1000,
                evidence_count=0,
                document_count=0
            )
            await self._finalize_run(run_id, "abstained", "abstained", state, dt)
            return AbstainDecisionResponse(
                confidence=0.0,
                reason=str(e),
                decision_trace=dt
            )
            
        except Exception as e:
            logger.error(f"Decision Engine Error: {e}")
            async with AsyncSessionLocal() as db:
                run = await db.get(AgentRun, run_id)
                run.status = "failed"
                run.total_latency_ms = (time.monotonic() - start_time) * 1000
                await db.commit()
            raise e

    async def _classify_decision_type(self, query: str, state: AgentState, start_time: float) -> str:
        prompt = f"""Classify the user's intent into ONE of the following categories:
- comparison: comparing two or more options.
- recommendation: asking for a choice, advice, or recommendation.
- risk_analysis: asking about risks, dangers, downsides.
- impact_analysis: asking about impact, effects, or downstream dependencies.
- decision_matrix: explicitly asking for structured evaluation/scores.
- general_information: just a factual question (e.g. "who is", "what is", "where is", "when did").

Return ONLY valid JSON: {{"decision_type": "..."}}

Query: {query}"""
        try:
            res = await agentic_orchestrator._safe_llm_call([ChatMessage(role="user", content=prompt)], state, start_time)
            import re
            if res and isinstance(res, str):
                match = re.search(r'\{.*\}', res, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    return data.get("decision_type", "general_information")
        except Exception as e:
            logger.warning(f"Decision classification failed: {e}")
        return "general_information"

    def _calculate_confidence(self, evidence: List[Any], conflicts: List[DecisionConflict]) -> float:
        # Deterministic rules for confidence
        base_confidence = 0.5
        
        # Evidence coverage
        if len(evidence) >= 5:
            base_confidence += 0.2
        elif len(evidence) >= 2:
            base_confidence += 0.1
            
        # Source diversity
        doc_ids = {str(e.document_id) for e in evidence}
        if len(doc_ids) >= 3:
            base_confidence += 0.2
        elif len(doc_ids) == 2:
            base_confidence += 0.1
            
        # Conflict penalty
        if len(conflicts) > 0:
            base_confidence -= min(0.3, len(conflicts) * 0.1)
            
        return max(0.1, min(0.99, base_confidence))

    def _validate_citations(self, response: DecisionResponseBase, cited_sources: List[Any]) -> DecisionResponseBase:
        # We will filter out any DecisionFactor or Risk where source_id is not in cited_sources
        valid_ids = {str(s.source_id) for s in cited_sources}
        
        def filter_factors(factors):
            if not factors: return []
            return [f for f in factors if f.source_id in valid_ids]
            
        def filter_risks(risks):
            if not risks: return []
            return [r for r in risks if r.source_id in valid_ids]
            
        def filter_impacts(impacts):
            if not impacts: return []
            return [i for i in impacts if i.source_id in valid_ids]
            
        def filter_alternatives(alts):
            if not alts: return []
            return [a for a in alts if a.source_id in valid_ids]

        if hasattr(response, 'factors'):
            response.factors = filter_factors(response.factors)
        if hasattr(response, 'similarities'):
            response.similarities = filter_factors(response.similarities)
            response.differences = filter_factors(response.differences)
            response.advantages = filter_factors(response.advantages)
            response.disadvantages = filter_factors(response.disadvantages)
        if hasattr(response, 'risks'):
            response.risks = filter_risks(response.risks)
        if hasattr(response, 'impacts'):
            response.impacts = filter_impacts(response.impacts)
            response.dependencies = filter_factors(response.dependencies)
        if hasattr(response, 'alternatives'):
            response.alternatives = filter_alternatives(response.alternatives)
            
        return response

    async def _log_step(self, run_id: UUID, step_type: str, payload: AgentStepPayload, state: AgentState, start_time: float):
        async with AsyncSessionLocal() as db:
            p_dump = payload.model_dump(exclude_unset=True)
            step = AgentStep(
                run_id=run_id,
                step_type=step_type,
                latency_ms=(time.monotonic() - start_time) * 1000,
                payload=p_dump
            )
            db.add(step)
            await db.commit()
            
    async def _finalize_run(self, run_id: UUID, classification: str, status: str, state: AgentState, trace: DecisionTrace):
        async with AsyncSessionLocal() as db:
            run = await db.get(AgentRun, run_id)
            run.classification = classification
            run.status = status
            run.iterations = trace.iterations
            run.total_latency_ms = trace.latency_ms
            run.workflow_trace = trace.model_dump(mode="json")
            await db.commit()

decision_engine = DecisionIntelligenceEngine()
